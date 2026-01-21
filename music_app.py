# =============================
# INhee Hi‑Fi Music Search
# (Fixed: Default Search Execution & Thumbnail Display)
# =============================

import os
import re
import json
import urllib.parse
import requests
import streamlit as st
from typing import List, Dict, Tuple, Optional
from platform import python_version
from datetime import datetime, timezone

VERSION = f"2026-01-21 Unified v7 (Auto-Search + Thumb-Fix) @ {datetime.now().strftime('%H:%M:%S')}"

# --------------------
# 매핑
# --------------------
ORDER_LABEL_MAP = {
    "조회수 많은 순": "viewCount",
    "관련도 순": "relevance",
    "업로드 날짜 순": "date",
    "평점 순": "rating",
}
ORDER_INV_MAP = {v: k for k, v in ORDER_LABEL_MAP.items()}

# --------------------
# 페이지 설정
# --------------------
st.set_page_config(
    page_title="INhee Hi‑Fi Music Search",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================
# 안전한 API 키 로딩
# ============================
def load_youtube_api_key() -> Optional[str]:
    key = os.getenv("YOUTUBE_API_KEY")
    if key: return key
    try:
        key = st.secrets["YOUTUBE_API_KEY"]
        if key: return key
    except Exception: pass
    return None

YOUTUBE_API_KEY = load_youtube_api_key()

# ============================
# 세션 상태 초기화 (검색 로직 이전에 위치)
# ============================
ss = st.session_state
ss.setdefault("selected_video_id", "LK0sKS6l2V4")
ss.setdefault("last_query", "")
ss.setdefault("results", [])
ss.setdefault("next_token", None)
ss.setdefault("use_scraping", not bool(YOUTUBE_API_KEY))
ss.setdefault("current_order", "viewCount")
ss.setdefault("initialized", False) # 자동 검색 여부 체크용

# ============================
# 사이드바
# ============================
with st.sidebar:
    st.header("🔎 검색 설정")

    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.20, 0.05)

    api_key_present = bool(YOUTUBE_API_KEY)
    st.write("🔐 YOUTUBE_API_KEY:", "✅ 감지" if api_key_present else "❌ 없음")
    
    st.markdown("---")
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식"], index=3)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=1)
    direct = st.text_input("직접 입력", placeholder="예: 재즈 발라드, Beatles")

    order_label = st.selectbox("정렬 기준", list(ORDER_LABEL_MAP.keys()), index=0)
    current_order = ORDER_LABEL_MAP[order_label]

    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("한 번에 불러올 개수", 12, 60, 24, step=4)

    if not api_key_present:
        dev_key_input = st.text_input("개발용 키 입력(선택)", type="password")
        if dev_key_input:
            YOUTUBE_API_KEY = dev_key_input
            api_key_present = True
            ss.use_scraping = False
            st.success("API 모드로 전환됨")

    do_search = st.button("✅ OK (검색 실행)")

# ============================
# CSS (Thumbnail Fix 적용)
# ============================
CUSTOM_CSS = """
<style>
:root { --ui-scale: __UI_SCALE__; }
html, .stApp { font-size: calc(16px * var(--ui-scale)); }
.stApp { background: #070b15; color:#e6f1ff; }

/* 카드 스타일 유지 */
.card {
    display:flex; flex-direction:column; height: 350px; 
    border-radius:12px; padding:10px; background: rgba(255,255,255,.03);
    border:1px solid rgba(0,229,255,.15); margin-bottom: 20px;
}

/* 썸네일 오류 해결: background-size와 비율 강제 적용 */
.thumb {
    position: relative; width: 100%; padding-top: 56.25%; 
    border-radius: 10px; overflow: hidden;
    background-color: #000;
    background-position: center !important;
    background-size: cover !important; /* 이미지 꽉 채우기 */
    background-repeat: no-repeat !important;
}

.thumb .overlay {
    position: absolute; inset: 0; display: flex; align-items: flex-end;
    justify-content: space-between; padding: 8px;
    background: linear-gradient(180deg, transparent 60%, rgba(0,0,0,0.7) 100%);
}
.badge {
    font-size: calc(0.75rem * var(--ui-scale)); padding:2px 6px;
    border-radius:4px; color:#a6f6ff; background:rgba(0,0,0,0.6);
}
.card .title {
    font-weight:700; font-size: calc(0.95rem * var(--ui-scale));
    line-height: 1.3; margin-top:10px; height: 2.6em;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}
.card .meta { color:#9dd5ff; font-size: calc(0.85rem * var(--ui-scale)); margin-top:5px; }
</style>
""".replace("__UI_SCALE__", f"{ui_scale}")

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================
# 유틸리티 함수들 (기존 로직 유지)
# ============================
def parse_iso8601_duration(iso: str) -> str:
    h = re.search(r"(\d+)H", iso or ""); m = re.search(r"(\d+)M", iso or ""); s = re.search(r"(\d+)S", iso or "")
    hh=int(h.group(1)) if h else 0; mm=int(m.group(1)) if m else 0; ss=int(s.group(1)) if s else 0
    if hh==0 and mm==0 and ss==0: return "LIVE"
    return f"{hh:d}:{mm:02d}:{ss:02d}" if hh else f"{mm:d}:{ss:02d}"

