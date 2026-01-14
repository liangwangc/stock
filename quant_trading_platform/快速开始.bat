@echo off
chcp 65001 >nul
echo ========================================
echo 量化交易平台 - 快速启动
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

echo [1/2] 检查依赖包...
pip show pandas >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包，请稍候...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] 依赖包安装失败，请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
) else (
    echo [提示] 依赖包已安装
)

echo.
echo [2/2] 启动量化交易平台...
echo.
python main.py

pause

