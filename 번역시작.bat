@echo off
chcp 65001 >nul
title Gemini 번역 서버
echo ================================================
echo   Gemini 번역 서버
echo   게임 플레이 중 이 창을 닫지 마세요!
echo ================================================
echo.
python "%~dp0gemini_trans.py"
echo.
echo 서버가 종료되었습니다.
pause
