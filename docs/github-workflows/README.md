# GitHub Actions 워크플로우 — 수동 복사 필요

GenSpark(또는 GitHub App)의 기본 토큰은 `.github/workflows/*` 파일을 push할 권한(`workflows` scope)이 없기 때문에, 본 폴더에 **사본**을 둡니다.

## 설치 방법 (Cursor 또는 로컬 터미널에서)

```bash
# 레포 루트에서
mkdir -p .github/workflows
cp docs/github-workflows/*.yml .github/workflows/
git add .github/workflows/
git commit -m "chore: GitHub Actions 워크플로우 추가"
git push origin main
```

## 워크플로우 목록

| 파일 | 트리거 | 설명 |
|---|---|---|
| `ci.yml` | push/PR | 모듈 로드 + 서버 기동 + `/api/health` 200 확인 |
| `daily-crawl.yml` | cron `30 8 * * *` (KST 17:30) + 수동 | `node src/jobs/dailyCrawl.js` → DB 아티팩트 업로드 |
| `package-zip.yml` | push to main + 수동 | `종합사용툴.zip` 생성 → 아티팩트 |

## Secrets 등록 (daily-crawl.yml용)

GitHub → Settings → Secrets and variables → Actions → New repository secret

- `YOUTUBE_API_KEY` (필수)
- `YOUTUBE_API_KEY_2`, `YOUTUBE_API_KEY_3` (선택, 로테이션)

## 수동 실행

Actions 탭 → 워크플로우 선택 → **Run workflow** 버튼 클릭.
