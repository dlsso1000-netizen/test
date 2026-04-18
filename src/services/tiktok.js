/**
 * TikTok 공개 프로필 스크래퍼 (교육용)
 * ------------------------------------------------------------
 * - TikTok 은 공식 API가 매우 제한적이라, 공개 웹페이지의
 *   OG 메타데이터 / JSON-LD 일부만 추출합니다.
 * - 로그인/보호된 데이터는 가져오지 않으며, robots.txt에 따라
 *   자주 호출하지 않도록 자체 캐시(15분)만 적용합니다.
 * - TikTok의 이용약관을 준수하여 상업적 용도로 쓰지 마세요.
 *
 * 지원 기능 (best-effort, 구조 변경 시 실패 가능)
 *  - getProfile(username)     @username 의 공개 프로필 정보
 *  - searchHashtag(tag)       태그 페이지 메타데이터
 * ------------------------------------------------------------
 */
const https = require('https');
const cache = require('./cache');

const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15';

function fetchHTML(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      {
        headers: {
          'User-Agent': UA,
          'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
          Accept: 'text/html,application/xhtml+xml',
        },
      },
      (res) => {
        // redirect 따라가기
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          return resolve(fetchHTML(new URL(res.headers.location, url).toString()));
        }
        if (res.statusCode !== 200) {
          return reject(new Error(`TikTok 페이지 요청 실패: HTTP ${res.statusCode}`));
        }
        let body = '';
        res.setEncoding('utf8');
        res.on('data', (c) => (body += c));
        res.on('end', () => resolve(body));
      }
    );
    req.setTimeout(10000, () => {
      req.destroy(new Error('TikTok 요청 타임아웃'));
    });
    req.on('error', reject);
  });
}

function extractMeta(html, prop) {
  const m = html.match(
    new RegExp(`<meta[^>]+(?:property|name)=["']${prop}["'][^>]+content=["']([^"']+)["']`, 'i')
  );
  return m ? m[1] : null;
}

function extractSIGI(html) {
  // TikTok은 __UNIVERSAL_DATA_FOR_REHYDRATION__ 또는 SIGI_STATE 스크립트에 JSON을 심습니다.
  const patterns = [
    /<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([\s\S]+?)<\/script>/,
    /<script id="SIGI_STATE"[^>]*>([\s\S]+?)<\/script>/,
  ];
  for (const p of patterns) {
    const m = html.match(p);
    if (m) {
      try {
        return JSON.parse(m[1]);
      } catch (_) {}
    }
  }
  return null;
}

function normalizeUsername(raw) {
  return String(raw || '').trim().replace(/^@+/, '').split(/[/?#]/)[0];
}

async function getProfile(username) {
  const user = normalizeUsername(username);
  if (!user) throw new Error('사용자명이 비어 있습니다.');
  const cacheKey = `tk:profile:${user}`;
  return cache.wrap(
    cacheKey,
    async () => {
      const url = `https://www.tiktok.com/@${encodeURIComponent(user)}`;
      const html = await fetchHTML(url);
      const title = extractMeta(html, 'og:title') || `@${user}`;
      const description = extractMeta(html, 'og:description') || '';
      const image = extractMeta(html, 'og:image') || '';

      // SIGI 데이터에서 팔로워/하트/영상 추출 시도
      let stats = {};
      const data = extractSIGI(html);
      if (data) {
        const scope =
          data?.__DEFAULT_SCOPE__?.['webapp.user-detail']?.userInfo ||
          data?.UserModule?.users?.[user] ||
          null;
        if (scope) {
          stats = {
            followers: Number(scope.stats?.followerCount || scope.followerCount || 0),
            following: Number(scope.stats?.followingCount || scope.followingCount || 0),
            hearts: Number(scope.stats?.heartCount || scope.heartCount || 0),
            videos: Number(scope.stats?.videoCount || scope.videoCount || 0),
            verified: !!(scope.user?.verified || scope.verified),
          };
        }
      }

      return {
        platform: 'tiktok',
        username: user,
        url,
        title,
        description: description.slice(0, 300),
        thumbnail: image,
        stats,
        fetchedAt: new Date().toISOString(),
      };
    },
    900 // 15분 캐시
  );
}

async function searchHashtag(tag) {
  const t = String(tag || '').trim().replace(/^#/, '');
  if (!t) throw new Error('태그가 비어 있습니다.');
  const cacheKey = `tk:tag:${t}`;
  return cache.wrap(
    cacheKey,
    async () => {
      const url = `https://www.tiktok.com/tag/${encodeURIComponent(t)}`;
      const html = await fetchHTML(url);
      return {
        platform: 'tiktok',
        tag: t,
        url,
        title: extractMeta(html, 'og:title'),
        description: extractMeta(html, 'og:description'),
        thumbnail: extractMeta(html, 'og:image'),
        fetchedAt: new Date().toISOString(),
      };
    },
    900
  );
}

module.exports = { getProfile, searchHashtag };
