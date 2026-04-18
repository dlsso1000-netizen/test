# 📊 종합사용툴 v2.1

> YouTube Data API v3 + Google Gemini AI + TikTok/Instagram 공개 메타까지 담은 **멀티 플랫폼 영상 분석 대시보드**.
> 국가별 TOP 100 · 급상승 채널 · 채널 심층 분석 · AI 트렌드 · 수익 계산 · 채널 비교 · SNS 프로필 · 북마크 모두 한 번에.

참고 사이트: [Playboard](https://playboard.co) · [Vling](https://vling.net) · [NoxInfluencer](https://kr.noxinfluencer.com)

![version](https://img.shields.io/badge/version-2.1.0-7c5cff) ![node](https://img.shields.io/badge/node-%3E%3D18-339933) ![license](https://img.shields.io/badge/license-MIT-blue) ![docker](https://img.shields.io/badge/docker-ready-2496ED)

---

## ✨ 주요 기능 (v2.1 완성판)

| 메뉴 | 설명 |
|---|---|
| 📊 **TOP 100 랭킹** | 12개국 · 17개 카테고리 · 4가지 정렬 + Chart.js 바 차트 |
| 🚀 **급상승 채널** | DB 히스토리 기반 구독자·조회수 증가율 TOP N |
| 🔍 **검색** | 영상/채널 검색 + 관련성/조회수/최신 정렬 |
| 📺 **채널 분석** | KPI · 최근 영상 20 · **Chart.js 2축 히스토리** · AI 분석 · ⭐북마크 |
| ⚖️ **채널 비교** | 비교 표 + 레이더 차트 + Gemini AI 리포트 |
| 💰 **수익 계산기** | CPM·월 업로드 가정 → 월 예상 수익 3단계 추정 |
| 🤖 **AI 분석** | Gemini로 트렌드 요약 · 제목 10개 추천 · 채널 리포트 |
| 📱 **SNS 프로필** | TikTok · Instagram 공개 메타 조회 (교육용) |
| ⭐ **북마크** | 관심 채널 즐겨찾기 (localStorage, 기기별) |

공통 기능:
- ⚡ **다중 API 키 로테이션** — 할당량 소진 시 자동 전환 (`YOUTUBE_API_KEY_2/_3/_4/_5`)
- 💾 **SQLite 히스토리 누적** — 조회할 때마다 구독자/조회수 변화 기록
- 🧊 **캐시 레이어** — 유닛 절감 (카테고리 24h, 인기영상 30m, SNS 15m)
- 🛡 **Rate limiting** — IP 기반 간이 리미터 (전역 120req/min, 비싼 엔드포인트 30req/min)
- 📦 **일일 크롤** — `npm run crawl` 또는 GitHub Actions scheduled 자동 수집
- 🐳 **Docker / Fly.io / Render.com 배포 설정 내장**

---

## 🚀 빠른 시작

### A) 로컬 Node.js
```bash
git clone https://github.com/dlsso1000-netizen/test.git
cd test
npm install
cp .env.example .env      # YOUTUBE_API_KEY 입력 (필수), GEMINI_API_KEY (선택)
npm start                 # → http://localhost:3000
```

### B) Docker (한 줄 실행)
```bash
cp .env.example .env      # 키 입력
docker compose up --build -d
# → http://localhost:3000
```

자세한 배포(Docker / Fly.io / Render.com / systemd)는 [`docs/DEPLOY.md`](docs/DEPLOY.md) 참고.

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
│   ├── server.js                 # 엔트리 포인트 + 라우터 + 리미터
│   ├── db/database.js            # SQLite 스키마 + 저장 헬퍼
│   ├── services/
│   │   ├── youtube.js            # YouTube API (다중 키 로테이션)
│   │   ├── gemini.js             # Google Gemini AI
│   │   ├── cache.js              # node-cache 래퍼
│   │   ├── calculators.js        # NoxScore / 수익 추정
│   │   ├── rising.js             # 급상승 채널 계산
│   │   ├── tiktok.js             # TikTok 공개 메타 스크래퍼
│   │   └── instagram.js          # Instagram 공개 메타 스크래퍼
│   ├── middleware/rateLimit.js   # IP 기반 간이 리미터
│   ├── routes/
│   │   ├── videos.js             # 영상/트렌딩/카테고리/검색
│   │   ├── channels.js           # 채널 상세/히스토리/비교
│   │   ├── analytics.js          # 랭킹 · 수익 · 급상승 · AI
│   │   └── sns.js                # TikTok / Instagram 라우트
│   └── jobs/dailyCrawl.js        # 일일 크롤 스크립트
├── public/
│   ├── index.html                # SPA 진입점 (+ Chart.js CDN)
│   ├── css/style.css             # 디자인 시스템
│   └── js/
│       ├── common.js             # 포맷/유틸
│       ├── bookmarks.js          # localStorage 북마크 모듈
│       └── app.js                # 해시 라우터 + 10개 페이지
├── .github/workflows/
│   ├── ci.yml                    # 모듈 로드 + 헬스체크
│   ├── daily-crawl.yml           # 매일 KST 17:30 크롤
│   └── package-zip.yml           # ZIP 아티팩트 빌드
├── data/                         # SQLite (.gitignore)
├── samples/                      # 샘플 JSON
├── docs/
│   ├── cursor-share.md           # Cursor 협업 공유 노트
│   ├── DEPLOY.md                 # 배포 가이드 (Docker/Fly/Render)
│   └── SNS-NOTES.md              # TikTok/IG 스크래퍼 주의사항
├── Dockerfile                    # multi-stage 빌드
├── docker-compose.yml            # 볼륨 + 헬스체크 포함
├── fly.toml                      # Fly.io 배포
├── render.yaml                   # Render.com 배포
├── scripts/make-zip.sh           # ZIP 패키징
└── .env.example                  # 환경변수 템플릿
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
- `GET /api/rising-channels?metric=subscribers|views&days=7&limit=50` — 급상승 TOP N
- `GET /api/falling-channels?metric=...&days=...` — 정체/감소 채널
- `POST /api/ai/analyze-channel` `{channelId}`
- `POST /api/ai/analyze-trend` `{region,categoryId?}`
- `POST /api/ai/suggest-titles` `{topic,style}`
- `POST /api/ai/compare` `{ids:[A,B,...]}`
- `POST /api/cache/flush` — 캐시 비우기

### SNS (공개 메타, 교육용)
- `GET /api/tiktok/profile/:username` — TikTok 프로필
- `GET /api/tiktok/tag/:tag` — TikTok 해시태그
- `GET /api/instagram/profile/:username` — Instagram 프로필
- `GET /api/instagram/tag/:tag` — Instagram 해시태그

> ⚠ SNS 엔드포인트는 공식 API가 아니며, 각 플랫폼의 공개 메타데이터만 파싱합니다. `docs/SNS-NOTES.md` 참고.

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
