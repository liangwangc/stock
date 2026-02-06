@echo off
chcp 65001 >nul
echo ========================================
echo 翻译API测试工具
echo ========================================
echo.

REM 尝试查找PHP路径
set PHP_PATH=

REM 检查常见PHP安装路径
if exist "D:\xampp\php\php.exe" (
    set PHP_PATH=D:\xampp\php\php.exe
) else if exist "C:\xampp\php\php.exe" (
    set PHP_PATH=C:\xampp\php\php.exe
) else if exist "D:\php\php.exe" (
    set PHP_PATH=D:\php\php.exe
) else if exist "C:\php\php.exe" (
    set PHP_PATH=C:\php\php.exe
) else (
    REM 尝试使用系统PATH中的php
    where php >nul 2>&1
    if %errorlevel% == 0 (
        set PHP_PATH=php
    )
)

if "%PHP_PATH%"=="" (
    echo 错误：未找到PHP！
    echo.
    echo 请确保：
    echo 1. 已安装PHP
    echo 2. PHP在系统PATH中，或者
    echo 3. 修改此批处理文件，设置PHP路径
    echo.
    echo 常见PHP安装路径：
    echo   D:\xampp\php\php.exe
    echo   C:\xampp\php\php.exe
    echo   D:\php\php.exe
    echo   C:\php\php.exe
    echo.
    pause
    exit /b 1
)

echo 使用PHP: %PHP_PATH%
echo.
echo 开始测试...
echo.

cd /d "%~dp0"
"%PHP_PATH%" test_translation_apis.php

echo.
pause
