import streamlit as st
import urllib.parse
import requests
from bs4 import BeautifulSoup
import re
import time

# 페이지 설정 - 세련된 디자인
st.set_page_config(
    page_title="🎵 INhee Hi-Fi Music Search", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🎵"
)

# 세련된 CSS 디자인 (Glassmorphism + Gradient + Modern)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 {
        color: #00d4ff;
        font-weight: 700;
        text-align: center;
        background: linear-gradient(45deg, #00d4ff, #0099cc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 30px rgba(0, 212, 255, 0.5);
    }
    
    /* Glassmorphism 효과 */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 212, 255, 0.1);
    }
    
    .stSelectbox > div > div > select,
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 12px;
        color: #e2e8f0;
        padding: 12px 16px;
        font-size: 14px;
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div > select:focus,
    .stTextInput > div > div > input:focus {
        border-color: #00d4ff;
        box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.2);
        transform: translateY(-2px);
    }
    
    /* 검색 버튼 */
    .stButton > button {
        background: linear-gradient(45deg, #00d4ff, #0099cc);
        color: white;
        border: none;
        border-radius: 15px;
        padding: 14px 32px;
        font-weight: 600;
        font-size: 16px;
        box-shadow: 0 8px 25px rgba(0, 212, 255, 0.4);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 35px rgba(0, 212, 255, 0.6);
    }
    
    .stButton > button:active {
        transform: translateY(-1px);
    }
    
    /* 비디오 플레이어 */
    .video-player-container {
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 2rem;
        border: 1px solid rgba(0, 212, 255, 0.3);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    }
    
    /* 음악 카드 - Grid 레이아웃 */
    .music-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1.5rem;
        padding: 2rem 0;
    }
    
    .music-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 1.5rem;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .music-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.2), transparent);
        transition: left 0.5s;
    }
    
    .music-card:hover::before {
        left: 100%;
    }
    
    .music-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 40px rgba(0, 212, 255, 0.3);
        border-color: rgba(0, 212, 255, 0.5);
    }
    
    .thumbnail-img {
        width: 100%;
        height: 160px;
        object-fit: cover;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    
    .music-title {
        font-weight: 600;
        font-size: 16px;
        margin-bottom: 0.5rem;
        color: #e2e8f0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .music-duration {
        color: #00d4ff;
        font-size: 14px;
        font-weight: 500;
    }
    
    /* 사이드바 개선 */
    .css-1d391kg {
        background: linear-gradient(180deg, rgba(15,15,35,0.95) 0%, rgba(26,26,46,0.95) 100%);
        backdrop-filter: blur(20px);
    }
    
    .stMarkdown {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'selected_video_id' not in st.session_state:
    st.session_state.selected_video_id = None
if 'search_triggered' not in st.session_state:
    st.session_state.search_triggered = False

# 메인 헤더
st.markdown("""
<div class="glass-card" style="text-align: center; margin-bottom: 3rem;">
    <h1>🎵 INhee Hi-Fi Music Search</h1>
    <p style="color: #94a3b8; font-size: 18px; margin-top: -0.5rem;">
        원하는 음악을 찾아 바로 감상하세요
    </p>
</div>
""", unsafe_allow_html=True)

# 1단계: 사이드바 - 검색 조건 수집 (검색 즉시 실행 안됨)
with st.sidebar:
    st.markdown('<div class="glass-card" style="padding: 2rem;">', unsafe_allow_html=True)
    
    st.markdown("""
        <h3 style="color: #00d4ff; margin-bottom: 1.5rem; text-align: center;">
            🔎 검색 조건 설정
        </h3>
    """, unsafe_allow_html=True)
    
    # 정확히 요청한 옵션들만
    genre_options = ["국내가요", "팝송", "섹소폰", "클래식"]
    instrument_options = ["섹소폰", "드럼", "기타", "베이스"]
    
    selected_genre = st.selectbox("🎼 장르 선택", genre_options, key="genre")
    selected_instrument = st.selectbox("🎸 악기 선택", instrument_options, key="instrument")
    keyword_input = st.text_input("🔤 직접 입력", placeholder="추가 키워드...", key="keyword")
    
    st.markdown("---")
    
    # 2단계: OK1 버튼 (검색 트리거)
    if st.button("🚀 OK1 검색 시작", key="search_ok1", help="모든 조건을 조합하여 검색합니다"):
        search_terms = []
        if selected_genre:
            search_terms.append(selected_genre)
        if selected_instrument:
            search_terms.append(selected_instrument)
        if keyword_input:
            search_terms.append(keyword_input.strip())
        
        if search_terms:
            final_query = " ".join(search_terms)
            st.session_state.search_query = final_query
            st.session_state.search_triggered = True
            st.rerun()
        else:
            st.error("⚠️ 최소 하나의 검색 조건을 선택해주세요!")
    
    st.markdown('</div>', unsafe_allow_html=True)

# 3단계: 검색 실행 및 결과 표시
if st.session_state.search_triggered and 'search_query' in st.session_state:
    search_query = st.session_state.search_query
    
    # 메인 영역 2열 레이아웃
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<h3 style="text-align: center;">🎥 지금 재생 중</h3>', unsafe_allow_html=True)
        
        # 비디오 플레이어
        if st.session_state.selected_video_id:
            video_url = f"https://www.youtube.com/watch?v={st.session_state.selected_video_id}"
            st.markdown(f"""
                <div class="video-player-container">
                    {st.video(video_url)}
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="video-player-container" style="display: flex; align-items: center; justify-content: center; height: 300px;">
                    <p style="color: #94a3b8; text-align: center;">
                        검색 결과에서 영상을 선택해주세요 🎵
                    </p>
                </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown('<h3 style="text-align: center;">📊 검색 정보</h3>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="glass-card" style="padding: 1.5rem; text-align: center;">
                <div style="font-size: 24px; color: #00d4ff; font-weight: 700;">
                    {len(st.session_state.search_results)}개
                </div>
                <div style="color: #94a3b8; font-size: 14px;">
                    검색어: <strong>{search_query}</strong>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # 4단계: 섬네일 그리드 (제한 없음)
    st.markdown('<h3 style="text-align: center; margin: 3rem 0 1rem 0;">🎨 검색 결과</h3>', unsafe_allow_html=True)
    
    if st.session_state.search_results:
        # CSS Grid로 무제한 결과 표시
        st.markdown("""
            <div class="music-grid">
        """, unsafe_allow_html=True)
        
        for i, video in enumerate(st.session_state.search_results):
            video_id = video['id']
            title = video['title']
            duration = video['duration']
            
            st.markdown(f"""
                <div class="music-card" onclick="playVideo('{video_id}')" 
                     title="클릭하여 재생">
                    <img src="https://i.ytimg.com/vi/{video_id}/mqdefault.jpg" 
                         alt="{title}" class="thumbnail-img">
                    <div class="music-title">{title}</div>
                    <div class="music-duration">⏱️ {duration}</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # JavaScript로 비디오 재생 제어
        st.markdown(f"""
        <script>
        function playVideo(videoId) {{
            // 세션 상태 업데이트
            parent = window.parent.document;
            sessionStateInput = parent.querySelector('input[name="selected_video_id"]');
            if (sessionStateInput) {{
                sessionStateInput.value = videoId;
            }}
            // 페이지 새로고침
            window.parent.location.reload();
        }}
        </script>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="text-align: center; padding: 3rem; color: #94a3b8;">
                <h3>🔍 검색 중...</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # 실제 검색 실행 (최초 1회만)
        if not st.session_state.search_results:
            with st.spinner(f'"{search_query}" 검색 중... 🌐'):
                try:
                    encoded_query = urllib.parse.quote(search_query)
                    youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}"
                    
                    response = requests.get(youtube_url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 개선된 정규식 패턴
                    video_pattern = r'"videoRenderer":\{"videoId":"([^"]+)".*?"title":\{"runs":\[{"text":"([^"]+)"}).*?"lengthText":\{"simpleText":"([^"]+)"'
                    videos = re.findall(video_pattern, response.text, re.DOTALL)
                    
                    results = []
                    for video_id, title, duration in videos[:50]:  # 최대 50개
                        if video_id and title:
                            results.append({
                                'id': video_id,
                                'title': title[:80] + '...' if len(title) > 80 else title,
                                'duration': duration
                            })
                    
                    st.session_state.search_results = results
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"⚠️ 검색 중 오류 발생: {str(e)[:100]}")
                    st.session_state.search_triggered = False

# 하단 푸터
st.markdown("""
<div style="text-align: center; padding: 3rem 0; color: #64748b; font-size: 14px;">
    © 2026 INhee Hi-Fi Music Services | Streamlit Cloud & GitHub Optimized
</div>
""", unsafe_allow_html=True)
