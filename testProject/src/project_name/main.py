#!/usr/bin/env python3
"""
Python项目主程序

这是项目的主要入口点。
"""

import os
import sys
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def hello_world(name: Optional[str] = None) -> str:
    """
    简单的问候函数
    
    Args:
        name: 要问候的名字，如果为None则使用环境变量或默认值
        
    Returns:
        问候语字符串
    """
    if name is None:
        name = os.getenv("USER", "World")
    
    return f"Hello, {name}!"


def get_app_info() -> dict:
    """
    获取应用信息
    
    Returns:
        包含应用信息的字典
    """
    return {
        "name": os.getenv("APP_NAME", "Python项目"),
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "False").lower() == "true"
    }


def main() -> None:
    """
    主函数
    
    这是程序的主要入口点。
    """
    print("=" * 50)
    print("Python项目启动")
    print("=" * 50)
    
    # 显示应用信息
    app_info = get_app_info()
    print(f"应用名称: {app_info['name']}")
    print(f"版本: {app_info['version']}")
    print(f"环境: {app_info['environment']}")
    print(f"调试模式: {app_info['debug']}")
    print()
    
    # 显示问候语
    greeting = hello_world()
    print(greeting)
    print()
    
    # 显示Python版本信息
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print()
    
    print("=" * 50)
    print("程序执行完成")
    print("=" * 50)


if __name__ == "__main__":
    main() 