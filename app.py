from __future__ import annotations

import hashlib
import base64
import json
import io
import html
import os
from pathlib import Path
import sys
if (Path(__file__).resolve().parent/'.vendor').exists():
    sys.path.insert(0,str(Path(__file__).resolve().parent/'.vendor'))

import streamlit as st
from config import BUSINESS_TYPES, SUBJECT_TYPES, AREA_TYPES, AD_STYLES, GOALS, RUNWAY_MODELS
from market_engine import analyze_market, make_ad_copy
from prompt_engine import build_runway_prompt
from runway_service import api_key_configured, estimated_cost, generate_image_to_video, save_video
from tts_service import VOICES, TTS_BACKEND, generate_tts, remove_tts_file
from video_merge import merge_video_bytes
from report_utils import build_project_report
from music_catalog import TRACKS, ensure_tracks
import studio_store as store_db
from studio_extensions import (sidebar_library, render_management, brand_controls, situation_controls,
    variant_selector, update_variant, market_controls, campaign_controls, qr_png)

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / 'outputs'
st.set_page_config(page_title='동네AI — 광고 스튜디오', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')
if os.getenv('DONGNAE_APP_PASSWORD') and not st.session_state.get('_demo_authenticated'):
    import hmac
    st.title('동네AI 마케터')
    with st.form('demo_login'):
        password = st.text_input('체험 비밀번호', type='password')
        submitted = st.form_submit_button('시작하기')
    if submitted:
        if hmac.compare_digest(password.encode('utf-8'), os.environ['DONGNAE_APP_PASSWORD'].encode('utf-8')):
            st.session_state['_demo_authenticated'] = True
            st.rerun()
        st.error('비밀번호를 확인해 주세요.')
    st.stop()
st.markdown((ROOT / 'studio.css').read_text(encoding='utf-8'), unsafe_allow_html=True)


def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


def speech_bytes(text, options):
    identity = digest((text, options))
    cached = st.session_state.get('studio_speech')
    if cached and cached['id'] == identity:
        return cached['bytes']
    path = None
    try:
        path = generate_tts(text, **options)
        data = Path(path).read_bytes()
        st.session_state['studio_speech'] = {'id': identity, 'bytes': data}
        return data
    finally:
        if path:
            remove_tts_file(path)


with st.sidebar:
    st.markdown('<div class="side-brand"><span>◈</span> 동네AI<small>CREATIVE STUDIO</small></div>', unsafe_allow_html=True)
    section = sidebar_library()
    st.markdown('<div class="side-label">EXPORT SETTINGS</div>', unsafe_allow_html=True)
    model = st.selectbox('영상 모델', list(RUNWAY_MODELS), format_func=lambda m: m.replace('_', ' ').title())
    duration = st.select_slider('장면 길이', [5, 10], value=5, format_func=lambda n: f'{n}초')
    st.caption('9:16 세로 영상 · MP4 · 24 fps')
    st.divider()
    st.caption('내레이션 · 무료 음성')
    with st.expander('영상 서비스 연결'):
        st.caption('Runway · ' + ('키 설정됨' if api_key_configured() else '키 미설정'))
        st.caption('음성 생성에는 가입이나 API 키가 필요하지 않습니다.')
    st.markdown('<div class="side-foot">작은 가게의 이야기를,<br>기억에 남는 광고로.</div>', unsafe_allow_html=True)

if section != '광고 제작':
    render_management(section)
    st.stop()

st.markdown('<div class="topbar"><span>WORKSPACE <b>/ 광고 스튜디오</b></span><span class="top-chip">VERTICAL FILM &nbsp; 9:16</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-title"><p>LOCAL STORIES, WELL TOLD.</p><h1>우리 가게의 다음 장면.</h1><div>사진에 움직임을, 이야기에 목소리를 더하세요.</div></div>', unsafe_allow_html=True)

editor, preview_panel = st.columns([1.55, 1], gap='large')
with editor:
    st.markdown('<div class="panel-heading"><h2>광고 편집</h2><span>CREATIVE DESK</span></div>', unsafe_allow_html=True)
    brand_tab, situation_tab, scene_tab, speech_tab, music_tab, market_tab, campaign_tab = st.tabs(['브랜드', '오늘의 상황', '장면', '카피 · 음성', '배경음악', '지역 근거', '캠페인'])
    with brand_tab:
        st.markdown('#### 어떤 이야기를 전할까요?')
        a, b = st.columns(2)
        store = a.text_input('브랜드명', placeholder='예: 현모헤어', key='brand_name')
        subject = b.text_input('홍보할 제품·서비스', placeholder='예: 시그니처 레이어드컷', key='subject_name')
        description = st.text_area('소개', placeholder='고객에게 전하고 싶은 제품이나 서비스의 특징', height=110, key='brand_description')
        unique = st.text_input('가장 자신 있는 한 가지', placeholder='예: 30년 경력의 1:1 맞춤 상담', key='brand_unique')
        a, b = st.columns(2)
        business = a.selectbox('업종', BUSINESS_TYPES,key='business_choice')
        subject_type = b.selectbox('홍보 대상', SUBJECT_TYPES,key='subject_choice')
        a, b = st.columns(2)
        location = a.text_input('지역', placeholder='예: 천안 안서동',key='location_name')
        area = b.selectbox('상권 유형', AREA_TYPES,key='area_choice')
        a, b = st.columns(2)
        style = a.selectbox('광고 분위기', AD_STYLES, index=3,key='style_choice')
        goal = b.selectbox('광고 목표', GOALS,key='goal_choice')
        brand_controls()

    analysis = analyze_market(area_type=area, business_type=business, goal=goal, location_name=location)
    form = dict(store_name=store, subject_name=subject, description=description, unique_point=unique,
                business_type=business, subject_type=subject_type, location_name=location,
                area_type=area, style=style, goal=goal)
    form['local_evidence'] = store_db.get_market(location)
    form['price'] = st.session_state.get('product_price',0)
    form['menu'] = st.session_state.get('brand_menu','')
    analysis['local_evidence'] = form['local_evidence']
    with situation_tab:
        situation_controls(form)
    with market_tab:
        local_rows, local_summary = market_controls(location)

    base_prompt = build_runway_prompt(business_type=business, subject_type=subject_type,
    subject_name=subject, description=description, style=style, goal=goal, analysis=analysis, unique_point=unique)
    base_prompt = base_prompt[:600] + ('\nUser-provided local evidence: '+local_summary[:180] if local_summary else '') + '\nNo generated text, subtitles, captions, logos or watermarks. Preserve the original subject. One realistic continuous shot.'

    with scene_tab:
        source = st.radio('장면 소스', ['사진으로 생성', '저장된 영상'], horizontal=True, label_visibility='collapsed',key='scene_source')
        uploads = []
        selected_paths = []
        prompts = []
        if source == '사진으로 생성':
            uploads = st.file_uploader('브랜드 사진', type=['jpg','jpeg','png','webp'], accept_multiple_files=True,
                                       help='최대 3장. 업로드 순서대로 영상이 연결됩니다.') or []
            if uploads:
                st.session_state['_scene_photos']=[(f.name,f.getvalue()) for f in uploads[:3]]
            elif st.session_state.get('_scene_photos') and st.checkbox('이전에 추가한 사진 재사용',value=True):
                for name,data in st.session_state['_scene_photos']:
                    file=io.BytesIO(data); file.name=name; uploads.append(file)
            if len(uploads) > 3:
                st.warning('한 편에 사진 3장까지 사용할 수 있습니다.')
                uploads = uploads[:3]
            for i, file in enumerate(uploads):
                identity = digest(file.getvalue())[:12]
                with st.container(border=True):
                    thumb, details = st.columns([1, 2])
                    thumb.image(file.getvalue(), use_container_width=True)
                    details.markdown(f'**SCENE {i+1:02d}**')
                    details.caption(file.name)
                    details.caption(f'{duration}초 · 9:16')
                    with st.expander('장면 연출 편집'):
                        prompts.append(st.text_area('영상 프롬프트', value=base_prompt[:950],
                            key=f'direction_{i}_{identity}_{digest(base_prompt)[:8]}', height=180, max_chars=1000))
            if not uploads:
                st.caption('제품, 공간, 서비스 사진을 추가하세요.')
        else:
            paths = sorted(OUTPUTS.glob('ad_*.mp4'), key=lambda p: p.stat().st_mtime, reverse=True)
            options=[p.name for p in paths]
            if 'saved_scene_names' in st.session_state:
                st.session_state['saved_scene_names']=[name for name in st.session_state['saved_scene_names'] if name in options]
            selected_names = st.multiselect('연결할 영상 · 선택한 순서대로 배치', options, max_selections=6,key='saved_scene_names')
            selected_paths = [OUTPUTS / name for name in selected_names]
            for i, path in enumerate(selected_paths):
                with st.expander(f'장면 {i+1:02d} · {path.name}'):
                    st.video(str(path))
            if not paths:
                st.caption('아직 저장된 개별 장면이 없습니다.')

    with speech_tab:
        variant_selector()
        if st.button('광고 카피 제안받기', disabled=not (subject.strip() and description.strip()), use_container_width=True):
            copy = make_ad_copy(subject_name=subject, description=description, analysis=analysis,
                                style=style, goal=goal, store_name=store)
            st.session_state.update(ad_headline=copy['headline'], ad_detail=unique or description,
                ad_cta=copy['cta'], ad_brand=' · '.join(s for s in [store,location] if s),
                ad_narration=f"{subject}. {unique or description}. {copy['cta']}")
        use_captions = st.toggle('자막', value=True, key='captions_enabled')
        caption_1 = st.text_input('첫 문장', key='ad_headline', placeholder='시선을 붙잡는 한 문장', disabled=not use_captions)
        caption_2 = st.text_input('핵심 장점', key='ad_detail', placeholder='우리 가게만의 차별점', disabled=not use_captions)
        caption_3 = st.text_input('방문·예약 문구', key='ad_cta', placeholder='지금 예약하세요', disabled=not use_captions)
        caption_4 = st.text_input('마지막 브랜드 문구', key='ad_brand', placeholder='가게 이름 · 지역', disabled=not use_captions)
        st.divider()
        use_tts = st.toggle('AI 내레이션', value=True, key='voice_enabled')
        voice_source = st.radio('내레이션 방식', ['무료 AI 음성', '음성 파일 업로드'], horizontal=True, disabled=not use_tts,key='voice_source_choice')
        uploaded_audio = None
        if voice_source == '무료 AI 음성':
            service_label = 'SUPERTONIC · LOCAL · FREE' if TTS_BACKEND == 'local' else 'GOOGLE TTS · ONLINE · FREE'
            st.markdown(f'<span class="service-label">{service_label}</span>', unsafe_allow_html=True)
            voice_id = st.selectbox('목소리', list(VOICES), format_func=VOICES.get, disabled=not use_tts,key='voice_choice')
            speed = st.slider('말하기 속도', .7, 1.5, 1.0, .05, disabled=not use_tts or TTS_BACKEND=='gtts',key='voice_speed')
            quality = st.selectbox('음성 품질', [8,12], format_func=lambda n: '표준' if n==8 else '정밀', disabled=not use_tts or TTS_BACKEND=='gtts',key='voice_quality')
            if TTS_BACKEND == 'gtts':
                st.caption('기본 한국어 음성을 사용합니다. 내레이션 문구는 Google 음성 서비스로 전송됩니다.')
            narration = st.text_area('내레이션', key='ad_narration', height=130, max_chars=3000,
                                     placeholder='광고에 담을 목소리를 작성하세요.', disabled=not use_tts)
            tts_options = dict(voice_id=voice_id, speed=speed, quality=quality)
            ready_speech = bool(narration.strip())
            if st.button('내레이션 미리 듣기', disabled=not use_tts or not ready_speech, use_container_width=True):
                try:
                    with st.spinner('목소리를 만들고 있습니다…'):
                        speech_bytes(narration.strip(), tts_options)
                except Exception as error:
                    st.error(str(error))
            cached_speech = st.session_state.get('studio_speech')
            if use_tts and cached_speech and cached_speech['id'] == digest((narration.strip(), tts_options)):
                st.audio(cached_speech['bytes'], format='audio/wav' if TTS_BACKEND == 'local' else 'audio/mpeg')
            st.caption('무료 · API 키 불필요 · 캡컷 애덤과는 다른 목소리입니다.')
        else:
            uploaded_audio = st.file_uploader('내레이션 오디오', type=['mp3','wav','m4a'], disabled=not use_tts,
                help='캡컷 등에서 만든 음성을 그대로 사용할 수 있습니다. 최대 20MB.')
            narration,tts_options = '',{}
            ready_speech = bool(uploaded_audio and uploaded_audio.size<=20*1024*1024)
            if uploaded_audio:
                if ready_speech:
                    st.audio(uploaded_audio.getvalue())
                else:
                    st.error('음성 파일은 20MB 이하로 올려 주세요.')
        current_variant = update_variant(caption_1,caption_2,caption_3,caption_4,narration)
        wants_ab = st.checkbox('같은 장면으로 A/B 두 편 함께 제작',value=False,
            disabled=not bool(st.session_state.get('studio_variants')) or (use_tts and voice_source=='음성 파일 업로드'),key='ab_enabled')
        ab_mode = wants_ab and bool(st.session_state.get('studio_variants')) and not (use_tts and voice_source=='음성 파일 업로드')
        if ab_mode:
            st.caption('장면 생성 비용은 한 번만 사용합니다. A/B는 첫 문장·자막·무료 음성을 다르게 만듭니다.')
            st.dataframe(st.session_state['studio_variants'],hide_index=True,use_container_width=True)

        with st.expander('광고 전략'):
            st.write('핵심 고객', analysis['target'])
            st.write('마케팅 키워드', ' · '.join(analysis['keywords']))
            st.caption('상권 유형별 샘플 프로필 기반 제안이며, 실제 매출·유동인구 분석은 아닙니다.')
            ad_copy = dict(headline=caption_1, body=caption_2, cta=caption_3)
            report = build_project_report(form, analysis, ad_copy, '\n\n'.join(prompts), model, duration)
            st.download_button('기획안 저장', report.encode('utf-8'), 'marketing_plan.json', 'application/json')

    with music_tab:
        st.markdown('#### 광고의 분위기를 더하세요')
        selected_music = st.selectbox('무료 배경음악', ['none', *TRACKS],
            format_func=lambda key: '음악 없음' if key == 'none' else TRACKS[key],key='bgm_choice')
        music_volume = st.slider('배경음악 음량', 0, 60, 18, format='%d%%', disabled=selected_music=='none',key='bgm_volume')
        duck_music = st.toggle('내레이션이 나올 때 음악 자동으로 낮추기', value=True, disabled=selected_music=='none')
        bgm_audio = None
        if selected_music != 'none':
            music_path = ensure_tracks()[selected_music]
            bgm_audio = music_path.read_bytes()
            st.audio(bgm_audio,format='audio/wav')
            st.caption('미리 듣기는 원본 음량입니다. 완성 영상에는 위 음량과 자동 조절이 적용됩니다.')
        st.caption('동네AI용으로 직접 합성한 기본 음악입니다. 광고에 무료로 사용할 수 있습니다.')
        st.caption('음악은 영상 길이에 맞춰 반복되며 끝에서 자연스럽게 작아집니다. 음악을 선택하면 원본 장면 소리는 제외됩니다.')

    with campaign_tab:
        campaign, tracking_links, tracking_base = campaign_controls(form,current_variant,ab_mode)
        use_qr = st.checkbox('영상 마지막 3초에 해당 광고 QR 표시',disabled=not bool(tracking_links),key='qr_enabled')
        if use_qr and tracking_links:
            st.caption('임시 주소가 바뀌면 이미 영상에 넣은 QR도 바뀌지 않습니다. 정식 게시 전 고정 주소를 사용하세요.')
    render_variants = st.session_state['studio_variants'] if ab_mode else [current_variant]

    # Speech generation happens before expensive video generation, so a voice error cannot waste scene credits.
    count = len(uploads) if source == '사진으로 생성' else len(selected_paths)
    signature = digest((source, model, duration, prompts,
        [digest(f.getvalue()) for f in uploads], [(p.name,p.stat().st_mtime_ns) for p in selected_paths]))
    cached = st.session_state.get('studio_scenes')
    same_scenes = bool(cached and cached['signature'] == signature)
    complete_cache = bool(same_scenes and len(cached['videos']) == count)
    cost = estimated_cost(model, duration)
    missing = []
    if not count:
        missing.append('장면을 추가해 주세요.')
    if source == '사진으로 생성' and not complete_cache and not api_key_configured():
        missing.append('영상 생성을 위해 Runway API 키를 설정해 주세요.')
    if use_tts and not ready_speech:
        missing.append('내레이션 문구 또는 음성 파일을 추가해 주세요.')
    if source == '사진으로 생성' and any(not p.strip() for p in prompts):
        missing.append('빈 장면 연출을 작성해 주세요.')

with preview_panel:
    with st.container(key='preview'):
        st.markdown('<div class="panel-heading"><h2>미리보기</h2><span>YOUR NEXT AD</span></div>', unsafe_allow_html=True)
        completed = st.session_state.get('studio_completed') or st.session_state.get('completed_ad')
        if completed:
            st.video(completed['bytes'])
            st.caption('마지막으로 완성한 영상 · 설정 변경 후 다시 제작하면 반영됩니다.')
            st.download_button('MP4 다운로드 ↓', completed['bytes'], 'dongnae_ad.mp4', 'video/mp4', use_container_width=True)
            alternatives=st.session_state.get('completed_variants',[])
            if len(alternatives)>1:
                for item in alternatives:
                    with st.expander(f"{item['label']}안 보기·다운로드"):
                        st.video(item['bytes'])
                        st.download_button(f"{item['label']}안 MP4",item['bytes'],f"dongnae_{item['label']}.mp4",'video/mp4',key='variant_download_'+item['label'])
        elif uploads:
            st.image(uploads[0].getvalue(), use_container_width=True)
            st.caption('첫 장면 · 원본 사진')
        elif selected_paths:
            st.video(str(selected_paths[0]))
            st.caption('첫 장면 · 원본 영상')
        else:
            title = html.escape(store or '동네의 발견')
            st.markdown(f'''<div class="film-placeholder"><div class="film-grain"></div>
                <div class="film-top">DONGNAE ORIGINAL <span>9:16</span></div>
                <div class="film-art"><i></i><i></i><i></i></div>
                <div class="film-copy"><small>EVERY LOCAL HAS A STORY.</small><h2>{title}</h2>
                <p>당신의 이야기가<br>시작되는 곳.</p></div><div class="film-bottom">AD PREVIEW <span>◈</span></div></div>''', unsafe_allow_html=True)
        a,b,c = st.columns(3)
        a.metric('장면', f'{count:02d}')
        b.metric('영상 길이', f'{count*duration}초' if source == '사진으로 생성' else '원본 기준')
        new_count = max(0, count - (len(cached['videos']) if same_scenes else 0)) if source == '사진으로 생성' else 0
        c.metric('영상 생성비', f"${cost['usd'] * new_count:.2f}")
        st.caption('TTS 무료 · 영상 생성만 과금 · 내레이션이 길면 마지막 화면이 연장됩니다.')
        for message in missing:
            st.caption(message)
        label = '광고 완성하기' if source == '저장된 영상' else ('변경 내용으로 다시 편집' if complete_cache else '광고 영상 만들기')
        if st.button(label + ' ↗', type='primary', disabled=bool(missing), use_container_width=True):
            try:
                progress = st.progress(0, text='제작을 준비합니다…')
                voice_results = {}
                if use_tts:
                    for variant in render_variants:
                        progress.progress(5,text=f"{variant['label']}안 내레이션을 준비합니다…")
                        voice_results[variant['label']] = uploaded_audio.getvalue() if voice_source == '음성 파일 업로드' else speech_bytes(variant['narration'].strip(),tts_options)
                if source == '저장된 영상':
                    scenes = [p.read_bytes() for p in selected_paths]
                else:
                    scenes = list(cached['videos']) if same_scenes else []
                    for i,file in enumerate(uploads):
                        if i < len(scenes):
                            continue
                        progress.progress(10 + int(i/count*60), text=f'장면 {i+1}/{count} 제작 중…')
                        result = generate_image_to_video(image_bytes=file.getvalue(), prompt=prompts[i].strip(), model=model, duration=duration)
                        if not result.ok:
                            raise RuntimeError(f'장면 {i+1}: {result.message}')
                        scenes.append(result.video_bytes)
                        st.session_state['studio_scenes'] = dict(signature=signature, videos=list(scenes))
                        save_video(result.video_bytes, directory=str(OUTPUTS))
                completed_variants=[]
                for number,variant in enumerate(render_variants):
                    progress.progress(80+int(number/len(render_variants)*15),text=f"{variant['label']}안 장면·자막·음악을 연결합니다…")
                    label=variant['label']
                    data,path = merge_video_bytes(scenes, output_dir=str(OUTPUTS),
                        final_captions=[variant['headline'],variant['detail'],variant['cta'],variant['brand']] if use_captions else None,
                        narration_audio=voice_results.get(label),bgm_audio=bgm_audio,bgm_volume=music_volume/100,duck_music=duck_music,
                        brand_logo=base64.b64decode(st.session_state['logo_b64']) if st.session_state.get('logo_b64') else None,
                        brand_color=st.session_state.get('brand_color'),
                        campaign_qr=qr_png(tracking_links[label]) if use_qr and label in tracking_links else None)
                    result=dict(bytes=data,path=path,label=label)
                    completed_variants.append(result)
                    st.session_state['studio_completed']=result
                    store_db.record_artifact(campaign['id'] if campaign else None,label,path)
                st.session_state['completed_variants']=completed_variants
                progress.progress(100,text='광고가 완성되었습니다.')
                st.rerun()
            except Exception as error:
                st.error(str(error))

st.markdown('<div class="page-footer"><b>동네AI</b><span>Made for the places we love.</span><span>ADVERTISING STUDIO</span></div>', unsafe_allow_html=True)
