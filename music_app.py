import streamlit as st
import urllib.parse
import requests
from bs4 import BeautifulSoup
import re

# 1. 페이지 설정 및 디자인 (다크/네온/모던 테마)
st.set_page_config(page_title="INhee Hi-Fi Music Search", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { 
        background-color: #1a1a2e; /* 다크 블루 */
        color: #e0e0e0; /* 밝은 회색 텍스트 */
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3, h4, h5, h6 { 
        color: #00bcd4; /* 네온 시안 */
        text-align: center;
        text-shadow: 0 0 5px #00bcd4; /* 약간의 네온 효과 */
    }
    .stSelectbox label, .stTextInput label, .stButton>button { 
        color: #00bcd4 !important; 
        font-weight: bold;
    }
    .stButton>button {
        background-color: #2c3e50; /* 어두운 버튼 배경 */
        border: 1px solid #00bcd4;
        border-radius: 5px;
        padding: 10px 20px;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #00bcd4; /* 호버 시 네온 배경 */
        color: #1a1a2e !important;
        text-shadow: none;
    }
    .stTextInput>div>div>input {
        background-color: #2c3e50; /* 어두운 입력창 */
        color: #e0e0e0;
        border: 1px solid #00bcd4;
        border-radius: 5px;
    }
    .video-container {
        border: 2px solid #00bcd4;
        border-radius: 10px;
        overflow: hidden;
        margin-top: 20px;
        box-shadow: 0 0 15px rgba(0, 188, 212, 0.5); /* 네온 그림자 */
    }
    .music-card {
        background-color: #2c3e50; /* 카드 배경 */
        border: 1px solid #00bcd4;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        cursor: pointer;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 0 5px rgba(0, 188, 212, 0.3);
    }
    .music-card:hover {
        background-color: #3f5f70; /* 호버 시 색상 변화 */
        box-shadow: 0 0 15px rgba(0, 188, 212, 0.7);
    }
    .music-card img {
        width: 120px;
        height: 90px;
        border-radius: 5px;
        margin-right: 15px;
        object-fit: cover;
    }
    .music-card-title {
        color: #e0e0e0;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .music-card-channel {
        color: #00bcd4;
        font-size: 0.85em;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎵 INhee Hi-Fi Music Search")

# 2. 사이드바: 검색 조건 입력
with st.sidebar:
    st.header("🔎 검색 설정")
    genre = st.selectbox("음악 장르 선택", ["전체", "국내가요", "팝송", "클래식", "재즈", "OST"])
    instrument = st.selectbox("악기 선택", ["전체", "섹소폰", "드럼", "기타", "베이스", "피아노"])
    
    st.markdown("---")
    direct_query = st.text_input("직접 검색어 입력", placeholder="예: 비틀즈, 감미로운 재즈")
    
    st.markdown("---")
    # 검색 트리거 버튼
    search_button = st.button("🎶 검색 시작")

# 3. 메인 영역: 검색 결과 및 플레이어
st.subheader("📺 지금 바로 감상하세요!")
current_video_url = st.empty() # 재생될 영상 URL을 저장할 임시 공간

# 초기 플레이어 (기본 영상)
if 'selected_video_id' not in st.session_state:
    st.session_state.selected_video_id = "LK0sKS6l2V4" # 사용자님의 섹소폰 영상 ID
st.markdown(f'<div class="video-container">{st.video(f"https://www.youtube.com/watch?v={st.session_state.selected_video_id}")}</div>', unsafe_allow_html=True)


st.subheader("⚡ 검색 결과 리스트")

# 검색 실행 로직
if search_button:
    search_terms = []
    if genre and genre != "전체":
        search_terms.append(genre)
    if instrument and instrument != "전체":
        search_terms.append(instrument)
    if direct_query:
        search_terms.append(direct_query)
    
    final_query = "+".join(search_terms) if search_terms else "음악" # 검색어 없으면 '음악'으로 검색
    
    if final_query:
        encoded_query = urllib.parse.quote(final_query)
        youtube_search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        # Streamlit Spinner로 로딩 표시 (i5-11400도 네트워크 대기는 필요)
        with st.spinner(f"'{final_query}'(으)로 유튜브 검색 중... 🌐"):
            try:
                # 웹 스크래핑으로 유튜브 검색 결과 파싱 (API 없이 섬네일 가져오기)
                response = requests.get(youtube_search_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 유튜브 검색 결과에서 영상 정보 추출 (정규식 활용)
                # 이 패턴은 유튜브 업데이트에 따라 변경될 수 있습니다.
                video_data = re.findall(r'"videoRenderer":{"videoId":"(.*?)"[^}]*"title":{"runs":\[{"text":"(.*?)"}\][^}]*"lengthText":{"simpleText":"(.*?)"}[^}]*"ownerText":{"runs":\[{"text":"(.*?)"}\]}', response.text)
                
                if video_data:
                    st.write(f"총 {len(video_data)}개의 검색 결과가 발견되었습니다.")
                    
                    # 4. 섬네일 리스트 출력
                    cols_per_row = 3 # 한 줄에 3개씩 섬네일 표시
                    rows = [st.columns(cols_per_row) for _ in range((len(video_data) + cols_per_row - 1) // cols_per_row)]

                    for idx, (video_id, title, length, channel) in enumerate(video_data):
                        if idx >= 9: break # 너무 많은 결과는 잘라냄 (최대 9개)
                        col = rows[idx // cols_per_row][idx % cols_per_row]
                        with col:
                            # 섬네일 클릭 시 재생되도록 버튼 대신 HTML 링크 활용
                            st.markdown(f"""
                                <div class="music-card" onclick="document.getElementById('play_video_{video_id}').click();">
                                    <img src="https://i.ytimg.com/vi/{video_id}/mqdefault.jpg" alt="{title}">
                                    <div>
                                        <div class="music-card-title">{title}</div>
                                        <div class="music-card-channel">{channel} · {length}</div>
                                    </div>
                                    <button id="play_video_{video_id}" style="display:none;" onclick="
                                        fetch('/_stcore/script/set_session_state', {{
                                            method: 'POST',
                                            headers: {{'Content-Type': 'application/json'}},
                                            body: JSON.stringify({{key: 'selected_video_id', value: '{video_id}'}})
                                        }});
                                        window.location.reload();
                                    "></button>
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    st.warning("😭 검색 결과가 없습니다. 다른 검색어를 입력해 보세요.")
            except Exception as e:
                st.error(f"⚠️ 검색 중 오류가 발생했습니다: {e}")
                st.warning("유튜브 웹사이트 구조 변경으로 인해 검색 기능이 일시적으로 불안정할 수 있습니다.")
    else:
        st.warning("✨ 검색어를 입력하거나 장르/악기를 선택하고 '검색 시작' 버튼을 눌러주세요!")

# Streamlit 세션 상태를 활용하여 선택된 비디오 ID 업데이트
if 'selected_video_id' in st.session_state and st.session_state.selected_video_id:
    # 비디오 ID가 업데이트되면 메인 플레이어를 다시 그립니다.
    pass # 이미 위에서 초기화 시 사용했으므로 추가적인 그리기 없음

st.markdown("---")
st.caption("© 2026 INhee Hi-Fi Music Services - i5-11400 Optimized for Speed")