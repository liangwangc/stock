"""
测试历史预测API数据获取
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.stock_prediction_db import StockPredictionDB
import json

print("测试历史预测数据获取...")
print("="*60)

symbol = "600519"

print(f"\n1. 测试 StockPredictionDB.get_predictions")
db = StockPredictionDB()
predictions = db.get_predictions(symbol=symbol, limit=10, order_by='prediction_time DESC')

if predictions:
    print(f"获取到 {len(predictions)} 条记录")
    print(f"\n第一条记录的字段:")
    first = predictions[0]
    for key in sorted(first.keys()):
        value = first.get(key)
        if value is not None:
            print(f"  {key}: {value} (type: {type(value).__name__})")
    
    print(f"\n检查关键字段:")
    key_fields = [
        'predicted_close_price', 'predicted_change_pct',
        'actual_price', 'actual_change_pct', 'actual_direction', 'prediction_hit',
        'prediction_type', 'current_price', 'prediction', 'up_probability', 
        'down_probability', 'confidence', 'final_score'
    ]
    for field in key_fields:
        value = first.get(field)
        status = "存在" if value is not None else "缺失"
        print(f"  {field}: {status} ({value})")
else:
    print("未获取到数据")

print(f"\n2. 测试数据格式")
if predictions and len(predictions) > 0:
    sample = predictions[0]
    print(f"prediction_date: {sample.get('prediction_date')} (type: {type(sample.get('prediction_date')).__name__})")
    print(f"target_date: {sample.get('target_date')} (type: {type(sample.get('target_date')).__name__})")
    print(f"prediction_time: {sample.get('prediction_time')} (type: {type(sample.get('prediction_time')).__name__})")
    print(f"current_price: {sample.get('current_price')} (type: {type(sample.get('current_price')).__name__})")
    print(f"predicted_close_price: {sample.get('predicted_close_price')} (type: {type(sample.get('predicted_close_price')).__name__})")
    print(f"predicted_change_pct: {sample.get('predicted_change_pct')} (type: {type(sample.get('predicted_change_pct')).__name__})")
