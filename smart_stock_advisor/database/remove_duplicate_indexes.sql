-- 删除重复索引优化脚本
-- 执行日期：2026-01-16
-- 说明：删除冗余索引，提升写入性能，减少锁竞争
-- 执行方式：mysql -u root -p stock_data < remove_duplicate_indexes.sql
-- 或使用Python：source database/remove_duplicate_indexes.sql

-- ==================== stock_history_data 表索引优化 ====================

-- 1. 删除 idx_symbol（冗余：被复合索引前缀覆盖）
-- 说明：uk_symbol_date_period 和 idx_symbol_date 的前缀都可以用于 WHERE symbol = ? 查询
-- 影响：无影响，查询仍然可以使用复合索引前缀
ALTER TABLE `stock_history_data` DROP INDEX IF EXISTS `idx_symbol`;

-- 2. 删除 idx_date_range（冗余：与 idx_symbol_date 重复，使用场景少）
-- 说明：idx_symbol_date (symbol, trade_date) 已经覆盖了最常见的查询模式
-- 影响：WHERE trade_date BETWEEN ? AND ? ORDER BY symbol 查询可能略微变慢，但可以使用 idx_trade_date
-- 建议：删除后监控查询性能，如果变慢可以重新创建
ALTER TABLE `stock_history_data` DROP INDEX IF EXISTS `idx_date_range`;

-- 验证：显示优化后的索引
-- SHOW INDEX FROM `stock_history_data`;

-- ==================== stock_predictions 表索引优化 ====================

-- 3. 删除 idx_symbol（冗余：被复合索引前缀覆盖）
-- 说明：idx_symbol_prediction_date 和 idx_symbol_prediction_time 的前缀都可以用于 WHERE symbol = ? 查询
-- 影响：无影响，查询仍然可以使用复合索引前缀
ALTER TABLE `stock_predictions` DROP INDEX IF EXISTS `idx_symbol`;

-- 4. 删除 idx_prediction_date（冗余：被复合索引前缀覆盖）
-- 说明：idx_prediction_date_score 的前缀可以用于 WHERE prediction_date = ? 查询
-- 影响：无影响，查询仍然可以使用复合索引前缀
ALTER TABLE `stock_predictions` DROP INDEX IF EXISTS `idx_prediction_date`;

-- 验证：显示优化后的索引
-- SHOW INDEX FROM `stock_predictions`;

-- ==================== north_bound_capital 表索引优化 ====================

-- 5. 删除 idx_date（冗余：与 UNIQUE KEY uk_date 重复）
-- 说明：uk_date 已经提供了索引功能，idx_date 是多余的
-- 影响：无影响，UNIQUE KEY 已经提供索引
ALTER TABLE `north_bound_capital` DROP INDEX IF EXISTS `idx_date`;

-- 验证：显示优化后的索引
-- SHOW INDEX FROM `north_bound_capital`;

-- ==================== 其他表索引检查 ====================

-- 注意：以下表需要进一步检查，暂时不删除
-- news_articles
-- realtime_trading_decisions
-- scheduled_task_history
-- parameter_optimization_history

-- ==================== 优化完成 ====================

-- 执行完成后，建议：
-- 1. 监控查询性能（特别是 WHERE symbol = ? 和 WHERE trade_date BETWEEN ? AND ? 查询）
-- 2. 监控写入性能（应该有所提升）
-- 3. 监控数据库锁竞争（应该有所减少）
-- 4. 如果性能下降，可以使用以下SQL重新创建索引：
--    ALTER TABLE `stock_history_data` ADD INDEX `idx_symbol` (`symbol`);
--    ALTER TABLE `stock_history_data` ADD INDEX `idx_date_range` (`trade_date`, `symbol`);
