@echo off
chcp 65001 >nul
title Rewind · 回溯 (port 8000)
cd /d %~dp0backend
echo [Rewind] 正在启动后端 http://127.0.0.1:8000 ...
.venv\Scripts\python.exe -m uvicorn main:app --port 8000
echo.
echo [Rewind] 服务已停止。窗口可直接关闭。
pause
