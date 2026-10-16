from __future__ import annotations
from datetime import datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit
import base64
import csv
import io
import json
import re

import streamlit as st
from PIL import Image
import studio_store as store
from campaign_planner import SITUATIONS,plan_campaign,parse_market_csv

ROOT=Path(__file__).parent
BRAND_KEYS=['brand_name','subject_name','brand_description','brand_unique','business_choice','subject_choice',
            'location_name','area_choice','style_choice','goal_choice','brand_address','booking_url','map_url',
            'brand_color','logo_b64','voice_choice','voice_speed','voice_quality','bgm_choice','bgm_volume']
BRAND_KEYS += ['brand_menu','product_price']
DRAFT_KEYS=BRAND_KEYS+['ad_headline','ad_detail','ad_cta','ad_brand','ad_narration','campaign_situation',
    'campaign_availability','campaign_offer','campaign_terms','campaign_base_url','captions_enabled','voice_enabled',
    'variant_picker','ab_enabled','qr_enabled','scene_source','saved_scene_names','voice_source_choice']


def public_base():
    connection=ROOT/'.runtime'/'connection.txt'
    if connection.exists():
        match=re.search(r'https://[a-z0-9.-]+',connection.read_text(encoding='utf-8'))
        if match: return match.group(0)
    return 'http://localhost:8503'


def qr_png(url):
    import qrcode
    output=io.BytesIO()
    qrcode.make(url).convert('RGB').save(output,format='PNG')
    return output.getvalue()


def apply_variant(variant):
    st.session_state.update(ad_headline=variant['headline'],ad_detail=variant['detail'],ad_cta=variant['cta'],
                            ad_brand=variant['brand'],ad_narration=variant['narration'],draft_variant=variant['label'])


def sidebar_library():
    section=st.radio('작업 공간',['광고 제작','캠페인·성과','브랜드 보관함','완성 영상'],key='workspace_section')
    previous=st.session_state.get('_previous_workspace','광고 제작')
    if previous=='광고 제작' and section!='광고 제작':
        st.session_state['_workspace_draft']={k:st.session_state[k] for k in DRAFT_KEYS if k in st.session_state}
    if section=='광고 제작' and previous!='광고 제작':
        for key,value in st.session_state.get('_workspace_draft',{}).items():
            if key not in st.session_state: st.session_state[key]=value
    st.session_state['_previous_workspace']=section
    if section=='광고 제작' and st.session_state.get('_brand_to_load'):
        for key,value in st.session_state.pop('_brand_to_load').items():
            if key in BRAND_KEYS: st.session_state[key]=value
    brands=store.list_brands()
    if brands:
        lookup={b['id']:b for b in brands}
        selected=st.selectbox('저장된 브랜드',list(lookup),format_func=lambda key:lookup[key]['name'])
        if st.button('브랜드 불러오기',use_container_width=True):
            data=lookup[selected]['data']
            st.session_state['_brand_to_load']=data
            for key in BRAND_KEYS:
                if key in data: st.session_state[key]=data[key]
            st.session_state['loaded_brand_id']=selected
            st.session_state.pop('studio_variants',None)
            st.session_state.pop('active_campaign',None)
            st.success('저장된 브랜드를 불러왔습니다.')
    return section


