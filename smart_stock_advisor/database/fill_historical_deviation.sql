-- 为历史数据填充偏差值
-- 执行日期：2026-01-16
-- 说明：为stock_predictions表中已有数据计算并填充偏差值字段

-- 更新偏差值字段（只更新为NULL的记录，避免覆盖已有数据）
UPDATE `stock_predictions`
SET 
    `deviation_pct` = `predicted_change_pct` - `actual_change_pct`,
    `absolute_deviation_pct` = ABS(`predicted_change_pct` - `actual_change_pct`),
    `deviation_price` = `predicted_close_price` - `actual_price`
WHERE `actual_change_pct` IS NOT NULL 
  AND `predicted_change_pct` IS NOT NULL
  AND (`deviation_pct` IS NULL OR `absolute_deviation_pct` IS NULL OR `deviation_price` IS NULL);

-- 显示更新统计
SELECT 
    COUNT(*) as total_records,
    SUM(CASE WHEN deviation_pct IS NOT NULL THEN 1 ELSE 0 END) as records_with_deviation,
    AVG(deviation_pct) as avg_deviation,
    AVG(absolute_deviation_pct) as avg_absolute_deviation,
    STDDEV(deviation_pct) as std_deviation
FROM `stock_predictions`
WHERE `actual_change_pct` IS NOT NULL 
  AND `predicted_change_pct` IS NOT NULL;
