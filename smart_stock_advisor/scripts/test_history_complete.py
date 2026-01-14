"""
完整测试历史预测数据获取流程
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.stock_prediction_db import StockPredictionDB
from utils.db_connection import DatabaseConnection
import json

print("完整测试历史预测数据获取...")
print("="*60)

symbol = "600519"

# 1. 检查数据库中是否有数据
print(f"\n1. 检查数据库中是否有 {symbol} 的预测数据")
db_conn = DatabaseConnection()
sql = "SELECT COUNT(*) as count FROM stock_predictions WHERE symbol = %s"
result = db_conn.execute_query(sql, (symbol,))
count = result[0].get('count', 0) if result else 0
print(f"   数据库中的记录数: {count}")

if count > 0:
    # 2. 检查字段是否存在
    print(f"\n2. 检查关键字段是否存在")
    sql = "SHOW COLUMNS FROM stock_predictions"
    columns = db_conn.execute_query(sql, None)
    column_names = [col.get('Field') for col in columns] if columns else []
    
    key_fields = [
        'predicted_close_price', 'predicted_change_pct',
        'actual_price', 'actual_change_pct', 'actual_direction', 'prediction_hit',
        'prediction_type', 'current_price', 'prediction', 'up_probability', 
        'down_probability', 'confidence', 'final_score'
    ]
    
    for field in key_fields:
        exists = field in column_names
        status = "存在" if exists else "缺失"
        print(f"   {field}: {status}")
    
    # 3. 测试 get_predictions 方法
    print(f"\n3. 测试 StockPredictionDB.get_predictions")
    db = StockPredictionDB()
    predictions = db.get_predictions(symbol=symbol, limit=5, order_by='prediction_time DESC')
    
    if predictions:
        print(f"   获取到 {len(predictions)} 条记录")
        print(f"\n   第一条记录的字段:")
        first = predictions[0]
        for key in sorted(first.keys()):
            value = first.get(key)
            if value is not None:
                print(f"     {key}: {value}")
        
        # 4. 检查API返回格式
        print(f"\n4. 模拟API返回格式")
        record = {
            'id': first.get('id'),
            'symbol': first.get('symbol', symbol),
            'name': first.get('name', ''),
            'prediction_date': str(first.get('prediction_date', '')) if first.get('prediction_date') else '',
            'target_date': str(first.get('target_date', '')) if first.get('target_date') else '',
            'prediction_time': str(first.get('prediction_time', '')) if first.get('prediction_time') else '',
            'current_price': float(first.get('current_price', 0) or 0),
            'predicted_close_price': float(first.get('predicted_close_price', 0)) if first.get('predicted_close_price') else None,
            'predicted_change_pct': float(first.get('predicted_change_pct', 0)) if first.get('predicted_change_pct') is not None else None,
            'prediction': first.get('prediction', '震荡'),
            'up_probability': float(first.get('up_probability', 0) or 0),
            'down_probability': float(first.get('down_probability', 0) or 0),
            'confidence': float(first.get('confidence', 0) or 0),
            'final_score': float(first.get('final_score', 0) or 0),
            'actual_price': float(first.get('actual_price', 0) or 0) if first.get('actual_price') else None,
            'actual_change_pct': float(first.get('actual_change_pct', 0) or 0) if first.get('actual_change_pct') is not None else None,
            'actual_direction': first.get('actual_direction', ''),
            'prediction_hit': first.get('prediction_hit', ''),
        }
        
        print(f"   处理后的记录:")
        for key, value in record.items():
            print(f"     {key}: {value} (type: {type(value).__name__})")
        
        # 5. 检查前端需要的字段
        print(f"\n5. 检查前端显示需要的字段")
        frontend_fields = {
            'prediction_time': record.get('prediction_time'),
            'prediction_date': record.get('prediction_date'),
            'target_date': record.get('target_date'),
            'current_price': record.get('current_price'),
            'predicted_close_price': record.get('predicted_close_price'),
            'predicted_change_pct': record.get('predicted_change_pct'),
            'prediction': record.get('prediction'),
            'up_probability': record.get('up_probability'),
            'down_probability': record.get('down_probability'),
            'confidence': record.get('confidence'),
            'actual_price': record.get('actual_price'),
            'actual_change_pct': record.get('actual_change_pct'),
            'actual_direction': record.get('actual_direction'),
            'prediction_hit': record.get('prediction_hit'),
        }
        
        all_ok = True
        for field, value in frontend_fields.items():
            status = "OK" if value is not None or field in ['actual_price', 'actual_change_pct', 'actual_direction', 'prediction_hit'] else "缺失"
            if status != "OK":
                all_ok = False
            print(f"   {field}: {status} ({value})")
        
        if all_ok:
            print(f"\n结论: 所有字段都正确，数据获取逻辑正常")
        else:
            print(f"\n结论: 部分字段缺失，需要检查")
    else:
        print("   未获取到数据")
else:
    print("   数据库中没有该股票的预测数据")
