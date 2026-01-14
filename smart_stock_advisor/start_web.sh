#!/bin/bash
echo "========================================"
echo "  股票预测系统 Web 应用启动脚本"
echo "========================================"
echo ""
echo "正在启动Web服务器..."
echo ""

cd "$(dirname "$0")"
python3 web_app.py
