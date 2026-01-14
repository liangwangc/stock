#!/usr/bin/env python3
"""
测试日志详情功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'audit_system'))

def test_log_details():
    """测试日志详情功能"""
    try:
        from audit_system.database import DatabaseManager, AuditLogDAO
        
        print("🔧 测试日志详情功能...")
        
        # 初始化数据库管理器
        db_manager = DatabaseManager()
        log_dao = AuditLogDAO(db_manager)
        
        # 测试获取系统日志
        print("\n📋 获取系统日志...")
        logs = log_dao.get_system_logs(limit=5)
        
        if logs:
            print(f"✅ 成功获取 {len(logs)} 条日志记录")
            
            # 测试获取第一条日志的详情
            first_log = logs[0]
            print(f"\n📝 测试获取日志详情 (ID: {first_log['id']})...")
            
            log_detail = log_dao.get_log_by_id(first_log['id'])
            if log_detail:
                print("✅ 成功获取日志详情")
                print(f"   操作类型: {log_detail.get('action', 'N/A')}")
                print(f"   操作用户: {log_detail.get('user_name', 'N/A')}")
                print(f"   操作对象: {log_detail.get('target_type', 'N/A')}")
                print(f"   操作详情: {log_detail.get('details', 'N/A')[:50]}...")
                print(f"   IP地址: {log_detail.get('ip_address', 'N/A')}")
                print(f"   用户代理: {log_detail.get('user_agent', 'N/A')[:50]}...")
            else:
                print("❌ 获取日志详情失败")
        else:
            print("⚠️  没有找到日志记录")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 稽核档案管理系统 - 日志详情功能测试")
    print("=" * 50)
    
    test_log_details()
    
    print("\n" + "=" * 50)
    print("✅ 测试完成")
