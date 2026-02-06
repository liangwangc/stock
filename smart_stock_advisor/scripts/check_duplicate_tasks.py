#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查重复的定时任务
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from utils.db_connection import DatabaseConnection
    from collections import defaultdict
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)

def check_duplicate_tasks():
    """检查重复的定时任务"""
    db = DatabaseConnection()
    
    # 查询所有启用的任务
    sql = """
        SELECT id, task_name, task_type, schedule_type, schedule_time, 
               schedule_weekdays, task_config, is_active, created_at
        FROM scheduled_tasks
        WHERE is_active = 1
        ORDER BY task_type, schedule_type, schedule_time
    """
    
    tasks = db.execute_query(sql)
    
    if not tasks:
        print("未找到启用的定时任务")
        return
    
    print("=" * 100)
    print(f"找到 {len(tasks)} 个启用的定时任务")
    print("=" * 100)
    print()
    
    # 按任务类型和调度类型分组，找出重复的任务
    task_groups = defaultdict(list)
    
    for task in tasks:
        # 创建分组键：任务类型 + 调度类型 + 调度时间
        key = (
            task.get('task_type', ''),
            task.get('schedule_type', ''),
            task.get('schedule_time', ''),
            task.get('schedule_weekdays', '')
        )
        task_groups[key].append(task)
    
    # 找出重复的任务组
    duplicate_groups = {k: v for k, v in task_groups.items() if len(v) > 1}
    
    if duplicate_groups:
        print("⚠️  发现重复的定时任务：")
        print("=" * 100)
        print()
        
        for key, group_tasks in duplicate_groups.items():
            task_type, schedule_type, schedule_time, schedule_weekdays = key
            print(f"【重复任务组】")
            print(f"  任务类型: {task_type}")
            print(f"  调度类型: {schedule_type}")
            print(f"  调度时间: {schedule_time}")
            print(f"  调度星期: {schedule_weekdays}")
            print(f"  重复数量: {len(group_tasks)} 个")
            print()
            
            for task in group_tasks:
                print(f"  - ID: {task.get('id')}")
                print(f"    任务名称: {task.get('task_name')}")
                print(f"    创建时间: {task.get('created_at')}")
                print(f"    任务配置: {task.get('task_config', '{}')}")
                print()
            
            print("-" * 100)
            print()
    else:
        print("✅ 未发现重复的定时任务")
        print()
    
    # 显示所有任务的详细信息
    print("=" * 100)
    print("所有启用的定时任务列表：")
    print("=" * 100)
    print()
    
    for task in tasks:
        print(f"ID: {task.get('id')}")
        print(f"  任务名称: {task.get('task_name')}")
        print(f"  任务类型: {task.get('task_type')}")
        print(f"  调度类型: {task.get('schedule_type')}")
        print(f"  调度时间: {task.get('schedule_time')}")
        print(f"  调度星期: {task.get('schedule_weekdays')}")
        print(f"  创建时间: {task.get('created_at')}")
        print()
    
    # 提供清理建议
    if duplicate_groups:
        print("=" * 100)
        print("清理建议：")
        print("=" * 100)
        print()
        print("可以通过以下SQL语句禁用重复的任务（保留ID最小的任务）：")
        print()
        
        for key, group_tasks in duplicate_groups.items():
            task_type, schedule_type, schedule_time, schedule_weekdays = key
            task_ids = [str(t.get('id')) for t in group_tasks]
            keep_id = min(task_ids, key=int)  # 保留ID最小的
            disable_ids = [tid for tid in task_ids if tid != keep_id]
            
            print(f"-- 任务类型: {task_type}, 调度时间: {schedule_time}")
            print(f"-- 保留任务 ID: {keep_id}")
            print(f"-- 禁用任务 ID: {', '.join(disable_ids)}")
            print(f"UPDATE scheduled_tasks SET is_active = 0 WHERE id IN ({', '.join(disable_ids)});")
            print()

if __name__ == '__main__':
    check_duplicate_tasks()
