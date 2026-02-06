#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查ML模型激活状态
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection

def check_model_active_status():
    """检查ML模型激活状态"""
    db = DatabaseConnection()
    
    print("=" * 80)
    print("ML模型激活状态检查")
    print("=" * 80)
    
    # 查询所有模型
    sql = """
        SELECT 
            id, 
            model_name, 
            model_type, 
            model_version,
            is_active,
            created_at,
            train_start_date,
            train_end_date,
            sample_count,
            feature_count
        FROM trained_models
        ORDER BY created_at DESC
    """
    
    results = db.execute_query(sql)
    
    if not results:
        print("\n[WARNING] 数据库中没有找到任何ML模型")
        print("\n请先训练模型，参考命令：")
        print("  py scripts/train_base_model.py --train-start 2023-01-01 --train-end 2024-12-31 --models xgb_classifier")
        return
    
    print(f"\n找到 {len(results)} 个模型记录：")
    print("-" * 80)
    
    # 按模型类型分组统计
    model_type_stats = {}
    active_models = []
    inactive_models = []
    
    for r in results:
        model_id = r.get('id')
        model_name = r.get('model_name', 'N/A')
        model_type = r.get('model_type', 'N/A')
        model_version = r.get('model_version', 'N/A')
        is_active = r.get('is_active', 0)
        created_at = r.get('created_at', 'N/A')
        train_start = r.get('train_start_date', 'N/A')
        train_end = r.get('train_end_date', 'N/A')
        sample_count = r.get('sample_count', 0)
        feature_count = r.get('feature_count', 0)
        
        status = "✓ [激活]" if is_active else "  [未激活]"
        
        print(f"{status} ID: {model_id:3d} | 类型: {model_type:20s} | 版本: {model_version:15s}")
        print(f"        名称: {model_name}")
        print(f"        训练数据: {train_start} ~ {train_end} | 样本数: {sample_count:8d} | 特征数: {feature_count:3d}")
        print(f"        创建时间: {created_at}")
        print()
        
        # 统计
        if model_type not in model_type_stats:
            model_type_stats[model_type] = {'total': 0, 'active': 0}
        model_type_stats[model_type]['total'] += 1
        if is_active:
            model_type_stats[model_type]['active'] += 1
            active_models.append({
                'id': model_id,
                'type': model_type,
                'name': model_name,
                'version': model_version
            })
        else:
            inactive_models.append({
                'id': model_id,
                'type': model_type,
                'name': model_name,
                'version': model_version
            })
    
    print("-" * 80)
    
    # 统计信息
    print("\n统计信息：")
    print("-" * 80)
    for model_type, stats in sorted(model_type_stats.items()):
        print(f"  {model_type:20s}: 总计 {stats['total']:2d} 个，激活 {stats['active']:2d} 个")
    
    print("-" * 80)
    
    # 激活状态总结
    if not active_models:
        print("\n[WARNING] ⚠️  没有激活的ML模型！")
        print("\n激活模型的方法：")
        print("  1. Web界面：设置页面 -> 模型学习 -> 已训练模型列表 -> 点击'激活'按钮")
        print("  2. API调用：POST /api/ml/models/{model_id}/activate")
        print("  3. 数据库：UPDATE trained_models SET is_active = 1 WHERE id = ?;")
        print("\n注意：同一类型的模型只能有一个激活的模型")
    else:
        print(f"\n[OK] ✓ 找到 {len(active_models)} 个激活的模型：")
        for model in active_models:
            print(f"  ✓ {model['type']:20s} - {model['name']} (ID: {model['id']}, 版本: {model['version']})")
        
        # 检查是否有重复激活（同一类型多个激活）
        type_count = {}
        for model in active_models:
            model_type = model['type']
            if model_type not in type_count:
                type_count[model_type] = []
            type_count[model_type].append(model)
        
        duplicate_active = {k: v for k, v in type_count.items() if len(v) > 1}
        if duplicate_active:
            print("\n[WARNING] ⚠️  发现同一类型有多个激活的模型（异常情况）：")
            for model_type, models in duplicate_active.items():
                print(f"  {model_type}:")
                for model in models:
                    print(f"    - ID: {model['id']}, 名称: {model['name']}")
        else:
            print("\n[OK] ✓ 激活状态正常（每个类型只有一个激活的模型）")

if __name__ == '__main__':
    check_model_active_status()
