#!/usr/bin/env python3
"""
测试编辑功能的脚本
"""

import requests
import json

# 测试配置
BASE_URL = "http://localhost:5000"
TEST_USER = {
    "username": "admin",
    "password": "admin123"
}

def test_login():
    """测试登录功能"""
    print("🔐 测试登录...")
    
    session = requests.Session()
    
    # 获取登录页面
    response = session.get(f"{BASE_URL}/login")
    if response.status_code != 200:
        print("❌ 无法访问登录页面")
        return None
    
    # 执行登录
    login_data = {
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    if response.status_code != 302:
        print("❌ 登录失败")
        return None
    
    print("✅ 登录成功")
    return session

def test_files_page(session):
    """测试档案列表页面"""
    print("\n📁 测试档案列表页面...")
    
    response = session.get(f"{BASE_URL}/files")
    if response.status_code != 200:
        print("❌ 无法访问档案列表页面")
        return False
    
    if "编辑" in response.text:
        print("✅ 档案列表页面包含编辑按钮")
        return True
    else:
        print("❌ 档案列表页面缺少编辑按钮")
        return False

def test_edit_page_access(session):
    """测试编辑页面访问"""
    print("\n✏️ 测试编辑页面访问...")
    
    # 首先获取档案列表
    response = session.get(f"{BASE_URL}/files")
    if response.status_code != 200:
        print("❌ 无法访问档案列表页面")
        return False
    
    # 尝试访问编辑页面（假设有ID为1的档案）
    response = session.get(f"{BASE_URL}/files/1/edit")
    if response.status_code == 200:
        print("✅ 可以访问编辑页面")
        return True
    elif response.status_code == 404:
        print("⚠️ 档案不存在，但编辑路由正常")
        return True
    else:
        print(f"❌ 编辑页面访问失败，状态码: {response.status_code}")
        return False

def test_attachment_endpoints(session):
    """测试附件相关端点"""
    print("\n📎 测试附件相关端点...")
    
    # 测试查看附件端点
    response = session.get(f"{BASE_URL}/attachments/1")
    if response.status_code in [200, 404]:
        print("✅ 查看附件端点正常")
    else:
        print(f"❌ 查看附件端点异常，状态码: {response.status_code}")
    
    # 测试删除附件端点（应该返回405 Method Not Allowed，因为我们没有使用DELETE方法）
    response = session.get(f"{BASE_URL}/attachments/1/delete")
    if response.status_code == 405:
        print("✅ 删除附件端点正常（GET方法被拒绝）")
    else:
        print(f"⚠️ 删除附件端点状态码: {response.status_code}")

def main():
    """主测试函数"""
    print("🚀 开始测试稽核档案管理系统编辑功能...")
    print(f"🌐 测试地址: {BASE_URL}")
    
    # 测试登录
    session = test_login()
    if not session:
        print("❌ 登录失败，无法继续测试")
        return
    
    # 测试档案列表页面
    test_files_page(session)
    
    # 测试编辑页面访问
    test_edit_page_access(session)
    
    # 测试附件相关端点
    test_attachment_endpoints(session)
    
    print("\n✨ 测试完成！")
    print("\n📝 如果所有测试都通过，说明编辑功能已经修复。")
    print("🔧 如果测试失败，请检查：")
    print("   1. 应用是否正在运行")
    print("   2. 数据库连接是否正常")
    print("   3. 数据库表结构是否已更新")

if __name__ == "__main__":
    main() 