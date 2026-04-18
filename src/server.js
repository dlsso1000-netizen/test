/**
 * 종합사용툴 - 메인 실행 파일
 * ====================================
 * YouTube Data API v3 기반 분석 대시보드
 * 실행: npm start  (또는 node src/server.js)
 * ====================================
 */

require('dotenv').config();
const express = require('express');
const path = require('path');
const https = require('https');

const app = express();
const PORT = process.env.PORT || 3000;
const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const DEFAULT_REGION = process.env.DEFAULT_REGION || 'KR';

// 정적 파일 서빙
app.use(express.static(path.join(__dirname, '..', 'public')));
app.use(express.json());

// =============================================
// 유틸: YouTube API 호출 헬퍼
// =============================================
function youtubeRequest(endpoint, params) {
  return new Promise((resolve, reject) => {
    if (!YOUTUBE_API_KEY || YOUTUBE_API_KEY === '여기에_YOUTUBE_API_키_입력') {
      return reject(new Error('YOUTUBE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.'));
    }

    const queryParams = new URLSearchParams({ ...params, key: YOUTUBE_API_KEY });
    const url = `https://www.googleapis.com/youtube/v3/${endpoint}?${queryParams.toString()}`;

    https.get(url, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.error) {
            reject(new Error(`YouTube API 오류: ${json.error.message}`));
          } else {
            resolve(json);
          }
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

// =============================================
// API 라우트
// =============================================

// 상태 확인
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    service: '종합사용툴',
    version: '1.0.0',
    youtubeApiReady: !!YOUTUBE_API_KEY && YOUTUBE_API_KEY !== '여기에_YOUTUBE_API_키_입력',
    geminiApiReady: !!GEMINI_API_KEY && GEMINI_API_KEY !== '여기에_GEMINI_API_키_입력',
    region: DEFAULT_REGION,
    timestamp: new Date().toISOString(),
  });
});

// 국가별 인기 영상 TOP 50
app.get('/api/trending', async (req, res) => {
  try {
    const region = req.query.region || DEFAULT_REGION;
    const maxResults = req.query.maxResults || 50;

    const data = await youtubeRequest('videos', {
      part: 'snippet,statistics,contentDetails',
      chart: 'mostPopular',
      regionCode: region,
      maxResults,
    });

    const videos = (data.items || []).map((item) => ({
      id: item.id,
      title: item.snippet.title,
      channelTitle: item.snippet.channelTitle,
      channelId: item.snippet.channelId,
      publishedAt: item.snippet.publishedAt,
      thumbnail: item.snippet.thumbnails?.medium?.url,
      viewCount: parseInt(item.statistics.viewCount || 0, 10),
      likeCount: parseInt(item.statistics.likeCount || 0, 10),
      commentCount: parseInt(item.statistics.commentCount || 0, 10),
      duration: item.contentDetails.duration,
      url: `https://www.youtube.com/watch?v=${item.id}`,
    }));

    res.json({ region, count: videos.length, videos });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 채널 정보 조회
app.get('/api/channel/:channelId', async (req, res) => {
  try {
    const data = await youtubeRequest('channels', {
      part: 'snippet,statistics,brandingSettings',
      id: req.params.channelId,
    });

    if (!data.items || data.items.length === 0) {
      return res.status(404).json({ error: '채널을 찾을 수 없습니다.' });
    }

    const ch = data.items[0];
    res.json({
      id: ch.id,
      title: ch.snippet.title,
      description: ch.snippet.description,
      country: ch.snippet.country,
      publishedAt: ch.snippet.publishedAt,
      thumbnail: ch.snippet.thumbnails?.medium?.url,
      subscriberCount: parseInt(ch.statistics.subscriberCount || 0, 10),
      viewCount: parseInt(ch.statistics.viewCount || 0, 10),
      videoCount: parseInt(ch.statistics.videoCount || 0, 10),
      url: `https://www.youtube.com/channel/${ch.id}`,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 검색 (주의: 100 유닛 소모)
app.get('/api/search', async (req, res) => {
  try {
    const q = req.query.q;
    if (!q) return res.status(400).json({ error: '검색어(q)가 필요합니다.' });

    const data = await youtubeRequest('search', {
      part: 'snippet',
      q,
      type: 'video',
      maxResults: req.query.maxResults || 10,
      regionCode: req.query.region || DEFAULT_REGION,
    });

    const results = (data.items || []).map((item) => ({
      videoId: item.id.videoId,
      title: item.snippet.title,
      channelTitle: item.snippet.channelTitle,
      channelId: item.snippet.channelId,
      publishedAt: item.snippet.publishedAt,
      thumbnail: item.snippet.thumbnails?.medium?.url,
      url: `https://www.youtube.com/watch?v=${item.id.videoId}`,
    }));

    res.json({ query: q, count: results.length, results });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 루트: 대시보드 HTML
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

// =============================================
// 서버 시작
// =============================================
app.listen(PORT, '0.0.0.0', () => {
  console.log('═══════════════════════════════════════════');
  console.log('🎬 종합사용툴 서버 시작!');
  console.log('═══════════════════════════════════════════');
  console.log(`📍 주소:      http://localhost:${PORT}`);
  console.log(`🌍 기본 지역: ${DEFAULT_REGION}`);
  console.log(`🔑 YouTube:   ${YOUTUBE_API_KEY && YOUTUBE_API_KEY !== '여기에_YOUTUBE_API_키_입력' ? '✅ 연결됨' : '❌ 미설정'}`);
  console.log(`🤖 Gemini:    ${GEMINI_API_KEY && GEMINI_API_KEY !== '여기에_GEMINI_API_키_입력' ? '✅ 연결됨' : '⚠️ 선택사항'}`);
  console.log('═══════════════════════════════════════════');
  console.log('💡 팁:');
  console.log('  - 대시보드: http://localhost:' + PORT);
  console.log('  - API 상태: http://localhost:' + PORT + '/api/health');
  console.log('  - 인기 영상: http://localhost:' + PORT + '/api/trending?region=KR');
  console.log('═══════════════════════════════════════════');
});
