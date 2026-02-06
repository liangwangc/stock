-- 为模型学习优化添加字段
-- 执行日期：2026-01-14

-- ==================== stock_predictions 表优化 ====================

-- 1. 添加因子权重快照字段（JSON格式，存储预测时实际使用的权重配置）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `factor_weights` JSON DEFAULT NULL COMMENT '因子权重快照（JSON格式，存储预测时实际使用的权重配置）' AFTER `final_score`;

-- 2. 添加市场状态字段
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `market_state` VARCHAR(20) DEFAULT NULL COMMENT '市场状态（bull_market/bear_market/sideways）' AFTER `factor_weights`;

-- 3. 添加数据质量评分字段
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `data_quality_score` DECIMAL(5,4) DEFAULT NULL COMMENT '数据质量评分（0-1，越高表示数据质量越好）' AFTER `market_state`;

-- 4. 添加因子一致性评分字段
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `factor_consistency_score` DECIMAL(5,4) DEFAULT NULL COMMENT '因子一致性评分（0-1，越高表示因子方向越一致）' AFTER `data_quality_score`;

-- 5. 添加配置ID字段（关联到prediction_config表）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `config_id` INT DEFAULT NULL COMMENT '使用的配置ID（关联prediction_config表）' AFTER `factor_consistency_score`;

-- 6. 添加索引
ALTER TABLE `stock_predictions` 
ADD INDEX IF NOT EXISTS `idx_market_state` (`market_state`);

ALTER TABLE `stock_predictions` 
ADD INDEX IF NOT EXISTS `idx_config_id` (`config_id`);

ALTER TABLE `stock_predictions` 
ADD INDEX IF NOT EXISTS `idx_data_quality` (`data_quality_score`);

-- ==================== prediction_factors 表优化 ====================

-- 7. 添加配置ID字段（关联到prediction_config表）
ALTER TABLE `prediction_factors` 
ADD COLUMN IF NOT EXISTS `config_id` INT DEFAULT NULL COMMENT '使用的配置ID（关联prediction_config表）' AFTER `us_sector_weight`;

-- 8. 添加索引
ALTER TABLE `prediction_factors` 
ADD INDEX IF NOT EXISTS `idx_config_id` (`config_id`);

-- ==================== realtime_trading_decisions 表优化 ====================

-- 9. 添加实际价格字段（决策后N天的价格）
ALTER TABLE `realtime_trading_decisions` 
ADD COLUMN IF NOT EXISTS `actual_price` DECIMAL(10,2) DEFAULT NULL COMMENT '实际价格（决策后N天的价格）' AFTER `suggested_price`;

-- 10. 添加实际收益率字段
ALTER TABLE `realtime_trading_decisions` 
ADD COLUMN IF NOT EXISTS `actual_return_pct` DECIMAL(8,4) DEFAULT NULL COMMENT '实际收益率（%）' AFTER `actual_price`;

-- 11. 添加决策效果字段
ALTER TABLE `realtime_trading_decisions` 
ADD COLUMN IF NOT EXISTS `decision_effectiveness` VARCHAR(20) DEFAULT NULL COMMENT '决策效果（good/bad/neutral）' AFTER `actual_return_pct`;

-- 12. 添加索引
ALTER TABLE `realtime_trading_decisions` 
ADD INDEX IF NOT EXISTS `idx_decision_effectiveness` (`decision_effectiveness`);

-- ==================== 外键约束（可选，如果prediction_config表存在） ====================

-- 注意：如果prediction_config表存在，可以添加外键约束
-- ALTER TABLE `stock_predictions` 
-- ADD CONSTRAINT `fk_stock_predictions_config` 
-- FOREIGN KEY (`config_id`) REFERENCES `prediction_config`(`id`) ON DELETE SET NULL;

-- ALTER TABLE `prediction_factors` 
-- ADD CONSTRAINT `fk_prediction_factors_config` 
-- FOREIGN KEY (`config_id`) REFERENCES `prediction_config`(`id`) ON DELETE SET NULL;
