-- 添加notes字段到audit_files表
ALTER TABLE audit_files ADD COLUMN notes TEXT COMMENT '备注信息' AFTER recommendations; 