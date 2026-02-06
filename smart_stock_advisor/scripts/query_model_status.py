#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import sys
import os
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection

db = DatabaseConnection()

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

print("=" * 80)
print("ML模型激活状态")
print("=" * 80)

if not results:
    print("\n数据库中没有找到任何ML模型")
else:
    print(f"\n找到 {len(results)} 个模型：\n")
    
    active_models = []
    for r in results:
        model_id = r.get('id')
        model_name = r.get('model_name', 'N/A')
        model_type = r.get('model_type', 'N/A')
        model_version = r.get('model_version', 'N/A')
        is_active = r.get('is_active', 0)
        created_at = r.get('created_at', 'N/A')
        
        status = "[激活]" if is_active else "[未激活]"
        print(f"{status} ID: {model_id}, 类型: {model_type}, 名称: {model_name}, 版本: {model_version}, 创建时间: {created_at}")
        
        if is_active:
            active_models.append({
                'id': model_id,
                'type': model_type,
                'name': model_name,
                'version': model_version
            })
    
    print("\n" + "-" * 80)
    
    if not active_models:
        print("\n警告: 没有激活的ML模型！")
    else:
        print(f"\n激活的模型 ({len(active_models)} 个):")
        for model in active_models:
            print(f"  - {model['type']}: {model['name']} (ID: {model['id']}, 版本: {model['version']})")
