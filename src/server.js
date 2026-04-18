/**
 * 종합사용툴 v2.0 — 메인 서버
 * ===========================================
 *  - YouTube Data API v3
 *  - Google Gemini AI
 *  - SQLite 히스토리 저장
 *  - 캐시 레이어 (node-cache)
 *  - 다중 API 키 로테이션
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

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const DEFAULT_REGION = process.env.DEFAULT_REGION || 'KR';

// 미들웨어
app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.join(__dirname, '..', 'public')));

// 공통 헬스체크
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    service: '종합사용툴',
    version: '2.0.0',
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

// 페이지 라우트 (SPA 느낌으로 해시 라우팅을 쓰되, 명시적 경로도 제공)
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

// 404 (API)
app.use('/api/*', (req, res) => res.status(404).json({ ok: false, error: 'API 경로를 찾을 수 없습니다.' }));

// 에러 핸들러
app.use((err, req, res, _next) => {
  console.error('[ERROR]', err);
  res.status(500).json({ ok: false, error: err.message || 'Internal Server Error' });
});

app.listen(PORT, () => {
  console.log('================================================');
  console.log(`🚀 종합사용툴 v2.0 실행 중: http://localhost:${PORT}`);
  console.log(`   YouTube API 키:   ${youtube.hasKey() ? `${youtube.keyCount()}개 로드됨 ✅` : '❌ 없음 (.env 확인)'}`);
  console.log(`   Gemini API 키:    ${gemini.isReady() ? '✅ 로드됨' : '❌ 없음 (.env 확인)'}`);
  console.log(`   기본 국가:        ${DEFAULT_REGION}`);
  console.log('================================================');
});
