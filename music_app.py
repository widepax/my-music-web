import os
import requests
import streamlit as st

# 1. 기본 설정
st.set_page_config(page_title="INhee Music Search", layout="wide")

def load_api_key():
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        try: key = st.secrets["YOUTUBE_API_KEY"]
        except: pass
    return key

API_KEY = load_api_key()

# 2. 세션 상태 관리 (로직 유지)
ss = st.session_state
if "selected_video_id" not in ss: ss.selected_video_id = "LK0sKS6l2V4"
if "results" not in ss: ss.results = []
if "last_query" not in ss: ss.last_query = "섹소폰"

# 3. 사이드바 (기존 UI 유지)
with st.sidebar:
    st.header("🔎 검색 설정")
    ui_scale = st.slider("👁 배율", 0.9, 1.6, 1.2)
    genre = st.selectbox("장르", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식", "MR/노래방"], index=3)
    instrument = st.selectbox("악기", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=1)
    direct = st.text_input("직접 입력")
    grid_cols = st.slider("가로 카드 수", 2, 6, 4)
    do_search = st.button("✅ 검색 실행 (OK)")

# 4. CSS: 에러의 원인이 된 예외 처리 문구를 모두 삭제하고 클릭 영역을 최상단으로 고정
st.markdown(f"""
<style>
    html, .stApp {{ font-size: calc(16px * {ui_scale}); background: #070b15; color:#e6f1ff; }}
    
    /* 카드 컨테이너 */
    .c-box {{ position: relative; width: 100%; margin-bottom: 20px; }}

    /* 디자인 레이어: 클릭이 통과되도록 설정 (pointer-events: none) */
    .c-design {{
        position: relative; background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,229,255,0.2); border-radius: 12px;
        overflow: hidden; pointer-events: none; z-index: 1;
    }}

    /* 조회수 배지 */
    .v-badge {{
        position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.8);
        color: #00e5ff; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;
    }}

    /* 실제 버튼: 디자인 위에 투명하게 덮어 모든 클릭을 가로챔 */
    .c-box div[data-testid="stButton"] > button {{
        position: absolute !important; top: 0 !important; left: 0 !important;
        width: 100% !important; height: 100% !important;
        background: transparent !important; color: transparent !important;
        border: none !important; z-index: 10 !important; cursor: pointer !important;
    }}
</style>
""", unsafe_allow_html=True)

# 5. 검색 로직 (조회수 포함)
def get_search(q):
    if not API_KEY: return []
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={q}&type=video&maxResults=24&key={API_KEY}"
        res = requests.get(url).json()
        vids = [it['id']['videoId'] for it in res.get("items", [])]
        v_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={','.join(vids)}&key={API_KEY}"
        v_res = requests.get(v_url).json()
        
        data = []
        for it in v_res.get("items", []):
            vc = int(it['statistics'].get('viewCount', 0))
            v_str = f"{vc//10000}만" if vc >= 10000 else f"{vc}"
            data.append({
                "id": it['id'], "title": it['snippet']['title'],
                "thumb": it['snippet']['thumbnails']['medium']['url'], "views": v_str
            })
        return data
    except: return []

if do_search or not ss.results:
    query = f"{direct} {genre} {instrument}".strip()
    ss.last_query = query if query else "섹소폰"
    ss.results = get_search(ss.last_query)

# 6. 메인 화면 출력
st.title("🎵 INhee Hi-Fi Music Search")
st.video(f"https://www.youtube.com/watch?v={ss.selected_video_id}")

if ss.results:
    st.subheader(f"🎼 '{ss.last_query}' 검색 결과")
    for i in range(0, len(ss.results), grid_cols):
        cols = st.columns(grid_cols)
        for j, col in enumerate(cols):
            if i + j < len(ss.results):
                item = ss.results[i + j]
                with col:
                    st.markdown(f"""
                    <div class="c-box">
                        <div class="c-design">
                            <div class="v-badge">👁 {item['views']}</div>
                            <img src="{item['thumb']}" style="width:100%; aspect-ratio:16/9; object-fit:cover;">
                            <div style="padding:10px; font-size:0.85rem; height:3em; overflow:hidden;">{item['title']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    # 카드 전체를 덮는 투명 버튼
                    if st.button("", key=f"v_{item['id']}"):
                        ss.selected_video_id = item['id']
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)