/**
 * SNS 스크래핑 라우트 (교육용)
 *  - GET /api/tiktok/profile/:username
 *  - GET /api/tiktok/tag/:tag
 *  - GET /api/instagram/profile/:username
 *  - GET /api/instagram/tag/:tag
 *
 * ⚠ 공식 API가 아닌 공개 웹페이지 메타데이터 파싱이므로
 *   각 플랫폼의 HTML 구조 변경 시 실패할 수 있습니다.
 */
const express = require('express');
const tiktok = require('../services/tiktok');
const instagram = require('../services/instagram');

const router = express.Router();

router.get('/tiktok/profile/:username', async (req, res) => {
  try {
    const data = await tiktok.getProfile(req.params.username);
    res.json({ ok: true, ...data });
  } catch (err) {
    res.status(500).json({ ok: false, platform: 'tiktok', error: err.message });
  }
});

router.get('/tiktok/tag/:tag', async (req, res) => {
  try {
    const data = await tiktok.searchHashtag(req.params.tag);
    res.json({ ok: true, ...data });
  } catch (err) {
    res.status(500).json({ ok: false, platform: 'tiktok', error: err.message });
  }
});

router.get('/instagram/profile/:username', async (req, res) => {
  try {
    const data = await instagram.getProfile(req.params.username);
    res.json({ ok: true, ...data });
  } catch (err) {
    res.status(500).json({ ok: false, platform: 'instagram', error: err.message });
  }
});

router.get('/instagram/tag/:tag', async (req, res) => {
  try {
    const data = await instagram.getHashtag(req.params.tag);
    res.json({ ok: true, ...data });
  } catch (err) {
    res.status(500).json({ ok: false, platform: 'instagram', error: err.message });
  }
});

module.exports = router;
