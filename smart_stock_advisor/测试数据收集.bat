@echo off
REM 测试数据收集脚本（Windows）
REM 分别测试A股和美股数据收集功能

echo ============================================================
echo 测试数据收集功能
echo ============================================================
echo.

cd /d "%~dp0\.."
cd smart_stock_advisor

echo 当前目录: %CD%
echo.

echo ============================================================
echo 测试1: A股数据收集（3只股票，1年数据）
echo ============================================================
echo.
python scripts\batch_collect_10years_data.py --market cn --batch-size 3 --years 1 --delay 0.5

if errorlevel 1 (
    echo.
    echo A股测试失败！
    pause
    exit /b 1
)

echo.
echo ============================================================
echo A股测试完成，等待3秒后开始美股测试...
echo ============================================================
timeout /t 3 /nobreak >nul

echo.
echo ============================================================
echo 测试2: 美股数据收集（3只股票，1年数据）
echo ============================================================
echo.
python scripts\batch_collect_10years_data.py --market us --batch-size 3 --years 1 --delay 0.5

if errorlevel 1 (
    echo.
    echo 美股测试失败！
    pause
    exit /b 1
)

echo.
echo ============================================================
echo 所有测试完成！
echo ============================================================
echo.
echo 如果测试成功，可以开始正式收集：
echo   A股: python scripts\batch_collect_10years_data.py --market cn --batch-size 50
echo   美股: python scripts\batch_collect_10years_data.py --market us --batch-size 50
echo.
pause
