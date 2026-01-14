@echo off
REM 批量收集10年历史数据启动脚本（Windows）
REM 使用方法：双击运行或命令行执行 start_data_collection.bat

echo ============================================================
echo 批量收集A股和美股10年历史数据
echo ============================================================
echo.

REM 切换到脚本目录
cd /d "%~dp0\.."
cd smart_stock_advisor

REM 检查Python是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python，请先安装Python
    pause
    exit /b 1
)

echo 当前目录: %CD%
echo.

REM 提示用户选择
echo 请选择要收集的市场：
echo 1. A股（CN）
echo 2. 美股（US）
echo 3. 测试模式（只收集5只股票，1年数据）
echo.
set /p choice=请输入选项 (1/2/3): 

if "%choice%"=="1" (
    echo.
    echo 开始收集A股数据（每批50只，延迟1秒）...
    echo 提示：可以使用Ctrl+C中断，然后使用--resume参数继续
    echo.
    python scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
) else if "%choice%"=="2" (
    echo.
    echo 开始收集美股数据（每批50只，延迟1秒）...
    echo 提示：可以使用Ctrl+C中断，然后使用--resume参数继续
    echo.
    python scripts\batch_collect_10years_data.py --market us --batch-size 50 --delay 1.0
) else if "%choice%"=="3" (
    echo.
    echo 测试模式：收集5只A股，1年数据...
    echo.
    python scripts\batch_collect_10years_data.py --market cn --batch-size 5 --years 1 --delay 0.5
) else (
    echo 无效选项
)

echo.
echo ============================================================
echo 数据收集完成或已中断
echo ============================================================
pause
