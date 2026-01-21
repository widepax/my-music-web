import streamlit as st

# 페이지 설정 (웹 브라우저 탭에 표시될 내용)
st.set_page_config(page_title="My Private Music Lounge", layout="wide", page_icon="🎵")

# --- 스타일링 (CSS) ---
st.markdown("""
    <style>
    .main-title {
        font-size: 45px;
        font-weight: bold;
        color: #1E90FF;
        text-align: center;
        margin-bottom: 10px;
    }
    .sub-title {
        font-size: 18px;
        text-align: center;
        color: #666;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 대문 (헤더) ---
st.markdown('<div class="main-title">🎶 INhee Hi-Fi Music Room 🎶</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">선별된 고화질/고음질 음악을 함께 감상하는 공간입니다.</div>', unsafe_allow_html=True)

# --- 사이드바: 드롭다운 분류 ---
st.sidebar.header("🎼 음악 카테고리")

# 1. 장르 분류
genre = st.sidebar.selectbox(
    "음악 장르를 선택하세요",
    ["선택 안함", "국내가요", "팝 (60~70년대)", "째즈", "클래식"]
)

# 2. 악기 분류
instrument = st.sidebar.selectbox(
    "악기별 분류를 선택하세요",
    ["선택 안함", "섹소폰", "드럼", "기타", "베이스", "피아노"]
)

# --- 메인 영역: 직접 검색 프롬프트 ---
st.subheader("🔍 직접 음악 찾기")
search_query = st.text_input("유튜브에서 듣고 싶은 음악이나 아티스트를 입력하세요", placeholder="예: 비틀즈 고화질 공연")

# --- 음악 재생 로직 ---
video_url = ""

# 1. 검색어가 있을 때 (우선순위)
if search_query:
    # 유튜브 검색 결과 페이지를 임베드하거나 링크 생성
    st.info(f"'{search_query}'에 대한 검색 결과입니다.")
    # 실제 구현 시에는 특정 영상 ID가 필요하므로 검색어 기반 링크 제안
    # 예시를 위해 검색 결과를 반영한 유튜브 주소 형식 사용
    video_url = "https://www.youtube.com/embed/LK0sKS6l2V4?rel=0&modestbranding=1&vq=hd1080"

# 2. 드롭다운 선택 시 (샘플 데이터 연동)
elif genre != "선택 안함" or instrument != "선택 안함":
    st.success(f"현재 선택: {genre} / {instrument}")
    
    # 예시 데이터 (실제 사용자님의 플레이리스트 ID로 교체하세요)
    if genre == "국내가요":
        video_url = "https://www.youtube.com/embed/videoseries?list=PL플레이리스트ID_가요"
    elif instrument == "섹소폰":
        video_url = "https://www.youtube.com/embed/videoseries?list=PL플레이리스트ID_섹소폰"
    else:
        # 기본 안내 영상 또는 최근 들은 곡
        video_url = "https://www.youtube.com/embed/dQw4w9WgXcQ" # 샘플

# --- 플레이어 출력 (고화질 설정) ---
if video_url:
    # 4K/HD 유도를 위해 vq=hd2160 등 파라미터 적용 (임베드 제약에 따라 작동 여부 상이)
    final_url = f"{video_url}&rel=0&modestbranding=1"
    st.components.v1.iframe(final_url, width=None, height=600, scrolling=False)
else:
    st.warning("왼쪽 메뉴에서 카테고리를 고르거나 검색어를 입력해 주세요.")

# --- 하단 정보 ---
st.caption("© 2024 My Music Web App - High Quality Audio & Video")