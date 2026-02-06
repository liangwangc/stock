# update_stock_history_16_now.py 优化说明

**创建日期**：2026-01-23  
**优化内容**：按股票分组，每个股票一次性获取整个日期范围的历史数据，大幅减少API调用次数

---

## 一、优化前的问题

### 1.1 原有实现方式

**代码位置**：`scripts/update_stock_history_16_now.py`（优化前）

**问题描述**：
- 对每个股票、每个日期都调用一次 `collect_stock_daily_data(symbol, date)`
- 每个 `collect_stock_daily_data` 调用都会触发 `ak.stock_zh_a_hist` API
- **API调用次数**：股票数 × 日期数

**示例**：
- 5400只股票 × 10个日期 = **54000次API调用**
- 即使使用多线程（10线程），也需要调用54000次API
- 长时间运行会遇到API限制

---

## 二、优化方案

### 2.1 核心优化思路

**优化策略**：按股票分组，每个股票一次性获取整个日期范围的历史数据

**优化原理**：
- `ak.stock_zh_a_hist` 支持一次获取一个日期范围（例如：2026-01-16 至 2026-01-23）
- 虽然不支持批量获取多只股票，但可以一次获取一只股票的多个日期
- **API调用次数**：从 股票数 × 日期数 降低到 **股票数**

**示例**：
- 优化前：5400只股票 × 10个日期 = **54000次API调用**
- 优化后：5400只股票 × 1次调用 = **5400次API调用**
- **API调用次数减少：10倍**

---

### 2.2 实现流程

```
1. 批量查询数据库中已存在的数据
   ↓
2. 按股票分组待处理任务
   - 格式：{symbol: [date1, date2, ...]}
   ↓
3. 对每个股票，一次性获取整个日期范围的历史数据
   - 调用：get_stock_data(symbol, start_date=min_date, end_date=max_date)
   - 返回：整个日期范围的DataFrame
   ↓
4. 从返回的数据中提取需要的日期
   - 遍历需要的日期列表
   - 从DataFrame中提取对应日期的数据
   ↓
5. 一次性计算所有日期的技术指标
   - 使用talib或pandas计算整个日期范围的技术指标
   - 构建技术指标映射：{date_str: {ma5: ..., rsi: ..., ...}}
   ↓
6. 构建数据字典并添加到批量保存列表
   - 提取价格数据、成交额、涨跌幅等
   - 添加技术指标
   - 计算涨跌停价
   ↓
7. 所有数据收集完成后，批量保存到数据库
```

---

## 三、优化效果

### 3.1 API调用次数对比

| 场景 | 优化前 | 优化后 | 减少倍数 |
|------|--------|--------|---------|
| **5400只股票，10个日期** | 54000次 | 5400次 | **10倍** |
| **5400只股票，20个日期** | 108000次 | 5400次 | **20倍** |
| **5400只股票，30个日期** | 162000次 | 5400次 | **30倍** |

---

### 3.2 性能提升

**优化前**（10线程，5400只股票，10个日期）：
- API调用次数：54000次
- 预计耗时：**5-10小时**（取决于API响应速度）
- 风险：**高**（长时间运行会遇到API限制）

**优化后**（10线程，5400只股票，10个日期）：
- API调用次数：5400次
- 预计耗时：**30-60分钟**（取决于API响应速度）
- 风险：**低**（API调用次数大幅减少）

**性能提升**：**5-10倍**（取决于日期数量）

---

## 四、技术实现细节

### 4.1 按股票分组

```python
# 按股票分组待处理任务
symbol_tasks_map = {}  # {symbol: [date1, date2, ...]}
for symbol, date in pending_tasks:
    symbol_str = str(symbol).strip()
    if symbol_str not in symbol_tasks_map:
        symbol_tasks_map[symbol_str] = []
    symbol_tasks_map[symbol_str].append(date)

# 去重日期列表
for symbol_str in symbol_tasks_map:
    symbol_tasks_map[symbol_str] = sorted(list(set(symbol_tasks_map[symbol_str])))
```

---

### 4.2 一次性获取整个日期范围

```python
# 计算日期范围
min_date = min(dates)
max_date = max(dates)

# 扩展日期范围（前后各加5天，用于计算技术指标）
min_date_obj = datetime.strptime(min_date, '%Y-%m-%d') - timedelta(days=5)
max_date_obj = datetime.strptime(max_date, '%Y-%m-%d') + timedelta(days=5)
extended_start = min_date_obj.strftime('%Y-%m-%d')
extended_end = max_date_obj.strftime('%Y-%m-%d')

# 一次性获取整个日期范围的历史数据
history_df = data_source.get_stock_data(
    symbol=symbol,
    start_date=extended_start,
    end_date=extended_end,
    use_db_only=False  # 允许调用API
)
```

---

### 4.3 一次性计算技术指标

