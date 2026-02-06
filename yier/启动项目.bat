@echo off
chcp 65001 >nul
title 付一二项目 - 启动服务器
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║         付一二（MemoCalendar）项目启动                  ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/4] 检查PHP环境...
echo ──────────────────────────────────────────────────────────
REM 先检查系统PATH
where php >nul 2>&1
if %errorlevel% == 0 goto :found

REM 检查XAMPP
if exist "C:\xampp\php\php.exe" (
    set PHP_PATH=C:\xampp\php\php.exe
    goto :found
)
if exist "C:\xampp64\php\php.exe" (
    set PHP_PATH=C:\xampp64\php\php.exe
    goto :found
)

REM 检查WAMP
if exist "C:\wamp64\bin\php" (
    for /d %%d in ("C:\wamp64\bin\php\php*") do (
        if exist "%%d\php.exe" (
            set PHP_PATH=%%d\php.exe
            goto :found
        )
    )
)

REM 未找到
echo ❌ PHP 未安装或未添加到PATH！
echo.
echo 解决方法：
echo   1. 安装 XAMPP: https://www.apachefriends.org/
echo   2. 安装 WAMP: https://www.wampserver.com/
echo   3. 或单独安装 PHP 并添加到系统PATH
echo.
echo 如果已安装XAMPP/WAMP，请运行: 查找PHP并启动.bat
echo   它会自动查找并启动
echo.
pause
exit /b 1

:found
if defined PHP_PATH (
    set "php=%PHP_PATH%"
) else (
    set "php=php"
)

echo ✅ PHP 已安装
php --version | findstr "PHP"
echo.

echo [2/4] 检查项目文件...
echo ──────────────────────────────────────────────────────────
if not exist "api.php" (
    echo ❌ api.php 不存在！
    pause
    exit /b 1
)
if not exist "index.html" (
    echo ❌ index.html 不存在！
    pause
    exit /b 1
)
echo ✅ 项目文件完整
echo.

echo [3/4] 检查端口占用...
echo ──────────────────────────────────────────────────────────
netstat -ano | findstr ":8000" >nul 2>&1
if %errorlevel% == 0 (
    echo ⚠️  端口 8000 已被占用
    echo    正在尝试使用端口 8080...
    set PORT=8080
) else (
    echo ✅ 端口 8000 可用
    set PORT=8000
)
echo.

echo [4/4] 启动Web服务器...
echo ──────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════
echo   服务器启动成功！
echo ═══════════════════════════════════════════════════════════
echo.
echo   📍 访问地址: http://localhost:%PORT%
echo   📁 项目目录: %CD%
echo.
echo   ⚠️  重要提示：
echo     1. 确保 MySQL 服务已启动
echo     2. 确保数据库 'word_app' 已创建
echo     3. 确保 api.php 中的密码配置正确
echo.
echo   💡 如果遇到数据库连接错误：
echo     1. 检查 MySQL 服务是否运行
echo     2. 编辑 api.php 修改数据库密码（第20行）
echo     3. 运行"测试数据库连接.bat"测试连接
echo.
echo   🛑 按 Ctrl+C 停止服务器
echo.
echo ═══════════════════════════════════════════════════════════
echo.

php -S localhost:%PORT%

echo.
echo 服务器已停止。
pause
