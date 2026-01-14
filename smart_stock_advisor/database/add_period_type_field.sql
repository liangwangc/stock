-- 添加周期类型字段，支持多周期K线数据存储
-- 执行方式：mysql -u root -p stock_data < add_period_type_field.sql

-- ==================== A股历史数据表 ====================

-- 添加period_type字段（如果不存在）
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `period_type` VARCHAR(10) DEFAULT 'daily' COMMENT '周期类型（daily=日线, weekly=周线, monthly=月线, yearly=年线）' 
AFTER `trade_date`;

-- 添加索引
ALTER TABLE `stock_history_data` 
ADD INDEX IF NOT EXISTS `idx_period_type` (`period_type`);

-- 添加复合唯一索引：股票代码 + 交易日期 + 周期类型
-- 注意：需要先删除原有的唯一索引，然后创建新的
ALTER TABLE `stock_history_data` 
DROP INDEX IF EXISTS `uk_symbol_date`;

ALTER TABLE `stock_history_data` 
ADD UNIQUE KEY `uk_symbol_date_period` (`symbol`, `trade_date`, `period_type`);

-- 将所有现有数据的period_type设置为'daily'
UPDATE `stock_history_data` 
SET `period_type` = 'daily' 
WHERE `period_type` IS NULL OR `period_type` = '';

-- ==================== 美股历史数据表 ====================

-- 添加period_type字段（如果不存在）
ALTER TABLE `us_stock_history_data` 
ADD COLUMN IF NOT EXISTS `period_type` VARCHAR(10) DEFAULT 'daily' COMMENT '周期类型（daily=日线, weekly=周线, monthly=月线, yearly=年线）' 
AFTER `trade_date`;

-- 添加索引
ALTER TABLE `us_stock_history_data` 
ADD INDEX IF NOT EXISTS `idx_period_type` (`period_type`);

-- 添加复合唯一索引：股票代码 + 交易日期 + 周期类型
ALTER TABLE `us_stock_history_data` 
DROP INDEX IF EXISTS `uk_symbol_date`;

ALTER TABLE `us_stock_history_data` 
ADD UNIQUE KEY `uk_symbol_date_period` (`symbol`, `trade_date`, `period_type`);

-- 将所有现有数据的period_type设置为'daily'
UPDATE `us_stock_history_data` 
SET `period_type` = 'daily' 
WHERE `period_type` IS NULL OR `period_type` = '';
