/**
 * 채널 관련 API 라우트
 * - GET /api/channel/:id              채널 상세
 * - GET /api/channel/:id/videos       최근 업로드 영상
 * - GET /api/channel/:id/history      DB에 쌓인 히스토리(시간별 추이)
 * - GET /api/channels?ids=A,B,C       배치 조회 (비교용)
 * - GET /api/handle/:handle           @handle 로 채널 검색
 * - GET /api/compare?ids=A,B,C        비교 표 데이터
 */
const express = require('express');
const youtube = require('../services/youtube');
const db = require('../db/database');
const calc = require('../services/calculators');

const router = express.Router();

router.get('/channel/:id', async (req, res) => {
  try {
    const data = await youtube.channelsByIds([req.params.id]);
    if (!data.items?.length) return res.status(404).json({ ok: false, error: '채널을 찾을 수 없습니다.' });
    const info = data.items[0];
    try {
      db.saveChannel(info);
    } catch (e) {}
    res.json({ ok: true, item: info });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/channel/:id/videos', async (req, res) => {
  try {
    const max = Math.min(Number(req.query.maxResults) || 20, 50);
    const data = await youtube.channelRecentVideos(req.params.id, max);
    res.json({ ok: true, count: data.items?.length || 0, items: data.items || [] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/channel/:id/history', (req, res) => {
  try {
    const rows = db.channelHistory(req.params.id);
    res.json({ ok: true, count: rows.length, items: rows });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/channels', async (req, res) => {
  try {
    const ids = (req.query.ids || '').split(',').map((s) => s.trim()).filter(Boolean);
    if (!ids.length) return res.status(400).json({ ok: false, error: 'ids 파라미터가 필요합니다.' });
    const data = await youtube.channelsByIds(ids);
    try {
      (data.items || []).forEach((c) => db.saveChannel(c));
    } catch (e) {}
    res.json({ ok: true, count: data.items?.length || 0, items: data.items || [] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/handle/:handle', async (req, res) => {
  try {
    const handle = req.params.handle.startsWith('@') ? req.params.handle : `@${req.params.handle}`;
    const data = await youtube.channelByHandle(handle);
    if (!data.items?.length) return res.status(404).json({ ok: false, error: '채널을 찾을 수 없습니다.' });
    const info = data.items[0];
    try {
      db.saveChannel(info);
    } catch (e) {}
    res.json({ ok: true, item: info });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/compare', async (req, res) => {
  try {
    const ids = (req.query.ids || '').split(',').map((s) => s.trim()).filter(Boolean);
    if (ids.length < 2) return res.status(400).json({ ok: false, error: '비교하려면 채널 ID 2개 이상을 ids로 전달하세요.' });
    const data = await youtube.channelsByIds(ids);
    const metrics = (data.items || []).map((c) => ({
      id: c.id,
      title: c.snippet?.title,
      thumbnail: c.snippet?.thumbnails?.default?.url,
      country: c.snippet?.country,
      subscribers: Number(c.statistics?.subscriberCount || 0),
      views: Number(c.statistics?.viewCount || 0),
      videos: Number(c.statistics?.videoCount || 0),
      avgViewsPerVideo: calc.avgViewsPerVideo(c.statistics),
      engagementEstimate: calc.engagementEstimate(c.statistics),
      noxScore: calc.noxScore(c.statistics),
      monthlyRevenueUSD: calc.revenueEstimateUSD(c.statistics),
    }));
    res.json({ ok: true, count: metrics.length, items: metrics, raw: data.items || [] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

module.exports = router;
