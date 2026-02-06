@echo off
chcp 65001 >nul
title 付一二项目 - 一键启动
color 0B

echo.
echo ========================================
echo 付一二项目 - 一键启动
echo ========================================
echo.

cd /d "%~dp0"

set PHP_FOUND=0
set PHP_PATH=

echo [1/3] 正在查找 PHP...
echo ----------------------------------------

REM 检查系统PATH
where php >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] 找到 PHP（系统PATH中）
    set PHP_PATH=php
    set PHP_FOUND=1
    goto :found
)

REM 检查XAMPP
if exist "C:\xampp\php\php.exe" (
    echo [OK] 找到 XAMPP PHP
    set PHP_PATH=C:\xampp\php\php.exe
    set PHP_FOUND=1
    goto :found
)

if exist "C:\xampp64\php\php.exe" (
    echo [OK] 找到 XAMPP64 PHP
    set PHP_PATH=C:\xampp64\php\php.exe
    set PHP_FOUND=1
    goto :found
)

REM 检查WAMP
if exist "C:\wamp64\bin\php" (
    for /d %%d in ("C:\wamp64\bin\php\php*") do (
        if exist "%%d\php.exe" (
            echo [OK] 找到 WAMP PHP: %%d
            set PHP_PATH=%%d\php.exe
            set PHP_FOUND=1
            goto :found
        )
    )
)

REM 检查其他常见位置
if exist "C:\php\php.exe" (
    echo [OK] 找到 PHP: C:\php\php.exe
    set PHP_PATH=C:\php\php.exe
    set PHP_FOUND=1
    goto :found
)

if exist "D:\xampp\php\php.exe" (
    echo [OK] 找到 XAMPP PHP: D:\xampp\php\php.exe
    set PHP_PATH=D:\xampp\php\php.exe
    set PHP_FOUND=1
    goto :found
)

REM 未找到
echo [X] 未找到 PHP
echo.
goto :notfound

:found
echo.
echo [2/3] 检查端口...
echo ----------------------------------------
netstat -ano | findstr ":8000" >nul 2>&1
if %errorlevel% == 0 (
    echo [警告] 端口 8000 已被占用，尝试使用 8080...
    set PORT=8080
) else (
    echo [OK] 端口 8000 可用
    set PORT=8000
)

echo.
echo [3/3] 启动服务器...
echo ========================================
echo.
echo   PHP路径: %PHP_PATH%
echo   项目目录: %CD%
echo   访问地址: http://localhost:%PORT%
echo.
echo   提示:
echo   - 确保 MySQL 服务已启动（如果使用数据库）
echo   - 确保数据库已导入
echo   - 按 Ctrl+C 停止服务器
echo.
echo ========================================
echo.
echo 正在启动，请稍候...
echo.

"%PHP_PATH%" -S localhost:%PORT%

echo.
echo 服务器已停止。
pause
exit /b 0

:notfound
echo ========================================
echo 未找到 PHP 环境
echo ========================================
echo.
echo 您的系统未安装 PHP，无法运行此项目。
echo.
echo 解决方案（选择其一）:
echo.
echo [方案1] 安装 XAMPP（推荐）
echo   - 下载: https://www.apachefriends.org/
echo   - 安装后重新运行此脚本即可
echo.
echo [方案2] 安装 WAMP
echo   - 下载: https://www.wampserver.com/
echo   - 安装后重新运行此脚本即可
echo.
echo [方案3] 单独安装 PHP
echo   - 下载: https://windows.php.net/download/
echo   - 解压到 C:\php\
echo   - 添加到系统PATH环境变量
echo.
echo ========================================
echo.
echo 注意: 此项目需要 PHP 才能运行，因为:
echo   - api.php 是 PHP 代码文件
echo   - 需要 PHP 来解释执行代码
echo   - 需要 MySQL 数据库存储数据
echo.
echo 安装 XAMPP 后，重新运行此脚本即可自动启动！
echo.
pause
exit /b 1
