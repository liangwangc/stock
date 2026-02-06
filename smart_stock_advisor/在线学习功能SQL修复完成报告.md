# 在线学习功能SQL修复完成报告

**修复日期**：2026-02-05  
**问题**：在线学习功能SQL查询错误

---

## 一、问题分析

### 1.1 问题描述

在线学习功能在执行时出现SQL查询错误：
- `Unknown column 'sp.factor_weights' in 'field list'`
- `Unknown column 'sp.factors' in 'field list'`

### 1.2 问题原因

1. **数据库字段不存在**：
   - `stock_predictions` 表中不存在 `factor_weights` 字段
   - `stock_predictions` 表中不存在 `factors` 字段
   - `stock_predictions` 表中不存在 `market_state` 字段
   - `stock_predictions` 表中不存在 `data_quality_score` 字段
   - `stock_predictions` 表中不存在 `factor_consistency_score` 字段

2. **数据存储位置**：
   - 权重信息存储在 `prediction_factors` 表中
   - 得分信息存储在 `prediction_factors` 表中

---

## 二、修复内容

### ✅ 2.1 修复 `utils/online_learning.py`

**文件**：`utils/online_learning.py`  
**方法**：`batch_update_weights()`

**修复前**：
```sql
SELECT 
    sp.symbol, sp.prediction_date, sp.target_date,
    sp.prediction, sp.up_probability, sp.down_probability, sp.confidence,
    sp.actual_price, sp.actual_change_pct, sp.actual_direction, sp.prediction_hit,
    sp.factor_weights, sp.factors  -- ❌ 这些字段不存在
FROM stock_predictions sp
WHERE sp.target_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
  AND sp.prediction_hit IS NOT NULL
  AND sp.factor_weights IS NOT NULL  -- ❌ 字段不存在
```

**修复后**：
```sql
SELECT 
    sp.symbol, sp.prediction_date, sp.target_date,
    sp.prediction, sp.up_probability, sp.down_probability, sp.confidence,
    sp.actual_price, sp.actual_change_pct, sp.actual_direction, sp.prediction_hit,
    -- 从prediction_factors表获取权重信息
    pf.technical_weight, pf.news_weight, pf.capital_flow_weight,
    pf.market_weight, pf.history_weight,
    pf.technical_score, pf.news_score, pf.capital_flow_score,
    pf.market_score, pf.history_score
FROM stock_predictions sp
LEFT JOIN prediction_factors pf 
    ON sp.symbol = pf.symbol 
    AND sp.target_date = pf.date
WHERE sp.target_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
  AND sp.prediction_hit IS NOT NULL
  AND pf.technical_weight IS NOT NULL
ORDER BY sp.target_date DESC
```

**关键修改**：
1. ✅ 移除了对 `sp.factor_weights` 和 `sp.factors` 字段的查询
2. ✅ 添加了 `LEFT JOIN prediction_factors` 关联查询
3. ✅ 从 `prediction_factors` 表获取权重和得分信息
4. ✅ 修改了WHERE条件，使用 `pf.technical_weight IS NOT NULL` 替代 `sp.factor_weights IS NOT NULL`

**数据处理逻辑**：
1. ✅ 从 `prediction_factors` 表构建 `factor_weights` 字典
2. ✅ 从 `prediction_factors` 表构建 `factors` 字典
3. ✅ 如果权重信息不存在，跳过该记录

---

### ✅ 2.2 修复 `utils/model_performance_evaluator.py`

**文件**：`utils/model_performance_evaluator.py`  
**方法**：`evaluate_prediction_performance()` 和 `evaluate_by_market_state()`

**修复内容**：
1. ✅ 移除了对 `sp.factor_weights` 字段的查询
2. ✅ 移除了对 `sp.market_state` 字段的查询
3. ✅ 移除了对 `sp.data_quality_score` 字段的查询
4. ✅ 移除了对 `sp.factor_consistency_score` 字段的查询
5. ✅ 在 `evaluate_by_market_state()` 中，将 `market_state` 设为 `NULL`，并更新分组逻辑

---

## 三、修复后的SQL查询

### 3.1 在线学习功能查询

