@echo off
chcp 65001 >nul
echo ========================================
echo 环境检查脚本
echo ========================================
echo.

echo [1] 检查 PHP...
where php >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ PHP 已安装
    php --version
) else (
    echo ❌ PHP 未安装或未添加到PATH
    echo    请安装 PHP 或将其添加到系统PATH
)
echo.

echo [2] 检查 MySQL...
where mysql >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ MySQL 客户端已安装
    mysql --version
) else (
    echo ❌ MySQL 客户端未安装或未添加到PATH
    echo    可以使用 MySQL Workbench 或其他工具连接数据库
)
echo.

echo [3] 检查 Python...
where python >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Python 已安装
    python --version
    echo.
    echo [3.1] 检查 pymysql...
    python -c "import pymysql" >nul 2>&1
    if %errorlevel% == 0 (
        echo ✅ pymysql 已安装
        echo    可以运行: python test_db_connection.py
    ) else (
        echo ⚠️  pymysql 未安装
        echo    安装命令: pip install pymysql
    )
) else (
    echo ❌ Python 未安装或未添加到PATH
)
echo.

echo [4] 检查项目文件...
if exist "api.php" (
    echo ✅ api.php 存在
) else (
    echo ❌ api.php 不存在
)

if exist "index.html" (
    echo ✅ index.html 存在
) else (
    echo ❌ index.html 不存在
)

if exist "word_app_backup_20260129.sql" (
    echo ✅ 数据库备份文件存在
) else (
    echo ⚠️  数据库备份文件不存在
)
echo.

echo [5] 检查 MySQL 服务...
sc query MySQL >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ MySQL 服务已注册
    sc query MySQL | findstr "STATE"
) else (
    echo ⚠️  未找到 MySQL 服务（可能使用其他名称或未安装）
)
echo.

echo ========================================
echo 检查完成
echo ========================================
echo.
echo 下一步操作：
echo 1. 如果 MySQL 未运行，请启动 MySQL 服务
echo 2. 导入数据库: mysql -u root -p ^< word_app_backup_20260129.sql
echo 3. 配置 api.php 中的数据库连接信息
echo 4. 启动 Web 服务器测试项目
echo.
pause
