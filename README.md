# Pro Roasting Logger

커피 로스팅 데이터를 실시간으로 기록하고 시각화하는 프로그램입니다.

## 기능

- 실시간 온도 모니터링 (BT/ET)
- RoR(Rate of Rise) 자동 계산
- 이벤트 마킹 (Turning Point, Yellowing, 1st Crack, 2nd Crack, Drop)
- 로스팅 커브 실시간 그래프
- CSV 데이터 저장

## 지원 장비

- Simulation (테스트용 가상 모드)
- Easyster (Modbus)
- Proaster (Modbus)
- Center 306 (USB)
- Probat (WebSocket)

## 개발 환경에서 실행

```bash
# 1. 가상환경 생성 (권장)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 실행
streamlit run roasting_log.py
```

## EXE 파일 빌드 (배포용)

### 방법 1: build.bat 사용 (Windows)

```bash
build.bat
```

### 방법 2: 수동 빌드

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. PyInstaller로 빌드
pyinstaller roasting_logger.spec --clean
```

빌드가 완료되면 `dist/RoastingLogger/` 폴더가 생성됩니다.

## 배포 방법

1. `dist/RoastingLogger/` 폴더 전체를 ZIP으로 압축
2. 압축 파일을 전달
3. 받는 사람은 압축을 풀고 `RoastingLogger.exe` 실행

## 문제 해결

### "실행이 안 돼요"

1. **폴더 전체를 복사했는지 확인**: `RoastingLogger.exe` 파일만 복사하면 안 됩니다. `dist/RoastingLogger/` 폴더 전체가 필요합니다.

2. **바이러스 백신 확인**: 일부 백신이 PyInstaller로 만든 exe를 차단할 수 있습니다. 예외 추가가 필요할 수 있습니다.

3. **콘솔 창 확인**: 프로그램 실행 시 검은 콘솔 창이 뜹니다. 에러 메시지가 있는지 확인하세요.

4. **브라우저 열기**: 프로그램이 실행되면 자동으로 브라우저가 열립니다. 열리지 않으면 수동으로 http://localhost:8501 접속하세요.

### "포트가 사용 중이에요"

다른 프로그램이 8501 포트를 사용 중일 수 있습니다. 기존 프로세스를 종료하거나 잠시 후 다시 시도하세요.

### 콘솔 창 숨기기 (배포 시)

`roasting_logger.spec` 파일에서 `console=True`를 `console=False`로 변경하고 다시 빌드하세요.

## 파일 구조

```
RoastingLogger/
├── roasting_log.py      # 메인 Streamlit 앱
├── drivers.py           # 장비 드라이버 모듈
├── launcher.py          # EXE 런처
├── roasting_logger.spec # PyInstaller 설정
├── build.bat            # Windows 빌드 스크립트
├── requirements.txt     # Python 의존성
└── README.md            # 이 파일
```

## 라이선스

MIT License
