#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试JSON序列化修复
验证date和datetime对象可以正确序列化
"""
import sys
import os
from datetime import datetime, date

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入修复后的函数
from utils.model_optimizer import _safe_json_dumps, _convert_to_serializable

def test_date_serialization():
    """测试date对象序列化"""
    print("=" * 60)
    print("测试date对象序列化")
    print("=" * 60)
    
    # 测试数据（模拟backtest_result）
    test_data = {
        'success': True,
        'start_date': '2026-01-01',
        'end_date': '2026-01-16',
        'trades': [
            {
                'date': date(2026, 1, 10),  # date对象
                'symbol': '000001',
                'action': 'BUY',
                'price': 10.5
            },
            {
                'date': date(2026, 1, 15),  # date对象
                'symbol': '000001',
                'action': 'SELL',
                'price': 11.2
            }
        ],
        'daily_values': [
            {
                'date': date(2026, 1, 10),  # date对象
                'capital': 100000.0,
                'total_value': 105000.0
            },
            {
                'date': datetime(2026, 1, 15, 15, 0, 0),  # datetime对象
                'capital': 100000.0,
                'total_value': 112000.0
            }
        ],
        'metrics': {
            'total_return': 12.5,
            'sharpe_ratio': 1.2
        }
    }
    
    print("\n1. 原始数据（包含date和datetime对象）:")
    print(f"   trades[0]['date'] 类型: {type(test_data['trades'][0]['date'])}")
    print(f"   daily_values[0]['date'] 类型: {type(test_data['daily_values'][0]['date'])}")
    print(f"   daily_values[1]['date'] 类型: {type(test_data['daily_values'][1]['date'])}")
    
    print("\n2. 使用_convert_to_serializable转换:")
    serializable_data = _convert_to_serializable(test_data)
    print(f"   trades[0]['date'] 类型: {type(serializable_data['trades'][0]['date'])}")
    print(f"   trades[0]['date'] 值: {serializable_data['trades'][0]['date']}")
    print(f"   daily_values[0]['date'] 类型: {type(serializable_data['daily_values'][0]['date'])}")
    print(f"   daily_values[0]['date'] 值: {serializable_data['daily_values'][0]['date']}")
    print(f"   daily_values[1]['date'] 类型: {type(serializable_data['daily_values'][1]['date'])}")
    print(f"   daily_values[1]['date'] 值: {serializable_data['daily_values'][1]['date']}")
    
    print("\n3. 使用_safe_json_dumps序列化:")
    try:
        json_str = _safe_json_dumps(test_data, ensure_ascii=False)
        print(f"   [OK] 序列化成功")
        print(f"   JSON长度: {len(json_str)} 字符")
        print(f"\n   JSON预览（前200字符）:")
        print(f"   {json_str[:200]}...")
        
        # 验证可以反序列化
        import json
        parsed = json.loads(json_str)
        print(f"\n4. 验证反序列化:")
        print(f"   [OK] 反序列化成功")
        print(f"   trades[0]['date']: {parsed['trades'][0]['date']}")
        print(f"   daily_values[0]['date']: {parsed['daily_values'][0]['date']}")
        print(f"   daily_values[1]['date']: {parsed['daily_values'][1]['date']}")
        
    except Exception as e:
        print(f"   [FAIL] 序列化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("测试完成：所有测试通过！")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_date_serialization()
    sys.exit(0 if success else 1)
