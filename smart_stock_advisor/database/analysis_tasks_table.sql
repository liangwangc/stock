-- 股票分析任务历史表
CREATE TABLE IF NOT EXISTS `analysis_tasks` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(100) NOT NULL COMMENT '任务ID',
    `user_id` INT DEFAULT NULL COMMENT '执行用户ID',
    `username` VARCHAR(50) DEFAULT NULL COMMENT '执行用户名',
    `limit_count` INT DEFAULT NULL COMMENT '分析数量（NULL表示全部）',
    `sort_type` VARCHAR(20) DEFAULT NULL COMMENT '排序方式（turnover/random）',
    `status` VARCHAR(20) DEFAULT NULL COMMENT '任务状态（running/completed/cancelled/failed）',
    `total_stocks` INT DEFAULT 0 COMMENT '总股票数',
    `success_count` INT DEFAULT 0 COMMENT '成功数量',
    `fail_count` INT DEFAULT 0 COMMENT '失败数量',
    `progress` INT DEFAULT 0 COMMENT '当前进度',
    `start_time` DATETIME DEFAULT NULL COMMENT '开始时间',
    `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
    `duration_seconds` INT DEFAULT NULL COMMENT '耗时（秒）',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_task_id` (`task_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_start_time` (`start_time`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票分析任务历史表';
