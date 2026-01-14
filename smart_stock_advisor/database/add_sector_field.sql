-- 为 stock_predictions 表添加 sector 字段
-- 如果字段已存在，此脚本会报错，可以忽略

-- 添加 sector 字段（板块）
ALTER TABLE `stock_predictions` 
ADD COLUMN `sector` VARCHAR(100) DEFAULT NULL COMMENT '所属板块' AFTER `industry`;

-- 添加 sector 索引（提高查询速度）
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_sector` (`sector`);
