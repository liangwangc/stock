#!/usr/bin/env python3
"""
项目启动脚本

这是一个简单的启动脚本，可以直接运行项目。
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from project_name.main import main

if __name__ == "__main__":
    main() 