# =========================================
# 종합사용툴 v2.1 Dockerfile
# Multi-stage: build (native deps 컴파일) → runtime
# =========================================

# ---- 1) Build stage ----
FROM node:20-bookworm-slim AS builder
WORKDIR /app

# better-sqlite3 네이티브 빌드 도구
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 make g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json* ./
# better-sqlite3 등 네이티브 모듈 재빌드 (이미지 CPU arch 기준)
RUN npm install --production --no-audit --no-fund

# ---- 2) Runtime stage ----
FROM node:20-bookworm-slim
WORKDIR /app
ENV NODE_ENV=production PORT=3000

# 런타임 필수 라이브러리만 (sqlite3 for better-sqlite3 native)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libsqlite3-0 tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 app

COPY --from=builder /app/node_modules ./node_modules
COPY --chown=app:app package.json ./
COPY --chown=app:app src ./src
COPY --chown=app:app public ./public
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app samples ./samples
COPY --chown=app:app docs ./docs
COPY --chown=app:app .env.example ./

# 데이터 폴더(런타임에 생성)
RUN mkdir -p /app/data && chown -R app:app /app/data

USER app
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/api/health').then(r=>r.ok?process.exit(0):process.exit(1)).catch(()=>process.exit(1))"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "src/server.js"]
