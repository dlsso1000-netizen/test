# Gemini Unity Game Translator

Steam 게임(중국어/일본어/영어)을 Google Gemini AI로 한국어 번역하는 프로그램입니다.
BepInEx + XUnity.AutoTranslator와 연동하여 Unity 게임의 텍스트를 실시간으로 번역합니다.

## 작동 원리

```
게임 텍스트 → XUnity.AutoTranslator → 로컬 Flask 서버 → Gemini API → 한국어 번역
```

## 빠른 시작 (3단계)

### 1단계: 초기 설치
1. [Python](https://www.python.org/downloads/) 설치 (**"Add Python to PATH" 반드시 체크!**)
2. [Google AI Studio](https://aistudio.google.com/apikey) 에서 API 키 발급
3. `setup.bat` 더블클릭 (패키지 자동 설치)
4. `config.json`을 메모장으로 열어 `api_keys`에 API 키 입력

```json
{
  "api_keys": [
    "여기에_발급받은_API_키_붙여넣기"
  ]
}
```

### 2단계: 게임 패치
`패치하기.bat` 더블클릭 → 게임 경로 입력 → 자동 설치 완료

- BepInEx 자동 다운로드 & 설치
- XUnity.AutoTranslator 자동 설치
- 번역 설정 자동 적용
- 한글 폰트 설정 (선택)

### 3단계: 번역 시작
1. `번역시작.bat` 더블클릭 (번역 서버 실행)
2. 게임 실행
3. 자동으로 한국어 번역 적용!

**게임 플레이 중 번역 서버 창을 닫지 마세요!**

## 주요 기능

- **다중 API 키 로테이션**: 여러 키를 등록하여 Rate Limit 분산
- **번역 캐시**: 같은 텍스트 재번역 방지 (파일 저장)
- **대화 컨텍스트**: 이전 번역 기록을 참고하여 일관된 번역
- **Safety 설정**: 게임 콘텐츠 차단 방지 옵션
- **배치 번역**: 여러 텍스트 일괄 번역
- **자동 패치**: BepInEx + XUnity.AutoTranslator 원클릭 설치

## 파일 구조

```
GeminiTranslator/
├── gemini_trans.py     # 번역 서버 (핵심)
├── game_patcher.py     # 게임 자동 패치 도구
├── config.json         # 설정 파일 (API 키 등)
├── requirements.txt    # Python 의존성
│
├── setup.bat           # 초기 설치 (영문)
├── 패치하기.bat         # 게임 패치 실행
├── 번역시작.bat         # 번역 서버 실행
├── run_server.bat      # 번역 서버 실행 (영문)
│
├── setup.sh            # Linux/Mac 설치
├── fonts/              # 한글 폰트 (.ttf 파일)
└── bepinex_config/     # BepInEx 설정 템플릿
    ├── AutoTranslatorConfig.ini
    └── xunity_endpoint.json
```

## 설정 옵션 (config.json)

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `api_keys` | `[]` | Google Gemini API 키 배열 (여러 개 가능) |
| `model` | `gemini-2.0-flash` | 사용할 Gemini 모델 |
| `source_lang` | `zh` | 원본 언어 (zh/ja/en) |
| `target_lang` | `ko` | 번역 대상 언어 |
| `port` | `5000` | 번역 서버 포트 |
| `context_turns` | `2` | 번역 컨텍스트로 사용할 이전 턴 수 |
| `safety_off` | `true` | Safety 필터 해제 여부 |
| `temperature` | `0.4` | 번역 창의성 (낮을수록 일관적) |
| `max_output_tokens` | `1024` | 최대 출력 토큰 |
| `cache_file` | `translation_cache.json` | 캐시 파일 경로 |
| `max_retries` | `3` | API 실패 시 재시도 횟수 |
| `max_consecutive_key_failures` | `3` | 키 로테이션 전 허용 연속 실패 수 |

## 수동 패치 방법

자동 패치가 안 되는 경우:

### 게임 타입 확인

| 구분 | 확인 방법 | BepInEx 버전 |
|------|-----------|-------------|
| IL2CPP 64bit | `GameAssembly.dll` + `UnityCrashHandler64.exe` | BepInEx IL2CPP x64 |
| IL2CPP 32bit | `GameAssembly.dll` + `UnityCrashHandler32.exe` | BepInEx IL2CPP x86 |
| Mono 64bit | `MonoBleedingEdge` 폴더 + `UnityCrashHandler64.exe` | BepInEx Mono x64 |
| Mono 32bit | `MonoBleedingEdge` 폴더 + `UnityCrashHandler32.exe` | BepInEx Mono x86 |

### 수동 설치 순서
1. [BepInEx](https://github.com/BepInEx/BepInEx/releases) 다운로드 → 게임 폴더에 압축 해제
2. 게임 한 번 실행 후 종료 (BepInEx 초기화)
3. [XUnity.AutoTranslator](https://github.com/bbepis/XUnity.AutoTranslator/releases) 다운로드 → 게임 폴더에 압축 해제
4. `bepinex_config/AutoTranslatorConfig.ini`를 `게임폴더/BepInEx/config/`에 복사

## 번역 수정

어색한 번역 수정 방법:
1. `translation_cache.json` 파일에서 해당 번역 찾아 수정
2. 또는 `BepInEx/Translation/ko/Text/` 폴더 내 파일 수정
3. 게임 재시작하면 수정된 번역 적용

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/` | GET | 서버 상태 확인 |
| `/translate` | GET/POST | 단일 텍스트 번역 |
| `/batch` | POST | 여러 텍스트 일괄 번역 |
| `/cache/stats` | GET | 캐시 통계 |
| `/cache/clear` | POST | 캐시 초기화 |
| `/cache/save` | POST | 캐시 즉시 저장 |
| `/history/clear` | POST | 대화 컨텍스트 초기화 |

## 문제 해결

| 증상 | 해결 방법 |
|------|-----------|
| API 키 오류 | config.json의 api_keys 확인. [Google AI Studio](https://aistudio.google.com/apikey)에서 재발급 |
| 한글 깨짐 | fonts/ 폴더에 .ttf 넣고 다시 패치. 또는 AutoTranslatorConfig.ini에서 OverrideFont 설정 |
| 번역 안 됨 | 번역 서버 실행 확인. 브라우저에서 `http://127.0.0.1:5000` 접속 확인 |
| 콘텐츠 차단 | config.json에서 `"safety_off": true` 확인 |
| 번역 느림 | 캐시가 쌓이면 점점 빨라짐. `gemini-2.0-flash` 모델 권장 |

## 지원 언어

| 코드 | 언어 |
|------|------|
| `zh` | 중국어 (간체) |
| `ko` | 한국어 |
| `ja` | 일본어 |
| `en` | 영어 |
