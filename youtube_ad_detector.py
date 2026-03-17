#!/usr/bin/env python3
"""
YouTube 미드롤 광고 구간 탐지기
- YouTube 영상의 미드롤 광고 삽입 위치를 추출합니다.
- SponsorBlock API를 통해 크리에이터가 삽입한 스폰서 구간도 확인합니다.
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.request
import urllib.error


def extract_video_id(url_or_id: str) -> str:
    """YouTube URL 또는 영상 ID에서 video ID를 추출합니다."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    raise ValueError(f"유효한 YouTube URL 또는 영상 ID가 아닙니다: {url_or_id}")


def format_time(ms: int) -> str:
    """밀리초를 HH:MM:SS 형식으로 변환합니다."""
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def get_player_response(video_id: str) -> dict:
    """YouTube InnerTube API를 통해 player response를 가져옵니다."""
    url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "videoId": video_id,
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "ko",
                "gl": "KR",
            }
        },
        "contentCheckOk": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_midroll_ads(player_response: dict) -> list[dict]:
    """Player response에서 미드롤 광고 위치를 추출합니다."""
    midrolls = []

    # adPlacements에서 추출
    ad_placements = player_response.get("adPlacements", [])
    for placement in ad_placements:
        renderer = placement.get("adPlacementRenderer", {})
        config = renderer.get("config", {}).get("adPlacementConfig", {})
        kind = config.get("adTimeOffset", {}).get("offsetStartMilliseconds")
        if kind is not None:
            offset_ms = int(kind)
            if offset_ms > 0:  # 프리롤(0ms) 제외
                midrolls.append({
                    "time_ms": offset_ms,
                    "time_formatted": format_time(offset_ms),
                    "type": "midroll_ad",
                })

    # playerAds에서도 추출 시도
    player_ads = player_response.get("playerAds", [])
    for ad in player_ads:
        ad_renderer = ad.get("adPlacementRenderer", {})
        cue_ranges = ad_renderer.get("cueRanges", [])
        for cue in cue_ranges:
            start_ms = cue.get("startTimeMs")
            if start_ms is not None:
                start_ms = int(start_ms)
                if start_ms > 0:
                    midrolls.append({
                        "time_ms": start_ms,
                        "time_formatted": format_time(start_ms),
                        "type": "midroll_ad",
                    })

    # 중복 제거 및 정렬
    seen = set()
    unique = []
    for m in sorted(midrolls, key=lambda x: x["time_ms"]):
        if m["time_ms"] not in seen:
            seen.add(m["time_ms"])
            unique.append(m)

    return unique


def get_sponsorblock_segments(video_id: str) -> list[dict]:
    """SponsorBlock API에서 스폰서/광고 구간을 가져옵니다."""
    # SponsorBlock은 videoID의 SHA256 해시 앞 4자리로 조회 가능
    hash_prefix = hashlib.sha256(video_id.encode()).hexdigest()[:4]
    url = f"https://sponsor.ajay.app/api/skipSegments/{hash_prefix}"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "YouTubeAdDetector/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise

    category_labels = {
        "sponsor": "스폰서 광고",
        "selfpromo": "자기 홍보",
        "interaction": "구독/좋아요 요청",
        "intro": "인트로",
        "outro": "아웃트로",
        "preview": "미리보기",
        "music_offtopic": "관련 없는 음악",
        "filler": "불필요한 구간",
    }

    segments = []
    for entry in data:
        if entry.get("videoID") != video_id:
            continue
        for seg in entry.get("segments", []):
            start_sec = seg["segment"][0]
            end_sec = seg["segment"][1]
            category = seg.get("category", "unknown")
            segments.append({
                "start_ms": int(start_sec * 1000),
                "end_ms": int(end_sec * 1000),
                "start_formatted": format_time(int(start_sec * 1000)),
                "end_formatted": format_time(int(end_sec * 1000)),
                "duration_sec": round(end_sec - start_sec, 1),
                "category": category,
                "category_label": category_labels.get(category, category),
                "votes": seg.get("votes", 0),
            })

    return sorted(segments, key=lambda x: x["start_ms"])


