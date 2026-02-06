@echo off
chcp 65001 >nul
title 导入扩展单词库（每个年级100+单词）

cd /d "%~dp0"

echo ========================================
echo 导入扩展单词库
echo ========================================
echo.
echo 每个年级包含100多个单词，包含例句
echo 预计总单词数：1200多个
echo 预计耗时：40多分钟
echo.
echo 按任意键开始导入，或按Ctrl+C取消...
pause >nul

D:\xampp\php\php.exe import_all_grades.php

echo.
pause
