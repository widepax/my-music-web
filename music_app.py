# =============================
# INhee Hi‑Fi Music Search 
# (Update: MR/Karaoke Category Added)
# =============================

import os
import re
import json
import urllib.parse
import requests
import streamlit as st
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# --------------------
# 매핑 및 설정
# --------------------
ORDER_LABEL_MAP = {
    "조회수 많은 순": "viewCount",
    "관련도 순": "relevance",
    "업로드 날짜 순": "date",
    "평점 순": "rating",
}

st.set_page_config(page_title="INhee Hi‑Fi Music Search", layout="wide")

# ============================
# 세션 상태 관리
# ============================
ss = st.session_state
ss.setdefault("selected_video_id", "LK0sKS6l2V4") # 기본 영상
ss.setdefault("results", [])
ss.setdefault("initialized", False)
ss.setdefault("use_scraping", not bool(os.getenv("YOUTUBE_API_KEY") or st.secrets.get("YOUTUBE_API_KEY")))

# ============================
# 사이드바 (MR 카테고리 추가)
# ============================
with st.sidebar:
    st.header("🔎 검색 설정")
    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.20, 0.05)
    
    st.markdown("---")
    # 카테고리에 'MR/노래방' 추가
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식", "MR/노래방"], index=3)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=1)
    direct = st.text_input("곡 제목 직접 입력", placeholder="예: My Way, 광화문 연가")

    order_label = st.selectbox("정렬 기준", list(ORDER_LABEL_MAP.keys()), index=0)
    current_order = ORDER_LABEL_MAP[order_label]
    
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("한 번에 불러올 개수", 12, 60, 24, step=4)

    do_search = st.button("✅ OK (검색 실행)")

# ============================
# CSS (썸네일 보정 포함)
# ============================
CUSTOM_CSS = f"""
<style>
:root {{ --ui-scale: {ui_scale}; }}
html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
.card {{
    display:flex; flex-direction:column; height: 360px; 
    border-radius:12px; padding:10px; background: rgba(255,255,255,.03);
    border:1px solid rgba(0,229,255,.15); margin-bottom: 20px;
}}
.thumb {{
    position: relative; width: 100%; padding-top: 56.25%; 
    border-radius: 10px; overflow: hidden;
    background-size: cover !important; background-position: center !important;
}}
.badge {{
    font-size: calc(0.75rem * var(--ui-scale)); padding:2px 6px;
    border-radius:4px; color:#a6f6ff; background:rgba(0,0,0,0.6);
}}
.title {{
    font-weight:700; font-size: calc(0.95rem * var(--ui-scale));
    margin-top:10px; height: 2.6em; display:-webkit-box; 
    -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================
# 검색 쿼리 빌더 (MR 전용 로직 적용)
# ============================
def build_smart_query(g, i, d):
    parts = []
    
    # 1. MR/노래방 모드일 경우
    if g == "MR/노래방":
        if d.strip():
            # 입력한 곡 제목 뒤에 보컬 제거 핵심 키워드 조합
            return f"{d.strip()} 노래방 MR Inst Karaoke"
        else:
            return "최신 노래방 인기 MR"

    # 2. 일반 모드
    if g and g != "(선택 없음)": parts.append(g)
    if i and i != "(선택 없음)": parts.append(i)
    if d.strip(): parts.append(d.strip())
    
    return " ".join(parts).strip()

# ============================
# YouTube 검색 API (기존 로직 유지)
# ============================
@st.cache_data(ttl=300)
def fetch_youtube(query, order, limit):
    api_key = os.getenv("YOUTUBE_API_KEY") or st.secrets.get("YOUTUBE_API_KEY")
    if not api_key: return [], None
    
    try:
        search_res = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video", "maxResults": limit, "order": order, "key": api_key}
        ).json()
        
        results = []
        for item in search_res.get("items", []):
            vid = item['id']['videoId']
            results.append({
                "video_id": vid,
                "title": item['snippet']['title'],
                "channel": item['snippet']['channelTitle'],
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                "date": item['snippet']['publishedAt'][:10]
            })
        return results, None
    except:
        return [], None

# ============================
# 검색 실행 제어
# ============================
def run_search_process(query):
    ss.results, _ = fetch_youtube(query, current_order, batch)
    ss.last_query = query

# 최초 1회 자동 검색 (섹소폰)
if not ss.initialized:
    run_search_process("섹소폰")
    ss.initialized = True

if do_search:
    target_query = build_smart_query(genre, instrument, direct)
    run_search_process(target_query)

# ============================
# 메인 UI 레이아웃
# ============================
st.title("🎵 INhee Hi‑Fi Music Search")

# 1. 플레이어
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")

# 2. 검색 결과 그리드
if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 검색 결과")
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            if i + j < len(ss.results):
                item = ss.results[i + j]
                with col:
                    st.markdown(f"""
                    <div class="card">
                        <div class="thumb" style="background-image: url('{item['thumbnail']}');">
                            <div style="position:absolute; bottom:5px; right:5px;">
                                <span class="badge">📅 {item['date']}</span>
                            </div>
                        </div>
                        <div class="title">{item['title']}</div>
                        <div style="color:#9dd5ff; font-size:0.8rem;">{item['channel']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("▶ 재생", key=f"play_{item['video_id']}"):
                        ss.selected_video_id = item['video_id']
                        st.rerun()