# ML模型训练字段使用分析与优化建议

**日期**: 2026-01-16  
**检查范围**: `stock_history_data` 表中ML训练使用的33个字段

---

## 一、检查结果概述

### 1.1 数据规模

- **总记录数**: 约 9,803,264 条（近1000万条）
- **字段数量**: 33个ML训练字段
- **检查方法**: 统计每个字段的非NULL记录数和完整率

---

## 二、字段分类与数据完整性

### 2.1 基础价格字段（7个）- ✅ 完整度高

| 字段名 | 完整率 | 说明 |
|--------|--------|------|
| `close_price` | 100% | 收盘价（关键字段）|
| `open_price` | 100% | 开盘价（关键字段）|
| `high_price` | 100% | 最高价（关键字段）|
| `low_price` | 100% | 最低价（关键字段）|
| `pre_close` | ~99.97% | 昨收价（极少数缺失）|
| `change_pct` | ~99.97% | 涨跌幅（部分为0）|
| `change_amount` | ~99.97% | 涨跌额（部分为0）|

**状态**: ✅ **全部可用，数据完整**

---

### 2.2 成交字段（4个）- ✅ 完整度较高

| 字段名 | 完整率 | 说明 |
|--------|--------|------|
| `volume` | 100% | 成交量（关键字段）|
| `amount` | ~99%+ | 成交额（部分可能缺失）|
| `turnover_rate` | ~90-99% | 换手率（部分缺失）|
| `volume_ratio` | ~90-99% | 量比（部分缺失）|

**状态**: ✅ **大部分可用，少量缺失可通过计算补充**

---

### 2.3 技术指标字段（9个）- ⚠️ 需要检查

| 字段名 | 完整率 | 说明 |
|--------|--------|------|
| `ma5` | 待确认 | 5日均线（需历史数据计算）|
| `ma10` | 待确认 | 10日均线（需历史数据计算）|
| `ma20` | 待确认 | 20日均线（需历史数据计算）|
| `ma60` | 待确认 | 60日均线（需历史数据计算）|
| `rsi` | 待确认 | RSI指标（需历史数据计算）|
| `macd` | 待确认 | MACD指标（需历史数据计算）|
| `macd_signal` | 待确认 | MACD信号线（需历史数据计算）|
| `macd_hist` | 待确认 | MACD柱状图（需历史数据计算）|
| `x2` | 待确认 | 自定义指标（需历史数据计算）|

**状态**: ⚠️ **依赖历史数据，早期数据可能缺失**

**问题分析**:
- 技术指标需要足够的历史数据才能计算（如MA60需要60天历史数据）
- 如果某只股票的历史数据不足，这些字段会为NULL
- 当前代码中使用0.0或50.0作为默认值可能不合理

---

### 2.4 资金流向字段（5个）- ❌ 可能缺失严重

| 字段名 | 完整率 | 说明 |
|--------|--------|------|
| `main_net_inflow` | 待确认 | 主力净流入 |
| `super_large_inflow` | 待确认 | 超大单流入 |
| `large_inflow` | 待确认 | 大单流入 |
| `medium_inflow` | 待确认 | 中单流入 |
| `small_inflow` | 待确认 | 小单流入 |

**状态**: ❌ **历史数据可能缺失严重**

**问题分析**:
- 资金流向数据是实时数据，历史数据可能无法获取
- 如果增量更新时没有获取这些数据，字段会为NULL
- 使用0.0作为默认值会导致模型学到错误的特征

---

### 2.5 估值字段（4个）- ⚠️ 部分缺失

| 字段名 | 完整率 | 说明 |
|--------|--------|------|
| `pe_ratio` | 待确认 | 市盈率（PE）|
| `pb_ratio` | 待确认 | 市净率（PB）|
| `total_market_cap` | 待确认 | 总市值 |
| `float_market_cap` | 待确认 | 流通市值 |

**状态**: ⚠️ **部分股票可能缺失（如ST股票、停牌股票）**

**问题分析**:
- PE/PB等估值指标在某些情况下可能无法计算（如亏损股、停牌股）
- 使用0.0作为默认值不合理（应该使用中位数或其他统计值）

---

### 2.6 融资融券字段（3个）- ⚠️ 部分缺失

| 字段名 | 完整率 | 说明 |
|--------|--------|------|
| `margin_balance` | 待确认 | 融资余额 |
| `short_balance` | 待确认 | 融券余额 |
| `margin_ratio` | 待确认 | 融资融券比例 |

**状态**: ⚠️ **部分股票不支持融资融券**

**问题分析**:
- 并非所有股票都支持融资融券（如科创板、创业板部分股票）
- 使用0.0作为默认值可能合理（表示不支持）

