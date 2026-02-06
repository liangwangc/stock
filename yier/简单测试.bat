@echo off
chcp 65001 >nul
title 单词库导入测试

cd /d "%~dp0"

echo ========================================
echo 单词库导入测试
echo ========================================
echo.

REM 检查XAMPP
if exist "C:\xampp\php\php.exe" (
    echo [OK] 找到 XAMPP PHP: C:\xampp\php\php.exe
    echo.
    echo 正在运行测试...
    echo.
    C:\xampp\php\php.exe test_import.php
    goto :end
)

if exist "C:\xampp64\php\php.exe" (
    echo [OK] 找到 XAMPP64 PHP: C:\xampp64\php\php.exe
    echo.
    echo 正在运行测试...
    echo.
    C:\xampp64\php\php.exe test_import.php
    goto :end
)

REM 检查WAMP
if exist "C:\wamp64\bin\php" (
    echo [OK] 找到 WAMP，正在查找PHP版本...
    for /d %%d in ("C:\wamp64\bin\php\php*") do (
        if exist "%%d\php.exe" (
            echo [OK] 使用: %%d\php.exe
            echo.
            echo 正在运行测试...
            echo.
            "%%d\php.exe" test_import.php
            goto :end
        )
    )
)

REM 检查其他位置
if exist "C:\php\php.exe" (
    echo [OK] 找到 PHP: C:\php\php.exe
    echo.
    echo 正在运行测试...
    echo.
    C:\php\php.exe test_import.php
    goto :end
)

if exist "D:\xampp\php\php.exe" (
    echo [OK] 找到 XAMPP PHP: D:\xampp\php\php.exe
    echo.
    echo 正在运行测试...
    echo.
    D:\xampp\php\php.exe test_import.php
    goto :end
)

REM 检查系统PATH
where php >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] 找到 PHP（系统PATH中）
    echo.
    echo 正在运行测试...
    echo.
    php test_import.php
    goto :end
)

echo [X] 未找到 PHP
echo.
echo 请检查以下位置：
echo   - C:\xampp\php\php.exe
echo   - C:\xampp64\php\php.exe
echo   - C:\wamp64\bin\php\php*\php.exe
echo   - C:\php\php.exe
echo.
echo 如果PHP在其他位置，请手动运行：
echo   [PHP路径] test_import.php
echo.

:end
echo.
echo ========================================
pause
