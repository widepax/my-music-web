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
query_params = st.query_params
current_video_id = query_params.get("v", "LK0sKS6l2V4")

ss.setdefault("results", [])
ss.setdefault("next_token", None)
ss.setdefault("initialized", False)
ss.setdefault("last_query", "섹소폰")

# 사이드바 설정
with st.sidebar:
    st.header("🔎 검색 설정")
    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.20, 0.05)
    st.markdown("---")
    # 카테고리: MR (TJ/KY 제외)
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식", "MR/노래방", "MR (TJ/KY 제외)"], index=6)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=0)
    direct = st.text_input("직접 입력", placeholder="곡 제목을 정확히 입력하세요")
    order_map = {"관련도순": "relevance", "조회수순": "viewCount", "최신순": "date"}
    order_label = st.selectbox("정렬 기준", list(order_map.keys()), index=0)
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("검색 개수", 12, 60, 24, step=4)
    
    # [수정] 검색 버튼이 다른 요소에 의해 숨겨지지 않도록 별도 영역 확보
    st.write("") 
    do_search = st.button("🚀 검색 실행 (지금 바로)", type="primary", use_container_width=True)

# CSS: 검색 버튼은 살리고, 섬네일 클릭 찌꺼기만 제거
st.markdown(f"""
<style>
    :root {{ --ui-scale: {ui_scale}; }}
    html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
    
    /* 카드 전체 링크: 섬네일/제목 어디든 클릭 가능 */
    .music-card-link {{
        display: block !important;
        text-decoration: none !important;
        color: inherit !important;
        margin-bottom: 20px;
        position: relative;
    }}
    
    .card-content {{
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2);
        border-radius: 12px;
        overflow: hidden;
        transition: all 0.2s ease;
    }}
    
    .music-card-link:hover .card-content {{
        border-color: #00e5ff;
        background: rgba(255,255,255,0.1);
        transform: translateY(-5px);
    }}

    /* [수정] 찌꺼기 제거: 보이지 않는 버튼 레이어가 클릭을 방해하지 않도록 처리 */
    .stButton > button {{
        transition: transform 0.1s;
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
    .v-channel {{ padding: 0 12px 12px 12px; color: #9dd5ff; font-size: 0.75rem; }}
</style>
""", unsafe_allow_html=True)

def search_youtube(query, order, limit, page_token=None):
    if not YOUTUBE_API_KEY: return [], None
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        res = requests.get(url, params={
            "part": "snippet", "q": query, "type": "video", 
            "maxResults": limit, "order": order, "key": YOUTUBE_API_KEY, "pageToken": page_token
        }).json()
        vids = [it['id']['videoId'] for it in res.get("items", [])]
        v_res = requests.get("https://www.googleapis.com/youtube/v3/videos", params={
            "part": "snippet,statistics", "id": ",".join(vids), "key": YOUTUBE_API_KEY
        }).json()
        
        results = []
        for it in v_res.get("items", []):
            count = int(it['statistics'].get('viewCount', 0))
            views = f"{count//10000}만" if count >= 10000 else (f"{count/1000:.1f}천" if count >= 1000 else str(count))
            results.append({
                "id": it['id'], "title": it['snippet']['title'], "channel": it['snippet']['channelTitle'],
                "thumb": it['snippet']['thumbnails']['medium']['url'], "views": views
            })
        return results, res.get("nextPageToken")
    except: return [], None

def build_query(g, i, d):
    d_clean = d.strip()
    # [수정] TJ/KY 제외 검색 필터 강화
    # 제목 뒤에 요청하신 키워드들을 붙이고, 뒤에 강력한 제외 키워드(-TJ -금영 등)를 추가합니다.
    exclude_str = "-TJ -금영 -KY -Media -KaraokeKpop" # 대형 노래방 채널 제외 명령어
    
    if g == "MR (TJ/KY 제외)":
        if not d_clean: return f"인기 MR 반주 {exclude_str}"
        return f'"{d_clean}" (노래방 OR MR OR Instrument OR Karaoke) {exclude_str}'
    
    elif g == "MR/노래방":
        if not d_clean: return "인기 노래방 반주"
        return f'"{d_clean}" (노래방 OR MR OR Instrument OR Karaoke)'
        
    parts = [f'"{d_clean}"'] if d_clean else []
    if g != "(선택 없음)": parts.append(g)
    if i != "(선택 없음)": parts.append(i)
    return " ".join(parts).strip()

# 초기 검색
if not ss.initialized:
    res, nt = search_youtube("섹소폰 연주", "relevance", 24)
    ss.results, ss.next_token, ss.initialized = res, nt, True

# 검색 실행
if do_search:
    q = build_query(genre, instrument, direct)
    ss.last_query = q
    res, nt = search_youtube(q, order_map[order_label], batch)
    ss.results, ss.next_token = res, nt

# 메인 UI
st.title("🎵 INhee Hi-Fi Music Room")
st.video(f"https://www.youtube.com/watch?v={current_video_id}")

if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 결과")
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(ss.results):
                item = ss.results[idx]
                
                # [수정] 재생 차단 채널 목록 및 판별
                blocked_names = ["TJ 노래방", "TJ Media", "금영 노래방", "KY Karaoke", "KY금영"]
                is_blocked = any(name in item['channel'] for name in blocked_names)
                
                with col:
                    # 차단 채널은 새창으로, 일반 채널은 현재 창 리로드로 즉시 재생
                    target_url = f"https://www.youtube.com/watch?v={item['id']}" if is_blocked else f"./?v={item['id']}"
                    target_attr = 'target="_blank"' if is_blocked else 'target="_self"'
                    
                    st.markdown(f"""
                    <a href="{target_url}" {target_attr} class="music-card-link">
                        <div class="card-content">
                            <div class="view-badge">👁 {item['views']}</div>
                            <img src="{item['thumb']}" class="thumb-img">
                            <div class="v-title">{item['title']}</div>
                            <div class="v-channel">{item['channel']}</div>
                        </div>
                    </a>
                    """, unsafe_allow_html=True)

    if ss.next_token:
        if st.button("＋ 결과 더 보기", use_container_width=True):
            new_res, new_token = search_youtube(ss.last_query, order_map[order_label], batch, page_token=ss.next_token)
            ss.results.extend(new_res)
            ss.next_token = new_token
            st.rerun()