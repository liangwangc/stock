#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试登录历史记录功能
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.login_history import LoginHistoryManager

# 测试记录登录历史
login_history = LoginHistoryManager()

# 测试解析User-Agent
test_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
ua_info = login_history.parse_user_agent(test_ua)
print("User-Agent解析结果：")
print(f"  设备类型: {ua_info['device_type']}")
print(f"  浏览器: {ua_info['browser']}")
print(f"  操作系统: {ua_info['os']}")

# 测试记录登录（成功）
print("\n测试记录登录历史（成功）...")
success = login_history.record_login(
    username='test_user',
    login_status='success',
    user_id=1,
    ip_address='192.168.1.100',
    user_agent=test_ua,
    session_id='test_session_123'
)
print(f"记录结果: {'成功' if success else '失败'}")

# 测试记录登录（失败）
print("\n测试记录登录历史（失败）...")
success = login_history.record_login(
    username='test_user',
    login_status='failed',
    user_id=None,
    failure_reason='密码错误',
    ip_address='192.168.1.100',
    user_agent=test_ua
)
print(f"记录结果: {'成功' if success else '失败'}")

# 测试查询登录历史
print("\n测试查询登录历史...")
history = login_history.get_login_history(username='test_user', limit=10)
print(f"查询结果: 找到 {len(history)} 条记录")
if history:
    print("\n最近5条记录：")
    for i, record in enumerate(history[:5], 1):
        print(f"  {i}. {record.get('username')} - {record.get('login_status')} - {record.get('login_time')} - {record.get('ip_address')}")
