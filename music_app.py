
# =============================
# INhee Hi‑Fi Music Search (Unified • secrets-safe • grid/height fix • UI scale)
# =============================

# --- 필수 임포트 ---
import os
import re
import json
import urllib.parse
import requests
import streamlit as st
from typing import List, Dict, Tuple, Optional
from platform import python_version
from datetime import datetime

# --------------------
# 전역 상수 / 버전
# --------------------
VERSION = f"2026-01-21 Unified v2 (secrets-safe + grid/height + UI-scale) @ {datetime.now().strftime('%H:%M:%S')}"

# 정렬 라벨 <-> API 파라미터 매핑
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
# 안전한 API 키 로딩 (환경변수 → secrets → 없으면 None)
# ============================
def load_youtube_api_key() -> Optional[str]:
    # 1) 환경변수 우선 (로컬/웹 IDE에서 간단)
    key = os.getenv("YOUTUBE_API_KEY")
    if key:
        return key

    # 2) Streamlit secrets (없으면 예외 가능 → 가드)
    try:
        # secrets.toml이 없거나 키가 없으면 예외 가능
        key = st.secrets["YOUTUBE_API_KEY"]
        if key:
            return key
    except Exception:
        pass

    # 3) 없으면 None → 스크래핑 모드 폴백
    return None

YOUTUBE_API_KEY = load_youtube_api_key()

# ============================
# 사이드바 (먼저 렌더: UI 배율/검색 설정)
# ============================
with st.sidebar:
    st.header("🔎 검색 설정")

    # 글자/UI 배율 (작게 보일 때 키우기)
    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.15, 0.05,
                         help="미리보기 글자가 작다면 1.15~1.30 정도로 키워 보세요.")

    api_key_present = bool(YOUTUBE_API_KEY)
    st.write("🔐 YOUTUBE_API_KEY:", "✅ 감지" if api_key_present else "❌ 없음")
    st.write("🧭 모드:", "API" if api_key_present else "SCRAPING (임시)")

    st.markdown("---")
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식"], index=0)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=0)
    direct = st.text_input("직접 입력", placeholder="예: 재즈 발라드, Beatles")

    order_label = st.selectbox("정렬 기준", list(ORDER_LABEL_MAP.keys()), index=0)
    current_order = ORDER_LABEL_MAP[order_label]

    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("한 번에 불러올 개수", 12, 60, 24, step=4)

    st.markdown("---")
    # 개발/로컬 편의: 키가 없으면 임시 입력으로 API 모드 전환
    if not api_key_present:
        dev_key_input = st.text_input("개발용 키 입력(선택)", type="password",
                                      help="로컬에서만 임시로 입력하세요. 운영에선 secrets/환경변수 권장.")
        if dev_key_input:
            YOUTUBE_API_KEY = dev_key_input
            api_key_present = True
            st.success("API 모드로 전환됨")

    do_search = st.button("✅ OK (검색 실행)")

