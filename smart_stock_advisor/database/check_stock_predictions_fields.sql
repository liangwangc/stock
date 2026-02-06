-- 检查 stock_predictions 表的字段结构

-- 1. 查看表结构
SHOW COLUMNS FROM stock_predictions;

-- 2. 检查是否有 prediction_type 字段
SELECT COUNT(*) as has_prediction_type
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'stock_predictions' 
  AND COLUMN_NAME = 'prediction_type';

-- 3. 检查是否有 stock_type 字段
SELECT COUNT(*) as has_stock_type
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'stock_predictions' 
  AND COLUMN_NAME = 'stock_type';

-- 4. 查看数据示例（不区分类型）
SELECT 
    id,
    symbol,
    name,
    prediction_date,
    target_date,
    prediction_time,
    prediction,
    confidence
FROM stock_predictions
ORDER BY prediction_time DESC
LIMIT 10;

-- 5. 如果有 stock_type 字段，查看不同类型的数据分布
-- SELECT stock_type, COUNT(*) as count
-- FROM stock_predictions
-- GROUP BY stock_type;

-- 6. 如果有 prediction_type 字段，查看不同类型的数据分布
-- SELECT prediction_type, COUNT(*) as count
-- FROM stock_predictions
-- GROUP BY prediction_type;

-- 7. 查看今天的预测数据（不区分类型）
SELECT COUNT(*) as today_count
FROM stock_predictions
WHERE target_date = CURDATE();

-- 8. 查看明天的预测数据（不区分类型）
SELECT COUNT(*) as tomorrow_count
FROM stock_predictions
WHERE target_date = DATE_ADD(CURDATE(), INTERVAL 1 DAY);
