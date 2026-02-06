-- 单词库功能升级脚本
-- 执行此脚本以添加单词库功能

USE word_app;

-- 1. 修改users表，添加单词库相关字段
ALTER TABLE users 
ADD COLUMN enable_word_bank TINYINT(1) DEFAULT 0 COMMENT '是否启用单词库：1启用，0禁用',
ADD COLUMN grade VARCHAR(20) DEFAULT NULL COMMENT '年级：grade1-grade12（一年级到高三）';

-- 2. 创建单词库表
CREATE TABLE IF NOT EXISTS word_bank (
    id INT NOT NULL AUTO_INCREMENT,
    grade VARCHAR(20) NOT NULL COMMENT '年级：grade1-grade12',
    word VARCHAR(100) NOT NULL COMMENT '单词',
    pronunciation VARCHAR(100) DEFAULT '' COMMENT '音标',
    meaning TEXT COMMENT '中文释义',
    example TEXT COMMENT '例句',
    word_order INT DEFAULT 0 COMMENT '单词顺序',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_grade (grade),
    KEY idx_grade_order (grade, word_order),
    UNIQUE KEY uk_grade_word (grade, word)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='单词库表';

-- 3. 添加words表字段，标记单词来源
ALTER TABLE words 
ADD COLUMN source ENUM('manual','word_bank') DEFAULT 'manual' COMMENT '单词来源：manual手动录入，word_bank单词库';

-- 4. 添加索引优化查询
ALTER TABLE words ADD INDEX idx_source (source);
ALTER TABLE words ADD INDEX idx_user_date_source (user_id, date_added, source);

-- 5. 插入示例单词库数据（一年级示例）
-- 注意：这里只插入少量示例，实际使用时需要导入完整的单词库
INSERT INTO word_bank (grade, word, pronunciation, meaning, example, word_order) VALUES
('grade1', 'hello', '/həˈloʊ/', '你好', 'Hello, how are you?\n你好，你好吗？', 1),
('grade1', 'good', '/ɡʊd/', '好的', 'Have a good day!\n祝你有美好的一天！', 2),
('grade1', 'thank', '/θæŋk/', '谢谢', 'Thank you very much.\n非常感谢。', 3),
('grade1', 'yes', '/jes/', '是的', 'Yes, I do.\n是的，我愿意。', 4),
('grade1', 'no', '/noʊ/', '不', 'No, thank you.\n不，谢谢。', 5)
ON DUPLICATE KEY UPDATE word=word;

-- 6. 插入其他年级示例（可以后续扩展）
-- 这里只做示例，实际需要导入完整的各年级单词库
