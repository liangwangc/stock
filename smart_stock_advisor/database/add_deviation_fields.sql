-- 为stock_predictions表添加偏差值字段
-- 执行日期：2026-01-16
-- 说明：添加偏差值字段，用于存储预测值与实际值的偏差，便于模型学习和模型训练

-- ==================== stock_predictions 表优化 ====================

-- 1. 添加偏差值字段（预测涨跌幅 - 实际涨跌幅，有符号）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `deviation_pct` DECIMAL(8, 4) DEFAULT NULL 
    COMMENT '偏差值（预测涨跌幅 - 实际涨跌幅，%，正数表示高估，负数表示低估）' 
    AFTER `actual_change_pct`;

-- 2. 添加绝对偏差值字段（|预测涨跌幅 - 实际涨跌幅|，用于评估预测准确性）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `absolute_deviation_pct` DECIMAL(8, 4) DEFAULT NULL 
    COMMENT '绝对偏差值（|预测涨跌幅 - 实际涨跌幅|，%，用于评估预测准确性）' 
    AFTER `deviation_pct`;

-- 3. 添加价格偏差字段（预测收盘价 - 实际价格）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `deviation_price` DECIMAL(10, 2) DEFAULT NULL 
    COMMENT '价格偏差（预测收盘价 - 实际价格，元，正数表示高估，负数表示低估）' 
    AFTER `absolute_deviation_pct`;

-- 4. 添加索引（用于快速查询和分析）
ALTER TABLE `stock_predictions` 
ADD INDEX IF NOT EXISTS `idx_deviation_pct` (`deviation_pct`);

ALTER TABLE `stock_predictions` 
ADD INDEX IF NOT EXISTS `idx_absolute_deviation_pct` (`absolute_deviation_pct`);

-- 5. 为已有数据填充偏差值（如果字段已存在则跳过）
-- 注意：这个UPDATE语句会在字段添加后自动执行，如果字段已存在则不会报错
UPDATE `stock_predictions`
SET 
    `deviation_pct` = `predicted_change_pct` - `actual_change_pct`,
    `absolute_deviation_pct` = ABS(`predicted_change_pct` - `actual_change_pct`),
    `deviation_price` = `predicted_close_price` - `actual_price`
WHERE `actual_change_pct` IS NOT NULL 
  AND `predicted_change_pct` IS NOT NULL
  AND (`deviation_pct` IS NULL OR `absolute_deviation_pct` IS NULL OR `deviation_price` IS NULL);
