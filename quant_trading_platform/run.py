"""
快速启动脚本
"""
import os
import sys

# 确保在正确的目录运行
if __name__ == "__main__":
    # 切换到脚本所在目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # 运行主程序
    from main import main
    main()

