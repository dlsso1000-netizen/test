#!/usr/bin/env python3
"""
영상 프롬프트 추출 도구 (Multi-Platform Video Prompt Extractor)

YouTube, TikTok, Instagram, Sora 커뮤니티 등 다양한 플랫폼의 영상에서
AI 생성 프롬프트를 역추출합니다.

지원 플랫폼:
  - YouTube (youtube.com, youtu.be)
  - TikTok (tiktok.com)
  - Instagram Reels (instagram.com/reel/...)
  - Sora 커뮤니티 (sora.com)
  - 로컬 영상 파일 (.mp4, .mov, .avi, .webm 등)

분석 모드:
  1. Vision API 분석 - 영상 프레임을 AI로 분석하여 프롬프트 역추출
  2. URL 스크래핑 - 플랫폼 페이지에서 메타데이터/설명 추출
  3. C2PA 메타데이터 - AI 생성 출처 확인
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ─── 플랫폼 감지 ───────────────────────────────────────────────

PLATFORM_PATTERNS = {
    "youtube": [
        r"(youtube\.com|youtu\.be)",
    ],
    "tiktok": [
        r"tiktok\.com",
    ],
    "instagram": [
        r"instagram\.com",
    ],
    "sora": [
        r"sora\.com",
    ],
}


def detect_platform(url):
    """URL에서 플랫폼 감지"""
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url):
                return platform
    return "unknown"


# ─── 의존성 확인 ───────────────────────────────────────────────

def check_dependencies(need_openai=True):
    """필요한 패키지 확인"""
    missing = []
    if requests is None:
        missing.append("requests")
    if need_openai and OpenAI is None:
        missing.append("openai")
    if missing:
        print(f"[!] 필요한 패키지가 없습니다: {', '.join(missing)}")
        print(f"    설치: pip install {' '.join(missing)}")
        return False
    return True


def check_ytdlp():
    """yt-dlp 설치 확인"""
    if shutil.which("yt-dlp"):
        return True
    print("[!] yt-dlp가 설치되어 있지 않습니다.")
    print("    설치: pip install yt-dlp")
    print("    또는: brew install yt-dlp  (macOS)")
    return False


def check_ffmpeg():
    """ffmpeg 설치 확인"""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return True
    print("[!] ffmpeg/ffprobe가 설치되어 있지 않습니다.")
    print("    설치: sudo apt install ffmpeg  (Ubuntu/Debian)")
    print("          brew install ffmpeg       (macOS)")
    return False


# ─── 영상 다운로드 (yt-dlp) ────────────────────────────────────

def download_video(url, output_dir=None):
    """yt-dlp로 영상 다운로드 (YouTube, TikTok, Instagram 등)"""
    if not check_ytdlp():
        return None

    output_dir = output_dir or tempfile.mkdtemp()
    output_path = os.path.join(output_dir, "downloaded_video.mp4")

    platform = detect_platform(url)
    platform_names = {
        "youtube": "YouTube",
        "tiktok": "TikTok",
        "instagram": "Instagram",
        "sora": "Sora",
        "unknown": "영상",
    }
    print(f"[*] {platform_names.get(platform, '영상')} 다운로드 중: {url}")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        "--max-filesize", "200M",
    ]

    # 틱톡 워터마크 없는 버전 시도
    if platform == "tiktok":
        cmd.extend(["--extractor-args", "tiktok:api_hostname=api22-normal-c-useast2a.tiktokv.com"])

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"[+] 다운로드 완료: {output_path}")
            return output_path
        else:
            # mp4가 아닌 다른 형식으로 저장되었을 수 있음
            for f in os.listdir(output_dir):
                full_path = os.path.join(output_dir, f)
                if os.path.isfile(full_path):
                    print(f"[+] 다운로드 완료: {full_path}")
                    return full_path
            print(f"[!] 다운로드 실패")
            if result.stderr:
                print(f"    오류: {result.stderr[:200]}")
            return None
    except subprocess.TimeoutExpired:
        print("[!] 다운로드 시간 초과 (2분)")
        return None
    except FileNotFoundError:
        print("[!] yt-dlp를 찾을 수 없습니다.")
        return None


def get_video_info(url):
    """yt-dlp로 영상 메타데이터 가져오기 (다운로드 없이)"""
    if not check_ytdlp():
        return None

    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-playlist",
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


# ─── 프레임 추출 ──────────────────────────────────────────────

def extract_frames(video_path, num_frames=4):
    """ffmpeg로 영상에서 프레임 추출"""
    if not check_ffmpeg():
        return []

    tmpdir = tempfile.mkdtemp()
    frames = []

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True
        )
        duration = float(result.stdout.strip())
        interval = duration / (num_frames + 1)

        for i in range(num_frames):
            timestamp = interval * (i + 1)
            output_path = os.path.join(tmpdir, f"frame_{i:03d}.jpg")
            subprocess.run(
                ["ffmpeg", "-ss", str(timestamp), "-i", video_path,
                 "-vframes", "1", "-q:v", "2", output_path,
                 "-y", "-loglevel", "error"],
                capture_output=True
            )
            if os.path.exists(output_path):
                frames.append(output_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"[!] 프레임 추출 실패: {e}")
        return []

    return frames


# ─── Vision API 분석 ──────────────────────────────────────────

def encode_image_base64(image_path):
    """이미지를 base64로 인코딩"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_with_vision_api(frames, api_key=None, platform="unknown", video_info=None):
    """OpenAI Vision API로 프레임 분석하여 프롬프트 역추출"""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[!] OPENAI_API_KEY가 설정되지 않았습니다.")
        print("    export OPENAI_API_KEY='your-key-here'")
        return None

    client = OpenAI(api_key=api_key)

    # 플랫폼별 컨텍스트 추가
    context = ""
    if video_info:
        title = video_info.get("title", "")
        description = video_info.get("description", "")
        tags = video_info.get("tags", [])
        if title:
            context += f"\n영상 제목: {title}"
        if description:
            context += f"\n영상 설명: {description[:500]}"
        if tags:
            context += f"\n태그: {', '.join(tags[:20])}"

    prompt_text = (
        "다음 프레임들은 영상에서 추출한 것입니다. "
        "이 프레임들을 분석하여 이 영상을 AI 영상 생성 도구(Sora 2, Runway, Kling 등)로 "
        "재현할 수 있는 프롬프트를 영어와 한국어로 각각 작성해주세요.\n"
        f"{context}\n\n"
        "다음 요소들을 상세히 포함해주세요:\n"
        "- 장면 묘사 (배경, 환경, 공간)\n"
        "- 캐릭터/피사체 설명 (외형, 의상, 표정)\n"
        "- 카메라 움직임 및 앵글 (팬, 틸트, 줌, 트래킹 등)\n"
        "- 조명 및 색감 (자연광, 네온, 컬러그레이딩 등)\n"
        "- 아트 스타일 (애니메이션, 실사, 3D, 시네마틱 등)\n"
        "- 분위기 및 톤 (긴장감, 평화, 액션 등)\n"
        "- 액션/동작 설명 (움직임, 전환, 이펙트)\n"
        "- 텍스트/자막이 있다면 해당 내용\n\n"
        "JSON 형식으로 응답해주세요:\n"
        "{\n"
        '  "prompt_en": "영문 프롬프트 (상세하게)",\n'
        '  "prompt_ko": "한국어 프롬프트 (상세하게)",\n'
        '  "style": "아트 스타일",\n'
        '  "camera": "카메라 워크",\n'
        '  "mood": "분위기/톤",\n'
        '  "duration_suggestion": "추천 영상 길이",\n'
        '  "recommended_tool": "추천 AI 도구 (Sora 2 / Runway / Kling / Pika 등)",\n'
        '  "tags": ["관련", "태그", "목록"]\n'
        "}"
    )

    content = [{"type": "text", "text": prompt_text}]

    for frame_path in frames:
        b64 = encode_image_base64(frame_path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    print("[*] OpenAI Vision API로 분석 중...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=3000
    )

    return response.choices[0].message.content


# ─── 플랫폼별 스크래핑 ────────────────────────────────────────

def scrape_platform_metadata(url):
    """플랫폼별 메타데이터 스크래핑"""
    platform = detect_platform(url)

    # yt-dlp로 메타데이터 가져오기 (가장 안정적)
    print(f"[*] 영상 메타데이터 가져오는 중...")
    info = get_video_info(url)

    if info:
        result = {}
        result["platform"] = platform
        result["title"] = info.get("title", "")
        result["description"] = info.get("description", "")
        result["uploader"] = info.get("uploader", "")
        result["tags"] = info.get("tags", [])
        result["duration"] = info.get("duration", 0)
        result["view_count"] = info.get("view_count", 0)
        result["like_count"] = info.get("like_count", 0)

        # 틱톡/인스타의 경우 설명에 프롬프트가 포함될 수 있음
        desc = info.get("description", "")
        prompt_hints = extract_prompt_from_description(desc)
        if prompt_hints:
            result["detected_prompts"] = prompt_hints

        return result

    # yt-dlp 실패 시 직접 스크래핑
    if platform == "sora":
        return scrape_sora_community(url)

    return None


def extract_prompt_from_description(description):
    """영상 설명에서 프롬프트 힌트 추출"""
    if not description:
        return []

    prompts = []

    # 일반적인 프롬프트 패턴
    patterns = [
        r"[Pp]rompt[:\s]+(.+?)(?:\n\n|\n#|$)",
        r"프롬프트[:\s]+(.+?)(?:\n\n|\n#|$)",
        r"[Ss]ora\s*(?:2)?\s*[Pp]rompt[:\s]+(.+?)(?:\n\n|\n#|$)",
        r"(?:generated|created)\s+(?:with|using)[:\s]+(.+?)(?:\n\n|\n#|$)",
        r"AI\s*(?:프롬프트|prompt)[:\s]+(.+?)(?:\n\n|\n#|$)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, description, re.DOTALL | re.IGNORECASE)
        prompts.extend(matches)

    return [p.strip() for p in prompts if len(p.strip()) > 10]


def scrape_sora_community(url):
    """Sora 커뮤니티 페이지에서 프롬프트 스크래핑"""
    if not requests:
        print("[!] requests 패키지가 필요합니다: pip install requests")
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[*] Sora 커뮤니티에서 프롬프트 추출 중: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        patterns = [
            r'"prompt"\s*:\s*"([^"]+)"',
            r'<meta[^>]*name="description"[^>]*content="([^"]+)"',
            r'"text"\s*:\s*"([^"]+)"',
            r'data-prompt="([^"]+)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                return {"platform": "sora", "detected_prompts": [matches[0]]}

        json_ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        for block in json_ld:
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    for key in ["description", "prompt", "text"]:
                        if key in data:
                            return {"platform": "sora", "detected_prompts": [data[key]]}
            except json.JSONDecodeError:
                continue

        return None

    except requests.RequestException as e:
        print(f"[!] 요청 실패: {e}")
        return None


# ─── C2PA 메타데이터 ──────────────────────────────────────────

def check_c2pa_metadata(video_path):
    """C2PA 메타데이터 확인"""
    print(f"[*] C2PA 메타데이터 확인 중: {video_path}")

    try:
        result = subprocess.run(
            ["c2patool", video_path],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        else:
            print("[i] C2PA 메타데이터가 없거나 c2patool이 설치되지 않았습니다.")
            return None
    except FileNotFoundError:
        print("[i] c2patool 미설치 (선택사항, AI 생성 확인용)")
        return None


# ─── 결과 출력 ─────────────────────────────────────────────────

def format_result(result, mode):
    """결과를 보기 좋게 출력"""
    print("\n" + "=" * 60)

    if mode == "vision":
        print("  AI Vision 분석 결과")
        print("=" * 60)
        try:
            json_match = re.search(r'\{.*"prompt_en".*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                print(f"\n[영문 프롬프트]\n{data.get('prompt_en', 'N/A')}")
                print(f"\n[한국어 프롬프트]\n{data.get('prompt_ko', 'N/A')}")
                print(f"\n[스타일] {data.get('style', 'N/A')}")
                print(f"[카메라] {data.get('camera', 'N/A')}")
                print(f"[분위기] {data.get('mood', 'N/A')}")
                print(f"[추천 길이] {data.get('duration_suggestion', 'N/A')}")
                print(f"[추천 도구] {data.get('recommended_tool', 'N/A')}")
                tags = data.get("tags", [])
                if tags:
                    print(f"[태그] {', '.join(tags)}")
            else:
                print(result)
        except (json.JSONDecodeError, AttributeError):
            print(result)

    elif mode == "metadata":
        print("  영상 메타데이터")
        print("=" * 60)
        if isinstance(result, dict):
            platform_names = {
                "youtube": "YouTube", "tiktok": "TikTok",
                "instagram": "Instagram", "sora": "Sora",
            }
            p = result.get("platform", "unknown")
            print(f"\n[플랫폼] {platform_names.get(p, p)}")
            if result.get("title"):
                print(f"[제목] {result['title']}")
            if result.get("uploader"):
                print(f"[업로더] {result['uploader']}")
            if result.get("description"):
                desc = result["description"]
                if len(desc) > 300:
                    desc = desc[:300] + "..."
                print(f"[설명] {desc}")
            if result.get("tags"):
                print(f"[태그] {', '.join(result['tags'][:15])}")
            if result.get("duration"):
                mins = int(result["duration"]) // 60
                secs = int(result["duration"]) % 60
                print(f"[길이] {mins}:{secs:02d}")
            if result.get("detected_prompts"):
                print(f"\n[발견된 프롬프트]")
                for i, p in enumerate(result["detected_prompts"], 1):
                    print(f"  {i}. {p}")
        else:
            print(f"\n{result}")

    elif mode == "c2pa":
        print("  C2PA 메타데이터")
        print("=" * 60)
        print(f"\n{result}")

    print("\n" + "=" * 60)


def save_result(result, output_path):
    """결과를 파일로 저장"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"\n[+] 결과 저장됨: {output_path}")


# ─── 메인 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="영상 프롬프트 추출 도구 (YouTube, TikTok, Instagram, Sora 등)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # YouTube 영상에서 프롬프트 역추출
  python video_prompt_extractor.py --url https://youtube.com/watch?v=xxxxx

  # TikTok 영상에서 프롬프트 역추출
  python video_prompt_extractor.py --url https://tiktok.com/@user/video/xxxxx

  # Instagram Reel에서 프롬프트 역추출
  python video_prompt_extractor.py --url https://instagram.com/reel/xxxxx

  # Sora 커뮤니티 영상
  python video_prompt_extractor.py --url https://sora.com/g/gen_xxxxx

  # 로컬 파일 분석
  python video_prompt_extractor.py --video my_video.mp4

  # 메타데이터만 빠르게 확인 (다운로드/분석 없이)
  python video_prompt_extractor.py --url https://youtube.com/watch?v=xxx --meta-only

  # 모든 분석 + 결과 저장
  python video_prompt_extractor.py --url https://tiktok.com/... --all -o result.txt

  # 프레임 수 지정 (더 정확한 분석)
  python video_prompt_extractor.py --url https://youtube.com/... --frames 8
        """
    )

    parser.add_argument("--video", "-v", help="분석할 로컬 영상 파일 경로")
    parser.add_argument("--url", "-u", help="영상 URL (YouTube, TikTok, Instagram, Sora 등)")
    parser.add_argument("--frames", "-f", type=int, default=4, help="추출할 프레임 수 (기본: 4)")
    parser.add_argument("--api-key", "-k", help="OpenAI API 키 (또는 OPENAI_API_KEY 환경변수)")
    parser.add_argument("--c2pa", action="store_true", help="C2PA 메타데이터만 확인")
    parser.add_argument("--meta-only", "-m", action="store_true", help="메타데이터만 확인 (다운로드 없이)")
    parser.add_argument("--all", "-a", action="store_true", help="모든 분석 방법 사용")
    parser.add_argument("--output", "-o", help="결과를 저장할 파일 경로")
    parser.add_argument("--keep-video", action="store_true", help="다운로드한 영상 파일 유지")

    args = parser.parse_args()

    if not args.video and not args.url:
        parser.print_help()
        print("\n[!] --video 또는 --url 옵션을 지정해주세요.")
        sys.exit(1)

    results = []
    downloaded_video = None
    video_info = None

    # ── URL 처리 ──
    if args.url:
        platform = detect_platform(args.url)
        platform_names = {
            "youtube": "YouTube", "tiktok": "TikTok",
            "instagram": "Instagram", "sora": "Sora", "unknown": "알 수 없는 플랫폼",
        }
        print(f"\n[*] 플랫폼 감지: {platform_names.get(platform, platform)}")

        # 1) 메타데이터 추출
        metadata = scrape_platform_metadata(args.url)
        if metadata:
            format_result(metadata, "metadata")
            results.append(f"[Metadata]\n{json.dumps(metadata, ensure_ascii=False, indent=2)}")
            video_info = metadata

        if args.meta_only:
            if not results:
                print("[!] 메타데이터를 가져올 수 없습니다.")
                sys.exit(1)
        else:
            # 2) 영상 다운로드 후 분석
            if not check_dependencies():
                sys.exit(1)

            downloaded_video = download_video(args.url)
            if downloaded_video:
                args.video = downloaded_video

    # ── 영상 파일 분석 ──
    if args.video and not args.meta_only:
        video_path = Path(args.video)
        if not video_path.exists():
            print(f"[!] 파일을 찾을 수 없습니다: {args.video}")
            sys.exit(1)

        # C2PA 메타데이터 확인
        if args.c2pa or args.all:
            c2pa_result = check_c2pa_metadata(str(video_path))
            if c2pa_result:
                format_result(c2pa_result, "c2pa")
                results.append(f"[C2PA Metadata]\n{c2pa_result}")

        # Vision API 분석
        if not args.c2pa or args.all:
            if not check_dependencies(need_openai=True):
                sys.exit(1)

            print(f"\n[*] 영상에서 프레임 추출 중 ({args.frames}개)...")
            frames = extract_frames(str(video_path), args.frames)

            if not frames:
                print("[!] 프레임 추출에 실패했습니다.")
                if not results:
                    sys.exit(1)
            else:
                print(f"[+] {len(frames)}개 프레임 추출 완료")

                platform = detect_platform(args.url) if args.url else "local"
                vision_result = analyze_with_vision_api(
                    frames, args.api_key, platform, video_info
                )
                if vision_result:
                    format_result(vision_result, "vision")
                    results.append(f"[Vision Analysis]\n{vision_result}")

                # 임시 프레임 정리
                for frame in frames:
                    try:
                        os.remove(frame)
                    except OSError:
                        pass

        # 다운로드한 영상 정리
        if downloaded_video and not args.keep_video:
            try:
                os.remove(downloaded_video)
                print(f"[i] 임시 영상 파일 삭제됨")
            except OSError:
                pass

    # ── 결과 저장 ──
    if args.output and results:
        combined = "\n\n" + "=" * 60 + "\n\n"
        save_result(combined.join(results), args.output)

    if not results:
        print("\n[!] 프롬프트를 추출하지 못했습니다.")
        sys.exit(1)

    print("\n[완료] 프롬프트 추출이 완료되었습니다!")


if __name__ == "__main__":
    main()