---

## 三、当前训练逻辑问题分析

### 3.1 问题1：缺失值处理不合理 ❌

**当前实现**（`ml_data_loader.py` 第195-236行）:
```python
# 对于缺失字段，直接使用0.0或50.0
features['ma5'] = float(latest.get('ma5', 0)) if latest.get('ma5') else 0.0
features['rsi'] = float(latest.get('rsi', 50)) if latest.get('rsi') else 50.0
features['pe_ratio'] = float(latest.get('pe_ratio', 0)) if latest.get('pe_ratio') else 0.0
features['main_net_inflow'] = float(latest.get('main_net_inflow', 0)) if latest.get('main_net_inflow') else 0.0
```

**问题**:
1. **技术指标**: 使用0.0不合理，应该标记为缺失或使用前值
2. **资金流向**: 使用0.0会误导模型（0表示净流入为0，但NULL表示数据不可用）
3. **估值指标**: 使用0.0不合理（0 PE/PB表示特殊状态，但NULL表示数据不可用）

---

### 3.2 问题2：未区分"数据为0"和"数据缺失" ❌

**问题**:
- 数据库中的NULL值表示数据缺失
- 数据库中的0值可能表示真实值为0（如涨跌幅为0）
- 当前代码无法区分这两种情况

**影响**:
- 模型可能学到错误的模式
- 缺失值被当作0，降低了特征的信息量

---

### 3.3 问题3：字段选择未考虑数据完整性 ❌

**当前实现**（`ml_data_loader.py` 第371-393行）:
```python
# SQL查询中包含了所有33个字段，无论是否有数据
SELECT symbol, trade_date, close_price, ..., main_net_inflow, ..., pe_ratio, ...
FROM stock_history_data
```

**问题**:
- 即使某些字段数据缺失严重（如资金流向），仍然会被用于训练
- 没有根据数据完整性动态选择字段

---

### 3.4 问题4：特征工程中的缺失值处理简单 ❌

**当前实现**（`ml_feature_engineering.py` 第73-95行）:
```python
def _handle_missing_values(self, X: pd.DataFrame, method: str = 'fill') -> pd.DataFrame:
    if method == 'fill':
        # 数值列：用0填充
        numeric_columns = X.select_dtypes(include=[np.number]).columns
        X[numeric_columns] = X[numeric_columns].fillna(0)
```

**问题**:
- 所有缺失值都用0填充，不够智能
- 应该考虑字段的实际含义和缺失原因

---

## 四、优化建议

### 4.1 建议1：改进缺失值处理策略 ✅

#### 方案A：使用缺失值标记

```python
# 1. 添加缺失值标记特征
if latest.get('ma5') is None:
    features['ma5'] = 0.0  # 或使用中位数
    features['ma5_missing'] = 1  # 标记缺失
else:
    features['ma5'] = float(latest.get('ma5'))
    features['ma5_missing'] = 0
```

#### 方案B：使用前值填充（技术指标）

```python
# 技术指标可以使用前值（如果历史数据存在）
if latest.get('ma5') is None:
    # 尝试使用前几天的值
    for prev_record in reversed(history_records[:-1]):
        if prev_record.get('ma5'):
            features['ma5'] = float(prev_record.get('ma5'))
            break
    else:
        features['ma5'] = 0.0  # 如果都没有，使用0
```

#### 方案C：使用统计值填充（估值指标）

```python
# 估值指标使用中位数或分位数填充
if latest.get('pe_ratio') is None:
    # 计算该股票历史PE的中位数
    pe_values = [r.get('pe_ratio') for r in history_records if r.get('pe_ratio')]
    if pe_values:
        features['pe_ratio'] = np.median(pe_values)
    else:
        features['pe_ratio'] = 0.0  # 或使用市场平均值
```

---

### 4.2 建议2：根据数据完整性动态选择字段 ✅

```python
def _select_fields_by_completeness(self, df: pd.DataFrame, min_completeness: float = 0.5) -> List[str]:
    """根据数据完整性选择字段"""
    field_completeness = {}
    for col in df.columns:
        non_null_count = df[col].notna().sum()
        completeness = non_null_count / len(df) if len(df) > 0 else 0
        field_completeness[col] = completeness
    
    # 只选择完整率>=min_completeness的字段
    selected_fields = [
        col for col, completeness in field_completeness.items()
        if completeness >= min_completeness or col in CRITICAL_FIELDS
    ]
    
    return selected_fields
```

---

### 4.3 建议3：改进特征工程中的缺失值处理 ✅

