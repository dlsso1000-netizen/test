/* ============================================
   종합사용툴 v2.0 SPA 라우터
   - 해시 기반 라우팅 (#/ranking, #/channel 등)
   ============================================ */

const root = document.getElementById('app');
let healthCache = null;

async function getHealth() {
  if (healthCache) return healthCache;
  try {
    healthCache = await api('/api/health');
  } catch (e) {
    healthCache = { youtubeApiReady: false, geminiApiReady: false };
  }
  return healthCache;
}

/* ========= 각 페이지 렌더러 ========= */

async function renderHome() {
  const health = await getHealth();
  root.innerHTML = `
    <section class="hero">
      <h1>📊 종합사용툴 v2.0</h1>
      <p>YouTube Data API v3 + Google Gemini AI 기반 글로벌 영상 분석 대시보드.<br>
      국가별 TOP 100 랭킹 · 채널 분석 · AI 트렌드 리포트 · 수익 계산 · 채널 비교까지 한 번에.</p>
    </section>
    <div class="container">
      <div class="kpi-grid">
        <div class="kpi">
          <div class="label">YouTube API</div>
          <div class="value" style="color:${health.youtubeApiReady ? 'var(--ok)' : 'var(--danger)'}">${health.youtubeApiReady ? '✅ 연결됨' : '❌ 미설정'}</div>
          <div class="delta">${health.youtubeApiReady ? `키 ${health.youtubeKeyCount}개 로드` : '.env에 YOUTUBE_API_KEY 추가'}</div>
        </div>
        <div class="kpi">
          <div class="label">Gemini AI</div>
          <div class="value" style="color:${health.geminiApiReady ? 'var(--ok)' : 'var(--warn)'}">${health.geminiApiReady ? '✅ 연결됨' : '⚠ 선택사항'}</div>
          <div class="delta">${health.geminiApiReady ? 'AI 분석 사용 가능' : '.env에 GEMINI_API_KEY 추가'}</div>
        </div>
        <div class="kpi">
          <div class="label">기본 국가</div>
          <div class="value">${health.region || 'KR'}</div>
          <div class="delta">.env에서 DEFAULT_REGION 변경</div>
        </div>
        <div class="kpi">
          <div class="label">캐시 히트</div>
          <div class="value">${(health.cacheStats?.hits || 0).toLocaleString()}</div>
          <div class="delta">${(health.cacheStats?.keys || 0)} 키 보관 중</div>
        </div>
      </div>

      <h2 class="section">🔥 주요 기능</h2>
      <div class="grid cols-3">
        ${featureCard('📊', '국가별 TOP 100', '12개국 인기 영상을 카테고리별로 분석', '#/ranking')}
        ${featureCard('🔍', '영상/채널 검색', '키워드로 바로 찾고 통계 확인', '#/search')}
        ${featureCard('📺', '채널 심층 분석', '채널 ID/핸들로 상세 통계 · 최근 영상 · 히스토리', '#/channel')}
        ${featureCard('⚖️', '채널 비교', '여러 채널 지표를 한 번에 비교 (+AI 리포트)', '#/compare')}
        ${featureCard('💰', '수익 계산기', 'CPM 기반 월 예상 수익 추정', '#/calculator')}
        ${featureCard('🤖', 'AI 트렌드 분석', 'Gemini로 트렌드 · 제목 · 썸네일 인사이트', '#/ai')}
      </div>

      <h2 class="section">🚀 빠른 시작</h2>
      <div class="grid cols-2">
        <div class="card" style="padding: 18px;">
          <h3 style="margin-bottom: 8px;">1️⃣ API 키 등록</h3>
          <p style="color: var(--muted); font-size: 13px; line-height: 1.6;">
            <code>.env</code> 파일에 <code>YOUTUBE_API_KEY</code>(필수) / <code>GEMINI_API_KEY</code>(선택)를 추가한 뒤 서버를 재시작하세요.<br>
            여러 키를 <code>YOUTUBE_API_KEY_2</code>, <code>_3</code>... 으로 추가하면 자동 로테이션됩니다.
          </p>
        </div>
        <div class="card" style="padding: 18px;">
          <h3 style="margin-bottom: 8px;">2️⃣ 랭킹 확인</h3>
          <p style="color: var(--muted); font-size: 13px; line-height: 1.6;">
            상단 <strong>랭킹 TOP 100</strong> 메뉴에서 국가 · 카테고리를 선택하면
            인기 영상 100개를 즉시 불러옵니다. 유닛 소모는 쿼리당 1유닛(캐시 30분).
          </p>
        </div>
      </div>
    </div>
  `;
}

