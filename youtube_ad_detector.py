#!/usr/bin/env python3
"""
YouTube 광고 구간 탐지기
- YouTube 영상의 프리롤/미드롤/포스트롤 광고 삽입 위치를 추출합니다.
- YouTube 웹페이지 HTML에서 직접 광고 cue point를 파싱합니다.
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


def format_time_from_sec(seconds: float) -> str:
    """초를 HH:MM:SS 형식으로 변환합니다."""
    return format_time(int(seconds * 1000))


def get_ad_type(offset_ms: int, total_ms: int) -> str:
    """광고 위치에 따른 유형을 반환합니다."""
    if offset_ms == 0:
        return "프리롤 (영상 시작 전)"
    elif total_ms > 0 and offset_ms >= total_ms - 1000:
        return "포스트롤 (영상 종료 후)"
    else:
        return "미드롤 (영상 중간)"


def fetch_youtube_page(video_id: str) -> str:
    """YouTube 영상 웹페이지 HTML을 가져옵니다."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def extract_ytInitialPlayerResponse(html: str) -> dict:
    """HTML에서 ytInitialPlayerResponse JSON을 추출합니다."""
    # ytInitialPlayerResponse 변수를 찾기
    patterns = [
        r'var\s+ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;',
        r'ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    # 더 넓은 범위로 시도
    match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.*?"}\s*})\s*;', html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return {}


def extract_ytInitialData(html: str) -> dict:
    """HTML에서 ytInitialData JSON을 추출합니다."""
    patterns = [
        r'var\s+ytInitialData\s*=\s*(\{.+?\})\s*;',
        r'ytInitialData\s*=\s*(\{.+?\})\s*;',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return {}


def get_player_response_via_api(video_id: str) -> dict:
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
        "racyCheckOk": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_all_ads(player_response: dict, total_length_ms: int = 0) -> list[dict]:
    """Player response에서 모든 광고 위치를 추출합니다 (프리롤 포함)."""
    ads = []

    # 1. adPlacements에서 추출
    ad_placements = player_response.get("adPlacements", [])
    for placement in ad_placements:
        renderer = placement.get("adPlacementRenderer", {})
        config = renderer.get("config", {}).get("adPlacementConfig", {})
        kind = config.get("adTimeOffset", {}).get("offsetStartMilliseconds")
        ad_kind = config.get("kind", "")
        if kind is not None:
            offset_ms = int(kind)
            ads.append({
                "time_ms": offset_ms,
                "time_formatted": format_time(offset_ms),
                "type": get_ad_type(offset_ms, total_length_ms),
                "kind": ad_kind,
            })

    # 2. playerAds에서 추출
    player_ads = player_response.get("playerAds", [])
    for ad in player_ads:
        ad_renderer = ad.get("adPlacementRenderer", {})
        config = ad_renderer.get("config", {}).get("adPlacementConfig", {})
        ad_kind = config.get("kind", "")
        offset_info = config.get("adTimeOffset", {})
        kind = offset_info.get("offsetStartMilliseconds")
        if kind is not None:
            offset_ms = int(kind)
            ads.append({
                "time_ms": offset_ms,
                "time_formatted": format_time(offset_ms),
                "type": get_ad_type(offset_ms, total_length_ms),
                "kind": ad_kind,
            })
        # cueRanges도 체크
        cue_ranges = ad_renderer.get("cueRanges", [])
        for cue in cue_ranges:
            start_ms = cue.get("startTimeMs")
            if start_ms is not None:
                start_ms = int(start_ms)
                ads.append({
                    "time_ms": start_ms,
                    "time_formatted": format_time(start_ms),
                    "type": get_ad_type(start_ms, total_length_ms),
                    "kind": "cueRange",
                })

    # 중복 제거 및 정렬
    seen = set()
    unique = []
    for a in sorted(ads, key=lambda x: x["time_ms"]):
        if a["time_ms"] not in seen:
            seen.add(a["time_ms"])
            unique.append(a)

    return unique


def extract_ad_slots_from_html(html: str, total_length_ms: int = 0) -> list[dict]:
    """HTML에서 광고 cue point를 다양한 방법으로 추출합니다."""
    ads = []

    # 방법 1: cueRanges 패턴 (JSON 내부)
    cue_pattern = r'"cueRanges"\s*:\s*\[(.*?)\]'
    for match in re.finditer(cue_pattern, html):
        try:
            cue_data = json.loads(f"[{match.group(1)}]")
            for cue in cue_data:
                start_ms = cue.get("startTimeMs")
                if start_ms is not None:
                    start_ms = int(start_ms)
                    ads.append({
                        "time_ms": start_ms,
                        "time_formatted": format_time(start_ms),
                        "type": get_ad_type(start_ms, total_length_ms),
                        "kind": "cueRange_html",
                    })
        except (json.JSONDecodeError, ValueError):
            pass

    # 방법 2: adPlacementConfig 내의 offsetStartMilliseconds
    offset_pattern = r'"offsetStartMilliseconds"\s*:\s*"?(\d+)"?'
    for match in re.finditer(offset_pattern, html):
        offset_ms = int(match.group(1))
        ads.append({
            "time_ms": offset_ms,
            "time_formatted": format_time(offset_ms),
            "type": get_ad_type(offset_ms, total_length_ms),
            "kind": "offset_html",
        })

    # 방법 3: adSlots 또는 ad_tag 패턴
    ad_slot_pattern = r'"adSlots"\s*:\s*\[(.*?)\]'
    for match in re.finditer(ad_slot_pattern, html, re.DOTALL):
        try:
            slot_data = json.loads(f"[{match.group(1)}]")
            for slot in slot_data:
                offset = slot.get("adPlacementRenderer", {}).get("config", {}).get(
                    "adPlacementConfig", {}
                ).get("adTimeOffset", {}).get("offsetStartMilliseconds")
                if offset is not None:
                    offset_ms = int(offset)
                    ads.append({
                        "time_ms": offset_ms,
                        "time_formatted": format_time(offset_ms),
                        "type": get_ad_type(offset_ms, total_length_ms),
                        "kind": "adSlot_html",
                    })
        except (json.JSONDecodeError, ValueError):
            pass

    # 중복 제거
    seen = set()
    unique = []
    for a in sorted(ads, key=lambda x: x["time_ms"]):
        if a["time_ms"] not in seen:
            seen.add(a["time_ms"])
            unique.append(a)

    return unique


def get_sponsorblock_segments(video_id: str) -> list[dict]:
    """SponsorBlock API에서 스폰서/광고 구간을 가져옵니다."""
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

    all_categories = list(category_labels.keys())
    segments = []

    # 방법 1: 직접 API (videoID로 직접 조회 - 더 정확함)
    try:
        cats = "&".join(f"category={c}" for c in all_categories)
        url = f"https://sponsor.ajay.app/api/skipSegments?videoID={video_id}&{cats}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "YouTubeAdDetector/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for seg in data:
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
    except urllib.error.HTTPError as e:
        if e.code == 404:
            pass  # 이 영상에 등록된 구간 없음
        else:
            raise RuntimeError(f"SponsorBlock 직접 API 오류 (HTTP {e.code})")
    except urllib.error.URLError as e:
        raise RuntimeError(f"SponsorBlock 연결 실패: {e.reason}")

    # 방법 2: 해시 기반 API (백업)
    if not segments:
        try:
            hash_prefix = hashlib.sha256(video_id.encode()).hexdigest()[:4]
            url = f"https://sponsor.ajay.app/api/skipSegments/{hash_prefix}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "YouTubeAdDetector/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
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
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pass  # 등록된 구간 없음
            else:
                raise RuntimeError(f"SponsorBlock 해시 API 오류 (HTTP {e.code})")
        except urllib.error.URLError as e:
            raise RuntimeError(f"SponsorBlock 연결 실패: {e.reason}")

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


def print_results(video_id: str, video_info: dict, ads: list, sponsors: list):
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

    # 광고 슬롯 (프리롤 + 미드롤 + 포스트롤)
    preroll = [a for a in ads if a["time_ms"] == 0]
    midroll = [a for a in ads if 0 < a["time_ms"] < video_info["length_seconds"] * 1000]
    postroll = [a for a in ads if a["time_ms"] >= video_info["length_seconds"] * 1000 and a["time_ms"] > 0]

    print(f"\n광고 슬롯 (총 {len(ads)}개)")
    print("-" * 40)

    if preroll:
        print(f"\n  [프리롤 광고] {len(preroll)}개")
        for i, a in enumerate(preroll, 1):
            print(f"    {i}. 영상 시작 전 (00:00)")

    if midroll:
        print(f"\n  [미드롤 광고] {len(midroll)}개")
        for i, m in enumerate(midroll, 1):
            print(f"    {i}. {m['time_formatted']}  (영상 시작 후 {m['time_ms'] // 1000}초)")

    if postroll:
        print(f"\n  [포스트롤 광고] {len(postroll)}개")
        for i, a in enumerate(postroll, 1):
            print(f"    {i}. 영상 종료 후")

    if not ads:
        print("  광고 슬롯이 감지되지 않았습니다.")
        print("  (광고가 비활성화되었거나, 비로그인 상태에서 감지 불가)")

    # SponsorBlock 스폰서 구간
    print(f"\n SponsorBlock 크리에이터 스폰서 구간 ({len(sponsors)}개)")
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
    if ads or sponsors:
        print(f"\n 타임라인 시각화")
        print("-" * 40)
        total_sec = video_info["length_seconds"]
        if total_sec > 0:
            bar_width = 50
            timeline = list("-" * bar_width)

            for a in ads:
                if a["time_ms"] == 0:
                    timeline[0] = "V"
                else:
                    pos = int((a["time_ms"] / 1000) / total_sec * (bar_width - 1))
                    pos = min(pos, bar_width - 1)
                    timeline[pos] = "V"

            for s in sponsors:
                start_pos = int((s["start_ms"] / 1000) / total_sec * (bar_width - 1))
                end_pos = int((s["end_ms"] / 1000) / total_sec * (bar_width - 1))
                start_pos = min(start_pos, bar_width - 1)
                end_pos = min(end_pos, bar_width - 1)
                for p in range(start_pos, end_pos + 1):
                    if timeline[p] == "V":
                        timeline[p] = "X"
                    else:
                        timeline[p] = "#"

            print(f"  [{''.join(timeline)}]")
            print(f"  0:00{' ' * (bar_width - 8)}{video_info['length_formatted']}")
            print(f"\n  범례: V = 광고 슬롯  # = 스폰서 구간  X = 둘 다")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 영상의 광고 및 스폰서 구간을 탐지합니다.",
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="디버그 모드: API 원본 응답을 debug_response.json으로 저장",
    )
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.video)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n영상 분석 중... (ID: {video_id})")

    all_ads = []
    player_response = {}

    # 방법 1: YouTube 웹페이지 HTML에서 직접 파싱
    print("  [1/3] YouTube 웹페이지 분석 중...")
    try:
        html = fetch_youtube_page(video_id)
        player_response = extract_ytInitialPlayerResponse(html)

        if args.debug:
            with open("debug_page_response.json", "w", encoding="utf-8") as f:
                json.dump(player_response, f, ensure_ascii=False, indent=2)
            print(f"  -> 웹페이지 player response 저장: debug_page_response.json")

            # ad 관련 키만 별도 저장
            ad_keys = {}
            for key in ["adPlacements", "playerAds", "adSlots", "adBreakParams"]:
                if key in player_response:
                    ad_keys[key] = player_response[key]
            if ad_keys:
                with open("debug_ad_data.json", "w", encoding="utf-8") as f:
                    json.dump(ad_keys, f, ensure_ascii=False, indent=2)
                print(f"  -> 광고 데이터 저장: debug_ad_data.json")

        total_length_ms = int(player_response.get("videoDetails", {}).get("lengthSeconds", 0)) * 1000
        page_ads = extract_all_ads(player_response, total_length_ms)
        html_ads = extract_ad_slots_from_html(html, total_length_ms)

        # 두 결과 합치기
        seen = set()
        for a in page_ads + html_ads:
            if a["time_ms"] not in seen:
                seen.add(a["time_ms"])
                all_ads.append(a)

        print(f"  -> 웹페이지에서 {len(all_ads)}개 광고 슬롯 발견")
    except Exception as e:
        print(f"  -> 웹페이지 분석 실패: {e}")

    # 방법 2: InnerTube API로 보충
    print("  [2/3] InnerTube API 분석 중...")
    try:
        api_response = get_player_response_via_api(video_id)

        if args.debug:
            with open("debug_api_response.json", "w", encoding="utf-8") as f:
                json.dump(api_response, f, ensure_ascii=False, indent=2)
            print(f"  -> API response 저장: debug_api_response.json")

        if not player_response:
            player_response = api_response

        total_length_ms = int(api_response.get("videoDetails", {}).get("lengthSeconds", 0)) * 1000
        api_ads = extract_all_ads(api_response, total_length_ms)

        seen = {a["time_ms"] for a in all_ads}
        new_count = 0
        for a in api_ads:
            if a["time_ms"] not in seen:
                seen.add(a["time_ms"])
                all_ads.append(a)
                new_count += 1

        print(f"  -> API에서 {new_count}개 추가 광고 슬롯 발견")
    except Exception as e:
        print(f"  -> API 분석 실패: {e}")

    all_ads.sort(key=lambda x: x["time_ms"])

    video_info = get_video_info(player_response)

    # 방법 3: SponsorBlock 조회
    sponsors = []
    print("  [3/3] SponsorBlock 조회 중...")
    if not args.no_sponsorblock:
        try:
            sponsors = get_sponsorblock_segments(video_id)
            print(f"  -> SponsorBlock에서 {len(sponsors)}개 구간 발견")
        except Exception:
            print("  -> SponsorBlock 조회 실패 - 건너뜁니다")
    else:
        print("  -> 건너뜀")

    print()

    if args.json:
        result = {
            "video_id": video_id,
            "video_info": video_info,
            "ad_slots": all_ads,
            "sponsor_segments": sponsors,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_results(video_id, video_info, all_ads, sponsors)

    if not all_ads and not sponsors:
        print("참고: YouTube는 비로그인 상태에서 광고 데이터를 제한적으로 제공합니다.")
        print("      --debug 옵션으로 원본 응답을 저장해서 확인해볼 수 있습니다.")
        print("      예: python youtube_ad_detector.py 영상ID --debug")


if __name__ == "__main__":
    main()
