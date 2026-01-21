# =============================
# INhee Hi‑Fi Music Search (섬네일 개선 버전)
# =============================

import os, re, json, urllib.parse, requests, streamlit as st
from typing import List, Dict, Optional
from datetime import datetime, timezone
from platform import python_version

VERSION = f"2026-01-21 Unified v6 (thumbnail fix) @ {datetime.now().strftime('%H:%M:%S')}"

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
    except Exception:
        pass
    return None

YOUTUBE_API_KEY = load_youtube_api_key()

# ============================
# 사이드바
# ============================
with st.sidebar:
    st.header("🔎 검색 설정")
    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.20, 0.05)
    api_key_present = bool(YOUTUBE_API_KEY)
    st.write("🔐 YOUTUBE_API_KEY:", "✅ 감지" if api_key_present else "❌ 없음")
    st.write("🧭 모드:", "API" if api_key_present else "SCRAPING (임시)")
    st.markdown("---")
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식"], index=3)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=1)
    direct = st.text_input("직접 입력", placeholder="예: 재즈 발라드, Beatles")
    order_label = st.selectbox("정렬 기준", list(ORDER_LABEL_MAP.keys()), index=0)
    current_order = ORDER_LABEL_MAP[order_label]
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("한 번에 불러올 개수", 12, 60, 24, step=4)
    st.markdown("---")
    if not api_key_present:
        dev_key_input = st.text_input("개발용 키 입력(선택)", type="password")
        if dev_key_input:
            YOUTUBE_API_KEY = dev_key_input
            api_key_present = True
            st.success("API 모드로 전환됨")
    do_search = st.button("✅ OK (검색 실행)")

# ============================
# CSS (섬네일 object-fit + 카드 높이 개선)
# ============================
CUSTOM_CSS = f"""
<style>
:root {{ --ui-scale: {ui_scale}; }}
html, .stApp {{ font-size: calc(16px * var(--ui-scale)); }}
.stApp {{ background: radial-gradient(1200px 800px at 8% 10%, #0a0f1f 0%, #080d1a 50%, #070b15 100%);
        color:#e6f1ff; font-family:"Segoe UI", system-ui, -apple-system, Roboto,"Noto Sans KR",sans-serif; }}
h1,h2,h3 {{ color:#00e5ff; text-shadow:0 0 6px rgba(0,229,255,.35); }}
.card {{ display:flex; flex-direction:column; height:330px; border-radius:12px; padding:10px;
        background:linear-gradient(160deg,rgba(255,255,255,.05),rgba(255,255,255,.02));
        border:1px solid rgba(0,229,255,.15); transition: transform .06s ease, box-shadow .2s ease; }}
.card:hover {{ transform: translateY(-2px); box-shadow:0 12px 22px rgba(0,229,255,.16); }}
.thumb {{ position: relative; width: 100%; height: 0; padding-top: 56.25%; border-radius:10px;
        overflow:hidden; background:linear-gradient(135deg, #0b1220 0%, #0e1627 100%);
        border:1px solid rgba(0,229,255,.18); box-shadow:0 4px 14px rgba(0,0,0,.25); }}
.thumb img {{ position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover; }}
.thumb .overlay {{ position:absolute; inset:0; display:flex; align-items:flex-end; justify-content:space-between;
        padding:8px; background:linear-gradient(180deg, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%);
        color:#eaf7ff; font-size:calc(0.85rem*var(--ui-scale)); }}
.badge {{ display:inline-block; font-size:calc(0.8rem*var(--ui-scale)); padding:2px 8px;
        border-radius:999px; border:1px solid rgba(0,229,255,.35); color:#a6f6ff;
        background:rgba(0,229,255,.14); backdrop-filter: blur(2px); white-space:nowrap; }}
.textwrap {{ flex:1; display:flex; flex-direction:column; margin-top:8px; }}
.title {{ font-weight:700; color:#eaf7ff; line-height:1.2em; display:-webkit-box;
        -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis;
        min-height:calc(1.2em*2); max-height:calc(1.2em*2); font-size:calc(1rem*var(--ui-scale)); }}
.meta {{ font-size:calc(0.9rem*var(--ui-scale)); color:#9dd5ff; line-height:1.2em; margin-top:6px;
        display:-webkit-box; -webkit-line-clamp:1; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================
# 썸네일 유틸
# ============================
PLACEHOLDER_THUMB = "https://via.placeholder.com/480x270/0b1220/9dd5ff?text=No+Thumbnail"

def sanitize_thumb_url(video_id: Optional[str], api_thumb_dict: Optional[dict]) -> str:
    # API 썸네일 확인
    if api_thumb_dict and isinstance(api_thumb_dict, dict):
        for key in ("medium","high","default"):
            v = api_thumb_dict.get(key)
            if v and v.get("url"): return v["url"]
    # video_id fallback
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return PLACEHOLDER_THUMB

# ============================
# 세션 상태
# ============================
ss = st.session_state
ss.setdefault("selected_video_id","LK0sKS6l2V4")
ss.setdefault("last_query","")
ss.setdefault("results",[])
ss.setdefault("next_token",None)
ss.setdefault("use_scraping", not bool(YOUTUBE_API_KEY))
ss.setdefault("current_order","viewCount")

# ============================
# 상단 플레이어
# ============================
st.title("🎵 INhee Hi‑Fi Music Search")
st.caption(f"App VERSION: {VERSION}")
st.markdown('<div class="video-frame">', unsafe_allow_html=True)
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")
st.markdown("</div>", unsafe_allow_html=True)

# ============================
# 카드 렌더링
# ============================
def render_cards(results: List[Dict]):
    n = len(results)
    for row_start in range(0,n,grid_cols):
        row_items = results[row_start:row_start+grid_cols]
        cols = st.columns(len(row_items))
        for col_idx, item in enumerate(row_items):
            with cols[col_idx]:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                vid = item.get("video_id")
                thumb = item.get("thumbnail") or sanitize_thumb_url(vid,None)
                # img 태그 + object-fit 적용
                thumb_html = f"""
                <div class="thumb">
                    <img src="{thumb}" onerror="this.src='{PLACEHOLDER_THUMB}'">
                    <div class="overlay">
                        <div class="ov-left">
                            <span class="badge">👁 {item.get('views_display','N/A')}</span>
                            <span class="badge">📅 {item.get('date_display','N/A')}</span>
                        </div>
                        <div class="ov-right">
                            <span class="badge">⏱ {item.get('duration','')}</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(thumb_html, unsafe_allow_html=True)
                st.markdown('<div class="textwrap">', unsafe_allow_html=True)
                st.markdown(f'<div class="title">{item.get("title","")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="meta">{item.get("channel","")} · {item.get("duration","")}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if st.button("▶ 재생", key=f"play_{vid}_{row_start}_{col_idx}", use_container_width=True):
                    ss.selected_video_id = vid
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ============================
# 검색 후 렌더링
# ============================
if ss.results:
    ss.results = ss.results[:batch]  # batch 제한
    render_cards(ss.results)
