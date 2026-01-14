# 美股period_type字段修复说明

## 修复内容

### 步骤1：在SQL INSERT语句的字段列表中添加period_type

**文件**：`utils/us_stock_storage.py`

**位置**：`save_stock_history`方法的SQL语句

**修改**：在`trade_date`字段之后添加`period_type`字段

```python
# 修改前
(symbol, name, trade_date, exchange,
 ...

# 修改后
(symbol, name, trade_date, period_type, exchange,
 ...
```

### 步骤2：在SQL VALUES占位符中添加period_type

**修改**：在VALUES子句中添加一个`%s`占位符（在trade_date之后）

```python
# 修改前
VALUES (%s, %s, %s, %s, ...)  # 第3个是trade_date，第4个是exchange

# 修改后
VALUES (%s, %s, %s, %s, %s, ...)  # 第3个是trade_date，第4个是period_type，第5个是exchange
```

### 步骤3：在ON DUPLICATE KEY UPDATE中添加period_type

**修改**：在ON DUPLICATE KEY UPDATE子句中添加period_type的更新

```python
# 修改前
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    exchange = VALUES(exchange),
    ...

# 修改后
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    period_type = VALUES(period_type),
    exchange = VALUES(exchange),
    ...
```

### 步骤4：在参数列表中添加period_type参数

**文件**：`utils/us_stock_storage.py`

**位置**：`save_stock_history`方法的params元组

**修改**：在trade_date参数之后添加period_type参数

```python
# 修改前
params = (
    symbol,
    data.get('name'),
    trade_date,
    data.get('exchange'),
    ...

# 修改后
period_type = data.get('period_type', 'daily')  # 默认为'daily'

params = (
    symbol,
    data.get('name'),
    trade_date,
    period_type,  # 新增
    data.get('exchange'),
    ...
```

### 步骤5：在数据收集器中添加period_type字段

**文件**：`utils/us_stock_collector.py`

**位置**：`collect_stock_history`方法中准备数据的字典

**修改**：在data字典中添加period_type字段

```python
# 修改前
data = {
    'name': stock_info.get('name_en') if stock_info else symbol,
    'exchange': stock_info.get('exchange') if stock_info else None,
    ...

# 修改后
data = {
    'name': stock_info.get('name_en') if stock_info else symbol,
    'period_type': 'daily',  # 默认为日线数据
    'exchange': stock_info.get('exchange') if stock_info else None,
    ...
```

## 验证

1. ✅ 语法检查通过
2. ⏳ 等待API限流解除后进行实际数据保存测试

## 总结

已成功修复美股数据存储中缺少`period_type`字段的问题，修复方式与A股数据存储的修复方式一致。现在：

- SQL字段列表包含period_type
- SQL占位符数量匹配参数数量
- 数据字典中包含period_type字段（默认为'daily'）
- ON DUPLICATE KEY UPDATE包含period_type的更新

修复完成！等待API限流解除后即可进行实际测试。
