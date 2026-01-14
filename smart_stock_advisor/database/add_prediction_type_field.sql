-- 为 stock_predictions 表添加 prediction_type 字段
-- 用于区分"收盘-明日"和"未收盘-明天"两种预测类型

-- 添加 prediction_type 字段
ALTER TABLE `stock_predictions` 
ADD COLUMN `prediction_type` VARCHAR(20) DEFAULT 'after_close' COMMENT '预测类型（after_close=收盘-明日，before_close=未收盘-明天）' AFTER `target_date`;

-- 添加索引
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_prediction_type` (`prediction_type`);

-- 添加复合索引（用于查询特定类型的预测）
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_prediction_type_date` (`prediction_type`, `prediction_date`);