# ============================
# UI 공통 CSS (실제 <style> 태그)
# - ui_scale 반영
# - 카드/텍스트 높이 고정
# ============================
CUSTOM_CSS = f"""
<style>
:root {{
  --ui-scale: {ui_scale};
}}
html, .stApp {{
  font-size: calc(16px * var(--ui-scale));
}}
.stApp {{
  background: radial-gradient(1200px 800px at 8% 10%, #0a0f1f 0%, #080d1a 50%, #070b15 100%);
  color:#e6f1ff;
  font-family: "Segoe UI", system-ui, -apple-system, Roboto, "Noto Sans KR", sans-serif;
}}
h1,h2,h3 {{ color:#00e5ff; text-shadow:0 0 6px rgba(0,229,255,.35); }}

.glass {{
  background:linear-gradient(160deg,rgba(255,255,255,.05),rgba(255,255,255,.02));
  border:1px solid rgba(0,229,255,.18);
  border-radius:14px;
  backdrop-filter:blur(10px);
  box-shadow:0 10px 26px rgba(0,20,50,.35);
}}
.stButton>button {{
  background:linear-gradient(120deg,#0b0f1a,#111827);
  border:1px solid rgba(0,229,255,.25)!important;
  color:#eaf7ff;
  font-weight:700;
  padding:.58rem .95rem;
  border-radius:10px;
  transition:transform .06s ease, box-shadow .2s ease, border .2s ease, background .25s ease;
  font-size: calc(0.95rem * var(--ui-scale));
}}
.stButton>button:hover {{
  transform: translateY(-1px);
  box-shadow:0 8px 18px rgba(0,229,255,.18);
  border:1px solid rgba(0,229,255,.45)!important;
  background:linear-gradient(120deg,#0e1422,#182236);
}}
.stTextInput>div>div>input,
.stSelectbox div[data-baseweb="select"]>div {{
  background:rgba(255,255,255,.05)!important;
  border:1px solid rgba(0,229,255,.18)!important;
  color:#e6f1ff!important;
  border-radius:10px!important;
}}
.video-frame {{
  border-radius:14px;
  overflow:hidden;
  border:1px solid rgba(0,229,255,.18);
  box-shadow:0 16px 34px rgba(0,0,0,.35);
}}

/* 카드 */
.card {{
  display:flex;
  flex-direction:column;
  justify-content:flex-start;
  height: 330px; /* 카드 전체 높이 고정 */
  cursor:pointer;
  border-radius:12px;
  padding:10px;
  background:linear-gradient(160deg,rgba(255,255,255,.05),rgba(255,255,255,.02));
  border:1px solid rgba(0,229,255,.15);
  transition: transform .06s ease, box-shadow .2s ease, border .2s ease;
}}
.card:hover {{
  transform: translateY(-2px);
  box-shadow:0 12px 22px rgba(0,229,255,.16);
  border:1px solid rgba(0,229,255,.35);
}}
.card img {{
  width:100%;
  height:170px;
  object-fit:cover;
  border-radius:10px;
}}

/* 텍스트 영역 높이 고정(제목 2줄 + 메타 1줄) */
.card .textwrap {{
  display:flex;
  flex-direction:column;
  margin-top:8px;
  min-height: calc(1.2em * 2 + 6px + 1.2em);
  max-height: calc(1.2em * 2 + 6px + 1.2em);
}}
.card .title,
.card .meta {{ margin: 0; }}

.card .title {{
  font-weight:700;
  color:#eaf7ff;
  line-height: 1.2em;
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  overflow:hidden;
  text-overflow:ellipsis;
  min-height: calc(1.2em * 2);
  max-height: calc(1.2em * 2);
  font-size: calc(1.0rem * var(--ui-scale));
}}
.card .meta {{
  font-size: calc(0.9rem * var(--ui-scale));
  color:#9dd5ff;
  line-height: 1.2em;
  margin-top:6px;
  display:-webkit-box;
  -webkit-line-clamp:1;
  -webkit-box-orient:vertical;
  overflow:hidden;
  text-overflow:ellipsis;
  min-height: 1.2em;
  max-height: 1.2em;
}}

.section {{ padding:14px 16px; }}
.badge {{
  display:inline-block;
  font-size: calc(0.85rem * var(--ui-scale));
  padding:4px 8px;
  border-radius:999px;
  border:1px solid rgba(0,229,255,.35);
  color:#a6f6ff;
  background:rgba(0,229,255,.06);
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================
# 유틸
# ============================
def parse_iso8601_duration(iso: str) -> str:
    h = re.search(r"(\d+)H", iso or "")
    m = re.search(r"(\d+)M", iso or "")
    s = re.search(r"(\d+)S", iso or "")
    hh = int(h.group(1)) if h else 0
    mm = int(m.group(1)) if m else 0
    ss = int(s.group(1)) if s else 0
    total = hh*3600 + mm*60 + ss
    if total == 0:
        return "LIVE/SHORT"
    return f"{hh:d}:{mm:02d}:{ss:02d}" if hh else f"{mm:d}:{ss:02d}"

def dedupe_by_video_id(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for it in items:
        vid = it.get("video_id")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        out.append(it)
    return out

# ============================
# YouTube API / SCRAPING
# ============================
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

@st.cache_data(show_spinner=False)
def yt_api_search(query: str, order: str = "viewCount", max_results: int = 50, page_token: Optional[str] = None):
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 50),
        "order": order,
        "videoEmbeddable": "true",
        "safeSearch": "none",
        "regionCode": "KR",
        "relevanceLanguage": "ko",
        "key": YOUTUBE_API_KEY,
    }
    if page_token:
        params["pageToken"] = page_token

    r = requests.get(SEARCH_URL, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    next_token = data.get("nextPageToken")

    ids = [it.get("id", {}).get("videoId") for it in items if it.get("id", {}).get("videoId")]
    durations = {}
    if ids:
        params2 = {
            "part": "contentDetails",
            "id": ",".join(ids),
            "key": YOUTUBE_API_KEY,
            "maxResults": 50
        }
        rv = requests.get(VIDEOS_URL, params=params2, timeout=15)
        rv.raise_for_status()
        dv = rv.json()
        for v in dv.get("items", []):
            vid = v["id"]
            durations[vid] = parse_iso8601_duration(v.get("contentDetails", {}).get("duration", "PT0S"))

    results: List[Dict] = []
    for it in items:
        vid = it["id"]["videoId"]
        sn = it.get("snippet", {})
        thumbs = sn.get("thumbnails", {})
        thumb = thumbs.get("medium") or thumbs.get("high") or thumbs.get("default") or {}
        results.append({
            "video_id": vid,
            "title": sn.get("title", ""),
            "channel": sn.get("channelTitle", ""),
            "thumbnail": thumb.get("url", f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"),
            "duration": durations.get(vid, "LIVE/SHORT")
        })
    return results, next_token

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "CONSENT=PENDING+999;"
}

def _extract_json_after_marker(html: str, marker: str) -> Optional[str]:
    start = html.find(marker)
    if start == -1:
        return None
    brace_start = html.find("{", start)
    if brace_start == -1:
        return None
    depth = 0
    i = brace_start
    while i < len(html):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return html[brace_start:i+1]
        i += 1
    return None

@st.cache_data(show_spinner=False)
def scrape_youtube_search(query: str, max_items: int = 50) -> Tuple[List[Dict], Optional[int], Optional[int], Optional[str]]:
    q = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={q}&hl=ko&gl=KR"
    try:
        r = requests.get(url, headers=COMMON_HEADERS, timeout=15)
        status = r.status_code
        html = r.text

        raw_json = _extract_json_after_marker(html, "ytInitialData")
        if not raw_json:
            raw_json = _extract_json_after_marker(html, "var ytInitialData =")
        if not raw_json:
            return [], status, len(html), "ytInitialData JSON 블롭을 찾지 못했습니다."

        try:
            data = json.loads(raw_json)
        except Exception:
            data = json.loads(raw_json.strip().rstrip(";"))

        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "videoRenderer":
                        yield v
                    else:
                        yield from walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from walk(v)

        results: List[Dict] = []
        for vr in walk(data):
            vid = vr.get("videoId")
            title_runs = (((vr.get("title") or {}).get("runs")) or [{"text": ""}])
            title = title_runs[0].get("text", "")
            owner_runs = (((vr.get("ownerText") or {}).get("runs")) or [{"text": ""}])
            channel = owner_runs[0].get("text", "")
            length = ((vr.get("lengthText") or {}).get("simpleText")) or "LIVE/SHORT"
            if vid and title:
                results.append({
                    "video_id": vid,
                    "title": title,
                    "channel": channel,
                    "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                    "duration": length
                })
            if len(results) >= max_items:
                break

        return results, status, len(html), None
    except Exception as e:
        return [], None, None, str(e)

# ============================
# 세션 상태
# ============================
ss = st.session_state
ss.setdefault("selected_video_id", "LK0sKS6l2V4")
ss.setdefault("last_query", "")
ss.setdefault("results", [])
ss.setdefault("next_token", None)
ss.setdefault("use_scraping", not bool(YOUTUBE_API_KEY))
ss.setdefault("current_order", "viewCount")

# ============================
# 상단 타이틀 & 플레이어
# ============================
st.title("🎵 INhee Hi‑Fi Music Room")
st.caption(f"App VERSION: {VERSION}")

st.markdown('<div class="section glass">', unsafe_allow_html=True)
st.subheader("📺 지금 바로 감상하세요")
st.markdown('<div class="video-frame">', unsafe_allow_html=True)
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ============================
# 검색 로직
# ============================
def build_query(g: str, i: str, q: str) -> str:
    parts = []
    if g and g != "(선택 없음)":
        parts.append(g)
    if i and i != "(선택 없음)":
        parts.append(i)
    if q and q.strip():
        parts.append(q.strip())
    return " ".join(parts).strip()

def run_search(query: str, batch_size: int, order: str):
    ss.results = []
    ss.next_token = None
    ss.last_query = query
    with st.spinner(f"‘{query}’ 검색 중…"):
        if ss.use_scraping:
            results, http_status, html_len, err = scrape_youtube_search(query, max_items=batch_size)
            if err:
                st.error(f"스크래핑 실패(임시 모드): {err} / HTTP: {http_status} / HTML: {html_len}")
            ss.results.extend(results)
            ss.results = dedupe_by_video_id(ss.results)
            ss.next_token = None
        else:
            try:
                results, nextt = yt_api_search(query, order=order, max_results=batch_size, page_token=None)
                ss.results.extend(results)
                ss.results = dedupe_by_video_id(ss.results)
                ss.next_token = nextt
            except requests.HTTPError as e:
                msg = {}
                if getattr(e, "response", None):
                    try:
                        msg = e.response.json()
                    except Exception:
                        try:
                            msg = {"status_code": e.response.status_code, "text": e.response.text[:300]}
                        except Exception:
                            msg = {"error": str(e)}
                else:
                    msg = {"error": str(e)}
                st.error(f"API 호출 실패: {msg}")

if do_search:
    q = build_query(genre, instrument, direct)
    ss.current_order = current_order  # 사이드바 선택 반영
    if not q:
        st.warning("검색어를 입력하거나 장르/악기를 선택한 뒤 **OK**를 눌러주세요.")
    else:
        run_search(q, batch, ss.current_order)

# ============================
# 결과 출력 (행 단위 렌더링 + 더보기)
# ============================
st.markdown('<div class="section glass">', unsafe_allow_html=True)
st.subheader("🎼 검색 결과")

if ss.last_query and not ss.results:
    st.warning("검색 결과가 없어요. 다른 키워드로 시도해 보세요.")
elif ss.results:
    ss.results = dedupe_by_video_id(ss.results)
    st.caption(
        f"🔎 ‘{ss.last_query}’ — {len(ss.results)}개 로드됨 · 정렬: {ORDER_INV_MAP.get(ss.current_order, ss.current_order)}"
    )

    n = len(ss.results)
    for row_start in range(0, n, grid_cols):
        row_items = ss.results[row_start:row_start + grid_cols]
        cols = st.columns(len(row_items))
        for col_idx, item in enumerate(row_items):
            with cols[col_idx]:
                st.markdown('<div class="card">', unsafe_allow_html=True)

                thumb = item.get("thumbnail") or f"https://i.ytimg.com/vi/{item['video_id']}/mqdefault.jpg"
                st.image(thumb, use_container_width=True)

                st.markdown('<div class="textwrap">', unsafe_allow_html=True)
                st.markdown(f'<div class="title">{item.get("title","")}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="meta">{item.get("channel","")} · {item.get("duration","")}</div>',
                    unsafe_allow_html=True
                )
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="btnwrap">', unsafe_allow_html=True)
                if st.button("▶ 재생", key=f"play_{item['video_id']}_{row_start}_{col_idx}", use_container_width=True):
                    ss.selected_video_id = item["video_id"]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

    if ss.next_token and not ss.use_scraping:
        more_key = f"more_{len(ss.results)}_{ss.next_token}_{grid_cols}"
        if st.button("＋ 더 보기", key=more_key, use_container_width=True):
            with st.spinner("추가 로딩 중…"):
                new, new_token = yt_api_search(
                    ss.last_query,
                    order=ss.current_order,
                    max_results=batch,
                    page_token=ss.next_token
                )
                new = dedupe_by_video_id(new)
                ss.results.extend(new)
                ss.results = dedupe_by_video_id(ss.results)
                ss.next_token = new_token
                st.rerun()
else:
    st.info("좌측에서 조건을 선택/입력하고 **OK** 버튼을 눌러 검색을 시작해 보세요.")

st.markdown("</div>", unsafe_allow_html=True)

# ============================
# 개발자 도구 / 진단
# ============================
with st.expander("🛠️ 개발자 도구 / 진단"):
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 앱 재실행(하단)"):
            st.rerun()
    with c2:
        try:
            pr = requests.get("https://www.google.com", timeout=5)
            st.success(f"인터넷 연결 OK (HTTP {pr.status_code})")
        except Exception as e:
            st.error(f"인터넷 연결 실패: {e}")

    st.write("앱 버전:", VERSION)
    st.write("Streamlit 버전:", st.__version__)
    st.write("Python 버전:", python_version())
    st.write("현재 정렬:", ORDER_INV_MAP.get(ss.current_order, ss.current_order))
    st.write("API 모드 여부:", "예" if not ss.use_scraping else "아니오")

    # 현재 실행 파일/엔트리 확인(웹 IDE에서 경로 디버깅)
    try:
        st.write("RUN FILE:", __file__)
    except Exception:
        pass
    st.write("STREAMLIT_SCRIPT_PATH:", os.environ.get("STREAMLIT_SCRIPT_PATH"))
