@echo off
chcp 65001 >nul
title 付一二项目 - 完整诊断工具
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║         付一二（MemoCalendar）项目诊断工具              ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [步骤 1/5] 检查项目文件...
echo ──────────────────────────────────────────────────────────
if exist "api.php" (
    echo ✅ api.php 存在
) else (
    echo ❌ api.php 不存在
    goto :error
)

if exist "index.html" (
    echo ✅ index.html 存在
) else (
    echo ❌ index.html 不存在
    goto :error
)

if exist "word_app_backup_20260129.sql" (
    echo ✅ 数据库备份文件存在
) else (
    echo ⚠️  数据库备份文件不存在
)
echo.

echo [步骤 2/5] 检查环境...
echo ──────────────────────────────────────────────────────────

where php >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ PHP 已安装
    php --version | findstr "PHP"
) else (
    echo ❌ PHP 未安装或未添加到PATH
    echo    提示: 可以安装XAMPP/WAMP或单独安装PHP
)
echo.

where mysql >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ MySQL 客户端已安装
    mysql --version
) else (
    echo ⚠️  MySQL 客户端未安装或未添加到PATH
    echo    提示: 可以使用MySQL Workbench或其他工具
)
echo.

where python >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Python 已安装
    python --version
    python -c "import pymysql" >nul 2>&1
    if %errorlevel% == 0 (
        echo ✅ pymysql 已安装
    ) else (
        echo ⚠️  pymysql 未安装
        echo    安装命令: pip install pymysql
    )
) else (
    echo ❌ Python 未安装
)
echo.

echo [步骤 3/5] 检查MySQL服务...
echo ──────────────────────────────────────────────────────────

sc query MySQL >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ 找到 MySQL 服务
    sc query MySQL | findstr "STATE"
) else (
    echo ⚠️  未找到标准 MySQL 服务
    echo    可能的原因:
    echo    1. MySQL服务名称不同（如MySQL80, MySQL57）
    echo    2. 使用XAMPP/WAMP（需要手动启动）
    echo    3. MySQL未安装
    echo.
    echo    请手动检查:
    echo    - 打开"服务"管理器（services.msc）
    echo    - 查找MySQL相关服务
    echo    - 或使用XAMPP/WAMP控制面板
)
echo.

echo [步骤 4/5] 检查数据库配置...
echo ──────────────────────────────────────────────────────────
findstr /C:"db_pass" api.php | findstr /V "//"
echo    提示: 当前密码配置为 'root'
echo    如果您的MySQL密码不同，请修改 api.php 第20行
echo.

echo [步骤 5/5] 测试数据库连接...
echo ──────────────────────────────────────────────────────────

where python >nul 2>&1
if %errorlevel% == 0 (
    python -c "import pymysql" >nul 2>&1
    if %errorlevel% == 0 (
        echo 正在尝试连接数据库...
        python simple_test.py
    ) else (
        echo ⚠️  无法运行Python测试（pymysql未安装）
        echo    请先安装: pip install pymysql
    )
) else (
    echo ⚠️  无法运行Python测试（Python未安装）
    echo    请使用其他方法测试数据库连接
)
echo.

echo ╔══════════════════════════════════════════════════════════╗
echo ║                     诊断完成                              ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo 下一步操作:
echo.
echo 1. 如果MySQL服务未启动:
echo    - 打开服务管理器（Win+R，输入 services.msc）
echo    - 找到MySQL服务并启动
echo    - 或使用XAMPP/WAMP控制面板启动MySQL
echo.
echo 2. 如果数据库未导入:
echo    - 运行: mysql -u root -p ^< word_app_backup_20260129.sql
echo    - 或使用MySQL Workbench导入SQL文件
echo.
echo 3. 如果密码不正确:
echo    - 编辑 api.php，修改第20行的密码
echo.
echo 4. 测试完成后:
echo    - 双击"启动服务器.bat"启动PHP服务器
echo    - 或配置Apache/Nginx
echo    - 浏览器访问项目
echo.
goto :end

:error
echo.
echo ❌ 项目文件不完整，请检查！
echo.
pause
exit /b 1

:end
pause
