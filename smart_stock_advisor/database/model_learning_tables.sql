-- 模型学习系统数据库表

-- 1. 模型性能记录表
CREATE TABLE IF NOT EXISTS `model_performance` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `evaluation_date` DATE NOT NULL COMMENT '评估日期',
    `evaluation_type` VARCHAR(50) NOT NULL COMMENT '评估类型（prediction/trading）',
    `time_period` VARCHAR(50) DEFAULT NULL COMMENT '评估时间周期（7d/30d/90d）',
    `direction_accuracy` DECIMAL(5, 4) DEFAULT NULL COMMENT '方向准确率',
    `magnitude_mae` DECIMAL(8, 4) DEFAULT NULL COMMENT '幅度平均绝对误差',
    `confidence_calibration` DECIMAL(5, 4) DEFAULT NULL COMMENT '置信度校准度',
    `total_return` DECIMAL(8, 4) DEFAULT NULL COMMENT '总收益率',
    `sharpe_ratio` DECIMAL(8, 4) DEFAULT NULL COMMENT '夏普比率',
    `max_drawdown` DECIMAL(8, 4) DEFAULT NULL COMMENT '最大回撤',
    `win_rate` DECIMAL(5, 4) DEFAULT NULL COMMENT '胜率',
    `profit_loss_ratio` DECIMAL(8, 4) DEFAULT NULL COMMENT '盈亏比',
    `factor_contributions` JSON DEFAULT NULL COMMENT '因子贡献度（JSON）',
    `market_condition` VARCHAR(50) DEFAULT NULL COMMENT '市场状态（bull/bear/sideways）',
    `sample_count` INT DEFAULT NULL COMMENT '样本数量',
    `details` JSON DEFAULT NULL COMMENT '详细信息（JSON）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_evaluation_date` (`evaluation_date`),
    INDEX `idx_evaluation_type` (`evaluation_type`),
    INDEX `idx_time_period` (`time_period`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型性能记录表';

-- 2. 参数优化历史表
CREATE TABLE IF NOT EXISTS `parameter_optimization_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `optimization_date` DATETIME NOT NULL COMMENT '优化日期',
    `optimization_method` VARCHAR(50) NOT NULL COMMENT '优化方法（grid_search/bayesian/genetic/rl）',
    `old_parameters` JSON DEFAULT NULL COMMENT '优化前参数（JSON）',
    `new_parameters` JSON DEFAULT NULL COMMENT '优化后参数（JSON）',
    `old_performance` JSON DEFAULT NULL COMMENT '优化前性能指标（JSON）',
    `new_performance` JSON DEFAULT NULL COMMENT '优化后性能指标（JSON）',
    `improvement_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '改进百分比',
    `is_applied` TINYINT(1) DEFAULT 0 COMMENT '是否已应用（1:是, 0:否）',
    `applied_at` DATETIME DEFAULT NULL COMMENT '应用时间',
    `applied_by` INT DEFAULT NULL COMMENT '应用人ID',
    `backtest_result` JSON DEFAULT NULL COMMENT '回测结果（JSON）',
    `optimization_config` JSON DEFAULT NULL COMMENT '优化配置（JSON）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_optimization_date` (`optimization_date`),
    INDEX `idx_is_applied` (`is_applied`),
    INDEX `idx_optimization_method` (`optimization_method`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='参数优化历史表';

-- 3. 模型学习任务表
CREATE TABLE IF NOT EXISTS `model_learning_tasks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `task_name` VARCHAR(100) NOT NULL COMMENT '任务名称',
    `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型（evaluation/optimization/backtest）',
    `schedule_type` VARCHAR(50) NOT NULL COMMENT '调度类型（daily/weekly/monthly）',
    `schedule_time` VARCHAR(20) DEFAULT NULL COMMENT '调度时间（HH:MM）',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `last_run_time` DATETIME DEFAULT NULL COMMENT '上次运行时间',
    `next_run_time` DATETIME DEFAULT NULL COMMENT '下次运行时间',
    `run_status` VARCHAR(20) DEFAULT 'pending' COMMENT '运行状态（pending/running/completed/failed）',
    `last_run_result` JSON DEFAULT NULL COMMENT '上次运行结果（JSON）',
    `config` JSON DEFAULT NULL COMMENT '任务配置（JSON）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_task_name` (`task_name`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_next_run_time` (`next_run_time`),
    INDEX `idx_task_type` (`task_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型学习任务表';
