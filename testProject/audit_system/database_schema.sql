-- 稽核档案管理系统数据库表结构

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    real_name VARCHAR(100) NOT NULL COMMENT '真实姓名',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '电话',
    department VARCHAR(100) COMMENT '部门',
    role ENUM('admin', 'user', 'auditor') DEFAULT 'user' COMMENT '角色',
    status ENUM('active', 'inactive', 'locked') DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    last_login TIMESTAMP NULL COMMENT '最后登录时间',
    login_attempts INT DEFAULT 0 COMMENT '登录尝试次数',
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 部门表
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '部门名称',
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '部门代码',
    parent_id INT NULL COMMENT '父部门ID',
    manager VARCHAR(100) COMMENT '部门负责人',
    description TEXT COMMENT '部门描述',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (parent_id) REFERENCES departments(id) ON DELETE SET NULL,
    INDEX idx_code (code),
    INDEX idx_parent_id (parent_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门表';

-- 档案分类表
CREATE TABLE IF NOT EXISTS file_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '分类名称',
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '分类代码',
    parent_id INT NULL COMMENT '父分类ID',
    description TEXT COMMENT '分类描述',
    sort_order INT DEFAULT 0 COMMENT '排序',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (parent_id) REFERENCES file_categories(id) ON DELETE SET NULL,
    INDEX idx_code (code),
    INDEX idx_parent_id (parent_id),
    INDEX idx_sort_order (sort_order),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='档案分类表';

-- 稽核档案表
CREATE TABLE IF NOT EXISTS audit_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_number VARCHAR(50) UNIQUE NOT NULL COMMENT '档案编号',
    title VARCHAR(200) NOT NULL COMMENT '档案标题',
    category_id INT NOT NULL COMMENT '档案分类ID',
    department_id INT NOT NULL COMMENT '所属部门ID',
    auditor_id INT NOT NULL COMMENT '稽核人员ID',
    audit_date DATE COMMENT '稽核日期',
    status ENUM('pending', 'in_progress', 'completed', 'archived') DEFAULT 'pending' COMMENT '状态',
    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium' COMMENT '优先级',
    description TEXT COMMENT '档案描述',
    findings TEXT COMMENT '稽核发现',
    recommendations TEXT COMMENT '建议措施',
    notes TEXT COMMENT '备注信息',
    created_by INT NOT NULL COMMENT '创建人ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    FOREIGN KEY (category_id) REFERENCES file_categories(id),
    FOREIGN KEY (department_id) REFERENCES departments(id),
    FOREIGN KEY (auditor_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_file_number (file_number),
    INDEX idx_category_id (category_id),
    INDEX idx_department_id (department_id),
    INDEX idx_auditor_id (auditor_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_audit_date (audit_date),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='稽核档案表';

-- 档案附件表
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

-- 稽核日志表
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

-- 通知表
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

-- 系统设置表
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

-- 插入默认数据
INSERT IGNORE INTO departments (name, code, description) VALUES 
('稽核部', 'AUDIT', '负责内部稽核工作'),
('财务部', 'FINANCE', '负责财务管理'),
('人事部', 'HR', '负责人力资源管理'),
('技术部', 'TECH', '负责技术开发'),
('运营部', 'OPERATIONS', '负责日常运营');

INSERT IGNORE INTO file_categories (name, code, description, sort_order) VALUES 
('财务稽核', 'FINANCE_AUDIT', '财务相关稽核档案', 1),
('运营稽核', 'OPERATIONS_AUDIT', '运营相关稽核档案', 2),
('合规稽核', 'COMPLIANCE_AUDIT', '合规相关稽核档案', 3),
('IT稽核', 'IT_AUDIT', 'IT系统稽核档案', 4),
('人事稽核', 'HR_AUDIT', '人事相关稽核档案', 5);

-- 插入默认管理员用户 (密码: admin123)
INSERT IGNORE INTO users (username, password_hash, real_name, email, role, department) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iKGi', '系统管理员', 'admin@example.com', 'admin', '稽核部'); 