import os
import requests
import streamlit as st
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

# 쿼리 파라미터를 이용한 재생 전환 로직 (가장 확실한 방식)
query_params = st.query_params
if "v" in query_params:
    ss.selected_video_id = query_params["v"]
    # 파라미터 초기화 (무한 루프 방지)
    st.query_params.clear()

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

# CSS: 버튼 찌꺼기를 원천 차단하기 위해 <a> 태그 기반 카드 설계
st.markdown(f"""
<style>
    :root {{ --ui-scale: {ui_scale}; }}
    html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
    
    /* 카드 전체를 클릭 가능한 링크로 설정 */
    .music-card {{
        display: block;
        text-decoration: none !important;
        color: inherit !important;
        position: relative;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2);
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 20px;
        transition: all 0.2s ease-in-out;
        z-index: 1;
    }}
    
    .music-card:hover {{
        border-color: #00e5ff;
        background: rgba(255,255,255,0.1);
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    }}

    .view-badge {{
        position: absolute; top: 8px; right: 8px;
        background: rgba(0, 0, 0, 0.8); color: #00e5ff;
        padding: 2px 8px; border-radius: 4px;
        font-size: 0.75rem; font-weight: bold;
    }}
    .thumb-img {{ width: 100%; aspect-ratio: 16 / 9; object-fit: cover; display: block; }}
    .v-title {{
        padding: 12px 12px 2px 12px; font-size: 0.9rem; font-weight: 600; color: #eaf7ff;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
        overflow: hidden; height: 2.4em; line-height: 1.2;
    }}
    .v-channel {{
        padding: 0 12px 12px 12px; color: #9dd5ff; font-size: 0.75rem;
    }}
</style>
""", unsafe_allow_html=True)

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
    if g == "MR/노래방":
        return f'"{d_clean}" (노래방 OR MR OR Instrument OR Karaoke)' if d_clean else "인기 노래방 반주"
    parts = [f'"{d_clean}"'] if d_clean else []
    if g != "(선택 없음)": parts.append(g)
    if i != "(선택 없음)": parts.append(i)
    return " ".join(parts).strip()

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
                
                # 재생 불가 채널 판별
                blocked_list = ["TJ 노래방", "TJ Media", "금영 노래방", "KY Karaoke"]
                is_blocked = any(name in item['channel'] for name in blocked_list)
                
                # 핵심 수정: Streamlit 버튼을 완전히 제거하고 HTML <a> 태그 사용
                # 일반 채널은 현재 페이지 리로드(?v=ID), 차단 채널은 유튜브 새창 열기
                target_url = f"https://www.youtube.com/watch?v={item['id']}" if is_blocked else f"./?v={item['id']}"
                target_attr = 'target="_blank"' if is_blocked else 'target="_self"'
                
                with col:
                    st.markdown(f"""
                    <a href="{target_url}" {target_attr} class="music-card">
                        <div class="view-badge">👁 {item['views']}</div>
                        <img src="{item['thumb']}" class="thumb-img">
                        <div class="v-title">{item['title']}</div>
                        <div class="v-channel">{item['channel']}</div>
                    </a>
                    """, unsafe_allow_html=True)

    if ss.next_token:
        # 이 버튼은 카드 외부에 있으므로 유지
        if st.button("＋ 결과 더 보기", use_container_width=True):
            new_res, new_token = search_youtube(ss.last_query, order_map[order_label], batch, page_token=ss.next_token)
            ss.results.extend(new_res)
            ss.next_token = new_token
            st.rerun()