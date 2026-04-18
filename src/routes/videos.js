/**
 * 영상 관련 API 라우트
 * - GET /api/trending         국가 인기 영상 (TOP 50)
 * - GET /api/top100           국가 인기 영상 TOP 100
 * - GET /api/categories       비디오 카테고리 목록
 * - GET /api/video/:id        단일 영상 상세
 * - GET /api/search           영상/채널 검색
 */
const express = require('express');
const youtube = require('../services/youtube');
const db = require('../db/database');

const router = express.Router();

router.get('/trending', async (req, res) => {
  try {
    const region = (req.query.region || 'KR').toUpperCase();
    const categoryId = req.query.categoryId || undefined;
    const maxResults = Math.min(Number(req.query.maxResults) || 50, 50);
    const data = await youtube.trending({ region, categoryId, maxResults });
    // history 저장
    if (data.items?.length) {
      try {
        data.items.forEach((v) => db.saveVideo(v, region));
        db.saveRankingSnapshot(region, categoryId, data.items);
      } catch (e) {
        console.warn('[trending] DB 저장 실패:', e.message);
      }
    }
    res.json({ ok: true, region, categoryId: categoryId || null, count: data.items?.length || 0, items: data.items || [] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/top100', async (req, res) => {
  try {
    const region = (req.query.region || 'KR').toUpperCase();
    const categoryId = req.query.categoryId || undefined;
    const data = await youtube.trendingTop100({ region, categoryId });
    if (data.items?.length) {
      try {
        data.items.forEach((v) => db.saveVideo(v, region));
        db.saveRankingSnapshot(region, categoryId, data.items);
      } catch (e) {
        console.warn('[top100] DB 저장 실패:', e.message);
      }
    }
    res.json({ ok: true, region, categoryId: categoryId || null, count: data.items.length, items: data.items });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/categories', async (req, res) => {
  try {
    const region = (req.query.region || 'KR').toUpperCase();
    const data = await youtube.videoCategories({ region });
    const items = (data.items || []).filter((c) => c.snippet?.assignable);
    res.json({ ok: true, region, count: items.length, items });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/video/:id', async (req, res) => {
  try {
    const data = await youtube.videosByIds([req.params.id]);
    if (!data.items?.length) return res.status(404).json({ ok: false, error: '영상을 찾을 수 없습니다.' });
    res.json({ ok: true, item: data.items[0] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

router.get('/search', async (req, res) => {
  try {
    const q = (req.query.q || '').trim();
    if (!q) return res.status(400).json({ ok: false, error: '검색어가 필요합니다. (q=)' });
    const type = req.query.type || 'video';
    const maxResults = Math.min(Number(req.query.maxResults) || 25, 50);
    const region = req.query.region || undefined;
    const order = req.query.order || 'relevance';
    const data = await youtube.search({ q, type, maxResults, regionCode: region, order });
    res.json({ ok: true, query: q, type, count: data.items?.length || 0, items: data.items || [] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

module.exports = router;
