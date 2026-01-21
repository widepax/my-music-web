import streamlit as st

# 1. 페이지 설정 및 디자인 (사용자님의 스타일 유지/보강)
st.set_page_config(page_title="INhee Hi-Fi Music Room", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #1a1a2e; color: #ffffff; }
    .stSelectbox label, .stTextInput label { color: #00d4ff !important; font-weight: bold; }
    h1 { color: #00d4ff; text-align: center; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎵 INhee Hi-Fi 뮤직룸")

# 2. 임시 데이터베이스 (나중에 엑셀과 연결될 부분입니다)
# 실제 유튜브 'ID' (v= 뒤의 글자들)를 넣어야 정상 재생됩니다.
music_data = {
    "국내가요": "https://www.youtube.com/embed/9N9U_o7-H-k", # 예시: 김광석
    "팝송": "https://www.youtube.com/embed/S2Cti1277AM",    # 예시: 비틀즈
    "섹소폰": "https://www.youtube.com/embed/modestb4N2M",  # 섹소폰 연주
    "클래식": "https://www.youtube.com/embed/jgpJVI3t4mE"
}

# 3. 사이드바 구성 (카테고리 선택)
with st.sidebar:
    st.header("📂 음악 카테고리")
    category = st.selectbox("장르를 선택하세요", list(music_data.keys()))
    st.write("---")
    st.info("M365 엑셀 리스트와 연동 준비 완료")

# 4. 메인 영역: 검색 및 재생
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔍 직접 음악 찾기")
    search_query = st.text_input("가수나 제목을 입력하고 엔터를 치세요", placeholder="예: 비틀즈")

with col2:
    st.subheader("📻 현재 재생 중")
    # 논리 1: 검색어가 있으면 검색어 우선, 없으면 카테고리 선택곡 재생
    if search_query:
        st.write(f"'{search_query}' 검색 결과 테마를 재생합니다.")
        # 실제로는 유튜브 검색 API가 필요하지만, 우선 샘플 영상을 띄웁니다.
        video_url = "https://www.youtube.com/embed/S2Cti1277AM" 
    else:
        st.write(f"선택하신 [{category}] 음악입니다.")
        video_url = music_data[category]

    # 유튜브 영상 출력 (디자인에 맞춰 자동 크기 조절)
    st.video(video_url)

st.write("---")
st.caption("© 2026 INhee Hi-Fi Music Services - i5-11400 Optimized")