@echo off
chcp 65001 >nul
echo ========================================
echo   股票预测系统 Web 应用启动脚本
echo ========================================
echo.
echo 正在启动Web服务器...
echo.

cd /d %~dp0
py web_app.py

pause
