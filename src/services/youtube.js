/**
 * YouTube Data API v3 클라이언트 (다중 키 로테이션 지원)
 * ------------------------------------------------------
 * - YOUTUBE_API_KEY / YOUTUBE_API_KEY_2 / YOUTUBE_API_KEY_3 읽어서 로테이션
 * - 할당량 소진(403 quotaExceeded) 시 자동으로 다음 키로 전환
 * - 모든 호출은 캐시 레이어(cache.wrap)를 거칠 수 있음
 */
const https = require('https');
const cache = require('./cache');

const API_BASE = 'https://www.googleapis.com/youtube/v3';

// --- 멀티 키 관리 ---
function collectKeys() {
  const keys = [];
  for (const name of ['YOUTUBE_API_KEY', 'YOUTUBE_API_KEY_2', 'YOUTUBE_API_KEY_3', 'YOUTUBE_API_KEY_4', 'YOUTUBE_API_KEY_5']) {
    const v = process.env[name];
    if (v && v !== '여기에_YOUTUBE_API_키_입력' && !v.startsWith('여기에')) keys.push({ name, key: v, exceeded: false });
  }
  return keys;
}
let KEYS = collectKeys();
let cursor = 0;

function currentKey() {
  if (KEYS.length === 0) return null;
  // 모두 소진되었으면 다시 리셋(다음 호출에서 재시도)
  if (KEYS.every((k) => k.exceeded)) {
    KEYS.forEach((k) => (k.exceeded = false));
  }
  // 사용 가능한 첫 키
  for (let i = 0; i < KEYS.length; i++) {
    const idx = (cursor + i) % KEYS.length;
    if (!KEYS[idx].exceeded) {
      cursor = idx;
      return KEYS[idx];
    }
  }
  return KEYS[0];
}

function markExceeded(key) {
  const k = KEYS.find((x) => x.key === key);
  if (k) {
    k.exceeded = true;
    cursor = (cursor + 1) % KEYS.length;
    console.warn(`[YouTube API] ${k.name} 할당량 소진 → 다음 키로 전환`);
  }
}

function hasKey() {
  return KEYS.length > 0;
}
function reloadKeys() {
  KEYS = collectKeys();
  cursor = 0;
}

// --- HTTP 요청 ---
function rawRequest(endpoint, params) {
  return new Promise((resolve, reject) => {
    const keyEntry = currentKey();
    if (!keyEntry) {
      return reject(new Error('YouTube API 키가 설정되지 않았습니다. .env에 YOUTUBE_API_KEY를 입력하세요.'));
    }
    const queryParams = new URLSearchParams({ ...params, key: keyEntry.key });
    const url = `${API_BASE}/${endpoint}?${queryParams.toString()}`;

    https
      .get(url, (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            if (json.error) {
              const reason = json.error.errors?.[0]?.reason || '';
              if (reason === 'quotaExceeded' || reason === 'dailyLimitExceeded' || reason === 'rateLimitExceeded') {
                markExceeded(keyEntry.key);
                // 다른 키가 있다면 재시도
                if (KEYS.some((k) => !k.exceeded)) {
                  return rawRequest(endpoint, params).then(resolve).catch(reject);
                }
              }
              return reject(new Error(`YouTube API 오류: ${json.error.message} (${reason})`));
            }
            resolve(json);
          } catch (e) {
            reject(e);
          }
        });
      })
      .on('error', reject);
  });
}

async function request(endpoint, params, { ttl = 1800, useCache = true } = {}) {
  if (!useCache) return rawRequest(endpoint, params);
  const cacheKey = `yt:${endpoint}:${JSON.stringify(params)}`;
  return cache.wrap(cacheKey, () => rawRequest(endpoint, params), ttl);
}

// =========================================
// 고수준 API 함수들
// =========================================

// 국가별 인기 영상 (기본 50개, maxResults 최대 50, 1 unit)
async function trending({ region = 'KR', categoryId, maxResults = 50, pageToken } = {}) {
  const params = {
    part: 'snippet,statistics,contentDetails',
    chart: 'mostPopular',
    regionCode: region,
    maxResults,
  };
  if (categoryId) params.videoCategoryId = categoryId;
  if (pageToken) params.pageToken = pageToken;
  return request('videos', params, { ttl: 1800 });
}

// TOP 100 = mostPopular 50 + 다음 페이지 50 합치기 (2 units)
async function trendingTop100({ region = 'KR', categoryId } = {}) {
  const cacheKey = `yt:top100:${region}:${categoryId || 'all'}`;
  return cache.wrap(
    cacheKey,
    async () => {
      const first = await trending({ region, categoryId, maxResults: 50 });
      let items = first.items || [];
      if (first.nextPageToken && items.length < 100) {
        try {
          const second = await trending({ region, categoryId, maxResults: 50, pageToken: first.nextPageToken });
          items = items.concat(second.items || []);
        } catch (e) {
          // 추가 페이지 실패해도 50개로 반환
        }
      }
      return { items: items.slice(0, 100), region, categoryId: categoryId || null };
    },
    1800
  );
}

// 비디오 카테고리 리스트 (국가별)
async function videoCategories({ region = 'KR' } = {}) {
  const params = { part: 'snippet', regionCode: region };
  return request('videoCategories', params, { ttl: 24 * 3600 });
}

// 채널 상세 (배치 가능, 1 unit)
async function channelsByIds(ids) {
  if (!ids.length) return { items: [] };
  const params = {
    part: 'snippet,statistics,brandingSettings,topicDetails,contentDetails',
    id: ids.join(','),
    maxResults: ids.length,
  };
  return request('channels', params, { ttl: 1800 });
}

async function channelByHandle(handle) {
  const params = {
    part: 'snippet,statistics,brandingSettings,topicDetails',
    forHandle: handle,
  };
  return request('channels', params, { ttl: 1800 });
}

// 비디오 배치 조회
async function videosByIds(ids) {
  if (!ids.length) return { items: [] };
  const params = {
    part: 'snippet,statistics,contentDetails',
    id: ids.join(','),
    maxResults: ids.length,
  };
  return request('videos', params, { ttl: 900 });
}

// 검색 (100 unit, 비싸므로 캐시 & TTL↑)
async function search({ q, type = 'video', maxResults = 25, regionCode, pageToken, order = 'relevance' } = {}) {
  const params = { part: 'snippet', q, type, maxResults, order };
  if (regionCode) params.regionCode = regionCode;
  if (pageToken) params.pageToken = pageToken;
  return request('search', params, { ttl: 3600 });
}

// 채널의 업로드 영상 목록 (uploads playlist ID로 조회)
async function channelRecentVideos(channelId, maxResults = 20) {
  const channelResp = await channelsByIds([channelId]);
  const uploadsPlaylist = channelResp.items?.[0]?.contentDetails?.relatedPlaylists?.uploads;
  if (!uploadsPlaylist) return { items: [] };
  const params = {
    part: 'snippet,contentDetails',
    playlistId: uploadsPlaylist,
    maxResults,
  };
  const playlist = await request('playlistItems', params, { ttl: 1800 });
  const videoIds = (playlist.items || []).map((it) => it.contentDetails?.videoId).filter(Boolean);
  if (!videoIds.length) return { items: [] };
  return await videosByIds(videoIds);
}

module.exports = {
  trending,
  trendingTop100,
  videoCategories,
  channelsByIds,
  channelByHandle,
  videosByIds,
  search,
  channelRecentVideos,
  hasKey,
  reloadKeys,
  keyCount: () => KEYS.length,
};
