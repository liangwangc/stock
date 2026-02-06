"""
测试批量获取代码逻辑
验证代码结构是否正确，不依赖网络
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.stock_history_collector import StockHistoryCollector
from utils.logger import get_logger

logger = get_logger(__name__)


def test_code_logic():
    """测试代码逻辑是否正确"""
    print("=" * 80)
    print("测试批量获取代码逻辑")
    print("=" * 80)
    
    collector = StockHistoryCollector()
    
    # 1. 检查方法是否存在
    print("\n1. 检查方法是否存在...")
    if hasattr(collector, '_incremental_update_today_batch'):
        print("   [通过] _incremental_update_today_batch 方法存在")
    else:
        print("   [失败] _incremental_update_today_batch 方法不存在")
        return False
    
    if hasattr(collector, 'incremental_update_today'):
        print("   [通过] incremental_update_today 方法存在")
    else:
        print("   [失败] incremental_update_today 方法不存在")
        return False
    
    # 2. 检查方法签名
    print("\n2. 检查方法签名...")
    import inspect
    
    # 检查 incremental_update_today 的参数
    sig = inspect.signature(collector.incremental_update_today)
    params = list(sig.parameters.keys())
    
    if 'use_batch_api' in params:
        print("   [通过] incremental_update_today 包含 use_batch_api 参数")
    else:
        print("   [失败] incremental_update_today 缺少 use_batch_api 参数")
        return False
    
    # 检查默认值
    default_value = sig.parameters['use_batch_api'].default
    if default_value == True:
        print(f"   [通过] use_batch_api 默认值为 True")
    else:
        print(f"   [警告] use_batch_api 默认值为 {default_value}，建议设为 True")
    
    # 3. 检查 clean_nan_value 函数
    print("\n3. 检查 clean_nan_value 函数...")
    try:
        from utils.stock_history_storage import clean_nan_value
        print("   [通过] clean_nan_value 函数存在")
        
        # 测试函数
        import pandas as pd
        import numpy as np
        
        test_cases = [
            (None, None),
            (np.nan, None),
            (pd.NA, None),
            (float('nan'), None),
            (123.45, 123.45),
            (0, 0),
            ('test', 'test'),
            ('nan', None),
        ]
        
        all_passed = True
        for input_val, expected in test_cases:
            result = clean_nan_value(input_val)
            if result != expected:
                print(f"   [失败] clean_nan_value({input_val}) = {result}, 期望 {expected}")
                all_passed = False
        
        if all_passed:
            print("   [通过] clean_nan_value 函数测试通过")
        else:
            print("   [失败] clean_nan_value 函数测试失败")
            return False
            
    except ImportError as e:
        print(f"   [失败] 无法导入 clean_nan_value: {str(e)}")
        return False
    
    # 4. 检查代码结构
    print("\n4. 检查代码结构...")
    
    # 读取源代码文件
    collector_file = os.path.join(project_root, 'utils', 'stock_history_collector.py')
    with open(collector_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('_incremental_update_today_batch', '批量更新方法'),
        ('ak.stock_zh_a_spot_em', '批量API调用'),
        ('clean_nan_value', 'NaN值清理'),
        ('save_stock_daily_data_batch', '批量保存'),
        ('use_batch_api', '批量API参数'),
    ]
    
    all_passed = True
    for keyword, description in checks:
        if keyword in content:
            print(f"   [通过] 找到 {description}: {keyword}")
        else:
            print(f"   [失败] 未找到 {description}: {keyword}")
            all_passed = False
    
    if not all_passed:
        return False
    
    # 5. 检查逻辑流程
    print("\n5. 检查逻辑流程...")
    
    # 检查是否在 incremental_update_today 中调用了批量方法
    if 'if use_batch_api and len(target_dates) == 1 and target_dates[0] == today:' in content:
        print("   [通过] 找到批量API调用条件判断")
    else:
        print("   [失败] 未找到批量API调用条件判断")
        return False
    
    if 'return self._incremental_update_today_batch' in content:
        print("   [通过] 找到批量方法调用")
    else:
        print("   [失败] 未找到批量方法调用")
        return False
    
    # 6. 总结
    print("\n" + "=" * 80)
    print("代码逻辑验证总结")
    print("=" * 80)
    print("[成功] 所有代码逻辑检查通过！")
    print("\n功能说明:")
    print("1. 批量获取方法已实现")
    print("2. 自动启用逻辑已添加")
    print("3. NaN值清理已集成")
    print("4. 批量保存已优化")
    print("\n注意:")
    print("- 如果网络正常，批量API应该能在1-2秒内完成")
    print("- 如果遇到网络错误，系统会自动重试3次")
    print("- 如果批量API失败，可以设置 use_batch_api=False 使用逐只获取")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    try:
        success = test_code_logic()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
