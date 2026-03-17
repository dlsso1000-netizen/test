#!/usr/bin/env python3
"""
Sora 2 영상 프롬프트 추출 도구
Video Prompt Extractor for Sora 2

영상 파일 또는 URL에서 AI 생성 프롬프트를 역추출합니다.
3가지 모드 지원:
  1. 로컬 영상 파일 분석 (OpenAI Vision API)
  2. Sora 커뮤니티 URL에서 프롬프트 스크래핑
  3. C2PA 메타데이터 확인
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def check_dependencies():
    """필요한 패키지 확인"""
    missing = []
    if requests is None:
        missing.append("requests")
    if OpenAI is None:
        missing.append("openai")
    if missing:
        print(f"[!] 필요한 패키지가 없습니다: {', '.join(missing)}")
        print(f"    설치: pip install {' '.join(missing)}")
        return False
    return True


def extract_frames(video_path, num_frames=4):
    """ffmpeg를 사용해 영상에서 프레임 추출"""
    tmpdir = tempfile.mkdtemp()
    frames = []

    try:
        # 영상 길이 확인
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

    except FileNotFoundError:
        print("[!] ffmpeg/ffprobe가 설치되어 있지 않습니다.")
        print("    설치: sudo apt install ffmpeg  (Ubuntu/Debian)")
        print("          brew install ffmpeg       (macOS)")
        return []

    return frames


def encode_image_base64(image_path):
    """이미지를 base64로 인코딩"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_with_vision_api(frames, api_key=None):
    """OpenAI Vision API로 프레임 분석하여 프롬프트 역추출"""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[!] OPENAI_API_KEY가 설정되지 않았습니다.")
        print("    export OPENAI_API_KEY='your-key-here'")
        return None

    client = OpenAI(api_key=api_key)

    content = [
        {
            "type": "text",
            "text": (
                "다음 프레임들은 AI(Sora 2)로 생성된 영상에서 추출한 것입니다. "
                "이 프레임들을 분석하여 원본 영상을 생성하는 데 사용되었을 법한 "
                "Sora 2 프롬프트를 영어와 한국어로 각각 작성해주세요.\n\n"
                "다음 요소들을 포함해주세요:\n"
                "- 장면 묘사 (배경, 환경)\n"
                "- 캐릭터/피사체 설명\n"
                "- 카메라 움직임 및 앵글\n"
                "- 조명 및 색감\n"
                "- 아트 스타일 (애니메이션, 실사 등)\n"
                "- 분위기 및 톤\n"
                "- 액션/동작 설명\n\n"
                "JSON 형식으로 응답해주세요:\n"
                '{"prompt_en": "...", "prompt_ko": "...", '
                '"style": "...", "camera": "...", "mood": "..."}'
            )
        }
    ]

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
        max_tokens=2000
    )

    return response.choices[0].message.content


