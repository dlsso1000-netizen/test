/**
 * YouTube 광고 구간 탐지기 - Popup Script
 */

const statusEl = document.getElementById("status");
const contentEl = document.getElementById("content");
const adNowEl = document.getElementById("ad-now-container");
const refreshBtn = document.getElementById("refreshBtn");

function formatTime(seconds) {
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) {
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  }
  return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
}

function getBadgeClass(type) {
  if (type.includes("프리롤")) return "preroll";
  if (type.includes("미드롤")) return "midroll";
  if (type.includes("포스트롤")) return "postroll";
  return "detected";
}

function renderResults(data) {
  if (!data || !data.videoId) {
    statusEl.textContent = "YouTube 영상 페이지에서 사용해주세요.";
    statusEl.className = "status error";
    contentEl.innerHTML = "";
    return;
  }

  const elapsed = Date.now() - data.lastUpdate;
  const sec = Math.round(elapsed / 1000);
  statusEl.textContent = `마지막 갱신: ${sec < 5 ? "방금" : sec + "초 전"}`;
  statusEl.className = "status";

  let html = "";

  // 영상 정보
  html += `<div class="video-info">`;
  html += `<div class="video-title">${escapeHtml(data.videoTitle)}</div>`;
  html += `<div class="video-meta">${escapeHtml(data.channelName)} · ${formatTime(data.videoDuration)} · ${data.videoId}</div>`;
  html += `</div>`;

  // 광고 슬롯
  const slots = data.adSlots || [];
  html += `<div class="section">`;
  html += `<div class="section-title">광고 슬롯 <span class="count">${slots.length}개</span></div>`;
  if (slots.length > 0) {
    for (const slot of slots) {
      const badgeClass = getBadgeClass(slot.type);
      html += `<div class="ad-item">`;
      html += `<span class="ad-badge ${badgeClass}">${slot.type}</span>`;
      html += `<span>${slot.timeFormatted}</span>`;
      if (slot.source) html += `<span style="color:#999;margin-left:8px;font-size:10px">(${slot.source})</span>`;
      html += `</div>`;
    }
  } else {
    html += `<div class="empty">감지된 광고 슬롯이 없습니다.</div>`;
    html += `<div class="empty">영상을 잠시 재생하면 광고가 감지될 수 있습니다.</div>`;
  }
  html += `</div>`;

  // 실시간 감지된 광고
  const events = data.adEvents || [];
  if (events.length > 0) {
    html += `<div class="section">`;
    html += `<div class="section-title">실시간 감지된 광고 <span class="count">${events.length}개</span></div>`;
    for (const ev of events) {
      html += `<div class="ad-item">`;
      html += `<span class="ad-badge detected">감지</span>`;
      html += `<span>${ev.timeFormatted}에서 광고 재생됨</span>`;
      html += `</div>`;
    }
    html += `</div>`;
  }

  // SponsorBlock
  const sponsors = data.sponsorSegments || [];
  html += `<div class="section">`;
  html += `<div class="section-title">SponsorBlock 스폰서 구간 <span class="count">${sponsors.length}개</span></div>`;
  if (sponsors.length > 0) {
    for (const s of sponsors) {
      html += `<div class="sponsor-item">`;
      html += `<span class="sponsor-badge">${s.categoryLabel}</span>`;
      html += `<span>${s.startFormatted} ~ ${s.endFormatted} (${s.durationSec}초)</span>`;
      html += `</div>`;
    }
  } else {
    html += `<div class="empty">SponsorBlock에 등록된 구간이 없습니다.</div>`;
  }
  html += `</div>`;

  // 타임라인
  if (data.videoDuration > 0 && (slots.length > 0 || sponsors.length > 0)) {
    const barWidth = 40;
    let bar = Array(barWidth).fill("-");

    for (const slot of slots) {
      const pos = Math.min(
        Math.floor((slot.timeMs / 1000 / data.videoDuration) * (barWidth - 1)),
        barWidth - 1
      );
      bar[pos] = '<span class="ad">V</span>';
    }
    for (const s of sponsors) {
      const sp = Math.min(
        Math.floor((s.startMs / 1000 / data.videoDuration) * (barWidth - 1)),
        barWidth - 1
      );
      const ep = Math.min(
        Math.floor((s.endMs / 1000 / data.videoDuration) * (barWidth - 1)),
        barWidth - 1
      );
      for (let p = sp; p <= ep; p++) {
        bar[p] = bar[p].includes("ad") ? '<span class="ad">X</span>' : '<span class="sponsor">#</span>';
      }
    }

    html += `<div class="timeline">`;
    html += `<div class="timeline-bar">[${bar.join("")}]</div>`;
    html += `<div>0:00${" ".repeat(Math.max(0, barWidth - 10))}${formatTime(data.videoDuration)}</div>`;
    html += `</div>`;
    html += `<div class="legend">V = 광고 · # = 스폰서 · X = 둘 다</div>`;
  }

  contentEl.innerHTML = html;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function loadData() {
  statusEl.textContent = "데이터 로딩 중...";
  statusEl.className = "status loading";

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    if (!tab || !tab.url || !tab.url.includes("youtube.com/watch")) {
      statusEl.textContent = "YouTube 영상 페이지를 열어주세요.";
      statusEl.className = "status error";
      contentEl.innerHTML = `
        <div style="padding:20px 16px;text-align:center;color:#999">
          <p>YouTube에서 영상을 재생한 후</p>
          <p>이 확장 프로그램 아이콘을 클릭하세요.</p>
        </div>
      `;
      return;
    }

    chrome.tabs.sendMessage(tab.id, { type: "getData" }, (response) => {
      if (chrome.runtime.lastError) {
        statusEl.textContent = "페이지를 새로고침 후 다시 시도해주세요.";
        statusEl.className = "status error";
        contentEl.innerHTML = `
          <div style="padding:16px;color:#999;font-size:12px">
            <p>Content script가 로드되지 않았습니다.</p>
            <p>YouTube 페이지를 새로고침(F5)한 후 다시 시도해주세요.</p>
          </div>
        `;
        return;
      }

      if (response && response.data) {
        renderResults(response.data);
      } else {
        statusEl.textContent = "데이터를 가져오지 못했습니다.";
        statusEl.className = "status error";
      }
    });
  });
}

refreshBtn.addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { type: "refresh" }, (response) => {
        if (response && response.data) {
          renderResults(response.data);
        }
      });
    }
  });
});

// 팝업 열릴 때 자동 로딩
loadData();
