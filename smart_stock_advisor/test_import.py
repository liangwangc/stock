#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试导入web_app.py"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    print("正在导入web_app...")
    import web_app
    print("✅ web_app导入成功")
except Exception as e:
    print(f"❌ web_app导入失败: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("正在导入utils.model_optimizer...")
    from utils.model_optimizer import ModelOptimizer
    print("✅ ModelOptimizer导入成功")
except Exception as e:
    print(f"❌ ModelOptimizer导入失败: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("正在导入utils.scheduled_task_manager...")
    from utils.scheduled_task_manager import ScheduledTaskManager
    print("✅ ScheduledTaskManager导入成功")
except Exception as e:
    print(f"❌ ScheduledTaskManager导入失败: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ 所有模块导入成功！")
