/**
 * 급상승 채널 검출
 * - channel_history 테이블에서 최근 기록과 과거 기록을 비교해
 *   구독자/조회수 증가율 상위 N개 채널을 계산
 * - 데이터가 부족하면 빈 배열 반환 (일일 크롤 1회 이상 필요)
 */
const { db } = require('../db/database');

/**
 * @param {number} days        비교 기간 (기본 7일)
 * @param {number} limit       결과 상한
 * @param {string} metric      'subscribers' | 'views'
 * @returns {Array<{channel_id,title,thumbnail,old,new,delta,pct}>}
 */
function risingChannels({ days = 7, limit = 50, metric = 'subscribers' } = {}) {
  const now = new Date();
  const since = new Date(now.getTime() - days * 24 * 3600 * 1000).toISOString();

  const col = metric === 'views' ? 'view_count' : 'subscriber_count';

  // 각 채널의 최신 값 + 기간 시작 시점 값 조회
  const rows = db
    .prepare(
      `
    SELECT
      c.channel_id,
      c.title,
      c.thumbnail,
      c.country,
      (SELECT ${col} FROM channel_history h1 WHERE h1.channel_id = c.channel_id ORDER BY recorded_at DESC LIMIT 1) AS new_val,
      (SELECT ${col} FROM channel_history h2 WHERE h2.channel_id = c.channel_id AND recorded_at <= ? ORDER BY recorded_at DESC LIMIT 1) AS old_val
    FROM channels c
    WHERE new_val IS NOT NULL AND old_val IS NOT NULL AND old_val > 0
  `
    )
    .all(since);

  const items = rows
    .map((r) => {
      const delta = (r.new_val || 0) - (r.old_val || 0);
      const pct = r.old_val > 0 ? (delta / r.old_val) * 100 : 0;
      return {
        channelId: r.channel_id,
        title: r.title,
        thumbnail: r.thumbnail,
        country: r.country,
        old: r.old_val,
        new: r.new_val,
        delta,
        pct: Number(pct.toFixed(3)),
        metric,
      };
    })
    .filter((x) => x.delta > 0)
    .sort((a, b) => b.pct - a.pct)
    .slice(0, limit);

  return items;
}

/** 조회수 감소 등 이상치/정체 채널도 볼 수 있게 */
function fallingChannels({ days = 7, limit = 30, metric = 'views' } = {}) {
  const all = risingChannels({ days, limit: 10000, metric });
  return all
    .filter((x) => x.delta < 0)
    .sort((a, b) => a.pct - b.pct)
    .slice(0, limit);
}

module.exports = { risingChannels, fallingChannels };
