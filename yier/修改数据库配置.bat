@echo off
chcp 65001 >nul
title 修改数据库配置
color 0B

echo.
echo ========================================
echo 修改数据库配置
echo ========================================
echo.

cd /d "%~dp0"

echo 当前配置:
echo ----------------------------------------
type api.php | findstr /C:"db_host" /C:"db_user" /C:"db_pass" /C:"db_name" | findstr /V "//"
echo.

echo ========================================
echo 请输入您的数据库信息
echo ========================================
echo.

set /p DB_HOST=数据库主机 (默认: localhost): 
set /p DB_USER=数据库用户名 (默认: root): 
set /p DB_PASS=数据库密码 (直接回车为空): 
set /p DB_NAME=数据库名称 (必填): 

if "%DB_HOST%"=="" set DB_HOST=localhost
if "%DB_USER%"=="" set DB_USER=root
if "%DB_NAME%"=="" (
    echo.
    echo [错误] 数据库名称不能为空！
    pause
    exit /b 1
)

echo.
echo ========================================
echo 确认配置信息
echo ========================================
echo   数据库主机: %DB_HOST%
echo   用户名: %DB_USER%
echo   密码: %DB_PASS%
echo   数据库名: %DB_NAME%
echo.
set /p CONFIRM=确认修改？(Y/N): 

if /i not "%CONFIRM%"=="Y" (
    echo 已取消
    pause
    exit /b 0
)

echo.
echo 正在修改配置...

REM 使用PowerShell修改文件
powershell -Command "$content = Get-Content api.php -Raw; $content = $content -replace '\\$db_host = ''[^'']*'';', '$db_host = ''%DB_HOST%'';'; $content = $content -replace '\\$db_user = ''[^'']*'';', '$db_user = ''%DB_USER%'';'; $content = $content -replace '\\$db_pass = ''[^'']*'';', '$db_pass = ''%DB_PASS%'';'; $content = $content -replace '\\$db_name = ''[^'']*'';', '$db_name = ''%DB_NAME%'';'; Set-Content api.php -Value $content -NoNewline"

if %errorlevel% == 0 (
    echo.
    echo [OK] 配置已成功修改！
    echo.
    echo 新配置:
    echo ----------------------------------------
    type api.php | findstr /C:"db_host" /C:"db_user" /C:"db_pass" /C:"db_name" | findstr /V "//"
    echo.
    echo ========================================
    echo 下一步
    echo ========================================
    echo.
    echo 1. 确保数据库 "%DB_NAME%" 已存在
    echo 2. 确保数据库中有必要的表结构
    echo 3. 如果没有表，请导入 SQL 文件:
    echo    - word_app_backup_20260129.sql (基础表)
    echo    - database_upgrade.sql (新功能)
    echo.
    echo 4. 测试连接: 运行"测试数据库连接.bat"
    echo.
) else (
    echo.
    echo [错误] 修改失败，请手动编辑 api.php 文件
    echo.
    echo 需要修改的位置（第18-21行）:
    echo   $db_host = '%DB_HOST%';
    echo   $db_user = '%DB_USER%';
    echo   $db_pass = '%DB_PASS%';
    echo   $db_name = '%DB_NAME%';
    echo.
)

pause
