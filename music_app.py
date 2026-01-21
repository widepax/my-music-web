import streamlit as st
import urllib.parse

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="INhee Hi-Fi Music Search", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stTextInput>div>div>input { background-color: #262730; color: white; border: 1px solid #00d4ff; }
    .music-card { border: 1px solid #333; padding: 10px; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🔍 INhee 나만의 유튜브 음악 검색")

# 2. 검색창 구성
search_query = st.text_input("가수나 노래 제목을 입력하세요 (예: 비틀즈, 섹소폰 재즈)", "")

if search_query:
    # 유튜브 검색 URL 생성
    encoded_query = urllib.parse.quote(search_query)
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
    
    st.subheader(f"'{search_query}'에 대한 검색 결과입니다.")
    
    # 3. 검색 결과 레이아웃 (섬네일처럼 보이기 위한 구성)
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info("💡 아래 링크를 클릭하면 유튜브 검색 결과로 바로 연결됩니다.")
        # 섬네일과 링크를 시각적으로 표시
        st.markdown(f"""
            <div style="background-color: #262730; padding: 20px; border-radius: 15px; border-left: 5px solid #ff0000;">
                <h3 style="margin: 0;">📺 유튜브에서 바로 보기</h3>
                <p style="color: #aaa;">클릭하시면 {search_query}의 최신 영상 리스트로 이동합니다.</p>
                <a href="{search_url}" target="_blank" style="background-color: #ff0000; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    유튜브 검색 결과 열기
                </a>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.write("🎹 **추천 카테고리**")
        if st.button("🎷 섹소폰 베스트"):
            st.video("https://www.youtube.com/watch?v=LK0sKS6l2V4")
        if st.button("🎸 7080 가요"):
            st.video("https://www.youtube.com/watch?v=9N9U_o7-H-k")

else:
    # 검색 전 초기 화면 (사용자님이 좋아하는 영상 섬네일 배치 가능)
    st.write("---")
    st.write("아래는 추천 영상입니다.")
    st.video("https://www.youtube.com/watch?v=LK0sKS6l2V4") # 그 섹소폰 영상