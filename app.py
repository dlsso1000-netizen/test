import streamlit as st
import pandas as pd
import time
import warnings
import json
import re
from typing import Tuple, List, Optional

# 경고 무시
warnings.filterwarnings("ignore")

# 페이지 설정
st.set_page_config(page_title="유튜브 트렌드 분석기", layout="wide")


# ==========================================
# [함수 1] 유튜브 연관 검색어
# ==========================================
def get_youtube_suggestions(keyword: str) -> List[str]:
    """유튜브 자동완성 API를 통해 연관 검색어 가져오기"""
    import requests
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"http://suggestqueries.google.com/complete/search?client=youtube&ds=yt&client=firefox&q={keyword}"
        response = requests.get(url, headers=headers, timeout=5)
        return response.json()[1]
    except Exception:
        return []


# ==========================================
# [함수 2] 구글 트렌드 히트맵 (pytrends)
# ==========================================
def get_trend_data(kw_list: List[str]) -> Optional[pd.DataFrame]:
    """pytrends를 사용하여 키워드 트렌드 데이터 가져오기"""
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='ko-KR', tz=540)
        pytrends.build_payload(kw_list, cat=0, timeframe='today 12-m', geo='KR', gprop='youtube')
        data = pytrends.interest_over_time()
        if not data.empty:
            return data.drop(columns=['isPartial'])
        return None
    except Exception:
        return None


# ==========================================
# [방법 1] undetected-chromedriver 사용 (가장 효과적)
# ==========================================
def get_trends_with_undetected_chrome() -> Tuple[Optional[pd.DataFrame], str]:
    """
    undetected-chromedriver를 사용하여 Google Trends 실시간 검색어 스크래핑
    봇 탐지를 우회하는 가장 효과적인 방법
    """
    driver = None
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # undetected-chromedriver 옵션 설정
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")  # 새로운 headless 모드
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=ko-KR")

        # 브라우저 시작
        driver = uc.Chrome(options=options, use_subprocess=True)

        # Google Trends 실시간 페이지 접속
        url = "https://trends.google.co.kr/trending?geo=KR"
        driver.get(url)

        # 페이지 로딩 대기 (최대 15초)
        time.sleep(5)

        # 트렌드 데이터 추출
        trends = extract_trends_from_page(driver)

        driver.quit()

        if trends:
            return pd.DataFrame(trends), "성공: undetected-chromedriver로 데이터를 가져왔습니다."
        else:
            raise Exception("트렌드 데이터를 찾을 수 없음")

    except Exception as e:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return None, f"undetected-chromedriver 실패: {str(e)}"


