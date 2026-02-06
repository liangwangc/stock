@echo off
chcp 65001 >nul
echo ========================================
echo 数据库连接测试
echo ========================================
echo.

cd /d "%~dp0"

echo 正在运行Python测试脚本...
echo.

python simple_test.py

echo.
echo ========================================
echo 测试完成
echo ========================================
echo.
echo 如果看到"✅ 数据库连接成功！"表示连接正常
echo 如果看到"❌"错误信息，请检查：
echo   1. MySQL服务是否启动
echo   2. 数据库密码是否正确（当前配置：root）
echo   3. 数据库 word_app 是否存在
echo.
pause
