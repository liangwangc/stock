-- 新闻通知表
-- 存储重要新闻的推送通知记录

CREATE TABLE IF NOT EXISTS `news_notifications` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `news_id` BIGINT NOT NULL COMMENT '新闻ID',
    `notification_type` VARCHAR(20) NOT NULL DEFAULT 'important' COMMENT '通知类型（important/positive/negative/policy）',
    `title` VARCHAR(500) NOT NULL COMMENT '新闻标题',
    `symbol` VARCHAR(10) DEFAULT NULL COMMENT '关联股票代码',
    `sentiment` VARCHAR(20) DEFAULT NULL COMMENT '情感倾向',
    `is_sent` TINYINT(1) DEFAULT 0 COMMENT '是否已发送（1=已发送，0=未发送）',
    `sent_at` DATETIME DEFAULT NULL COMMENT '发送时间',
    `is_read` TINYINT(1) DEFAULT 0 COMMENT '是否已读（1=已读，0=未读）',
    `read_at` DATETIME DEFAULT NULL COMMENT '阅读时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX `idx_news_id` (`news_id`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_is_sent` (`is_sent`),
    INDEX `idx_is_read` (`is_read`),
    INDEX `idx_notification_type` (`notification_type`),
    INDEX `idx_created_at` (`created_at`),
    
    FOREIGN KEY (`news_id`) REFERENCES `news_articles`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻通知表';
