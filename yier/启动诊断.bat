@echo off
chcp 65001 >nul
title 启动诊断工具
color 0E

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║             项目启动诊断工具                            ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

set ERRORS=0

echo [检查1] PHP 环境
echo ──────────────────────────────────────────────────────────
where php >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PHP 未安装或未添加到PATH
    echo.
    echo 解决方案：
    echo   方案A: 安装 XAMPP（推荐）
    echo     - 下载: https://www.apachefriends.org/
    echo     - 安装后，PHP路径: C:\xampp\php\php.exe
    echo.
    echo   方案B: 安装 WAMP
    echo     - 下载: https://www.wampserver.com/
    echo     - 安装后，PHP路径: C:\wamp64\bin\php\phpX.X.X\php.exe
    echo.
    echo   方案C: 单独安装 PHP
    echo     - 下载: https://windows.php.net/download/
    echo     - 解压到 C:\php\
    echo     - 添加到系统PATH环境变量
    echo.
    set /a ERRORS+=1
    goto :check2
)

echo ✅ PHP 已安装
php --version | findstr "PHP"
echo.

:check2
echo [检查2] 项目文件
echo ──────────────────────────────────────────────────────────
if not exist "api.php" (
    echo ❌ api.php 不存在
    set /a ERRORS+=1
) else (
    echo ✅ api.php 存在
)

if not exist "index.html" (
    echo ❌ index.html 不存在
    set /a ERRORS+=1
) else (
    echo ✅ index.html 存在
)
echo.

echo [检查3] 端口占用
echo ──────────────────────────────────────────────────────────
netstat -ano | findstr ":8000" >nul 2>&1
if %errorlevel% == 0 (
    echo ⚠️  端口 8000 已被占用
    echo    可以使用端口 8080 启动
    echo    命令: php -S localhost:8080
) else (
    echo ✅ 端口 8000 可用
)
echo.

echo [检查4] MySQL 服务（可选，但建议检查）
echo ──────────────────────────────────────────────────────────
sc query MySQL >nul 2>&1
if %errorlevel% == 0 (
    sc query MySQL | findstr "RUNNING" >nul 2>&1
    if %errorlevel% == 0 (
        echo ✅ MySQL 服务正在运行
    ) else (
        echo ⚠️  MySQL 服务已安装但未运行
        echo    请启动 MySQL 服务
    )
) else (
    echo ⚠️  未找到标准 MySQL 服务
    echo    如果使用 XAMPP/WAMP，请手动检查
)
echo.

echo ═══════════════════════════════════════════════════════════
echo 诊断结果
echo ═══════════════════════════════════════════════════════════
echo.

if %ERRORS% == 0 (
    echo ✅ 所有检查通过！可以启动项目
    echo.
    echo 启动命令：
    echo   php -S localhost:8000
    echo.
    echo 或双击运行: 启动项目.bat
    echo.
    echo 启动后访问: http://localhost:8000
) else (
    echo ❌ 发现 %ERRORS% 个问题，请先解决后再启动
    echo.
    echo 常见问题解决：
    echo   1. PHP未安装 → 安装 XAMPP/WAMP
    echo   2. 端口被占用 → 使用其他端口（8080）
    echo   3. MySQL未运行 → 启动 MySQL 服务
    echo.
)

echo ═══════════════════════════════════════════════════════════
pause
