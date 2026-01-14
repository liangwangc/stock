-- 添加X2指标字段，支持计算收盘价在N日价格区间中的相对位置
-- 执行方式：mysql -u root -p stock_data < add_x2_field.sql

-- ==================== A股历史数据表 ====================

-- 添加x2字段（如果不存在）
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `x2` DECIMAL(8, 4) DEFAULT NULL COMMENT 'X2指标（收盘价在20日区间中的相对位置，0-100）' 
AFTER `rsi`;

-- 添加索引（可选，如果需要根据x2查询）
-- ALTER TABLE `stock_history_data` 
-- ADD INDEX IF NOT EXISTS `idx_x2` (`x2`);

-- ==================== 美股历史数据表 ====================

-- 添加x2字段（如果不存在）
ALTER TABLE `us_stock_history_data` 
ADD COLUMN IF NOT EXISTS `x2` DECIMAL(8, 4) DEFAULT NULL COMMENT 'X2指标（收盘价在20日区间中的相对位置，0-100）' 
AFTER `rsi`;

-- 添加索引（可选，如果需要根据x2查询）
-- ALTER TABLE `us_stock_history_data` 
-- ADD INDEX IF NOT EXISTS `idx_x2` (`x2`);
