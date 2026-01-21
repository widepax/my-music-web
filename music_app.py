import os
import requests
import streamlit as st
from typing import Optional

# 1. 앱 설정 및 스타일
st.set_page_config(page_title="INhee Hi‑Fi Music Search", layout="wide")

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

# CSS: 썸네일 클릭 가능하게 만드는 핵심 스타일
st.markdown(f"""
<style>
    :root {{ --ui-scale: {ui_scale}; }}
    html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
    
    /* 카드 전체 영역을 버튼으로 덮는 스타일 */
    .stButton > button {{
        width: 100%; height: 380px; border: none; padding: 0; background: none; 
        color: inherit; text-align: left; position: relative; z-index: 10;
    }}
    .card-wrapper {{ position: relative; width: 100%; height: 380px; margin-bottom: 25px; }}
    .card-design {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        display:flex; flex-direction:column; border-radius:12px; padding:12px; 
        background: rgba(255,255,255,.05); border:1px solid rgba(0,229,255,.15);
        transition: all 0.2s; pointer-events: none; z-index: 5;
    }}
    .stButton:hover + .card-design, .stButton > button:hover {{
        border-color: #00e5ff !important; background: rgba(255,255,255,.1); transform: translateY(-5px);
    }}
    .thumb {{
        width: 100%; padding-top: 56.25%; border-radius: 8px; overflow: hidden;
        background-size: cover !important; background-position: center !important;
    }}
    .title {{ font-weight:700; font-size: 0.95rem; margin-top:12px; height: 2.6em; overflow:hidden; }}
    .channel {{ color:#9dd5ff; font-size: 0.8rem; margin-top:5px; }}
</style>
""", unsafe_allow_html=True)

# 검색 함수
def build_query(g, i, d):
    d_clean = d.strip()
    if g == "MR/노래방": return f'"{d_clean}" 노래방' if d_clean else "인기 노래방"
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

# 검색 실행 로직
if not ss.initialized:
    res, nt = search_youtube("섹소폰", "relevance", 24)
    ss.results, ss.next_token, ss.initialized = res, nt, True

if do_search:
    q = build_query(genre, instrument, direct)
    ss.last_query = q
    res, nt = search_youtube(q, order_map[order_label], batch)
    ss.results, ss.next_token = res, nt

# 메인 화면 구성
st.title("🎵 INhee Hi‑Fi Music Search")
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")
st.info("💡 썸네일 전체를 클릭하면 재생됩니다. 재생 차단 영상은 화면 중앙 'YouTube에서 보기'를 눌러주세요.")

# 결과 그리드
if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 결과")
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            if i + j < len(ss.results):
                item = ss.results[i + j]
                with col:
                    # 썸네일 영역 전체 클릭 구현 (Card Wrapper)
                    st.markdown('<div class="card-wrapper">', unsafe_allow_html=True)
                    if st.button("", key=f"btn_{item['id']}_{i}_{j}"):
                        ss.selected_video_id = item['id']
                        st.rerun()
                    st.markdown(f"""
                        <div class="card-design">
                            <div class="thumb" style="background-image: url('{item['thumb']}');"></div>
                            <div class="title">{item['title']}</div>
                            <div class="channel">{item['channel']}</div>
                            <div style="font-size:0.7rem; color:gray; margin-top:auto;">📅 {item['date']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # 더 보기 버튼
    if ss.next_token:
        if st.button("＋ 더 보기 (결과 추가)", use_container_width=True):
            with st.spinner("불러오는 중..."):
                q = build_query(genre, instrument, direct) if ss.last_query != "섹소폰" else "섹소폰"
                new_res, new_token = search_youtube(q, order_map[order_label], batch, page_token=ss.next_token)
                ss.results.extend(new_res)
                ss.next_token = new_token
                st.rerun()