import os
import requests
import streamlit as st

# =============================
# 1. 앱 설정 및 스타일 (UI 복구)
# =============================
st.set_page_config(page_title="INhee Hi-Fi Music Search", layout="wide")

def load_api_key():
    # 에러 방지를 위해 안전하게 키 로드
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        try: key = st.secrets.get("YOUTUBE_API_KEY")
        except: key = None
    return key

YOUTUBE_API_KEY = load_api_key()

# 세션 상태 (검색 결과 및 현재 영상 고정)
if "results" not in st.session_state:
    st.session_state.results = []
if "current_video_id" not in st.session_state:
    st.session_state.current_video_id = "LK0sKS6l2V4"
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# CSS: 찌꺼기 상자를 유발하는 요소를 완전히 제거하고 텍스트 겹침 수정
st.markdown("""
<style>
    html, .stApp { background: #070b15; color:#e6f1ff; }
    
    /* 검색 결과 카드 디자인 */
    .music-card {
        cursor: pointer;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2);
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 20px;
        transition: 0.2s;
    }
    .music-card:hover { 
        border-color: #00e5ff; 
        transform: translateY(-5px); 
        background: rgba(255,255,255,0.1); 
    }
    .thumb-img { width: 100%; aspect-ratio: 16/9; object-fit: cover; }
    
    /* 텍스트 겹침 방지 및 가독성 향상 */
    .v-title { 
        padding: 10px 10px 2px 10px; 
        font-size: 0.9rem; 
        font-weight: bold; 
        color: #fff; 
        line-height: 1.4;
        height: 2.8em;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    .v-channel { 
        padding: 0 10px 12px 10px; 
        font-size: 0.75rem; 
        color: #9dd5ff; 
    }
    
    /* 불필요한 Streamlit 기본 요소(찌꺼기) 강제 숨김 */
    div[data-testid="stVerticalBlock"] > div[style*="border: none"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# =============================
# 2. 사이드바 및 검색 로직
# =============================
with st.sidebar:
    st.header("🔎 검색 설정")
    genre = st.selectbox("장르 선택", ["섹소폰", "국내가요", "팝송", "MR (TJ/KY제외)", "MR/노래방"], index=0)
    direct = st.text_input("곡 제목 입력", placeholder="곡명을 입력하세요")
    do_search = st.button("✅ 검색 실행 (OK)", type="primary", use_container_width=True)

def fetch_videos(q):
    if not YOUTUBE_API_KEY: return []
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
            output.append({
                "id": it['id'],
                "title": it['snippet']['title'],
                "channel": it['snippet']['channelTitle'],
                "thumb": it['snippet']['thumbnails']['medium']['url']
            })
        return output
    except: return []

if do_search:
    # 제외 키워드 반영 로직
    keywords = "(노래방 OR MR OR Instrument OR Karaoke OR Inst)"
    exclude = "-TJ -금영 -KY -Media" if "제외" in genre else ""
    query = f'"{direct}" {keywords if "MR" in genre else genre} {exclude}'
    
    st.session_state.results = fetch_videos(query)
    st.session_state.last_query = direct

# =============================
# 3. 메인 화면 (플레이어 및 결과)
# =============================
st.title("🎵 INhee Hi-Fi Music Search")

# [수정] 깜빡임을 최소화하기 위해 플레이어를 세션 상태와 연동
st.video(f"https://www.youtube.com/watch?v={st.session_state.current_video_id}")

if st.session_state.results:
    st.subheader(f"🎼 '{st.session_state.last_query}' 검색 결과")
    
    # 4열 그리드 레이아웃
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.results):
        with cols[idx % 4]:
            # TJ/KY 채널 판별
            is_blocked = any(name in item['channel'] for name in ["TJ", "금영", "KY", "Media"])
            
            # 카드 렌더링
            st.markdown(f"""
                <div class="music-card">
                    <img src="{item['thumb']}" class="thumb-img">
                    <div class="v-title">{item['title']}</div>
                    <div class="v-channel">{item['channel']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # [핵심] 찌꺼기 없는 투명 버튼으로 클릭 처리
            # 버튼 클릭 시에만 세션 상태를 바꿔서 검색 결과는 유지하고 영상만 교체
            if st.button("재생", key=f"btn_{item['id']}", use_container_width=True):
                if is_blocked:
                    # 차단 채널은 새창 열기
                    import webbrowser
                    webbrowser.open(f"https://www.youtube.com/watch?v={item['id']}")
                else:
                    st.session_state.current_video_id = item['id']
                    st.rerun()