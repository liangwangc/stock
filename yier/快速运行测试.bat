@echo off
chcp 65001 >nul
title 快速运行测试

cd /d "%~dp0"

echo ========================================
echo 单词库导入测试
echo ========================================
echo.

REM 尝试使用PowerShell运行
powershell.exe -ExecutionPolicy Bypass -File "运行测试.ps1"

if %errorlevel% neq 0 (
    echo.
    echo PowerShell脚本运行失败，尝试查找PHP...
    echo.
    
    REM 检查常见位置
    if exist "C:\xampp\php\php.exe" (
        echo 找到 XAMPP PHP
        C:\xampp\php\php.exe test_import.php
        goto :end
    )
    
    if exist "C:\xampp64\php\php.exe" (
        echo 找到 XAMPP64 PHP
        C:\xampp64\php\php.exe test_import.php
        goto :end
    )
    
    if exist "C:\wamp64\bin\php" (
        echo 找到 WAMP，正在查找PHP版本...
        for /d %%d in ("C:\wamp64\bin\php\php*") do (
            if exist "%%d\php.exe" (
                echo 使用: %%d\php.exe
                "%%d\php.exe" test_import.php
                goto :end
            )
        )
    )
    
    echo.
    echo 未找到PHP！
    echo 请先安装XAMPP: https://www.apachefriends.org/
    echo 或运行: powershell -File 查找PHP路径.ps1
)

:end
pause
