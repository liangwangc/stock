-- 稽核档案管理系统数据库修复脚本
-- 执行此脚本前请确保已备份数据库

-- 1. 添加notes字段到audit_files表
ALTER TABLE audit_files ADD COLUMN IF NOT EXISTS notes TEXT COMMENT '备注信息' AFTER recommendations;

-- 2. 创建file_attachments表（如果不存在）
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
    status ENUM('active', 'deleted') DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (file_id) REFERENCES audit_files(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id),
    INDEX idx_file_id (file_id),
    INDEX idx_uploaded_by (uploaded_by),
    INDEX idx_file_type (file_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='档案附件表';

-- 3. 创建audit_logs表（如果不存在）
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '操作用户ID',
    action VARCHAR(100) NOT NULL COMMENT '操作类型',
    target_type VARCHAR(100) NOT NULL COMMENT '操作对象类型',
    target_id INT NOT NULL COMMENT '操作对象ID',
    details TEXT COMMENT '操作详情',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_target_type (target_type),
    INDEX idx_target_id (target_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='稽核日志表';

-- 4. 创建notifications表（如果不存在）
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '接收用户ID',
    title VARCHAR(200) NOT NULL COMMENT '通知标题',
    content TEXT COMMENT '通知内容',
    type ENUM('info', 'warning', 'error', 'success') DEFAULT 'info' COMMENT '通知类型',
    is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读',
    related_type VARCHAR(100) COMMENT '相关对象类型',
    related_id INT COMMENT '相关对象ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    read_at TIMESTAMP NULL COMMENT '阅读时间',
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_type (type),
    INDEX idx_is_read (is_read),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知表';

-- 5. 创建system_settings表（如果不存在）
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) UNIQUE NOT NULL COMMENT '设置键',
    value TEXT COMMENT '设置值',
    description TEXT COMMENT '设置描述',
    category VARCHAR(100) COMMENT '设置分类',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开',
    updated_by INT COMMENT '更新人ID',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (updated_by) REFERENCES users(id),
    INDEX idx_key (`key`),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统设置表';

-- 6. 插入默认部门数据（如果不存在）
INSERT IGNORE INTO departments (name, code, description) VALUES 
('稽核部', 'AUDIT', '负责内部稽核工作'),
('财务部', 'FINANCE', '负责财务管理'),
('人事部', 'HR', '负责人力资源管理'),
('技术部', 'TECH', '负责技术开发'),
('运营部', 'OPERATIONS', '负责日常运营');

-- 7. 插入默认档案分类数据（如果不存在）
INSERT IGNORE INTO file_categories (name, code, description, sort_order) VALUES 
('财务稽核', 'FINANCE_AUDIT', '财务相关稽核档案', 1),
('运营稽核', 'OPERATIONS_AUDIT', '运营相关稽核档案', 2),
('合规稽核', 'COMPLIANCE_AUDIT', '合规相关稽核档案', 3),
('IT稽核', 'IT_AUDIT', 'IT系统稽核档案', 4),
('人事稽核', 'HR_AUDIT', '人事相关稽核档案', 5);

-- 8. 插入默认管理员用户（如果不存在）
INSERT IGNORE INTO users (username, password_hash, real_name, email, role, department) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iKGi', '系统管理员', 'admin@example.com', 'admin', '稽核部');

-- 9. 检查表是否创建成功
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    TABLE_COMMENT
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'nanan_data' 
AND TABLE_NAME IN ('audit_files', 'file_attachments', 'audit_logs', 'notifications', 'system_settings')
ORDER BY TABLE_NAME; 