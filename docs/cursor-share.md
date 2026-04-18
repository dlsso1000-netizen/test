# 📋 Cursor 공유용 - 종합사용툴 v2.1 전체 기능 완성

> **한 줄 요약**: v2.1 — Phase 3까지 전부 구현 완료. Chart.js 고급 차트, 급상승 채널 API, TikTok/Instagram 스크래퍼, 북마크, Docker/Render/Fly 배포 설정, GitHub Actions 일일 크롤·CI·ZIP 패키징 워크플로우, Rate limit 모두 탑재.

- **레포**: https://github.com/dlsso1000-netizen/test
- **브랜치**: `main`
- **작업 환경**: GenSpark 샌드박스 → 같은 원격 push
- **로컬 실행**: `npm install && cp .env.example .env` → 키 입력 → `npm start` → http://localhost:3000

---

## 🆕 v2.1 에서 추가된 것 (이번 커밋)

### 신규 서비스/라우트
| 파일 | 설명 |
|---|---|
| `src/services/rising.js` | channel_history 기반 구독자/조회수 증가율 TOP N 계산 |
| `src/services/tiktok.js` | TikTok 공개 프로필/태그 메타 (og + SIGI JSON) 파싱 |
| `src/services/instagram.js` | Instagram og:description → followers/following/posts 파싱 |
| `src/routes/sns.js` | `/api/tiktok/*`, `/api/instagram/*` 엔드포인트 |
| `src/middleware/rateLimit.js` | 60초 윈도우 IP 기반 가벼운 리미터 |

### 신규 API
- `GET /api/rising-channels?metric=subscribers|views&days=7&limit=50`
- `GET /api/falling-channels?metric=...&days=...`
- `GET /api/tiktok/profile/:username`
- `GET /api/tiktok/tag/:tag`
- `GET /api/instagram/profile/:username`
- `GET /api/instagram/tag/:tag`

### 프론트 신규
- **Chart.js** 통합 (`<script src="cdn.jsdelivr...">`) — 채널 히스토리(라인 2축), 랭킹 TOP 20 분포(바), 채널 비교(레이더)
- **급상승 채널 페이지** (`#/rising`) — metric/기간/상한 선택 + 표
- **SNS 페이지** (`#/sns`) — TikTok/Instagram 프로필·태그 조회
- **북마크 페이지** (`#/bookmarks`) — localStorage 기반
- 채널 상세에 ⭐ 북마크 토글 버튼

### 배포 파일
- `Dockerfile` (multi-stage, better-sqlite3 네이티브 빌드 포함)
- `.dockerignore`
- `docker-compose.yml` (영속 볼륨 `jonghap-data`)
- `fly.toml` — Fly.io 배포
- `render.yaml` — Render.com 배포
- `docs/DEPLOY.md` — 전체 배포 가이드 (Docker/Fly/Render/Vercel/systemd)
- `docs/SNS-NOTES.md` — 스크래퍼 주의/구조 변경 대응 방법

### GitHub Actions 워크플로우 (docs/github-workflows/ 에 사본 보관)

⚠️ GenSpark/GitHub App의 기본 토큰은 `.github/workflows/*` 를 push 할 수 있는 권한이 없어서, 이 레포에는 **사본만** `docs/github-workflows/` 에 들어 있습니다.

**Cursor에서 아래 3줄만 돌려주시면 적용 완료**:
```bash
mkdir -p .github/workflows && cp docs/github-workflows/*.yml .github/workflows/
git add .github/workflows/ && git commit -m "chore: GitHub Actions 워크플로우 추가" && git push origin main
```

| 파일 | 트리거 | 하는 일 |
|---|---|---|
| `daily-crawl.yml` | cron `30 8 * * *` (KST 17:30) + 수동 | `node src/jobs/dailyCrawl.js` → DB 아티팩트 업로드 |
| `package-zip.yml` | push to main + 수동 | `종합사용툴.zip` 생성 → 아티팩트 업로드 |
| `ci.yml` | push/PR | 모듈 로드 + 서버 기동 + `/api/health` 200 확인 |

**Secrets 등록 필요** (daily-crawl.yml 용):
- GitHub → Settings → Secrets and variables → Actions
- `YOUTUBE_API_KEY` (필수), `YOUTUBE_API_KEY_2/_3` (선택, 로테이션)

### Rate limit 적용 위치
- 전역 `/api/*` — 60초/120회
- `/api/search`, `/api/ai/*`, `/api/tiktok/*`, `/api/instagram/*` — 60초/30회 (비싼 엔드포인트)

