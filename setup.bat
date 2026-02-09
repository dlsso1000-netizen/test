@echo off
chcp 65001 >nul
echo ================================================
echo   Gemini Unity Game Translator - 설치 스크립트
echo ================================================
echo.

:: Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo   https://www.python.org/downloads/ 에서 다운로드하세요.
    echo   설치 시 "Add Python to PATH" 를 반드시 체크하세요!
    pause
    exit /b 1
)

echo [1/3] Python 확인 완료
python --version

:: pip 패키지 설치
echo.
echo [2/3] 필요한 패키지 설치 중...
pip install flask requests
if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [3/3] 설치 완료!
echo.
echo ================================================
echo   다음 단계:
echo   1. config.json 을 열어 api_key 를 입력하세요.
echo      (Google AI Studio에서 발급: https://aistudio.google.com/apikey)
echo   2. gemini_trans.py 를 실행하세요.
echo   3. 게임 폴더에 BepInEx + XUnity.AutoTranslator 를 설치하세요.
echo   4. bepinex_config/AutoTranslatorConfig.ini 를
echo      게임폴더/BepInEx/config/ 에 복사하세요.
echo ================================================
echo.
pause
