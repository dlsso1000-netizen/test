/**
 * 데일리 크롤 잡
 * - 주요 국가의 TOP 100 영상을 수집하여 DB에 저장
 * - 등장하는 채널들의 최신 통계도 함께 저장 (히스토리 누적)
 * - 실행: node src/jobs/dailyCrawl.js
 * - 스케줄: cron 또는 외부 스케줄러 (예: GitHub Actions) 에서 호출
 */
require('dotenv').config();
const youtube = require('../services/youtube');
const db = require('../db/database');

const REGIONS = (process.env.CRAWL_REGIONS || 'KR,US,JP').split(',').map((s) => s.trim()).filter(Boolean);

async function crawlOne(region) {
  console.log(`[crawl] ${region} TOP 100 수집 시작...`);
  const top = await youtube.trendingTop100({ region });
  const videos = top.items || [];
  const channelIds = [...new Set(videos.map((v) => v.snippet?.channelId).filter(Boolean))];
  videos.forEach((v) => db.saveVideo(v, region));
  db.saveRankingSnapshot(region, null, videos);
  console.log(`[crawl] ${region} 영상 ${videos.length}개 저장, 채널 ${channelIds.length}개 집계 예정`);

  // 채널 배치 조회는 최대 50개씩
  for (let i = 0; i < channelIds.length; i += 50) {
    const batch = channelIds.slice(i, i + 50);
    const resp = await youtube.channelsByIds(batch);
    (resp.items || []).forEach((c) => db.saveChannel(c));
  }
  console.log(`[crawl] ${region} 완료`);
}

(async () => {
  try {
    if (!youtube.hasKey()) {
      console.error('[crawl] YOUTUBE_API_KEY가 없습니다. .env를 확인하세요.');
      process.exit(1);
    }
    console.log(`[crawl] 대상 국가: ${REGIONS.join(', ')}`);
    for (const region of REGIONS) {
      try {
        await crawlOne(region);
      } catch (e) {
        console.error(`[crawl] ${region} 실패:`, e.message);
      }
    }
    console.log('[crawl] 모든 작업 완료.');
    process.exit(0);
  } catch (e) {
    console.error('[crawl] 치명적 오류:', e);
    process.exit(1);
  }
})();
