# 📊 종합사용툴 v2.0

> YouTube Data API v3 + Google Gemini AI 기반 **글로벌 영상 분석 대시보드**.
> 국가별 TOP 100 · 채널 심층 분석 · AI 트렌드 요약 · 수익 계산 · 채널 비교를 한 번에.

참고 사이트: [Playboard](https://playboard.co) · [Vling](https://vling.net) · [NoxInfluencer](https://kr.noxinfluencer.com)

![version](https://img.shields.io/badge/version-2.0.0-7c5cff) ![node](https://img.shields.io/badge/node-%3E%3D18-339933) ![license](https://img.shields.io/badge/license-MIT-blue)

---

## ✨ 주요 기능

| 메뉴 | 설명 |
|---|---|
| 📊 **TOP 100 랭킹** | 12개국 · 17개 카테고리 · 조회수/좋아요/댓글/최신순 정렬 |
| 🔍 **검색** | 영상/채널 검색 + 관련성/조회수/최신 정렬 |
| 📺 **채널 분석** | 프로필 · KPI · 최근 영상 20개 · 히스토리 차트 · AI 분석 |
| ⚖️ **채널 비교** | 최대 5개 채널 지표 비교 + Gemini AI 비교 리포트 |
| 💰 **수익 계산기** | CPM · 월 업로드 수 가정으로 월 예상 수익 (3단계 추정) |
| 🤖 **AI 분석** | Gemini로 트렌드 요약 · 제목 10개 추천 · 채널 리포트 |

추가 기능:
- ⚡ **다중 API 키 로테이션** — 할당량 소진 시 자동 전환
- 💾 **SQLite 히스토리 누적** — 조회할 때마다 구독자/조회수 변화 기록
- 🧊 **캐시 레이어** — 유닛 절감 (카테고리 24시간, 인기영상 30분)
- 📦 **일일 크롤 잡** — `npm run crawl` 로 주요 국가 TOP 100 자동 수집

---

## 🚀 빠른 시작

```bash
# 1) 저장소 클론
git clone https://github.com/dlsso1000-netizen/test.git
cd test
git pull origin main

# 2) 의존성 설치
npm install

# 3) 환경변수 설정
cp .env.example .env
# .env 파일에 YOUTUBE_API_KEY=AIzaSy... 입력 (필수)
# (선택) GEMINI_API_KEY=AIzaSy... 입력

# 4) 실행
npm start
# → http://localhost:3000 접속
```

---

## 🔑 API 키 발급

### YouTube Data API v3 (필수)
1. https://console.cloud.google.com/apis/library/youtube.googleapis.com 접속
2. 프로젝트 생성 → API 사용 설정 → 사용자 인증 정보 → API 키 생성
3. (권장) 보안 제한: 애플리케이션 제한 · API 제한에서 YouTube Data API v3만 허용
4. 기본 할당량: **10,000 유닛/일** (매일 PT 00:00 = KST 17:00 리셋)

### Google Gemini API (선택)
1. https://aistudio.google.com/app/apikey
2. Create API Key → 복사

### 다중 키 (선택)
`.env` 에 `YOUTUBE_API_KEY_2`, `YOUTUBE_API_KEY_3` … 형태로 추가하면 자동 로테이션됩니다.

---

## 📁 프로젝트 구조

```
.
├── src/
│   ├── server.js              # 엔트리 포인트
│   ├── db/database.js         # SQLite 스키마 + 저장 헬퍼
│   ├── services/
│   │   ├── youtube.js         # YouTube API (다중 키 로테이션)
│   │   ├── gemini.js          # Google Gemini AI
│   │   ├── cache.js           # node-cache 래퍼
│   │   └── calculators.js     # NoxScore / 수익 추정
│   ├── routes/
│   │   ├── videos.js          # 영상/트렌딩/카테고리/검색
│   │   ├── channels.js        # 채널 상세/히스토리/비교
│   │   └── analytics.js       # 랭킹 · 수익 · AI
│   └── jobs/dailyCrawl.js     # 일일 크롤 스크립트
├── public/
│   ├── index.html             # SPA 진입점
│   ├── css/style.css          # 디자인 시스템
│   └── js/
│       ├── common.js          # 포맷/유틸
│       └── app.js             # 해시 라우터 + 7개 페이지
├── data/                      # SQLite (.gitignore)
├── samples/                   # 샘플 JSON
├── docs/cursor-share.md       # Cursor 협업 공유 노트
├── scripts/make-zip.sh        # ZIP 패키징
└── .env.example               # 환경변수 템플릿
```

---

## 📡 API 엔드포인트

### 영상 / 트렌딩
- `GET /api/health` — 서버/키/캐시 상태
- `GET /api/trending?region=KR[&categoryId=10]` — TOP 50
- `GET /api/top100?region=KR[&categoryId=10]` — TOP 100
- `GET /api/ranking?region=KR` — 정리된 지표(랭킹용)
- `GET /api/categories?region=KR` — 카테고리 목록
- `GET /api/video/:id` — 영상 상세
- `GET /api/search?q=...&type=video|channel&region=KR&order=viewCount`

### 채널
- `GET /api/channel/:id` — 채널 상세
- `GET /api/channel/:id/videos?maxResults=20` — 최근 업로드 영상
- `GET /api/channel/:id/history` — 로컬 DB 히스토리
- `GET /api/handle/:handle` — @handle 검색
- `GET /api/channels?ids=A,B,C` — 배치 조회
- `GET /api/compare?ids=A,B,C` — 비교 표 데이터

### 분석 / 유틸
- `GET /api/revenue?id=...&cpm=1.5&uploads=4` — 월 수익 추정
- `POST /api/ai/analyze-channel` `{channelId}`
- `POST /api/ai/analyze-trend` `{region,categoryId?}`
- `POST /api/ai/suggest-titles` `{topic,style}`
- `POST /api/ai/compare` `{ids:[A,B,...]}`
- `POST /api/cache/flush` — 캐시 비우기

---

## 🧮 유닛 소모 가이드 (YouTube Data API v3)

| 작업 | 유닛 |
|---|---|
| 영상 · 채널 상세 | 1 |
| TOP 50 / 카테고리 | 1 |
| TOP 100 | 2 |
| **검색 (search.list)** | **100** |
| 배치 조회 (50개) | 1 |

**예시**: 하루 10,000 유닛 = TOP 100 × 5,000회 또는 검색 100회.

---

## ⏰ 일일 크롤

```bash
npm run crawl
```

`CRAWL_REGIONS=KR,US,JP` 의 TOP 100 데이터와 채널 통계를 SQLite에 저장합니다.
cron / GitHub Actions / systemd timer 로 하루 1회 실행 권장.

---

## 🛠️ 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `YOUTUBE_API_KEY가 설정되지 않았습니다` | `.env` 복사 및 키 입력 후 재시작 |
| `quotaExceeded` | 10,000 유닛 초과. 추가 키 로테이션 또는 KST 17:00 기다리기 |
| `GEMINI_API_KEY가 설정되지 않았습니다` | AI 기능은 선택사항. `.env`에 Gemini 키 추가 |
| 채널을 찾을 수 없음 | ID가 `UC`로 시작하는지 / 핸들은 `@` 없이 입력 |

---

## 📦 ZIP 패키징

```bash
bash scripts/make-zip.sh   # 종합사용툴.zip
# 또는
npm run package
```

---

## 📄 라이선스

MIT © 2026 dlsso1000-netizen

**⚠️ 주의**: 본 도구는 YouTube Data API 공식 정책에 따라 사용되어야 하며, 크롤링/재배포로 인한 법적 책임은 사용자에게 있습니다.
