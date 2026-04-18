/**
 * 분석/유틸리티 라우트
 * - GET  /api/revenue?id=CHANNEL_ID&cpm=1.5&uploads=4
 * - GET  /api/ranking?region=KR&categoryId=10   (TOP 100 + 점수 계산)
 * - POST /api/ai/analyze-channel                 채널 AI 분석
 * - POST /api/ai/analyze-trend                   트렌드 AI 요약
 * - POST /api/ai/suggest-titles                  제목 추천
 * - POST /api/ai/compare                         채널 비교 AI 리포트
 */
const express = require('express');
const youtube = require('../services/youtube');
const gemini = require('../services/gemini');
const calc = require('../services/calculators');
const rising = require('../services/rising');

const router = express.Router();

// ===== 급상승 / 정체 채널 =====
router.get('/rising-channels', (req, res) => {
  try {
    const days = Math.max(1, Math.min(Number(req.query.days) || 7, 90));
    const limit = Math.max(1, Math.min(Number(req.query.limit) || 50, 200));
    const metric = (req.query.metric === 'views') ? 'views' : 'subscribers';
    const items = rising.risingChannels({ days, limit, metric });
    res.json({ ok: true, days, metric, count: items.length, items });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/falling-channels', (req, res) => {
  try {
    const days = Math.max(1, Math.min(Number(req.query.days) || 7, 90));
    const limit = Math.max(1, Math.min(Number(req.query.limit) || 30, 100));
    const metric = (req.query.metric === 'subscribers') ? 'subscribers' : 'views';
    const items = rising.fallingChannels({ days, limit, metric });
    res.json({ ok: true, days, metric, count: items.length, items });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/revenue', async (req, res) => {
  try {
    const id = req.query.id;
    if (!id) return res.status(400).json({ ok: false, error: 'id 파라미터가 필요합니다.' });
    const cpm = Number(req.query.cpm) || 1.5;
    const uploads = Number(req.query.uploads) || 4;
    const data = await youtube.channelsByIds([id]);
    if (!data.items?.length) return res.status(404).json({ ok: false, error: '채널을 찾을 수 없습니다.' });
    const item = data.items[0];
    const revenue = calc.revenueEstimateUSD(item.statistics, cpm, uploads);
    res.json({
      ok: true,
      channel: { id: item.id, title: item.snippet?.title, thumbnail: item.snippet?.thumbnails?.default?.url },
      stats: {
        subscribers: Number(item.statistics?.subscriberCount || 0),
        views: Number(item.statistics?.viewCount || 0),
        videos: Number(item.statistics?.videoCount || 0),
        avgViews: calc.avgViewsPerVideo(item.statistics),
        noxScore: calc.noxScore(item.statistics),
      },
      revenue,
    });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 랭킹 + 채널별 지표 강화 (TOP100 기반)
router.get('/ranking', async (req, res) => {
  try {
    const region = (req.query.region || 'KR').toUpperCase();
    const categoryId = req.query.categoryId || undefined;
    const top = await youtube.trendingTop100({ region, categoryId });
    const items = (top.items || []).map((v, i) => ({
      rank: i + 1,
      videoId: v.id,
      title: v.snippet?.title,
      channelTitle: v.snippet?.channelTitle,
      channelId: v.snippet?.channelId,
      thumbnail: v.snippet?.thumbnails?.high?.url,
      views: Number(v.statistics?.viewCount || 0),
      likes: Number(v.statistics?.likeCount || 0),
      comments: Number(v.statistics?.commentCount || 0),
      publishedAt: v.snippet?.publishedAt,
      duration: v.contentDetails?.duration || '',
      categoryId: v.snippet?.categoryId,
    }));
    res.json({ ok: true, region, categoryId: categoryId || null, count: items.length, items });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ===== AI =====
router.post('/ai/analyze-channel', async (req, res) => {
  try {
    if (!gemini.isReady()) return res.status(400).json({ ok: false, error: 'GEMINI_API_KEY가 설정되지 않았습니다.' });
    const id = req.body?.channelId;
    if (!id) return res.status(400).json({ ok: false, error: 'channelId가 필요합니다.' });
    const ch = await youtube.channelsByIds([id]);
    if (!ch.items?.length) return res.status(404).json({ ok: false, error: '채널 없음' });
    const videos = await youtube.channelRecentVideos(id, 10);
    const text = await gemini.analyzeChannel(ch.items[0], videos.items || []);
    res.json({ ok: true, channelId: id, analysis: text });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.post('/ai/analyze-trend', async (req, res) => {
  try {
    if (!gemini.isReady()) return res.status(400).json({ ok: false, error: 'GEMINI_API_KEY가 설정되지 않았습니다.' });
    const region = (req.body?.region || 'KR').toUpperCase();
    const categoryId = req.body?.categoryId || undefined;
    const top = await youtube.trending({ region, categoryId, maxResults: 20 });
    const text = await gemini.analyzeTrend(top.items || [], region);
    res.json({ ok: true, region, analysis: text });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.post('/ai/suggest-titles', async (req, res) => {
  try {
    if (!gemini.isReady()) return res.status(400).json({ ok: false, error: 'GEMINI_API_KEY가 설정되지 않았습니다.' });
    const topic = (req.body?.topic || '').trim();
    const style = req.body?.style || '일반';
    if (!topic) return res.status(400).json({ ok: false, error: 'topic이 필요합니다.' });
    const text = await gemini.suggestTitles(topic, style);
    res.json({ ok: true, topic, titles: text });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.post('/ai/compare', async (req, res) => {
  try {
    if (!gemini.isReady()) return res.status(400).json({ ok: false, error: 'GEMINI_API_KEY가 설정되지 않았습니다.' });
    const ids = Array.isArray(req.body?.ids) ? req.body.ids : [];
    if (ids.length < 2) return res.status(400).json({ ok: false, error: '비교할 채널 ID 2개 이상 필요' });
    const ch = await youtube.channelsByIds(ids);
    const text = await gemini.compareChannels(ch.items || []);
    res.json({ ok: true, ids, analysis: text });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

module.exports = router;