def scrape_sora_community(url):
    """Sora 커뮤니티 페이지에서 프롬프트 스크래핑"""
    if not requests:
        print("[!] requests 패키지가 필요합니다: pip install requests")
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[*] URL에서 프롬프트 추출 중: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # Sora 커뮤니티 페이지에서 프롬프트 패턴 찾기
        patterns = [
            r'"prompt"\s*:\s*"([^"]+)"',
            r'<meta[^>]*name="description"[^>]*content="([^"]+)"',
            r'"text"\s*:\s*"([^"]+)"',
            r'data-prompt="([^"]+)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                return matches[0]

        # JSON-LD 데이터 확인
        json_ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        for block in json_ld:
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    for key in ["description", "prompt", "text"]:
                        if key in data:
                            return data[key]
            except json.JSONDecodeError:
                continue

        print("[!] 페이지에서 프롬프트를 찾을 수 없습니다.")
        print("    Sora 커뮤니티 공개 영상 URL이 맞는지 확인해주세요.")
        return None

    except requests.RequestException as e:
        print(f"[!] 요청 실패: {e}")
        return None


def check_c2pa_metadata(video_path):
    """C2PA 메타데이터 확인 (c2patool 필요)"""
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
            print("    c2patool 설치: https://github.com/contentauth/c2patool")
            return None
    except FileNotFoundError:
        print("[i] c2patool이 설치되어 있지 않습니다.")
        print("    설치: cargo install c2patool")
        print("    또는: https://github.com/contentauth/c2patool/releases")
        return None


def format_result(result, mode):
    """결과를 보기 좋게 출력"""
    print("\n" + "=" * 60)
    print("  추출된 프롬프트 결과")
    print("=" * 60)

    if mode == "vision":
        # JSON 파싱 시도
        try:
            # JSON 블록 추출
            json_match = re.search(r'\{[^{}]*"prompt_en"[^{}]*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                print(f"\n[영문 프롬프트]\n{data.get('prompt_en', 'N/A')}")
                print(f"\n[한국어 프롬프트]\n{data.get('prompt_ko', 'N/A')}")
                print(f"\n[스타일] {data.get('style', 'N/A')}")
                print(f"[카메라] {data.get('camera', 'N/A')}")
                print(f"[분위기] {data.get('mood', 'N/A')}")
            else:
                print(result)
        except (json.JSONDecodeError, AttributeError):
            print(result)

    elif mode == "scrape":
        print(f"\n[원본 프롬프트]\n{result}")

    elif mode == "c2pa":
        print(f"\n[C2PA 메타데이터]\n{result}")

    print("\n" + "=" * 60)


def save_result(result, output_path):
    """결과를 파일로 저장"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"[+] 결과 저장됨: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Sora 2 영상 프롬프트 추출 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 로컬 영상 파일에서 프롬프트 역추출 (OpenAI API 필요)
  python video_prompt_extractor.py --video my_video.mp4

  # Sora 커뮤니티 URL에서 프롬프트 스크래핑
  python video_prompt_extractor.py --url https://sora.com/g/...

  # C2PA 메타데이터 확인
  python video_prompt_extractor.py --video my_video.mp4 --c2pa

  # 모든 방법 시도 + 결과 저장
  python video_prompt_extractor.py --video my_video.mp4 --all --output result.txt

  # 프레임 수 지정 (더 정확한 분석)
  python video_prompt_extractor.py --video my_video.mp4 --frames 8
        """
    )

    parser.add_argument("--video", "-v", help="분석할 영상 파일 경로")
    parser.add_argument("--url", "-u", help="Sora 커뮤니티 영상 URL")
    parser.add_argument("--frames", "-f", type=int, default=4, help="추출할 프레임 수 (기본: 4)")
    parser.add_argument("--api-key", "-k", help="OpenAI API 키 (또는 OPENAI_API_KEY 환경변수)")
    parser.add_argument("--c2pa", action="store_true", help="C2PA 메타데이터만 확인")
    parser.add_argument("--all", "-a", action="store_true", help="모든 분석 방법 사용")
    parser.add_argument("--output", "-o", help="결과를 저장할 파일 경로")

    args = parser.parse_args()

    if not args.video and not args.url:
        parser.print_help()
        print("\n[!] --video 또는 --url 옵션을 지정해주세요.")
        sys.exit(1)

    results = []

    # 1. Sora 커뮤니티 URL 스크래핑
    if args.url:
        result = scrape_sora_community(args.url)
        if result:
            format_result(result, "scrape")
            results.append(f"[Scrape Result]\n{result}")

    # 2. 로컬 영상 파일 분석
    if args.video:
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
            if not check_dependencies():
                sys.exit(1)

            print(f"[*] 영상에서 프레임 추출 중 ({args.frames}개)...")
            frames = extract_frames(str(video_path), args.frames)

            if not frames:
                print("[!] 프레임 추출에 실패했습니다.")
                sys.exit(1)

            print(f"[+] {len(frames)}개 프레임 추출 완료")

            vision_result = analyze_with_vision_api(frames, args.api_key)
            if vision_result:
                format_result(vision_result, "vision")
                results.append(f"[Vision Analysis]\n{vision_result}")

            # 임시 프레임 파일 정리
            for frame in frames:
                try:
                    os.remove(frame)
                except OSError:
                    pass

    # 결과 저장
    if args.output and results:
        combined = "\n\n" + "=" * 60 + "\n\n"
        save_result(combined.join(results), args.output)

    if not results:
        print("\n[!] 프롬프트를 추출하지 못했습니다.")
        sys.exit(1)

    print("\n[완료] 프롬프트 추출이 완료되었습니다!")


if __name__ == "__main__":
    main()
