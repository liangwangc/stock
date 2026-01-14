#!/bin/bash

echo "========================================"
echo "量化交易平台 - 快速启动"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python，请先安装Python 3.7+"
    exit 1
fi

echo "[1/2] 检查依赖包..."
if ! python3 -c "import pandas" &> /dev/null; then
    echo "[提示] 正在安装依赖包，请稍候..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖包安装失败"
        exit 1
    fi
else
    echo "[提示] 依赖包已安装"
fi

echo ""
echo "[2/2] 启动量化交易平台..."
echo ""
python3 main.py

