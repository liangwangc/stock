@echo off
chcp 65001 >nul
title 创建数据库
color 0B

echo.
echo ========================================
echo 创建 word_app 数据库
echo ========================================
echo.

set DB_NAME=word_app
set DB_USER=root
set DB_PASS=

echo 正在查找 MySQL...
echo.

REM 检查XAMPP MySQL
if exist "C:\xampp\mysql\bin\mysql.exe" (
    set MYSQL_PATH=C:\xampp\mysql\bin\mysql.exe
    set MYSQLADMIN_PATH=C:\xampp\mysql\bin\mysqladmin.exe
    goto :found
)

if exist "C:\xampp64\mysql\bin\mysql.exe" (
    set MYSQL_PATH=C:\xampp64\mysql\bin\mysql.exe
    set MYSQLADMIN_PATH=C:\xampp64\mysql\bin\mysqladmin.exe
    goto :found
)

REM 检查WAMP MySQL
if exist "C:\wamp64\bin\mysql\mysql8.0.31\bin\mysql.exe" (
    set MYSQL_PATH=C:\wamp64\bin\mysql\mysql8.0.31\bin\mysql.exe
    set MYSQLADMIN_PATH=C:\wamp64\bin\mysql\mysql8.0.31\bin\mysqladmin.exe
    goto :found
)

REM 检查系统PATH
where mysql >nul 2>&1
if %errorlevel% == 0 (
    set MYSQL_PATH=mysql
    set MYSQLADMIN_PATH=mysqladmin
    goto :found
)

echo [X] 未找到 MySQL！
echo.
echo 请确保：
echo   1. 已安装 XAMPP 或 WAMP
echo   2. MySQL 服务已启动
echo   3. MySQL 已添加到系统PATH
echo.
pause
exit /b 1

:found
echo [OK] 找到 MySQL: %MYSQL_PATH%
echo.

REM 检查MySQL服务是否运行
echo 检查 MySQL 服务状态...
"%MYSQLADMIN_PATH%" -u %DB_USER% ping >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] MySQL 服务可能未启动
    echo.
    echo 请先启动 MySQL 服务：
    echo   - XAMPP: 打开 XAMPP Control Panel，启动 MySQL
    echo   - WAMP: 确保 MySQL 服务运行
    echo.
    pause
    exit /b 1
)

echo [OK] MySQL 服务正在运行
echo.

REM 创建数据库
echo [1/3] 创建数据库 %DB_NAME%...
echo.
"%MYSQL_PATH%" -u %DB_USER% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>nul
if %errorlevel% == 0 (
    echo [OK] 数据库创建成功
) else (
    echo [X] 数据库创建失败
    echo.
    echo 请检查：
    echo   1. MySQL 用户名和密码是否正确
    echo   2. 是否有创建数据库的权限
    echo.
    pause
    exit /b 1
)

echo.

REM 导入数据库结构
echo [2/3] 导入数据库结构...
echo.
if exist "word_app_backup_20260129.sql" (
    "%MYSQL_PATH%" -u %DB_USER% %DB_NAME% < word_app_backup_20260129.sql 2>nul
    if %errorlevel% == 0 (
        echo [OK] 数据库结构导入成功
    ) else (
        echo [警告] 导入过程中可能有错误，请检查
    )
) else (
    echo [警告] 未找到 word_app_backup_20260129.sql 文件
    echo 将只创建空数据库
)

echo.

REM 升级数据库（添加新功能）
echo [3/3] 升级数据库（添加登录功能）...
echo.
if exist "database_upgrade.sql" (
    "%MYSQL_PATH%" -u %DB_USER% %DB_NAME% < database_upgrade.sql 2>nul
    if %errorlevel% == 0 (
        echo [OK] 数据库升级成功
    ) else (
        echo [警告] 升级过程中可能有错误，请检查
    )
) else (
    echo [警告] 未找到 database_upgrade.sql 文件
    echo 新功能可能无法使用
)

echo.
echo ========================================
echo 数据库创建完成！
echo ========================================
echo.
echo 默认管理员账号：
echo   账号: admin
echo   密码: admin123
echo.
echo 现在可以登录系统了！
echo.
pause
