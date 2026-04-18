/**
 * SQLite 데이터베이스 초기화 & 접근 모듈
 * - 채널/영상/랭킹 히스토리 저장
 */
const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

const DATA_DIR = path.join(__dirname, '..', '..', 'data');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

const DB_PATH = path.join(DATA_DIR, 'jonghap.db');
const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');

// 스키마 초기화
db.exec(`
  CREATE TABLE IF NOT EXISTS channels (
    channel_id      TEXT PRIMARY KEY,
    title           TEXT,
    description     TEXT,
    country         TEXT,
    category_id     TEXT,
    thumbnail       TEXT,
    subscriber_count INTEGER,
    view_count      INTEGER,
    video_count     INTEGER,
    published_at    TEXT,
    updated_at      TEXT
  );

  CREATE TABLE IF NOT EXISTS channel_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id       TEXT,
    subscriber_count INTEGER,
    view_count       INTEGER,
    video_count      INTEGER,
    recorded_at      TEXT,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
  );
  CREATE INDEX IF NOT EXISTS idx_channel_history_channel
    ON channel_history(channel_id, recorded_at);

  CREATE TABLE IF NOT EXISTS videos (
    video_id      TEXT PRIMARY KEY,
    channel_id    TEXT,
    title         TEXT,
    description   TEXT,
    thumbnail     TEXT,
    category_id   TEXT,
    region        TEXT,
    view_count    INTEGER,
    like_count    INTEGER,
    comment_count INTEGER,
    duration      TEXT,
    published_at  TEXT,
    updated_at    TEXT
  );

  CREATE TABLE IF NOT EXISTS ranking_snapshot (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    region      TEXT,
    category_id TEXT,
    rank        INTEGER,
    video_id    TEXT,
    snapshot_at TEXT
  );
  CREATE INDEX IF NOT EXISTS idx_ranking_region_cat
    ON ranking_snapshot(region, category_id, snapshot_at);

  CREATE TABLE IF NOT EXISTS api_cache (
    cache_key   TEXT PRIMARY KEY,
    payload     TEXT,
    expires_at  INTEGER
  );
`);

// ===== 헬퍼 =====
const nowIso = () => new Date().toISOString();

const upsertChannel = db.prepare(`
  INSERT INTO channels
    (channel_id, title, description, country, category_id, thumbnail,
     subscriber_count, view_count, video_count, published_at, updated_at)
  VALUES (@channel_id, @title, @description, @country, @category_id, @thumbnail,
          @subscriber_count, @view_count, @video_count, @published_at, @updated_at)
  ON CONFLICT(channel_id) DO UPDATE SET
    title=@title, description=@description, country=@country, category_id=@category_id,
    thumbnail=@thumbnail, subscriber_count=@subscriber_count, view_count=@view_count,
    video_count=@video_count, updated_at=@updated_at;
`);

const insertChannelHistory = db.prepare(`
  INSERT INTO channel_history (channel_id, subscriber_count, view_count, video_count, recorded_at)
  VALUES (?, ?, ?, ?, ?);
`);

const upsertVideo = db.prepare(`
  INSERT INTO videos
    (video_id, channel_id, title, description, thumbnail, category_id, region,
     view_count, like_count, comment_count, duration, published_at, updated_at)
  VALUES (@video_id, @channel_id, @title, @description, @thumbnail, @category_id, @region,
          @view_count, @like_count, @comment_count, @duration, @published_at, @updated_at)
  ON CONFLICT(video_id) DO UPDATE SET
    title=@title, thumbnail=@thumbnail, view_count=@view_count, like_count=@like_count,
    comment_count=@comment_count, region=@region, updated_at=@updated_at;
`);

const insertRanking = db.prepare(`
  INSERT INTO ranking_snapshot (region, category_id, rank, video_id, snapshot_at)
  VALUES (?, ?, ?, ?, ?);
`);

const getChannelHistory = db.prepare(`
  SELECT subscriber_count, view_count, video_count, recorded_at
  FROM channel_history
  WHERE channel_id = ?
  ORDER BY recorded_at ASC;
`);

const getChannel = db.prepare(`SELECT * FROM channels WHERE channel_id = ?;`);

function saveChannel(info) {
  upsertChannel.run({
    channel_id: info.id,
    title: info.snippet?.title || '',
    description: info.snippet?.description || '',
    country: info.snippet?.country || null,
    category_id: info.topicDetails?.topicCategories?.[0] || null,
    thumbnail: info.snippet?.thumbnails?.high?.url || info.snippet?.thumbnails?.default?.url || '',
    subscriber_count: Number(info.statistics?.subscriberCount || 0),
    view_count: Number(info.statistics?.viewCount || 0),
    video_count: Number(info.statistics?.videoCount || 0),
    published_at: info.snippet?.publishedAt || null,
    updated_at: nowIso(),
  });
  insertChannelHistory.run(
    info.id,
    Number(info.statistics?.subscriberCount || 0),
    Number(info.statistics?.viewCount || 0),
    Number(info.statistics?.videoCount || 0),
    nowIso()
  );
}

function saveVideo(v, region = 'KR') {
  upsertVideo.run({
    video_id: v.id,
    channel_id: v.snippet?.channelId || '',
    title: v.snippet?.title || '',
    description: (v.snippet?.description || '').slice(0, 500),
    thumbnail: v.snippet?.thumbnails?.high?.url || v.snippet?.thumbnails?.default?.url || '',
    category_id: v.snippet?.categoryId || null,
    region,
    view_count: Number(v.statistics?.viewCount || 0),
    like_count: Number(v.statistics?.likeCount || 0),
    comment_count: Number(v.statistics?.commentCount || 0),
    duration: v.contentDetails?.duration || '',
    published_at: v.snippet?.publishedAt || null,
    updated_at: nowIso(),
  });
}

function saveRankingSnapshot(region, categoryId, videos) {
  const snapshotAt = nowIso();
  const tx = db.transaction((items) => {
    items.forEach((v, i) => insertRanking.run(region, categoryId || 'ALL', i + 1, v.id, snapshotAt));
  });
  tx(videos);
}

function channelHistory(channelId) {
  return getChannelHistory.all(channelId);
}

function findChannel(channelId) {
  return getChannel.get(channelId);
}

module.exports = {
  db,
  saveChannel,
  saveVideo,
  saveRankingSnapshot,
  channelHistory,
  findChannel,
};
