@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo 启动项目服务器
echo ========================================
echo.

REM 检查XAMPP PHP
if exist "C:\xampp\php\php.exe" (
    echo 找到 PHP: C:\xampp\php\php.exe
    echo.
    echo 正在启动服务器...
    echo 访问地址: http://localhost:8000
    echo 按 Ctrl+C 停止服务器
    echo.
    "C:\xampp\php\php.exe" -S localhost:8000
    goto :end
)

REM 检查XAMPP64 PHP
if exist "C:\xampp64\php\php.exe" (
    echo 找到 PHP: C:\xampp64\php\php.exe
    echo.
    echo 正在启动服务器...
    echo 访问地址: http://localhost:8000
    echo 按 Ctrl+C 停止服务器
    echo.
    "C:\xampp64\php\php.exe" -S localhost:8000
    goto :end
)

REM 检查系统PATH中的PHP
where php >nul 2>&1
if %errorlevel% == 0 (
    echo 找到 PHP（系统PATH中）
    echo.
    echo 正在启动服务器...
    echo 访问地址: http://localhost:8000
    echo 按 Ctrl+C 停止服务器
    echo.
    php -S localhost:8000
    goto :end
)

REM 未找到PHP
echo 错误: 未找到 PHP！
echo.
echo 请先安装 XAMPP:
echo   下载地址: https://www.apachefriends.org/
echo   安装到: C:\xampp\
echo.
echo 如果已安装 XAMPP，请检查路径是否正确
echo.

:end
pause
