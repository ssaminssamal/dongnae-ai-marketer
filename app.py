from __future__ import annotations
import streamlit as st
from config import APP_TITLE, APP_SUBTITLE, BUSINESS_TYPES, SUBJECT_TYPES, AREA_TYPES, AD_STYLES, GOALS, RUNWAY_MODELS
from market_engine import analyze_market, make_ad_copy
from prompt_engine import build_runway_prompt
from runway_service import api_key_configured, estimated_cost, generate_image_to_video, save_video
from report_utils import build_project_report

st.set_page_config(page_title=APP_TITLE, page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.block-container {max-width:1180px;padding-top:2rem;padding-bottom:4rem}
.hero{padding:1.4rem 1.5rem;border:1px solid rgba(128,128,128,.25);border-radius:18px;margin-bottom:1.2rem}
.hero h1{margin:0 0 .35rem 0}.muted{opacity:.72}
.result-card{border:1px solid rgba(128,128,128,.22);border-radius:14px;padding:1rem 1.1rem;min-height:150px}
.step{display:inline-block;padding:.25rem .65rem;border-radius:999px;border:1px solid rgba(128,128,128,.3);font-size:.85rem;margin-bottom:.5rem}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 생성 설정")
    model = st.selectbox("Runway 모델", list(RUNWAY_MODELS.keys()), format_func=lambda x: RUNWAY_MODELS[x]["label"], help="개발 중에는 Gen-4 Turbo, 최종 결과물은 Gen-4.5를 추천합니다.")
    duration = st.select_slider("영상 길이", options=[5, 10], value=5)
    cost = estimated_cost(model, duration)
    st.metric("예상 생성비", f"{cost['credits']} credits", f"약 ${cost['usd']:.2f}")
    st.divider(); st.subheader("API 상태")
    if api_key_configured():
        st.success("Runway API 키 감지됨"); st.caption("크레딧이 있으면 실제 생성 버튼이 동작합니다.")
    else:
        st.warning("Runway API 키 없음"); st.caption("결제 전에는 분석·카피·프롬프트까지 모두 테스트할 수 있습니다.")
    st.divider(); st.caption("상권 분석은 현재 공모전 데모용 샘플 프로필입니다. 실서비스 단계에서 공공 상권 데이터로 교체하는 구조입니다.")

st.markdown(f'<div class="hero"><h1>🎬 {APP_TITLE}</h1><div class="muted">{APP_SUBTITLE}</div><br/><b>사진 1장 → 상권 분석 → 광고 전략 → AI 영상 프롬프트 → Runway 광고영상</b></div>', unsafe_allow_html=True)

tab_create, tab_ready = st.tabs(["🚀 광고 만들기", "✅ 결제 전 점검"])
with tab_create:
    st.markdown('<span class="step">STEP 1</span>', unsafe_allow_html=True); st.subheader("사업과 홍보 대상을 입력하세요")
    c1,c2,c3=st.columns(3)
    with c1:
        store_name=st.text_input("가게 / 브랜드명", placeholder="예: 안서헤어"); business_type=st.selectbox("업종", BUSINESS_TYPES)
    with c2:
        subject_type=st.selectbox("홍보 대상", SUBJECT_TYPES); subject_name=st.text_input("홍보 대상 이름", placeholder="예: 레이어드컷 / 수제버거 / 영어회화")
    with c3:
        goal=st.selectbox("광고 목표", GOALS); style=st.selectbox("광고 콘셉트", AD_STYLES)
    description=st.text_area("간단한 설명", placeholder="예: 1:1 상담 후 얼굴형에 맞춰 디자인하는 레이어드컷", height=90)
    unique_point=st.text_input("강조하고 싶은 차별점 (선택)", placeholder="예: 예약제, 당일 제작, 10년 경력, 역에서 3분")

    st.markdown('<span class="step">STEP 2</span>', unsafe_allow_html=True); st.subheader("상권 정보를 선택하세요")
    a1,a2=st.columns(2)
    with a1: location_name=st.text_input("지역 / 상권명", placeholder="예: 천안 안서동")
    with a2: area_type=st.selectbox("상권 유형", AREA_TYPES)

    st.markdown('<span class="step">STEP 3</span>', unsafe_allow_html=True); st.subheader("대표 사진을 올려주세요")
    uploaded=st.file_uploader("제품·메뉴·서비스·매장·시술·포트폴리오 사진", type=["jpg","jpeg","png","webp"], help="Runway로 보낼 때 세로형 720×1280 이미지로 자동 정리합니다.")
    if uploaded: st.image(uploaded, caption="업로드 사진", width=360)

    can_plan=bool(subject_name.strip() and description.strip())
    if st.button("🧠 상권 분석 + 광고 기획 만들기", type="primary", use_container_width=True, disabled=not can_plan):
        analysis=analyze_market(area_type,business_type,goal,location_name)
        ad_copy=make_ad_copy(subject_name,description,analysis,style,goal,store_name)
        prompt=build_runway_prompt(business_type,subject_type,subject_name,description,style,goal,analysis,unique_point)
        st.session_state["analysis"]=analysis; st.session_state["ad_copy"]=ad_copy; st.session_state["runway_prompt"]=prompt
        st.session_state["form"]={"store_name":store_name,"business_type":business_type,"subject_type":subject_type,"subject_name":subject_name,"description":description,"goal":goal,"style":style,"location_name":location_name,"area_type":area_type,"unique_point":unique_point}

    if "analysis" in st.session_state:
        analysis=st.session_state["analysis"]; ad_copy=st.session_state["ad_copy"]
        st.divider(); st.markdown('<span class="step">STEP 4</span>', unsafe_allow_html=True); st.subheader("분석 결과와 광고 기획")
        r1,r2,r3=st.columns(3)
        with r1:
            st.markdown("**🎯 예상 핵심 고객**"); st.write(analysis["target"]); st.markdown("**⏰ 반응 시간대**"); st.write(analysis["peak"])
        with r2:
            st.markdown("**📍 상권 특성**"); [st.write("•",x) for x in analysis["traits"]]
        with r3:
            st.markdown("**💡 마케팅 키워드**"); st.write(" · ".join(analysis["keywords"])); st.markdown("**업종 강조점**"); st.write(" · ".join(analysis["business_points"]))
        st.info(analysis["disclaimer"])
        st.markdown("#### 광고 카피"); st.success(ad_copy["headline"]); st.write(ad_copy["body"]); st.write("**CTA:**", ad_copy["cta"])
        st.markdown("#### Runway 영상 연출 프롬프트")
        prompt_value=st.text_area("영상 생성 전에 직접 수정할 수 있습니다.", value=st.session_state["runway_prompt"], height=390, key="prompt_editor")
        report=build_project_report(st.session_state["form"],analysis,ad_copy,prompt_value,model,duration)
        st.download_button("📄 분석·프롬프트 JSON 저장", data=report.encode("utf-8"), file_name="ai_marketing_plan.json", mime="application/json")

        st.divider(); st.markdown('<span class="step">STEP 5</span>', unsafe_allow_html=True); st.subheader("Runway AI 광고영상 생성")
        cc1,cc2,cc3=st.columns(3); cc1.metric("모델",RUNWAY_MODELS[model]["label"].split(" · ")[0]); cc2.metric("영상 길이",f"{duration}초"); cc3.metric("예상 비용",f"{cost['credits']} credits / ${cost['usd']:.2f}")
        missing=[]
        if uploaded is None: missing.append("대표 사진")
        if not api_key_configured(): missing.append("Runway API 키")
        if missing: st.warning("실제 영상 생성 전 필요한 항목: "+", ".join(missing)+"\n\n결제 전에는 여기까지가 정상 동작 범위입니다.")
        if st.button("🎬 실제 Runway 영상 생성", type="primary", use_container_width=True, disabled=bool(missing)):
            with st.spinner("Runway가 영상을 생성 중입니다. 모델과 서버 상황에 따라 시간이 걸릴 수 있습니다..."):
                result=generate_image_to_video(uploaded.getvalue(),prompt_value,model,duration)
            if result.ok:
                local_path=save_video(result.video_bytes); st.success("광고영상 생성 완료!"); st.video(result.video_bytes)
                st.download_button("⬇️ MP4 다운로드", data=result.video_bytes, file_name="dongnae_ai_ad.mp4", mime="video/mp4", use_container_width=True)
                st.caption(f"로컬 저장 위치: {local_path}")
            else:
                st.error(result.message)
                if result.error_code=="CREDITS": st.info("코드는 정상 연결된 상태입니다. Runway Dev에서 크레딧을 충전한 뒤 다시 실행하면 됩니다.")

with tab_ready:
    st.subheader("결제 전 준비 상태")
    checks=[("Python 환경",True,"이 앱이 열렸다면 정상"),("Streamlit UI",True,"정상"),("상권 분석 모듈",True,"정상"),("광고 카피 생성",True,"정상"),("Runway 프롬프트 생성",True,"정상"),("사진 자동 세로형 변환",True,"실제 생성 시 자동 처리"),("Runway API 키",api_key_configured(),".env에서 자동 감지"),("Runway 크레딧",None,"실제 생성 요청 시 Runway가 확인")]
    for name,state,note in checks:
        icon="✅" if state is True else ("⬜" if state is False else "💳")
        st.write(f"{icon} **{name}** — {note}")
    st.markdown("""#### 결제 후 할 일은 2개뿐입니다
1. Runway Dev에서 크레딧을 충전합니다.
2. `.env`에 `RUNWAYML_API_SECRET=key_...`가 들어 있는지 확인하고 Streamlit을 재시작합니다.

그 다음 **광고 만들기 → 실제 Runway 영상 생성**을 누르면 됩니다.
""")