function featureCard(emoji, title, desc, href) {
  return `
    <a href="${href}" class="card" style="display:block; padding: 18px 20px;">
      <div style="font-size: 36px; margin-bottom: 10px;">${emoji}</div>
      <div style="font-weight: 800; font-size: 16px; margin-bottom: 6px;">${title}</div>
      <div style="color: var(--muted); font-size: 13px;">${desc}</div>
    </a>`;
}

/* ========= 랭킹 페이지 ========= */
async function renderRanking() {
  root.innerHTML = `
    <section class="hero">
      <h1>📊 국가별 TOP 100 랭킹</h1>
      <p>YouTube Data API v3의 mostPopular 차트 기준 · 국가/카테고리별 최대 100개</p>
    </section>
    <div class="container">
      <div class="controls">
        <select class="select" id="region"></select>
        <select class="select" id="category"></select>
        <select class="select" id="sort">
          <option value="rank">인기순 (기본)</option>
          <option value="views">조회수 높은순</option>
          <option value="likes">좋아요순</option>
          <option value="comments">댓글순</option>
          <option value="newest">최신순</option>
        </select>
        <button class="btn" id="reload">🔄 불러오기</button>
        <span class="pill" id="meta"></span>
      </div>
      <div id="list" class="grid cols-4"><div class="loading">⏳ 로딩 중...</div></div>
    </div>
  `;
  const regionEl = document.getElementById('region');
  const categoryEl = document.getElementById('category');
  const sortEl = document.getElementById('sort');
  const listEl = document.getElementById('list');
  const metaEl = document.getElementById('meta');

  fillRegionSelect(regionEl, 'KR');
  await fillCategorySelect(categoryEl, regionEl.value);

  async function load() {
    listEl.innerHTML = '<div class="loading">⏳ TOP 100을 불러오는 중...</div>';
    try {
      const region = regionEl.value;
      const categoryId = categoryEl.value;
      const url = `/api/ranking?region=${region}${categoryId ? `&categoryId=${categoryId}` : ''}`;
      const data = await api(url);
      let items = data.items || [];
      const s = sortEl.value;
      if (s === 'views') items = [...items].sort((a, b) => b.views - a.views);
      else if (s === 'likes') items = [...items].sort((a, b) => b.likes - a.likes);
      else if (s === 'comments') items = [...items].sort((a, b) => b.comments - a.comments);
      else if (s === 'newest') items = [...items].sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));
      metaEl.textContent = `${data.region} · ${items.length}개 결과`;
      if (!items.length) { listEl.innerHTML = '<div class="error">결과가 없습니다.</div>'; return; }
      listEl.innerHTML = items.map((v, i) => rankCard(v, i + 1)).join('');
    } catch (e) {
      showError(listEl, e.message);
    }
  }
  document.getElementById('reload').onclick = load;
  regionEl.onchange = async () => { await fillCategorySelect(categoryEl, regionEl.value); load(); };
  categoryEl.onchange = load;
  sortEl.onchange = load;
  load();
}

function rankCard(v, rank) {
  const url = `https://www.youtube.com/watch?v=${v.videoId}`;
  return `
    <a class="card" href="${url}" target="_blank" rel="noopener">
      <span class="rank ${rank <= 3 ? 'top3' : ''}">#${rank}</span>
      <img class="thumb" src="${v.thumbnail}" alt="thumb" loading="lazy">
      <div class="body">
        <div class="title">${escapeHtml(v.title)}</div>
        <div class="meta">
          <a href="#/channel?id=${v.channelId}" onclick="event.stopPropagation(); location.hash='#/channel?id=${v.channelId}'; return false;" style="color: var(--accent2);">${escapeHtml(v.channelTitle)}</a>
        </div>
        <div class="meta" style="margin-top: 6px;">
          <span>👁 ${formatNumber(v.views)}</span>
          <span>👍 ${formatNumber(v.likes)}</span>
          <span>💬 ${formatNumber(v.comments)}</span>
          <span>🕒 ${formatDuration(v.duration)}</span>
        </div>
        <div class="meta" style="margin-top: 4px;">
          <span>📅 ${timeAgo(v.publishedAt)}</span>
        </div>
      </div>
    </a>`;
}

