-- 添加字段到file_attachments表
ALTER TABLE file_attachments 
ADD COLUMN status ENUM('active', 'deleted') DEFAULT 'active' COMMENT '状态' AFTER description,
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间' AFTER status,
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER created_at; 