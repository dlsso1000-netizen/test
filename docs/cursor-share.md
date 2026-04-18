# 📋 Cursor 공유용 - 종합사용툴 v2.0 전면 업그레이드 완료

> **한 줄 요약**: v2.0 대규모 개편 완료 — TOP 100 / 카테고리 / 채널상세(+히스토리 그래프) / 검색 / 수익계산 / 채널비교 / Gemini AI(트렌드·채널·제목) 모든 MVP 기능 구현, SQLite 히스토리 + 다중 키 로테이션 + 캐시 내장.

- **레포**: https://github.com/dlsso1000-netizen/test
- **브랜치**: `main`
- **작업 환경**: GenSpark 샌드박스 → 같은 원격 push
- **로컬 실행**: `npm install && cp .env.example .env` → 키 입력 → `npm start` → http://localhost:3000

---

## 🚀 v2.0 신규/업그레이드 항목 (이번 커밋)

### 백엔드 구조 재편
- `src/server.js` — 엔트리 포인트 재작성 (라우터 분리, 에러 핸들러)
- `src/services/youtube.js` — YouTube Data API 래퍼 **+ 다중 키 로테이션** (`YOUTUBE_API_KEY`, `_2`, `_3` …)
- `src/services/gemini.js` — Google Gemini AI 연동 (gemini-1.5-flash)
- `src/services/cache.js` — node-cache 기반 캐시 래퍼 (유닛 절감)
- `src/services/calculators.js` — 평균 조회수 / 참여도 / NoxScore / 월 수익 추정
- `src/db/database.js` — SQLite (better-sqlite3) 스키마 + 저장 헬퍼
- `src/routes/videos.js` · `channels.js` · `analytics.js` — API 라우트 분리
- `src/jobs/dailyCrawl.js` — 주요 국가 TOP 100 일일 크롤 스크립트

### 새 API 엔드포인트
| 경로 | 설명 | 유닛 |
|---|---|---|
| `GET /api/health` | 상태 + 키/캐시 | 0 |
| `GET /api/trending?region=KR[&categoryId=10]` | TOP 50 | 1 |
| `GET /api/top100?region=KR[&categoryId=10]` | TOP 100 | 2 |
| `GET /api/ranking?region=KR` | 랭킹(정제된 지표 포함) | 2 |
| `GET /api/categories?region=KR` | 카테고리 목록 | 1 (24h 캐시) |
| `GET /api/video/:id` | 영상 상세 | 1 |
| `GET /api/search?q=...&type=video|channel&region=KR&order=viewCount` | 검색 | **100** |
| `GET /api/channel/:id` / `/api/handle/:handle` | 채널 상세 | 1 |
| `GET /api/channel/:id/videos` | 채널 최근 영상 20 | ≈2 |
| `GET /api/channel/:id/history` | 로컬 DB 히스토리 | 0 |
| `GET /api/channels?ids=A,B,C` | 배치 조회 | 1 |
| `GET /api/compare?ids=A,B,C` | 비교 지표 표 | 1 |
| `GET /api/revenue?id=...&cpm=1.5&uploads=4` | 수익 계산 | 1 |
| `POST /api/ai/analyze-channel {channelId}` | AI 채널 분석 | 2 + Gemini |
| `POST /api/ai/analyze-trend {region}` | AI 트렌드 요약 | 1 + Gemini |
| `POST /api/ai/suggest-titles {topic,style}` | AI 제목 10개 | Gemini |
| `POST /api/ai/compare {ids:[...]}` | AI 채널 비교 리포트 | 1 + Gemini |
| `POST /api/cache/flush` | 캐시 비우기 | 0 |

### 프론트엔드 (SPA)
- `public/index.html` — 단일 진입점, 해시 라우팅
- `public/js/app.js` — 라우터 + 7개 페이지 렌더러
- `public/js/common.js` — 유틸 (숫자/시간/카테고리)
- `public/css/style.css` — 다크 글래스모피즘 디자인

