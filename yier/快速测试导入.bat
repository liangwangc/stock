@echo off
chcp 65001 >nul
title 快速测试导入

cd /d "%~dp0"

set PHP_FOUND=0
set PHP_PATH=

REM 检查系统PATH
where php >nul 2>&1
if %errorlevel% == 0 (
    set PHP_PATH=php
    set PHP_FOUND=1
    goto :found
)

REM 检查XAMPP
if exist "C:\xampp\php\php.exe" (
    set PHP_PATH=C:\xampp\php\php.exe
    set PHP_FOUND=1
    goto :found
)

if exist "C:\xampp64\php\php.exe" (
    set PHP_PATH=C:\xampp64\php\php.exe
    set PHP_FOUND=1
    goto :found
)

REM 检查WAMP
if exist "C:\wamp64\bin\php" (
    for /d %%d in ("C:\wamp64\bin\php\php*") do (
        if exist "%%d\php.exe" (
            set PHP_PATH=%%d\php.exe
            set PHP_FOUND=1
            goto :found
        )
    )
)

if exist "C:\php\php.exe" (
    set PHP_PATH=C:\php\php.exe
    set PHP_FOUND=1
    goto :found
)

if exist "D:\xampp\php\php.exe" (
    set PHP_PATH=D:\xampp\php\php.exe
    set PHP_FOUND=1
    goto :found
)

echo 未找到 PHP，请先安装 PHP
pause
exit /b 1

:found
echo 找到 PHP: %PHP_PATH%
echo.
echo 正在测试导入（只导入一年级前5个单词）...
echo.
"%PHP_PATH%" test_import.php
echo.
pause