def brand_controls():
    st.text_area('메뉴·서비스 목록',key='brand_menu',placeholder='한 줄에 하나씩 메뉴·서비스와 가격을 적어 두세요.',height=90)
    st.number_input('대표 상품·서비스 가격(원)',min_value=0,step=1000,key='product_price',help='0이면 광고 기획에서 가격을 쓰지 않습니다.')
    st.text_input('가게 주소',key='brand_address',placeholder='고객에게 안내할 실제 주소')
    st.text_input('예약·문의 링크',key='booking_url',placeholder='https://…')
    st.text_input('지도·길찾기 링크',key='map_url',placeholder='https://…')
    st.color_picker('브랜드 색상',value='#d95b39',key='brand_color')
    logo=st.file_uploader('브랜드 로고',type=['png','jpg','jpeg'],help='최대 2MB. 완성 영상 오른쪽 위에 표시됩니다.')
    if logo:
        try:
            if logo.size>2*1024*1024: raise ValueError('로고는 2MB 이하로 올려 주세요.')
            with Image.open(io.BytesIO(logo.getvalue())) as image:
                if max(image.size)>4096: raise ValueError('로고의 가로·세로는 4,096px 이하여야 합니다.')
                image=image.convert('RGBA'); image.thumbnail((512,512))
                buf=io.BytesIO(); image.save(buf,format='PNG')
                st.session_state['logo_b64']=base64.b64encode(buf.getvalue()).decode()
        except Exception as error: st.error(str(error))
    if st.session_state.get('logo_b64'):
        st.image(base64.b64decode(st.session_state['logo_b64']),width=100)
        if not logo and st.button('저장된 로고 지우기'): st.session_state['logo_b64']=''; st.rerun()
    a,b=st.columns(2)
    if a.button('브랜드 저장',use_container_width=True):
        try:
            payload={k:st.session_state[k] for k in BRAND_KEYS if k in st.session_state}
            store.safe_url(payload.get('booking_url','')); store.safe_url(payload.get('map_url',''))
            identity=store.save_brand(payload.get('brand_name',''),payload,st.session_state.get('loaded_brand_id'))
            st.session_state['loaded_brand_id']=identity
            st.success('브랜드와 현재 음성·음악 설정을 저장했습니다.')
        except ValueError as error: st.error(str(error))
    if b.button('새 브랜드로 저장',use_container_width=True):
        try:
            payload={k:st.session_state[k] for k in BRAND_KEYS if k in st.session_state}
            store.safe_url(payload.get('booking_url','')); store.safe_url(payload.get('map_url',''))
            st.session_state['loaded_brand_id']=store.save_brand(payload.get('brand_name',''),payload)
            st.success('새 브랜드로 저장했습니다.')
        except ValueError as error: st.error(str(error))


def situation_controls(form):
    st.markdown('#### 오늘 가게에는 어떤 일이 있나요?')
    situation=st.selectbox('오늘의 상황',SITUATIONS,key='campaign_situation')
    availability=st.text_input('실제 가능한 시간·남은 수량',placeholder='예: 내일 오후 2시·4시 예약 가능',key='campaign_availability')
    offer=st.text_input('실제로 제공할 혜택',placeholder='예: 방문 상담 시 두피 진단 제공 · 할인 없이 비워도 됩니다',key='campaign_offer')
    terms=st.text_area('혜택 조건',placeholder='대상·가능 시간·제외 항목 등 고객에게 안내할 조건',key='campaign_terms',height=90)
    if st.button('상황에 맞는 A/B 기획 만들기',type='primary',use_container_width=True):
        try:
            plan=plan_campaign(form,situation,availability,offer,terms)
            st.session_state['studio_variants']=plan['variants']
            st.session_state['variant_picker']='A'
            st.session_state['plan_rationale']=plan['rationale']
            apply_variant(plan['variants'][0])
            st.session_state.pop('active_campaign',None)
            st.success('카피 · 음성 탭에서 A와 B를 비교하고 수정할 수 있습니다.')
        except ValueError as error: st.error(str(error))
    for reason in st.session_state.get('plan_rationale',[]): st.caption(reason)
    st.caption('현재는 입력 사실을 조합하는 설명 가능한 기획 엔진입니다. 확인되지 않은 할인·매출 수치는 만들지 않습니다.')


def variant_selector():
    variants=st.session_state.get('studio_variants',[])
    if variants:
        selected=st.radio('편집할 광고',['A','B'],horizontal=True,key='variant_picker')
        if st.button(f'{selected}안 문구 불러오기'):
            apply_variant(next(v for v in variants if v['label']==selected))
        st.caption('불러온 문구를 아래에서 수정하면 해당 안에 반영됩니다.')


