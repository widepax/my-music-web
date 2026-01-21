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

# 사이드바 설정
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

# CSS: 카드 배치 정렬 및 전체 영역 클릭 최적화
st.markdown(f"""
<style>
    :root {{ --ui-scale: {ui_scale}; }}
    html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
    
    /* 카드 컨테이너 정렬 */
    .video-card {{
        position: relative;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2);
        border-radius: 12px;
        padding: 10px;
        transition: transform 0.2s, border-color 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
    }}
    
    .video-card:hover {{
        border-color: #00e5ff;
        transform: translateY(-5px);
        background: rgba(255,255,255,0.1);
    }}

    /* 버튼을 카드 전체 크기로 키우고 투명화하여 덮어씌움 */
    .stButton > button {{
        width: 100%;
        border: none;
        background: transparent;
        color: transparent;
        padding: 0;
        margin: 0;
        height: auto;
    }}

    /* 썸네일 이미지 고정 비율 */
    .thumb-img {{
        width: 100%;
        aspect-ratio: 16 / 9;
        object-fit: cover;
        border-radius: 8px;
    }}

    .title-text {{
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 10px;
        color: #eaf7ff;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 2.4em;
        line-height: 1.2;
    }}

    .channel-text {{
        font-size: 0.75rem;
        color: #9dd5ff;
        margin-top: 5px;
    }}
</style>
""", unsafe_allow_html=True)

# 검색 함수 (로직 유지)
def build_query(g, i, d):
    d_clean = d.strip()
    if g == "MR/노래방": 
        return f'"{d_clean}" 노래방' if d_clean else "인기 노래방 반주"
    parts = [f'"{d_clean}"'] if d_clean else []
    if g != "(선택 없음)": parts.append(g)
    if i != "(선택 없음)": parts.append(i)
    return " ".join(parts).strip()

@st.cache_data(ttl=600)
def search_youtube(query, order, limit, page_token=None):
    if not YOUTUBE_API_KEY: return [], None
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {"part": "snippet", "q": query, "type": "video", "maxResults": limit, "order": order, "key": YOUTUBE_API_KEY, "pageToken": page_token}
        res = requests.get(url, params=params).json()
        results = []
        for it in res.get("items", []):
            vid = it['id']['videoId']
            results.append({"id": vid, "title": it['snippet']['title'], "channel": it['snippet']['channelTitle'], "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", "date": it['snippet']['publishedAt'][:10]})
        return results, res.get("nextPageToken")
    except: return [], None

# 검색 제어 (로직 유지)
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

# 1. 상단 재생 화면 (앵커 포인트를 위해 맨 위 배치)
placeholder = st.empty()
with placeholder.container():
    st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")

st.info("💡 아래 썸네일을 클릭하면 이 화면에서 바로 재생됩니다.")

# 2. 결과 그리드 배치
if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 검색 결과")
    
    # 그리드 배치를 위한 열 생성
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            if i + j < len(ss.results):
                item = ss.results[i + j]
                with col:
                    # 카드 형태의 디자인과 버튼을 결합
                    with st.container():
                        # 카드 디자인 (HTML)
                        st.markdown(f"""
                        <div class="video-card">
                            <img src="{item['thumb']}" class="thumb-img">
                            <div class="title-text">{item['title']}</div>
                            <div class="channel-text">{item['channel']}</div>
                            <div style="font-size:0.7rem; color:gray; margin-top:auto;">📅 {item['date']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 버튼을 투명하게 만들어 카드 위로 배치 (클릭 시 재생)
                        if st.button("▶ 재생", key=f"btn_{item['id']}_{i+j}", use_container_width=True):
                            ss.selected_video_id = item['id']
                            st.rerun()

    # 더 보기 버튼
    if ss.next_token:
        if st.button("＋ 결과 더 보기 (더 많은 곡 찾기)", use_container_width=True):
            with st.spinner("불러오는 중..."):
                q = ss.last_query
                new_res, new_token = search_youtube(q, order_map[order_label], batch, page_token=ss.next_token)
                ss.results.extend(new_res)
                ss.next_token = new_token
                st.rerun()