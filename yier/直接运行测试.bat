@echo off
chcp 65001 >nul
title 单词库导入测试

cd /d "%~dp0"

echo ========================================
echo 单词库导入测试
echo ========================================
echo.

set PHP_PATH=D:\xampp\php\php.exe

if exist "%PHP_PATH%" (
    echo [OK] 找到 PHP: %PHP_PATH%
    echo.
    echo 正在运行测试...
    echo.
    "%PHP_PATH%" test_import.php
) else (
    echo [X] 未找到 PHP: %PHP_PATH%
    echo.
    echo 请检查路径是否正确
)

echo.
echo ========================================
pause
