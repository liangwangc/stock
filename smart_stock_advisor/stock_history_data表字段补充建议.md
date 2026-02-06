# stock_history_data表字段补充建议

## 一、当前表结构分析

### 1.1 已有字段

**技术指标字段**：
- ✅ MA5, MA10, MA20, MA60（移动平均线）
- ✅ RSI（相对强弱指标）
- ✅ MACD, MACD_Signal, MACD_Hist（MACD指标）
- ✅ X2（收盘价在20日价格区间中的相对位置）

**其他字段**：
- ✅ 价格数据：open_price, close_price, high_price, low_price, pre_close
- ✅ 成交数据：volume, amount, turnover_rate, volume_ratio
- ✅ 盘口数据：outer_volume, inner_volume, bid_ask_ratio
- ✅ 资金流向：main_net_inflow, super_large_inflow, large_inflow, medium_inflow, small_inflow
- ✅ 融资融券：margin_balance, short_balance, margin_ratio

### 1.2 预测代码中使用的指标

**从 `stock_predictor.py` 分析**：
- ✅ MACD：已存储（macd, macd_signal, macd_hist）
- ✅ RSI：已存储（rsi）
- ✅ KDJ：**未存储**（代码中实时计算）
- ✅ CCI：**未存储**（代码中实时计算）
- ✅ MA：已存储（ma5, ma10, ma20, ma60）
- ❓ X2：**已存储**（x2），但预测代码中**未使用**

## 二、建议添加的字段

### 2.1 P0级（必须添加）- 预测代码中已使用但未存储

#### 1. KDJ指标 ✅ 必须添加

**原因**：
- 预测代码中已使用KDJ指标（`calculate_technical_score` 方法）
- 每次预测都需要实时计算，效率低
- 存储后可以提高预测速度

**建议字段**：
```sql
ALTER TABLE `stock_history_data` 
ADD COLUMN `kdj_k` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ K值' AFTER `macd_hist`,
ADD COLUMN `kdj_d` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ D值' AFTER `kdj_k`,
ADD COLUMN `kdj_j` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ J值' AFTER `kdj_d`;
```

**计算公式**（参考代码）：
```python
# RSV = (收盘价 - N日最低价) / (N日最高价 - N日最低价) × 100
# K = RSV的M1日指数移动平均
# D = K的M2日指数移动平均
# J = 3K - 2D
```

#### 2. CCI指标 ✅ 必须添加

**原因**：
- 预测代码中已使用CCI指标（`calculate_technical_score` 方法）
- 配置中已有 `cci_period` 设置
- 每次预测都需要实时计算

**建议字段**：
```sql
ALTER TABLE `stock_history_data` 
ADD COLUMN `cci` DECIMAL(8, 4) DEFAULT NULL COMMENT 'CCI指标' AFTER `kdj_j`;
```

**计算公式**（参考代码）：
```python
# TP = (最高价 + 最低价 + 收盘价) / 3
# CCI = (TP - TP的N日移动平均) / (0.015 × TP的N日平均绝对偏差)
```

### 2.2 P1级（建议添加）- 常用技术指标

#### 3. BOLL（布林线）指标 ✅ 建议添加

**原因**：
- 常用的技术指标，判断价格波动范围
- 有助于预测和风险控制
- 可以判断超买超卖

**建议字段**：
```sql
ALTER TABLE `stock_history_data` 
ADD COLUMN `boll_upper` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL上轨' AFTER `cci`,
ADD COLUMN `boll_middle` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL中轨（MA20）' AFTER `boll_upper`,
ADD COLUMN `boll_lower` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL下轨' AFTER `boll_middle`;
```

**计算公式**：
```python
# 中轨 = N日移动平均线（通常N=20）
# 标准差 = N日收盘价的标准差
# 上轨 = 中轨 + 2 × 标准差
# 下轨 = 中轨 - 2 × 标准差
```

### 2.3 P2级（可选添加）- 其他有用指标

#### 4. OBV（能量潮）指标 ⚠️ 可选

**原因**：
- 量价关系指标
- 有助于判断资金流向

**建议字段**：
```sql
ALTER TABLE `stock_history_data` 
ADD COLUMN `obv` DECIMAL(20, 2) DEFAULT NULL COMMENT 'OBV指标（能量潮）' AFTER `boll_lower`;
```

#### 5. ATR（平均真实波幅）指标 ⚠️ 可选

**原因**：
- 波动率指标
- 有助于风险控制

**建议字段**：
```sql
ALTER TABLE `stock_history_data` 
ADD COLUMN `atr` DECIMAL(10, 4) DEFAULT NULL COMMENT 'ATR指标（平均真实波幅）' AFTER `obv`;
```

#### 6. WR（威廉指标） ⚠️ 可选

**原因**：
- 超买超卖指标
- 类似RSI但计算方法不同

**建议字段**：
```sql
ALTER TABLE `stock_history_data` 
ADD COLUMN `wr` DECIMAL(8, 4) DEFAULT NULL COMMENT 'WR指标（威廉指标）' AFTER `atr`;
```

