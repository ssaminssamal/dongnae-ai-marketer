"""Static presentation fragments; interactive controls stay native Streamlit."""
import html
import streamlit as st


def load_styles(root):
    st.markdown('<style>' + (root/'studio.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)


def render_header():
    st.markdown('''<div class="studio-top"><span class="studio-logo">◈ 동네AI</span><span>AD STUDIO</span></div>
    <section class="studio-hero"><div class="hero-eyebrow">우리 동네의 이야기를, 한 편의 광고로.</div>
    <h1>우리 가게가 빛나는 순간.</h1><p>사진 몇 장과 가게 소개만 준비하세요.<br>문구부터 목소리까지, 광고의 완성을 도와드릴게요.</p>
    <div class="hero-steps"><span>01 가게 소개</span><i>→</i><span>02 사진 추가</span><i>→</i><span>03 광고 문구</span><i>→</i><span>04 영상 완성</span></div></section>''', unsafe_allow_html=True)


def stage(number, title, subtitle):
    st.markdown(f'<section class="stage-heading"><span>{html.escape(number)}</span><div><h2>{html.escape(title)}</h2><p>{html.escape(subtitle)}</p></div></section>', unsafe_allow_html=True)


def render_empty_preview():
    st.markdown('''<div class="preview-film"><div class="film-meta">DONGNAE ORIGINAL<span>9:16</span></div>
    <div class="film-art"><div class="film-sun"></div><div class="film-shop"><b>◈</b></div></div>
    <div class="film-copy"><small>당신의 가게에, 새로운 시선.</small><h3>다음 장면의 주인공은<br>우리 가게.</h3><p>사진을 추가하면<br>첫 장면이 여기에 나타납니다.</p></div><div class="film-bottom">LOCAL STORIES, WELL TOLD.</div></div>''', unsafe_allow_html=True)
