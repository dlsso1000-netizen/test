# Google Trends 실시간 검색어 스크래퍼

Google Trends의 봇 탐지를 우회하여 실시간 급상승 검색어를 가져오는 Streamlit 앱입니다.

## 주요 기능

- **실시간 급상승 검색어**: Google Trends 한국의 실시간 인기 검색어 수집
- **연관 키워드 채굴**: 유튜브 자동완성 API를 통한 연관 검색어 발굴
- **트렌드 비교**: pytrends를 활용한 키워드별 검색량 추이 비교

## 봇 탐지 우회 방법

이 프로젝트는 3가지 방법을 순차적으로 시도합니다:

1. **undetected-chromedriver** (가장 효과적)
   - Chrome의 자동화 탐지를 우회하도록 설계된 라이브러리
   - WebDriver 플래그를 자동으로 패치

2. **selenium-stealth**
   - 브라우저 지문(fingerprint)을 일반 사용자처럼 위장
   - JavaScript 속성 수정으로 탐지 회피

3. **강화된 Selenium 설정**
   - `navigator.webdriver` 속성 숨기기
   - 자동화 관련 Chrome 플래그 비활성화

## 설치 방법

### 로컬 설치

```bash
# 1. 저장소 클론
git clone <repository-url>
cd test

# 2. 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. 종속성 설치
pip install -r requirements.txt

# 4. Chrome 브라우저 설치 필요
# Ubuntu: sudo apt install google-chrome-stable
# Mac: brew install --cask google-chrome

# 5. 실행
streamlit run app.py
```

### Docker 사용

```bash
# Docker Compose로 실행
docker-compose up -d

# 또는 직접 빌드
docker build -t trend-analyzer .
docker run -p 8501:8501 --shm-size=2g trend-analyzer
```

## 사용법

1. 브라우저에서 `http://localhost:8501` 접속
2. **실시간 급상승** 탭에서 "트렌드 가져오기" 클릭
3. 스크래핑 방법 선택 가능 (자동/수동)

## 트러블슈팅

### Chrome 관련 오류

```bash
# ChromeDriver 수동 설치
pip install webdriver-manager

# 또는 Chrome 버전 확인 후 호환 드라이버 설치
google-chrome --version
```

### 봇 탐지로 차단되는 경우

1. VPN 사용 시도
2. `--headless` 옵션 제거하고 GUI 모드로 테스트
3. 요청 간격 늘리기 (time.sleep 값 증가)

### 메모리 부족 (Docker)

```bash
# shm_size 증가
docker run -p 8501:8501 --shm-size=4g trend-analyzer
```

## 기술 스택

- Python 3.11+
- Streamlit
- Selenium / undetected-chromedriver / selenium-stealth
- BeautifulSoup4
- pytrends
- pandas

## 라이선스

MIT License
