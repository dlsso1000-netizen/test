@echo off
chcp 65001 >nul
title Gemini Translator - 초기 설치
echo ================================================
echo   Gemini Unity Game Translator - 초기 설치
echo ================================================
echo.

:: Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo   https://www.python.org/downloads/ 에서 다운로드하세요.
    echo   설치 시 "Add Python to PATH" 반드시 체크!
    echo.
    pause
    exit /b 1
)

echo [1/2] Python 확인 완료:
python --version
echo.

:: 패키지 설치
echo [2/2] 필요한 패키지 설치 중...
pip install flask requests
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause
    exit /b 1
)

echo.
echo ================================================
echo   설치 완료!
echo ================================================
echo.
echo   다음 단계:
echo   1. config.json 을 메모장으로 열어 api_keys 에 API 키 입력
echo   2. [패치하기.bat] 실행하여 게임 패치
echo   3. [번역시작.bat] 실행하여 번역 서버 시작
echo   4. 게임 실행!
echo.
pause
