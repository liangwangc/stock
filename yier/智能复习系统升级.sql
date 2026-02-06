-- 智能复习系统升级脚本
-- 以听写为主，学习为辅的复习系统
USE word_app;

-- 1. 创建单词复习记录表
CREATE TABLE IF NOT EXISTS word_review_logs (
    id INT NOT NULL AUTO_INCREMENT,
    word_id INT NOT NULL COMMENT '单词ID',
    user_id INT NOT NULL COMMENT '用户ID',
    review_date DATE NOT NULL COMMENT '复习日期',
    review_mode ENUM('study', 'dictation') DEFAULT 'study' COMMENT '复习模式：study学习模式，dictation听写模式',
    quality INT NOT NULL COMMENT '评分：1忘记，3模糊，5记住',
    should_advance TINYINT(1) DEFAULT 0 COMMENT '是否跳转：0不跳转，1跳转',
    ef_factor_before FLOAT COMMENT '复习前的ef_factor',
    ef_factor_after FLOAT COMMENT '复习后的ef_factor',
    interval_days_before INT COMMENT '复习前的间隔天数',
    interval_days_after INT COMMENT '复习后的间隔天数',
    repetitions_before INT COMMENT '复习前的repetitions',
    repetitions_after INT COMMENT '复习后的repetitions',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (id),
    KEY idx_word_id (word_id),
    KEY idx_user_id (user_id),
    KEY idx_review_date (review_date),
    KEY idx_word_date (word_id, review_date),
    KEY idx_user_date_mode (user_id, review_date, review_mode),
    CONSTRAINT fk_review_log_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE,
    CONSTRAINT fk_review_log_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='单词复习记录表';

-- 2. 优化words表，添加统计字段（使用存储过程检查字段是否存在）
DELIMITER $$

DROP PROCEDURE IF EXISTS add_column_if_not_exists$$
CREATE PROCEDURE add_column_if_not_exists(
    IN table_name VARCHAR(128),
    IN column_name VARCHAR(128),
    IN column_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = table_name
        AND COLUMN_NAME = column_name
    ) THEN
        SET @sql = CONCAT('ALTER TABLE ', table_name, ' ADD COLUMN ', column_name, ' ', column_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$

DROP PROCEDURE IF EXISTS add_index_if_not_exists$$
CREATE PROCEDURE add_index_if_not_exists(
    IN table_name VARCHAR(128),
    IN index_name VARCHAR(128),
    IN index_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.STATISTICS 
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = table_name
        AND INDEX_NAME = index_name
    ) THEN
        SET @sql = CONCAT('ALTER TABLE ', table_name, ' ADD INDEX ', index_name, ' ', index_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$

DELIMITER ;

-- 添加统计字段
CALL add_column_if_not_exists('words', 'last_review_date', 'DATE DEFAULT NULL COMMENT ''最后一次复习日期''');
CALL add_column_if_not_exists('words', 'last_review_mode', 'ENUM(''study'', ''dictation'') DEFAULT NULL COMMENT ''最后一次复习模式''');
CALL add_column_if_not_exists('words', 'consecutive_remembered', 'INT DEFAULT 0 COMMENT ''连续记住次数（以听写为主）''');
CALL add_column_if_not_exists('words', 'consecutive_forgot', 'INT DEFAULT 0 COMMENT ''连续忘记次数（以听写为主）''');
CALL add_column_if_not_exists('words', 'review_priority', 'INT DEFAULT 0 COMMENT ''复习优先级（数字越大越优先）''');

-- 添加兼容性字段（如果还没有）
CALL add_column_if_not_exists('words', 'forgot_count', 'INT DEFAULT 0 COMMENT ''忘记按钮点击次数''');
CALL add_column_if_not_exists('words', 'vague_count', 'INT DEFAULT 0 COMMENT ''模糊按钮点击次数''');
CALL add_column_if_not_exists('words', 'remembered_count', 'INT DEFAULT 0 COMMENT ''记住按钮点击次数''');

-- 添加索引
CALL add_index_if_not_exists('words', 'idx_last_review_date', '(last_review_date)');
CALL add_index_if_not_exists('words', 'idx_review_priority', '(review_priority)');
CALL add_index_if_not_exists('words', 'idx_user_priority_review', '(user_id, review_priority DESC, next_review)');
CALL add_index_if_not_exists('word_review_logs', 'idx_word_mode_date', '(word_id, review_mode, review_date DESC)');

-- 清理存储过程
DROP PROCEDURE IF EXISTS add_column_if_not_exists;
DROP PROCEDURE IF EXISTS add_index_if_not_exists;
