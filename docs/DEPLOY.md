# 🚀 배포 가이드

## 1. Docker (가장 간단)

```bash
cp .env.example .env          # 키 입력
docker compose up --build -d  # 빌드 + 백그라운드 실행
curl http://localhost:3000/api/health
```

- 데이터(SQLite)는 `jonghap-data` 네임드 볼륨에 저장됩니다.
- 중지: `docker compose down` (데이터는 유지)
- 재시작: `docker compose restart app`

## 2. Fly.io

```bash
# Fly CLI 설치: https://fly.io/docs/hands-on/install-flyctl/
fly launch --now=false          # fly.toml 은 이미 준비됨
fly volumes create jonghap_data --region nrt --size 1
fly secrets set YOUTUBE_API_KEY=AIza... GEMINI_API_KEY=AIza...
fly deploy
```

무료 플랜에서도 동작하지만, 트래픽 없을 때 머신이 자동 종료됩니다.

## 3. Render.com

1. https://render.com → New Web Service → GitHub 연결
2. `render.yaml` 감지됨 → Apply
3. Environment 탭에 `YOUTUBE_API_KEY`, `GEMINI_API_KEY` 입력
4. 자동 배포 완료 후 제공 URL 접속

## 4. Vercel (정적 UI만)

본 프로젝트는 **SSR/영구 DB가 필요**하므로 Vercel Serverless에는 **완전히 적합하지 않습니다**.
별도 서버(Render/Fly)로 API를 운영하고 UI만 Vercel로 올리는 식으로 분리 가능:

1. `public/` 폴더만 Vercel에 정적 배포
2. `public/js/common.js` 의 `api()` 가 외부 API 서버 URL을 바라보도록 수정
3. API 서버는 Render/Fly/자체 VM 에 띄움

## 5. systemd (Ubuntu VPS)

```ini
# /etc/systemd/system/jonghap-tool.service
[Unit]
Description=종합사용툴 v2.1
After=network.target

[Service]
WorkingDirectory=/opt/jonghap-tool
ExecStart=/usr/bin/node src/server.js
Restart=always
EnvironmentFile=/opt/jonghap-tool/.env
User=ubuntu

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now jonghap-tool
sudo systemctl status jonghap-tool
sudo journalctl -u jonghap-tool -f
```

## 6. GitHub Actions 일일 크롤

`.github/workflows/daily-crawl.yml` 이 매일 KST 17:30(UTC 08:30)에 실행됩니다.

- Secrets 등록 필요: Settings → Secrets and variables → Actions
  - `YOUTUBE_API_KEY`, `YOUTUBE_API_KEY_2` (선택), `YOUTUBE_API_KEY_3` (선택)
- 수동 실행: Actions 탭 → `종합사용툴 일일 크롤` → Run workflow

⚠ Actions 러너는 휘발성이라 DB가 유지되지 않습니다. 장기 누적이 필요하면:
- (A) 배포된 서버에서 cron 으로 직접 실행
- (B) 아티팩트/외부 DB(Supabase 등)에 업로드

## 7. 환경변수 요약

| 키 | 필수 | 설명 |
|---|---|---|
| `YOUTUBE_API_KEY` | ✅ | YouTube Data API v3 키 |
| `YOUTUBE_API_KEY_2..5` | ⭕ | 로테이션용 추가 키 |
| `GEMINI_API_KEY` | ⭕ | Gemini AI 분석 |
| `PORT` | ⭕ | 기본 3000 |
| `DEFAULT_REGION` | ⭕ | 기본 KR |
| `CRAWL_REGIONS` | ⭕ | 일일 크롤 대상 (기본 KR,US,JP) |
