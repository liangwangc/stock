@echo off
chcp 65001 >nul
title 备用启动 - 仅查看页面（PHP功能不可用）
color 0E

echo.
echo ========================================
echo 备用启动 - 仅查看页面
echo ========================================
echo.
echo 注意: 此方式只能查看页面，PHP功能不可用！
echo 如果需要完整功能，请安装 XAMPP 后使用"一键启动.bat"
echo.
echo ========================================
echo.

cd /d "%~dp0"

REM 检查Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] 未找到 Python
    echo.
    echo 此备用方案需要 Python
    echo 请安装 Python 或使用"一键启动.bat"（需要XAMPP）
    pause
    exit /b 1
)

echo [OK] 找到 Python
echo.
echo 正在启动简单HTTP服务器...
echo.
echo 访问地址: http://localhost:8000
echo.
echo 警告: 
echo   - 只能查看页面外观
echo   - PHP功能（登录、添加单词等）不可用
echo   - 需要完整功能请安装 XAMPP
echo.
echo 按 Ctrl+C 停止服务器
echo.
echo ========================================
echo.

python -m http.server 8000

pause
