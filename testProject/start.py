#!/usr/bin/env python3
"""
稽核档案管理系统 - 启动脚本

这个脚本位于项目根目录，用于启动Web应用
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入web应用
from scripts.main.web_app import app

if __name__ == "__main__":
    print("🚀 启动稽核档案管理系统...")
    print("🌐 请在浏览器中访问: http://localhost:5000")
    print("🔐 默认管理员账户: admin / admin123")
    app.run(debug=True, host='0.0.0.0', port=5000)
