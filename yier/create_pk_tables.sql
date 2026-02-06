-- PK排行榜功能数据库表创建脚本

-- 1. 创建用户排名快照表
CREATE TABLE IF NOT EXISTS user_rankings (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    ranking_date DATE NOT NULL COMMENT '排名日期',
    period_type ENUM('daily', 'weekly', 'monthly', 'yearly') NOT NULL COMMENT '排名周期类型',
    rank_position INT NOT NULL COMMENT '排名位置',
    total_words INT DEFAULT 0 COMMENT '学习单词总数',
    streak_days INT DEFAULT 0 COMMENT '连续打卡天数',
    completion_rate DECIMAL(5,2) DEFAULT 0.00 COMMENT '完成率',
    mastered_words INT DEFAULT 0 COMMENT '已掌握单词数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_date_type (user_id, ranking_date, period_type),
    KEY idx_period_type (period_type),
    KEY idx_rank_position (rank_position),
    CONSTRAINT fk_ranking_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户排名快照表';

-- 2. 创建排名历史表（用于计算排名变化）
CREATE TABLE IF NOT EXISTS user_ranking_history (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    ranking_date DATE NOT NULL COMMENT '排名日期',
    period_type ENUM('daily', 'weekly', 'monthly', 'yearly') NOT NULL COMMENT '排名周期类型',
    rank_position INT NOT NULL COMMENT '排名位置',
    total_words INT DEFAULT 0 COMMENT '学习单词总数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_date_type (user_id, ranking_date, period_type),
    KEY idx_ranking_date (ranking_date),
    CONSTRAINT fk_history_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户排名历史表';