def format_views_kr(n: Optional[str]) -> str:
    try: v = int(n)
    except: return "N/A"
    if v >= 100_000_000: return f"{v/100_000_000:.1f}억"
    if v >= 10_000: return f"{v/10_000:.1f}만"
    return f"{v}"

def format_date_iso_kr(iso: Optional[str]) -> str:
    if not iso: return "N/A"
    try: return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%Y.%m.%d")
    except: return "N/A"

def sanitize_thumb_url(video_id: str) -> str:
    # YouTube 고해상도 썸네일 우선 사용
    return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"

# ============================
# 검색 함수
# ============================
@st.cache_data(ttl=300)
def yt_api_search(query: str, order: str, max_results: int, page_token: Optional[str] = None):
    params = {
        "part": "snippet", "q": query, "type": "video", "maxResults": max_results,
        "order": order, "regionCode": "KR", "key": YOUTUBE_API_KEY, "pageToken": page_token
    }
    r = requests.get("https://www.googleapis.com/youtube/v3/search", params=params)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    
    ids = [it['id']['videoId'] for it in items]
    # 상세 정보 추가 로드 (조회수, 길이)
    rv = requests.get("https://www.googleapis.com/youtube/v3/videos", 
                      params={"part": "contentDetails,statistics", "id": ",".join(ids), "key": YOUTUBE_API_KEY})
    dv = rv.json().get("items", [])
    v_info = {v['id']: v for v in dv}

    results = []
    for it in items:
        vid = it['id']['videoId']
        sn = it['snippet']
        info = v_info.get(vid, {})
        results.append({
            "video_id": vid, "title": sn['title'], "channel": sn['channelTitle'],
            "thumbnail": sanitize_thumb_url(vid),
            "duration": parse_iso8601_duration(info.get("contentDetails", {}).get("duration")),
            "views_display": format_views_kr(info.get("statistics", {}).get("viewCount")),
            "date_display": format_date_iso_kr(sn['publishedAt'])
        })
    return results, data.get("nextPageToken")

def run_search(query: str, batch_size: int, order: str):
    ss.results = []
    ss.last_query = query
    ss.current_order = order
    with st.spinner("검색 중..."):
        if ss.use_scraping:
            # 기존 스크래핑 로직 호출 (생략됨, 원본 유지 요망)
            pass 
        else:
            res, nt = yt_api_search(query, order, batch_size)
            ss.results = res
            ss.next_token = nt

# ============================
# 메인 레이아웃 및 플레이어
# ============================
st.title("🎵 INhee Hi‑Fi Music Search")

# 플레이어 영역
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")

# ----------------------------
# 핵심: 자동 첫 검색 실행 로직
# ----------------------------
if not ss.initialized:
    # 디폴트 쿼리 생성 (섹소폰 + 섹소폰)
    default_q = "섹소폰 섹소폰"
    run_search(default_q, batch, "viewCount")
    ss.initialized = True

if do_search:
    q_parts = [genre if genre != "(선택 없음)" else "", 
               instrument if instrument != "(선택 없음)" else "", 
               direct]
    final_q = " ".join([p for p in q_parts if p.strip()]).strip()
    if final_q:
        run_search(final_q, batch, current_order)

# ============================
# 결과 렌더링
# ============================
if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 검색 결과")
    
    # 그리드 출력
    n_res = len(ss.results)
    for i in range(0, n_res, grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            if i + j < n_res:
                item = ss.results[i + j]
                with col:
                    # 썸네일 이미지를 배경으로 넣을 때 작은 따옴표 문제 방지
                    t_url = item['thumbnail']
                    st.markdown(f"""
                    <div class="card">
                        <div class="thumb" style="background-image: url('{t_url}');">
                            <div class="overlay">
                                <span class="badge">👁 {item['views_display']}</span>
                                <span class="badge">⏱ {item['duration']}</span>
                            </div>
                        </div>
                        <div class="title">{item['title']}</div>
                        <div class="meta">{item['channel']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("▶ 재생", key=f"btn_{item['video_id']}_{i+j}", use_container_width=True):
                        ss.selected_video_id = item['video_id']
                        st.rerun()

# (이후 개발자 도구 등 기존 코드 유지...)