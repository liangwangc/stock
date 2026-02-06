#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查"未收盘-明天"预测是否保存了明日预测价格和涨幅
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection

def check_before_close_predictions():
    """检查未收盘-明天预测的数据"""
    db = None
    try:
        db = DatabaseConnection()
        
        print("=" * 80)
        print("检查'未收盘-明天'预测是否保存了明日预测价格和涨幅")
        print("=" * 80)
        
        # 1. 检查字段是否存在
        print("\n【步骤1】检查数据库字段...")
        result = db.execute_query("SHOW COLUMNS FROM stock_predictions")
        existing_columns = [row['Field'] for row in result]
        
        has_predicted_close_price = 'predicted_close_price' in existing_columns
        has_predicted_change_pct = 'predicted_change_pct' in existing_columns
        has_prediction_type = 'prediction_type' in existing_columns
        
        print(f"  predicted_close_price 字段: {'✅ 存在' if has_predicted_close_price else '❌ 不存在'}")
        print(f"  predicted_change_pct 字段: {'✅ 存在' if has_predicted_change_pct else '❌ 不存在'}")
        print(f"  prediction_type 字段: {'✅ 存在' if has_prediction_type else '❌ 不存在'}")
        
        if not has_predicted_close_price or not has_predicted_change_pct:
            print("\n⚠️  缺少必要字段！请先运行以下脚本添加字段：")
            print("  python scripts/check_and_add_predicted_price_fields.py")
            return False
        
        if not has_prediction_type:
            print("\n⚠️  缺少 prediction_type 字段！")
            return False
        
        # 2. 查询未收盘-明天的预测记录
        print("\n【步骤2】查询'未收盘-明天'预测记录...")
        
        # 查询最近的 before_close 类型记录
        sql = """
            SELECT 
                symbol, name, prediction_date, target_date, prediction_type,
                current_price, predicted_close_price, predicted_change_pct,
                prediction, up_probability, down_probability, confidence,
                prediction_time
            FROM stock_predictions
            WHERE prediction_type = 'before_close'
            ORDER BY prediction_time DESC
            LIMIT 20
        """
        
        records = db.execute_query(sql)
        
        if not records:
            print("  ⚠️  没有找到'未收盘-明天'类型的预测记录")
            print("\n  可能原因：")
            print("  1. 还没有进行过'未收盘-明天'预测")
            print("  2. prediction_type 字段值不是 'before_close'")
            return False
        
        print(f"  找到 {len(records)} 条记录\n")
        
        # 3. 统计有预测价格和涨幅的记录
        print("【步骤3】统计预测价格和涨幅的保存情况...")
        
        total_count = len(records)
        has_price_count = sum(1 for r in records if r.get('predicted_close_price') is not None)
        has_change_pct_count = sum(1 for r in records if r.get('predicted_change_pct') is not None)
        has_both_count = sum(1 for r in records if r.get('predicted_close_price') is not None and r.get('predicted_change_pct') is not None)
        
        print(f"  总记录数: {total_count}")
        print(f"  有 predicted_close_price: {has_price_count} ({has_price_count/total_count*100:.1f}%)")
        print(f"  有 predicted_change_pct: {has_change_pct_count} ({has_change_pct_count/total_count*100:.1f}%)")
        print(f"  两者都有: {has_both_count} ({has_both_count/total_count*100:.1f}%)")
        
        # 4. 显示详细记录
        print("\n【步骤4】最近10条记录的详细信息：")
        print("-" * 80)
        print(f"{'股票代码':<10} {'股票名称':<12} {'当前价格':<10} {'预测收盘价':<12} {'预测涨幅':<12} {'预测时间':<20}")
        print("-" * 80)
        
        for i, record in enumerate(records[:10], 1):
            symbol = record.get('symbol', '')
            name = record.get('name', '')[:10]
            current_price = record.get('current_price', 0)
            predicted_price = record.get('predicted_close_price')
            predicted_change = record.get('predicted_change_pct')
            prediction_time = record.get('prediction_time', '')
            
            price_str = f"{predicted_price:.2f}" if predicted_price else "NULL"
            change_str = f"{predicted_change:+.2f}%" if predicted_change is not None else "NULL"
            
            print(f"{symbol:<10} {name:<12} {current_price:<10.2f} {price_str:<12} {change_str:<12} {str(prediction_time):<20}")
        
        print("-" * 80)
        
        # 5. 检查没有预测价格的记录
        missing_records = [r for r in records if r.get('predicted_close_price') is None or r.get('predicted_change_pct') is None]
        if missing_records:
            print(f"\n【步骤5】发现 {len(missing_records)} 条记录缺少预测价格或涨幅：")
            for r in missing_records[:5]:
                print(f"  - {r.get('symbol')} {r.get('name')} (预测时间: {r.get('prediction_time')})")
                print(f"    predicted_close_price: {r.get('predicted_close_price')}")
                print(f"    predicted_change_pct: {r.get('predicted_change_pct')}")
        
        # 6. 总结
        print("\n" + "=" * 80)
        print("检查总结")
        print("=" * 80)
        
        if has_both_count == total_count and total_count > 0:
            print("✅ 所有'未收盘-明天'预测记录都包含了明日预测价格和涨幅！")
            return True
        elif has_both_count > 0:
            print(f"⚠️  部分记录（{has_both_count}/{total_count}）包含了预测价格和涨幅")
            print("   可能原因：")
            print("   1. 旧记录是在添加字段之前保存的")
            print("   2. 预测时计算失败")
            print("   3. 保存时出错")
            return False
        else:
            print("❌ 没有记录包含预测价格和涨幅！")
            print("   可能原因：")
            print("   1. 预测时没有计算这两个值")
            print("   2. 保存时没有正确保存")
            print("   3. 数据库字段不存在（但前面检查已通过）")
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
    check_before_close_predictions()
