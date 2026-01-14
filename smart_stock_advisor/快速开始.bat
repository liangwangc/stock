@echo off
chcp 65001 >nul
echo ============================================================
echo Smart Stock Advisor - 智能股票预测系统
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 检查依赖是否安装
echo 正在检查依赖...
python -c "import pandas, numpy, akshare, matplotlib" >nul 2>&1
if errorlevel 1 (
    echo [提示] 检测到缺少依赖，正在安装...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo.
echo 依赖检查完成！
echo.
echo 请输入股票代码（如：600519），或按Ctrl+C退出
echo.

REM 运行主程序
python main.py

pause



