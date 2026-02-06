@echo off
chcp 65001 >nul
echo ========================================
echo 启动 PHP 内置服务器
echo ========================================
echo.

echo 正在启动服务器...
echo 访问地址: http://localhost:8000
echo 按 Ctrl+C 停止服务器
echo.

cd /d "%~dp0"
php -S localhost:8000

pause
