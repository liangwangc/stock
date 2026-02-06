@echo off
chcp 65001 >nul
title 单词库批量导入工具
color 0B

echo.
echo ========================================
echo 单词库批量导入工具
echo ========================================
echo.

cd /d "%~dp0"

set PHP_FOUND=0
set PHP_PATH=

echo [1/2] 正在查找 PHP...
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
echo [2/2] 启动导入工具...
echo ========================================
echo.
echo PHP路径: %PHP_PATH%
echo.
echo 提示：可以输入 all 导入所有年级，或输入数字（如 1,2,3）导入指定年级
echo.

"%PHP_PATH%" import_word_bank.php

echo.
echo ========================================
echo 导入完成！
echo ========================================
pause
exit /b 0

:notfound
echo ========================================
echo 未找到 PHP 环境
echo ========================================
echo.
echo 您的系统未安装 PHP，无法运行导入工具。
echo.
echo 解决方案:
echo   1. 安装 XAMPP: https://www.apachefriends.org/
echo   2. 或安装 WAMP: https://www.wampserver.com/
echo   3. 或单独安装 PHP: https://windows.php.net/download/
echo.
pause
exit /b 1
