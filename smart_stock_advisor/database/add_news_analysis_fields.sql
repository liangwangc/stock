-- 添加新闻内容分析字段
-- 执行日期：2026-01-16
-- 说明：添加新闻发布时间分析和真实性验证相关字段

-- ==================== news_articles 表字段补充 ====================

-- 添加可靠性相关字段
ALTER TABLE `news_articles` 
ADD COLUMN IF NOT EXISTS `reliability_score` DECIMAL(5, 4) DEFAULT NULL COMMENT '可靠性得分（0-1，基于发布时间和真实性分析）' AFTER `relevance_score`,
ADD COLUMN IF NOT EXISTS `is_reliable` TINYINT(1) DEFAULT 1 COMMENT '是否可靠（1=可靠，0=不可靠）' AFTER `reliability_score`,
ADD COLUMN IF NOT EXISTS `should_use_for_prediction` TINYINT(1) DEFAULT 1 COMMENT '是否应该用于预测（1=是，0=否）' AFTER `is_reliable`,
ADD COLUMN IF NOT EXISTS `time_quality` VARCHAR(20) DEFAULT NULL COMMENT '时间质量（good/normal/suspicious/invalid）' AFTER `should_use_for_prediction`,
ADD COLUMN IF NOT EXISTS `time_analysis_result` JSON COMMENT '发布时间分析结果（JSON格式）' AFTER `time_quality`,
ADD COLUMN IF NOT EXISTS `credibility_score` DECIMAL(5, 4) DEFAULT NULL COMMENT '可信度得分（0-1，基于内容真实性分析）' AFTER `time_analysis_result`,
ADD COLUMN IF NOT EXISTS `credibility_analysis_result` JSON COMMENT '真实性分析结果（JSON格式）' AFTER `credibility_score`,
ADD COLUMN IF NOT EXISTS `analysis_warnings` JSON COMMENT '分析警告信息（JSON格式数组）' AFTER `credibility_analysis_result`;

-- 添加索引
ALTER TABLE `news_articles` 
ADD INDEX IF NOT EXISTS `idx_reliability_score` (`reliability_score`),
ADD INDEX IF NOT EXISTS `idx_is_reliable` (`is_reliable`),
ADD INDEX IF NOT EXISTS `idx_should_use_for_prediction` (`should_use_for_prediction`),
ADD INDEX IF NOT EXISTS `idx_time_quality` (`time_quality`);
