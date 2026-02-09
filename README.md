# Gemini Unity Game Translator

Steam 중국어 게임을 Google Gemini AI로 한국어 번역하는 프로그램입니다.
BepInEx + XUnity.AutoTranslator와 연동하여 Unity 게임의 텍스트를 실시간으로 번역합니다.

## 작동 원리

```
게임 텍스트 → XUnity.AutoTranslator → 로컬 Flask 서버 → Gemini API → 한국어 번역
```

1. BepInEx가 Unity 게임에 로드됨
2. XUnity.AutoTranslator가 게임 내 텍스트를 감지
3. CustomEndpoint를 통해 로컬 번역 서버(gemini_trans.py)에 요청
4. Gemini API로 중국어 → 한국어 번역 수행
5. 번역 결과를 캐시하여 같은 텍스트 재번역 방지

## 사전 준비물

### 1. Google Gemini API 키
- [Google AI Studio](https://aistudio.google.com/apikey) 에서 API 키 발급
- 신규 가입 시 무료 크레딧 제공

### 2. Python 3.10+
- [python.org](https://www.python.org/downloads/) 에서 다운로드
- **설치 시 "Add Python to PATH" 반드시 체크!**

### 3. BepInEx + XUnity.AutoTranslator
- [BepInEx](https://github.com/BepInEx/BepInEx/releases) - Unity 게임 모드 프레임워크
- [XUnity.AutoTranslator](https://github.com/bbepis/XUnity.AutoTranslator/releases) - 자동 번역 플러그인

## 설치 방법

### 1단계: 의존성 설치

**Windows:**
```
setup.bat 실행
```

또는 수동 설치:
```bash
pip install flask requests
```

### 2단계: API 키 설정

`config.json` 파일을 열어 `api_key`에 발급받은 키를 입력:

```json
{
  "api_key": "여기에_API_키_입력",
  "model": "gemini-2.0-flash",
  "source_lang": "zh",
  "target_lang": "ko"
}
```

### 3단계: 게임에 BepInEx 설치

게임 종류에 따라 다른 버전이 필요합니다:

| 구분 | 확인 방법 | BepInEx 버전 |
|------|-----------|-------------|
| **IL2CPP 64bit** | `GameAssembly.dll` 존재 + `UnityCrashHandler64.exe` | BepInEx IL2CPP x64 |
| **IL2CPP 32bit** | `GameAssembly.dll` 존재 + `UnityCrashHandler32.exe` | BepInEx IL2CPP x86 |
| **Mono 64bit** | `MonoBleedingEdge` 폴더 존재 + `UnityCrashHandler64.exe` | BepInEx Mono x64 |
| **Mono 32bit** | `MonoBleedingEdge` 폴더 존재 + `UnityCrashHandler32.exe` | BepInEx Mono x86 |

BepInEx 설치:
1. 게임 폴더에 BepInEx 압축 파일 해제
2. 게임을 한 번 실행하여 BepInEx 초기 폴더 생성
3. 게임 종료

### 4단계: XUnity.AutoTranslator 설치

1. XUnity.AutoTranslator 다운로드 (BepInEx용)
2. `BepInEx/plugins/` 폴더에 플러그인 파일 복사

### 5단계: 번역 설정 적용

`bepinex_config/AutoTranslatorConfig.ini` 를 게임폴더의 `BepInEx/config/` 에 복사합니다.

### 6단계: 한글 폰트 설정 (선택)

한글이 깨지는 경우:
1. 한글 폰트 파일(.ttf)을 게임 폴더에 복사
2. `AutoTranslatorConfig.ini`의 `[Font]` 섹션에서 `OverrideFont=폰트이름` 설정

추천 폰트: NanumGothic, 안성탕면체, 맑은고딕 등

## 사용 방법

### 1. 번역 서버 실행
```bash
# Windows
run_server.bat 더블클릭

# 또는 직접 실행
python gemini_trans.py
```

서버가 정상 시작되면:
```
==================================================
  Gemini Unity Game Translator
  모델: gemini-2.0-flash
  번역: zh → ko
==================================================
[OK] API 키가 정상적으로 확인되었습니다.
[서버 시작] http://127.0.0.1:5000
```

### 2. 게임 실행
- 번역 서버가 실행된 상태에서 게임을 시작하면 자동으로 번역이 적용됩니다.
- **게임 플레이 중 번역 서버 창을 닫지 마세요!**

### 3. 번역 확인
- 게임 내 중국어 텍스트가 한국어로 표시됩니다.
- 콘솔 창에서 번역 로그를 실시간으로 확인할 수 있습니다.

## 설정 옵션 (config.json)

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `api_key` | `""` | Google Gemini API 키 |
| `model` | `gemini-2.0-flash` | 사용할 Gemini 모델 |
| `source_lang` | `zh` | 원본 언어 (zh=중국어, ja=일본어, en=영어) |
| `target_lang` | `ko` | 번역 대상 언어 |
| `port` | `5000` | 번역 서버 포트 |
| `cache_file` | `translation_cache.json` | 번역 캐시 파일 |
| `max_retries` | `3` | API 호출 실패 시 재시도 횟수 |
| `batch_size` | `10` | 배치 번역 시 한 번에 처리할 텍스트 수 |
| `system_prompt` | (기본 프롬프트) | Gemini에게 전달할 번역 지시 프롬프트 |

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/` | GET | 서버 상태 확인 |
| `/translate` | GET/POST | 단일 텍스트 번역 |
| `/batch` | POST | 여러 텍스트 일괄 번역 |
| `/cache/stats` | GET | 캐시 통계 |
| `/cache/clear` | POST | 캐시 초기화 |
| `/cache/save` | POST | 캐시 즉시 저장 |

## 번역 수정

어색한 번역이 있다면:
1. `translation_cache.json` 파일을 텍스트 편집기로 열기
2. 해당 번역 찾아서 수정
3. 게임 재시작하면 수정된 번역이 적용됨

또는 XUnity.AutoTranslator의 번역 파일:
- `BepInEx/Translation/ko/Text/` 폴더 내 파일 수정

## 파일 구조

```
gemini-unity-translator/
├── gemini_trans.py              # 메인 번역 서버
├── config.json                  # 설정 파일 (API 키 등)
├── requirements.txt             # Python 의존성
├── setup.bat                    # Windows 설치 스크립트
├── setup.sh                     # Linux/Mac 설치 스크립트
├── run_server.bat               # Windows 서버 실행
├── translation_cache.json       # 번역 캐시 (자동 생성)
└── bepinex_config/
    ├── AutoTranslatorConfig.ini # XUnity.AutoTranslator 설정
    └── xunity_endpoint.json     # CustomEndpoint 설정
```

## 문제 해결

### API 키 오류
- config.json의 api_key 값 확인
- [Google AI Studio](https://aistudio.google.com/apikey)에서 키 재발급

### 한글 깨짐
- AutoTranslatorConfig.ini에서 OverrideFont 설정
- 한글 지원 폰트(.ttf) 파일을 게임 폴더에 복사

### 번역이 안 됨
- 번역 서버(gemini_trans.py)가 실행 중인지 확인
- 브라우저에서 `http://127.0.0.1:5000` 접속하여 서버 상태 확인
- AutoTranslatorConfig.ini의 Endpoint 설정이 CustomEndpoint인지 확인

### 번역 속도가 느림
- `gemini-2.0-flash` 모델은 빠르고 저렴한 옵션
- 캐시가 쌓이면 반복 텍스트는 즉시 반환됨

## 지원 언어

source_lang / target_lang 에 사용 가능한 언어 코드:

| 코드 | 언어 |
|------|------|
| `zh` | 중국어 |
| `ko` | 한국어 |
| `ja` | 일본어 |
| `en` | 영어 |
