-- 用户登录历史记录表
-- 执行日期：2026-01-16
-- 说明：记录用户每次登录尝试的详细信息，包括成功和失败的登录

-- ==================== user_login_history 表 ====================

-- 创建用户登录历史记录表
CREATE TABLE IF NOT EXISTS `user_login_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `user_id` BIGINT DEFAULT NULL COMMENT '用户ID（登录成功时记录，失败时为NULL）',
    `username` VARCHAR(50) NOT NULL COMMENT '用户名（登录时使用的用户名）',
    `login_status` VARCHAR(20) NOT NULL DEFAULT 'success' COMMENT '登录状态（success=成功，failed=失败）',
    `failure_reason` VARCHAR(255) DEFAULT NULL COMMENT '失败原因（如：密码错误、用户不存在、用户已禁用等）',
    `ip_address` VARCHAR(50) DEFAULT NULL COMMENT '登录IP地址',
    `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '用户代理（浏览器信息）',
    `login_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
    `session_id` VARCHAR(255) DEFAULT NULL COMMENT '会话ID（登录成功时记录）',
    `location` VARCHAR(100) DEFAULT NULL COMMENT '登录地点（可根据IP解析，可选）',
    `device_type` VARCHAR(50) DEFAULT NULL COMMENT '设备类型（如：PC、Mobile、Tablet等，可选）',
    `browser` VARCHAR(100) DEFAULT NULL COMMENT '浏览器类型（如：Chrome、Firefox等，可选）',
    `os` VARCHAR(100) DEFAULT NULL COMMENT '操作系统（如：Windows、macOS、Linux等，可选）',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_username` (`username`),
    INDEX `idx_login_status` (`login_status`),
    INDEX `idx_login_time` (`login_time`),
    INDEX `idx_ip_address` (`ip_address`),
    INDEX `idx_session_id` (`session_id`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户登录历史记录表';
