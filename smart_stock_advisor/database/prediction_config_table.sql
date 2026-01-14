-- 预测参数配置表结构

-- 配置主表
CREATE TABLE IF NOT EXISTS `prediction_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `config_name` VARCHAR(100) NOT NULL COMMENT '配置名称',
    `description` TEXT COMMENT '配置描述',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认配置（1:是, 0:否）',
    `is_active` TINYINT(1) DEFAULT 0 COMMENT '是否激活（1:激活, 0:未激活）',
    `created_by` INT COMMENT '创建人ID',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_config_name` (`config_name`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_is_default` (`is_default`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测配置主表';

-- 配置值表
CREATE TABLE IF NOT EXISTS `prediction_config_values` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `config_id` INT NOT NULL COMMENT '配置ID',
    `category` VARCHAR(50) NOT NULL COMMENT '配置分类 (prediction/indicator/news/trading)',
    `param_key` VARCHAR(100) NOT NULL COMMENT '参数键',
    `param_value` TEXT NOT NULL COMMENT '参数值（JSON格式或字符串）',
    `param_type` VARCHAR(20) NOT NULL COMMENT '参数类型 (number/boolean/string)',
    `description` VARCHAR(255) COMMENT '参数描述',
    `min_value` DECIMAL(10,4) COMMENT '最小值',
    `max_value` DECIMAL(10,4) COMMENT '最大值',
    `unit` VARCHAR(20) COMMENT '单位（如：%, 天, 倍）',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (`config_id`) REFERENCES `prediction_config`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uk_config_param` (`config_id`, `category`, `param_key`),
    INDEX `idx_config_id` (`config_id`),
    INDEX `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置值表';

-- 配置历史表
CREATE TABLE IF NOT EXISTS `prediction_config_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `config_id` INT NOT NULL COMMENT '配置ID',
    `action` VARCHAR(20) NOT NULL COMMENT '操作类型 (create/update/delete/activate/deactivate)',
    `old_values` JSON COMMENT '修改前的值（JSON格式）',
    `new_values` JSON COMMENT '修改后的值（JSON格式）',
    `changed_by` INT COMMENT '修改人ID',
    `change_description` VARCHAR(500) COMMENT '变更说明',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
    FOREIGN KEY (`config_id`) REFERENCES `prediction_config`(`id`) ON DELETE CASCADE,
    INDEX `idx_config_id` (`config_id`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置历史表';
