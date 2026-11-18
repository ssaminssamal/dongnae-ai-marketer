from __future__ import annotations

import hashlib
import hmac
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st
from PIL import Image
from config import BUSINESS_TYPES, AD_STYLES, RUNWAY_MODELS
from copy_service import FIELDS, generate_copy, validate_copy
from secrets_config import setting
from scene_prompts import build_scene_prompt
from studio_ui import render_header, stage, render_empty_preview, load_styles
from runway_service import api_key_configured, estimated_cost, generate_image_to_video
from tts_service import VOICES, TTS_BACKEND, generate_tts, remove_tts_file
from video_merge import merge_video_bytes

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / 'outputs'
st.set_page_config(page_title='동네AI 마케터', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')
password = setting('DONGNAE_APP_PASSWORD')
if password and not st.session_state.get('_demo_authenticated'):
    st.title('동네AI 마케터')
    with st.form('demo_login'):
        entered = st.text_input('체험 비밀번호', type='password')
        submitted = st.form_submit_button('시작하기')
    if submitted:
        if hmac.compare_digest(entered.encode(), password.encode()):
            st.session_state['_demo_authenticated'] = True
            st.rerun()
        st.error('비밀번호를 확인해 주세요.')
    st.stop()


def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


def export_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')


def speech_bytes(text, options):
    identity = digest((text, options))
    cached = st.session_state.get('speech')
    if cached and cached['id'] == identity:
        return cached['bytes']
    path = None
    try:
        path = generate_tts(text, **options)
        data = Path(path).read_bytes()
        st.session_state['speech'] = {'id': identity, 'bytes': data}
        return data
    finally:
        if path:
            remove_tts_file(path)


load_styles(ROOT)
render_header()
with st.sidebar:
    st.subheader('제작 설정')
    duration = st.select_slider('장면 길이', [5, 10], value=5, format_func=lambda value: f'{value}초')
    st.caption('세로형 9:16 · MP4 · 한글 자막 지원')
    with st.expander('고급 설정'):
        model = st.selectbox('영상 모델', list(RUNWAY_MODELS),
            format_func=lambda key: '빠른 제작 · Gen-4 Turbo' if key == 'gen4_turbo' else '고품질 제작 · Gen-4.5')
        st.caption('영상 서비스: ' + ('설정됨' if api_key_configured() else '연결 설정 필요'))
        st.caption('문구 서비스: ' + ('설정됨' if setting('GEMINI_API_KEY') else '연결 설정 필요'))

editor, preview = st.columns([1.5, 1], gap='large')
with editor:
    stage('01', '우리 가게 소개', '광고에 담을 상품과 특징을 알려주세요.')
    a, b = st.columns(2)
    store = a.text_input('가게명')
    business = b.selectbox('업종', BUSINESS_TYPES)
    product = st.text_input('홍보할 상품·서비스')
    description = st.text_area('특징과 홍보 정보', help='확인된 사실만 입력하세요. 입력하지 않은 객관적 주장은 차단 대상입니다.')
    a, b = st.columns(2)
    price = a.text_input('가격 안내 (선택)', placeholder='예: 아메리카노 3,000원')
    discount = b.text_input('할인 안내 (선택)', placeholder='예: 학생증 제시 시 10% 할인')
    effect = st.text_input('효능·인증 안내 (선택)')
    style = st.selectbox('광고 분위기', AD_STYLES)
    facts = dict(store=store.strip(), business=business, product=product.strip(), description=description.strip(),
                 price=price.strip(), discount=discount.strip(), effect=effect.strip())
    context = dict(facts, style=style)
    facts_id = digest(context)
    ready_facts = bool(store.strip() and product.strip() and description.strip())

    stage('02', '사진 추가', '상품과 공간이 잘 보이는 사진을 1~3장 올려주세요.')
    files = st.file_uploader('업로드 순서가 장면 순서입니다', type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True) or []
    valid_photos = 1 <= len(files) <= 3
    photos = []
    if len(files) > 3:
        st.error('사진은 최대 3장입니다. 초과 사진을 삭제해 주세요.')
    for file in files[:3]:
        try:
            if file.size > 20 * 1024 * 1024:
                raise ValueError('사진 한 장은 20MB 이하로 올려 주세요.')
            with Image.open(io.BytesIO(file.getvalue())) as image:
                image.verify()
            photos.append({'name': file.name, 'bytes': file.getvalue(), 'sha256': hashlib.sha256(file.getvalue()).hexdigest()})
        except (OSError, ValueError, Image.DecompressionBombError):
            st.error('읽을 수 없거나 너무 큰 사진입니다. 다른 사진을 올려 주세요.')
            valid_photos = False
    if photos:
        for column, photo in zip(st.columns(len(photos)), photos):
            column.image(photo['bytes'], caption=photo['name'], width='stretch')

    stage('03', '광고 문구', 'AI가 제안한 문구를 확인하고 우리 가게에 맞게 다듬으세요.')
    st.caption('문구 생성: Google Gemini · 입력한 가게 정보가 Google로 전송됩니다.')
    if st.button('AI 광고 문구 생성', disabled=not ready_facts):
        try:
            with st.spinner('입력한 사실을 바탕으로 광고 문구를 생성합니다…'):
                generated = generate_copy(context)
            validation = validate_copy(generated, facts)
            st.session_state['copy_history'] = st.session_state.get('copy_history', []) + [
                dict(at=datetime.now(timezone.utc).isoformat(), input_id=facts_id, facts=facts, generated=generated, validation=validation)]
            st.session_state['copy_input_id'] = facts_id
            st.session_state['copy_generated'] = generated
            for field in FIELDS:
                st.session_state['copy_' + field] = generated[field]
        except RuntimeError as error:
            st.error(str(error))
    labels = dict(headline='첫 문장', detail='핵심 장점', cta='방문·문의 문구', brand='가게 문구', narration='내레이션')
    copy = {}
    for field in FIELDS:
        copy[field] = st.text_area(labels[field], key='copy_' + field, height=80, max_chars=500)
    validation = validate_copy(copy, facts)
    copy_current = st.session_state.get('copy_input_id') == facts_id
    copy_ready = copy_current and validation['passed'] and all(value.strip() for value in copy.values())
    if not copy_current:
        st.info('가게 정보를 입력한 후 AI 문구를 생성하세요. 입력이 바뀌면 다시 생성해야 합니다.')
    elif not validation['passed']:
        st.error('확인되지 않은 주장 때문에 제작을 차단했습니다. 해당 문장을 삭제하거나 실제 입력 문장 그대로 수정하세요.')
        st.dataframe(validation['issues'], hide_index=True)
    else:
        st.success('입력한 정보와 문구가 일치합니다. 제작을 진행할 수 있어요.')
    st.caption('가격·할인·효능은 입력한 문장 그대로 사용해 주세요. 게시 전 최종 문구를 확인해 주세요.')

    condition = 'product_preservation'
    base_prompt = build_scene_prompt(context, improved=True)
    prompts = []
    if photos:
        with st.expander('장면 연출 자세히 설정'):
            st.caption('원본 상품의 모양·색·글자를 보존하고 움직임을 최소화하는 연출이 기본 적용됩니다.')
            for i, photo in enumerate(photos):
                prompts.append(st.text_area(f'장면 {i+1} · 연출 프롬프트', value=base_prompt,
                    key=f'prompt_{photo["sha256"]}_{i}_{digest(base_prompt)}', max_chars=950))

    stage('04', '광고 완성', '자막과 목소리를 더해 한 편의 영상으로 만드세요.')
    use_captions = st.checkbox('한글 자막 넣기', value=True)
    use_tts = st.checkbox('내레이션 넣기', value=True)
    voice = st.selectbox('목소리', list(VOICES), format_func=VOICES.get, disabled=not use_tts)
    options = dict(voice_id=voice, speed=1.0, quality=8)
    st.caption('음성: ' + ('로컬 Supertonic' if TTS_BACKEND == 'local' else '온라인 Google TTS (문구가 음성 서비스로 전송됩니다)'))
    if st.button('내레이션 미리 듣기', disabled=not (use_tts and copy_ready)):
        try:
            with st.spinner('음성을 생성합니다…'):
                st.audio(speech_bytes(copy['narration'].strip(), options))
        except RuntimeError as error:
            st.error(str(error))
    signature = digest((model, duration, condition, prompts, [p['sha256'] for p in photos]))
    cached = st.session_state.get('scenes', {})
    same_scenes = cached.get('signature') == signature
    scene_count = len(cached.get('videos', [])) if same_scenes else 0
    st.caption(f'새 장면 예상 생성비: ${estimated_cost(model, duration)["usd"] * max(0, len(photos)-scene_count):.2f} · 문구 API 비용 별도')
    blocked = not (ready_facts and valid_photos and copy_ready and prompts and all(p.strip() for p in prompts))
    if not api_key_configured() and scene_count < len(photos):
        st.info('영상 생성을 위해 RUNWAYML_API_SECRET을 설정해 주세요.')
        blocked = True
    render_id = digest((facts_id, signature, copy, use_captions, use_tts, options))
    if st.button('광고 영상 만들기', type='primary', disabled=blocked):
        try:
            # Recheck immediately before any paid request; edited narration is included.
            if not validate_copy(copy, facts)['passed']:
                raise RuntimeError('광고 문구 검증을 통과하지 못했습니다.')
            progress = st.progress(0, text='음성을 준비합니다…')
            audio = speech_bytes(copy['narration'].strip(), options) if use_tts else None
            scenes = list(cached['videos']) if same_scenes else []
            for i, photo in enumerate(photos):
                if i < len(scenes):
                    continue
                progress.progress(10 + int(60*i/len(photos)), text=f'장면 {i+1}/{len(photos)} 생성 중…')
                pending = st.session_state.setdefault('pending_tasks', {})
                task_key = digest((signature, i))
                result = generate_image_to_video(image_bytes=photo['bytes'], prompt=prompts[i], model=model, duration=duration,
                    task_state=pending.setdefault(task_key, {}))
                if not result.ok:
                    raise RuntimeError(f'장면 {i+1}: {result.message}')
                scenes.append(result.video_bytes)
                st.session_state['scenes'] = dict(signature=signature, videos=list(scenes))
            progress.progress(80, text='장면·자막·음성을 합칩니다…')
            data, path = merge_video_bytes(scenes, output_dir=str(OUTPUTS),
                final_captions=[copy[k] for k in FIELDS if k != 'narration'] if use_captions else None,
                narration_audio=audio)
            record = dict(id=uuid4().hex, at=datetime.now(timezone.utc).isoformat(), condition=condition,
                facts=facts, photos=[{k: p[k] for k in ('name', 'sha256')} for p in photos], prompts=prompts,
                model=model, duration=duration, original_copy=st.session_state['copy_generated'],
                final_copy=copy, validation=validation, scenes=len(scenes), output=Path(path).name)
            st.session_state['runs'] = st.session_state.get('runs', []) + [record]
            st.session_state.setdefault('run_media', {})[record['id']] = dict(video=data, photos=[p['bytes'] for p in photos])
            st.session_state['completed'] = dict(bytes=data, render_id=render_id, record=record)
            progress.progress(100, text='완성되었습니다.')
            st.rerun()
        except RuntimeError as error:
            st.error(str(error))
        except Exception:
            st.error('제작에 실패했습니다. 연결·영상 크레딧·한글 폰트·음성 설정을 확인해 주세요. 완성된 장면은 같은 설정으로 재시도할 때 재사용합니다.')

with preview:
    st.subheader('미리보기')
    completed = st.session_state.get('completed')
    if completed:
        if completed['render_id'] != render_id:
            st.warning('아래 영상은 이전 설정의 결과입니다. 현재 설정을 반영하려면 다시 제작하세요.')
        st.video(completed['bytes'])
        st.download_button('최종 MP4 다운로드', completed['bytes'], completed['record']['output'], 'video/mp4')
        if setting('DONGNAE_REVIEW_MODE') == '1':
            st.download_button('제작 기록 저장', export_json(completed['record']), 'ad_record.json', 'application/json')
    else:
        if photos:
            st.image(photos[0]['bytes'], caption='첫 장면 · 원본 사진', width='stretch')
        else:
            render_empty_preview()
    st.caption('완성된 영상은 이곳에서 확인하고 내려받을 수 있습니다.')
    a, b = st.columns(2)
    a.metric('장면', f'{len(photos)}개')
    b.metric('기본 길이', f'{len(photos)*duration}초')

if setting('DONGNAE_REVIEW_MODE') == '1':
    from review_panel import render_review
    render_review(digest, export_json)
