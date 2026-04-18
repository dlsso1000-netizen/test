/* 공용 유틸 */
const REGIONS = [
  { code: 'KR', name: '🇰🇷 한국' },
  { code: 'US', name: '🇺🇸 미국' },
  { code: 'JP', name: '🇯🇵 일본' },
  { code: 'GB', name: '🇬🇧 영국' },
  { code: 'DE', name: '🇩🇪 독일' },
  { code: 'FR', name: '🇫🇷 프랑스' },
  { code: 'IN', name: '🇮🇳 인도' },
  { code: 'BR', name: '🇧🇷 브라질' },
  { code: 'CA', name: '🇨🇦 캐나다' },
  { code: 'AU', name: '🇦🇺 호주' },
  { code: 'VN', name: '🇻🇳 베트남' },
  { code: 'TW', name: '🇹🇼 대만' },
];

function formatNumber(n) {
  n = Number(n || 0);
  if (n >= 1e8) return (n / 1e8).toFixed(1) + '억';
  if (n >= 1e4) return (n / 1e4).toFixed(1) + '만';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + '천';
  return n.toLocaleString();
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return '방금 전';
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}일 전`;
  if (diff < 2592000) return `${Math.floor(diff / 604800)}주 전`;
  if (diff < 31536000) return `${Math.floor(diff / 2592000)}개월 전`;
  return `${Math.floor(diff / 31536000)}년 전`;
}

function escapeHtml(str) {
  return String(str || '').replace(/[&<>"']/g, (s) => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[s]));
}

// 간단 fetch JSON 래퍼 + 에러 처리
async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  let data;
  try { data = await res.json(); } catch (_) { throw new Error(`HTTP ${res.status}`); }
  if (!data.ok && data.error) throw new Error(data.error);
  return data;
}

function showError(container, msg) {
  container.innerHTML = `<div class="error">⚠️ ${escapeHtml(msg)}</div>`;
}

// 국가 <select> 채우기
function fillRegionSelect(selectEl, defaultCode = 'KR') {
  selectEl.innerHTML = REGIONS.map((r) => `<option value="${r.code}" ${r.code === defaultCode ? 'selected' : ''}>${r.name}</option>`).join('');
}

// 카테고리 <select> 채우기 (API 호출)
async function fillCategorySelect(selectEl, region = 'KR') {
  selectEl.innerHTML = '<option value="">⏳ 불러오는 중...</option>';
  try {
    const data = await api(`/api/categories?region=${region}`);
    const opts = ['<option value="">전체 카테고리</option>']
      .concat((data.items || []).map((c) => `<option value="${c.id}">${escapeHtml(c.snippet.title)}</option>`));
    selectEl.innerHTML = opts.join('');
  } catch (e) {
    selectEl.innerHTML = `<option value="">전체 카테고리</option>`;
  }
}

// 네비게이션 하이라이트
function markActiveNav(hash) {
  document.querySelectorAll('.nav-links a').forEach((a) => {
    if (a.dataset.page === hash) a.classList.add('active');
    else a.classList.remove('active');
  });
}

// ISO 8601 duration → "12:34"
function formatDuration(iso) {
  if (!iso) return '';
  const match = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!match) return '';
  const h = Number(match[1] || 0);
  const m = Number(match[2] || 0);
  const s = Number(match[3] || 0);
  const pad = (n) => String(n).padStart(2, '0');
  return h ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}
