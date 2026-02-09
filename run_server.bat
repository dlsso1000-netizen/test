@echo off
chcp 65001 >nul
title Gemini Translator Server
echo 번역 서버를 시작합니다...
echo 게임 플레이 중 이 창을 닫지 마세요!
echo.
python gemini_trans.py
pause
