-- 诊断搜索功能数据的SQL脚本
-- 用于排查主页搜索股票没有数据的问题

-- ============================================
-- 1. 检查表结构和字段
-- ============================================
-- 查看表结构
SHOW COLUMNS FROM stock_predictions;

-- 检查是否有 stock_type 字段
SELECT COUNT(*) as has_stock_type
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'stock_predictions' 
  AND COLUMN_NAME = 'stock_type';

-- ============================================
-- 2. 检查数据总量
-- ============================================
-- 查看总记录数
SELECT COUNT(*) as total_count FROM stock_predictions;

-- 查看 stock_type 字段的数据分布
SELECT stock_type, COUNT(*) as count
FROM stock_predictions
GROUP BY stock_type;

-- ============================================
-- 3. 检查"收盘-明日"类型的数据
-- ============================================
-- 查看"收盘-明日"类型的总记录数
SELECT COUNT(*) as after_close_total
FROM stock_predictions
WHERE stock_type = '收盘-明日';

-- 查看今天的"收盘-明日"类型数据
SELECT COUNT(*) as today_after_close_count
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE();

-- 查看明天的"收盘-明日"类型数据
SELECT COUNT(*) as tomorrow_after_close_count
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = DATE_ADD(CURDATE(), INTERVAL 1 DAY);

-- 查看最近7天的"收盘-明日"类型数据分布
SELECT 
    target_date,
    COUNT(*) as count
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY target_date
ORDER BY target_date DESC;

-- ============================================
-- 4. 查看数据示例（不限制日期）
-- ============================================
-- 查看最近20条"收盘-明日"类型的数据
SELECT 
    id,
    symbol,
    name,
    stock_type,
    prediction_date,
    target_date,
    prediction,
    confidence,
    prediction_time
FROM stock_predictions
WHERE stock_type = '收盘-明日'
ORDER BY prediction_time DESC
LIMIT 20;

-- ============================================
-- 5. 检查 symbol 和 name 字段
-- ============================================
-- 查看 symbol 和 name 字段的情况
SELECT 
    COUNT(*) as total,
    COUNT(symbol) as has_symbol,
    COUNT(name) as has_name,
    COUNT(CASE WHEN symbol IS NULL OR symbol = '' THEN 1 END) as null_symbol,
    COUNT(CASE WHEN name IS NULL OR name = '' OR name = '未知' THEN 1 END) as null_name
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE();

-- 查看 symbol 和 name 的示例值
SELECT 
    symbol,
    name,
    LENGTH(symbol) as symbol_len,
    LENGTH(name) as name_len,
    target_date
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE()
LIMIT 10;

-- ============================================
-- 6. 测试搜索功能（模拟代码逻辑）
-- ============================================
-- 测试搜索：搜索包含"600"的股票代码
SELECT 
    symbol,
    name,
    stock_type,
    target_date,
    prediction
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE()
  AND (symbol LIKE '%600%' OR name LIKE '%600%')
ORDER BY prediction_time DESC
LIMIT 10;

-- 测试搜索：搜索包含"茅台"的股票名称
SELECT 
    symbol,
    name,
    stock_type,
    target_date,
    prediction
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE()
  AND (symbol LIKE '%茅台%' OR name LIKE '%茅台%')
ORDER BY prediction_time DESC
LIMIT 10;

-- ============================================
-- 7. 检查去重逻辑相关的字段
-- ============================================
-- 查看是否有重复的 symbol（同一 target_date）
SELECT 
    symbol,
    target_date,
    COUNT(*) as count,
    GROUP_CONCAT(prediction_time ORDER BY prediction_time DESC SEPARATOR ', ') as prediction_times
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE()
GROUP BY symbol, target_date
HAVING count > 1
LIMIT 10;

-- ============================================
-- 8. 检查 prediction_time 字段
-- ============================================
-- 查看 prediction_time 字段的情况
SELECT 
    COUNT(*) as total,
    COUNT(prediction_time) as has_prediction_time,
    MIN(prediction_time) as min_time,
    MAX(prediction_time) as max_time
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE();

-- ============================================
-- 9. 完整的数据检查（模拟实际查询）
-- ============================================
-- 模拟 get_predictions 的查询（不限制日期）
SELECT 
    COUNT(*) as total_records
FROM stock_predictions
WHERE stock_type = '收盘-明日' AND stock_type IS NOT NULL;

-- 模拟过滤 target_date 后的记录数
SELECT 
    COUNT(*) as filtered_records
FROM stock_predictions
WHERE stock_type = '收盘-明日' AND stock_type IS NOT NULL
  AND target_date = CURDATE();

-- 模拟去重后的记录数（每个symbol只保留最新的）
SELECT 
    COUNT(DISTINCT symbol) as unique_symbols
FROM stock_predictions
WHERE stock_type = '收盘-明日' AND stock_type IS NOT NULL
  AND target_date = CURDATE()
  AND symbol IS NOT NULL AND symbol != '';
