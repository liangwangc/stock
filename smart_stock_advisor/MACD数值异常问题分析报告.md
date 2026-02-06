# MACD数值异常问题分析报告

**问题发现时间**：2026-01-26  
**问题描述**：16号以后的MACD数值很大，16号以前的数值很小

---

## 一、问题现象

### 1.1 数据对比

通过 `check_macd_values.py` 脚本检查发现：

**15号数据（akshare）**：
- MACD最小值：0.0006
- MACD最大值：0.7833
- MACD平均值：0.1581
- MACD中位数：0.0588

**16号数据（tushare）**：
- MACD最小值：0.0000
- MACD最大值：100.0000
- MACD平均值：46.1468
- MACD中位数：45.1035

### 1.2 典型对比案例

| 股票代码 | 15号收盘价 | 15号MACD | 16号收盘价 | 16号MACD | MACD比值 | 收盘价比值 |
|---------|----------|---------|----------|---------|---------|-----------|
| 000026  | 16.60    | 0.4280  | 16.64    | 69.4444  | 162.25x  | 1.0024    |
| 000031  | 2.97     | -0.0222 | 2.92     | 66.6667  | 3003.00x | 0.9832    |
| 000034  | 41.72    | 0.5354  | 41.12    | 74.1935  | 138.58x  | 0.9856    |
| 000045  | 12.25    | 0.0036  | 12.38    | 76.5625  | 21267.36x| 1.0106    |

**关键发现**：
- ✅ 收盘价几乎相同（比值0.98-1.01），说明价格单位是一致的
- ❌ MACD值差异巨大（162倍到21267倍），说明问题不在价格本身

---

## 二、问题原因分析

### 2.1 数据源差异

- **15号及之前**：数据源是 `akshare`
- **16号及之后**：数据源是 `tushare`

### 2.2 MACD计算逻辑

MACD计算需要历史数据（至少26天）：
```python
# fetch_tushare_data_16_23.py 中的计算逻辑
def calculate_technical_indicators(self, history_df: pd.DataFrame, current_close: float):
    closes = history_df['close'].dropna()
    closes = pd.concat([closes, pd.Series([current_close])])
    
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_signal
```

### 2.3 问题根源

**假设**：AkShare返回的价格单位可能是"分"（需要除以100），而Tushare返回的是"元"。

**验证**：
1. 如果15号之前的数据价格单位是"分"（例如：1660分 = 16.60元）
2. 16号的数据价格单位是"元"（例如：16.64元）
3. 在计算16号的MACD时，使用了混合单位的历史数据：
   - 历史数据（15号及之前）：价格是"分"单位（例如：1660）
   - 当前数据（16号）：价格是"元"单位（例如：16.64）
4. MACD = EMA12 - EMA26，如果历史数据是"分"单位，当前数据是"元"单位，会导致MACD值异常放大

**但是**：从收盘价对比看，15号和16号的收盘价几乎相同（16.60 vs 16.64），说明数据库中存储的价格单位应该是一致的。

### 2.4 进一步分析

**可能的原因**：

1. **历史数据获取问题**：
   - `get_historical_data_for_indicators()` 从数据库获取历史数据
   - 如果数据库中15号之前的数据价格单位是"分"，而16号的数据价格单位是"元"
   - 在计算MACD时混合使用，会导致MACD值异常

2. **AkShare价格单位问题**：
   - 需要检查 `stock_history_collector.py` 中AkShare数据的处理
   - 看是否有价格单位转换逻辑

3. **Tushare价格单位问题**：
   - Tushare官方文档说明价格单位是"元"
   - 但需要确认实际返回的数据

---

## 三、解决方案

### 方案1：统一价格单位（推荐）

**步骤**：
1. 检查数据库中15号之前的数据价格单位
2. 如果发现价格单位不一致，统一转换为"元"
3. 重新计算16号及之后的MACD值

### 方案2：修复MACD计算逻辑

**步骤**：
1. 在 `calculate_technical_indicators()` 中，确保所有历史数据价格单位一致
2. 在计算MACD前，检查并统一价格单位

### 方案3：重新计算所有MACD值

**步骤**：
1. 统一数据库中所有价格数据单位（确保都是"元"）
2. 重新计算所有日期的MACD值

---

## 四、检查建议

### 4.1 检查价格单位

```sql
-- 检查15号之前和16号之后的价格范围
SELECT 
    CASE 
        WHEN trade_date < '2026-01-16' THEN 'before_16'
        ELSE 'after_16'
    END AS period,
    MIN(close_price) AS min_price,
    MAX(close_price) AS max_price,
    AVG(close_price) AS avg_price,
    COUNT(*) AS count
FROM stock_history_data
WHERE trade_date >= '2026-01-01' AND trade_date <= '2026-01-20'
GROUP BY period;
```

### 4.2 检查AkShare数据源

检查 `stock_history_collector.py` 中AkShare数据的处理逻辑，看是否有价格单位转换。

### 4.3 检查Tushare数据源

确认Tushare返回的价格单位确实是"元"。

---

## 五、临时解决方案

如果需要快速修复16号及之后的MACD值：

1. **方案A**：将16号及之后的MACD值除以100（如果确认是单位问题）
2. **方案B**：重新计算16号及之后的MACD值，确保使用统一单位的历史数据

---

## 六、根本解决方案

**长期方案**：
1. ✅ 统一所有数据源的价格单位（确保都是"元"）
2. ✅ 在数据入库时进行单位检查和转换
3. ✅ 在MACD计算前，验证历史数据单位一致性
4. ✅ 添加数据质量检查，防止单位不一致的问题

---

**报告完成时间**：2026-01-26