## 三、X2指标配置

### 3.1 当前状态

- ✅ **数据表中已有X2字段**：`stock_history_data.x2`
- ✅ **数据收集时已计算**：`stock_history_collector.py` 中已计算
- ✅ **数据存储时已保存**：`stock_history_storage.py` 中已保存
- ❌ **配置中缺少X2设置**：`INDICATOR_CONFIG` 中没有 `x2_period`
- ❌ **设置页面缺少X2配置**：技术指标参数配置中没有X2周期设置
- ❓ **预测代码中未使用**：`stock_predictor.py` 中未发现X2的使用

### 3.2 建议

**✅ 需要添加X2配置**：

1. **在 `config.py` 中添加**：
   ```python
   INDICATOR_CONFIG = {
       # ... 现有配置 ...
       "x2_period": 20  # X2指标周期（默认20日）
   }
   ```

2. **在设置页面添加**：
   - 添加X2周期配置输入框
   - 位置：技术指标参数配置区域

3. **在数据收集器中使用配置**：
   - 修改 `stock_history_collector.py` 中的X2计算
   - 使用配置中的 `x2_period` 而不是硬编码20

4. **考虑在预测中使用X2**：
   - 如果X2指标对预测有帮助，可以在 `calculate_technical_score` 中使用
   - X2可以判断价格在区间中的位置，有助于判断超买超卖

## 四、实施优先级

### P0（必须立即实施）

1. ✅ **添加KDJ字段**（K、D、J值）
   - 预测代码中已使用
   - 需要存储以提高效率

2. ✅ **添加CCI字段**
   - 预测代码中已使用
   - 需要存储以提高效率

3. ✅ **添加X2配置**
   - 数据表中已有数据
   - 需要配置以支持灵活调整

### P1（建议实施）

4. ✅ **添加BOLL字段**（上轨、中轨、下轨）
   - 常用技术指标
   - 有助于预测

### P2（可选实施）

5. ⚠️ **添加OBV字段**
6. ⚠️ **添加ATR字段**
7. ⚠️ **添加WR字段**

## 五、实施步骤

### 步骤1：添加数据库字段

**创建SQL脚本**：`database/add_missing_indicators.sql`

```sql
-- 添加KDJ指标字段
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `kdj_k` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ K值' AFTER `macd_hist`,
ADD COLUMN IF NOT EXISTS `kdj_d` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ D值' AFTER `kdj_k`,
ADD COLUMN IF NOT EXISTS `kdj_j` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ J值' AFTER `kdj_d`;

-- 添加CCI指标字段
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `cci` DECIMAL(8, 4) DEFAULT NULL COMMENT 'CCI指标' AFTER `kdj_j`;

-- 添加BOLL指标字段（可选）
ALTER TABLE `stock_history_data` 
ADD COLUMN IF NOT EXISTS `boll_upper` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL上轨' AFTER `cci`,
ADD COLUMN IF NOT EXISTS `boll_middle` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL中轨（MA20）' AFTER `boll_upper`,
ADD COLUMN IF NOT EXISTS `boll_lower` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL下轨' AFTER `boll_middle`;
```

### 步骤2：修改数据收集器

**文件**：`utils/stock_history_collector.py`

- 在 `collect_stock_daily_data` 方法中计算KDJ、CCI、BOLL
- 使用配置中的参数（如 `x2_period`）

### 步骤3：修改数据存储

**文件**：`utils/stock_history_storage.py`

- 在 `save_stock_daily_data` 方法中添加新字段到INSERT和UPDATE语句

### 步骤4：修改预测代码

**文件**：`predictor/stock_predictor.py`

- 如果数据表中已有KDJ、CCI值，优先从数据库读取
- 如果数据表中没有，再实时计算

### 步骤5：添加配置

**文件**：`config.py` 和 `templates/settings.html`

- 添加X2周期配置
- 添加BOLL参数配置（如果需要）

## 六、总结

### 6.1 参数设置与模型学习关系

- ✅ **可以调用模型学习结果**：通过"应用优化参数"功能
- ❌ **不是自动动态调整**：需要手动应用或满足自动应用条件（改进>=5%）
- ✅ **支持热更新**：应用后立即生效，无需重启服务

**建议**：
- 在参数设置页面添加"从模型学习结果加载"功能
- 显示最近的优化历史，允许用户选择应用

### 6.2 X2配置

- ✅ **需要添加**：数据表中已有X2数据，但配置中缺少
- ✅ **建议添加**：X2周期配置（当前硬编码为20日）

### 6.3 stock_history_data表字段

**必须添加**：
- ✅ KDJ（K、D、J值）- 预测代码中已使用
- ✅ CCI - 预测代码中已使用

**建议添加**：
- ✅ BOLL（上轨、中轨、下轨）- 常用技术指标

**可选添加**：
- ⚠️ OBV、ATR、WR等

---

**报告日期**：2026-01-14  
**版本**：v1.0
