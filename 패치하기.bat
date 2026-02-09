@echo off
chcp 65001 >nul
title 게임 패치 도구
python "%~dp0game_patcher.py"
pause