```python
# 计算技术指标（一次性计算整个日期范围，避免重复计算）
technical_data_map = {}  # {date_str: {ma5: ..., rsi: ..., ...}}

if len(history_df) >= 60 and 'close' in history_df.columns:
    closes = history_df['close']
    
    # 使用talib计算技术指标（一次性计算所有日期）
    ma5_series = pd.Series(talib.MA(closes_array, timeperiod=5), index=history_df.index)
    ma10_series = pd.Series(talib.MA(closes_array, timeperiod=10), index=history_df.index)
    ma20_series = pd.Series(talib.MA(closes_array, timeperiod=20), index=history_df.index)
    ma60_series = pd.Series(talib.MA(closes_array, timeperiod=60), index=history_df.index)
    rsi_series = pd.Series(talib.RSI(closes_array, timeperiod=14), index=history_df.index)
    macd_series, macd_signal_series, macd_hist_series = talib.MACD(...)
    
    # 构建技术指标映射
    for date_idx in history_df.index:
        date_str = date_idx.strftime('%Y-%m-%d')
        tech_data = {
            'ma5': ma5_series.loc[date_idx],
            'ma10': ma10_series.loc[date_idx],
            'ma20': ma20_series.loc[date_idx],
            'ma60': ma60_series.loc[date_idx],
            'rsi': rsi_series.loc[date_idx],
            'macd': macd_series.loc[date_idx],
            ...
        }
        technical_data_map[date_str] = tech_data
```

---

### 4.4 从历史数据中提取需要的日期

```python
# 从历史数据中提取需要的日期
for date in dates:
    date_idx = pd.to_datetime(date)
    if date_idx in history_df.index:
        target_row = history_df.loc[date_idx]
        
        # 构建数据字典
        data = {
            'symbol': symbol,
            'name': stock_name,
            'trade_date': date,
            'open_price': target_row.get('open'),
            'close_price': target_row.get('close'),
            ...
        }
        
        # 添加技术指标
        if date in technical_data_map:
            data.update(technical_data_map[date])
        
        # 添加到批量保存列表
        collected_data.append((symbol, date, data))
```

---

## 五、优化优势

### 5.1 减少API调用次数

- ✅ **大幅减少API调用**：从 股票数 × 日期数 降低到 **股票数**
- ✅ **避免API限制**：API调用次数减少10-30倍，大幅降低被限流的风险
- ✅ **提升稳定性**：减少网络请求次数，降低网络错误概率

---

### 5.2 提升处理效率

- ✅ **减少网络等待时间**：每个股票只需要1次网络请求，而不是多次
- ✅ **批量计算技术指标**：一次性计算整个日期范围的技术指标，避免重复计算
- ✅ **减少数据库查询**：股票名称只查询一次，而不是每个日期都查询

---

### 5.3 保持数据完整性

- ✅ **数据格式一致**：使用与 `collect_stock_daily_data` 相同的数据格式
- ✅ **技术指标完整**：支持MA5/MA10/MA20/MA60、RSI、MACD、X2等技术指标
- ✅ **数据字段完整**：包含价格、成交量、成交额、涨跌幅等所有字段

---

## 六、注意事项

### 6.1 API调用频率

**虽然API调用次数大幅减少，但仍需注意**：
- 5400次API调用仍然需要一定时间（约30-60分钟）
- 建议使用合理的线程数（10-20线程）
- 如果遇到API限制，可以降低线程数或添加延迟

---

### 6.2 内存占用

**批量获取历史数据会占用更多内存**：
- 每个股票的历史数据：约10-30KB（取决于日期范围）
- 5400只股票：约50-150MB内存
- 技术指标计算：约50-100MB内存
- **总内存占用**：约100-250MB（可接受）

---

### 6.3 日期范围扩展

**为了计算技术指标，会扩展日期范围**：
- 原始日期范围：2026-01-16 至 2026-01-23
- 扩展后范围：2026-01-11 至 2026-01-28（前后各加5天）
- **影响**：会获取更多数据，但可以一次性计算所有日期的技术指标

---

## 七、使用示例

### 7.1 基本使用

```bash
# 获取从2026-01-16到现在的所有股票数据
python scripts/update_stock_history_16_now.py

# 指定开始和结束日期
python scripts/update_stock_history_16_now.py --start-date 2026-01-16 --end-date 2026-01-23

# 指定股票代码
python scripts/update_stock_history_16_now.py --symbol 000001

# 指定多个股票代码
python scripts/update_stock_history_16_now.py --symbols 000001 600519 000858

# 指定线程数
python scripts/update_stock_history_16_now.py --threads 20
```

---

### 7.2 优化效果示例

**场景**：5400只股票，10个日期（2026-01-16 至 2026-01-25）

**优化前**：
- API调用次数：54000次
- 预计耗时：5-10小时
- 风险：高（API限制）

**优化后**：
- API调用次数：5400次
- 预计耗时：30-60分钟
- 风险：低（API调用次数大幅减少）

**性能提升**：**10倍**

---

## 八、总结

### 8.1 优化成果

- ✅ **API调用次数减少10-30倍**（取决于日期数量）
- ✅ **处理时间减少5-10倍**
- ✅ **避免API限制风险**
- ✅ **保持数据完整性和一致性**

### 8.2 适用场景

- ✅ **历史数据批量获取**：适合获取多个日期的历史数据
- ✅ **数据补全**：适合补全缺失的历史数据
- ✅ **定期更新**：适合定期更新历史数据

### 8.3 注意事项

- ⚠️ **API调用频率**：虽然大幅减少，但仍需注意API限制
- ⚠️ **内存占用**：批量获取会占用更多内存（约100-250MB）
- ⚠️ **日期范围扩展**：为了计算技术指标，会扩展日期范围（前后各加5天）

---

**文档完成时间**：2026-01-23  
**状态**：✅ 优化完成，已实施
