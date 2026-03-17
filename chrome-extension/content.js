/**
 * YouTube 광고 구간 탐지기 - Content Script
 * YouTube 페이지 내에서 실행되어 실제 광고 데이터를 감지합니다.
 */

(function () {
  "use strict";

  const AD_DATA_KEY = "__yt_ad_detector_data";

  // 광고 데이터 저장소
  let detectedData = {
    videoId: "",
    videoTitle: "",
    channelName: "",
    videoDuration: 0,
    adSlots: [],        // YouTube 광고 슬롯 (프리롤/미드롤/포스트롤)
    adEvents: [],       // 실제로 재생된 광고 이벤트
    sponsorSegments: [],
    lastUpdate: 0,
  };

  // 시간 포맷팅
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

  // 현재 영상 ID 추출
  function getVideoId() {
    const params = new URLSearchParams(window.location.search);
    return params.get("v") || "";
  }

  // 영상 기본 정보 수집
  function getVideoInfo() {
    const player = document.querySelector("#movie_player");
    const titleEl = document.querySelector(
      "h1.ytd-watch-metadata yt-formatted-string, #title h1 yt-formatted-string"
    );
    const channelEl = document.querySelector(
      "#channel-name yt-formatted-string a, ytd-channel-name yt-formatted-string a"
    );

    detectedData.videoId = getVideoId();
    detectedData.videoTitle = titleEl ? titleEl.textContent.trim() : document.title;
    detectedData.channelName = channelEl ? channelEl.textContent.trim() : "";

    if (player && player.getDuration) {
      detectedData.videoDuration = player.getDuration();
    }
  }

  // ytInitialPlayerResponse에서 광고 슬롯 추출
  function extractAdSlotsFromPlayerResponse() {
    const slots = [];

    // 페이지 소스에서 ytInitialPlayerResponse 찾기
    const scripts = document.querySelectorAll("script");
    let playerResponse = null;

    for (const script of scripts) {
      const text = script.textContent;
      if (text.includes("ytInitialPlayerResponse")) {
        const match = text.match(
          /var\s+ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;/
        );
        if (match) {
          try {
            playerResponse = JSON.parse(match[1]);
          } catch (e) {
            // 파싱 실패
          }
        }
      }
    }

    if (playerResponse) {
      // adPlacements 추출
      const adPlacements = playerResponse.adPlacements || [];
      for (const placement of adPlacements) {
        const renderer = placement.adPlacementRenderer || {};
        const config = (renderer.config || {}).adPlacementConfig || {};
        const offset = (config.adTimeOffset || {}).offsetStartMilliseconds;
        if (offset !== undefined) {
          const ms = parseInt(offset, 10);
          slots.push({
            timeMs: ms,
            timeFormatted: formatTime(ms / 1000),
            type: getAdType(ms),
            source: "adPlacements",
          });
        }
      }
    }

    return slots;
  }

  // 광고 유형 판별
  function getAdType(offsetMs) {
    if (offsetMs === 0) return "프리롤";
    if (detectedData.videoDuration > 0 && offsetMs >= detectedData.videoDuration * 1000 - 1000) {
      return "포스트롤";
    }
    return "미드롤";
  }

  // YouTube 플레이어에서 광고 cue point 직접 추출
  function extractAdCuePoints() {
    const slots = [];
    const player = document.querySelector("#movie_player");

    if (!player) return slots;

    // 방법 1: 프로그레스바의 광고 마커 (노란색 점)에서 추출
    const adMarkers = document.querySelectorAll(
      ".ytp-ad-marker-background, .ytp-chapter-hover-container[style*='background: rgb(255, 204, 0)']"
    );

    // 방법 2: 프로그레스바에서 광고 구간 직접 추출
    const progressBar = document.querySelector(".ytp-progress-list");
    if (progressBar) {
      const adSegments = progressBar.querySelectorAll(
        ".ytp-play-progress[style*='background: rgb(255, 204, 0)'], .ytp-ad-progress-list"
      );
    }

    // 방법 3: getProgressState 등 플레이어 API 활용
    if (player.getAdState) {
      try {
        const adState = player.getAdState();
        if (adState) {
          slots.push({
            timeMs: 0,
            timeFormatted: "현재",
            type: "광고 재생 중",
            source: "playerAPI",
          });
        }
      } catch (e) {}
    }

    // 방법 4: 챕터 마커에서 광고 구간 유추
    const chapters = document.querySelectorAll(
      ".ytp-progress-bar-container .ytp-chapters-container > div"
    );

    return slots;
  }

  // 프로그레스바의 노란색 광고 마커 위치를 직접 읽기
  function extractAdMarkersFromProgressBar() {
    const slots = [];
    const duration = detectedData.videoDuration;
    if (duration <= 0) return slots;

    // 광고 마커 (노란색 점들)
    const markers = document.querySelectorAll(
      ".ytp-ad-marker-background"
    );

    markers.forEach((marker) => {
      const style = marker.getAttribute("style") || "";
      const leftMatch = style.match(/left:\s*([\d.]+)%/);
      if (leftMatch) {
        const percent = parseFloat(leftMatch[1]);
        const timeSec = (percent / 100) * duration;
        const timeMs = Math.round(timeSec * 1000);
        slots.push({
          timeMs,
          timeFormatted: formatTime(timeSec),
          type: getAdType(timeMs),
          source: "progressBar",
        });
      }
    });

    return slots;
  }

  // 현재 광고 재생 상태 감지
  function detectCurrentAdState() {
    const player = document.querySelector("#movie_player");
    if (!player) return null;

    // 광고 재생 중인지 확인
    const adOverlay = document.querySelector(".ytp-ad-player-overlay, .ytp-ad-overlay-container .ytp-ad-text");
    const adModule = document.querySelector(".ytp-ad-module");
    const skipButton = document.querySelector(".ytp-ad-skip-button, .ytp-skip-ad-button, .ytp-ad-skip-button-modern");
    const adText = document.querySelector(".ytp-ad-text, .ytp-ad-preview-text, .ytp-ad-simple-ad-badge");
    const adDuration = document.querySelector(".ytp-ad-duration-remaining");

    const isAdPlaying =
      player.classList.contains("ad-showing") ||
      player.classList.contains("ad-interrupting") ||
      !!adOverlay ||
      !!skipButton ||
      !!adText;

    if (isAdPlaying) {
      let adInfo = "광고 재생 중";
      if (adDuration) adInfo += ` (${adDuration.textContent})`;
      if (skipButton) adInfo += " [건너뛰기 가능]";
      return adInfo;
    }

    return null;
  }

  // SponsorBlock 데이터 조회
  async function fetchSponsorBlockData(videoId) {
    const categories = [
      "sponsor", "selfpromo", "interaction", "intro",
      "outro", "preview", "music_offtopic", "filler"
    ];
    const categoryLabels = {
      sponsor: "스폰서 광고",
      selfpromo: "자기 홍보",
      interaction: "구독/좋아요 요청",
      intro: "인트로",
      outro: "아웃트로",
      preview: "미리보기",
      music_offtopic: "관련 없는 음악",
      filler: "불필요한 구간",
    };

    const cats = categories.map((c) => `category=${c}`).join("&");
    const url = `https://sponsor.ajay.app/api/skipSegments?videoID=${videoId}&${cats}`;

    try {
      const resp = await fetch(url);
      if (resp.status === 404) return [];
      if (!resp.ok) return [];
      const data = await resp.json();
      return data.map((seg) => ({
        startMs: Math.round(seg.segment[0] * 1000),
        endMs: Math.round(seg.segment[1] * 1000),
        startFormatted: formatTime(seg.segment[0]),
        endFormatted: formatTime(seg.segment[1]),
        durationSec: Math.round((seg.segment[1] - seg.segment[0]) * 10) / 10,
        category: seg.category,
        categoryLabel: categoryLabels[seg.category] || seg.category,
        votes: seg.votes || 0,
      }));
    } catch (e) {
      return [];
    }
  }

  // 광고 재생 이벤트 모니터링
  function monitorAdEvents() {
    const player = document.querySelector("#movie_player");
    if (!player) return;

    // MutationObserver로 광고 상태 변화 감지
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "attributes" && mutation.attributeName === "class") {
          const classList = player.classList;
          if (classList.contains("ad-showing") || classList.contains("ad-interrupting")) {
            const currentTime = player.getCurrentTime ? player.getCurrentTime() : 0;
            const event = {
              timeMs: Math.round(currentTime * 1000),
              timeFormatted: formatTime(currentTime),
              timestamp: Date.now(),
              type: "ad_started",
            };

            // 중복 방지 (같은 시간대 5초 이내)
            const isDuplicate = detectedData.adEvents.some(
              (e) => Math.abs(e.timeMs - event.timeMs) < 5000 && Date.now() - e.timestamp < 30000
            );
            if (!isDuplicate) {
              detectedData.adEvents.push(event);
              saveData();
            }
          }
        }
      }
    });

    observer.observe(player, { attributes: true });
  }

  // 모든 광고 데이터 수집
  async function collectAllData() {
    const videoId = getVideoId();
    if (!videoId) return;

    getVideoInfo();

    // 1. 프로그레스바 광고 마커
    const progressBarSlots = extractAdMarkersFromProgressBar();

    // 2. PlayerResponse 광고 슬롯
    const playerSlots = extractAdSlotsFromPlayerResponse();

    // 3. Cue points
    const cueSlots = extractAdCuePoints();

    // 중복 제거하며 합치기
    const allSlots = [];
    const seen = new Set();

    for (const slot of [...progressBarSlots, ...playerSlots, ...cueSlots]) {
      const key = slot.timeMs;
      if (!seen.has(key)) {
        seen.add(key);
        allSlots.push(slot);
      }
    }

    // 실제 감지된 광고 이벤트도 슬롯에 추가
    for (const event of detectedData.adEvents) {
      if (!seen.has(event.timeMs)) {
        seen.add(event.timeMs);
        allSlots.push({
          timeMs: event.timeMs,
          timeFormatted: event.timeFormatted,
          type: getAdType(event.timeMs),
          source: "실시간 감지",
        });
      }
    }

    allSlots.sort((a, b) => a.timeMs - b.timeMs);
    detectedData.adSlots = allSlots;

    // 4. SponsorBlock
    detectedData.sponsorSegments = await fetchSponsorBlockData(videoId);
    detectedData.lastUpdate = Date.now();

    saveData();
  }

  // 데이터 저장 (popup에서 읽을 수 있도록)
  function saveData() {
    try {
      window.sessionStorage.setItem(AD_DATA_KEY, JSON.stringify(detectedData));
    } catch (e) {}

    // chrome.storage도 사용
    try {
      if (chrome && chrome.runtime) {
        chrome.runtime.sendMessage({
          type: "adData",
          data: detectedData,
        });
      }
    } catch (e) {}
  }

  // 메시지 수신 (popup에서 데이터 요청)
  if (chrome && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.type === "getData") {
        // 최신 데이터 갱신
        collectAllData().then(() => {
          sendResponse({ data: detectedData });
        });
        return true; // async response
      }
      if (request.type === "refresh") {
        collectAllData().then(() => {
          sendResponse({ data: detectedData });
        });
        return true;
      }
    });
  }

  // 초기화
  function init() {
    // 영상 로딩 대기 후 데이터 수집
    setTimeout(() => {
      collectAllData();
      monitorAdEvents();
    }, 2000);

    // 주기적으로 프로그레스바 마커 갱신 (영상 로딩 후 마커가 늦게 뜰 수 있음)
    setTimeout(() => collectAllData(), 5000);
    setTimeout(() => collectAllData(), 10000);

    // 페이지 이동 감지 (YouTube SPA)
    let lastUrl = location.href;
    const urlObserver = new MutationObserver(() => {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        detectedData = {
          videoId: "",
          videoTitle: "",
          channelName: "",
          videoDuration: 0,
          adSlots: [],
          adEvents: [],
          sponsorSegments: [],
          lastUpdate: 0,
        };
        setTimeout(() => {
          collectAllData();
          monitorAdEvents();
        }, 3000);
      }
    });
    urlObserver.observe(document.body, { childList: true, subtree: true });
  }

  // DOM 준비 후 실행
  if (document.readyState === "complete" || document.readyState === "interactive") {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
