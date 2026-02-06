# 查询股票预测数据的正确SQL

## 一、问题说明

如果遇到 `Unknown column 'prediction_type'` 错误，说明表中可能使用的是 `stock_type` 字段而不是 `prediction_type` 字段。

## 二、检查表结构

首先检查表中有哪些字段：

```sql
-- 查看表结构
SHOW COLUMNS FROM stock_predictions;

-- 或者
DESC stock_predictions;
```

## 三、正确的查询语句

### 情况1：如果表中有 `stock_type` 字段

```sql
-- 查询今天的"收盘-明日"类型预测数据
SELECT COUNT(*) 
FROM stock_predictions 
WHERE stock_type = '收盘-明日' 
  AND target_date = CURDATE();

-- 查询今天的"未收盘-明日"类型预测数据
SELECT COUNT(*) 
FROM stock_predictions 
WHERE stock_type = '未收盘-明日' 
  AND target_date = CURDATE();

-- 查看数据示例
SELECT 
    id,
    symbol,
    name,
    stock_type,
    prediction_date,
    target_date,
    prediction,
    confidence
FROM stock_predictions
WHERE stock_type = '收盘-明日'
  AND target_date = CURDATE()
ORDER BY prediction_time DESC
LIMIT 10;
```

### 情况2：如果表中有 `prediction_type` 字段

```sql
-- 查询今天的"收盘-明日"类型预测数据
SELECT COUNT(*) 
FROM stock_predictions 
WHERE prediction_type = 'after_close' 
  AND target_date = CURDATE();

-- 查询今天的"未收盘-明日"类型预测数据
SELECT COUNT(*) 
FROM stock_predictions 
WHERE prediction_type = 'before_close' 
  AND target_date = CURDATE();

-- 查看数据示例
SELECT 
    id,
    symbol,
    name,
    prediction_type,
    prediction_date,
    target_date,
    prediction,
    confidence
FROM stock_predictions
WHERE prediction_type = 'after_close'
  AND target_date = CURDATE()
ORDER BY prediction_time DESC
LIMIT 10;
```

### 情况3：如果表中没有类型字段（旧版本）

```sql
-- 查询今天的预测数据（不区分类型）
SELECT COUNT(*) 
FROM stock_predictions 
WHERE target_date = CURDATE();

-- 查看数据示例
SELECT 
    id,
    symbol,
    name,
    prediction_date,
    target_date,
    prediction,
    confidence
FROM stock_predictions
WHERE target_date = CURDATE()
ORDER BY prediction_time DESC
LIMIT 10;
```

## 四、添加字段（如果需要）

### 添加 `prediction_type` 字段

```sql
-- 检查字段是否存在
SELECT COUNT(*) as has_field
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'stock_predictions' 
  AND COLUMN_NAME = 'prediction_type';

-- 如果不存在，添加字段
ALTER TABLE `stock_predictions` 
ADD COLUMN `prediction_type` VARCHAR(20) DEFAULT 'after_close' 
COMMENT '预测类型（after_close=收盘-明日，before_close=未收盘-明天）' 
AFTER `target_date`;

-- 添加索引
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_prediction_type` (`prediction_type`);

-- 为现有数据设置默认值（如果有数据）
UPDATE stock_predictions 
SET prediction_type = 'after_close' 
WHERE prediction_type IS NULL;
```

### 添加 `stock_type` 字段（如果使用stock_type）

```sql
-- 检查字段是否存在
SELECT COUNT(*) as has_field
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'stock_predictions' 
  AND COLUMN_NAME = 'stock_type';

-- 如果不存在，添加字段
ALTER TABLE `stock_predictions` 
ADD COLUMN `stock_type` VARCHAR(20) DEFAULT '收盘-明日' 
COMMENT '股票类型（收盘-明日/未收盘-明日）' 
AFTER `target_date`;

-- 添加索引
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_stock_type` (`stock_type`);

-- 为现有数据设置默认值（如果有数据）
UPDATE stock_predictions 
SET stock_type = '收盘-明日' 
WHERE stock_type IS NULL;
```

## 五、字段映射关系

| prediction_type | stock_type |
|----------------|------------|
| `after_close` | `收盘-明日` |
| `before_close` | `未收盘-明日` |

## 六、快速检查脚本

执行以下SQL快速检查：

```sql
-- 1. 检查字段
SELECT 
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
          AND TABLE_NAME = 'stock_predictions' 
          AND COLUMN_NAME = 'prediction_type'
    ) THEN '有 prediction_type 字段' ELSE '没有 prediction_type 字段' END as prediction_type_status,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
          AND TABLE_NAME = 'stock_predictions' 
          AND COLUMN_NAME = 'stock_type'
    ) THEN '有 stock_type 字段' ELSE '没有 stock_type 字段' END as stock_type_status;

-- 2. 查看数据总数
SELECT COUNT(*) as total_count FROM stock_predictions;

-- 3. 查看今天的数据（不区分类型）
SELECT COUNT(*) as today_count 
FROM stock_predictions 
WHERE target_date = CURDATE();

-- 4. 查看明天的数据（不区分类型）
SELECT COUNT(*) as tomorrow_count 
FROM stock_predictions 
WHERE target_date = DATE_ADD(CURDATE(), INTERVAL 1 DAY);
```
