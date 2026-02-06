@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo 使用 XAMPP 启动项目
echo ========================================
echo.

if exist "C:\xampp\php\php.exe" (
    set PHP_PATH=C:\xampp\php\php.exe
    goto :start
)

if exist "C:\xampp64\php\php.exe" (
    set PHP_PATH=C:\xampp64\php\php.exe
    goto :start
)

echo 错误: 未找到 XAMPP！
echo.
echo 请先安装 XAMPP:
echo   下载地址: https://www.apachefriends.org/
echo   安装路径: C:\xampp\ 或 C:\xampp64\
echo.
pause
exit /b 1

:start
echo 找到 PHP: %PHP_PATH%
echo.
echo 正在启动服务器...
echo.
echo ========================================
echo 访问地址: http://localhost:8000
echo ========================================
echo.
echo 提示:
echo   1. 确保 MySQL 服务已启动（在 XAMPP Control Panel）
echo   2. 确保数据库已导入
echo   3. 按 Ctrl+C 停止服务器
echo.
echo ========================================
echo.

"%PHP_PATH%" -S localhost:8000

echo.
echo 服务器已停止。
pause
