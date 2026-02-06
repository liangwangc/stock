-- 数据库升级脚本：添加登录、权限和日志功能
-- 执行此脚本以升级数据库结构

USE word_app;

-- 1. 修改users表，添加密码和角色字段
ALTER TABLE users 
ADD COLUMN password VARCHAR(255) DEFAULT NULL COMMENT '密码（MD5加密）',
ADD COLUMN role ENUM('user','admin') DEFAULT 'user' COMMENT '角色：user普通用户，admin管理员',
ADD COLUMN created_by INT DEFAULT NULL COMMENT '创建者ID',
ADD COLUMN is_active TINYINT(1) DEFAULT 1 COMMENT '是否激活：1激活，0禁用',
ADD COLUMN last_login DATETIME DEFAULT NULL COMMENT '最后登录时间';

-- 2. 创建登录日志表
CREATE TABLE IF NOT EXISTS login_logs (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    login_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45) DEFAULT NULL COMMENT '登录IP地址',
    user_agent TEXT COMMENT '用户代理信息',
    login_status ENUM('success','failed') DEFAULT 'success' COMMENT '登录状态',
    fail_reason VARCHAR(255) DEFAULT NULL COMMENT '失败原因',
    PRIMARY KEY (id),
    KEY idx_user_id (user_id),
    KEY idx_login_time (login_time),
    KEY idx_username (username),
    CONSTRAINT fk_login_logs_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='登录日志表';

-- 3. 创建默认管理员账户（密码：admin123）
-- MD5('admin123') = 0192023a7bbd73250516f069df18b500
INSERT INTO users (username, password, role, daily_goal, created_at) 
VALUES ('admin', '0192023a7bbd73250516f069df18b500', 'admin', 5, NOW())
ON DUPLICATE KEY UPDATE password = '0192023a7bbd73250516f069df18b500', role = 'admin';

-- 4. 为现有用户设置默认密码（如果密码为空）
-- 默认密码为用户名的小写MD5值，用户首次登录后应修改密码
UPDATE users SET password = MD5(LOWER(username)) WHERE password IS NULL OR password = '';

-- 5. 添加索引优化查询
ALTER TABLE users ADD INDEX idx_username_password (username, password);
ALTER TABLE users ADD INDEX idx_role (role);
