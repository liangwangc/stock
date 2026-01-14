"""
测试数据收集脚本

快速测试A股和美股数据收集功能是否正常
"""
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.batch_collect_10years_data import CNStockBatchCollector, USStockBatchCollector

def test_cn_collection():
    """测试A股数据收集"""
    print("=" * 60)
    print("测试A股数据收集（3只股票，1年数据）")
    print("=" * 60)
    
    try:
        collector = CNStockBatchCollector(batch_size=3, delay=0.5)
        result = collector.batch_collect(years=1, resume=False)
        
        print("\n" + "=" * 60)
        print("A股测试结果:")
        print(f"  已完成: {result['completed']}")
        print(f"  失败: {result['failed']}")
        print(f"  耗时: {result['total_duration_seconds']:.1f} 秒")
        print("=" * 60)
        
        return result['completed'] > 0
    except Exception as e:
        print(f"\nA股测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_us_collection():
    """测试美股数据收集"""
    print("\n" + "=" * 60)
    print("测试美股数据收集（3只股票，1年数据）")
    print("=" * 60)
    
    try:
        collector = USStockBatchCollector(batch_size=3, delay=0.5)
        result = collector.batch_collect(years=1, resume=False)
        
        print("\n" + "=" * 60)
        print("美股测试结果:")
        print(f"  已完成: {result['completed']}")
        print(f"  失败: {result['failed']}")
        print(f"  耗时: {result['total_duration_seconds']:.1f} 秒")
        print("=" * 60)
        
        return result['completed'] > 0
    except Exception as e:
        print(f"\n美股测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n开始测试数据收集功能...\n")
    
    # 测试A股
    cn_success = test_cn_collection()
    
    # 等待一下
    import time
    time.sleep(2)
    
    # 测试美股
    us_success = test_us_collection()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结:")
    print(f"  A股测试: {'✓ 通过' if cn_success else '✗ 失败'}")
    print(f"  美股测试: {'✓ 通过' if us_success else '✗ 失败'}")
    print("=" * 60)
    
    if cn_success and us_success:
        print("\n所有测试通过！可以开始正式的数据收集。")
        print("\n正式收集命令：")
        print("  A股: python scripts\\batch_collect_10years_data.py --market cn --batch-size 50")
        print("  美股: python scripts\\batch_collect_10years_data.py --market us --batch-size 50")
    else:
        print("\n部分测试失败，请检查错误信息并修复问题。")
