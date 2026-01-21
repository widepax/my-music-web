import os
import requests
import streamlit as st
import streamlit.components.v1 as components

# 1. 앱 설정 및 기본 스타일링 (UI 복구)
st.set_page_config(page_title="INhee Hi-Fi Music", layout="wide")

def load_api_key():
    return os.getenv("YOUTUBE_API_KEY") or st.secrets.get("YOUTUBE_API_KEY")

YOUTUBE_API_KEY = load_api_key()

# 세션 상태: 검색 결과 유지용
if "results" not in st.session_state:
    st.session_state.results = []

# [핵심] 찌꺼기 없는 깜빡임 방지 JS
components.html(
    """
    <script>
    window.parent.document.addEventListener('playNow', function(e) {
        const vId = e.detail.videoId;
        const iframes = window.parent.document.querySelectorAll('iframe');
        for (let f of iframes) {
            if (f.src.includes('youtube.com/embed')) {
                f.src = 'https://www.youtube.com/embed/' + vId + '?autoplay=1';
                break;
            }
        }
    });
    </script>
    """, height=0
)

# 깨진 UI를 바로잡는 전용 CSS
st.markdown("""
<style>
    html, .stApp { background: #070b15; color:#e6f1ff; }
    .music-card {
        cursor: pointer; background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2); border-radius: 12px;
        overflow: hidden; margin-bottom: 20px; transition: 0.2s;
        display: flex; flex-direction: column;
    }
    .music-card:hover { border-color: #00e5ff; transform: translateY(-5px); background: rgba(255,255,255,0.1); }
    .thumb-img { width: 100%; aspect-ratio: 16/9; object-fit: cover; }
    .v-title { padding: 12px 10px 5px 10px; font-size: 0.9rem; font-weight: bold; height: 3.2em; overflow: hidden; line-height: 1.3; }
    .v-channel { padding: 0 10px 12px 10px; font-size: 0.75rem; color: #9dd5ff; }
</style>
""", unsafe_allow_html=True)

# 2. 사이드바 검색 (MR 제외 로직 포함)
with st.sidebar:
    st.header("🔎 검색 설정")
    genre = st.selectbox("장르 선택", ["섹소폰", "국내가요", "팝송", "MR (TJ/KY제외)", "MR/노래방"], index=0)
    direct = st.text_input("곡 제목 입력", placeholder="곡명을 입력하세요")
    do_search = st.button("✅ 검색 실행 (OK)", type="primary", use_container_width=True)

if do_search:
    exclude = "-TJ -금영 -KY -Media" if "제외" in genre else ""
    keywords = "(노래방 OR MR OR Instrument OR Karaoke OR Inst)" if "MR" in genre else genre
    final_query = f'"{direct}" {keywords} {exclude}'.strip()
    
    url = "https://www.googleapis.com/youtube/v3/search"
    res = requests.get(url, params={"part": "snippet", "q": final_query, "type": "video", "maxResults": 24, "key": YOUTUBE_API_KEY}).json()
    
    vids = [it['id']['videoId'] for it in res.get("items", [])]
    if vids:
        v_res = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "snippet,statistics", "id": ",".join(vids), "key": YOUTUBE_API_KEY}).json()
        st.session_state.results = v_res.get("items", [])

# 3. 메인 화면 출력
st.title("🎵 INhee Hi-Fi Music Search")
st.video("https://www.youtube.com/watch?v=LK0sKS6l2V4") # 기본 플레이어

if st.session_state.results:
    cols = st.columns(4)
    for idx, it in enumerate(st.session_state.results):
        v_id = it['id']
        title = it['snippet']['title']
        channel = it['snippet']['channelTitle']
        thumb = it['snippet']['thumbnails']['medium']['url']
        
        with cols[idx % 4]:
            is_blocked = any(name in channel for name in ["TJ", "금영", "KY", "Media"])
            
            # 클릭 시 동작: 차단 채널은 새창, 일반은 JS로 즉각 재생
            click_js = f"window.open('https://www.youtube.com/watch?v={v_id}', '_blank')" if is_blocked else \
                       f"window.parent.document.dispatchEvent(new CustomEvent('playNow', {{detail: {{videoId: '{v_id}'}}}}))"
            
            st.markdown(f"""
                <div class="music-card" onclick="{click_js}">
                    <img src="{thumb}" class="thumb-img">
                    <div class="v-title">{title}</div>
                    <div class="v-channel">{channel}</div>
                </div>
            """, unsafe_allow_html=True)