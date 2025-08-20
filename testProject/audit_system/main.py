#!/usr/bin/env python3
"""
稽核档案管理系统主程序

提供命令行界面的档案管理系统
"""

import sys
import os
import getpass
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audit_system.database import DatabaseManager
from audit_system.auth import AuthManager, PermissionManager
from audit_system.models import AuditFile, User, FileCategory, Department


class AuditSystemCLI:
    """稽核档案管理系统命令行界面"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.auth_manager = AuthManager(self.db_manager)
        self.permission_manager = PermissionManager(self.auth_manager)
        self.current_user = None
        self.current_token = None
    
    def run(self):
        """运行系统"""
        self.show_welcome()
        
        while True:
            if not self.current_user:
                self.show_login_menu()
            else:
                self.show_main_menu()
    
    def show_welcome(self):
        """显示欢迎信息"""
        print("=" * 60)
        print("🏛️  稽核档案管理系统")
        print("=" * 60)
        print("欢迎使用稽核档案管理系统！")
        print("本系统提供完整的档案管理、用户认证、权限控制等功能")
        print("=" * 60)
    
    def show_login_menu(self):
        """显示登录菜单"""
        print("\n🔐 用户登录")
        print("1. 用户登录")
        print("2. 退出系统")
        
        choice = input("\n请选择操作 (1-2): ").strip()
        
        if choice == "1":
            self.login()
        elif choice == "2":
            print("👋 感谢使用稽核档案管理系统！")
            sys.exit(0)
        else:
            print("❌ 无效选择，请重新输入")
    
    def login(self):
        """用户登录"""
        print("\n" + "=" * 40)
        print("用户登录")
        print("=" * 40)
        
        username = input("用户名: ").strip()
        password = getpass.getpass("密码: ").strip()
        
        if not username or not password:
            print("❌ 用户名和密码不能为空")
            return
        
        # 执行登录
        result = self.auth_manager.login(username, password)
        
        if result["success"]:
            self.current_user = result["user"]
            self.current_token = result["token"]
            print(f"✅ {result['message']}")
            print(f"👤 欢迎，{self.current_user['real_name']} ({self.current_user['role']})")
        else:
            print(f"❌ {result['message']}")
    
    def show_main_menu(self):
        """显示主菜单"""
        print(f"\n🏠 主菜单 - 用户: {self.current_user['real_name']} ({self.current_user['role']})")
        print("=" * 50)
        print("1. 📁 档案管理")
        print("2. 👥 用户管理")
        print("3. 📊 系统统计")
        print("4. 📝 操作日志")
        print("5. ⚙️  系统设置")
        print("6. 🔐 修改密码")
        print("7. 🚪 退出登录")
        print("8. ❌ 退出系统")
        
        choice = input("\n请选择操作 (1-8): ").strip()
        
        if choice == "1":
            self.show_file_management_menu()
        elif choice == "2":
            self.show_user_management_menu()
        elif choice == "3":
            self.show_statistics_menu()
        elif choice == "4":
            self.show_logs_menu()
        elif choice == "5":
            self.show_system_settings_menu()
        elif choice == "6":
            self.change_password()
        elif choice == "7":
            self.logout()
        elif choice == "8":
            print("👋 感谢使用稽核档案管理系统！")
            sys.exit(0)
        else:
            print("❌ 无效选择，请重新输入")
    
    def show_file_management_menu(self):
        """显示档案管理菜单"""
        while True:
            print(f"\n📁 档案管理")
            print("=" * 30)
            print("1. 📋 查看档案列表")
            print("2. ➕ 创建新档案")
            print("3. ✏️  编辑档案")
            print("4. 🔍 搜索档案")
            print("5. 📊 档案统计")
            print("6. ↩️  返回主菜单")
            
            choice = input("\n请选择操作 (1-6): ").strip()
            
            if choice == "1":
                self.list_audit_files()
            elif choice == "2":
                self.create_audit_file()
            elif choice == "3":
                self.edit_audit_file()
            elif choice == "4":
                self.search_audit_files()
            elif choice == "5":
                self.show_file_statistics()
            elif choice == "6":
                break
            else:
                print("❌ 无效选择，请重新输入")
    
    def list_audit_files(self):
        """查看档案列表"""
        print("\n📋 档案列表")
        print("=" * 50)
        
        try:
            from audit_system.database import AuditFileDAO
            file_dao = AuditFileDAO(self.db_manager)
            files = file_dao.get_audit_files(limit=20)
            
            if not files:
                print("📭 暂无档案记录")
                return
            
            print(f"{'ID':<5} {'档案编号':<15} {'标题':<30} {'状态':<10} {'优先级':<8} {'创建时间':<20}")
            print("-" * 100)
            
            for file in files:
                print(f"{file['id']:<5} {file['file_number']:<15} {file['title'][:28]:<30} "
                      f"{file['status']:<10} {file['priority']:<8} {str(file['created_at'])[:19]:<20}")
            
            print(f"\n共显示 {len(files)} 条记录")
            
        except Exception as e:
            print(f"❌ 获取档案列表失败: {e}")
    
    def create_audit_file(self):
        """创建新档案"""
        if not self.permission_manager.can_create_files(self.current_token):
            print("❌ 权限不足，无法创建档案")
            return
        
        print("\n➕ 创建新档案")
        print("=" * 30)
        
        try:
            # 获取档案分类
            from audit_system.database import FileCategoryDAO
            category_dao = FileCategoryDAO(self.db_manager)
            categories = category_dao.get_all_categories()
            
            print("可用的档案分类:")
            for cat in categories:
                print(f"{cat['id']}. {cat['name']}")
            
            # 获取部门
            from audit_system.database import DepartmentDAO
            dept_dao = DepartmentDAO(self.db_manager)
            departments = dept_dao.get_all_departments()
            
            print("\n可用的部门:")
            for dept in departments:
                print(f"{dept['id']}. {dept['name']}")
            
            # 输入档案信息
            file_number = input("\n档案编号: ").strip()
            title = input("档案标题: ").strip()
            category_id = input("档案分类ID: ").strip()
            department_id = input("所属部门ID: ").strip()
            description = input("档案描述: ").strip()
            priority = input("优先级 (low/medium/high/urgent): ").strip() or "medium"
            audit_date = input("稽核日期 (YYYY-MM-DD): ").strip()
            
            if not all([file_number, title, category_id, department_id]):
                print("❌ 档案编号、标题、分类、部门为必填项")
                return
            
            # 创建档案
            from audit_system.database import AuditFileDAO
            file_dao = AuditFileDAO(self.db_manager)
            
            file_id = file_dao.create_audit_file(
                file_number=file_number,
                title=title,
                category_id=int(category_id),
                department_id=int(department_id),
                auditor_id=self.current_user['id'],
                description=description,
                priority=priority,
                audit_date=audit_date if audit_date else None
            )
            
            print(f"✅ 档案创建成功！档案ID: {file_id}")
            
        except Exception as e:
            print(f"❌ 创建档案失败: {e}")
    
    def edit_audit_file(self):
        """编辑档案"""
        print("\n✏️  编辑档案")
        print("=" * 30)
        
        file_id = input("请输入要编辑的档案ID: ").strip()
        if not file_id:
            print("❌ 档案ID不能为空")
            return
        
        try:
            from audit_system.database import AuditFileDAO
            file_dao = AuditFileDAO(self.db_manager)
            
            file_info = file_dao.get_audit_file_by_id(int(file_id))
            if not file_info:
                print("❌ 档案不存在")
                return
            
            # 检查权限
            if not self.permission_manager.can_edit_files(self.current_token, file_info['created_by']):
                print("❌ 权限不足，无法编辑此档案")
                return
            
            print(f"\n当前档案信息:")
            print(f"标题: {file_info['title']}")
            print(f"状态: {file_info['status']}")
            print(f"描述: {file_info['description']}")
            
            # 输入更新信息
            new_title = input("\n新标题 (回车保持不变): ").strip()
            new_description = input("新描述 (回车保持不变): ").strip()
            new_status = input("新状态 (pending/in_progress/completed/archived): ").strip()
            new_findings = input("稽核发现: ").strip()
            new_recommendations = input("建议措施: ").strip()
            
            # 构建更新数据
            update_data = {}
            if new_title:
                update_data['title'] = new_title
            if new_description:
                update_data['description'] = new_description
            if new_status:
                update_data['status'] = new_status
            if new_findings:
                update_data['findings'] = new_findings
            if new_recommendations:
                update_data['recommendations'] = new_recommendations
            
            if update_data:
                success = file_dao.update_audit_file(int(file_id), **update_data)
                if success:
                    print("✅ 档案更新成功")
                else:
                    print("❌ 档案更新失败")
            else:
                print("ℹ️  未输入任何更新内容")
                
        except Exception as e:
            print(f"❌ 编辑档案失败: {e}")
    
    def search_audit_files(self):
        """搜索档案"""
        print("\n🔍 搜索档案")
        print("=" * 30)
        
        keyword = input("请输入搜索关键词: ").strip()
        if not keyword:
            print("❌ 搜索关键词不能为空")
            return
        
        try:
            # 这里可以实现更复杂的搜索逻辑
            print(f"🔍 搜索关键词: {keyword}")
            print("ℹ️  搜索功能正在开发中...")
            
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
    
    def show_file_statistics(self):
        """显示档案统计"""
        print("\n📊 档案统计")
        print("=" * 30)
        
        try:
            # 统计各状态档案数量
            query = """
            SELECT status, COUNT(*) as count 
            FROM audit_files 
            GROUP BY status
            """
            status_stats = self.db_manager.execute_query(query)
            
            print("档案状态统计:")
            for stat in status_stats:
                print(f"  {stat['status']}: {stat['count']} 个")
            
            # 统计各分类档案数量
            query = """
            SELECT fc.name, COUNT(*) as count 
            FROM audit_files af
            LEFT JOIN file_categories fc ON af.category_id = fc.id
            GROUP BY af.category_id
            """
            category_stats = self.db_manager.execute_query(query)
            
            print("\n档案分类统计:")
            for stat in category_stats:
                print(f"  {stat['name']}: {stat['count']} 个")
                
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
    
    def show_user_management_menu(self):
        """显示用户管理菜单"""
        if not self.permission_manager.can_manage_users(self.current_token):
            print("❌ 权限不足，无法访问用户管理")
            return
        
        while True:
            print(f"\n👥 用户管理")
            print("=" * 30)
            print("1. 📋 查看用户列表")
            print("2. ➕ 创建新用户")
            print("3. ✏️  编辑用户")
            print("4. 🔒 锁定/解锁用户")
            print("5. ↩️  返回主菜单")
            
            choice = input("\n请选择操作 (1-5): ").strip()
            
            if choice == "1":
                self.list_users()
            elif choice == "2":
                self.create_user()
            elif choice == "3":
                print("ℹ️  编辑用户功能正在开发中...")
            elif choice == "4":
                print("ℹ️  锁定/解锁用户功能正在开发中...")
            elif choice == "5":
                break
            else:
                print("❌ 无效选择，请重新输入")
    
    def list_users(self):
        """查看用户列表"""
        print("\n📋 用户列表")
        print("=" * 50)
        
        try:
            from audit_system.database import UserDAO
            user_dao = UserDAO(self.db_manager)
            users = user_dao.get_all_users()
            
            if not users:
                print("📭 暂无用户记录")
                return
            
            print(f"{'ID':<5} {'用户名':<15} {'真实姓名':<15} {'角色':<10} {'状态':<10} {'部门':<15}")
            print("-" * 80)
            
            for user in users:
                print(f"{user['id']:<5} {user['username']:<15} {user['real_name']:<15} "
                      f"{user['role']:<10} {user['status']:<10} {user['department']:<15}")
            
            print(f"\n共显示 {len(users)} 条记录")
            
        except Exception as e:
            print(f"❌ 获取用户列表失败: {e}")
    
    def create_user(self):
        """创建新用户"""
        print("\n➕ 创建新用户")
        print("=" * 30)
        
        username = input("用户名: ").strip()
        password = getpass.getpass("密码: ").strip()
        real_name = input("真实姓名: ").strip()
        email = input("邮箱: ").strip()
        phone = input("电话: ").strip()
        department = input("部门: ").strip()
        role = input("角色 (admin/user/auditor): ").strip() or "user"
        
        if not all([username, password, real_name, email]):
            print("❌ 用户名、密码、真实姓名、邮箱为必填项")
            return
        
        result = self.auth_manager.create_user(
            username=username,
            password=password,
            real_name=real_name,
            email=email,
            phone=phone,
            department=department,
            role=role,
            creator_id=self.current_user['id']
        )
        
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    
    def show_statistics_menu(self):
        """显示统计菜单"""
        print("\n📊 系统统计")
        print("=" * 30)
        print("1. 📁 档案统计")
        print("2. 👥 用户统计")
        print("3. 📈 趋势分析")
        print("4. ↩️  返回主菜单")
        
        choice = input("\n请选择操作 (1-4): ").strip()
        
        if choice == "1":
            self.show_file_statistics()
        elif choice == "2":
            self.show_user_statistics()
        elif choice == "3":
            print("ℹ️  趋势分析功能正在开发中...")
        elif choice == "4":
            return
        else:
            print("❌ 无效选择，请重新输入")
    
    def show_user_statistics(self):
        """显示用户统计"""
        print("\n👥 用户统计")
        print("=" * 30)
        
        try:
            # 统计各角色用户数量
            query = """
            SELECT role, COUNT(*) as count 
            FROM users 
            GROUP BY role
            """
            role_stats = self.db_manager.execute_query(query)
            
            print("用户角色统计:")
            for stat in role_stats:
                print(f"  {stat['role']}: {stat['count']} 人")
            
            # 统计各状态用户数量
            query = """
            SELECT status, COUNT(*) as count 
            FROM users 
            GROUP BY status
            """
            status_stats = self.db_manager.execute_query(query)
            
            print("\n用户状态统计:")
            for stat in status_stats:
                print(f"  {stat['status']}: {stat['count']} 人")
                
        except Exception as e:
            print(f"❌ 获取用户统计失败: {e}")
    
    def show_logs_menu(self):
        """显示日志菜单"""
        if not self.permission_manager.can_view_logs(self.current_token):
            print("❌ 权限不足，无法查看日志")
            return
        
        print("\n📝 操作日志")
        print("=" * 30)
        print("1. 📋 查看系统日志")
        print("2. 👤 查看用户日志")
        print("3. 🔍 搜索日志")
        print("4. ↩️  返回主菜单")
        
        choice = input("\n请选择操作 (1-4): ").strip()
        
        if choice == "1":
            self.show_system_logs()
        elif choice == "2":
            self.show_user_logs()
        elif choice == "3":
            print("ℹ️  日志搜索功能正在开发中...")
        elif choice == "4":
            return
        else:
            print("❌ 无效选择，请重新输入")
    
    def show_system_logs(self):
        """显示系统日志"""
        print("\n📋 系统操作日志")
        print("=" * 60)
        
        try:
            from audit_system.database import AuditLogDAO
            log_dao = AuditLogDAO(self.db_manager)
            logs = log_dao.get_system_logs(limit=20)
            
            if not logs:
                print("📭 暂无日志记录")
                return
            
            print(f"{'时间':<20} {'用户':<15} {'操作':<15} {'对象':<15} {'详情':<30}")
            print("-" * 100)
            
            for log in logs:
                print(f"{str(log['created_at'])[:19]:<20} {log['username']:<15} {log['action']:<15} "
                      f"{log['target_type']:<15} {log['details'][:28]:<30}")
            
            print(f"\n共显示 {len(logs)} 条记录")
            
        except Exception as e:
            print(f"❌ 获取系统日志失败: {e}")
    
    def show_user_logs(self):
        """显示用户日志"""
        print("\n📋 用户操作日志")
        print("=" * 60)
        
        try:
            from audit_system.database import AuditLogDAO
            log_dao = AuditLogDAO(self.db_manager)
            logs = log_dao.get_user_logs(self.current_user['id'], limit=20)
            
            if not logs:
                print("📭 暂无日志记录")
                return
            
            print(f"{'时间':<20} {'操作':<15} {'对象':<15} {'详情':<30}")
            print("-" * 80)
            
            for log in logs:
                print(f"{str(log['created_at'])[:19]:<20} {log['action']:<15} "
                      f"{log['target_type']:<15} {log['details'][:28]:<30}")
            
            print(f"\n共显示 {len(logs)} 条记录")
            
        except Exception as e:
            print(f"❌ 获取用户日志失败: {e}")
    
    def show_system_settings_menu(self):
        """显示系统设置菜单"""
        if not self.permission_manager.can_manage_system(self.current_token):
            print("❌ 权限不足，无法访问系统设置")
            return
        
        print("\n⚙️  系统设置")
        print("=" * 30)
        print("1. 🔧 数据库配置")
        print("2. 📧 邮件配置")
        print("3. 🔐 安全设置")
        print("4. 📊 备份设置")
        print("5. ↩️  返回主菜单")
        
        choice = input("\n请选择操作 (1-5): ").strip()
        
        if choice == "1":
            print("ℹ️  数据库配置功能正在开发中...")
        elif choice == "2":
            print("ℹ️  邮件配置功能正在开发中...")
        elif choice == "3":
            print("ℹ️  安全设置功能正在开发中...")
        elif choice == "4":
            print("ℹ️  备份设置功能正在开发中...")
        elif choice == "5":
            return
        else:
            print("❌ 无效选择，请重新输入")
    
    def change_password(self):
        """修改密码"""
        print("\n🔐 修改密码")
        print("=" * 30)
        
        old_password = getpass.getpass("当前密码: ").strip()
        new_password = getpass.getpass("新密码: ").strip()
        confirm_password = getpass.getpass("确认新密码: ").strip()
        
        if not all([old_password, new_password, confirm_password]):
            print("❌ 所有密码字段都不能为空")
            return
        
        if new_password != confirm_password:
            print("❌ 新密码与确认密码不匹配")
            return
        
        if len(new_password) < 6:
            print("❌ 新密码长度不能少于6位")
            return
        
        result = self.auth_manager.change_password(
            self.current_user['id'], old_password, new_password
        )
        
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    
    def logout(self):
        """退出登录"""
        if self.current_token:
            self.auth_manager.logout(self.current_token)
        
        self.current_user = None
        self.current_token = None
        print("✅ 已退出登录")


def main():
    """主函数"""
    try:
        system = AuditSystemCLI()
        system.run()
    except KeyboardInterrupt:
        print("\n\n👋 系统被用户中断，正在退出...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 系统运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 