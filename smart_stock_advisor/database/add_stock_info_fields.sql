-- 为股票预测结果表添加行业、板块等信息字段

-- 检查并添加字段（如果不存在）
-- 注意：MySQL不支持IF NOT EXISTS语法在ALTER TABLE中，需要先检查

-- 添加行业字段
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `industry` VARCHAR(100) DEFAULT NULL COMMENT '所属行业' AFTER `name`;

-- 添加概念板块字段（JSON格式存储多个概念）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `concepts` TEXT DEFAULT NULL COMMENT '概念板块（JSON数组格式）' AFTER `industry`;

-- 添加主要概念板块字段（用于快速查询）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `main_concept` VARCHAR(100) DEFAULT NULL COMMENT '主要概念板块' AFTER `concepts`;

-- 添加地区字段（用于区分沪深、港股等）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `market` VARCHAR(20) DEFAULT 'A股' COMMENT '所属市场（A股/港股/美股）' AFTER `main_concept`;

-- 添加指数成分股标记
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `is_index_component` TINYINT(1) DEFAULT 0 COMMENT '是否指数成分股（1:是, 0:否）' AFTER `market`;

-- 添加所属指数（JSON格式，可能属于多个指数）
ALTER TABLE `stock_predictions` 
ADD COLUMN IF NOT EXISTS `index_components` TEXT DEFAULT NULL COMMENT '所属指数（JSON数组，如：["沪深300", "中证500"]）' AFTER `is_index_component`;

-- 添加索引以提高查询性能
ALTER TABLE `stock_predictions` 
ADD INDEX IF NOT EXISTS `idx_industry` (`industry`);

ALTER TABLE `stock_predictions` 
ADD INDEX IF NOT EXISTS `idx_main_concept` (`main_concept`);

ALTER TABLE `stock_predictions` 
ADD INDEX IF NOT EXISTS `idx_market` (`market`);
