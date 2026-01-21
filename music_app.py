import os
import requests
import streamlit as st
from typing import List, Dict, Optional

# =============================
# 1. 앱 설정 및 스타일
# =============================
st.set_page_config(page_title="INhee Hi-Fi Music Search", layout="wide")

def load_api_key_safe() -> Optional[str]:
    """환경 변수 또는 Streamlit secrets에서 YouTube API 키를 안전하게 로드합니다."""
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        try:
            # st.secrets에 없을 경우 대비
            if "YOUTUBE_API_KEY" in st.secrets:
                key = st.secrets["YOUTUBE_API_KEY"]
        except Exception:
            pass
    return key

YOUTUBE_API_KEY = load_api_key_safe()

# API 키가 없으면 앱 실행 중단
if not YOUTUBE_API_KEY:
    st.error("🚨 YouTube API 키가 설정되지 않았습니다! 앱을 실행할 수 없습니다.")
    st.info("환경 변수나 Streamlit Cloud의 secrets에 'YOUTUBE_API_KEY'를 설정해주세요.")
    st.stop()


# 세션 상태 초기화
ss = st.session_state
if "initialized" not in ss:
    ss.results = []
    ss.next_token = None
    ss.initialized = False
    ss.last_query = "섹소폰"
    ss.current_order = "relevance"
    ss.user_input = ""

def custom_css(ui_scale):
    """앱에 적용할 사용자 정의 CSS 스타일을 반환합니다."""
    st.markdown(f"""
        <style>
            :root {{ --ui-scale: {ui_scale}; }}
            html, .stApp {{ 
                font-size: calc(16px * var(--ui-scale)); 
                background: #070b15; 
                color:#e6f1ff; 
            }}
            .music-card-link {{
                display: block;
                text-decoration: none;
                color: inherit;
                border-radius: 12px;
                overflow: hidden;
                position: relative;
                border: 1px solid rgba(0, 229, 255, 0.2);
                background: rgba(255, 255, 255, 0.05);
                transition: all 0.2s ease;
                margin-bottom: 20px;
            }}
            .music-card-link:hover {{
                border-color: #00e5ff;
                background: rgba(255, 255, 255, 0.1);
                transform: translateY(-5px);
            }}
            .view-badge {{
                position: absolute; top: 8px; right: 8px;
                background: rgba(0, 0, 0, 0.8); color: #00e5ff;
                padding: 2px 8px; border-radius: 4px;
                font-size: 0.75rem; font-weight: bold;
            }}
            .thumb-img {{ 
                width: 100%; 
                aspect-ratio: 16 / 9; 
                object-fit: cover; 
                display: block; 
            }}
            .v-title {{
                padding: 12px 12px 2px 12px; font-size: 0.9rem; font-weight: 600; color: #eaf7ff;
                display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
                overflow: hidden; height: 2.4em; line-height: 1.2;
            }}
            .v-channel {{ 
                padding: 0 12px 12px 12px; 
                color: #9dd5ff; 
                font-size: 0.75rem; 
            }}
            .stButton>button {{
                border-radius: 20px;
                border: 1px solid #4CAF50;
                background-color: #4CAF50;
                color: white;
                padding: 10px 24px;
                cursor: pointer;
                font-size: 16px;
            }}
            .stButton>button:hover {{
                background-color: #45a049;
            }}
        </style>
    """, unsafe_allow_html=True)

# =============================
# 2. 사이드바 UI 및 검색 설정
# =============================
with st.sidebar:
    st.header("🔎 검색 설정")
    ui_scale = st.slider("👁 글자/UI 배율", 0.9, 1.6, 1.20, 0.05)
    st.markdown("---")
    
    genre = st.selectbox("장르 선택", ["(선택 없음)", "국내가요", "팝송", "섹소폰", "클래식", "MR/노래방", "MR (TJ/KY 제외)"], index=3)
    instrument = st.selectbox("악기 선택", ["(선택 없음)", "섹소폰", "드럼", "기타", "베이스"], index=0)
    direct = st.text_input("직접 입력", placeholder="곡 제목을 정확히 입력하세요")
    
    order_map = {"관련도순": "relevance", "조회수순": "viewCount", "최신순": "date"}
    order_label = st.selectbox("정렬 기준", list(order_map.keys()), index=0)
    
    grid_cols = st.slider("한 줄 카드 수", 2, 6, 4)
    batch = st.slider("검색 개수", 12, 60, 24, step=4)
    
    st.write("")
    do_search = st.button("🚀 검색 실행", type="primary", use_container_width=True)

# CSS 스타일 적용
custom_css(ui_scale)

