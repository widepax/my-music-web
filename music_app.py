import os
import requests
import streamlit as st
import streamlit.components.v1 as components

# 1. 앱 설정
st.set_page_config(page_title="INhee Hi-Fi Music", layout="wide")

def load_api_key():
    return os.getenv("YOUTUBE_API_KEY") or st.secrets.get("YOUTUBE_API_KEY")

YOUTUBE_API_KEY = load_api_key()

# 세션 상태 관리 (검색 결과 유지용)
if "results" not in st.session_state:
    st.session_state.results = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# 2. 깜빡임 없는 재생을 위한 자바스크립트 주입
# 이 코드는 부모 창의 iframe(비디오) 소스만 즉시 바꿉니다.
components.html(
    """
    <script>
    window.parent.document.addEventListener('playNow', function(e) {
        const vId = e.detail.videoId;
        // 스트림릿의 비디오 iframe을 찾아 소스만 교체
        const iframes = window.parent.document.querySelectorAll('iframe');
        for (let f of iframes) {
            if (f.src.includes('youtube.com/embed')) {
                f.src = 'https://www.youtube.com/embed/' + vId + '?autoplay=1';
                break;
            }
        }
    });
    </script>
    """,
    height=0,
)

# 3. 스타일 설정
st.markdown("""
<style>
    .music-card {
        cursor: pointer;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2);
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 20px;
        transition: 0.2s;
        position: relative;
    }
    .music-card:hover { border-color: #00e5ff; transform: translateY(-3px); }
    .thumb-img { width: 100%; aspect-ratio: 16/9; object-fit: cover; pointer-events: none; }
    .card-info { padding: 10px; pointer-events: none; }
    .v-title { font-size: 0.9rem; font-weight: bold; height: 2.4em; overflow: hidden; color: #fff; }
    .v-channel { font-size: 0.75rem; color: #9dd5ff; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# 4. 사이드바 검색 로직
with st.sidebar:
    st.header("🔎 검색")
    genre = st.selectbox("장르", ["섹소폰", "국내가요", "팝송", "MR (TJ/KY제외)", "MR/노래방"], index=0)
    direct = st.text_input("곡 제목 입력")
    do_search = st.button("🚀 검색 실행", type="primary", use_container_width=True)

def search(q):
    exclude = "-TJ -금영 -KY -Media" if "제외" in genre else ""
    final_q = f"{direct} {genre} {exclude}".strip()
    url = "https://www.googleapis.com/youtube/v3/search"
    res = requests.get(url, params={
        "part": "snippet", "q": final_q, "type": "video", 
        "maxResults": 24, "key": YOUTUBE_API_KEY
    }).json()
    
    vids = [it['id']['videoId'] for it in res.get("items", [])]
    if not vids: return []
    
    v_details = requests.get("https://www.googleapis.com/youtube/v3/videos", params={
        "part": "snippet,statistics", "id": ",".join(vids), "key": YOUTUBE_API_KEY
    }).json()
    
    output = []
    for it in v_details.get("items", []):
        output.append({
            "id": it['id'],
            "title": it['snippet']['title'],
            "channel": it['snippet']['channelTitle'],
            "thumb": it['snippet']['thumbnails']['medium']['url']
        })
    return output

if do_search or (not st.session_state.results and not st.session_state.last_query):
    st.session_state.results = search(direct)
    st.session_state.last_query = direct

# 5. 메인 화면 레이아웃
st.title("🎵 INhee Music Player")

# 상단 비디오 플레이어 (기본 영상)
st.video("https://www.youtube.com/watch?v=LK0sKS6l2V4")

# 검색 결과 출력
if st.session_state.results:
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.results):
        with cols[idx % 4]:
            # TJ/KY 채널 판별
            is_blocked = any(x in item['channel'] for x in ["TJ", "금영", "KY", "Media"])
            
            # 클릭 이벤트: 차단 채널은 유튜브 새창, 일반 채널은 자바스크립트로 즉시 교체
            if is_blocked:
                click_js = f"window.open('https://www.youtube.com/watch?v={item['id']}', '_blank')"
            else:
                click_js = f"window.parent.document.dispatchEvent(new CustomEvent('playNow', {{detail: {{videoId: '{item['id']}'}}}}))"

            st.markdown(f"""
                <div class="music-card" onclick="{click_js}">
                    <img src="{item['thumb']}" class="thumb-img">
                    <div class="card-info">
                        <div class="v-title">{item['title']}</div>
                        <div class="v-channel">{item['channel']}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)