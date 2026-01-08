@echo off
echo ========================================
echo Pro Roasting Logger - Build Script
echo ========================================
echo.

REM 기존 빌드 폴더 정리
echo [1/4] 기존 빌드 파일 정리 중...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM 가상환경 활성화 확인
echo [2/4] Python 환경 확인 중...
python --version
if errorlevel 1 (
    echo 오류: Python이 설치되어 있지 않습니다!
    pause
    exit /b 1
)

REM 의존성 설치
echo [3/4] 의존성 설치 중...
pip install -r requirements.txt
if errorlevel 1 (
    echo 오류: 의존성 설치 실패!
    pause
    exit /b 1
)

REM PyInstaller로 빌드
echo [4/4] EXE 빌드 중... (몇 분 소요됩니다)
pyinstaller roasting_logger.spec --clean
if errorlevel 1 (
    echo 오류: 빌드 실패!
    pause
    exit /b 1
)

echo.
echo ========================================
echo 빌드 완료!
echo 실행 파일 위치: dist\RoastingLogger\RoastingLogger.exe
echo ========================================
echo.
echo 배포하려면 dist\RoastingLogger 폴더 전체를 압축하세요.
pause
