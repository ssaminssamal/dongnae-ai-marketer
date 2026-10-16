"""Public campaign landing pages. Owner controls remain behind gateway login."""
from __future__ import annotations
import html
import secrets
from aiohttp import web
import studio_store as store


def page(title,body):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#242e29"><title>'+html.escape(title)+'</title><style>body{margin:0;min-height:100dvh;background:#f6f5f1;color:#26362a;font-family:system-ui;display:grid;place-items:center}main{max-width:460px;width:86%;padding:40px 0}h1{font-size:30px;line-height:1.4;overflow-wrap:anywhere}p{line-height:1.9;white-space:pre-wrap;overflow-wrap:anywhere}button,a.action{display:block;text-align:center;box-sizing:border-box;width:100%;font:inherit;padding:16px;background:#26362a;border:0;color:#fff;border-radius:8px;margin:12px 0;text-decoration:none}small{display:block;color:#737d6d;font-size:11px;line-height:1.8}.code{font-size:26px;font-weight:800;letter-spacing:2px}.brand{font-size:12px;letter-spacing:1px}form{margin:0}</style><main>'+body+'</main></html>'


def register_campaign_routes(app):
    async def campaign(request):
        token=request.match_info['token']
        variant=store.public_variant(token)
        if not variant: return web.Response(status=404,text='가게 소식을 찾을 수 없습니다.')
        if not variant['available']:
            return web.Response(status=410,text=page('안내 종료','<h1>종료된 안내입니다.</h1><p>가게에 직접 문의해 주세요.</p>'),content_type='text/html')
        visitor=request.cookies.get('dn_visitor') or secrets.token_urlsafe(18)
        settings=variant['settings']; copy=variant['copy']
        action=request.match_info.get('action')
        if action:
            if request.method!='POST': return web.Response(status=405)
            kinds={'booking':'booking_click','map':'map_click','coupon':'coupon_claim'}
            if action not in kinds: return web.Response(status=404)
            if action in ('booking','map'):
                destination=settings.get('booking_url' if action=='booking' else 'map_url','')
                if not destination: return web.Response(status=404)
                store.record_event(token,kinds[action],visitor)
                response=web.HTTPSeeOther(store.safe_url(destination))
            else:
                if not settings.get('offer'): return web.Response(status=404)
                store.record_event(token,'coupon_claim',visitor)
                body='<p class="brand">'+html.escape(settings.get('store_name',''))+'</p><h1>가게에서 이 코드를 보여주세요.</h1><p class="code">'+html.escape(variant['code'])+'</p><p>'+html.escape(settings['offer'])+'</p><p>'+html.escape(settings.get('terms',''))+'</p><small>사용 기한: '+html.escape(settings['expires'])+' (한국 시간)<br>실제 사용 가능 여부와 중복 사용은 가게에서 확인합니다.</small><a class="action" href="/c/'+token+'">가게 소식으로 돌아가기</a>'
                response=web.Response(text=page('쿠폰 확인',body),content_type='text/html')
        else:
            store.record_event(token,'view',visitor)
            body='<p class="brand">'+html.escape(settings.get('store_name','동네 가게'))+'</p><h1>'+html.escape(copy['headline'])+'</h1><p>'+html.escape(copy.get('detail',''))+'</p>'
            if settings.get('address'): body+='<p>📍 '+html.escape(settings['address'])+'</p>'
            for action,label,enabled in [('booking','예약·문의 페이지 열기',bool(settings.get('booking_url'))),('map','길찾기 열기',bool(settings.get('map_url'))),('coupon','쿠폰 받기',bool(settings.get('offer')))]:
                if enabled: body+=f'<form method="post" action="/c/{token}/{action}"><button>{label}</button></form>'
            if settings.get('terms'): body+='<small>'+html.escape(settings['terms'])+'</small>'
            body+='<small>안내 기한: '+html.escape(settings['expires'])+' (한국 시간)<br>반응 집계에 익명 브라우저 쿠키를 사용합니다. 이름·전화번호·IP 주소는 이 기능에 저장하지 않습니다.</small>'
            response=web.Response(text=page(settings.get('store_name','동네AI'),body),content_type='text/html')
        response.set_cookie('dn_visitor',visitor,max_age=86400*30,httponly=True,samesite='Lax',secure=request.secure or request.headers.get('X-Forwarded-Proto')=='https')
        return response
    app.router.add_get('/c/{token:[A-Za-z0-9_-]{20,80}}',campaign)
    app.router.add_post('/c/{token:[A-Za-z0-9_-]{20,80}}/{action:booking|map|coupon}',campaign)
