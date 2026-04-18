#!/bin/bash
# ============================================
# 종합사용툴.zip 패키징 스크립트
# ============================================
# 사용법: bash scripts/make-zip.sh
# 결과: 프로젝트 루트에 "종합사용툴.zip" 생성
# ============================================

set -e

PROJECT_NAME="종합사용툴"
ZIP_NAME="${PROJECT_NAME}.zip"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT_DIR"

# 기존 ZIP 삭제
rm -f "${ZIP_NAME}"

# .env 파일이 있어도 포함하지 않도록 주의
echo "📦 종합사용툴 패키징 시작..."

zip -r "${ZIP_NAME}" \
  src/ \
  public/ \
  samples/ \
  docs/ \
  scripts/ \
  .github/ \
  package.json \
  .gitignore \
  .dockerignore \
  .env.example \
  Dockerfile \
  docker-compose.yml \
  fly.toml \
  render.yaml \
  README.md \
  -x "*.env" \
  -x "node_modules/*" \
  -x "*.zip" \
  -x ".git/*" \
  -x "*.DS_Store" \
  -x "data/*.db*" \
  -x "package-lock.json"

if [ -f "${ZIP_NAME}" ]; then
  SIZE=$(du -h "${ZIP_NAME}" | cut -f1)
  echo ""
  echo "✅ 완료!"
  echo "📦 파일: ${ZIP_NAME}"
  echo "📊 크기: ${SIZE}"
  echo "📍 경로: ${ROOT_DIR}/${ZIP_NAME}"
  echo ""
  echo "💡 사용법:"
  echo "  1. ${ZIP_NAME} 압축 해제"
  echo "  2. cd 종합사용툴"
  echo "  3. npm install"
  echo "  4. cp .env.example .env (그리고 API 키 입력)"
  echo "  5. npm start"
else
  echo "❌ 패키징 실패"
  exit 1
fi
