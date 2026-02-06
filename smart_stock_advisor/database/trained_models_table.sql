-- 训练好的模型信息表
-- 用于存储机器学习模型的元数据、配置和性能指标

CREATE TABLE IF NOT EXISTS `trained_models` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `model_name` VARCHAR(100) NOT NULL COMMENT '模型名称（如：xgb_classifier_v1.0）',
    `model_type` VARCHAR(50) NOT NULL COMMENT '模型类型（xgb_classifier/lgb_classifier/xgb_regressor/lgb_regressor/ensemble等）',
    `model_version` VARCHAR(20) NOT NULL COMMENT '模型版本（如：v1.0）',
    `model_file_path` VARCHAR(500) NOT NULL COMMENT '模型文件路径（相对路径）',
    `feature_list` JSON COMMENT '特征列表（JSON格式，包含所有使用的特征名称）',
    `feature_importance` JSON COMMENT '特征重要性（JSON格式，{feature_name: importance_score}）',
    `training_config` JSON COMMENT '训练配置（JSON格式，包含超参数、训练策略等）',
    `training_metrics` JSON COMMENT '训练指标（JSON格式，包含准确率、MAE、F1-score等）',
    `train_start_date` DATE COMMENT '训练数据开始日期',
    `train_end_date` DATE COMMENT '训练数据结束日期',
    `val_start_date` DATE COMMENT '验证数据开始日期',
    `val_end_date` DATE COMMENT '验证数据结束日期',
    `test_start_date` DATE COMMENT '测试数据开始日期',
    `test_end_date` DATE COMMENT '测试数据结束日期',
    `sample_count` INT COMMENT '训练样本数',
    `feature_count` INT COMMENT '特征数量',
    `is_active` TINYINT(1) DEFAULT 0 COMMENT '是否激活（1=激活，0=未激活），同一类型只能有一个激活的模型',
    `description` TEXT COMMENT '模型描述',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_model_type` (`model_type`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_model_name` (`model_name`),
    UNIQUE KEY `uk_model_name_version` (`model_name`, `model_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='训练好的模型信息表';
