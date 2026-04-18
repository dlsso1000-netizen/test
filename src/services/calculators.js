/**
 * 채널 분석 보조 계산기
 *  - 평균 조회수
 *  - 가상의 참여도 (조회수/구독자 기반 간이 지표)
 *  - NoxScore 유사 종합 점수
 *  - 수익 추정 (월, USD)
 */

function avgViewsPerVideo(stats) {
  const views = Number(stats?.viewCount || 0);
  const videos = Number(stats?.videoCount || 0);
  if (!videos) return 0;
  return Math.round(views / videos);
}

function engagementEstimate(stats) {
  const subs = Number(stats?.subscriberCount || 0);
  const avg = avgViewsPerVideo(stats);
  if (!subs) return 0;
  // 평균 조회수 / 구독자 * 100 → 대략 상위 5% 채널은 20%+, 평범한 채널은 3~8%
  return Number(((avg / subs) * 100).toFixed(2));
}

// NoxScore 유사 (0~100). 구독자 · 조회수 · 영상 효율을 로그 정규화로 합산.
function noxScore(stats) {
  const subs = Number(stats?.subscriberCount || 0);
  const views = Number(stats?.viewCount || 0);
  const videos = Number(stats?.videoCount || 0);
  if (!subs && !views) return 0;

  const subScore = Math.min(Math.log10(Math.max(subs, 1)) * 12, 40); // max 40
  const viewScore = Math.min(Math.log10(Math.max(views, 1)) * 8, 35); // max 35
  const avg = videos ? views / videos : 0;
  const avgScore = Math.min(Math.log10(Math.max(avg, 1)) * 5, 25); // max 25
  return Math.round(subScore + viewScore + avgScore);
}

/**
 * 수익 추정 (월, USD)
 * - CPM 가정: $0.5 ~ $2.5 (평균 $1.5)
 * - 월 조회수 = 평균 조회수/영상 * 월간 업로드 4개 가정
 *   (실제 시스템에선 최근 30일 조회수로 계산해야 정확)
 */
function revenueEstimateUSD(stats, cpm = 1.5, monthlyUploads = 4) {
  const avg = avgViewsPerVideo(stats);
  const monthlyViews = avg * monthlyUploads;
  // CPM = 1천 회당 가격
  const rev = (monthlyViews / 1000) * cpm;
  return {
    low: Math.round((rev * 0.33) * 100) / 100,
    mid: Math.round(rev * 100) / 100,
    high: Math.round((rev * 2) * 100) / 100,
    currency: 'USD',
    assumptions: { cpm, monthlyUploads, avgViewsPerVideo: avg },
  };
}

/** 검색 결과의 채널 ID만 중복 제거해 반환 */
function uniqueChannelIds(searchItems) {
  return [...new Set((searchItems || []).map((s) => s.snippet?.channelId).filter(Boolean))];
}

module.exports = {
  avgViewsPerVideo,
  engagementEstimate,
  noxScore,
  revenueEstimateUSD,
  uniqueChannelIds,
};