---

## 🎯 현재 페이지 맵 (총 9개)

| 경로 | 기능 |
|---|---|
| `#/` | 홈 (KPI + 기능 카드) |
| `#/ranking` | 국가/카테고리 TOP 100 + Chart.js 바 |
| `#/rising` | 급상승 채널 (DB 기반) |
| `#/search` | 영상/채널 검색 |
| `#/channel` | 채널 상세 + Chart.js 히스토리 + AI + ⭐ |
| `#/compare` | 비교 표 + 레이더 차트 + AI 비교 리포트 |
| `#/calculator` | 월 수익 3단계 추정 |
| `#/ai` | 트렌드 요약 + 제목 10개 |
| `#/sns` | TikTok / Instagram 프로필·태그 |
| `#/bookmarks` | 관심 채널 localStorage |

---

## 🧪 빠른 검증 (로컬)

```bash
npm install
cp .env.example .env
# YOUTUBE_API_KEY, (선택) GEMINI_API_KEY 입력
npm start

# 주요 확인
curl http://localhost:3000/api/health
curl http://localhost:3000/api/rising-channels
curl http://localhost:3000/api/tiktok/profile/mrbeast   # 교육용
curl http://localhost:3000/api/top100?region=KR         # 키 필요
```

**샘플 테스트 결과** (2026-04-18 sandbox):
- `/api/tiktok/profile/mrbeast` → followers 126M, hearts 1.3B, videos 457 ✅
- `/api/instagram/profile/natgeo` → HTTP 429 (Instagram 자체 제한. 집/개인 IP에서는 대체로 성공)
- Rate limiter → 검색 31번째 호출부터 HTTP 429 ✅

---

## 🐳 Docker로 바로 띄우기

```bash
cp .env.example .env   # 키 입력
docker compose up --build -d
# → http://localhost:3000
docker compose logs -f app
```

자세한 배포 방법은 `docs/DEPLOY.md` 참고.

---

## 🧠 Cursor에서 봐두면 좋은 파일

1. `src/services/youtube.js` — **다중 키 로테이션**
2. `src/services/rising.js` — 히스토리 비교 SQL
3. `src/services/tiktok.js` / `instagram.js` — 구조 변경 시 여기 패턴 업데이트
4. `src/middleware/rateLimit.js` — 가벼운 인-메모리 리미터
5. `public/js/app.js` — SPA 라우터 + 10개 페이지
6. `public/js/bookmarks.js` — localStorage 북마크 모듈
7. `Dockerfile` / `docker-compose.yml` — 배포 기반
8. `.github/workflows/*.yml` — CI / 크롤 / ZIP
9. `docs/DEPLOY.md` — 전체 배포 가이드
10. `docs/SNS-NOTES.md` — 스크래퍼 유지보수 팁

---

## ⚠️ 알려진 제한

- **Instagram 스크래퍼**: 샌드박스 IP에서 HTTP 429 자주 발생. 로컬/개인 IP에서는 대체로 동작.
- **TikTok 스크래퍼**: 공개 SIGI JSON 의존. 구조 변경 시 `extractSIGI()` 패턴 수정 필요.
- **GitHub Actions 권한**: 기본 토큰에 `workflows` 권한이 없어 `.github/workflows/*.yml` push 실패 → 사본을 `docs/github-workflows/`에 뒀으니 Cursor에서 3줄로 복사·push (`cp docs/github-workflows/*.yml .github/workflows/`).
- **Vercel**: 영구 DB가 없어서 본 앱과 부적합. Docker/Render/Fly 추천.

---

## 🐛 에러 공유 방법 (Cursor ↔ GenSpark)

민감정보 마스킹 후 `samples/` 폴더에 JSON으로 저장하고 커밋:
```json
// samples/error-YYYYMMDD.json
{
  "endpoint": "/api/xxx",
  "status": 500,
  "message": "(에러 메시지)",
  "requestParams": { "region": "KR", "...": "..." }
}
```

`docs/cursor-share.md` 맨 위에 한 줄 요약 추가 후 push 해 주시면 바로 확인합니다.

---

## 🔗 참고

- YouTube Data API v3: https://developers.google.com/youtube/v3
- Gemini API: https://ai.google.dev/gemini-api/docs
- TikTok for Developers: https://developers.tiktok.com
- Instagram Graph API: https://developers.facebook.com/docs/instagram-api
- 참고 사이트: Playboard · Vling · NoxInfluencer
