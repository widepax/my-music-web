import os
import requests
import streamlit as st
import streamlit.components.v1 as components

# =============================
# 1. 앱 설정 및 스타일
# =============================
st.set_page_config(page_title="INhee Hi-Fi Music Search", layout="wide")

def load_api_key():
    # 환경변수 우선, 없으면 secrets에서 가져오되 에러 방지를 위해 get() 사용
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        try:
            key = st.secrets.get("YOUTUBE_API_KEY")
        except:
            key = None
    return key

YOUTUBE_API_KEY = load_api_key()

# 세션 상태 관리 (검색 결과 유지 및 무한 루프 방지)
if "results" not in st.session_state:
    st.session_state.results = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# [핵심] 깜빡임 없는 재생을 위한 JS 브릿지
components.html(
    """
    <script>
    window.parent.document.addEventListener('playVideoNow', function(e) {
        const vId = e.detail.videoId;
        const iframes = window.parent.document.querySelectorAll('iframe');
        for (let f of iframes) {
            if (f.src.includes('youtube.com/embed')) {
                f.src = 'https://www.youtube.com/embed/' + vId + '?autoplay=1';
                f.scrollIntoView({behavior: "smooth"});
                break;
            }
        }
    });
    </script>
    """,
    height=0,
)

st.markdown("""
<style>
    .music-card {
        cursor: pointer; background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2); border-radius: 12px;
        overflow: hidden; margin-bottom: 20px; transition: 0.2s;
    }
    .music-card:hover { border-color: #00e5ff; transform: translateY(-5px); background: rgba(255,255,255,0.1); }
    .thumb-img { width: 100%; aspect-ratio: 16/9; object-fit: cover; pointer-events: none; }
    .v-title { padding: 10px 10px 2px 10px; font-size: 0.85rem; font-weight: bold; color: #fff; height: 3.2em; overflow: hidden; pointer-events: none; }
    .v-channel { padding: 0 10px 10px 10px; font-size: 0.75rem; color: #9dd5ff; pointer-events: none; }
</style>
""", unsafe_allow_html=True)

# =============================
# 2. 사이드바 검색 설정
# =============================
with st.sidebar:
    st.header("🔎 검색 설정")
    genre = st.selectbox("장르 선택", ["섹소폰", "국내가요", "팝송", "MR (TJ/KY제외)", "MR/노래방"], index=0)
    direct = st.text_input("곡 제목 입력", placeholder="곡명을 입력하세요")
    do_search = st.button("✅ 검색 실행 (OK)", type="primary", use_container_width=True)

def build_youtube_query(g, d):
    d_clean = d.strip()
    exclude = "-TJ -금영 -KY -Media -KaraokeKpop"
    
    # 요청하신 키워드 조합 로직
    keywords = "(노래방 OR MR OR Instrument OR Karaoke OR Inst)"
    
    if g == "MR (TJ/KY제외)":
        return f'"{d_clean}" {keywords} {exclude}'
    elif g == "MR/노래방":
        return f'"{d_clean}" {keywords}'
    else:
        return f'"{d_clean}" {g}'

def fetch_videos(q):
    if not YOUTUBE_API_KEY:
        st.error("API 키가 없습니다. secrets.toml 파일을 확인하세요.")
        return []
    url = "https://www.googleapis.com/youtube/v3/search"
    try:
        res = requests.get(url, params={
            "part": "snippet", "q": q, "type": "video", "maxResults": 24, "key": YOUTUBE_API_KEY
        }).json()
        vids = [it['id']['videoId'] for it in res.get("items", [])]
        if not vids: return []
        
        v_res = requests.get("https://www.googleapis.com/youtube/v3/videos", params={
            "part": "snippet,statistics", "id": ",".join(vids), "key": YOUTUBE_API_KEY
        }).json()
        
        output = []
        for it in v_res.get("items", []):
            count = int(it['statistics'].get('viewCount', 0))
            views = f"{count//10000}만" if count >= 10000 else f"{count}회"
            output.append({
                "id": it['id'], "title": it['snippet']['title'],
                "channel": it['snippet']['channelTitle'],
                "thumb": it['snippet']['thumbnails']['medium']['url'], "views": views
            })
        return output
    except: return []

# 검색 실행 로직
if do_search:
    query = build_youtube_query(genre, direct)
    st.session_state.results = fetch_videos(query)
    st.session_state.last_query = query

# =============================
# 3. 메인 화면 구성
# =============================
st.title("🎵 INhee Hi-Fi Music Search")

# 상단 플레이어 (기본 영상)
st.video("https://www.youtube.com/watch?v=LK0sKS6l2V4")

if st.session_state.results:
    st.subheader(f"🎼 검색 결과: {direct}")
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.results):
        with cols[idx % 4]:
            # TJ, 금영 채널 판별
            blocked = ["TJ", "금영", "KY", "Media"]
            is_blocked = any(name in item['channel'] for name in blocked)
            
            # [수정] 클릭 로직: 차단 채널은 새창 리다이렉션, 일반은 즉시 재생
            if is_blocked:
                click_action = f"window.open('https://www.youtube.com/watch?v={item['id']}', '_blank')"
            else:
                click_action = f"window.parent.document.dispatchEvent(new CustomEvent('playVideoNow', {{detail: {{videoId: '{item['id']}'}}}}))"

            st.markdown(f"""
                <div class="music-card" onclick="{click_action}">
                    <img src="{item['thumb']}" class="thumb-img">
                    <div class="v-title">{item['title']}</div>
                    <div class="v-channel">{item['channel']} | 👁 {item['views']}</div>
                </div>
            """, unsafe_allow_html=True)