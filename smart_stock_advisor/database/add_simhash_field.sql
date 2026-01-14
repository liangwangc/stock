-- 为 news_articles 表添加 simhash 字段
-- 如果字段已存在，此脚本会报错，可以忽略

-- 添加 simhash 字段
ALTER TABLE `news_articles` 
ADD COLUMN `simhash` BIGINT UNSIGNED DEFAULT NULL COMMENT 'SimHash值（用于相似度检测）' AFTER `duplicate_of`;

-- 添加 simhash 索引（提高查询速度）
ALTER TABLE `news_articles` 
ADD INDEX `idx_simhash` (`simhash`);