/* ========= 검색 페이지 ========= */
async function renderSearch() {
  root.innerHTML = `
    <section class="hero">
      <h1>🔍 영상/채널 검색</h1>
      <p>⚠ 검색은 호출당 <strong>100 유닛</strong>을 사용합니다 (기본 일일 10,000 = 100회)</p>
    </section>
    <div class="container">
      <div class="controls">
        <input class="input" id="q" placeholder="키워드 입력 (예: ai 뉴스, 챌린지, 쇼츠 편집)">
        <select class="select" id="type">
          <option value="video">영상</option>
          <option value="channel">채널</option>
        </select>
        <select class="select" id="region"></select>
        <select class="select" id="order">
          <option value="relevance">관련성</option>
          <option value="viewCount">조회수</option>
          <option value="rating">평점</option>
          <option value="date">최신</option>
        </select>
        <button class="btn" id="go">🔍 검색</button>
      </div>
      <div id="list" class="grid cols-4"></div>
    </div>
  `;
  fillRegionSelect(document.getElementById('region'), 'KR');
  async function go() {
    const q = document.getElementById('q').value.trim();
    const type = document.getElementById('type').value;
    const region = document.getElementById('region').value;
    const order = document.getElementById('order').value;
    const listEl = document.getElementById('list');
    if (!q) { listEl.innerHTML = '<div class="error">키워드를 입력하세요.</div>'; return; }
    listEl.innerHTML = '<div class="loading">⏳ 검색 중... (100 유닛 소모)</div>';
    try {
      const data = await api(`/api/search?q=${encodeURIComponent(q)}&type=${type}&region=${region}&order=${order}&maxResults=30`);
      if (!data.items?.length) { listEl.innerHTML = '<div class="error">결과가 없습니다.</div>'; return; }
      listEl.innerHTML = data.items.map((item) => searchCard(item, type)).join('');
    } catch (e) {
      showError(listEl, e.message);
    }
  }
  document.getElementById('go').onclick = go;
  document.getElementById('q').addEventListener('keypress', (e) => { if (e.key === 'Enter') go(); });
}

function searchCard(item, type) {
  const sn = item.snippet || {};
  if (type === 'channel') {
    const chId = item.id?.channelId;
    return `
      <a class="card" href="#/channel?id=${chId}" style="display:block;">
        <img class="thumb" src="${sn.thumbnails?.high?.url || sn.thumbnails?.default?.url}" loading="lazy">
        <div class="body">
          <div class="title">${escapeHtml(sn.title)}</div>
          <div class="meta"><span>${escapeHtml((sn.description || '').slice(0, 80))}</span></div>
        </div>
      </a>`;
  }
  const vid = item.id?.videoId;
  return `
    <a class="card" href="https://www.youtube.com/watch?v=${vid}" target="_blank">
      <img class="thumb" src="${sn.thumbnails?.high?.url || sn.thumbnails?.default?.url}" loading="lazy">
      <div class="body">
        <div class="title">${escapeHtml(sn.title)}</div>
        <div class="meta">${escapeHtml(sn.channelTitle)} · ${timeAgo(sn.publishedAt)}</div>
      </div>
    </a>`;
}

