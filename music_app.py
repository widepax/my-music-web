import os
import re
import requests
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

# =============================
# 1. 앱 설정 및 스타일
# =============================
st.set_page_config(page_title="INhee Hi‑Fi Music Search", layout="wide")

def load_api_key_safe() -> Optional[str]:
    """등록된 API 키를 안전하게 로드"""
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        try:
            if "YOUTUBE_API_KEY" in st.secrets:
                key = st.secrets["YOUTUBE_API_KEY"]
        except: pass
    return key

YOUTUBE_API_KEY = load_api_key_safe()

# 세션 상태 초기화
ss = st.session_state
ss.setdefault("selected_video_id", "LK0sKS6l2V4") 
ss.setdefault("results", [])
ss.setdefault("initialized", False)
ss.setdefault("last_query", "섹소폰")

# --------------------
# 사이드바
# --------------------
with st.sidebar:
    st.header("🔎 검색 설정")
    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.20, 0.05)
    
    st.markdown("---")
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식", "MR/노래방"], index=3)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=1)
    direct = st.text_input("직접 입력", placeholder="곡 제목이나 가수명")

    order_map = {"조회수순": "viewCount", "최신순": "date", "관련도순": "relevance"}
    order_label = st.selectbox("정렬 기준", list(order_map.keys()), index=0)
    
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("검색 개수", 12, 60, 24, step=4)
    do_search = st.button("✅ 검색 실행 (OK)")

# --------------------
# CSS (썸네일 클릭 유도를 위한 포인터 추가)
# --------------------
st.markdown(f"""
<style>
    :root {{ --ui-scale: {ui_scale}; }}
    html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
    .card {{
        display:flex; flex-direction:column; height: 390px; 
        border-radius:12px; padding:10px; background: rgba(255,255,255,.05);
        border:1px solid rgba(0,229,255,.2); margin-bottom: 20px;
        transition: all 0.2s ease;
    }}
    .card:hover {{
        border-color: #00e5ff;
        background: rgba(255,255,255,.08);
        transform: translateY(-3px);
    }}
    .thumb-btn {{
        cursor: pointer; /* 이미지 클릭 가능하게 손가락 표시 */
        border: none;
        padding: 0;
        background: none;
        width: 100%;
    }}
    .thumb {{
        position: relative; width: 100%; padding-top: 56.25%; 
        border-radius: 10px; overflow: hidden;
        background-size: cover !important; background-position: center !important;
    }}
    .title {{
        font-weight:700; font-size: calc(0.90rem * var(--ui-scale));
        margin-top:12px; height: 2.6em; line-height: 1.3;
        display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
    }}
    .badge {{
        font-size: 0.7rem; padding:2px 6px; border-radius:4px; 
        background:rgba(0,0,0,0.7); color:#a6f6ff;
    }}
</style>
""", unsafe_allow_html=True)

# =============================
# 2. 검색 엔진 (기존 로직 유지)
# =============================
def build_query(g, i, d):
    if g == "MR/노래방":
        return f"{d.strip()} 노래방 MR Inst Karaoke" if d.strip() else "최신 노래방 반주"
    parts = [p for p in [g, i, d] if p and p != "(선택 없음)"]
    return " ".join(parts).strip()

@st.cache_data(ttl=600)
def search_youtube(query, order, limit):
    if not YOUTUBE_API_KEY: return []
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet", "q": query, "type": "video", 
            "maxResults": limit, "order": order, "key": YOUTUBE_API_KEY
        }
        res = requests.get(url, params=params).json()
        results = []
        for it in res.get("items", []):
            vid = it['id']['videoId']
            results.append({
                "id": vid,
                "title": it['snippet']['title'],
                "channel": it['snippet']['channelTitle'],
                "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                "date": it['snippet']['publishedAt'][:10]
            })
        return results
    except: return []

# =============================
# 3. 화면 렌더링
# =============================
st.title("🎵 INhee Hi‑Fi Music Search")

if not ss.initialized:
    ss.results = search_youtube("섹소폰", "viewCount", 24)
    ss.initialized = True

if do_search:
    q = build_query(genre, instrument, direct)
    ss.last_query = q
    ss.results = search_youtube(q, order_map[order_label], batch)

# [메인 플레이어]
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")
st.caption("💡 재생 불가 영상은 아래의 [🌐 유튜브] 버튼을 이용해 주세요.")

# [결과 그리드]
if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 결과")
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            if i + j < len(ss.results):
                item = ss.results[i + j]
                with col:
                    # 1. 썸네일 클릭 가능하게 만들기
                    # 썸네일 영역 전체를 클릭하면 재생되도록 invisible button 기법 활용
                    with st.container():
                        st.markdown(f"""
                        <div class="card">
                            <div class="thumb" style="background-image: url('{item['thumb']}');">
                                <div style="position:absolute; bottom:5px; right:5px;">
                                    <span class="badge">📅 {item['date']}</span>
                                </div>
                            </div>
                            <div class="title">{item['title']}</div>
                            <div style="color:#9dd5ff; font-size:0.75rem; margin-top:5px;">{item['channel']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 버튼 레이아웃
                        c1, c2 = st.columns(2)
                        with c1:
                            # 이 버튼이 클릭되면 selected_video_id가 변경됨
                            if st.button("▶ 재생", key=f"play_{item['id']}"):
                                ss.selected_video_id = item['id']
                                st.rerun()
                        with c2:
                            url = f"https://www.youtube.com/watch?v={item['id']}"
                            st.link_button("🌐 유튜브", url, use_container_width=True)

# =============================