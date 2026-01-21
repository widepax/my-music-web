import os
import requests
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

# =============================
# 1. 앱 설정 및 스타일
# =============================
st.set_page_config(page_title="INhee Hi-Fi Music Search", layout="wide")

def load_api_key_safe() -> Optional[str]:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        try:
            if "YOUTUBE_API_KEY" in st.secrets:
                key = st.secrets["YOUTUBE_API_KEY"]
        except: pass
    return key

YOUTUBE_API_KEY = load_api_key_safe()

ss = st.session_state
ss.setdefault("selected_video_id", "LK0sKS6l2V4") 
ss.setdefault("results", [])
ss.setdefault("next_token", None)
ss.setdefault("initialized", False)
ss.setdefault("last_query", "섹소폰")

# 사이드바 설정 (기존 로직 100% 유지)
with st.sidebar:
    st.header("🔎 검색 설정")
    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.20, 0.05)
    st.markdown("---")
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식", "MR/노래방"], index=3)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=1)
    direct = st.text_input("직접 입력", placeholder="곡 제목을 정확히 입력하세요")
    order_map = {"관련도순": "relevance", "조회수순": "viewCount", "최신순": "date"}
    order_label = st.selectbox("정렬 기준", list(order_map.keys()), index=0)
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("검색 개수", 12, 60, 24, step=4)
    do_search = st.button("✅ 검색 실행 (OK)")

# CSS: 클릭 문제를 해결하는 최상단 레이어 설정
st.markdown(f"""
<style>
    :root {{ --ui-scale: {ui_scale}; }}
    html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
    
    /* 카드 전체를 감싸는 상자 */
    .card-outer {{
        position: relative;
        width: 100%;
        margin-bottom: 25px;
    }}

    /* 디자인 레이어: pointer-events: none으로 클릭이 통과되게 함 */
    .card-design {{
        position: relative;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2);
        border-radius: 12px;
        overflow: hidden;
        z-index: 1;
        pointer-events: none; 
        transition: all 0.2s;
    }}
    .card-outer:hover .card-design {{
        border-color: #00e5ff;
        background: rgba(255,255,255,0.1);
        transform: translateY(-5px);
    }}

    /* 클릭을 받는 실제 버튼 레이어: z-index를 높여 디자인 위로 올림 */
    .card-outer div[data-testid="stButton"] > button {{
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        background: transparent !important;
        color: transparent !important;
        border: none !important;
        z-index: 10 !important; /* 디자인보다 무조건 위 */
        cursor: pointer !important;
        margin: 0 !important;
    }}

    .view-badge {{
        position: absolute; top: 8px; right: 8px;
        background: rgba(0, 0, 0, 0.8); color: #00e5ff;
        padding: 2px 8px; border-radius: 4px;
        font-size: 0.75rem; font-weight: bold;
    }}
    .thumb-img {{ width: 100%; aspect-ratio: 16 / 9; object-fit: cover; }}
    .v-title {{
        padding: 12px; font-size: 0.9rem; font-weight: 600; color: #eaf7ff;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
        overflow: hidden; height: 2.4em; line-height: 1.2;
    }}
</style>
""", unsafe_allow_html=True)

# 조회수 및 검색 함수 (로직 유지)
def format_views(count):
    if not count: return "0"
    c = int(count)
    if c >= 10000: return f"{c//10000}만"
    if c >= 1000: return f"{c/1000:.1f}천"
    return str(c)

@st.cache_data(ttl=600)
def search_youtube(query, order, limit, page_token=None):
    if not YOUTUBE_API_KEY: return [], None
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        res = requests.get(url, params={"part": "snippet", "q": query, "type": "video", "maxResults": limit, "order": order, "key": YOUTUBE_API_KEY, "pageToken": page_token}).json()
        vids = [it['id']['videoId'] for it in res.get("items", [])]
        v_res = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "snippet,statistics", "id": ",".join(vids), "key": YOUTUBE_API_KEY}).json()
        results = []
        for it in v_res.get("items", []):
            results.append({
                "id": it['id'], "title": it['snippet']['title'], "channel": it['snippet']['channelTitle'],
                "thumb": it['snippet']['thumbnails']['medium']['url'], "date": it['snippet']['publishedAt'][:10],
                "views": format_views(it['statistics'].get('viewCount', 0))
            })
        return results, res.get("nextPageToken")
    except: return [], None

def build_query(g, i, d):
    d_clean = d.strip()
    if g == "MR/노래방": return f'"{d_clean}" 노래방' if d_clean else "인기 노래방 반주"
    parts = [f'"{d_clean}"'] if d_clean else []
    if g != "(선택 없음)": parts.append(g)
    if i != "(선택 없음)": parts.append(i)
    return " ".join(parts).strip()

# 로직 실행
if not ss.initialized:
    res, nt = search_youtube("섹소폰", "relevance", 24)
    ss.results, ss.next_token, ss.initialized = res, nt, True

if do_search:
    q = build_query(genre, instrument, direct)
    ss.last_query = q
    res, nt = search_youtube(q, order_map[order_label], batch)
    ss.results, ss.next_token = res, nt

# 메인 UI
st.title("🎵 INhee Hi-Fi Music Search")
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")

if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 검색 결과")
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(ss.results):
                item = ss.results[idx]
                with col:
                    # 클릭 영역을 정의하는 컨테이너
                    st.markdown(f"""
                    <div class="card-outer">
                        <div class="card-design">
                            <div class="view-badge">👁 {item['views']}</div>
                            <img src="{item['thumb']}" class="thumb-img">
                            <div class="v-title">{item['title']}</div>
                            <div style="padding:0 12px 12px 12px; color:#9dd5ff; font-size:0.75rem;">{item['channel']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 이 버튼이 투명한 상태로 디자인 위를 완전히 덮어 클릭을 가로챔
                    if st.button("", key=f"v_{item['id']}_{idx}"):
                        ss.selected_video_id = item['id']
                        st.rerun()
                    
                    st.markdown("</div>", unsafe_allow_html=True)

    if ss.next_token:
        if st.button("＋ 결과 더 보기", use_container_width=True):
            new_res, new_token = search_youtube(ss.last_query, order_map[order_label], batch, page_token=ss.next_token)
            ss.results.extend(new_res)
            ss.next_token = new_token
            st.rerun()