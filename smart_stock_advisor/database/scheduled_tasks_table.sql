-- 定时任务管理表
-- 用于管理股票历史数据增量更新等定时任务

CREATE TABLE IF NOT EXISTS `scheduled_tasks` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_name` VARCHAR(100) NOT NULL COMMENT '任务名称',
    `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型（如：stock_history_update）',
    `task_config` JSON DEFAULT NULL COMMENT '任务配置（JSON格式）',
    `is_active` TINYINT(1) DEFAULT 0 COMMENT '是否启用（1=启用，0=禁用）',
    `schedule_type` VARCHAR(20) DEFAULT 'daily' COMMENT '调度类型（daily/hourly/weekly/custom）',
    `schedule_time` TIME DEFAULT NULL COMMENT '执行时间（格式：HH:MM:SS）',
    `schedule_weekdays` VARCHAR(20) DEFAULT NULL COMMENT '执行星期（1-7，逗号分隔，如：1,2,3,4,5）',
    `cron_expression` VARCHAR(100) DEFAULT NULL COMMENT 'Cron表达式（如果schedule_type=custom）',
    `last_run_time` DATETIME DEFAULT NULL COMMENT '上次执行时间',
    `next_run_time` DATETIME DEFAULT NULL COMMENT '下次执行时间',
    `last_run_status` VARCHAR(20) DEFAULT NULL COMMENT '上次执行状态（success/failed/running）',
    `last_run_message` TEXT DEFAULT NULL COMMENT '上次执行消息',
    `run_count` INT DEFAULT 0 COMMENT '执行次数',
    `success_count` INT DEFAULT 0 COMMENT '成功次数',
    `fail_count` INT DEFAULT 0 COMMENT '失败次数',
    `created_by` INT DEFAULT NULL COMMENT '创建人ID',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_task_type` (`task_type`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_next_run_time` (`next_run_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='定时任务管理表';

-- 定时任务执行历史表
CREATE TABLE IF NOT EXISTS `scheduled_task_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_id` BIGINT NOT NULL COMMENT '任务ID',
    `task_name` VARCHAR(100) DEFAULT NULL COMMENT '任务名称',
    `task_type` VARCHAR(50) DEFAULT NULL COMMENT '任务类型',
    `start_time` DATETIME NOT NULL COMMENT '开始时间',
    `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
    `duration_seconds` INT DEFAULT NULL COMMENT '执行时长（秒）',
    `status` VARCHAR(20) NOT NULL COMMENT '状态（success/failed/running）',
    `message` TEXT DEFAULT NULL COMMENT '执行消息',
    `result_data` JSON DEFAULT NULL COMMENT '执行结果数据（JSON格式）',
    `error_info` TEXT DEFAULT NULL COMMENT '错误信息',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_start_time` (`start_time`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='定时任务执行历史表';