def update_variant(headline,detail,cta,brand,narration):
    label=st.session_state.get('draft_variant','A')
    current=dict(label=label,headline=headline,detail=detail,cta=cta,brand=brand,narration=narration)
    variants=st.session_state.get('studio_variants')
    if variants:
        st.session_state['studio_variants']=[current if v['label']==label else v for v in variants]
    return current


def market_controls(region):
    st.markdown('#### 출처가 있는 지역 자료')
    st.caption('공공데이터나 직접 조사한 CSV를 가져옵니다. 파일에 적힌 출처의 진위는 자동 검증하지 않습니다.')
    example='region,metric,value,unit,source_url,as_of\n'
    st.download_button('빈 CSV 양식',example.encode('utf-8-sig'),'market_template.csv','text/csv')
    upload=st.file_uploader('지역 지표 CSV',type=['csv'],help='region, metric, value, unit, source_url, as_of 열이 필요합니다.')
    if st.button('지역 자료 검증 후 저장',disabled=not upload):
        try:
            rows=parse_market_csv(upload.getvalue()); store.save_market(rows)
            st.success(f'{len(rows)}행을 검증하고 저장했습니다.')
        except (ValueError,UnicodeError) as error: st.error(str(error))
    rows=store.get_market(region)
    if rows:
        st.dataframe(rows,use_container_width=True,hide_index=True)
        st.caption('입력한 지역명과 일치하는 사용자 제공 지표입니다. 서로 다른 기준일·단위의 수치를 합산하지 않습니다.')
        facts=' / '.join(f"{r['metric']} {r['value']:g}{r['unit']} (기준 {r['as_of']})" for r in rows[:5])
        st.download_button('지역 근거 자료 저장',json.dumps({'region':region,'provenance':'user_supplied_unverified','facts':rows},ensure_ascii=False,indent=2).encode(),'local_evidence.json','application/json')
        return rows,facts
    st.info('이 지역의 실제 자료가 아직 없습니다. 기본 상권 제안은 샘플 프로필입니다.')
    return [],''


def campaign_controls(form,current,ab_mode):
    st.markdown('#### 방문으로 이어지는 링크')
    base=st.text_input('외부 접속 기본 주소',value=public_base(),key='campaign_base_url')
    st.caption('현재 trycloudflare 임시 주소는 재시작하면 바뀝니다. 정식 배포·영상 QR에는 고정 HTTPS 주소를 쓰세요.')
    name=st.text_input('캠페인명',value=(form.get('store_name') or '우리 가게')+' 광고')
    expiry=st.date_input('안내·쿠폰 종료일',value=datetime.now(store.KST).date()+timedelta(days=7),min_value=datetime.now(store.KST).date())
    confirmed=st.checkbox('가게 정보·예약 링크·혜택 조건을 확인했습니다.')
    variants=st.session_state.get('studio_variants',[]) if ab_mode else [current]
    if st.button('캠페인·추적 링크 만들기',disabled=not confirmed):
        try:
            if not store.safe_url(base): raise ValueError('추적 링크를 만들 기본 주소를 입력해 주세요.')
            parsed=urlsplit(base)
            if parsed.path not in ('','/') or parsed.query or parsed.fragment: raise ValueError('기본 주소에는 https://도메인 형태만 입력하세요.')
            settings=dict(store_name=form.get('store_name',''),address=st.session_state.get('brand_address',''),
                booking_url=st.session_state.get('booking_url',''),map_url=st.session_state.get('map_url',''),
                offer=st.session_state.get('campaign_offer','').strip(),terms=st.session_state.get('campaign_terms',''),expires=expiry.isoformat())
            if not variants: raise ValueError('먼저 광고 문구를 작성해 주세요.')
            identity=store.create_campaign(name,settings,variants)
            st.session_state['active_campaign']=identity
            st.success('캠페인을 저장했습니다. 아래 링크를 게시글에 붙이거나 QR로 사용하세요.')
        except ValueError as error: st.error(str(error))
    campaign=store.get_campaign(st.session_state.get('active_campaign',''))
    links={}
    if campaign:
        for v in campaign['variants']:
            url=base.rstrip('/')+'/c/'+v['token']; links[v['label']]=url
            st.markdown(f"**{v['label']}안 · {v['code']}**")
            st.code(url,language=None)
            st.download_button(f"{v['label']}안 QR 저장",qr_png(url),f"campaign_{v['label']}_qr.png",'image/png',key='qr_'+v['id'])
        if any(v['copy']!=next((item for item in variants if item['label']==v['label']),{}) for v in campaign['variants']):
            st.warning('문구를 수정했습니다. 현재 광고와 연결할 캠페인을 새로 만든 뒤 QR을 사용하세요.')
            return campaign,{},base
    return campaign,links,base


