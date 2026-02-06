@echo off
chcp 65001 >nul
echo ========================================
echo 单词库错误检查工具
echo ========================================
echo.

REM 尝试查找PHP路径
set PHP_PATH=

if exist "D:\xampp\php\php.exe" (
    set PHP_PATH=D:\xampp\php\php.exe
) else if exist "C:\xampp\php\php.exe" (
    set PHP_PATH=C:\xampp\php\php.exe
) else if exist "D:\php\php.exe" (
    set PHP_PATH=D:\php\php.exe
) else if exist "C:\php\php.exe" (
    set PHP_PATH=C:\php\php.exe
) else (
    where php >nul 2>&1
    if %errorlevel% == 0 (
        set PHP_PATH=php
    )
)

if "%PHP_PATH%"=="" (
    echo 错误：未找到PHP！
    echo.
    echo 请确保已安装PHP
    echo.
    pause
    exit /b 1
)

echo 使用PHP: %PHP_PATH%
echo.
echo 开始检查...
echo.

cd /d "%~dp0"
"%PHP_PATH%" check_word_bank_errors.php

echo.
pause