def get_video_info(player_response: dict) -> dict:
    """영상 기본 정보를 추출합니다."""
    details = player_response.get("videoDetails", {})
    return {
        "title": details.get("title", "알 수 없음"),
        "author": details.get("author", "알 수 없음"),
        "length_seconds": int(details.get("lengthSeconds", 0)),
        "length_formatted": format_time(int(details.get("lengthSeconds", 0)) * 1000),
        "view_count": details.get("viewCount", "알 수 없음"),
    }


def print_results(video_id: str, video_info: dict, midrolls: list, sponsors: list):
    """결과를 보기 좋게 출력합니다."""
    print("=" * 60)
    print("  YouTube 광고 구간 탐지 결과")
    print("=" * 60)
    print(f"  영상: {video_info['title']}")
    print(f"  채널: {video_info['author']}")
    print(f"  길이: {video_info['length_formatted']}")
    print(f"  조회수: {video_info['view_count']}")
    print(f"  ID: {video_id}")
    print("=" * 60)

    # 미드롤 광고
    print(f"\n📺 미드롤 광고 슬롯 ({len(midrolls)}개)")
    print("-" * 40)
    if midrolls:
        for i, m in enumerate(midrolls, 1):
            print(f"  {i}. {m['time_formatted']}  (영상 시작 후 {m['time_ms'] // 1000}초)")
    else:
        print("  미드롤 광고가 감지되지 않았습니다.")
        print("  (8분 미만 영상이거나 광고가 비활성화된 영상)")

    # SponsorBlock 스폰서 구간
    print(f"\n🏷️  SponsorBlock 크리에이터 스폰서 구간 ({len(sponsors)}개)")
    print("-" * 40)
    if sponsors:
        for i, s in enumerate(sponsors, 1):
            print(
                f"  {i}. [{s['category_label']}] "
                f"{s['start_formatted']} ~ {s['end_formatted']} "
                f"({s['duration_sec']}초, 투표: {s['votes']})"
            )
    else:
        print("  SponsorBlock에 등록된 구간이 없습니다.")

    # 타임라인 시각화
    if midrolls or sponsors:
        print(f"\n📊 타임라인 시각화")
        print("-" * 40)
        total_sec = video_info["length_seconds"]
        if total_sec > 0:
            bar_width = 50
            timeline = list("─" * bar_width)

            for m in midrolls:
                pos = int((m["time_ms"] / 1000) / total_sec * (bar_width - 1))
                pos = min(pos, bar_width - 1)
                timeline[pos] = "▼"

            for s in sponsors:
                start_pos = int((s["start_ms"] / 1000) / total_sec * (bar_width - 1))
                end_pos = int((s["end_ms"] / 1000) / total_sec * (bar_width - 1))
                start_pos = min(start_pos, bar_width - 1)
                end_pos = min(end_pos, bar_width - 1)
                for p in range(start_pos, end_pos + 1):
                    if timeline[p] == "▼":
                        timeline[p] = "◆"
                    else:
                        timeline[p] = "█"

            print(f"  ├{''.join(timeline)}┤")
            print(f"  0:00{' ' * (bar_width - 8)}{video_info['length_formatted']}")
            print(f"\n  범례: ▼ = 미드롤 광고  █ = 스폰서 구간  ◆ = 둘 다")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 영상의 미드롤 광고 및 스폰서 구간을 탐지합니다.",
    )
    parser.add_argument(
        "video",
        help="YouTube 영상 URL 또는 영상 ID",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="결과를 JSON 형식으로 출력",
    )
    parser.add_argument(
        "--no-sponsorblock",
        action="store_true",
        help="SponsorBlock 조회 건너뛰기",
    )
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.video)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n영상 분석 중... (ID: {video_id})")

    # YouTube player response 가져오기
    try:
        player_response = get_player_response(video_id)
    except Exception as e:
        print(f"오류: YouTube API 요청 실패 - {e}", file=sys.stderr)
        sys.exit(1)

    video_info = get_video_info(player_response)
    midrolls = extract_midroll_ads(player_response)

    # SponsorBlock 조회
    sponsors = []
    if not args.no_sponsorblock:
        try:
            sponsors = get_sponsorblock_segments(video_id)
        except Exception:
            print("  (SponsorBlock 조회 실패 - 건너뜁니다)")

    if args.json:
        result = {
            "video_id": video_id,
            "video_info": video_info,
            "midroll_ads": midrolls,
            "sponsor_segments": sponsors,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_results(video_id, video_info, midrolls, sponsors)


if __name__ == "__main__":
    main()