# =============================
# 3. 핵심 로직 함수
# =============================
def search_youtube(query: str, order: str, limit: int, page_token: Optional[str] = None) -> (List[Dict], Optional[str]):
    """YouTube API를 호출하여 동영상 정보를 가져옵니다."""
    if not YOUTUBE_API_KEY:
        st.error("YouTube API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
        return [], None
    try:
        # 1. 검색 API로 Video ID 목록 확보
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            "part": "snippet", "q": query, "type": "video", 
            "maxResults": limit, "order": order, "key": YOUTUBE_API_KEY, "pageToken": page_token
        }
        res = requests.get(search_url, params=search_params, timeout=5)
        res.raise_for_status()
        search_data = res.json()
        
        video_ids = [item['id']['videoId'] for item in search_data.get("items", [])]
        if not video_ids:
            return [], None

        # 2. Videos API로 상세 정보(조회수 등) 확보
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            "part": "snippet,statistics", "id": ",".join(video_ids), "key": YOUTUBE_API_KEY
        }
        v_res = requests.get(videos_url, params=videos_params, timeout=5)
        v_res.raise_for_status()
        videos_data = v_res.json()
        
        results = []
        for item in videos_data.get("items", []):
            count = int(item['statistics'].get('viewCount', 0))
            if count >= 10000:
                views = f"{count // 10000}만"
            elif count >= 1000:
                views = f"{count / 1000:.1f}천"
            else:
                views = str(count)
            
            results.append({
                "id": item['id'],
                "title": item['snippet']['title'],
                "channel": item['snippet']['channelTitle'],
                "thumb": item['snippet']['thumbnails']['medium']['url'],
                "views": views
            })
        return results, search_data.get("nextPageToken")

    except requests.exceptions.RequestException as e:
        st.error(f"API 요청 중 오류가 발생했습니다: {e}")
        return [], None
    except (KeyError, IndexError) as e:
        st.error(f"API 응답 데이터를 처리하는 중 오류가 발생했습니다: {e}")
        return [], None

def build_query(g: str, i: str, d: str) -> str:
    """선택된 옵션을 바탕으로 YouTube 검색어를 조합합니다."""
    d_clean = d.strip()
    exclude_str = "-TJ -금영 -KY -Media -KaraokeKpop"
    
    if g == "MR (TJ/KY 제외)":
        base = f'"{d_clean}"' if d_clean else "MR 반주"
        return f'{base} (노래방 OR MR OR Instrument OR Karaoke) {exclude_str}'
    
    if g == "MR/노래방":
        base = f'"{d_clean}"' if d_clean else "노래방"
        return f'{base} (노래방 OR MR OR Instrument OR Karaoke)'
        
    parts = [f'"{d_clean}"'] if d_clean else []
    if g != "(선택 없음)": parts.append(g)
    if i != "(선택 없음)": parts.append(i)
    return " ".join(parts).strip()

def dedupe_by_video_id(results: List[Dict]) -> List[Dict]:
    """Video ID를 기준으로 중복된 결과를 제거합니다."""
    seen = set()
    deduped = []
    for item in results:
        if item['id'] not in seen:
            seen.add(item['id'])
            deduped.append(item)
    return deduped

def run_search(query: str, limit: int, order: str):
    """검색을 실행하고 세션 상태를 업데이트합니다."""
    with st.spinner(f"'{query}' 검색 중..."):
        results, next_token = search_youtube(query, order, limit)
        ss.results = results if results else []
        ss.next_token = next_token
        ss.last_query = query
        ss.current_order = order

# =============================
# 4. 앱 동작 및 화면 렌더링
# =============================
# 안전하게 query_params 가져오기
query_params = getattr(st, 'query_params', {})

# -- 검색 실행 --
if do_search:
    q = build_query(genre, instrument, direct)
    if not q:
        st.warning("검색어를 입력하거나 장르/악기를 선택한 뒤 검색을 눌러주세요.")
    else:
        run_search(q, batch, order_map[order_label])
        # 검색 시 재생 중인 비디오가 있다면 URL 파라미터에서 제거
        if "v" in query_params:
            # st.query_params.clear() 대신 st.rerun()을 사용하거나,
            # 혹은 새로운 URL로 리디렉션하는 방식을 고려해야 합니다.
            # 지금은 st.rerun()으로 상태를 갱신합니다.
            st.rerun()

# -- 초기 로딩 시 기본 검색 --
if not ss.initialized:
    run_search(ss.last_query, 24, "relevance")
    ss.initialized = True

# -- 동영상 재생기 --
current_video_id = query_params.get("v")
if current_video_id:
    st.header("🎵 현재 재생 중인 곡")
    st.video(f"https://www.youtube.com/watch?v={current_video_id}")
    st.markdown("---")

# -- 검색 결과 표시 --
st.subheader("🎼 검색 결과")
if not ss.results:
    st.warning("검색 결과가 없습니다. 다른 키워드로 시도해 보세요.")
else:
    ss.results = dedupe_by_video_id(ss.results)
    
    ORDER_INV_MAP = {v: k for k, v in order_map.items()}
    order_display = ORDER_INV_MAP.get(ss.current_order, ss.current_order)
    st.caption(f"🔎 ‘{ss.last_query}’ — {len(ss.results)}개 로드됨 · 정렬: {order_display}")

    # 그리드 레이아웃으로 결과 카드 표시
    cols = st.columns(grid_cols)
    for i, item in enumerate(ss.results):
        col = cols[i % grid_cols]
        thumb_url = item.get("thumb", f"https://i.ytimg.com/vi/{item['id']}/mqdefault.jpg")

        card_html = f"""
        <a href="?v={item['id']}" target="_self" class="music-card-link">
            <div style="position: relative;">
                <img src="{thumb_url}" class="thumb-img">
                <span class="view-badge">{item['views']}</span>
            </div>
            <div class="v-title">{item.get("title", "")}</div>
            <div class="v-channel">{item.get("channel", "")}</div>
        </a>
        """
        col.markdown(card_html, unsafe_allow_html=True)

    st.markdown("---")

    # -- '더 보기' 버튼 --
    if ss.next_token:
        if st.button("＋ 결과 더 보기", use_container_width=True):
            with st.spinner("결과를 더 가져오는 중..."):
                new_res, new_token = search_youtube(
                    ss.last_query,
                    ss.current_order,
                    batch,
                    page_token=ss.next_token
                )
                ss.results.extend(new_res)
                ss.next_token = new_token
                st.rerun()