### 페이지 구성
1. **홈** (`#/`) — API 상태 KPI, 기능 카드
2. **TOP 100 랭킹** (`#/ranking`) — 12개국 · 카테고리 · 정렬 4가지
3. **검색** (`#/search`) — 영상/채널 · 정렬 옵션
4. **채널 분석** (`#/channel?id=UCxxx` / `?handle=xxx`) — 프로필·KPI·최근 영상 20개·**히스토리 SVG 차트**·AI 분석 버튼
5. **채널 비교** (`#/compare`) — 다채널 표 + AI 비교 리포트
6. **수익 계산기** (`#/calculator`) — 채널 ID + CPM + 월 업로드
7. **AI 분석** (`#/ai`) — 트렌드 요약 + 제목 추천

---

## 🔑 환경변수

```ini
YOUTUBE_API_KEY=AIzaSy...       # 필수
YOUTUBE_API_KEY_2=              # 선택 (자동 로테이션)
YOUTUBE_API_KEY_3=              # 선택
GEMINI_API_KEY=AIzaSy...        # 선택 (AI 기능)
PORT=3000
DEFAULT_REGION=KR
CRAWL_REGIONS=KR,US,JP
```

- `.env`는 **절대 커밋 금지** (`.gitignore`에 포함됨)
- 다중 키는 `YOUTUBE_API_KEY_2` 식으로 넣으면 403 quotaExceeded 시 자동 전환

---

## 🗄️ 데이터베이스

SQLite 파일: `data/jonghap.db` (커밋 제외)

- `channels` · `videos` · `channel_history` · `ranking_snapshot`
- 호출 시마다 히스토리 자동 누적 → `/api/channel/:id/history` 로 조회, 차트 렌더링

---

## ⏰ 일일 크롤

```bash
node src/jobs/dailyCrawl.js
# or
npm run crawl
```

- 기본: KR, US, JP TOP 100 수집 → DB 누적
- 유닛 소모: 국가당 약 10~15 유닛 (TOP 100 2 + 채널 배치 조회)
- cron, GitHub Actions, systemd timer 등으로 1일 1회 실행 권장

---

## 🧪 빠른 검증 (로컬)

```bash
npm install
cp .env.example .env   # 키 입력
npm start              # http://localhost:3000

# API 테스트
curl http://localhost:3000/api/health
curl "http://localhost:3000/api/top100?region=KR"
curl "http://localhost:3000/api/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw"   # Google Developers
```

---

## 📦 ZIP 패키징

- 로컬: `bash scripts/make-zip.sh` → `종합사용툴.zip`
- GitHub Actions: `.github/workflows/package-zip.yml` (별도 커밋 필요 — 권한 이슈로 현재 비활성)

---

## 🧠 Cursor에서 볼 핵심 파일

1. `src/server.js` — 시작점
2. `src/services/youtube.js` — **다중 키 로테이션** 로직, 이해해두면 유용
3. `src/services/gemini.js` — 프롬프트 템플릿 커스터마이즈 지점
4. `src/services/calculators.js` — NoxScore/수익 추정 공식 조정 가능
5. `src/routes/analytics.js` — AI 라우트 + 랭킹 지표
6. `public/js/app.js` — SPA 라우터 + 7개 페이지
7. `public/css/style.css` — 디자인 토큰 (`:root`)

---

## ⚠️ 아직 안 된 것 / Phase 3 후보

- [ ] Chart.js 기반 고급 차트 (현재는 의존성 없는 간이 SVG)
- [ ] Instagram / TikTok 공식 API 혹은 스크래퍼 — 플랫폼 정책 검토 필요
- [ ] 사용자 로그인 / 관심채널 북마크 기능
- [ ] 일일 크롤 자동화(cron 셋업)
- [ ] Docker / Vercel / Cloudflare Pages 배포
- [ ] `/api/rising-channels` (구독자 급상승 채널 검출)

---

## 🐛 에러가 나면?

**민감정보 마스킹 후** `samples/` 폴더에 JSON으로 저장하고 커밋해 주세요:
```
samples/error-YYYYMMDD.json
{
  "endpoint": "/api/xxx",
  "status": 500,
  "message": "(에러 메시지)",
  "requestParams": { ... }
}
```
그리고 `docs/cursor-share.md` 맨 위에 한 줄 요약을 추가한 뒤 push 해 주시면 Cursor → GenSpark 왕복이 쉽습니다.

---

## 🔗 참고

- 참고 사이트: Playboard · Vling · NoxInfluencer
- YouTube Data API v3 문서: https://developers.google.com/youtube/v3
- Gemini API 문서: https://ai.google.dev/gemini-api/docs
