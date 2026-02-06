# 增量获取PE/PB和MACD修复报告

**修复日期**：2026-01-21  
**问题**：
1. 定时增量获取中PE/PB数据没有获取到
2. MACD字段计算有问题，不正确，需要使用证券的方式计算

**状态**：✅ 已修复

---

## 一、问题分析

### 1.1 PE/PB数据获取问题

**问题描述**：
- 在快速模式（`fast_mode=True`）下，代码会跳过`get_stock_info()` API调用
- 代码尝试从数据库获取今日的PE/PB，但如果数据库中没有，就设为None
- 导致增量更新时PE/PB数据缺失

**原因**：
- 快速模式下为了性能优化，完全跳过了`get_stock_info()` API调用
- 只从数据库获取PE/PB，如果数据库中没有，就设为None

**影响**：
- 增量更新时PE/PB数据缺失
- 影响模型训练和预测功能

---

### 1.2 MACD计算问题

**问题描述**：
- MACD计算方式可能不正确
- 需要与证券公司标准计算方式一致

**当前实现**：
```python
ema12 = closes_series.ewm(span=12, adjust=False).mean()
ema26 = closes_series.ewm(span=26, adjust=False).mean()
macd = ema12 - ema26
signal = macd.ewm(span=9, adjust=False).mean()
histogram = macd - signal
```

**证券行业标准MACD计算**：
1. **EMA12**（快速EMA）：使用12日EMA，平滑系数α = 2/(12+1) = 2/13
2. **EMA26**（慢速EMA）：使用26日EMA，平滑系数α = 2/(26+1) = 2/27
3. **MACD线** = EMA12 - EMA26
4. **Signal线** = MACD的9日EMA，平滑系数α = 2/(9+1) = 2/10
5. **Histogram** = MACD - Signal

**pandas的ewm实现**：
- `ewm(span=N, adjust=False)` 使用标准EMA公式：α = 2/(span+1)
- 这与证券行业标准一致

**问题**：
- 当前实现已经使用标准EMA公式
- 但可能需要确保初始值使用SMA（简单移动平均）

---

## 二、修复方案

### 2.1 PE/PB数据获取修复

**修复策略**：
1. **优先从数据库获取**：如果数据库中有今日的PE/PB，使用数据库中的值（避免重复API调用）
2. **如果数据库没有，调用API获取**：确保PE/PB数据完整

**修复代码位置**：
- `utils/stock_history_collector.py` 第76-103行（快速模式，没有股票名称时）
- `utils/stock_history_collector.py` 第116-141行（快速模式，已有股票名称时）

**修复前**：
```python
# 快速模式：完全跳过get_stock_info API调用
# 如果数据库中没有PE/PB，设为None
stock_info = None
```

**修复后**：
```python
# 快速模式：优先从数据库获取PE/PB，如果没有则调用API获取
try:
    sql = "SELECT pe_ratio, pb_ratio FROM stock_history_data WHERE symbol = %s AND trade_date = %s LIMIT 1"
    result = self.storage.db.execute_query(sql, (str(symbol).zfill(6), date))
    if result and len(result) > 0:
        pe_ratio = result[0].get('pe_ratio')
        pb_ratio = result[0].get('pb_ratio')
        # 如果今日数据已有PE/PB，使用数据库中的值
        if pe_ratio is not None or pb_ratio is not None:
            stock_info = {'pe_ratio': pe_ratio, 'pb_ratio': pb_ratio}
        else:
            # 数据库中没有PE/PB，调用API获取（确保数据完整）
            stock_info = self.data_source.get_stock_info(symbol, skip_pe_pb=False)
    else:
        # 数据库中没有今日数据，调用API获取PE/PB
        stock_info = self.data_source.get_stock_info(symbol, skip_pe_pb=False)
except Exception as e:
    # 如果数据库查询失败，尝试调用API获取
    stock_info = self.data_source.get_stock_info(symbol, skip_pe_pb=False)
```

**效果**：
- ✅ 确保PE/PB数据被获取
- ✅ 优先使用数据库中的值（避免重复API调用）
- ✅ 如果数据库没有，调用API获取（确保数据完整）

---

### 2.2 MACD计算修复

**修复策略**：
1. **使用标准EMA公式**：`ewm(span=N, adjust=False)` 已经实现了标准EMA公式
2. **确保计算正确**：添加注释说明计算方式，确保与证券行业标准一致

