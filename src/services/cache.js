/**
 * 캐시 레이어 - node-cache 기반
 * 목적: YouTube API 할당량(10,000 units/일) 절약
 */
const NodeCache = require('node-cache');

// 기본 TTL: 30분 (1800초), 인기 영상은 1시간, 검색은 15분
const cache = new NodeCache({ stdTTL: 1800, checkperiod: 300 });

function get(key) {
  return cache.get(key);
}
function set(key, value, ttl = 1800) {
  return cache.set(key, value, ttl);
}
function del(key) {
  return cache.del(key);
}
function flush() {
  return cache.flushAll();
}
function stats() {
  return cache.getStats();
}

// wrapper: fetcher 결과를 자동 캐싱
async function wrap(key, fetcher, ttl = 1800) {
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const value = await fetcher();
  cache.set(key, value, ttl);
  return value;
}

module.exports = { get, set, del, flush, stats, wrap };
