# Sora 2 Video Prompt Extractor

Sora 2로 생성된 영상에서 프롬프트를 역추출하는 도구입니다.

## 기능

| 모드 | 설명 | 필요 도구 |
|------|------|-----------|
| Vision 분석 | 영상 프레임을 AI로 분석하여 프롬프트 역추출 | OpenAI API + ffmpeg |
| URL 스크래핑 | Sora 커뮤니티 공개 영상에서 원본 프롬프트 추출 | - |
| C2PA 확인 | AI 생성 메타데이터 확인 | c2patool |

## 설치

```bash
pip install -r requirements.txt
```

ffmpeg도 필요합니다 (영상 프레임 추출용):
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## 사용법

### 1. 로컬 영상 파일에서 프롬프트 역추출

```bash
export OPENAI_API_KEY='your-key-here'
python video_prompt_extractor.py --video 귀멸의칼날.mp4
```

### 2. Sora 커뮤니티 URL에서 프롬프트 가져오기

```bash
python video_prompt_extractor.py --url https://sora.com/g/gen_xxxxx
```

### 3. C2PA 메타데이터 확인

```bash
python video_prompt_extractor.py --video my_video.mp4 --c2pa
```

### 4. 모든 방법 + 결과 저장

```bash
python video_prompt_extractor.py --video my_video.mp4 --all --output result.txt
```

### 옵션

```
--video, -v    분석할 영상 파일 경로
--url, -u      Sora 커뮤니티 영상 URL
--frames, -f   추출할 프레임 수 (기본: 4, 많을수록 정확)
--api-key, -k  OpenAI API 키
--c2pa         C2PA 메타데이터만 확인
--all, -a      모든 분석 방법 사용
--output, -o   결과를 저장할 파일 경로
```

## 참고

- Vision 분석은 **원본 프롬프트를 그대로 추출하는 것이 아니라** AI가 영상을 보고 역추론하는 방식입니다
- Sora 커뮤니티에 공개된 영상은 원본 프롬프트를 가져올 수 있습니다
- 프레임 수를 늘리면 (--frames 8) 더 정확한 분석이 가능합니다