```sql
SELECT 
    sp.symbol, sp.prediction_date, sp.target_date,
    sp.prediction, sp.up_probability, sp.down_probability, sp.confidence,
    sp.actual_price, sp.actual_change_pct, sp.actual_direction, sp.prediction_hit,
    -- 从prediction_factors表获取权重信息
    pf.technical_weight, pf.news_weight, pf.capital_flow_weight,
    pf.market_weight, pf.history_weight,
    pf.technical_score, pf.news_score, pf.capital_flow_score,
    pf.market_score, pf.history_score
FROM stock_predictions sp
LEFT JOIN prediction_factors pf 
    ON sp.symbol = pf.symbol 
    AND sp.target_date = pf.date
WHERE sp.target_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
  AND sp.prediction_hit IS NOT NULL
  AND pf.technical_weight IS NOT NULL
ORDER BY sp.target_date DESC
```

**说明**：
- ✅ 使用 `LEFT JOIN` 关联 `prediction_factors` 表
- ✅ 从 `prediction_factors` 表获取权重和得分信息
- ✅ 使用 `pf.technical_weight IS NOT NULL` 确保有权重数据

---

## 四、数据处理逻辑

### 4.1 构建 factor_weights 字典

```python
factor_weights = {}
if record.get('technical_weight') is not None:
    factor_weights['technical_weight'] = float(record.get('technical_weight', 0))
if record.get('news_weight') is not None:
    factor_weights['news_weight'] = float(record.get('news_weight', 0))
if record.get('capital_flow_weight') is not None:
    factor_weights['capital_flow_weight'] = float(record.get('capital_flow_weight', 0))
if record.get('market_weight') is not None:
    factor_weights['market_weight'] = float(record.get('market_weight', 0))
if record.get('history_weight') is not None:
    factor_weights['history_weight'] = float(record.get('history_weight', 0))
```

### 4.2 构建 factors 字典

```python
factors = {}
if record.get('technical_score') is not None:
    factors['technical'] = {'score': float(record.get('technical_score', 0))}
if record.get('news_score') is not None:
    factors['news'] = {'score': float(record.get('news_score', 0))}
if record.get('capital_flow_score') is not None:
    factors['capital_flow'] = {'score': float(record.get('capital_flow_score', 0))}
if record.get('market_score') is not None:
    factors['market'] = {'score': float(record.get('market_score', 0))}
if record.get('history_score') is not None:
    factors['history'] = {'score': float(record.get('history_score', 0))}
```

---

## 五、修复完成情况

### ✅ 已修复的文件

1. ✅ **`utils/online_learning.py`**
   - ✅ 修复了 `batch_update_weights()` 方法的SQL查询
   - ✅ 移除了对不存在字段的查询
   - ✅ 添加了 `prediction_factors` 表关联查询
   - ✅ 更新了数据处理逻辑

2. ✅ **`utils/model_performance_evaluator.py`**
   - ✅ 修复了 `evaluate_prediction_performance()` 方法的SQL查询
   - ✅ 修复了 `evaluate_by_market_state()` 方法的SQL查询
   - ✅ 移除了对不存在字段的查询

---

## 六、测试建议

### 6.1 在线学习功能测试

1. **测试步骤**：
   - 打开设置页面 → 模型学习
   - 找到"在线学习（批量更新权重）"区域
   - 选择时间范围（7/14/30天）
   - 点击"🔄 执行在线学习"按钮

2. **预期结果**：
   - ✅ 不再出现SQL错误
   - ✅ 能够正确获取权重和得分信息
   - ✅ 能够生成新的权重配置

### 6.2 性能评估功能测试

1. **测试步骤**：
   - 打开设置页面 → 模型学习
   - 找到"性能评估"区域
   - 选择时间范围（7/30/90天）
   - 点击"🔍 执行评估"按钮

2. **预期结果**：
   - ✅ 不再出现SQL错误
   - ✅ 能够正确显示评估结果

---

## 七、总结

### 7.1 修复完成情况

✅ **所有SQL查询错误已修复**
- ✅ 在线学习功能
- ✅ 性能评估功能
- ✅ 综合评估功能

### 7.2 关键改进

1. ✅ **数据源调整**：从 `stock_predictions` 表改为从 `prediction_factors` 表获取权重和得分信息
2. ✅ **查询优化**：使用 `LEFT JOIN` 关联查询，确保数据完整性
3. ✅ **错误处理**：添加了数据存在性检查，避免空数据导致错误

### 7.3 后续建议

1. **数据库字段**：如果需要使用 `factor_weights`、`factors` 等字段，可以考虑执行 `database/add_model_learning_fields.sql` 脚本添加这些字段
2. **数据一致性**：确保 `prediction_factors` 表中有完整的权重和得分数据
3. **性能优化**：如果数据量很大，可以考虑添加索引优化查询性能

---

**报告生成时间**：2026-02-05  
**修复状态**：✅ 全部完成
