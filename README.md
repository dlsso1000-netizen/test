# Video Prompt Extractor

YouTube, TikTok, Instagram, Sora 등 다양한 플랫폼의 영상에서 AI 생성 프롬프트를 역추출하는 도구입니다.

## 지원 플랫폼

| 플랫폼 | URL 예시 | 지원 기능 |
|--------|----------|-----------|
| YouTube | `youtube.com/watch?v=...` | 다운로드 + 분석 + 메타데이터 |
| TikTok | `tiktok.com/@user/video/...` | 다운로드 + 분석 + 메타데이터 |
| Instagram | `instagram.com/reel/...` | 다운로드 + 분석 + 메타데이터 |
| Sora | `sora.com/g/...` | 원본 프롬프트 스크래핑 + 분석 |
| 로컬 파일 | `my_video.mp4` | 분석 |

## 설치

### 1단계: Python 패키지 설치
```bash
pip install -r requirements.txt
```

### 2단계: ffmpeg 설치 (영상 프레임 추출용)
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# https://ffmpeg.org/download.html 에서 다운로드
```

### 3단계: OpenAI API 키 설정 (Vision 분석용)
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## 사용법

### YouTube 영상
```bash
python video_prompt_extractor.py --url "https://youtube.com/watch?v=xxxxx"
```

### TikTok 영상
```bash
python video_prompt_extractor.py --url "https://tiktok.com/@user/video/xxxxx"
```

### Instagram Reel
```bash
python video_prompt_extractor.py --url "https://instagram.com/reel/xxxxx"
```

### Sora 커뮤니티 영상
```bash
python video_prompt_extractor.py --url "https://sora.com/g/gen_xxxxx"
```

### 로컬 파일
```bash
python video_prompt_extractor.py --video my_video.mp4
```

### 메타데이터만 빠르게 확인 (다운로드 없이)
```bash
python video_prompt_extractor.py --url "https://youtube.com/watch?v=xxx" --meta-only
```

### 모든 분석 + 결과 파일로 저장
```bash
python video_prompt_extractor.py --url "https://tiktok.com/..." --all -o result.txt
```

### 다운로드한 영상 보관
```bash
python video_prompt_extractor.py --url "https://youtube.com/..." --keep-video
```

## 전체 옵션

```
--url, -u        영상 URL (YouTube, TikTok, Instagram, Sora 등)
--video, -v      로컬 영상 파일 경로
--frames, -f     추출할 프레임 수 (기본: 4, 많을수록 정확)
--api-key, -k    OpenAI API 키
--meta-only, -m  메타데이터만 확인 (다운로드/분석 없이)
--c2pa           C2PA 메타데이터만 확인
--all, -a        모든 분석 방법 사용
--output, -o     결과를 저장할 파일 경로
--keep-video     다운로드한 영상 파일 삭제하지 않고 유지
```

## 작동 원리

1. **메타데이터 추출** - yt-dlp로 영상 제목, 설명, 태그 등을 가져옴
2. **영상 다운로드** - yt-dlp로 영상을 임시 다운로드
3. **프레임 추출** - ffmpeg로 영상에서 균등 간격으로 프레임 캡처
4. **AI 분석** - OpenAI GPT-4o Vision API로 프레임을 분석하여 프롬프트 역추출
5. **프롬프트 생성** - 영문/한국어 프롬프트 + 스타일/카메라/분위기 정보 제공

## 참고

- Vision 분석은 원본 프롬프트를 그대로 추출하는 것이 아니라 AI가 역추론하는 방식입니다
- 영상 설명에 프롬프트가 포함된 경우 자동으로 감지합니다
- 프레임 수를 늘리면 (`--frames 8`) 더 정확한 분석이 가능합니다
- yt-dlp는 1500개 이상의 사이트를 지원하므로 위 플랫폼 외에도 사용 가능합니다
