from __future__ import annotations

import streamlit as st

from config import (
    APP_TITLE,
    APP_SUBTITLE,
    BUSINESS_TYPES,
    SUBJECT_TYPES,
    AREA_TYPES,
    AD_STYLES,
    GOALS,
    RUNWAY_MODELS,
)

from market_engine import (
    analyze_market,
    make_ad_copy,
)

from prompt_engine import (
    build_runway_prompt,
)

from runway_service import (
    api_key_configured,
    estimated_cost,
    generate_image_to_video,
    save_video,
)

from report_utils import (
    build_project_report,
)

from video_merge import (
    merge_video_bytes,
)


# =========================================================
# Streamlit 기본 설정
# =========================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .hero {
        padding: 1.4rem 1.5rem;
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 18px;
        margin-bottom: 1.2rem;
    }

    .hero h1 {
        margin: 0 0 .35rem 0;
    }

    .muted {
        opacity: .72;
    }

    .result-card {
        border: 1px solid rgba(128,128,128,.22);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        min-height: 150px;
    }

    .step {
        display: inline-block;
        padding: .25rem .65rem;
        border-radius: 999px;
        border: 1px solid rgba(128,128,128,.3);
        font-size: .85rem;
        margin-bottom: .5rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:

    st.header("⚙️ 생성 설정")

    model = st.selectbox(
        "Runway 모델",
        options=list(RUNWAY_MODELS.keys()),
        format_func=lambda x: RUNWAY_MODELS[x]["label"],
    )

    duration = st.select_slider(
        "영상 길이",
        options=[5, 10],
        value=5,
    )

    cost = estimated_cost(
        model,
        duration,
    )

    st.metric(
        "예상 생성비(장면 1개)",
        f"{cost['credits']} credits",
        f"약 ${cost['usd']:.2f}",
    )

    st.divider()

    st.subheader("API 상태")

    if api_key_configured():

        st.success(
            "Runway API 키 감지됨"
        )

        st.caption(
            "크레딧이 있으면 실제 영상 생성이 가능합니다."
        )

    else:

        st.warning(
            "Runway API 키 없음"
        )

        st.caption(
            "분석과 프롬프트 생성까지만 사용할 수 있습니다."
        )

    st.divider()

    st.caption(
        "현재 상권 분석은 공모전 데모용 샘플 프로필입니다. "
        "향후 실제 공공 상권 데이터로 교체할 수 있습니다."
    )


# =========================================================
# Hero
# =========================================================

st.markdown(
    f"""
    <div class="hero">

        <h1>🎬 {APP_TITLE}</h1>

        <div class="muted">
            {APP_SUBTITLE}
        </div>

        <br/>

        <b>
        사진 여러 장
        → 상권 분석
        → 광고 전략
        → AI 영상
        → 자막
        → TTS
        → 최종 광고영상
        </b>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Tabs
# =========================================================

tab_create, tab_ready = st.tabs(
    [
        "🚀 광고 만들기",
        "✅ 시스템 점검",
    ]
)


# =========================================================
# 광고 만들기 TAB
# =========================================================

with tab_create:

    # =====================================================
    # STEP 1
    # =====================================================

    st.markdown(
        '<span class="step">STEP 1</span>',
        unsafe_allow_html=True,
    )

    st.subheader(
        "사업과 홍보 대상을 입력하세요"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        store_name = st.text_input(
            "가게 / 브랜드명",
            placeholder="예: 현모헤어",
        )

        business_type = st.selectbox(
            "업종",
            BUSINESS_TYPES,
        )

    with c2:

        subject_type = st.selectbox(
            "홍보 대상",
            SUBJECT_TYPES,
        )

        subject_name = st.text_input(
            "홍보 대상 이름",
            placeholder="예: 레이어드컷",
        )

    with c3:

        goal = st.selectbox(
            "광고 목표",
            GOALS,
        )

        style = st.selectbox(
            "광고 콘셉트",
            AD_STYLES,
        )

    description = st.text_area(
        "간단한 설명",
        placeholder=(
            "예: 1:1 상담 후 얼굴형에 맞는 "
            "헤어스타일링"
        ),
        height=90,
    )

    unique_point = st.text_input(
        "강조하고 싶은 차별점",
        placeholder=(
            "예: 30년 경력, "
            "뛰어난 두피마사지"
        ),
    )


    # =====================================================
    # STEP 2
    # =====================================================

    st.markdown(
        '<span class="step">STEP 2</span>',
        unsafe_allow_html=True,
    )

    st.subheader(
        "상권 정보를 선택하세요"
    )

    a1, a2 = st.columns(2)

    with a1:

        location_name = st.text_input(
            "지역 / 상권명",
            placeholder="예: 천안 안서동",
        )

    with a2:

        area_type = st.selectbox(
            "상권 유형",
            AREA_TYPES,
        )


    # =====================================================
    # STEP 3
    # =====================================================

    st.markdown(
        '<span class="step">STEP 3</span>',
        unsafe_allow_html=True,
    )

    st.subheader(
        "대표 사진을 올려주세요"
    )

    uploaded_files = st.file_uploader(
        "제품·메뉴·서비스·매장·시술·포트폴리오 사진",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],
        accept_multiple_files=True,
        help=(
            "최대 3장을 추천합니다. "
            "각 사진이 하나의 광고 장면이 됩니다."
        ),
    )

    # 최대 3장
    if (
        uploaded_files
        and len(uploaded_files) > 3
    ):

        st.warning(
            "공모전 데모에서는 최대 3장까지만 사용합니다."
        )

        uploaded_files = uploaded_files[:3]

    # 미리보기
    if uploaded_files:

        preview_cols = st.columns(
            len(uploaded_files)
        )

        for idx, uploaded in enumerate(
            uploaded_files
        ):

            with preview_cols[idx]:

                st.image(
                    uploaded,
                    caption=f"장면 {idx + 1}",
                    use_container_width=True,
                )


    # =====================================================
    # 광고 기획 생성
    # =====================================================

    can_plan = bool(
        subject_name.strip()
        and description.strip()
    )

    if st.button(
        "🧠 상권 분석 + 광고 기획 만들기",
        type="primary",
        use_container_width=True,
        disabled=not can_plan,
    ):

        # -------------------------------------------------
        # 상권 분석
        # -------------------------------------------------

        analysis = analyze_market(
            area_type=area_type,
            business_type=business_type,
            goal=goal,
            location_name=location_name,
        )

        # -------------------------------------------------
        # 광고 카피
        # -------------------------------------------------

        ad_copy = make_ad_copy(
            subject_name=subject_name,
            description=description,
            analysis=analysis,
            style=style,
            goal=goal,
            store_name=store_name,
        )

        # -------------------------------------------------
        # Runway 기본 Prompt
        # -------------------------------------------------

        base_prompt = build_runway_prompt(
            business_type=business_type,
            subject_type=subject_type,
            subject_name=subject_name,
            description=description,
            style=style,
            goal=goal,
            analysis=analysis,
            unique_point=unique_point,
        )

        # -------------------------------------------------
        # session_state
        # -------------------------------------------------

        st.session_state["analysis"] = (
            analysis
        )

        st.session_state["ad_copy"] = (
            ad_copy
        )

        st.session_state["base_prompt"] = (
            base_prompt
        )

        st.session_state["form"] = {

            "store_name":
                store_name,

            "business_type":
                business_type,

            "subject_type":
                subject_type,

            "subject_name":
                subject_name,

            "description":
                description,

            "goal":
                goal,

            "style":
                style,

            "location_name":
                location_name,

            "area_type":
                area_type,

            "unique_point":
                unique_point,
        }

        # -------------------------------------------------
        # 장면별 Prompt
        # -------------------------------------------------

        prompts = []

        if uploaded_files:

            for i in range(
                len(uploaded_files)
            ):

                if i == 0:

                    scene_prompt = (
                        f"{base_prompt}\n\n"
                        "Focus on the main subject. "
                        "Create a strong opening shot. "
                        "Use clear natural movement."
                    )

                elif i == 1:

                    scene_prompt = (
                        f"{base_prompt}\n\n"
                        "Create a second advertising scene. "
                        "Highlight another important selling point. "
                        "Use natural realistic movement."
                    )

                else:

                    scene_prompt = (
                        f"{base_prompt}\n\n"
                        "Create a polished final commercial scene. "
                        "Use a welcoming atmosphere and smooth camera movement. "
                        "Leave clean visual space for text overlay."
                    )

                prompts.append(
                    scene_prompt[:950]
                )

        st.session_state[
            "scene_prompts"
        ] = prompts


    # =====================================================
    # STEP 4
    # =====================================================

    if (
        "analysis"
        in st.session_state
    ):

        analysis = (
            st.session_state[
                "analysis"
            ]
        )

        ad_copy = (
            st.session_state[
                "ad_copy"
            ]
        )

        st.divider()

        st.markdown(
            '<span class="step">STEP 4</span>',
            unsafe_allow_html=True,
        )

        st.subheader(
            "분석 결과와 광고 기획"
        )

        r1, r2, r3 = st.columns(3)

        # ---------------------------------------------
        # 고객
        # ---------------------------------------------

        with r1:

            st.markdown(
                '<div class="result-card">',
                unsafe_allow_html=True,
            )

            st.markdown(
                "**🎯 예상 핵심 고객**"
            )

            st.write(
                analysis["target"]
            )

            st.markdown(
                "**⏰ 반응 시간대**"
            )

            st.write(
                analysis["peak"]
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        # ---------------------------------------------
        # 상권
        # ---------------------------------------------

        with r2:

            st.markdown(
                '<div class="result-card">',
                unsafe_allow_html=True,
            )

            st.markdown(
                "**📍 상권 특성**"
            )

            for item in analysis["traits"]:

                st.write(
                    f"• {item}"
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        # ---------------------------------------------
        # 키워드
        # ---------------------------------------------

        with r3:

            st.markdown(
                '<div class="result-card">',
                unsafe_allow_html=True,
            )

            st.markdown(
                "**💡 마케팅 키워드**"
            )

            st.write(
                " · ".join(
                    analysis["keywords"]
                )
            )

            st.markdown(
                "**업종 강조점**"
            )

            st.write(
                " · ".join(
                    analysis[
                        "business_points"
                    ]
                )
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        st.info(
            analysis["disclaimer"]
        )


        # =================================================
        # 광고 카피
        # =================================================

        st.markdown(
            "### ✍️ 광고 카피"
        )

        st.success(
            ad_copy["headline"]
        )

        st.write(
            ad_copy["body"]
        )

        st.write(
            "**CTA:**",
            ad_copy["cta"],
        )


        # =================================================
        # 장면별 Runway Prompt
        # =================================================

        st.markdown(
            "### 🎥 장면별 Runway 프롬프트"
        )

        edited_prompts = []

        scene_prompts = (
            st.session_state.get(
                "scene_prompts",
                [],
            )
        )

        if uploaded_files:

            # 업로드 수와 Prompt 수가 다르면 다시 생성
            if (
                len(scene_prompts)
                != len(uploaded_files)
            ):

                base_prompt = (
                    st.session_state[
                        "base_prompt"
                    ]
                )

                scene_prompts = []

                for i in range(
                    len(uploaded_files)
                ):

                    scene_prompts.append(
                        base_prompt[:950]
                    )

                st.session_state[
                    "scene_prompts"
                ] = scene_prompts

            for i in range(
                len(uploaded_files)
            ):

                default_prompt = (
                    scene_prompts[i]
                )

                edited = st.text_area(
                    f"장면 {i + 1} 프롬프트",
                    value=default_prompt,
                    height=220,
                    key=f"scene_prompt_{i}",
                )

                edited_prompts.append(
                    edited
                )

        else:

            st.warning(
                "사진을 먼저 업로드해주세요."
            )


        # =================================================
        # 광고 자막
        # =================================================

        st.markdown(
            "### 💬 마지막 장면 광고 자막"
        )

        use_captions = st.checkbox(
            "마지막 장면에 광고 자막 넣기",
            value=True,
        )

        caption_1 = st.text_input(
            "자막 1",
            value=(
                ad_copy["headline"]
            ),
        )

        # 차별점에서 자막 기본값 생성
        if unique_point.strip():

            unique_caption = (
                unique_point.strip()
            )

        else:

            unique_caption = (
                "전문성과 경험으로 "
                "차이를 만듭니다."
            )

        caption_2 = st.text_input(
            "자막 2",
            value=unique_caption,
        )

        caption_3 = st.text_input(
            "자막 3",
            value=(
                ad_copy["cta"]
            ),
        )

        brand_caption = (
            f"{store_name}"
        )

        if location_name.strip():

            brand_caption += (
                f" · {location_name}"
            )

        caption_4 = st.text_input(
            "마지막 브랜드 문구",
            value=brand_caption,
        )


        # =================================================
        # TTS
        # =================================================

        st.markdown(
            "### 🎙 TTS 내레이션"
        )

        use_tts = st.checkbox(
            "한국어 TTS 내레이션 사용",
            value=True,
        )

        # 기본 내레이션 생성
        narration_default = (
            f"{subject_name}. "
        )

        if unique_point.strip():

            narration_default += (
                f"{unique_point}. "
            )

        narration_default += (
            f"{ad_copy['cta']}"
        )

        narration_text = st.text_area(
            "내레이션 문구",
            value=narration_default,
            height=110,
            disabled=not use_tts,
        )

        st.caption(
            "현재 데모에서는 gTTS 한국어 음성을 사용합니다. "
            "추후 남성/여성·감성·유머러스 음성 스타일 선택 기능으로 확장할 수 있습니다."
        )


        # =================================================
        # 리포트 저장
        # =================================================

        report = build_project_report(
            st.session_state["form"],
            analysis,
            ad_copy,
            (
                "\n\n".join(
                    edited_prompts
                )
                if edited_prompts
                else ""
            ),
            model,
            duration,
        )

        st.download_button(
            "📄 분석·프롬프트 JSON 저장",
            data=report.encode(
                "utf-8"
            ),
            file_name=(
                "ai_marketing_plan.json"
            ),
            mime="application/json",
        )


        # =================================================
        # STEP 5
        # =================================================

        st.divider()

        st.markdown(
            '<span class="step">STEP 5</span>',
            unsafe_allow_html=True,
        )

        st.subheader(
            "Runway AI 광고영상 생성"
        )

        clip_count = (
            len(uploaded_files)
            if uploaded_files
            else 0
        )

        total_credits = (
            cost["credits"]
            * clip_count
        )

        total_usd = (
            cost["usd"]
            * clip_count
        )

        cc1, cc2, cc3 = (
            st.columns(3)
        )

        cc1.metric(
            "모델",
            RUNWAY_MODELS[
                model
            ]["label"].split(
                " · "
            )[0],
        )

        cc2.metric(
            "영상 길이",
            (
                f"{duration}초 "
                f"× {clip_count}장면"
            ),
        )

        cc3.metric(
            "예상 총비용",
            (
                f"{total_credits} credits "
                f"/ ${total_usd:.2f}"
            ),
        )


        # =================================================
        # 생성 가능 여부
        # =================================================

        missing = []

        if not uploaded_files:

            missing.append(
                "대표 사진"
            )

        if not api_key_configured():

            missing.append(
                "Runway API 키"
            )

        if missing:

            st.warning(
                "실제 영상 생성 전 필요한 항목: "
                + ", ".join(missing)
            )


        # =================================================
        # 생성 버튼
        # =================================================

        generate_clicked = st.button(
            "🎬 AI 광고영상 만들기",
            type="primary",
            use_container_width=True,
            disabled=bool(missing),
        )


        # =================================================
        # 실제 영상 생성
        # =================================================

        if generate_clicked:

            scene_videos = []

            saved_clip_paths = []

            progress = st.progress(
                0,
                text=(
                    "영상 생성을 준비하는 중입니다..."
                ),
            )

            # ---------------------------------------------
            # Runway 장면 생성
            # ---------------------------------------------

            for i, file in enumerate(
                uploaded_files
            ):

                progress.progress(
                    int(
                        (
                            i
                            / len(
                                uploaded_files
                            )
                        )
                        * 80
                    ),
                    text=(
                        f"장면 "
                        f"{i + 1}/"
                        f"{len(uploaded_files)} "
                        f"생성 중..."
                    ),
                )

                prompt_text = (
                    edited_prompts[i]
                    .strip()
                )

                image_bytes = (
                    file.getvalue()
                )

                result = (
                    generate_image_to_video(
                        image_bytes=
                            image_bytes,
                        prompt=
                            prompt_text,
                        model=
                            model,
                        duration=
                            duration,
                    )
                )

                if not result.ok:

                    st.error(
                        f"장면 {i + 1} 생성 실패\n\n"
                        f"{result.message}"
                    )

                    st.stop()

                scene_videos.append(
                    result.video_bytes
                )

                clip_path = save_video(
                    result.video_bytes
                )

                saved_clip_paths.append(
                    clip_path
                )


            # =================================================
            # 자막 준비
            # =================================================

            final_captions = None

            if use_captions:

                final_captions = [
                    caption_1,
                    caption_2,
                    caption_3,
                    caption_4,
                ]


            # =================================================
            # TTS 준비
            # =================================================

            final_narration = None

            if (
                use_tts
                and narration_text.strip()
            ):

                final_narration = (
                    narration_text.strip()
                )


            # =================================================
            # 합치기
            # =================================================

            progress.progress(
                85,
                text=(
                    "영상 합치기와 "
                    "자막·내레이션 작업 중..."
                ),
            )

            try:

                (
                    merged_bytes,
                    merged_path,
                ) = merge_video_bytes(
                    scene_videos,
                    final_captions=
                        final_captions,
                    narration_text=
                        final_narration,
                )

            except Exception as e:

                st.error(
                    f"최종 영상 제작 실패: {e}"
                )

                st.stop()


            # =================================================
            # 완료
            # =================================================

            progress.progress(
                100,
                text="광고영상 완성!",
            )

            st.success(
                "🎉 광고영상 생성 완료!"
            )


            # =================================================
            # 개별 장면
            # =================================================

            with st.expander(
                "개별 AI 생성 장면 보기"
            ):

                for i, vb in enumerate(
                    scene_videos
                ):

                    st.markdown(
                        f"#### 장면 {i + 1}"
                    )

                    st.video(
                        vb
                    )

                    st.caption(
                        "저장 위치: "
                        + saved_clip_paths[i]
                    )


            # =================================================
            # 최종 영상
            # =================================================

            st.markdown(
                "## 🎬 최종 광고영상"
            )

            st.video(
                merged_bytes
            )

            st.download_button(
                "⬇️ 최종 광고영상 MP4 다운로드",
                data=merged_bytes,
                file_name=(
                    "dongnae_ai_final_ad.mp4"
                ),
                mime="video/mp4",
                use_container_width=True,
            )

            st.caption(
                "최종 저장 위치: "
                + merged_path
            )


# =========================================================
# 시스템 점검 TAB
# =========================================================

with tab_ready:

    st.subheader(
        "시스템 준비 상태"
    )

    checks = [

        (
            "Python 환경",
            True,
            "이 앱이 열렸다면 정상",
        ),

        (
            "Streamlit UI",
            True,
            "정상",
        ),

        (
            "상권 분석",
            True,
            "정상",
        ),

        (
            "광고 카피",
            True,
            "정상",
        ),

        (
            "Runway Prompt",
            True,
            "정상",
        ),

        (
            "멀티 이미지",
            True,
            "최대 3장",
        ),

        (
            "영상 자동 합치기",
            True,
            "MoviePy",
        ),

        (
            "한국어 자막",
            True,
            "MoviePy + Pillow",
        ),

        (
            "TTS 내레이션",
            True,
            "gTTS",
        ),

        (
            "Runway API",
            api_key_configured(),
            ".env에서 감지",
        ),

        (
            "Runway 크레딧",
            None,
            "실제 생성 시 사용",
        ),
    ]

    for (
        name,
        state,
        note,
    ) in checks:

        if state is True:

            icon = "✅"

        elif state is False:

            icon = "⬜"

        else:

            icon = "💳"

        st.write(
            f"{icon} **{name}** — {note}"
        )


    st.divider()

    st.markdown(
        """
        ### 현재 광고 제작 흐름

        **① 사업 정보 입력**

        ↓

        **② 상권 특성 분석**

        ↓

        **③ 광고 카피 및 영상 프롬프트 생성**

        ↓

        **④ 사진별 Runway AI 영상 생성**

        ↓

        **⑤ 여러 영상 자동 연결**

        ↓

        **⑥ 마지막 장면 한글 광고 자막 삽입**

        ↓

        **⑦ 한국어 TTS 내레이션 삽입**

        ↓

        **⑧ 최종 MP4 생성 및 다운로드**
        """
    )