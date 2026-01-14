-- 手动创建缺失的数据库表
-- 请在MySQL客户端中执行这些命令

-- 1. 创建file_attachments表
CREATE TABLE file_attachments (
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
    INDEX idx_file_id (file_id),
    INDEX idx_uploaded_by (uploaded_by),
    INDEX idx_file_type (file_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='档案附件表';

-- 2. 添加notes字段到audit_files表（如果不存在）
ALTER TABLE audit_files ADD COLUMN notes TEXT COMMENT '备注信息' AFTER recommendations;

-- 3. 检查表是否创建成功
SHOW TABLES LIKE 'file_attachments';

-- 4. 检查audit_files表结构
DESCRIBE audit_files; 