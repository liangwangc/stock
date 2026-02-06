-- 添加缺失的技术指标字段
-- 执行方式：mysql -u root -p stock_data < add_missing_indicators.sql
-- 或者使用Python脚本：python database/add_missing_indicators_safe.py

-- ==================== A股历史数据表 ====================

-- 添加KDJ指标字段（如果不存在）
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `kdj_k` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ K值' AFTER `macd_hist`,
ADD COLUMN IF NOT EXISTS `kdj_d` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ D值' AFTER `kdj_k`,
ADD COLUMN IF NOT EXISTS `kdj_j` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ J值' AFTER `kdj_d`;

-- 添加CCI指标字段（如果不存在）
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `cci` DECIMAL(8, 4) DEFAULT NULL COMMENT 'CCI指标' AFTER `kdj_j`;

-- 添加BOLL指标字段（如果不存在，可选）
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `boll_upper` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL上轨' AFTER `cci`,
ADD COLUMN IF NOT EXISTS `boll_middle` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL中轨（MA20）' AFTER `boll_upper`,
ADD COLUMN IF NOT EXISTS `boll_lower` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL下轨' AFTER `boll_middle`;

-- 添加索引（可选，如果需要根据这些指标查询）
-- ALTER TABLE `stock_history_data` 
-- ADD INDEX IF NOT EXISTS `idx_kdj_k` (`kdj_k`),
-- ADD INDEX IF NOT EXISTS `idx_cci` (`cci`);

-- ==================== 美股历史数据表 ====================

-- 添加KDJ指标字段（如果不存在）
ALTER TABLE `us_stock_history_data` 
ADD COLUMN IF NOT EXISTS `kdj_k` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ K值' AFTER `macd_hist`,
ADD COLUMN IF NOT EXISTS `kdj_d` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ D值' AFTER `kdj_k`,
ADD COLUMN IF NOT EXISTS `kdj_j` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ J值' AFTER `kdj_d`;

-- 添加CCI指标字段（如果不存在）
ALTER TABLE `us_stock_history_data` 
ADD COLUMN IF NOT EXISTS `cci` DECIMAL(8, 4) DEFAULT NULL COMMENT 'CCI指标' AFTER `kdj_j`;

-- 添加BOLL指标字段（如果不存在，可选）
ALTER TABLE `us_stock_history_data` 
ADD COLUMN IF NOT EXISTS `boll_upper` DECIMAL(12, 4) DEFAULT NULL COMMENT 'BOLL上轨' AFTER `cci`,
ADD COLUMN IF NOT EXISTS `boll_middle` DECIMAL(12, 4) DEFAULT NULL COMMENT 'BOLL中轨（MA20）' AFTER `boll_upper`,
ADD COLUMN IF NOT EXISTS `boll_lower` DECIMAL(12, 4) DEFAULT NULL COMMENT 'BOLL下轨' AFTER `boll_middle`;
