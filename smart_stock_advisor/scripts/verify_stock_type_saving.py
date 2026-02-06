#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证设置页面和主页的预测是否都正确保存了stock_type字段
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection

def verify_stock_type_saving():
    """验证stock_type字段的保存情况"""
    db = None
    try:
        db = DatabaseConnection()
        
        print("=" * 80)
        print("验证设置页面和主页的预测是否都正确保存了stock_type字段")
        print("=" * 80)
        
        # 1. 检查字段是否存在
        print("\n【步骤1】检查数据库字段...")
        result = db.execute_query("SHOW COLUMNS FROM stock_predictions")
        existing_columns = [row['Field'] for row in result]
        
        has_stock_type = 'stock_type' in existing_columns
        has_prediction_type = 'prediction_type' in existing_columns
        
        print(f"  stock_type 字段: {'✅ 存在' if has_stock_type else '❌ 不存在'}")
        print(f"  prediction_type 字段: {'✅ 存在' if has_prediction_type else '❌ 不存在'}")
        
        if not has_stock_type and not has_prediction_type:
            print("\n⚠️  两个字段都不存在！")
            return False
        
        # 2. 查询最近的预测记录
        print("\n【步骤2】查询最近的预测记录...")
        
        # 查询最近24小时的预测记录
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        if has_stock_type:
            sql = """
                SELECT 
                    symbol, name, prediction_date, target_date,
                    stock_type, prediction_type,
                    prediction, confidence,
                    prediction_time
                FROM stock_predictions
                WHERE prediction_time >= %s
                ORDER BY prediction_time DESC
                LIMIT 50
            """
        else:
            sql = """
                SELECT 
                    symbol, name, prediction_date, target_date,
                    prediction_type,
                    prediction, confidence,
                    prediction_time
                FROM stock_predictions
                WHERE prediction_time >= %s
                ORDER BY prediction_time DESC
                LIMIT 50
            """
        
        records = db.execute_query(sql, (yesterday,))
        
        if not records:
            print("  ⚠️  最近24小时内没有预测记录")
            print("  建议：执行一次预测后再检查")
            return False
        
        print(f"  找到 {len(records)} 条最近24小时的预测记录\n")
        
        # 3. 统计字段值分布
        print("【步骤3】统计字段值分布...")
        
        if has_stock_type:
            stock_type_counts = {}
            prediction_type_counts = {}
            
            for r in records:
                stock_type = r.get('stock_type')
                prediction_type = r.get('prediction_type')
                
                if stock_type:
                    stock_type_counts[stock_type] = stock_type_counts.get(stock_type, 0) + 1
                if prediction_type:
                    prediction_type_counts[prediction_type] = prediction_type_counts.get(prediction_type, 0) + 1
            
            print("\n  stock_type 字段值分布：")
            for value, count in stock_type_counts.items():
                print(f"    {value}: {count} 条")
            
            print("\n  prediction_type 字段值分布：")
            for value, count in prediction_type_counts.items():
                print(f"    {value}: {count} 条")
            
            # 检查值映射是否正确
            print("\n【步骤4】检查值映射...")
            correct_mapping = True
            for r in records:
                stock_type = r.get('stock_type')
                prediction_type = r.get('prediction_type')
                
                if stock_type and prediction_type:
                    # 检查映射是否正确
                    expected_stock_type = None
                    if prediction_type == 'after_close':
                        expected_stock_type = '收盘-明日'
                    elif prediction_type == 'before_close':
                        expected_stock_type = '未收盘-明日'
                    
                    if expected_stock_type and stock_type != expected_stock_type:
                        print(f"  ⚠️  映射错误: {r.get('symbol')} - prediction_type={prediction_type}, stock_type={stock_type}, 期望={expected_stock_type}")
                        correct_mapping = False
            
            if correct_mapping:
                print("  ✅ 所有记录的映射都正确")
        else:
            # 只有prediction_type字段
            prediction_type_counts = {}
            for r in records:
                prediction_type = r.get('prediction_type')
                if prediction_type:
                    prediction_type_counts[prediction_type] = prediction_type_counts.get(prediction_type, 0) + 1
            
            print("\n  prediction_type 字段值分布：")
            for value, count in prediction_type_counts.items():
                print(f"    {value}: {count} 条")
        
        # 4. 显示最近10条记录的详细信息
        print("\n【步骤4】最近10条记录的详细信息：")
        print("-" * 80)
        if has_stock_type:
            print(f"{'股票代码':<10} {'股票名称':<12} {'stock_type':<15} {'prediction_type':<18} {'预测时间':<20}")
            print("-" * 80)
            for r in records[:10]:
                symbol = r.get('symbol', '')
                name = r.get('name', '')[:10]
                stock_type = r.get('stock_type', 'NULL')
                prediction_type = r.get('prediction_type', 'NULL')
                prediction_time = r.get('prediction_time', '')
                print(f"{symbol:<10} {name:<12} {str(stock_type):<15} {str(prediction_type):<18} {str(prediction_time):<20}")
        else:
            print(f"{'股票代码':<10} {'股票名称':<12} {'prediction_type':<18} {'预测时间':<20}")
            print("-" * 80)
            for r in records[:10]:
                symbol = r.get('symbol', '')
                name = r.get('name', '')[:10]
                prediction_type = r.get('prediction_type', 'NULL')
                prediction_time = r.get('prediction_time', '')
                print(f"{symbol:<10} {name:<12} {str(prediction_type):<18} {str(prediction_time):<20}")
        
        print("-" * 80)
        
        # 5. 总结
        print("\n" + "=" * 80)
        print("验证总结")
        print("=" * 80)
        
        if has_stock_type:
            has_after_close = any(r.get('stock_type') == '收盘-明日' for r in records)
            has_before_close = any(r.get('stock_type') == '未收盘-明日' for r in records)
            
            print(f"\n✅ stock_type 字段存在")
            print(f"  - 收盘-明日记录: {'✅ 有' if has_after_close else '❌ 无'}")
            print(f"  - 未收盘-明日记录: {'✅ 有' if has_before_close else '❌ 无'}")
            
            if has_after_close and has_before_close:
                print("\n✅ 设置页面和主页的预测都已正确保存stock_type字段！")
                return True
            else:
                print("\n⚠️  部分类型的预测记录缺失")
                return False
        else:
            print("\n⚠️  数据库中没有stock_type字段，使用prediction_type字段")
            print("  建议：添加stock_type字段以支持中文值")
            return False
        
    except Exception as e:
        print(f"\n❌ 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if db:
            db.close_connection()

if __name__ == '__main__':
    verify_stock_type_saving()
