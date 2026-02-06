@echo off
chcp 65001 >nul
echo ========================================
echo 单词库批量导入工具
echo ========================================
echo.

REM 检查PHP是否可用
where php >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到PHP，请先安装PHP或配置PATH
    echo.
    echo 如果已安装XAMPP，请使用：
    echo C:\xampp\php\php.exe import_word_bank.php
    pause
    exit /b
)

echo 正在启动导入工具...
echo.
echo 提示：可以输入 all 导入所有年级，或输入数字（如 1,2,3）导入指定年级
echo.

php import_word_bank.php

pause
