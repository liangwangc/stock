-- 检查搜索功能相关的数据
-- 表中有 stock_type 字段，值为 '收盘-明日' 或 '未收盘-明日'

-- 1. 查看表结构
SHOW COLUMNS FROM stock_predictions;

-- 2. 查看 stock_type 字段的数据分布
SELECT stock_type, COUNT(*) as count
FROM stock_predictions
GROUP BY stock_type;

-- 3. 查看今天的"收盘-明日"类型预测数据
SELECT COUNT(*) as today_after_close_count
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE();

-- 4. 查看明天的"收盘-明日"类型预测数据
SELECT COUNT(*) as tomorrow_after_close_count
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = DATE_ADD(CURDATE(), INTERVAL 1 DAY);

-- 5. 查看今天的"未收盘-明日"类型预测数据
SELECT COUNT(*) as today_before_close_count
FROM stock_predictions
WHERE stock_type = '未收盘-明日'
  AND prediction_date = CURDATE();

-- 6. 查看数据示例（收盘-明日，今天的target_date）
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
  AND target_date = CURDATE()
ORDER BY prediction_time DESC
LIMIT 10;

-- 7. 测试搜索功能：搜索包含"600"的股票代码
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

-- 8. 测试搜索功能：搜索包含"茅台"的股票名称
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

-- 9. 查看最近的数据（不限制日期，看看是否有数据）
SELECT 
    symbol,
    name,
    stock_type,
    prediction_date,
    target_date,
    prediction,
    prediction_time
FROM stock_predictions
WHERE stock_type = '收盘-明日'
ORDER BY prediction_time DESC
LIMIT 20;

-- 10. 检查是否有name字段为空的情况
SELECT COUNT(*) as null_name_count
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE()
  AND (name IS NULL OR name = '' OR name = '未知');
