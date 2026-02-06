-- 修复股票历史数据重复问题
-- 执行方式：mysql -u root -p stock_data < fix_duplicate_data.sql

-- ==================== 步骤1：检查唯一索引 ====================

-- 查看当前唯一索引
-- SHOW INDEXES FROM stock_history_data WHERE Key_name LIKE 'uk_%' OR Non_unique = 0;

-- ==================== 步骤2：确保 period_type 字段存在 ====================

-- 添加period_type字段（如果不存在）
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `period_type` VARCHAR(10) DEFAULT 'daily' COMMENT '周期类型（daily=日线, weekly=周线, monthly=月线, yearly=年线）' 
AFTER `trade_date`;

-- 将所有现有数据的period_type设置为'daily'（如果为NULL）
UPDATE `stock_history_data` 
SET `period_type` = 'daily' 
WHERE `period_type` IS NULL OR `period_type` = '';

-- ==================== 步骤3：删除旧的唯一索引（如果存在） ====================

-- 删除旧的唯一索引（只有symbol和trade_date）
ALTER TABLE `stock_history_data` 
DROP INDEX IF EXISTS `uk_symbol_date`;

-- ==================== 步骤4：创建新的唯一索引（包含period_type） ====================

-- 创建新的唯一索引：symbol + trade_date + period_type
ALTER TABLE `stock_history_data` 
ADD UNIQUE KEY `uk_symbol_date_period` (`symbol`, `trade_date`, `period_type`);

-- ==================== 步骤5：清理重复数据 ====================

-- 方法1：删除重复数据，保留ID最小的记录
-- 注意：执行前请先备份数据！

-- 创建临时表存储需要保留的记录（ID最小的记录）
CREATE TEMPORARY TABLE IF NOT EXISTS `temp_keep_records` AS
SELECT MIN(id) as id
FROM `stock_history_data`
GROUP BY `symbol`, `trade_date`, `period_type`;

-- 删除不在保留列表中的重复记录
-- DELETE FROM `stock_history_data`
-- WHERE id NOT IN (SELECT id FROM `temp_keep_records`);

-- 注意：上面的DELETE语句被注释了，请先检查temp_keep_records中的数据是否正确
-- 如果确认无误，再取消注释执行

-- 方法2：使用窗口函数（MySQL 8.0+）
-- DELETE FROM `stock_history_data`
-- WHERE id IN (
--     SELECT id FROM (
--         SELECT id,
--                ROW_NUMBER() OVER (PARTITION BY symbol, trade_date, period_type ORDER BY id) as rn
--         FROM `stock_history_data`
--     ) as t
--     WHERE rn > 1
-- );

-- ==================== 步骤6：验证修复结果 ====================

-- 检查是否还有重复数据
-- SELECT symbol, trade_date, period_type, COUNT(*) as count
-- FROM stock_history_data
-- GROUP BY symbol, trade_date, period_type
-- HAVING COUNT(*) > 1;

-- 如果上面的查询返回空结果，说明重复数据已清理完成
