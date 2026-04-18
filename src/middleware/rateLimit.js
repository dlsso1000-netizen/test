/**
 * 아주 가벼운 인-메모리 Rate Limiter (IP 기준 슬라이딩 윈도우)
 * 외부 의존성 없이 동작하도록 직접 구현.
 *  - 기본: 60초당 60회
 *  - 검색/AI 같은 비싼 엔드포인트는 별도 설정값으로 감쌀 수 있음
 */
function createLimiter({ windowMs = 60_000, max = 60, message = '요청이 너무 많습니다. 잠시 후 다시 시도하세요.' } = {}) {
  const buckets = new Map(); // ip -> [timestamps]
  return (req, res, next) => {
    const ip = (req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown')
      .toString()
      .split(',')[0]
      .trim();
    const now = Date.now();
    const arr = (buckets.get(ip) || []).filter((t) => now - t < windowMs);
    if (arr.length >= max) {
      res.setHeader('Retry-After', Math.ceil(windowMs / 1000));
      return res.status(429).json({ ok: false, error: message });
    }
    arr.push(now);
    buckets.set(ip, arr);
    // 주기적인 cleanup (큰 map 방지)
    if (buckets.size > 5000) {
      for (const [k, v] of buckets) {
        if (!v.length || now - v[v.length - 1] > windowMs) buckets.delete(k);
      }
    }
    next();
  };
}

module.exports = { createLimiter };