# ==========================================
# [방법 2] selenium-stealth 사용
# ==========================================
def get_trends_with_stealth() -> Tuple[Optional[pd.DataFrame], str]:
    """
    selenium-stealth를 사용하여 봇 탐지 우회
    """
    driver = None
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium_stealth import stealth

        # Chrome 옵션 설정
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # 브라우저 시작
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        # selenium-stealth 적용
        stealth(driver,
            languages=["ko-KR", "ko"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        # Google Trends 접속
        url = "https://trends.google.co.kr/trending?geo=KR"
        driver.get(url)
        time.sleep(5)

        # 트렌드 데이터 추출
        trends = extract_trends_from_page(driver)

        driver.quit()

        if trends:
            return pd.DataFrame(trends), "성공: selenium-stealth로 데이터를 가져왔습니다."
        else:
            raise Exception("트렌드 데이터를 찾을 수 없음")

    except Exception as e:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return None, f"selenium-stealth 실패: {str(e)}"


# ==========================================
# [방법 3] 일반 Selenium + 강화된 설정
# ==========================================
def get_trends_with_regular_selenium() -> Tuple[Optional[pd.DataFrame], str]:
    """
    일반 Selenium에 봇 탐지 회피 설정 추가
    """
    driver = None
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        # navigator.webdriver 숨기기
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        url = "https://trends.google.co.kr/trending?geo=KR"
        driver.get(url)
        time.sleep(5)

        trends = extract_trends_from_page(driver)

        driver.quit()

        if trends:
            return pd.DataFrame(trends), "성공: 일반 Selenium으로 데이터를 가져왔습니다."
        else:
            raise Exception("트렌드 데이터를 찾을 수 없음")

    except Exception as e:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return None, f"일반 Selenium 실패: {str(e)}"


# ==========================================
# [공통 함수] 페이지에서 트렌드 데이터 추출
# ==========================================
def extract_trends_from_page(driver) -> List[dict]:
    """
    Google Trends 페이지에서 실시간 검색어 데이터 추출
    """
    from selenium.webdriver.common.by import By
    from bs4 import BeautifulSoup

    trends = []

    try:
        # 페이지 소스 가져오기
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # 방법 1: 테이블 행에서 추출 시도
        # Google Trends는 동적으로 로드되므로 여러 선택자 시도

        # 트렌드 항목 찾기 (다양한 선택자 시도)
        selectors = [
            'div[class*="feed-item"]',
            'tr[class*="enOdEe"]',
            'div[class*="mZ3RIc"]',
            'table tbody tr',
            '[data-trending-item]',
        ]

        items = []
        for selector in selectors:
            try:
                items = driver.find_elements(By.CSS_SELECTOR, selector)
                if items and len(items) > 0:
                    break
            except Exception:
                continue

        # 항목에서 텍스트 추출
        if items:
            for i, item in enumerate(items[:20]):  # 최대 20개
                try:
                    text = item.text.strip()
                    if text:
                        lines = text.split('\n')
                        keyword = lines[0] if lines else text

                        # 검색량 정보 추출 시도
                        search_volume = ""
                        for line in lines:
                            if '+' in line or '만' in line or '천' in line:
                                search_volume = line
                                break

                        trends.append({
                            "순위": i + 1,
                            "급상승 검색어": keyword,
                            "검색량": search_volume if search_volume else "N/A",
                            "관련 뉴스": lines[1] if len(lines) > 1 else "관련 뉴스 없음"
                        })
                except Exception:
                    continue

        # 방법 2: JavaScript로 데이터 추출 시도
        if not trends:
            try:
                # 페이지의 JSON 데이터 찾기
                script_data = driver.execute_script("""
                    const scripts = document.querySelectorAll('script');
                    for (let script of scripts) {
                        if (script.textContent && script.textContent.includes('trendingSearches')) {
                            return script.textContent;
                        }
                    }
                    return null;
                """)

                if script_data:
                    # JSON 파싱 시도
                    json_match = re.search(r'\[.*"trendingSearches".*\]', script_data)
                    if json_match:
                        data = json.loads(json_match.group())
                        # 데이터 처리
                        pass
            except Exception:
                pass

        # 방법 3: 테이블 직접 파싱
        if not trends:
            try:
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for i, row in enumerate(rows):
                        cells = row.find_all(['td', 'th'])
                        if cells:
                            text = cells[0].get_text(strip=True)
                            if text and len(text) > 1:
                                trends.append({
                                    "순위": i + 1,
                                    "급상승 검색어": text,
                                    "검색량": cells[1].get_text(strip=True) if len(cells) > 1 else "N/A",
                                    "관련 뉴스": "관련 뉴스 없음"
                                })
            except Exception:
                pass

    except Exception as e:
        print(f"추출 오류: {e}")

    return trends


# ==========================================
# [메인 함수] 여러 방법 순차 시도
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def get_realtime_trends_smart() -> Tuple[pd.DataFrame, str]:
    """
    여러 방법을 순차적으로 시도하여 실시간 트렌드 가져오기
    1. undetected-chromedriver (가장 효과적)
    2. selenium-stealth
    3. 일반 Selenium + 강화 설정
    4. 폴백 데이터
    """
    methods = [
        ("undetected-chromedriver", get_trends_with_undetected_chrome),
        ("selenium-stealth", get_trends_with_stealth),
        ("일반 Selenium", get_trends_with_regular_selenium),
    ]

    errors = []

    for method_name, method_func in methods:
        try:
            df, msg = method_func()
            if df is not None and not df.empty:
                return df, msg
            errors.append(f"{method_name}: {msg}")
        except Exception as e:
            errors.append(f"{method_name}: {str(e)}")

    # 모든 방법 실패 시 폴백 데이터
    fallback_data = [
        {"순위": 1, "급상승 검색어": "손흥민", "검색량": "1만+", "관련 뉴스": "손흥민 리그 10호골 달성"},
        {"순위": 2, "급상승 검색어": "날씨", "검색량": "5천+", "관련 뉴스": "내일 전국 비 소식"},
        {"순위": 3, "급상승 검색어": "삼성전자", "검색량": "2천+", "관련 뉴스": "삼성전자 주가 분석"},
        {"순위": 4, "급상승 검색어": "비트코인", "검색량": "1천+", "관련 뉴스": "암호화폐 시장 동향"},
        {"순위": 5, "급상승 검색어": "로또 당첨번호", "검색량": "500+", "관련 뉴스": "이번주 로또 1등 당첨 지역"},
        {"순위": 6, "급상승 검색어": "아스널 vs 리버풀", "검색량": "1만+", "관련 뉴스": "프리미어리그 빅매치"},
        {"순위": 7, "급상승 검색어": "레알마드리드", "검색량": "500+", "관련 뉴스": "라리가 경기 결과"},
        {"순위": 8, "급상승 검색어": "PSG", "검색량": "500+", "관련 뉴스": "이강인 출전"},
        {"순위": 9, "급상승 검색어": "신영대", "검색량": "5천+", "관련 뉴스": "정치 뉴스"},
        {"순위": 10, "급상승 검색어": "아이스", "검색량": "2천+", "관련 뉴스": "관련 뉴스 없음"},
    ]

    error_summary = "\n".join(errors)
    return pd.DataFrame(fallback_data), f"모든 방법 실패. 예시 데이터를 표시합니다.\n\n시도한 방법들:\n{error_summary}"


# ==========================================
# [메인 화면 UI]
# ==========================================
st.title("유튜브 트렌드 분석기 (Enhanced)")
st.markdown("""
**개선된 봇 탐지 우회 기능:**
- `undetected-chromedriver`: 가장 효과적인 봇 탐지 우회
- `selenium-stealth`: 브라우저 지문 위장
- 강화된 Selenium 설정: 자동화 탐지 비활성화
""")

tab1, tab2, tab3 = st.tabs(["실시간 급상승", "연관 키워드 채굴", "트렌드 히트맵"])

# [탭 1] 실시간 트렌드
with tab1:
    st.header("대한민국 실시간 급상승 트렌드")

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("캐시 초기화", key="clear_cache"):
            st.cache_data.clear()
            st.rerun()

    with col2:
        method_choice = st.selectbox(
            "스크래핑 방법",
            ["자동 (순차 시도)", "undetected-chrome", "selenium-stealth", "일반 selenium"],
            key="method_select"
        )

    if st.button("트렌드 가져오기", type="primary", key="fetch_trends"):
        with st.spinner("Google Trends에서 데이터를 가져오는 중..."):

            if method_choice == "자동 (순차 시도)":
                df, msg = get_realtime_trends_smart()
            elif method_choice == "undetected-chrome":
                df, msg = get_trends_with_undetected_chrome()
                if df is None:
                    df = pd.DataFrame()
            elif method_choice == "selenium-stealth":
                df, msg = get_trends_with_stealth()
                if df is None:
                    df = pd.DataFrame()
            else:
                df, msg = get_trends_with_regular_selenium()
                if df is None:
                    df = pd.DataFrame()

            # 결과 표시
            if "성공" in msg:
                st.success(msg)
            else:
                st.warning(msg)

            if df is not None and not df.empty:
                st.dataframe(
                    df.set_index("순위"),
                    use_container_width=True,
                    height=600
                )
            else:
                st.error("데이터를 가져올 수 없습니다.")

# [탭 2] 연관 키워드
with tab2:
    st.header("유튜브 연관 검색어")
    col1, col2 = st.columns([3, 1])
    with col1:
        seed = st.text_input("검색어 입력", key="mining")
    with col2:
        btn = st.button("채굴 시작", use_container_width=True)

    if btn and seed:
        st.divider()
        with st.spinner("연관 검색어 검색 중..."):
            res = get_youtube_suggestions(seed)
        if res:
            st.success(f"{len(res)}개 발견!")
            df = pd.DataFrame(res, columns=["연관 검색어"])
            df.index = df.index + 1
            st.dataframe(df, use_container_width=True)
            st.text_area("복사하기", ", ".join(res))
        else:
            st.warning("결과 없음")

# [탭 3] 히트맵
with tab3:
    st.header("검색량 트렌드 비교")
    txt = st.text_input("비교할 단어 (쉼표로 구분)", "아이폰, 갤럭시", key="heatmap_input")

    if st.button("분석 실행", key="analyze_trends"):
        if txt:
            kw = [k.strip() for k in txt.split(',') if k.strip()]
            if len(kw) > 5:
                st.warning("최대 5개 키워드만 비교 가능합니다.")
                kw = kw[:5]

            with st.spinner("트렌드 데이터 분석 중..."):
                d = get_trend_data(kw)
                if d is not None:
                    d.index = d.index.strftime("%Y-%m-%d")
                    st.line_chart(d)
                    st.dataframe(d.tail(10))
                else:
                    st.error("데이터를 가져올 수 없습니다. 나중에 다시 시도해주세요.")


# ==========================================
# 사이드바 정보
# ==========================================
with st.sidebar:
    st.header("사용 방법")
    st.markdown("""
    **실시간 급상승 탭:**
    - Google Trends 한국의 실시간 검색어를 가져옵니다
    - 봇 탐지 우회를 위해 여러 방법을 순차적으로 시도합니다

    **연관 키워드 채굴 탭:**
    - 유튜브 자동완성 API를 통해 연관 검색어를 찾습니다

    **트렌드 히트맵 탭:**
    - pytrends를 사용하여 키워드별 검색량 추이를 비교합니다
    """)

    st.divider()

    st.header("기술 스택")
    st.markdown("""
    - `undetected-chromedriver`: 봇 탐지 우회
    - `selenium-stealth`: 브라우저 지문 위장
    - `pytrends`: Google Trends API
    - `streamlit`: 웹 인터페이스
    """)
