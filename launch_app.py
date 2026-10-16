"""Installable PWA shell + authenticated HTTP/WebSocket gateway for Streamlit."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if (ROOT/'.vendor').exists():
    sys.path.insert(0,str(ROOT/'.vendor'))
import argparse
import asyncio
import hashlib
import hmac
import os
import secrets
import socket
import subprocess
import time
import re
import webbrowser
from urllib.parse import urlsplit
from aiohttp import web, ClientSession, ClientTimeout, WSMsgType

COOKIE='dongnae_session'
HOP={'connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','transfer-encoding','upgrade'}


def create_app(upstream, password='', root=ROOT):
    signing_key=secrets.token_bytes(32)
    failures=[]
    def signed(expiry):
        value=str(expiry)
        return value+'.'+hmac.new(signing_key,value.encode(),hashlib.sha256).hexdigest()
    def authenticated(request):
        if not password:
            return True
        value=request.cookies.get(COOKIE,'')
        try:
            expiry=int(value.split('.')[0])
            return expiry>time.time() and hmac.compare_digest(value,signed(expiry))
        except (ValueError,IndexError,TypeError):
            return False
    def same_origin(request):
        origin=request.headers.get('Origin')
        return not origin or urlsplit(origin).netloc==request.host
    @web.middleware
    async def guard(request,handler):
        public=request.path in ('/healthz','/login','/manifest.webmanifest','/sw.js','/offline.html') or request.path.startswith('/pwa/') or bool(re.fullmatch(r'/c/[A-Za-z0-9_-]{20,80}(?:/(?:booking|map|coupon))?',request.path))
        if not public and not authenticated(request):
            if request.headers.get('Upgrade','').lower()=='websocket':
                return web.Response(status=401,text='Login required')
            return web.HTTPFound('/login')
        if request.method not in ('GET','HEAD','OPTIONS') and not same_origin(request):
            return web.Response(status=403,text='Origin rejected')
        response=await handler(request)
        if not response.prepared:
            response.headers['X-Content-Type-Options']='nosniff'
            response.headers['X-Frame-Options']='SAMEORIGIN'
            response.headers['Referrer-Policy']='same-origin'
            if not request.path.startswith('/pwa/'):
                response.headers['Cache-Control']='no-store'
        return response
    app=web.Application(middlewares=[guard],client_max_size=200*1024*1024)
    async def index(request):
        page=(root/'pwa'/'index.html').read_text(encoding='utf-8')
        if not password:
            page=page.replace('<form method="post" action="/logout"><button type="submit">잠금</button></form>','')
        return web.Response(text=page,content_type='text/html')
    async def login(request):
        if not password:
            return web.HTTPFound('/')
        error=''
        if request.method=='POST':
            if request.content_length and request.content_length>4096:
                return web.Response(status=413,text='Login request too large')
            now=time.time()
            failures[:]=[t for t in failures if now-t<60]
            if len(failures)>=8:
                return web.Response(status=429,text='잠시 후 다시 시도해 주세요.',content_type='text/plain')
            data=await request.post()
            if hmac.compare_digest(str(data.get('password','')).encode(),password.encode()):
                response=web.HTTPSeeOther('/')
                secure=request.secure or request.headers.get('X-Forwarded-Proto')=='https'
                response.set_cookie(COOKIE,signed(int(now)+86400),httponly=True,secure=secure,samesite='Strict',max_age=86400,path='/')
                return response
            failures.append(now)
            error='비밀번호를 다시 확인해 주세요.'
        page=(root/'pwa'/'login.html').read_text(encoding='utf-8').replace('{{ERROR}}',error)
        return web.Response(text=page,content_type='text/html')
    async def logout(request):
        response=web.HTTPSeeOther('/login')
        response.del_cookie(COOKIE,path='/')
        return response
    async def health(request):
        return web.json_response({'status':'ok'})
    async def static_root(request):
        name=request.path.lstrip('/')
        response=web.FileResponse(root/'pwa'/name)
        if name=='manifest.webmanifest':
            response.content_type='application/manifest+json'
        if name=='sw.js':
            response.headers['Service-Worker-Allowed']='/'
        return response
    async def proxy(request):
        target=upstream+request.raw_path
        headers={k:v for k,v in request.headers.items() if k.lower() not in HOP|{'host','content-length'} and not k.lower().startswith('sec-websocket-')}
        if request.headers.get('Upgrade','').lower()=='websocket':
            if not same_origin(request):
                return web.Response(status=403,text='Origin rejected')
            protocols=[p.strip() for p in request.headers.get('Sec-WebSocket-Protocol','').split(',') if p.strip()]
            headers['Origin']=upstream
            async with app['client'].ws_connect(target,headers=headers,protocols=protocols,max_msg_size=200*1024*1024,heartbeat=30) as remote:
                local=web.WebSocketResponse(protocols=[remote.protocol] if remote.protocol else (),max_msg_size=200*1024*1024,heartbeat=30)
                await local.prepare(request)
                async def relay(source,destination):
                    async for message in source:
                        if message.type==WSMsgType.TEXT: await destination.send_str(message.data)
                        elif message.type==WSMsgType.BINARY: await destination.send_bytes(message.data)
                        elif message.type in (WSMsgType.CLOSE,WSMsgType.CLOSED,WSMsgType.ERROR): break
                tasks=[asyncio.create_task(relay(local,remote)),asyncio.create_task(relay(remote,local))]
                try:
                    await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks: task.cancel()
                    await asyncio.gather(*tasks,return_exceptions=True)
                    await local.close()
                return local
        data=await request.read() if request.can_read_body else None
        async with app['client'].request(request.method,target,headers=headers,data=data,allow_redirects=False) as remote:
            response_headers=remote.headers.copy()
            for name in list(response_headers):
                if name.lower() in HOP: response_headers.popall(name,None)
            response_headers['Cache-Control']='no-store'
            response_headers['X-Frame-Options']='SAMEORIGIN'
            response=web.StreamResponse(status=remote.status,headers=response_headers)
            await response.prepare(request)
            async for chunk in remote.content.iter_chunked(65536): await response.write(chunk)
            await response.write_eof()
            return response
    async def client_context(app):
        app['client']=ClientSession(timeout=ClientTimeout(total=None,connect=20,sock_read=300),auto_decompress=False)
        yield
        await app['client'].close()
    app.cleanup_ctx.append(client_context)
    app.router.add_get('/',index)
    app.router.add_route('*','/login',login)
    app.router.add_post('/logout',logout)
    app.router.add_get('/healthz',health)
    for name in ('manifest.webmanifest','sw.js','offline.html'):
        app.router.add_get('/'+name,static_root)
    app.router.add_static('/pwa/',root/'pwa',show_index=False,follow_symlinks=False)
    from campaign_web import register_campaign_routes
    register_campaign_routes(app)
    app.router.add_route('*','/studio/{tail:.*}',proxy)
    return app


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=int(os.getenv('PORT','8503')))
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    password=os.getenv('DONGNAE_APP_PASSWORD','')
    if args.host not in ('127.0.0.1','localhost') and len(password)<12:
        parser.error('외부 공개 시 DONGNAE_APP_PASSWORD를 12자 이상 설정해 주세요.')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); internal_port=sock.getsockname()[1]
    runtime=ROOT/'.runtime'; runtime.mkdir(exist_ok=True)
    upstream=f'http://127.0.0.1:{internal_port}'
    app=create_app(upstream,password)
    async def backend_context(app):
        log=open(runtime/'backend.log','a',encoding='utf-8')
        env=os.environ.copy(); env.pop('DONGNAE_APP_PASSWORD',None)
        env['PYTHONIOENCODING']='utf-8'
        child=subprocess.Popen([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),
            f'--server.port={internal_port}','--server.address=127.0.0.1','--server.baseUrlPath=studio',
            '--theme.base=light','--theme.primaryColor=#d95b39','--theme.backgroundColor=#f6f5f1','--theme.secondaryBackgroundColor=#eeefe7','--theme.textColor=#252a26',
            '--server.headless=true','--browser.gatherUsageStats=false','--server.fileWatcherType=none'],
            cwd=ROOT,env=env,stdout=log,stderr=log)
        try:
            async with ClientSession() as client:
                for attempt in range(40):
                    if child.poll() is not None: raise RuntimeError('광고 스튜디오 실행 실패: .runtime/backend.log 확인')
                    try:
                        async with client.get(upstream+'/studio/_stcore/health',timeout=ClientTimeout(total=2)) as response:
                            if response.status==200: break
                    except (OSError,asyncio.TimeoutError): pass
                    await asyncio.sleep(.5)
                else: raise RuntimeError('광고 스튜디오 시작 시간 초과')
            print(f'동네AI 앱: http://localhost:{args.port}',flush=True)
            if not args.no_browser:
                asyncio.get_running_loop().call_later(1,webbrowser.open,f'http://localhost:{args.port}')
            yield
        finally:
            child.terminate()
            try: child.wait(timeout=8)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
            log.close()
    app.cleanup_ctx.append(backend_context)
    web.run_app(app,host=args.host,port=args.port,access_log=None,print=None)


if __name__=='__main__': main()
