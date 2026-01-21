
import json
import re
import requests
import urllib.parse
from typing import List, Dict, Tuple, Optional

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "CONSENT=PENDING+999;"
}

def _extract_json_after_marker(html: str, marker: str) -> Optional[str]:
    """
    html 문자열에서 'marker' 다음에 나오는 JSON 객체(중괄호 매칭)를 안전하게 잘라서 반환.
    정규식 사용 안 함: 중괄호 스택으로 밸런싱 처리.
    """
    start = html.find(marker)
    if start == -1:
        return None
    # marker 이후 첫 '{' 찾기
    brace_start = html.find("{", start)
    if brace_start == -1:
        return None

    depth = 0
    i = brace_start
    while i < len(html):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                # 닫히는 지점 포함 슬라이스
                return html[brace_start:i+1]
        i += 1
    return None  # 매칭 실패

@st.cache_data(show_spinner=False)
def scrape_youtube_search(query: str, max_items: int = 50) -> Tuple[List[Dict], Optional[int], Optional[int], Optional[str]]:
    """
    유튜브 검색 페이지에서 ytInitialData JSON을 안전 추출 → videoRenderer만 수집.
    반환: (results, http_status, html_length, error_message)
    """
    q = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={q}&hl=ko&gl=KR"

    try:
        r = requests.get(url, headers=COMMON_HEADERS, timeout=15)
        status = r.status_code
        html = r.text

        # 1차 시도: "ytInitialData" 마커
        raw_json = _extract_json_after_marker(html, "ytInitialData")
        # 2차 백업: "ytInitialData ="
        if not raw_json:
            raw_json = _extract_json_after_marker(html, "var ytInitialData =")

        if not raw_json:
            return [], status, len(html), "ytInitialData JSON 블롭을 찾지 못했습니다."

        try:
            data = json.loads(raw_json)
        except Exception as je:
            # 경우에 따라 끝에 ';' 등이 붙는 경우 방어
            raw_json_trim = raw_json.strip().rstrip(";")
            try:
                data = json.loads(raw_json_trim)
            except Exception as je2:
                return [], status, len(html), f"JSON 파싱 실패: {je2}"

        # videoRenderer까지 내려가며 수집
        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "videoRenderer":
                        yield v
                    else:
                        yield from walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from walk(v)

        results: List[Dict] = []
        for vr in walk(data):
            vid = vr.get("videoId")
            title_runs = (((vr.get("title") or {}).get("runs")) or [{"text": ""}])
            title = title_runs[0].get("text", "")
            owner_runs = (((vr.get("ownerText") or {}).get("runs")) or [{"text": ""}])
            channel = owner_runs[0].get("text", "")
            length = ((vr.get("lengthText") or {}).get("simpleText")) or "LIVE/SHORT"
            if vid and title:
                results.append({
                    "video_id": vid,
                    "title": title,
                    "channel": channel,
                    "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                    "duration": length
                })
            if len(results) >= max_items:
                break

        return results, status, len(html), None

    except Exception as e:
        return [], None, None, str(e)
