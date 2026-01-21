
import streamlit as st
import requests
import urllib.parse
import re
import json
from typing import List, Dict, Optional

# ----------------------------
# 페이지/스타일
# ----------------------------
st.set_page_config(page_title="INhee Hi‑Fi Music Search", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp { background: radial-gradient(1200px 800px at 8% 10%, #0f1834 0%, #0b1221 45%, #0b1221 100%); color:#e6f1ff; }
h1,h2,h3 { color:#00e5ff; text-shadow:0 0 6px rgba(0,229,255,.35); }
.glass { background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(255,255,255,.02)); border:1px solid rgba(0,229,255,.25); border-radius:14px; backdrop-filter:blur(10px); box-shadow:0 10px 30px rgba(0,20,50,.4); }
.stButton>button { background:linear-gradient(120deg,#0ea5b1,#1c70a3); border:1px solid rgba(0,229,255,.45)!important; color:#ecfeff; font-weight:700; padding:.6rem 1rem; border-radius:10px; }
.stTextInput>div>div>input, .stSelectbox div[data-baseweb="select"]>div { background:rgba(255,255,255,.06)!important; border:1px solid rgba(0,229,255,.25)!important; color:#e6f1ff!important; border-radius:10px!important; }
.video-frame { border-radius:14px; overflow:hidden; border:1px solid rgba(0,229,255,.25); box-shadow:0 18px 40px rgba(0,0,0,.35); }
.card { cursor:pointer; border-radius:12px; padding:10px; background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(255,255,255,.02)); border:1px solid rgba(0,229,255,.20); }
.card:hover { transform: translateY(-2px); box-shadow:0 12px 24px rgba(0,229,255,.18); border:1px solid rgba(0,229,255,.45); }
.card img { width:100%; height:170px; object-fit:cover; border-radius:10px; }
.card .title { font-weight:700; margin-top:8px; color:#eaf7ff; }
.card .meta { font-size: .88rem; color:#9dd5ff; }
.section { padding:14px 16px; }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# 유틸
# ----------------------------
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

YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", None)
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "CONSENT=PENDING+999;"
}

# ----------------------------
# API 검색 (권장)
# ----------------------------
@st.cache_data(show_spinner=False)
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

    ids = [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId")]
    details = {}
    if ids:
        params2 = {"part": "contentDetails", "id": ",".join(ids), "key": YOUTUBE_API_KEY, "maxResults": 50}
        rv = requests.get(VIDEOS_URL, params=params2, timeout=15)
        rv.raise_for_status()
        dv = rv.json()
        for v in dv.get("items", []):
            vid = v["id"]
            details[vid] = parse_iso8601_duration(v.get("contentDetails", {}).get("duration", "PT0S"))

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
            "duration": details.get(vid, "LIVE/SHORT")
        })
    return results, next_token

# ----------------------------
# 스크래핑 (대체, 실패 가능)
# ----------------------------
@st.cache_data(show_spinner=False)
def scrape_youtube_search(query: str, max_items: int = 50):
    q = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={q}&hl=ko&gl=KR"
    try:
        r = requests.get(url, headers=COMMON_HEADERS, timeout=15)
        status = r.status_code
        html = r.text

        # ytInitialData JSON 블롭 추출
        m = re.search(r"ytInitialData\"\s*:\s*(\{.*?\})\s*[,<]", html, re.S)
        if not m:
            # 대체 패턴
            m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});", html, re.S)
        if not m:
            return [], status, len(html), "ytInitialData not found"

        raw_json = m.group(1)
        data = json.loads(raw_json)

        # 렌더러 경로 내려가서 videoRenderer 수집
        # 안전하게 딕셔너리 탐색
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

        results = []
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

# ----------------------------
# 세션 상태
# ----------------------------
ss = st.session_state
ss.setdefault("selected_video_id", "LK0sKS6l2V4")
ss.setdefault("last_query", "")
ss.setdefault("results", [])
ss.setdefault("next_token", None)
ss.setdefault("use_scraping", False)

# ----------------------------
# 사이드바 (검색 조건 - 대기)
# ----------------------------
with st.sidebar:
    st.header("🔎 검색 설정")
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식"], index=0)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=0)
    direct = st.text_input("직접 입력", placeholder="예: 재즈 발라드, Beatles, 감성 피아노")
    st.markdown("---")
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("한 번에 불러올 개수", 8, 60, 20, step=4)
    st.markdown("---")
    if not YOUTUBE_API_KEY:
        st.info("🔐 API 키 미설정: **스크래핑 모드(비권장)** 로 시도합니다.")
        ss.use_scraping = True
    else:
        ss.use_scraping = False
        st.caption("✅ YouTube Data API v3 사용 중")
    do_search = st.button("✅ OK (검색 실행)")

# ----------------------------
# 상단 플레이어
# ----------------------------
st.markdown('<div class="section glass">', unsafe_allow_html=True)
st.subheader("📺 지금 바로 감상하세요")
st.markdown('<div class="video-frame">', unsafe_allow_html=True)
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# 검색 로직
# ----------------------------
def build_query(g: str, i: str, q: str) -> str:
    parts = []
    if g and g != "(선택 없음)": parts.append(g)
    if i and i != "(선택 없음)": parts.append(i)
    if q and q.strip(): parts.append(q.strip())
    return " ".join(parts).strip()

def run_search(query: str, batch: int):
    ss.results = []
    ss.next_token = None
    ss.last_query = query
    with st.spinner(f"‘{query}’ 검색 중…"):
        if ss.use_scraping:
            results, http_status, html_len, err = scrape_youtube_search(query, max_items=batch)
            if err:
                st.error(f"스크래핑 실패: {err}")
            else:
                st.caption(f"스크래핑 HTTP {http_status}, HTML {html_len} chars")
            ss.results.extend(results)
            ss.next_token = None
        else:
            try:
                results, nextt = yt_api_search(query, max_results=batch, page_token=None)
                ss.results.extend(results)
                ss.next_token = nextt
            except requests.HTTPError as e:
                # API 에러 메시지 자세히
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

# ----------------------------
# 결과 표시
# ----------------------------
st.markdown('<div class="section glass">', unsafe_allow_html=True)
st.subheader("🎼 검색 결과")
if ss.last_query and not ss.results:
    st.warning("검색 결과가 없어요. 키워드를 바꿔 시도해 보세요.")
elif ss.results:
    st.caption(f"🔎 ‘{ss.last_query}’ — {len(ss.results)}개 로드됨")
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

# ----------------------------
# 진단 패널
# ----------------------------
with st.expander("🛠️ 도움말 / 진단 열기"):
    st.write("문제가 있을 때 아래 항목을 확인해 주세요.")
    col1, col2 = st.columns(2)
    with col1:
        # 네트워크 체크
        try:
            pr = requests.get("https://www.google.com", timeout=5)
            st.success(f"인터넷 연결 OK (HTTP {pr.status_code})")
        except Exception as e:
            st.error(f"인터넷 연결 실패: {e}")
        # 시크릿
        st.write("YOUTUBE_API_KEY 설정:", "있음 ✅" if YOUTUBE_API_KEY else "없음 ❌")
        st.write("현재 모드:", "API" if not ss.use_scraping else "스크래핑")
    with col2:
        # API 키가 있으면 간단 테스트
        if YOUTUBE_API_KEY:
            try:
                test_res, _ = yt_api_search("saxophone jazz", max_results=3, page_token=None)
                st.success(f"API 테스트 OK: {len(test_res)}개")
            except Exception as e:
                st.error(f"API 테스트 실패: {e}")
        else:
            # 스크래핑 테스트
            r, http_status, html_len, err = scrape_youtube_search("saxophone jazz", max_items=3)
            if err:
                st.error(f"스크래핑 테스트 실패: {err}")
            else:
                st.success(f"스크래핑 테스트: {len(r)}개, HTTP {http_status}, HTML {html_len} chars")

st.markdown("---")
st.caption("© 2026 INhee Hi‑Fi Music Services · Streamlit Cloud Optimized")
