import streamlit as st

# 1. 디자인 (사용자님의 예쁜 스타일 그대로 유지)
st.set_page_config(page_title="INhee Hi-Fi", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #1a1a2e; color: white; }
    h1 { color: #00d4ff; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎵 INhee Hi-Fi 뮤직룸")

# 2. 사이드바 메뉴 (여기서 고르면 아래 'video_url'이 바뀝니다)
with st.sidebar:
    st.header("음악 카테고리")
    category = st.selectbox("음악 장르를 선택하세요", ["국내가요", "팝송", "섹소폰", "클래식"])

# 3. 핵심 로직: 선택한 장르에 따라 주소를 할당함
# 사용자님이 원하시는 영상 주소들을 여기에 하나씩 넣으시면 됩니다.
if category == "국내가요":
    video_url = "https://www.youtube.com/embed/9N9U_o7-H-k" # 예시: 김광석
elif category == "팝송":
    video_url = "https://www.youtube.com/embed/S2Cti1277AM" # 예시: 비틀즈
elif category == "섹소폰":
    video_url = "https://www.youtube.com/embed/LK0sKS6l2V4" # 사용자님이 올리신 그 영상
else:
    video_url = "https://www.youtube.com/embed/jgpJVI3t4mE" # 클래식

# 4. 화면 표시
st.subheader(f"📺 현재 [{category}] 모드로 감상 중입니다.")
st.video(video_url)

# 5. 검색창 (글자를 쓰고 엔터를 치면 안내 메시지가 뜹니다)
search_query = st.text_input("🔍 검색창에 가수 이름을 입력해 보세요")
if search_query:
    st.warning(f"'{search_query}'에 대한 자동 검색 기능은 현재 준비 중입니다. 위 메뉴를 이용해 주세요!")