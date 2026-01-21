import os
import requests
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

# =============================
# 1. 앱 설정 및 스타일 (UI 레이아웃)
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

# 사이드바 설정 (기존 로직 그대로 유지)
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
    # 삭제되었던 검색 실행 버튼 복구
    do_search = st.button("✅ 검색 실행 (OK)")

# CSS: 카드 배치 정렬 및 "섬네일 클릭" 활성화
st.markdown(f"""
<style>
    :root {{ --ui-scale: {ui_scale}; }}
    html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
    
    /* 카드 컨테이너 스타일 */
    .video-card {{
        position: relative;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2);
        border-radius: 12px;
        padding: 0px;
        transition: transform 0.2s, border-color 0.2s;
        height: 100%;
        overflow: hidden;
        z-index: 1;
    }}
    .video-card:hover {{
        border-color: #00e5ff;
        transform: translateY(-5px);
        background: rgba(255,255,255,0.1);
    }}

    /* 조회수 배지 */
    .view-badge {{
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(0, 0, 0, 0.75);
        color: #00e5ff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
        z-index: 5;
    }}

    .thumb-img {{
        width: 100%;
        aspect-ratio: 16 / 9;
        object-fit: cover;
    }}

    .info-container {{
        padding: 12px;
    }}

    .title-text {{
        font-size: 0.9rem;
        font-weight: 600;
        color: #eaf7ff;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 2.4em;
        line-height: 1.2;
    }}

    /* 핵심: 버튼을 투명하게 만들어 카드 전체를 덮음 */
    div[data-testid="stButton"] > button {{
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        background: transparent !important;
        border: none !important;
        color: transparent !important;
        z-index: 100 !important; /* 버튼이 가장 위로 오게 하여 클릭 가로채기 */
        cursor: pointer !important;
        margin: 0 !important;
    }}
    
    /* 사이드바 및 더보기 버튼은 정상적으로 보이게 예외 처리 */
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button,
    .more-btn-container div[data-testid="stButton"] > button {
        position: relative !important;
        background: inherit !important;
        color: inherit !important;
        border: 1px solid rgba(0,229,255,0.5) !important;
        z-index: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

# 조회수 포맷팅
def format_views(count):
    if not count: return "0"
    c = int(count)
    if c >= 10000: return f"{c//10000}만"
    if c >= 1000: return f"{c/1000:.1f}천"
    return str(c)

# 검색 함수 (조회수 포함 정보 추출)
@st.cache_data(ttl=600)
def search_youtube(query, order, limit, page_token=None):
    if not YOUTUBE_API_KEY: return [], None
    try:
        search_url = "https://www.googleapis.com/youtube/v3/search"
        s_params = {"part": "snippet", "q": query, "type": "video", "maxResults": limit, "order": order, "key": YOUTUBE_API_KEY, "pageToken": page_token}
        s_res = requests.get(search_url, params=s_params).json()
        
        vids = [it['id']['videoId'] for it in s_res.get("items", [])]
        if not vids: return [], None

        video_url = "https://www.googleapis.com/youtube/v3/videos"
        v_params = {"part": "snippet,statistics", "id": ",".join(vids), "key": YOUTUBE_API_KEY}
        v_res = requests.get(video_url, params=v_params).json()

        results = []
        for it in v_res.get("items", []):
            results.append({
                "id": it['id'],
                "title": it['snippet']['title'],
                "channel": it['snippet']['channelTitle'],
                "thumb": it['snippet']['thumbnails']['medium']['url'],
                "date": it['snippet']['publishedAt'][:10],
                "views": format_views(it['statistics'].get('viewCount', 0))
            })
        return results, s_res.get("nextPageToken")
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

# 결과 그리드 배치
if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 검색 결과")
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(ss.results):
                item = ss.results[idx]
                with col:
                    # 카드 컨테이너 (디자인)
                    st.markdown(f"""
                    <div class="video-card">
                        <div class="view-badge">👁 {item['views']}</div>
                        <img src="{item['thumb']}" class="thumb-img">
                        <div class="info-container">
                            <div class="title-text">{item['title']}</div>
                            <div style="color:#9dd5ff; font-size:0.75rem; margin-top:5px;">{item['channel']}</div>
                            <div style="font-size:0.7rem; color:gray; margin-top:5px;">📅 {item['date']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 카드 위에 투명하게 덮이는 실제 클릭 버튼
                    if st.button("", key=f"play_{item['id']}_{idx}"):
                        ss.selected_video_id = item['id']
                        st.rerun()

    # 더 보기 버튼 (전용 컨테이너로 스타일 예외처리)
    if ss.next_token:
        st.markdown('<div class="more-btn-container">', unsafe_allow_html=True)
        if st.button("＋ 결과 더 보기 (더 많은 곡 찾기)", use_container_width=True):
            new_res, new_token = search_youtube(ss.last_query, order_map[order_label], batch, page_token=ss.next_token)
            ss.results.extend(new_res)
            ss.next_token = new_token
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)