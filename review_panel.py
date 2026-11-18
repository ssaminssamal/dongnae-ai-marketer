"""Optional research records, excluded from the production editor."""
import streamlit as st


def render_review(digest, export_json):
    st.header('제작 품질 기록')
    st.caption('기록은 현재 접속 세션에 보관됩니다. 새로고침·서버 재시작 전에 JSON을 내려받으세요. 실제 측정값과 사장님 답변만 기록하세요.')
    runs = st.session_state.get('runs', [])
    if runs:
        selected = st.selectbox('평가할 제작 결과', list(range(len(runs))), format_func=lambda i: f'{runs[i]["facts"]["store"]} · {runs[i]["condition"]} · {runs[i]["id"][:8]}')
        run = runs[selected]
        media = st.session_state.get('run_media', {}).get(run['id'])
        if media:
            with st.expander('평가할 영상과 원본 사진 보기'):
                st.video(media['video'])
                for i, photo in enumerate(media['photos']):
                    st.image(photo, caption=f'장면 {i+1} 원본', width=250)
        saved = st.session_state.get('evaluations', {}).get(run['id'], {})
        rows = saved.get('rows', [dict(scene=i+1, shape='미평가', color='미평가', text='미평가', note='') for i in range(run['scenes'])])
        st.caption('장면 전체를 원본과 비교하세요. 글자가 없는 원본은 글자 항목을 해당 없음으로 표시합니다.')
        with st.form('evaluation_' + run['id']):
            edited = st.data_editor(rows, hide_index=True, key='distortion_' + run['id'],
                disabled=['scene'], column_config={key: st.column_config.SelectboxColumn(label, options=['미평가', '정상', '왜곡', '해당 없음'], required=True)
                for key, label in [('shape', '모양'), ('color', '색'), ('text', '글자·로고')]})
            owner = st.text_input('평가한 사장님 식별명 (선택)', value=saved.get('owner', ''), key='owner_' + run['id'], help='이름 대신 가게명이나 익명 식별명을 사용해도 됩니다.')
            choices = ['미평가', '그대로 사용 가능', '수정 후 사용', '사용 어려움']
            usable = st.selectbox('그대로 사용할 수 있나요?', choices, index=choices.index(saved.get('usable', '미평가')), key='usable_' + run['id'])
            feedback = st.text_area('고쳐야 할 부분과 실제 답변', value=saved.get('feedback', ''), key='feedback_' + run['id'])
            if st.form_submit_button('평가 저장'):
                st.session_state.setdefault('evaluations', {})[run['id']] = dict(run_id=run['id'], rows=edited, owner=owner, usable=usable, feedback=feedback)
                st.success('평가를 저장했습니다.')
        evaluations = st.session_state.get('evaluations', {})
        summary = []
        for item in runs:
            evaluation = evaluations.get(item['id'])
            if not evaluation:
                continue
            values = [row[k] for row in evaluation['rows'] for k in ('shape', 'color', 'text')]
            measured = sum(v in ('정상', '왜곡') for v in values)
            distorted = values.count('왜곡')
            summary.append(dict(가게=item['facts']['store'], 조건=item['condition'], 사진묶음=digest(item['photos'])[:12],
                평가항목=measured, 미평가=values.count('미평가'), 왜곡항목=distorted,
                왜곡률=f'{100*distorted/measured:.1f}%' if measured else '미측정'))
        if summary:
            st.dataframe(summary, hide_index=True)
        st.caption('왜곡률 = 왜곡 항목 ÷ 평가 완료한 유효 항목 × 100. 미평가·해당 없음은 분모에서 제외합니다. 같은 사진묶음끼리 비교하세요.')
    if st.session_state.get('copy_history') or runs:
        st.download_button('전체 실험·문구 검증·사장님 평가 JSON 다운로드', export_json(dict(
            schema_version=1, runs=runs, copy_history=st.session_state.get('copy_history', []),
            evaluations=st.session_state.get('evaluations', {}))), 'experiment_records.json', 'application/json')
