-- 新闻文章表
-- 存储从各个新闻源抓取的详细新闻信息

CREATE TABLE IF NOT EXISTS `news_articles` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(500) NOT NULL COMMENT '新闻标题',
    `content` TEXT COMMENT '新闻内容',
    `summary` TEXT COMMENT '新闻摘要',
    `publish_time` DATETIME COMMENT '发布时间',
    `fetch_time` DATETIME NOT NULL COMMENT '抓取时间',
    `source` VARCHAR(50) NOT NULL COMMENT '新闻来源（如：金十数据、财新等）',
    `source_url` VARCHAR(1000) COMMENT '新闻原始URL',
    `news_type` VARCHAR(20) DEFAULT 'market' COMMENT '新闻类型（stock/market/policy/industry）',
    
    -- 关联信息
    `symbol` VARCHAR(10) DEFAULT NULL COMMENT '关联股票代码（如果是股票新闻）',
    `sector` VARCHAR(100) DEFAULT NULL COMMENT '关联板块',
    `industry` VARCHAR(100) DEFAULT NULL COMMENT '关联行业',
    `concept` VARCHAR(200) DEFAULT NULL COMMENT '关联概念',
    
    -- 情感分析结果
    `sentiment` VARCHAR(20) DEFAULT NULL COMMENT '情感倾向（positive/negative/neutral）',
    `sentiment_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '情感得分（-1到1）',
    `sentiment_confidence` DECIMAL(5, 4) DEFAULT NULL COMMENT '情感分析置信度（0到1）',
    `is_positive` TINYINT(1) DEFAULT 0 COMMENT '是否利好（1=利好，0=非利好）',
    `is_negative` TINYINT(1) DEFAULT 0 COMMENT '是否利空（1=利空，0=非利空）',
    `is_policy` TINYINT(1) DEFAULT 0 COMMENT '是否政策新闻',
    `keywords` JSON COMMENT '匹配的关键词（JSON格式）',
    
    -- 相关性
    `relevance_type` VARCHAR(20) DEFAULT NULL COMMENT '相关性类型（direct/industry/market）',
    `relevance_score` DECIMAL(5, 4) DEFAULT NULL COMMENT '相关性得分（0到1）',
    
    -- 元数据
    `author` VARCHAR(100) DEFAULT NULL COMMENT '作者',
    `tags` JSON COMMENT '标签（JSON格式）',
    `view_count` INT DEFAULT 0 COMMENT '浏览次数（如果来源提供）',
    `is_duplicate` TINYINT(1) DEFAULT 0 COMMENT '是否重复新闻',
    `duplicate_of` BIGINT DEFAULT NULL COMMENT '重复新闻的原始ID',
    `simhash` BIGINT UNSIGNED DEFAULT NULL COMMENT 'SimHash值（用于相似度检测）',
    
    -- 时间戳
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_publish_time` (`publish_time`),
    INDEX `idx_fetch_time` (`fetch_time`),
    INDEX `idx_source` (`source`),
    INDEX `idx_sentiment` (`sentiment`),
    INDEX `idx_news_type` (`news_type`),
    INDEX `idx_sector` (`sector`),
    INDEX `idx_industry` (`industry`),
    INDEX `idx_is_positive` (`is_positive`),
    INDEX `idx_is_negative` (`is_negative`),
    INDEX `idx_is_policy` (`is_policy`),
    INDEX `idx_relevance_type` (`relevance_type`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_simhash` (`simhash`),
    
    -- 唯一索引：防止重复抓取（基于标题和来源）
    UNIQUE KEY `uk_title_source` (`title`(200), `source`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻文章表';

-- 新闻抓取任务表
CREATE TABLE IF NOT EXISTS `news_crawl_tasks` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `task_name` VARCHAR(100) NOT NULL COMMENT '任务名称',
    `task_type` VARCHAR(20) NOT NULL COMMENT '任务类型（stock/market/all）',
    `symbol` VARCHAR(10) DEFAULT NULL COMMENT '股票代码（如果是股票任务）',
    `sources` JSON COMMENT '新闻源列表（JSON格式）',
    `interval_minutes` INT NOT NULL DEFAULT 60 COMMENT '抓取间隔（分钟）',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活（1=激活，0=停止）',
    `last_run_time` DATETIME DEFAULT NULL COMMENT '最后运行时间',
    `next_run_time` DATETIME DEFAULT NULL COMMENT '下次运行时间',
    `run_count` INT DEFAULT 0 COMMENT '运行次数',
    `success_count` INT DEFAULT 0 COMMENT '成功次数',
    `fail_count` INT DEFAULT 0 COMMENT '失败次数',
    `last_error` TEXT COMMENT '最后错误信息',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_next_run_time` (`next_run_time`),
    INDEX `idx_task_type` (`task_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻抓取任务表';
