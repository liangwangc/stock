-- 添加单词复习状态点击次数字段
USE word_app;

-- 添加三个字段记录每种状态的点击次数
ALTER TABLE words 
ADD COLUMN forgot_count INT DEFAULT 0 COMMENT '忘记按钮点击次数',
ADD COLUMN vague_count INT DEFAULT 0 COMMENT '模糊按钮点击次数',
ADD COLUMN remembered_count INT DEFAULT 0 COMMENT '记住按钮点击次数';

-- 添加索引优化查询
ALTER TABLE words ADD INDEX idx_review_counts (forgot_count, vague_count, remembered_count);
