
import streamlit as st
import requests
import urllib.parse
import re
from typing import List, Dict, Optional

# ------------------------------------------------
# 0) 페이지/스타일: 네온 + 글래스모피즘
# ------------------------------------------------
st.set_page_config(
    page_title="INhee Hi‑Fi Music Search",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
/* 배경 그라디언트 + 글래스 카드 느낌 */
.main, .stApp {
  background: radial-gradient(1200px 800px at 10% 10%, #0f1834 0%, #0b1221 40%, #0b1221 100%);
  color: #e6f1ff;
  font-family: "Segoe UI", system-ui, -apple-system, Roboto, "Noto Sans KR", sans-serif;
}

h1, h2, h3 {
  color: #00e5ff;
  text-shadow: 0 0 6px rgba(0,229,255,0.35);
}

.glass {
  background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border: 1px solid rgba(0,229,255,0.25);
  border-radius: 14px;
  box-shadow: 0 10px 30px rgba(0,20,50,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
}

.stButton>button {
  background: linear-gradient(120deg, #0ea5b1, #1c70a3);
  border: 1px solid rgba(0,229,255,0.45) !important;
  color: #ecfeff;
  font-weight: 700;
  padding: 0.6rem 1rem;
  border-radius: 10px;
  transition: transform .06s ease, box-shadow .2s ease, background .3s ease;
}
.stButton>button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(0,229,255,0.25);
}

.stTextInput>div>div>input, .stSelectbox div[data-baseweb="select"] > div {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(0,229,255,0.25) !important;
  color: #e6f1ff !important;
  border-radius: 10px !important;
}

.video-frame {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(0,229,255,0.25);
  box-shadow: 0 18px 40px rgba(0,0,0,0.35);
}

/* 카드형 썸네일 */
.card {
  cursor: pointer;
  border-radius: 12px;
  padding: 10px;
  background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border: 1px solid rgba(0,229,255,0.20);
  transition: transform .06s ease, box-shadow .2s ease, border .2s ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(0,229,255,0.18);
  border: 1px solid rgba(0,229,255,0.45);
}

.card img {
  width: 100%;
  height: 170px;
  object-fit: cover;
  border-radius: 10px;
}

.card .title {
  font-weight: 700;
  margin-top: 8px;
  color: #eaf7ff;
}
.card .meta {
  font-size: 0.88rem;
  color: #9dd5ff;
}

/* 상단 배지/칩 */
.badge {
  display: inline-block;
  font-size: 0.8rem;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid rgba(0,229,255,0.4);
  color: #a6f6ff;
  background: rgba(0,229,255,0.06);
}

/* 섹션 여백 */
.section {
  padding: 14px 16px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ------------------------------------------------
# 1) 유틸: ISO8601 PT#M#S → mm:ss
# ------------------------------------------------
def parse_iso8601_duration(iso: str) -> str:
    # ex: PT1H02M05S, PT4M13S, PT59S
    hours, minutes, seconds = 0, 0, 0
    h = re.search(r"(\d+)H", iso)
    m = re.search(r"(\d+)M", iso)
    s = re.search(r"(\d+)S", iso)
    if h: hours = int(h.group(1))
    if m: minutes = int(m.group(1))
    if s: seconds = int(s.group(1))
    total = hours * 3600 + minutes * 60 + seconds
    if total == 0:
        return "LIVE/SHORT"
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:d}:{seconds:02d}"

# ------------------------------------------------
# 2) YouTube API 기반 검색 (권장)
# ------------------------------------------------
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", None)
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

@st.cache_data(show_spinner=False)
def yt_api_search(query: str, max_results: int = 50, page_token: Optional[str] = None):
    """YouTube Data API v3: search → videos"""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 50),
        "order": "relevance",
        "videoEmbeddable": "true",
        "safeSearch": "none",
        "key": YOUTUBE_API_KEY,
    }
    if page_token:
        params["pageToken"] = page_token

    r = requests.get(SEARCH_URL, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    next_token = data.get("nextPageToken")

    video_ids = [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId")]
    details_map = {}

    if video_ids:
        params_v = {
            "part": "contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY,
            "maxResults": 50
        }
        rv = requests.get(VIDEOS_URL, params=params_v, timeout=15)
        rv.raise_for_status()
        dv = rv.json()
        for v in dv.get("items", []):
            vid = v["id"]
            details_map[vid] = {
                "duration": parse_iso8601_duration(v.get("contentDetails", {}).get("duration", "PT0S")),
                "views": v.get("statistics", {}).get("viewCount")
            }

    results: List[Dict] = []
    for it in items:
        vid = it["id"]["videoId"]
        snip = it.get("snippet", {})
        thumb = snip.get("thumbnails", {}).get("medium") or snip.get("thumbnails", {}).get("high") or snip.get("thumbnails", {}).get("default")
        results.append({
            "video_id": vid,
            "title": snip.get("title", ""),
            "channel": snip.get("channelTitle", ""),
            "thumbnail": (thumb or {}).get("url", f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"),
            "duration": details_map.get(vid, {}).get("duration", "LIVE/SHORT"),
        })
    return results, next_token

# ------------------------------------------------
# 3) (옵션) API 미사용 HTML 스크래핑 대체 (취약)
#    - 유튜브 마크업/정책 변경 시 쉽게 깨짐
#    - Cloud에서 요청/파싱 제한될 수 있음
# ------------------------------------------------
@st.cache_data(show_spinner=False)
def scrape_youtube_search(query: str, max_items: int = 50, page: int = 1):
    encoded = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        html = r.text
        # 간략 패턴: videoRenderer 블록에서 videoId / title / lengthText / ownerText 추출
        # (YouTube 구조 변경 시 쉽게 실패)
        pattern = re.compile(
            r'"videoRenderer":\{"videoId":"(.*?)".*?"title":\{"runs":\[\{"text":"(.*?)"\}\]\}.*?'
            r'("lengthText":\{"simpleText":"(.*?)"\})?.*?'
            r'"ownerText":\{"runs":\[\{"text":"(.*?)"\}\]\}',
            re.S
        )
        raw = pattern.findall(html)
        results = []
        for tup in raw:
            video_id, title, _, length, channel = tup
            results.append({
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                "duration": length if length else "LIVE/SHORT"
            })
            if len(results) >= max_items:
                break
        # 스크래핑은 nextPageToken을 안정적으로 얻기 어려움 → 무한 로딩 미지원
        return results, None
    except Exception as e:
        st.warning(f"HTML 스크래핑 실패: {e}")
        return [], None

# ------------------------------------------------
# 4) 세션 상태
# ------------------------------------------------
if "selected_video_id" not in st.session_state:
    st.session_state.selected_video_id = "LK0sKS6l2V4"  # 초기 기본 영상
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "results" not in st.session_state:
    st.session_state.results = []
if "next_token" not in st.session_state:
    st.session_state.next_token = None
if "use_scraping" not in st.session_state:
    st.session_state.use_scraping = False

# ------------------------------------------------
# 5) 사이드바: 검색 조건(대기) + 옵션
# ------------------------------------------------
with st.sidebar:
    st.header("🔎 검색 설정")

    genre = st.selectbox(
        "장르 선택",
        ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식"],
        index=0
    )
    instrument = st.selectbox(
        "악기 선택",
        ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"],
        index=0
    )
    direct_query = st.text_input("직접 입력", placeholder="예: 재즈 발라드, Beatles, 감성 피아노")

    st.markdown("---")
    grid_cols = st.slider("한 줄에 표시할 카드 수", min_value=2, max_value=6, value=4, help="컬럼 수를 조절해 카드 크기를 바꿉니다.")
    page_batch = st.slider("한 번에 불러올 개수", min_value=8, max_value=60, value=20, step=4, help="‘더 보기’ 당 로딩되는 카드 수")

    st.markdown("---")
    if not YOUTUBE_API_KEY:
        st.info("🔐 API 키가 없어 **HTML 스크래핑(비권장)**으로 시도합니다.")
        st.session_state.use_scraping = True
    else:
        st.session_state.use_scraping = False
        st.caption("✅ YouTube Data API v3 사용 중")

    do_search = st.button("✅ OK (검색 실행)")

# ------------------------------------------------
# 6) 상단 플레이어
# ------------------------------------------------
st.markdown('<div class="section glass">', unsafe_allow_html=True)
st.subheader("📺 지금 바로 감상하세요")
player_container = st.container()
with player_container:
    st.markdown('<div class="video-frame">', unsafe_allow_html=True)
    st.video(f"https://www.youtube.com/watch?v={st.session_state.selected_video_id}")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------
# 7) OK 버튼 눌렀을 때만 검색 실행
# ------------------------------------------------
def build_query(g: str, i: str, q: str) -> str:
    terms = []
    if g and g != "(선택 없음)":
        terms.append(g)
    if i and i != "(선택 없음)":
        terms.append(i)
    if q and q.strip():
        terms.append(q.strip())
    return " ".join(terms).strip()

def run_search(query: str, batch: int):
    st.session_state.results = []
    st.session_state.next_token = None
    st.session_state.last_query = query

    with st.spinner(f"‘{query}’ 유튜브 검색 중…"):
        if st.session_state.use_scraping:
            results, _ = scrape_youtube_search(query, max_items=batch)
            st.session_state.results.extend(results)
            st.session_state.next_token = None  # 스크래핑은 추가 로딩 불가
        else:
            results, next_token = yt_api_search(query, max_results=batch, page_token=None)
            st.session_state.results.extend(results)
            st.session_state.next_token = next_token

if do_search:
    final_query = build_query(genre, instrument, direct_query)
    if not final_query:
        st.warning("검색어를 입력하거나 장르/악기를 선택한 뒤 **OK**를 눌러주세요.")
    else:
        run_search(final_query, page_batch)

# ------------------------------------------------
# 8) 결과 출력: 카드형 그리드 + 더 보기
# ------------------------------------------------
st.markdown('<div class="section glass">', unsafe_allow_html=True)
st.subheader("🎼 검색 결과")

if st.session_state.last_query and not st.session_state.results:
    # 검색했는데 결과 없음
    st.warning("검색 결과가 없어요. 다른 키워드로 시도해 보세요.")
elif st.session_state.results:
    st.caption(f"🔎 ‘{st.session_state.last_query}’ — 현재 {len(st.session_state.results)}개 로드됨")

    # 카드 그리드 표시
    cols = st.columns(grid_cols)
    for idx, item in enumerate(st.session_state.results):
        with cols[idx % grid_cols]:
            with st.container(border=False):
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.image(item["thumbnail"], use_container_width=True)
                st.markdown(f'<div class="title">{item["title"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="meta">{item["channel"]} · {item["duration"]}</div>', unsafe_allow_html=True)
                play = st.button("▶ 재생", key=f"play_{item['video_id']}", use_container_width=True)
                if play:
                    st.session_state.selected_video_id = item["video_id"]
                    # 즉시 갱신
                    try:
                        st.rerun()
                    except Exception:
                        st.experimental_rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # 더 보기 (API 사용 시에만)
    if st.session_state.next_token and not st.session_state.use_scraping:
        more = st.button("＋ 더 보기", use_container_width=True)
        if more:
            with st.spinner("추가 로딩 중…"):
                new_results, new_token = yt_api_search(
                    st.session_state.last_query,
                    max_results=page_batch,
                    page_token=st.session_state.next_token
                )
                st.session_state.results.extend(new_results)
                st.session_state.next_token = new_token
                try:
                    st.rerun()
                except Exception:
                    st.experimental_rerun()
else:
    # 아직 OK를 안 누른 초기 상태
    st.info("좌측에서 조건을 선택/입력하고 **OK** 버튼을 눌러 검색을 시작해 보세요.")

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2026 INhee Hi‑Fi Music Services · Streamlit Cloud Optimized")
