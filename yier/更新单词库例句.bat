@echo off
chcp 65001 >nul
echo ========================================
echo 单词库例句更新工具
echo ========================================
echo.

REM 检查PHP路径
set PHP_PATH=D:\xampp\php\php.exe

if not exist "%PHP_PATH%" (
    echo 错误：找不到PHP，请修改脚本中的PHP_PATH变量
    pause
    exit /b 1
)

echo 正在运行更新脚本...
echo.

"%PHP_PATH%" update_word_bank_examples.php

echo.
pause
