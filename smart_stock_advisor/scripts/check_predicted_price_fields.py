#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速检查预测价格字段是否存在
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection

def check_fields():
    """检查字段是否存在"""
    db = None
    try:
        db = DatabaseConnection()
        
        print("=" * 60)
        print("检查 stock_predictions 表字段")
        print("=" * 60)
        
        # 检查所有字段
        result = db.execute_query("SHOW COLUMNS FROM stock_predictions")
        existing_columns = [row['Field'] for row in result]
        
        print(f"\n当前表共有 {len(existing_columns)} 个字段")
        print("\n所有字段列表:")
        for i, col in enumerate(existing_columns, 1):
            print(f"  {i:2d}. {col}")
        
        # 检查目标字段
        print("\n" + "=" * 60)
        print("检查目标字段")
        print("=" * 60)
        
        has_predicted_close_price = 'predicted_close_price' in existing_columns
        has_predicted_change_pct = 'predicted_change_pct' in existing_columns
        
        print(f"\npredicted_close_price: {'✅ 存在' if has_predicted_close_price else '❌ 不存在'}")
        print(f"predicted_change_pct: {'✅ 存在' if has_predicted_change_pct else '❌ 不存在'}")
        
        if has_predicted_close_price and has_predicted_change_pct:
            print("\n✅ 所有字段都已存在！")
            return True
        else:
            print("\n⚠️  缺少字段，需要添加")
            print("\n可以运行以下SQL添加字段：")
            print("\n" + "-" * 60)
            if not has_predicted_close_price:
                print("ALTER TABLE `stock_predictions`")
                print("ADD COLUMN `predicted_close_price` DECIMAL(10,2) DEFAULT NULL")
                print("COMMENT '明日大概收盘价格' AFTER `current_price`;")
                print()
            if not has_predicted_change_pct:
                print("ALTER TABLE `stock_predictions`")
                print("ADD COLUMN `predicted_change_pct` DECIMAL(6,2) DEFAULT NULL")
                print("COMMENT '明日大概涨幅百分比' AFTER `predicted_close_price`;")
                print()
            print("ALTER TABLE `stock_predictions`")
            print("ADD INDEX `idx_predicted_change_pct` (`predicted_change_pct`);")
            print("-" * 60)
            return False
        
    except Exception as e:
        print(f"\n❌ 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if db:
            db.close_connection()

if __name__ == '__main__':
    check_fields()
