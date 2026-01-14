-- 为 stock_predictions 表添加预测价格和涨幅字段
-- 用于存储明日大概收盘价格和涨幅

-- 添加 predicted_close_price 字段（明日大概收盘价格）
ALTER TABLE `stock_predictions` 
ADD COLUMN `predicted_close_price` DECIMAL(10,2) DEFAULT NULL COMMENT '明日大概收盘价格' AFTER `current_price`;

-- 添加 predicted_change_pct 字段（明日大概涨幅百分比）
ALTER TABLE `stock_predictions` 
ADD COLUMN `predicted_change_pct` DECIMAL(6,2) DEFAULT NULL COMMENT '明日大概涨幅百分比' AFTER `predicted_close_price`;

-- 添加索引（用于查询和排序）
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_predicted_change_pct` (`predicted_change_pct`);