/* ========= 채널 상세 페이지 ========= */
async function renderChannel(params) {
  const id = params.get('id') || '';
  const handle = params.get('handle') || '';
  root.innerHTML = `
    <section class="hero">
      <h1>📺 채널 분석</h1>
      <p>채널 ID(UCxxxx...) 또는 핸들(@handle) 로 상세 통계를 조회합니다.</p>
    </section>
    <div class="container">
      <div class="controls">
        <input class="input" id="cid" placeholder="채널 ID (UCxxxx...)" value="${escapeHtml(id)}">
        <input class="input" id="handle" placeholder="또는 @handle" value="${escapeHtml(handle)}">
        <button class="btn" id="go">🔎 분석</button>
      </div>
      <div id="out"></div>
    </div>
  `;
  document.getElementById('go').onclick = load;
  if (id || handle) load();

  async function load() {
    const out = document.getElementById('out');
    const cid = document.getElementById('cid').value.trim();
    const hd = document.getElementById('handle').value.trim();
    if (!cid && !hd) { out.innerHTML = '<div class="error">채널 ID 또는 핸들을 입력하세요.</div>'; return; }
    out.innerHTML = '<div class="loading">⏳ 불러오는 중...</div>';
    try {
      let info;
      if (cid) info = (await api(`/api/channel/${encodeURIComponent(cid)}`)).item;
      else info = (await api(`/api/handle/${encodeURIComponent(hd.replace(/^@/, ''))}`)).item;

      const chId = info.id;
      const [videos, history] = await Promise.all([
        api(`/api/channel/${chId}/videos?maxResults=20`),
        api(`/api/channel/${chId}/history`),
      ]);
      renderChannelDetail(out, info, videos.items || [], history.items || []);
    } catch (e) {
      showError(out, e.message);
    }
  }
}

function renderChannelDetail(out, ch, videos, history) {
  const stats = ch.statistics || {};
  const subs = Number(stats.subscriberCount || 0);
  const views = Number(stats.viewCount || 0);
  const vidCnt = Number(stats.videoCount || 0);
  const avg = vidCnt ? Math.round(views / vidCnt) : 0;
  const engagement = subs ? ((avg / subs) * 100).toFixed(2) : 0;

  out.innerHTML = `
    <div class="profile-row">
      <img src="${ch.snippet?.thumbnails?.high?.url}" alt="thumb">
      <div style="flex: 1;">
        <h2>${escapeHtml(ch.snippet?.title)}</h2>
        <div class="kpis">
          <span>🌍 ${ch.snippet?.country || '미공개'}</span>
          <span>📅 ${timeAgo(ch.snippet?.publishedAt)}</span>
          <span>🆔 ${ch.id}</span>
        </div>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn ghost" id="copyId">📋 ID 복사</button>
        <button class="btn accent2" id="aiBtn">🤖 AI 분석</button>
      </div>
    </div>

    <div class="kpi-grid">
      <div class="kpi"><div class="label">구독자</div><div class="value">${formatNumber(subs)}</div></div>
      <div class="kpi"><div class="label">총 조회수</div><div class="value">${formatNumber(views)}</div></div>
      <div class="kpi"><div class="label">영상 수</div><div class="value">${formatNumber(vidCnt)}</div></div>
      <div class="kpi"><div class="label">평균 조회수</div><div class="value">${formatNumber(avg)}</div></div>
      <div class="kpi"><div class="label">참여도 (간이)</div><div class="value">${engagement}%</div></div>
    </div>

    <h2 class="section">📈 수집 히스토리 (${history.length}회)</h2>
    ${history.length
      ? `<canvas id="histChart" height="140" style="background:var(--card); border-radius:12px; padding:12px; border:1px solid var(--border);"></canvas>`
      : `<div class="loading">아직 저장된 히스토리가 없습니다. 반복 조회하면 변화 추이가 쌓입니다.</div>`}

    <h2 class="section">🎬 최근 업로드 영상</h2>
    <div class="grid cols-4">
      ${(videos || []).slice(0, 20).map((v, i) => {
        const sn = v.snippet || {};
        const st = v.statistics || {};
        return `
          <a class="card" href="https://www.youtube.com/watch?v=${v.id}" target="_blank">
            <img class="thumb" src="${sn.thumbnails?.high?.url}" loading="lazy">
            <div class="body">
              <div class="title">${escapeHtml(sn.title)}</div>
              <div class="meta">👁 ${formatNumber(st.viewCount)} · 👍 ${formatNumber(st.likeCount)} · 💬 ${formatNumber(st.commentCount)}</div>
              <div class="meta">${timeAgo(sn.publishedAt)} · ${formatDuration(v.contentDetails?.duration)}</div>
            </div>
          </a>`;
      }).join('')}
    </div>

    <h2 class="section" id="aiSection" style="display:none;">🤖 AI 분석 리포트</h2>
    <div id="aiResult"></div>
  `;

  document.getElementById('copyId').onclick = () => {
    navigator.clipboard.writeText(ch.id); alert(`채널 ID 복사됨: ${ch.id}`);
  };
  document.getElementById('aiBtn').onclick = async () => {
    const ai = document.getElementById('aiResult');
    document.getElementById('aiSection').style.display = 'block';
    ai.innerHTML = '<div class="loading">🤖 Gemini AI 분석 중... (약 5~10초)</div>';
    try {
      const res = await api('/api/ai/analyze-channel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channelId: ch.id }),
      });
      ai.innerHTML = `<div class="ai-output">${escapeHtml(res.analysis)}</div>`;
    } catch (e) {
      showError(ai, e.message);
    }
  };

  // 히스토리 차트 렌더
  if (history.length) renderHistoryChart(history);
}

