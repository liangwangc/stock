@echo off
chcp 65001 >nul
echo ========================================
echo 新闻系统定时任务调度器
echo ========================================
echo.

cd /d "%~dp0"

echo 正在启动调度器...
py scheduler.py

pause
