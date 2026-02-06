# 设置页面预测API调用修复报告

## 一、问题描述

**问题**：设置页面股票预测仍然在调用API，导致连接错误：
- `获取股票信息失败: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))`
- `获取股票信息失败: 'NoneType' object has no attribute 'startswith'`
- `正在获取指数 sh000001 的数据: 20260107 至 20260127`

**要求**：设置页面预测应该**完全**不使用API，只从数据库获取数据。

## 二、问题根源

### 2.1 API调用位置

1. **`_detect_anomalies` 方法**：
   - 调用 `check_suspension()` → 调用 `get_stock_info()` → 调用API
   - 调用 `check_st_stock()` → 调用 `get_stock_info()` → 调用API

2. **市场状态识别**：
   - 调用 `get_all_market_indices()` → 调用API获取指数数据

## 三、修复方案

### 3.1 已修复：`_detect_anomalies` 方法 ✅

**修改位置**：`predictor/stock_predictor.py` 第3011-3075行

**修改内容**：
1. **从数据库获取股票名称**：
   - 添加了从 `stock_history_data` 表获取股票名称的逻辑
   - 避免了调用 `get_stock_info()` API

2. **简化停牌检查**：
   - 如果数据库中有数据，假设股票未停牌
   - 如果数据库中没有数据，也假设未停牌（避免阻止预测）

3. **ST股票检查**：
   - 使用从数据库获取的股票名称检查ST股票
   - 如果无法获取名称，尝试使用数据库方法（但可能失败）

**代码变更**：
```python
# 设置页面预测：从数据库获取股票名称，避免调用API
stock_name_from_db = None
try:
    from utils.db_connection import DatabaseConnection
    db = DatabaseConnection()
    name_sql = """
        SELECT DISTINCT name 
        FROM stock_history_data 
        WHERE symbol = %s 
        AND name IS NOT NULL 
        LIMIT 1
    """
    name_result = db.execute_query(name_sql, (symbol,))
    if name_result and len(name_result) > 0:
        stock_name_from_db = name_result[0].get('name', '')
except Exception as e:
    self.logger.debug(f"从数据库获取股票名称失败: {str(e)}")

# 1. 检查停牌（设置页面预测：简化检查，只检查数据库中的名称，不调用API）
if stock_name_from_db:
    suspension_info = {'is_suspended': False}
else:
    suspension_info = {'is_suspended': False}

# 2. 检查ST股票（设置页面预测：从数据库获取股票名称检查）
if stock_name_from_db:
    is_st = 'ST' in stock_name_from_db or '*ST' in stock_name_from_db or 'st' in stock_name_from_db.lower()
    if is_st:
        anomalies.append('st_stock')
        # ... 设置ST股票详情
```

### 3.2 待修复：市场状态识别 ⚠️

**问题位置**：`predictor/stock_predictor.py` 第3612-3627行（`predict` 方法）和第4688-4703行（`predict_before_close` 方法）

**问题**：
- 调用 `self.data_source.get_all_market_indices(days=30)` 会触发API调用

**修复方案**：
- 从数据库获取指数数据（上证指数000001）
- 如果数据库获取失败，跳过市场状态识别（不调用API）

**需要修改的代码**：
```python
# 设置页面预测：从数据库获取指数数据，不调用API
indices_data = {}
try:
    from utils.db_connection import DatabaseConnection
    import pandas as pd
    db = DatabaseConnection()
    
    # 获取上证指数（000001）最近30天的数据
    index_sql = """
        SELECT trade_date, open_price, high_price, low_price, close_price, volume
        FROM stock_history_data
        WHERE symbol = '000001'
        AND trade_date <= %s
        ORDER BY trade_date DESC
        LIMIT 30
    """
    check_date = data_date if data_date else datetime.now().strftime('%Y-%m-%d')
    index_result = db.execute_query(index_sql, (check_date,))
    
    if index_result and len(index_result) > 0:
        # 转换为DataFrame
        df_data = []
        for row in index_result:
            df_data.append({
                'date': pd.to_datetime(row['trade_date']),
                'open': float(row['open_price']) if row['open_price'] else 0,
                'high': float(row['high_price']) if row['high_price'] else 0,
                'low': float(row['low_price']) if row['low_price'] else 0,
                'close': float(row['close_price']) if row['close_price'] else 0,
                'volume': float(row['volume']) if row['volume'] else 0
            })
        
        if df_data:
            index_df = pd.DataFrame(df_data)
            index_df = index_df.set_index('date')
            index_df = index_df.sort_index()
            indices_data['000001.SH'] = index_df
            self.logger.debug(f"从数据库获取上证指数数据，共 {len(index_df)} 条记录")
except Exception as e:
    self.logger.debug(f"从数据库获取指数数据失败: {str(e)}")
    # 如果数据库获取失败，跳过市场状态识别（设置页面预测应避免调用API）
    self.logger.debug("数据库获取指数数据失败，跳过市场状态识别（设置页面预测应避免调用API）")
```

## 四、修复状态

### 4.1 已完成 ✅

1. ✅ **`_detect_anomalies` 方法**：已修改为从数据库获取股票名称，避免调用API

### 4.2 待完成 ⚠️

1. ⚠️ **市场状态识别（`predict` 方法）**：需要修改为从数据库获取指数数据
2. ⚠️ **市场状态识别（`predict_before_close` 方法）**：需要修改为从数据库获取指数数据

## 五、注意事项

1. **数据库表结构**：
   - 确保 `stock_history_data` 表中有指数数据（symbol='000001'）
   - 确保字段名称正确：`trade_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`

2. **错误处理**：
   - 如果数据库获取失败，应该跳过市场状态识别，而不是调用API
   - 使用 `debug` 级别日志记录失败信息

3. **性能考虑**：
   - 数据库查询应该使用索引（`symbol`, `trade_date`）
   - 限制查询结果数量（LIMIT 30）

## 六、测试建议

1. **测试设置页面预测**：
   - 验证不再出现API调用错误
   - 验证预测功能正常
   - 验证市场状态识别功能（如果数据库中有指数数据）

2. **测试数据库查询**：
   - 验证能够从数据库获取指数数据
   - 验证数据格式正确（DataFrame格式）

3. **测试错误处理**：
   - 验证数据库获取失败时不会调用API
   - 验证预测功能仍然正常（即使市场状态识别失败）

---

**报告创建时间**：2026-01-27  
**修复状态**：部分完成（`_detect_anomalies` 已修复，市场状态识别待修复）  
**优先级**：高（需要尽快完成市场状态识别的修复）
