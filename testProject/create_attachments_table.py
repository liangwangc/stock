#!/usr/bin/env python3
"""
创建文件附件表脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'audit_system'))

from audit_system.database import DatabaseManager

def create_attachments_table():
    """创建文件附件表"""
    print("🔧 正在创建文件附件表...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 创建文件附件表
        print("创建文件附件表...")
        create_attachments_table_sql = """
        CREATE TABLE IF NOT EXISTS file_attachments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            file_id INT NOT NULL COMMENT '档案ID',
            filename VARCHAR(255) NOT NULL COMMENT '文件名',
            original_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
            file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
            file_size INT NOT NULL COMMENT '文件大小（字节）',
            file_type VARCHAR(100) COMMENT '文件类型',
            uploaded_by INT NOT NULL COMMENT '上传人ID',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
            description TEXT COMMENT '文件描述',
            FOREIGN KEY (file_id) REFERENCES audit_files(id) ON DELETE CASCADE,
            FOREIGN KEY (uploaded_by) REFERENCES users(id),
            INDEX idx_file_id (file_id),
            INDEX idx_uploaded_by (uploaded_by),
            INDEX idx_file_type (file_type),
            INDEX idx_uploaded_at (uploaded_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='档案附件表'
        """
        db_manager.execute_query(create_attachments_table_sql)
        print("✅ 文件附件表创建成功")
        
        # 验证表创建
        print("\n🔍 验证表创建...")
        try:
            desc_sql = "DESCRIBE file_attachments"
            result = db_manager.execute_query(desc_sql)
            if result:
                print("✅ 文件附件表结构:")
                for row in result:
                    field_name = list(row.values())[0] if row else "unknown"
                    print(f"  {field_name}")
            else:
                print("❌ 没有找到文件附件表")
        except Exception as e:
            print(f"❌ 验证失败: {e}")
        
        print("\n🎉 文件附件表创建完成！")
        return db_manager
        
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 稽核档案管理系统 - 文件附件表创建")
    print("=" * 60)
    
    # 创建表
    db_manager = create_attachments_table()
    if not db_manager:
        print("❌ 表创建失败")
        return
    
    print("\n" + "=" * 60)
    print("🎉 创建完成！")
    print("=" * 60)
    print("现在文件上传功能应该可以正常工作了！")
    print("=" * 60)
    
    # 关闭数据库连接
    db_manager.close()

if __name__ == "__main__":
    main() 