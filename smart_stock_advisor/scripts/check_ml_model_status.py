#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查ML模型状态脚本
用于验证是否有激活的ML模型
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)

def check_ml_model_status():
    """检查ML模型状态"""
    db = DatabaseConnection()
    
    print("=" * 60)
    print("检查ML模型状态")
    print("=" * 60)
    
    # 查询所有模型
    sql = """
        SELECT id, model_name, model_type, is_active, created_at
        FROM trained_models
        ORDER BY created_at DESC
        LIMIT 20
    """
    
    results = db.execute_query(sql)
    
    if not results:
        print("\n[WARNING] 数据库中没有找到任何ML模型")
        print("请先训练模型：")
        print("  py scripts/train_base_model.py --train-start 2023-01-01 --train-end 2024-12-31 --models xgb_classifier")
        return
    
    print(f"\n找到 {len(results)} 个模型记录：")
    print("-" * 60)
    
    active_models = []
    for r in results:
        model_id = r.get('id')
        model_name = r.get('model_name', 'N/A')
        model_type = r.get('model_type', 'N/A')
        is_active = r.get('is_active', 0)
        created_at = r.get('created_at', 'N/A')
        
        status = "[激活]" if is_active else "[未激活]"
        print(f"{status} ID: {model_id}, 类型: {model_type}, 名称: {model_name}, 创建时间: {created_at}")
        
        if is_active:
            active_models.append((model_id, model_type, model_name))
    
    print("-" * 60)
    
    if not active_models:
        print("\n[WARNING] 没有激活的ML模型！")
        print("请激活一个模型：")
        print("  1. 在Web界面：设置页面 -> 模型训练 -> 已训练模型列表 -> 点击'激活'按钮")
        print("  2. 或通过API：POST /api/ml/models/{model_id}/activate")
        return
    
    print(f"\n[OK] 找到 {len(active_models)} 个激活的模型：")
    for model_id, model_type, model_name in active_models:
        print(f"  - {model_type}: {model_name} (ID: {model_id})")
    
    # 测试ML模型集成
    print("\n" + "=" * 60)
    print("测试ML模型集成")
    print("=" * 60)
    
    try:
        from utils.ml_predictor_integration import MLPredictorIntegration
        from utils.ml_model_performance_monitor import get_performance_monitor
        
        ml_integration = MLPredictorIntegration()
        performance_monitor = get_performance_monitor()
        
        print("[OK] ML模型集成模块加载成功")
        
        # 测试获取模型ID
        for model_id, model_type, model_name in active_models:
            print(f"\n测试模型: {model_type} (ID: {model_id})")
            
            # 测试获取权重
            weight = performance_monitor.get_optimal_weight(model_id=model_id)
            print(f"  动态权重: {weight:.2%}")
            
            # 测试加载模型
            try:
                from utils.ml_model_manager import MLModelManager
                model_manager = MLModelManager()
                model_info = model_manager.get_model_info(model_type)
                if model_info:
                    print(f"  [OK] 模型信息获取成功")
                    print(f"  模型文件: {model_info.get('model_file_path', 'N/A')}")
                else:
                    print(f"  [WARNING] 无法获取模型信息")
            except Exception as e:
                print(f"  [ERROR] 加载模型信息失败: {str(e)}")
        
    except Exception as e:
        print(f"[ERROR] ML模型集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_ml_model_status()
