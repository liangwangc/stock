-- 添加缺失的复习统计字段
USE word_app;

-- 使用存储过程检查并添加字段（如果不存在）
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

-- 添加字段
CALL add_column_if_not_exists('words', 'last_review_date', 'DATE DEFAULT NULL COMMENT ''最后一次复习日期''');
CALL add_column_if_not_exists('words', 'last_review_mode', 'ENUM(''study'', ''dictation'') DEFAULT NULL COMMENT ''最后一次复习模式''');
CALL add_column_if_not_exists('words', 'consecutive_remembered', 'INT DEFAULT 0 COMMENT ''连续记住次数（以听写为主）''');
CALL add_column_if_not_exists('words', 'consecutive_forgot', 'INT DEFAULT 0 COMMENT ''连续忘记次数（以听写为主）''');
CALL add_column_if_not_exists('words', 'review_priority', 'INT DEFAULT 0 COMMENT ''复习优先级（数字越大越优先）''');

-- 添加索引
CALL add_index_if_not_exists('words', 'idx_last_review_date', '(last_review_date)');
CALL add_index_if_not_exists('words', 'idx_review_priority', '(review_priority)');
CALL add_index_if_not_exists('words', 'idx_user_priority_review', '(user_id, review_priority DESC, next_review)');

-- 清理存储过程
DROP PROCEDURE IF EXISTS add_column_if_not_exists;
DROP PROCEDURE IF EXISTS add_index_if_not_exists;