```python
def _handle_missing_values(self, X: pd.DataFrame, method: str = 'smart_fill') -> pd.DataFrame:
    """智能处理缺失值"""
    if method == 'smart_fill':
        for col in X.columns:
            if X[col].isna().sum() > 0:
                # 根据字段类型选择填充策略
                if col in ['ma5', 'ma10', 'ma20', 'ma60']:
                    # 技术指标：使用前值
                    X[col] = X[col].fillna(method='ffill').fillna(method='bfill').fillna(0)
                elif col in ['rsi', 'macd', 'macd_signal', 'macd_hist', 'x2']:
                    # 技术指标：使用中位数
                    median_val = X[col].median()
                    if pd.notna(median_val):
                        X[col] = X[col].fillna(median_val)
                    else:
                        X[col] = X[col].fillna(50 if 'rsi' in col or 'x2' in col else 0)
                elif col in ['pe_ratio', 'pb_ratio']:
                    # 估值指标：使用中位数（排除0值）
                    non_zero_values = X[col][X[col] > 0]
                    if len(non_zero_values) > 0:
                        median_val = non_zero_values.median()
                        X[col] = X[col].fillna(median_val)
                    else:
                        X[col] = X[col].fillna(0)
                elif col in ['main_net_inflow', 'super_large_inflow', ...]:
                    # 资金流向：使用0（缺失表示无数据）
                    X[col] = X[col].fillna(0)
                else:
                    # 其他字段：使用0
                    X[col] = X[col].fillna(0)
    elif method == 'fill':
        # 原有逻辑
        X = X.fillna(0)
    
    return X
```

---

### 4.4 建议4：在SQL查询中过滤缺失字段 ✅

```python
# 在SQL查询时，只查询有数据的字段
# 或者使用COALESCE设置合理的默认值
sql = """
    SELECT 
        symbol, trade_date,
        COALESCE(ma5, 0) as ma5,
        COALESCE(rsi, 50) as rsi,
        COALESCE(pe_ratio, 
            (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pe_ratio) 
             FROM stock_history_data WHERE pe_ratio > 0)
        ) as pe_ratio,
        ...
    FROM stock_history_data
    ...
"""
```

---

### 4.5 建议5：添加数据质量检查 ✅

```python
def check_training_data_quality(self, df: pd.DataFrame) -> Dict:
    """检查训练数据质量"""
    quality_report = {
        'total_samples': len(df),
        'missing_fields': {},
        'low_quality_fields': [],
        'warnings': []
    }
    
    # 检查每个字段的缺失率
    for col in df.columns:
        missing_rate = df[col].isna().sum() / len(df)
        quality_report['missing_fields'][col] = missing_rate
        
        if missing_rate > 0.5:
            quality_report['low_quality_fields'].append(col)
            quality_report['warnings'].append(
                f"字段 {col} 缺失率 {missing_rate:.2%}，建议检查"
            )
    
    return quality_report
```

---

## 五、实施优先级

### 高优先级（必须修复）

1. ✅ **修复缺失值处理逻辑**（建议4.1）- 影响模型准确性
2. ✅ **添加数据完整性检查**（建议4.5）- 了解数据质量

### 中优先级（建议实施）

3. ⚠️ **改进特征工程中的缺失值处理**（建议4.3）- 提升模型质量
4. ⚠️ **根据数据完整性动态选择字段**（建议4.2）- 优化特征选择

### 低优先级（可选）

5. ⚠️ **在SQL查询中过滤缺失字段**（建议4.4）- 减少数据传输

---

## 六、验证方法

### 6.1 运行数据完整性检查

```bash
py scripts/check_ml_training_fields.py
```

### 6.2 检查训练数据质量

在训练前添加质量检查：
```python
quality_report = data_loader.check_training_data_quality(train_df)
logger.info(f"数据质量报告: {quality_report}")
```

### 6.3 对比优化前后模型性能

- 记录优化前的模型准确率
- 实施优化后重新训练
- 对比模型性能提升

---

## 七、总结

### 当前状态

- ✅ 基础价格字段：数据完整，可用
- ✅ 成交字段：数据较完整，可用
- ⚠️ 技术指标字段：依赖历史数据，早期数据可能缺失
- ❌ 资金流向字段：历史数据可能缺失严重
- ⚠️ 估值字段：部分股票缺失
- ⚠️ 融资融券字段：部分股票不支持

### 主要问题

1. **缺失值处理不合理**：使用0填充所有缺失值
2. **未区分"0值"和"缺失值"**
3. **字段选择未考虑数据完整性**
4. **特征工程中的缺失值处理过于简单**

### 建议行动

1. 立即修复缺失值处理逻辑
2. 添加数据质量检查
3. 根据字段完整率动态选择特征
4. 改进特征工程中的缺失值处理策略

---

**下一步**: 实施高优先级优化，重新训练模型并对比性能提升。
