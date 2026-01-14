#!/usr/bin/env python3
"""
项目启动脚本

这是一个简单的启动脚本，可以直接运行项目。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 导入web应用
from scripts.main.web_app import app

if __name__ == "__main__":
    print("🚀 启动稽核档案管理系统...")
    print("🌐 请在浏览器中访问: http://localhost:5000")
    print("🔐 默认管理员账户: admin / admin123")
    app.run(debug=True, host='0.0.0.0', port=5000) 