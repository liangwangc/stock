# -*- coding: utf-8 -*-
"""
创建默认管理员账户脚本
在数据库中创建admin用户，密码：admin@123
"""
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.user_manager import UserManager
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)

def create_admin_user():
    """创建默认管理员账户"""
    if not USE_DATABASE:
        print("错误：数据库未启用，无法创建用户")
        return False
    
    try:
        um = UserManager()
        
        # 检查admin用户是否已存在
        existing_user = um.get_user_by_username('admin')
        if existing_user:
            print(f"管理员账户已存在（ID: {existing_user.get('id')}）")
            # 更新密码为admin@123
            um.update_user(existing_user['id'], password='admin@123')
            print("已更新管理员密码为：admin@123")
            return True
        
        # 创建新用户
        user_id = um.create_user('admin', 'admin@123', 'admin')
        if user_id:
            print(f"管理员账户创建成功！")
            print(f"  用户名: admin")
            print(f"  密码: admin@123")
            print(f"  角色: admin")
            print(f"  用户ID: {user_id}")
            return True
        else:
            print("创建管理员账户失败")
            return False
            
    except Exception as e:
        logger.error(f"创建管理员账户失败: {str(e)}")
        print(f"错误: {str(e)}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("创建默认管理员账户")
    print("=" * 60)
    success = create_admin_user()
    print("=" * 60)
    sys.exit(0 if success else 1)
