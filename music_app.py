
# =============================
# INhee Hi‑Fi Music Search (Unified)
# - OK 버튼 트리거
# - YouTube API (권장) + 스크래핑 대체
# - 정규식 제거(괄호 불균형 방지)
# - 캐시 데코레이터 폴리필 + 진단/캐시 클리어
# - 세련된 네온/글래스모피즘 UI
# =============================

# --- 반드시 최상단: import & cache 데코레이터 폴리필 ---
import sys
try:
    import streamlit as st
except Exception as e:
    raise RuntimeError(f"[FATAL] 'import streamlit as st' 실패: {e}")

# cache_data / cache 폴리필 (버전 호환)
if hasattr(st, "cache_data"):
    cache_data = st.cache_data  # 최신 권장
else:
    cache_data = st.cache       # 구버전 호환 (deprecated)

import requests
import urllib.parse
import json
import re
from typing import List, Dict, Tuple, Optional
from platform import python_version

# ------------------------------------------------
# 페이지/테마/CSS
# ------------------------------------------------
st.set_page_config(
    page_title="INhee Hi‑Fi Music Search",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
.stApp { background: radial-gradient(1200px 800px at 8% 10%, #0f1834 0%, #0b1221 45%, #0b1221 100%); color:#e6f1ff; }
h1,h2,h3 { color:#00e5ff; text-shadow:0 0 6px rgba(0,229,255,.35); }
.glass { background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(255,255,255,.02));
         border:1px solid rgba(0,229,255,.25); border-radius:14px; backdrop-filter:blur(10px);
         box-shadow:0 10px 30px rgba(0,20,50,.4); }
.stButton>button { background:linear-gradient(120deg,#0ea5b1,#1c70a3);
                   border:1px solid rgba(0,229,255,.45)!important; color:#ecfeff; font-weight:700;
                   padding:.6rem 1rem; border-radius:10px; }
.stTextInput>div>div>input, .stSelectbox div[data-baseweb="select"]>div {
  background:rgba(255,255,255,.06)!important; border:1px solid rgba(0,229,255,.25)!important;
  color:#e6f1ff!important; border-radius:10px!important;
}
.video-frame { border-radius:14px; overflow:hidden; border:1px solid rgba(0,229,255,.25); box-shadow:0 18px 40px rgba(0,0,0,.35); }
.card { cursor:pointer; border-radius:12px; padding:10px; background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(255,255,255,.02));
        border:1px solid rgba(0,229,255,.20); transition: transform .06s ease, box-shadow .2s ease, border .2s ease; }
.card:hover { transform: translateY(-2px); box-shadow:0 12px 24px rgba(0,229,255,.18); border:1px solid rgba(0,229,255,.45); }
.card img { width:100%; height:170px; object-fit:cover; border-radius:10px; }
.card .title { font-weight:700; margin-top:8px; color:#eaf7ff; }
.card .meta { font-size: .88rem; color:#9dd5ff; }
.section { padding:14px 16px; }
.badge { display:inline-block; font-size:.8rem; padding:4px 8px; border-radius:999px; border:1px solid rgba(0,229,255,.4);
         color:#a6f6ff; background:rgba(0,229,255,.06); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ------------------------------------------------
# 유틸: ISO8601 PT#H#M#S -> mm:ss / hh:mm:ss
# ------------------------------------------------
def parse_iso8601_duration(iso: str) -> str:
    h = re.search(r"(\d+)H", iso or "")
    m = re.search(r"(\d+)M", iso or "")
    s = re.search(r"(\d+)S", iso or "")
    hh = int(h.group(1)) if h else 0
    mm = int(m.group(1)) if m else 0
    ss = int(s.group(1)) if s else 0
    total = hh*3600 + mm*60 + ss
    if total == 0: return "LIVE/SHORT"
    return f"{hh:d}:{mm:02d}:{ss:02d}" if hh else f"{mm:d}:{ss:02d}"

# ------------------------------------------------
# YouTube API (권장)
# ------------------------------------------------
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", None)
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

@cache_data(show_spinner=False)
def yt_api_search(query: str, max_results: int = 50, page_token: Optional[str] = None):
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 50),
        "order": "relevance",
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

# ------------------------------------------------
# 스크래핑(대체 경로): 정규식 제거, 중괄호 밸런싱으로 ytInitialData 파싱
# ------------------------------------------------
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

@cache_data(show_spinner=False)
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

# ------------------------------------------------
# 세션 상태 초기화
# ------------------------------------------------
ss = st.session_state
ss.setdefault("selected_video_id", "LK0sKS6l2V4")  # 초기 기본 영상
ss.setdefault("last_query", "")
ss.setdefault("results", [])
ss.setdefault("next_token", None)
ss.setdefault("use_scraping", False)

# ------------------------------------------------
# 상단 타이틀
# ------------------------------------------------
st.title("🎵 INhee Hi‑Fi Music Search")

# ------------------------------------------------
# 사이드바: 검색 조건(OK 누를 때만 실행)
# ------------------------------------------------
with st.sidebar:
    st.header("🔎 검색 설정")

    # 요구사항에 맞춘 옵션 축소
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식"], index=0)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=0)
    direct = st.text_input("직접 입력", placeholder="예: 재즈 발라드, Beatles")

    st.markdown("---")
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("한 번에 불러올 개수", 12, 60, 24, step=4)

    st.markdown("---")
    if not YOUTUBE_API_KEY:
        st.info("🔐 API 키 미설정: **스크래핑 모드(비권장)** 로 시도합니다.")
        ss.use_scraping = True
    else:
        ss.use_scraping = False
        st.caption("✅ YouTube Data API v3 사용 중")

    do_search = st.button("✅ OK (검색 실행)")

# ------------------------------------------------
# 상단 플레이어
# ------------------------------------------------
st.markdown('<div class="section glass">', unsafe_allow_html=True)
st.subheader("📺 지금 바로 감상하세요")
st.markdown('<div class="video-frame">', unsafe_allow_html=True)
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------
# 검색 함수
# ------------------------------------------------
def build_query(g: str, i: str, q: str) -> str:
    parts = []
    if g and g != "(선택 없음)": parts.append(g)
    if i and i != "(선택 없음)": parts.append(i)
    if q and q.strip(): parts.append(q.strip())
    return " ".join(parts).strip()

def run_search(query: str, batch_size: int):
    ss.results = []
    ss.next_token = None
    ss.last_query = query
    with st.spinner(f"‘{query}’ 검색 중…"):
        if ss.use_scraping:
            results, http_status, html_len, err = scrape_youtube_search(query, max_items=batch_size)
            if err:
                st.error(f"스크래핑 실패: {err}")
            else:
                st.caption(f"스크래핑 HTTP {http_status}, HTML {html_len} chars")
            ss.results.extend(results)
            ss.next_token = None  # 스크래핑은 더 보기 불가
        else:
            # API 모드
            try:
                results, nextt = yt_api_search(query, max_results=batch_size, page_token=None)
                ss.results.extend(results)
                ss.next_token = nextt
            except requests.HTTPError as e:
                try:
                    msg = e.response.json()
                except Exception:
                    msg = {"error": str(e)}
                st.error(f"API 호출 실패: {msg}")

if do_search:
    q = build_query(genre, instrument, direct)
    if not q:
        st.warning("검색어를 입력하거나 장르/악기를 선택한 뒤 **OK**를 눌러주세요.")
    else:
        run_search(q, batch)

# ------------------------------------------------
# 결과 출력: 썸네일 그리드 + 더 보기(무제한, API 모드)
# ------------------------------------------------
st.markdown('<div class="section glass">', unsafe_allow_html=True)
st.subheader("🎼 검색 결과")

if ss.last_query and not ss.results:
    st.warning("검색 결과가 없어요. 다른 키워드로 시도해 보세요.")
elif ss.results:
    st.caption(f"🔎 ‘{ss.last_query}’ — 현재 {len(ss.results)}개 로드됨")
    cols = st.columns(grid_cols)
    for i, item in enumerate(ss.results):
        with cols[i % grid_cols]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.image(item["thumbnail"], use_container_width=True)
            st.markdown(f'<div class="title">{item["title"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="meta">{item["channel"]} · {item["duration"]}</div>', unsafe_allow_html=True)
            if st.button("▶ 재생", key=f"play_{item['video_id']}", use_container_width=True):
                ss.selected_video_id = item["video_id"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # 더 보기(썸네일 제한 없음) — API 모드에서 무한 로딩
    if ss.next_token and not ss.use_scraping:
        if st.button("＋ 더 보기", use_container_width=True):
            with st.spinner("추가 로딩 중…"):
                new, new_token = yt_api_search(ss.last_query, max_results=batch, page_token=ss.next_token)
                ss.results.extend(new)
                ss.next_token = new_token
                st.rerun()
else:
    st.info("좌측에서 조건을 선택/입력하고 **OK** 버튼을 눌러 검색을 시작해 보세요.")

st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------
# 개발자 도구: 캐시/재실행/진단
# ------------------------------------------------
with st.expander("🛠️ 개발자 도구 / 캐시 & 진단"):
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🧹 cache_data 지우기"):
            try:
                st.cache_data.clear()  # 최신
            except Exception:
                try:
                    st.experimental_singleton.clear()
                    st.experimental_memo.clear()
                except Exception:
                    pass
            st.success("cache_data cleared")
    with c2:
        if st.button("🔄 앱 재실행"):
            st.rerun()
    with c3:
        try:
            pr = requests.get("https://www.google.com", timeout=5)
            st.success(f"인터넷 연결 OK (HTTP {pr.status_code})")
        except Exception as e:
            st.error(f"인터넷 연결 실패: {e}")

    st.write("Streamlit 버전:", st.__version__)
    st.write("Python 버전:", python_version())
    st.write("모드:", "API" if not ss.use_scraping else "스크래핑")
    st.write("API 키 인식:", "✅" if YOUTUBE_API_KEY else "❌")

st.markdown("---")
st.caption("© 2026 INhee Hi‑Fi Music Services · Streamlit Cloud Optimized")
