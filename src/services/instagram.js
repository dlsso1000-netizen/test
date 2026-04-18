/**
 * Instagram 공개 프로필 스크래퍼 (교육용)
 * ------------------------------------------------------------
 * - Instagram은 로그인 강제가 심합니다. 공개 HTML(og:meta)만
 *   best-effort로 읽고, 보호된 데이터는 가져오지 않습니다.
 * - 자주 호출 시 429/로그인 리다이렉트가 뜰 수 있으므로
 *   15분 캐시와 타임아웃을 적용합니다.
 * - 상업적 용도로 사용 금지. 정식 데이터는 Instagram Graph API
 *   (Meta for Developers) 사용을 권장합니다.
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
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          return resolve(fetchHTML(new URL(res.headers.location, url).toString()));
        }
        if (res.statusCode !== 200) {
          return reject(new Error(`Instagram 페이지 요청 실패: HTTP ${res.statusCode}`));
        }
        let body = '';
        res.setEncoding('utf8');
        res.on('data', (c) => (body += c));
        res.on('end', () => resolve(body));
      }
    );
    req.setTimeout(10000, () => req.destroy(new Error('Instagram 요청 타임아웃')));
    req.on('error', reject);
  });
}

function extractMeta(html, prop) {
  const m = html.match(
    new RegExp(`<meta[^>]+(?:property|name)=["']${prop}["'][^>]+content=["']([^"']+)["']`, 'i')
  );
  return m ? m[1] : null;
}

// og:description 예: "12345 Followers, 321 Following, 120 Posts - @username"
function parseStats(desc) {
  if (!desc) return {};
  const str = desc.replace(/,/g, '');
  const followers = (str.match(/(\d+(?:\.\d+)?)[KMB]?\s*Followers/i) || [])[0];
  const following = (str.match(/(\d+(?:\.\d+)?)[KMB]?\s*Following/i) || [])[0];
  const posts = (str.match(/(\d+(?:\.\d+)?)[KMB]?\s*Posts/i) || [])[0];
  const parse = (v) => {
    if (!v) return 0;
    const n = parseFloat(v);
    if (/K/i.test(v)) return Math.round(n * 1000);
    if (/M/i.test(v)) return Math.round(n * 1_000_000);
    if (/B/i.test(v)) return Math.round(n * 1_000_000_000);
    return Math.round(n);
  };
  return {
    followers: parse(followers),
    following: parse(following),
    posts: parse(posts),
  };
}

function normalizeUsername(raw) {
  return String(raw || '').trim().replace(/^@+/, '').split(/[/?#]/)[0];
}

async function getProfile(username) {
  const user = normalizeUsername(username);
  if (!user) throw new Error('사용자명이 비어 있습니다.');
  const cacheKey = `ig:profile:${user}`;
  return cache.wrap(
    cacheKey,
    async () => {
      const url = `https://www.instagram.com/${encodeURIComponent(user)}/`;
      const html = await fetchHTML(url);
      const title = extractMeta(html, 'og:title') || `@${user}`;
      const description = extractMeta(html, 'og:description') || '';
      const image = extractMeta(html, 'og:image') || '';
      const stats = parseStats(description);
      return {
        platform: 'instagram',
        username: user,
        url,
        title,
        description: description.slice(0, 300),
        thumbnail: image,
        stats,
        fetchedAt: new Date().toISOString(),
      };
    },
    900
  );
}

async function getHashtag(tag) {
  const t = String(tag || '').trim().replace(/^#/, '');
  if (!t) throw new Error('태그가 비어 있습니다.');
  const cacheKey = `ig:tag:${t}`;
  return cache.wrap(
    cacheKey,
    async () => {
      const url = `https://www.instagram.com/explore/tags/${encodeURIComponent(t)}/`;
      const html = await fetchHTML(url);
      return {
        platform: 'instagram',
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

module.exports = { getProfile, getHashtag };