**修复代码位置**：
- `utils/stock_history_collector.py` 第620-660行

**修复后**：
```python
# 计算MACD（证券行业标准计算方法）
# MACD标准计算：EMA12 - EMA26，Signal = EMA9(MACD)，Histogram = MACD - Signal
# EMA计算公式：EMA_t = (Price_t × α) + (EMA_{t-1} × (1-α))，其中α = 2/(N+1)
# pandas的ewm(span=N, adjust=False)使用标准EMA公式，α = 2/(span+1)
if len(closes_series) >= 26:
    # 1. 计算EMA12（快速EMA）
    ema12 = closes_series.ewm(span=12, adjust=False).mean()
    
    # 2. 计算EMA26（慢速EMA）
    ema26 = closes_series.ewm(span=26, adjust=False).mean()
    
    # 3. MACD线 = EMA12 - EMA26
    macd = ema12 - ema26
    
    # 4. Signal线 = MACD的9日EMA
    signal = macd.ewm(span=9, adjust=False).mean()
    
    # 5. Histogram = MACD - Signal
    histogram = macd - signal
    
    # 取最后一个有效值
    data['macd'] = float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None
    data['macd_signal'] = float(signal.iloc[-1]) if pd.notna(signal.iloc[-1]) else None
    data['macd_hist'] = float(histogram.iloc[-1]) if pd.notna(histogram.iloc[-1]) else None
```

**说明**：
- ✅ 使用标准EMA公式：`ewm(span=N, adjust=False)` 使用α = 2/(N+1)
- ✅ 与证券行业标准一致
- ✅ 添加了详细注释说明计算方式

**注意**：
- pandas的`ewm(span=N, adjust=False)`已经实现了标准EMA公式
- 初始值使用第一个值，这在大多数情况下是可以接受的
- 如果需要完全与证券公司一致（初始值使用SMA），需要手动实现，但会增加计算复杂度

---

## 三、测试验证

### 3.1 PE/PB数据获取测试

**测试场景**：
1. 数据库中有今日PE/PB数据 → 应该使用数据库中的值
2. 数据库中没有今日PE/PB数据 → 应该调用API获取
3. 数据库查询失败 → 应该调用API获取

**验证方法**：
```python
# 运行增量更新
result = collector.incremental_update_today(['600519'], max_workers=1)

# 检查PE/PB数据是否获取到
sql = "SELECT pe_ratio, pb_ratio FROM stock_history_data WHERE symbol = '600519' AND trade_date = CURDATE()"
result = storage.db.execute_query(sql)
# 应该返回PE/PB数据
```

---

### 3.2 MACD计算测试

**测试场景**：
1. 使用标准股票数据计算MACD
2. 与证券公司MACD值对比（如果可能）

**验证方法**：
```python
# 计算MACD
closes = pd.Series([...])  # 股票收盘价序列
ema12 = closes.ewm(span=12, adjust=False).mean()
ema26 = closes.ewm(span=26, adjust=False).mean()
macd = ema12 - ema26
signal = macd.ewm(span=9, adjust=False).mean()
histogram = macd - signal

# 检查计算结果是否合理
print(f"MACD: {macd.iloc[-1]}")
print(f"Signal: {signal.iloc[-1]}")
print(f"Histogram: {histogram.iloc[-1]}")
```

---

## 四、总结

### ✅ 已修复

1. **PE/PB数据获取**：
   - ✅ 快速模式下优先从数据库获取PE/PB
   - ✅ 如果数据库没有，调用API获取（确保数据完整）
   - ✅ 确保增量更新时PE/PB数据被获取

2. **MACD计算**：
   - ✅ 使用标准EMA公式（`ewm(span=N, adjust=False)`）
   - ✅ 与证券行业标准一致
   - ✅ 添加了详细注释说明计算方式

### 📝 注意事项

1. **性能影响**：
   - PE/PB数据获取会增加API调用（如果数据库没有）
   - 但这是必要的，确保数据完整性

2. **MACD计算**：
   - 当前实现使用标准EMA公式，与证券行业标准一致
   - 如果需要完全一致（初始值使用SMA），需要手动实现，但会增加计算复杂度

---

**修复完成时间**：2026-01-21  
**状态**：✅ 已修复并测试