function renderHistoryChart(history) {
  // 단순 SVG 라인 차트 (의존성 없이)
  const canvas = document.getElementById('histChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.clientWidth;
  const H = canvas.height = 140;
  const pad = 30;
  const subs = history.map((h) => h.subscriber_count);
  const min = Math.min(...subs);
  const max = Math.max(...subs);
  const range = max - min || 1;

  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = 'rgba(124,92,255,0.9)';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  subs.forEach((v, i) => {
    const x = pad + (i / Math.max(subs.length - 1, 1)) * (W - pad * 2);
    const y = H - pad - ((v - min) / range) * (H - pad * 2);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();

  // 점
  ctx.fillStyle = '#7c5cff';
  subs.forEach((v, i) => {
    const x = pad + (i / Math.max(subs.length - 1, 1)) * (W - pad * 2);
    const y = H - pad - ((v - min) / range) * (H - pad * 2);
    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
  });

  // 라벨
  ctx.fillStyle = '#8d96c7'; ctx.font = '11px sans-serif';
  ctx.fillText(formatNumber(max), 4, 20);
  ctx.fillText(formatNumber(min), 4, H - 12);
  ctx.fillText(`${history.length}회 수집`, W - 100, 20);
}

/* ========= 채널 비교 페이지 ========= */
async function renderCompare() {
  root.innerHTML = `
    <section class="hero">
      <h1>⚖️ 채널 비교</h1>
      <p>최대 5개 채널 ID를 쉼표로 구분해서 붙여넣으세요 (UCxxxx, UCyyyy, ...)</p>
    </section>
    <div class="container">
      <div class="controls">
        <input class="input" id="ids" placeholder="UCxxx,UCyyy,UCzzz" style="min-width: 420px;">
        <button class="btn" id="go">⚖️ 비교</button>
        <button class="btn accent2" id="aiGo">🤖 AI 비교 리포트</button>
      </div>
      <div id="out"></div>
    </div>
  `;
  document.getElementById('go').onclick = load;
  document.getElementById('aiGo').onclick = aiLoad;

  async function load() {
    const out = document.getElementById('out');
    const ids = document.getElementById('ids').value.trim();
    if (!ids) { out.innerHTML = '<div class="error">채널 ID를 2개 이상 입력하세요.</div>'; return; }
    out.innerHTML = '<div class="loading">⏳ 불러오는 중...</div>';
    try {
      const data = await api(`/api/compare?ids=${encodeURIComponent(ids)}`);
      renderCompareTable(out, data.items);
    } catch (e) {
      showError(out, e.message);
    }
  }

  async function aiLoad() {
    const out = document.getElementById('out');
    const ids = document.getElementById('ids').value.trim().split(',').map((s) => s.trim()).filter(Boolean);
    if (ids.length < 2) { out.innerHTML = '<div class="error">AI 비교는 ID 2개 이상 필요합니다.</div>'; return; }
    out.innerHTML = '<div class="loading">🤖 Gemini AI 비교 분석 중...</div>';
    try {
      const res = await api('/api/ai/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids }),
      });
      out.innerHTML = `<div class="ai-output">${escapeHtml(res.analysis)}</div>`;
    } catch (e) {
      showError(out, e.message);
    }
  }
}

function renderCompareTable(out, items) {
  out.innerHTML = `
    <div style="overflow-x:auto;">
    <table class="table">
      <thead>
        <tr>
          <th>채널</th><th>구독자</th><th>총 조회수</th><th>영상 수</th>
          <th>평균 조회수/영상</th><th>참여도</th><th>NoxScore</th><th>월수익(중간값)</th>
        </tr>
      </thead>
      <tbody>
        ${items.map((c) => `
          <tr>
            <td><img src="${c.thumbnail}" width="32" style="border-radius:50%; vertical-align:middle; margin-right:8px;">
              <a href="#/channel?id=${c.id}" style="color:var(--accent2); font-weight:600;">${escapeHtml(c.title)}</a></td>
            <td>${formatNumber(c.subscribers)}</td>
            <td>${formatNumber(c.views)}</td>
            <td>${formatNumber(c.videos)}</td>
            <td>${formatNumber(c.avgViewsPerVideo)}</td>
            <td>${c.engagementEstimate}%</td>
            <td><span class="pill">${c.noxScore}</span></td>
            <td>$${c.monthlyRevenueUSD.mid.toLocaleString()}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    </div>
  `;
}

/* ========= 수익 계산기 ========= */
async function renderCalculator() {
  root.innerHTML = `
    <section class="hero">
      <h1>💰 수익 계산기</h1>
      <p>CPM·월간 업로드 수 가정으로 월 예상 수익을 추정합니다. (실제 수익과 다를 수 있음)</p>
    </section>
    <div class="container">
      <div class="controls">
        <input class="input" id="id" placeholder="채널 ID (UCxxx...)" style="min-width: 280px;">
        <input class="input" id="cpm" placeholder="CPM ($ per 1000 views)" value="1.5" style="max-width: 180px;">
        <input class="input" id="uploads" placeholder="월 업로드 개수" value="4" style="max-width: 180px;">
        <button class="btn" id="go">💰 계산</button>
      </div>
      <div id="out"></div>
    </div>
  `;
  document.getElementById('go').onclick = async () => {
    const id = document.getElementById('id').value.trim();
    const cpm = Number(document.getElementById('cpm').value) || 1.5;
    const uploads = Number(document.getElementById('uploads').value) || 4;
    const out = document.getElementById('out');
    if (!id) { out.innerHTML = '<div class="error">채널 ID를 입력하세요.</div>'; return; }
    out.innerHTML = '<div class="loading">⏳ 계산 중...</div>';
    try {
      const data = await api(`/api/revenue?id=${encodeURIComponent(id)}&cpm=${cpm}&uploads=${uploads}`);
      out.innerHTML = `
        <div class="profile-row">
          <img src="${data.channel.thumbnail}" style="width: 60px; height: 60px;">
          <div><h2>${escapeHtml(data.channel.title)}</h2></div>
        </div>
        <div class="kpi-grid">
          <div class="kpi"><div class="label">구독자</div><div class="value">${formatNumber(data.stats.subscribers)}</div></div>
          <div class="kpi"><div class="label">평균 조회수</div><div class="value">${formatNumber(data.stats.avgViews)}</div></div>
          <div class="kpi"><div class="label">NoxScore</div><div class="value">${data.stats.noxScore}</div></div>
        </div>
        <h2 class="section">💵 월 예상 수익 (USD)</h2>
        <div class="kpi-grid">
          <div class="kpi"><div class="label">낮은 추정</div><div class="value" style="color: var(--muted);">$${data.revenue.low.toLocaleString()}</div></div>
          <div class="kpi"><div class="label">중간 추정</div><div class="value" style="color: var(--ok);">$${data.revenue.mid.toLocaleString()}</div></div>
          <div class="kpi"><div class="label">높은 추정</div><div class="value" style="color: var(--accent2);">$${data.revenue.high.toLocaleString()}</div></div>
        </div>
        <div class="ok-banner">
          💡 <strong>가정</strong>: CPM $${data.revenue.assumptions.cpm} · 월 업로드 ${data.revenue.assumptions.monthlyUploads}개 · 평균 조회수 ${formatNumber(data.revenue.assumptions.avgViewsPerVideo)}<br>
          ⚠ CPM은 국가/카테고리에 따라 $0.3 ~ $10+ 편차가 큽니다. 한국 일반 = 약 $1~$3, 미국 IT/금융 = $5+
        </div>
      `;
    } catch (e) { showError(out, e.message); }
  };
}

/* ========= AI 분석 페이지 ========= */
async function renderAI() {
  const health = await getHealth();
  root.innerHTML = `
    <section class="hero">
      <h1>🤖 AI 분석 (Gemini)</h1>
      <p>${health.geminiApiReady ? 'Gemini API 연결됨 ✅' : '⚠ .env에 <code>GEMINI_API_KEY</code>를 추가해야 동작합니다.'}</p>
    </section>
    <div class="container">
      <div class="grid cols-2">
        <div class="card" style="padding: 18px;">
          <h3 style="margin-bottom: 12px;">🔥 트렌드 AI 요약</h3>
          <div class="controls">
            <select class="select" id="trendRegion"></select>
            <button class="btn" id="trendGo">트렌드 분석</button>
          </div>
          <div id="trendOut"></div>
        </div>
        <div class="card" style="padding: 18px;">
          <h3 style="margin-bottom: 12px;">✍️ 영상 제목 추천</h3>
          <div class="controls">
            <input class="input" id="topic" placeholder="주제 (예: 다이어트, AI 뉴스)" style="min-width: 200px;">
            <select class="select" id="style">
              <option>일반</option><option>궁금증 유발</option><option>감성</option><option>숫자 강조</option><option>유머</option>
            </select>
            <button class="btn accent2" id="titleGo">10개 추천</button>
          </div>
          <div id="titleOut"></div>
        </div>
      </div>
    </div>
  `;
  fillRegionSelect(document.getElementById('trendRegion'), 'KR');

  document.getElementById('trendGo').onclick = async () => {
    const region = document.getElementById('trendRegion').value;
    const out = document.getElementById('trendOut');
    out.innerHTML = '<div class="loading">🤖 분석 중...</div>';
    try {
      const res = await api('/api/ai/analyze-trend', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ region }) });
      out.innerHTML = `<div class="ai-output">${escapeHtml(res.analysis)}</div>`;
    } catch (e) { showError(out, e.message); }
  };
  document.getElementById('titleGo').onclick = async () => {
    const topic = document.getElementById('topic').value.trim();
    const style = document.getElementById('style').value;
    const out = document.getElementById('titleOut');
    if (!topic) { out.innerHTML = '<div class="error">주제를 입력하세요.</div>'; return; }
    out.innerHTML = '<div class="loading">🤖 제목 생성 중...</div>';
    try {
      const res = await api('/api/ai/suggest-titles', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ topic, style }) });
      out.innerHTML = `<div class="ai-output">${escapeHtml(res.titles)}</div>`;
    } catch (e) { showError(out, e.message); }
  };
}

/* ========= 라우터 ========= */
function parseHash() {
  const raw = location.hash.replace(/^#/, '') || '/';
  const [path, query = ''] = raw.split('?');
  return { path, params: new URLSearchParams(query) };
}

async function route() {
  const { path, params } = parseHash();
  markActiveNav(path.replace(/^\//, '') || 'home');
  try {
    if (path === '/' || path === '') return renderHome();
    if (path === '/ranking') return renderRanking();
    if (path === '/search') return renderSearch();
    if (path === '/channel') return renderChannel(params);
    if (path === '/compare') return renderCompare();
    if (path === '/calculator') return renderCalculator();
    if (path === '/ai') return renderAI();
    renderHome();
  } catch (e) {
    root.innerHTML = `<div class="container"><div class="error">⚠️ 페이지 로딩 실패: ${escapeHtml(e.message)}</div></div>`;
  }
}

window.addEventListener('hashchange', route);
window.addEventListener('load', route);
