import os
import requests
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

# =============================
# 1. 앱 설정 및 스타일
# =============================
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

# --------------------
# 사이드바
# --------------------
with st.sidebar:
    st.header("🔎 검색 설정")
    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.20, 0.05)
    
    st.markdown("---")
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식", "MR/노래방"], index=3)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=1)
    direct = st.text_input("직접 입력", placeholder="곡 제목을 정확히 입력하세요")

    # 정확도를 위해 '관련도순'을 기본 인덱스로 설정
    order_map = {"관련도순": "relevance", "조회수순": "viewCount", "최신순": "date"}
    order_label = st.selectbox("정렬 기준", list(order_map.keys()), index=0)
    
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("검색 개수", 12, 60, 24, step=4)
    do_search = st.button("✅ 검색 실행 (OK)")

# --------------------
# CSS (UI 및 카드 전체 클릭 스타일)
# --------------------
st.markdown(f"""
<style>
    :root {{ --ui-scale: {ui_scale}; }}
    html, .stApp {{ font-size: calc(16px * var(--ui-scale)); background: #070b15; color:#e6f1ff; }}
    
    /* 카드 전체를 감싸는 버튼 스타일 */
    .stButton > button {{
        width: 100%; border: none; padding: 0; background: none; color: inherit; text-align: left;
    }}
    .card {{
        display:flex; flex-direction:column; height: 380px; 
        border-radius:12px; padding:12px; background: rgba(255,255,255,.05);
        border:1px solid rgba(0,229,255,.15); transition: all 0.2s;
        cursor: pointer;
    }}
    .card:hover {{
        border-color: #00e5ff; background: rgba(255,255,255,.1); transform: translateY(-5px);
    }}
    .thumb {{
        width: 100%; padding-top: 56.25%; border-radius: 8px; overflow: hidden;
        background-size: cover !important; background-position: center !important;
    }}
    .title {{
        font-weight:700; font-size: calc(0.9rem * var(--ui-scale));
        margin-top:12px; height: 2.6em; overflow:hidden; line-height: 1.3;
    }}
    .channel {{ color:#9dd5ff; font-size: 0.8rem; margin-top:5px; }}
    
    /* 하단 더보기 버튼 전용 스타일 */
    .load-more-btn > div > button {{
        background: rgba(0,229,255,0.1) !important;
        border: 1px solid #00e5ff !important;
        color: #00e5ff !important;
        height: 50px; font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)

# =============================
# 2. 검색 엔진
# =============================
def build_query(g, i, d):
    d_clean = d.strip()
    if g == "MR/노래방":
        return f'"{d_clean}" 노래방 MR' if d_clean else "인기 노래방 반주"
    parts = []
    if d_clean: parts.append(f'"{d_clean}"')
    if g and g != "(선택 없음)": parts.append(g)
    if i and i != "(선택 없음)": parts.append(i)
    return " ".join(parts).strip()

@st.cache_data(ttl=600)
def search_youtube(query, order, limit, page_token=None):
    if not YOUTUBE_API_KEY: return [], None
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet", "q": query, "type": "video", 
            "maxResults": limit, "order": order, "key": YOUTUBE_API_KEY,
            "pageToken": page_token
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
        return results, res.get("nextPageToken")
    except: return [], None

# =============================
# 3. 화면 렌더링
# =============================
st.title("🎵 INhee Hi‑Fi Music Search")

if not ss.initialized:
    res, nt = search_youtube("섹소폰", "relevance", 24)
    ss.results, ss.next_token = res, nt
    ss.initialized = True

if do_search:
    q = build_query(genre, instrument, direct)
    ss.last_query = q
    res, nt = search_youtube(q, order_map[order_label], batch)
    ss.results, ss.next_token = res, nt

# [메인 플레이어]
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")
st.info("💡 영상 재생이 안 될 경우, 위 화면 중앙의 'YouTube에서 보기'를 클릭하세요.")

# [결과 그리드]
if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 검색 결과")
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            if i + j < len(ss.results):
                item = ss.results[i + j]
                with col:
                    # 카드 전체 버튼 (클릭 시 재생)
                    if st.button("", key=f"card_{item['id']}_{i}_{j}"):
                        ss.selected_video_id = item['id']
                        st.rerun()
                    
                    # 카드 UI 디자인 (버튼 위에 겹침)
                    st.markdown(f"""
                    <div style="margin-top:-65px; pointer-events:none;">
                        <div class="card">
                            <div class="thumb" style="background-image: url('{item['thumb']}');"></div>
                            <div class="title">{item['title']}</div>
                            <div class="channel">{item['channel']}</div>
                            <div style="font-size:0.7rem; color:gray; margin-top:auto;">📅 {item['date']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # --------------------
    # [더 보기 버튼 복구]
    # --------------------
    if ss.next_token:
        st.markdown('<div class="load-more-btn">', unsafe_allow_html=True)
        if st.button("＋ 더 보기", use_container_width=True):
            with st.spinner("추가 결과 불러오는 중..."):
                q = build_query(genre, instrument, direct) if ss.last_query != "섹소폰" else "섹소폰"
                new_res, new_token = search_youtube(q, order_map[order_label], batch, page_token=ss.next_token)
                ss.results.extend(new_res)
                ss.next_token = new_token
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)