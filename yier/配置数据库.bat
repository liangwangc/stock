@echo off
chcp 65001 >nul
title 配置数据库连接
color 0B

echo.
echo ========================================
echo 配置数据库连接
echo ========================================
echo.

cd /d "%~dp0"

echo 当前配置（api.php）:
echo ----------------------------------------
findstr /C:"db_host" api.php | findstr /V "//"
findstr /C:"db_user" api.php | findstr /V "//"
findstr /C:"db_pass" api.php | findstr /V "//"
findstr /C:"db_name" api.php | findstr /V "//"
echo.

echo ========================================
echo 选项
echo ========================================
echo.
echo [1] 使用现有数据库（修改数据库名）
echo [2] 创建新数据库 word_app
echo [3] 测试数据库连接
echo [4] 退出
echo.
set /p choice=请选择 (1-4): 

if "%choice%"=="1" goto :use_existing
if "%choice%"=="2" goto :create_new
if "%choice%"=="3" goto :test_connection
if "%choice%"=="4" exit /b

:use_existing
echo.
echo ========================================
echo 使用现有数据库
echo ========================================
echo.
set /p DB_NAME=请输入数据库名称: 
set /p DB_USER=请输入数据库用户名 (默认root): 
set /p DB_PASS=请输入数据库密码 (直接回车为空): 

if "%DB_USER%"=="" set DB_USER=root
if "%DB_PASS%"=="" set DB_PASS=

echo.
echo 正在修改配置...
echo.

REM 使用PowerShell修改文件
powershell -Command "(Get-Content api.php) -replace '\\$db_name = ''word_app'';', '$db_name = ''%DB_NAME%'';' | Set-Content api.php"
powershell -Command "(Get-Content api.php) -replace '\\$db_user = ''root'';', '$db_user = ''%DB_USER%'';' | Set-Content api.php"

if not "%DB_PASS%"=="" (
    powershell -Command "(Get-Content api.php) -replace '\\$db_pass = ''root'';', '$db_pass = ''%DB_PASS%'';' | Set-Content api.php"
) else (
    powershell -Command "(Get-Content api.php) -replace '\\$db_pass = ''root'';', '$db_pass = '''';' | Set-Content api.php"
)

echo [OK] 配置已更新
echo.
echo 新配置:
echo   数据库名: %DB_NAME%
echo   用户名: %DB_USER%
echo   密码: %DB_PASS%
echo.
echo 注意: 请确保该数据库已存在，并且包含必要的表结构
echo.
pause
goto :end

:create_new
echo.
echo ========================================
echo 创建新数据库 word_app
echo ========================================
echo.
echo 将创建数据库: word_app
echo.
call 创建数据库.bat
goto :end

:test_connection
echo.
echo ========================================
echo 测试数据库连接
echo ========================================
echo.
call 测试数据库连接.bat
goto :end

:end
pause
