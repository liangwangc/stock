"""
测试新闻获取和股票匹配（只运行一次）
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.data_processing.get_cls_news import fetch_and_store_news

if __name__ == '__main__':
    print("=" * 80)
    print("测试新闻获取和股票匹配功能（单次运行）")
    print("=" * 80)
    
    try:
        fetch_and_store_news()
        print("\n" + "=" * 80)
        print("[成功] 测试完成")
        print("=" * 80)
    except Exception as e:
        print(f"\n[失败] 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
