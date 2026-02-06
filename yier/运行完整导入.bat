@echo off
chcp 65001 >nul
title 单词库完整导入

cd /d "%~dp0"

echo ========================================
echo 单词库完整导入工具
echo ========================================
echo.

set PHP_PATH=D:\xampp\php\php.exe

if exist "%PHP_PATH%" (
    echo [OK] 找到 PHP: %PHP_PATH%
    echo.
    echo 提示：可以输入 all 导入所有年级，或输入数字（如 1,2,3）导入指定年级
    echo.
    "%PHP_PATH%" import_word_bank.php
) else (
    echo [X] 未找到 PHP: %PHP_PATH%
    echo.
    echo 请检查路径是否正确
)

echo.
echo ========================================
pause
