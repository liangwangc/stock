@echo off
chcp 65001 >nul
title 查找PHP并启动项目
color 0C

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║         自动查找 PHP 并启动项目                          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

set PHP_FOUND=0
set PHP_PATH=

echo [搜索1] 检查系统PATH中的PHP...
where php >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ 找到 PHP（在系统PATH中）
    set PHP_PATH=php
    set PHP_FOUND=1
    php --version | findstr "PHP"
    goto :start
)

echo [搜索2] 检查常见安装位置...
echo ──────────────────────────────────────────────────────────

REM XAMPP 32位
if exist "C:\xampp\php\php.exe" (
    echo ✅ 找到 XAMPP PHP (32位)
    set PHP_PATH=C:\xampp\php\php.exe
    set PHP_FOUND=1
    goto :start
)

REM XAMPP 64位
if exist "C:\xampp64\php\php.exe" (
    echo ✅ 找到 XAMPP PHP (64位)
    set PHP_PATH=C:\xampp64\php\php.exe
    set PHP_FOUND=1
    goto :start
)

REM WAMP
if exist "C:\wamp64\bin\php\php7.4.33\php.exe" (
    echo ✅ 找到 WAMP PHP
    set PHP_PATH=C:\wamp64\bin\php\php7.4.33\php.exe
    set PHP_FOUND=1
    goto :start
)

REM 检查 WAMP 的其他 PHP 版本
for /d %%d in ("C:\wamp64\bin\php\php*") do (
    if exist "%%d\php.exe" (
        echo ✅ 找到 WAMP PHP: %%d
        set PHP_PATH=%%d\php.exe
        set PHP_FOUND=1
        goto :start
    )
)

REM 检查其他常见位置
if exist "C:\php\php.exe" (
    echo ✅ 找到 PHP: C:\php\php.exe
    set PHP_PATH=C:\php\php.exe
    set PHP_FOUND=1
    goto :start
)

if exist "D:\xampp\php\php.exe" (
    echo ✅ 找到 XAMPP PHP: D:\xampp\php\php.exe
    set PHP_PATH=D:\xampp\php\php.exe
    set PHP_FOUND=1
    goto :start
)

if exist "D:\wamp64\bin\php" (
    for /d %%d in ("D:\wamp64\bin\php\php*") do (
        if exist "%%d\php.exe" (
            echo ✅ 找到 WAMP PHP: %%d
            set PHP_PATH=%%d\php.exe
            set PHP_FOUND=1
            goto :start
        )
    )
)

REM 未找到
echo ❌ 未找到 PHP！
echo.
goto :notfound

:start
echo.
echo ═══════════════════════════════════════════════════════════
echo   找到 PHP，准备启动服务器
echo ═══════════════════════════════════════════════════════════
echo.
echo   PHP路径: %PHP_PATH%
echo   项目目录: %CD%
echo   访问地址: http://localhost:8000
echo.
echo   ⚠️  重要提示：
echo     1. 确保 MySQL 服务已启动
echo     2. 确保数据库已导入
echo     3. 确保 api.php 中的密码正确
echo.
echo   🛑 按 Ctrl+C 停止服务器
echo.
echo ═══════════════════════════════════════════════════════════
echo.

%PHP_PATH% -S localhost:8000

echo.
echo 服务器已停止。
pause
exit /b 0

:notfound
echo ═══════════════════════════════════════════════════════════
echo   PHP 未安装！
echo ═══════════════════════════════════════════════════════════
echo.
echo 解决方案（选择其一）：
echo.
echo 【方案1】安装 XAMPP（推荐，最简单）
echo ──────────────────────────────────────────────────────────
echo   1. 下载 XAMPP: https://www.apachefriends.org/
echo   2. 安装到默认位置: C:\xampp\
echo   3. 重新运行此脚本
echo.
echo 【方案2】安装 WAMP
echo ──────────────────────────────────────────────────────────
echo   1. 下载 WAMP: https://www.wampserver.com/
echo   2. 安装到默认位置: C:\wamp64\
echo   3. 重新运行此脚本
echo.
echo 【方案3】单独安装 PHP
echo ──────────────────────────────────────────────────────────
echo   1. 下载 PHP: https://windows.php.net/download/
echo   2. 选择 Thread Safe 版本，ZIP 格式
echo   3. 解压到 C:\php\
echo   4. 添加到系统 PATH 环境变量
echo   5. 重新运行此脚本
echo.
echo ═══════════════════════════════════════════════════════════
echo.
echo 💡 推荐使用 XAMPP，因为它包含：
echo   - PHP（运行项目）
echo   - MySQL（数据库）
echo   - Apache（Web服务器）
echo   - phpMyAdmin（数据库管理）
echo.
pause
exit /b 1
