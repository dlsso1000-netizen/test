/**
 * 종합사용툴 v2.1 — 메인 서버
 * ===========================================
 *  - YouTube Data API v3 (다중 키 로테이션)
 *  - Google Gemini AI
 *  - TikTok / Instagram 공개 스크래퍼 (교육용)
 *  - SQLite 히스토리 저장
 *  - 캐시 레이어 (node-cache)
 *  - Rate limiting
 * 실행: npm start  (또는 node src/server.js)
 * ===========================================
 */
require('dotenv').config();
const express = require('express');
const path = require('path');
const fs = require('fs');

const youtube = require('./services/youtube');
const gemini = require('./services/gemini');
const cache = require('./services/cache');
require('./db/database'); // DB 초기화 트리거

const videosRoute = require('./routes/videos');
const channelsRoute = require('./routes/channels');
const analyticsRoute = require('./routes/analytics');
const snsRoute = require('./routes/sns');
const { createLimiter } = require('./middleware/rateLimit');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const DEFAULT_REGION = process.env.DEFAULT_REGION || 'KR';

// 미들웨어
app.set('trust proxy', 1);
app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.join(__dirname, '..', 'public')));

// 전역 레이트 리밋 (60초당 120회)
app.use('/api', createLimiter({ windowMs: 60_000, max: 120 }));

// 특히 비싼 엔드포인트들에 별도 제한
const strictLimiter = createLimiter({ windowMs: 60_000, max: 30, message: '검색/AI 호출이 너무 많습니다. 1분 후 재시도하세요.' });
app.use('/api/search', strictLimiter);
app.use('/api/ai', strictLimiter);
app.use('/api/tiktok', strictLimiter);
app.use('/api/instagram', strictLimiter);

// 공통 헬스체크
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    service: '종합사용툴',
    version: '2.1.0',
    youtubeApiReady: youtube.hasKey(),
    youtubeKeyCount: youtube.keyCount(),
    geminiApiReady: gemini.isReady(),
    region: DEFAULT_REGION,
    cacheStats: cache.stats(),
    timestamp: new Date().toISOString(),
  });
});

// 캐시 비우기 (관리용)
app.post('/api/cache/flush', (req, res) => {
  cache.flush();
  res.json({ ok: true, message: '캐시를 비웠습니다.' });
});

// API 라우트
app.use('/api', videosRoute);
app.use('/api', channelsRoute);
app.use('/api', analyticsRoute);
app.use('/api', snsRoute);

// 페이지 라우트 (SPA 기반이지만 직접 경로도 받아줌)
const pageHandler = (file) => (req, res) => {
  const fp = path.join(__dirname, '..', 'public', 'pages', file);
  if (fs.existsSync(fp)) return res.sendFile(fp);
  res.redirect('/');
};
app.get('/ranking', pageHandler('ranking.html'));
app.get('/channel', pageHandler('channel.html'));
app.get('/search', pageHandler('search.html'));
app.get('/ai', pageHandler('ai.html'));
app.get('/calculator', pageHandler('calculator.html'));
app.get('/compare', pageHandler('compare.html'));
app.get('/sns', pageHandler('sns.html'));
app.get('/rising', pageHandler('rising.html'));

// 404 (API)
app.use('/api/*', (req, res) => res.status(404).json({ ok: false, error: 'API 경로를 찾을 수 없습니다.' }));

// 에러 핸들러
app.use((err, req, res, _next) => {
  console.error('[ERROR]', err);
  res.status(500).json({ ok: false, error: err.message || 'Internal Server Error' });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log('================================================');
  console.log(`🚀 종합사용툴 v2.1 실행 중: http://localhost:${PORT}`);
  console.log(`   YouTube API 키:   ${youtube.hasKey() ? `${youtube.keyCount()}개 로드됨 ✅` : '❌ 없음 (.env 확인)'}`);
  console.log(`   Gemini API 키:    ${gemini.isReady() ? '✅ 로드됨' : '❌ 없음 (.env 확인)'}`);
  console.log(`   기본 국가:        ${DEFAULT_REGION}`);
  console.log('================================================');
});
