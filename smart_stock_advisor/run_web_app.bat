@echo off
chcp 65001 >nul
echo ========================================
echo 启动 Web 应用
echo ========================================
cd /d %~dp0
python web_app.py
pause
