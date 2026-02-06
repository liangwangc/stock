@echo off
chcp 65001 >nul
title 一键导入所有年级单词

cd /d "%~dp0"

echo ========================================
echo 一键导入所有年级单词
echo ========================================
echo.

D:\xampp\php\php.exe import_all_grades.php

echo.
pause
