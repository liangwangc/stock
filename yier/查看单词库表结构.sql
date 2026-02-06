-- 查看单词库表结构
USE word_app;

-- 1. 查看 word_bank 表结构
DESCRIBE word_bank;

-- 2. 查看 word_bank 表创建语句
SHOW CREATE TABLE word_bank;

-- 3. 查看 word_bank 表索引
SHOW INDEX FROM word_bank;

-- 4. 查看 word_bank 表数据统计
SELECT 
    grade,
    COUNT(*) as word_count,
    MIN(word_order) as min_order,
    MAX(word_order) as max_order
FROM word_bank
GROUP BY grade
ORDER BY grade;

-- 5. 查看指定年级的单词（示例：一年级）
SELECT * FROM word_bank WHERE grade = 'grade1' ORDER BY word_order LIMIT 10;

-- 6. 查看所有年级列表
SELECT DISTINCT grade FROM word_bank ORDER BY grade;