def render_management(section):
    st.markdown('## '+section)
    if section=='브랜드 보관함':
        brands=store.list_brands()
        if not brands: st.info('광고 제작 → 브랜드에서 정보를 저장하세요.')
        for brand in brands:
            with st.expander(brand['name']):
                st.write({k:v for k,v in brand['data'].items() if k!='logo_b64'})
                st.caption('수정하려면 왼쪽에서 브랜드를 불러온 뒤 광고 제작으로 이동하세요.')
    elif section=='완성 영상':
        items=store.list_artifacts()
        if not items: st.info('새 최종본에서 제작한 영상이 여기에 저장됩니다.')
        for item in items:
            with st.expander(f"{item['created']} · {item['label']}"):
                st.video(item['path'])
                st.download_button('영상 다운로드',Path(item['path']).read_bytes(),Path(item['path']).name,'video/mp4',key='artifact_'+str(item['id']))
    else:
        campaigns=store.list_campaigns()
        if not campaigns: st.info('광고 제작 → 캠페인 탭에서 추적 링크를 만드세요.'); return
        lookup={c['id']:c for c in campaigns}
        identity=st.selectbox('캠페인',list(lookup),format_func=lambda key:lookup[key]['name'])
        campaign=store.get_campaign(identity)
        rows=store.campaign_stats(identity)
        st.dataframe(rows,hide_index=True,use_container_width=True)
        st.caption('views=안내 페이지 조회, booking_click=예약 링크 클릭, map_click=지도 클릭, coupon_claim=쿠폰 받기, redeemed=사장님 확인 사용. 브라우저·날짜·항목별 중복을 줄인 수치이며 실제 인원·예약·매출과 다릅니다.')
        if rows:
            st.bar_chart({r['variant']:{'예약 클릭':r['booking_click'],'쿠폰 받기':r['coupon_claim'],'사용 확인':r['redeemed']} for r in rows})
            total=sum(r['views'] for r in rows)
            st.caption('아직 반응이 없어 우열을 판단할 수 없습니다.' if total==0 else '표본·노출 조건이 다를 수 있으므로 이 수치만으로 광고 효과의 인과관계나 우승안을 단정하지 않습니다.')
        buf=io.StringIO(); writer=csv.DictWriter(buf,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        st.download_button('성과 CSV 저장',buf.getvalue().encode('utf-8-sig'),'campaign_results.csv','text/csv')
        st.text_input('다시 공유할 기본 주소',value=public_base(),key='stats_base_url')
        for v in campaign['variants']: st.code(st.session_state['stats_base_url'].rstrip('/')+'/c/'+v['token'],language=None)
        active=st.toggle('캠페인 활성',value=bool(campaign['active']),key='active_'+identity)
        if active!=bool(campaign['active']): store.set_campaign_active(identity,active); st.rerun()
        with st.form('redeem'):
            code=st.text_input('사용 확인할 쿠폰 코드')
            reference=st.text_input('거래·방문 식별번호',help='전화번호·이름 대신 본인이 관리하는 번호를 입력하세요. 원문은 저장하지 않습니다.')
            if st.form_submit_button('사장님 확인 후 사용 기록'):
                try:
                    added=store.redeem(code,reference)
                    if added: st.success('사용을 기록했습니다. 화면을 새로고침하면 집계에 반영됩니다.')
                    else: st.warning('같은 쿠폰·식별번호로 이미 기록했습니다.')
                except ValueError as error: st.error(str(error))
