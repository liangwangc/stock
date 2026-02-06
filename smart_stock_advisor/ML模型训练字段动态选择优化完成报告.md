# ML模型训练字段动态选择优化完成报告

**日期**: 2026-01-16  
**优化内容**: 根据数据完整性动态选择训练字段

---

## 一、优化目标

### 问题

在ML模型训练中，某些字段的数据完整率很低（如资金流向字段可能只有30%的数据），但仍然被用于训练，这可能导致：
- 模型学到错误的模式
- 训练时间增加
- 模型性能下降

### 解决方案

根据字段的数据完整率自动过滤低质量字段，只保留高质量字段用于训练。

---

## 二、实现的功能

### 2.1 字段动态过滤

**文件**: `utils/ml_feature_engineering.py`  
**方法**: `prepare_features()` 和 `_filter_fields_by_completeness()`

#### 功能说明

```python
def prepare_features(self, df: pd.DataFrame, 
                    label_column: str = 'label_up',
                    exclude_columns: Optional[List[str]] = None,
                    filter_by_completeness: bool = True,  # 默认启用
                    min_completeness: float = 0.5,        # 最低完整率50%
                    critical_fields: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
```

#### 过滤规则

1. **关键字段始终保留**（即使完整率低）:
   - `close_price`, `open_price`, `high_price`, `low_price`, `volume`
   - 这些字段是预测的基础，必须保留

2. **完整率 >= 阈值（默认50%）的字段保留**:
   - 例如：`ma5`, `ma10`, `rsi` 等完整率高的字段

3. **完整率 < 阈值（默认50%）的字段移除**:
   - 例如：`main_net_inflow` 如果完整率只有30%，会被移除

#### 使用示例

```python
# 默认使用（自动过滤低质量字段）
X_train, y_train, feature_names = feature_engineering.prepare_features(
    train_df, label_column='label_up'
)

# 自定义阈值
X_train, y_train, feature_names = feature_engineering.prepare_features(
    train_df, 
    label_column='label_up',
    min_completeness=0.7  # 只保留完整率>=70%的字段
)

# 禁用过滤（使用所有字段）
X_train, y_train, feature_names = feature_engineering.prepare_features(
    train_df,
    label_column='label_up',
    filter_by_completeness=False  # 不过滤
)
```

---

## 三、实现细节

### 3.1 完整率计算

```python
def _filter_fields_by_completeness(self, 
                                  df: pd.DataFrame,
                                  feature_columns: List[str],
                                  min_completeness: float = 0.5,
                                  critical_fields: Optional[List[str]] = None) -> List[str]:
    """根据数据完整性过滤字段"""
    for col in feature_columns:
        # 计算完整率
        missing_count = df[col].isna().sum()
        completeness = 1.0 - (missing_count / len(df))
        
        # 关键字段始终保留
        if col in critical_set:
            filtered_columns.append(col)
        # 完整率>=阈值的字段保留
        elif completeness >= min_completeness:
            filtered_columns.append(col)
        # 完整率<阈值的字段移除
        else:
            removed_fields.append({'field': col, 'completeness': completeness})
```

### 3.2 日志输出

训练时会自动输出过滤信息：

```
2026-01-16 10:00:00 - INFO - 根据数据完整性过滤字段：从 50 个特征中移除了 5 个低质量字段，保留 45 个特征
2026-01-16 10:00:00 - DEBUG - 移除低质量字段: main_net_inflow(30.2%), super_large_inflow(28.5%), large_inflow(29.1%) 等5个字段
```

---

## 四、优化效果

### 4.1 预期效果

| 指标 | 优化前 | 优化后 | 改进 |
|------|--------|--------|------|
| **特征数量** | 50个（包含低质量字段） | 45个（只保留高质量字段） | ✅ 减少噪声特征 |
| **训练时间** | 基准 | 可能减少5-10% | ✅ 轻微提升 |
| **模型性能** | 基准 | 可能提升2-5% | ✅ 减少噪声影响 |
| **数据质量** | 包含低质量字段 | 只使用高质量字段 | ✅ 显著提升 |

### 4.2 实际效果

需要在实际训练中验证，但预期：
- ✅ 移除低质量字段，减少模型学到错误模式的风险
- ✅ 训练速度可能略有提升（特征数减少）
- ✅ 模型性能可能提升（减少噪声特征）

---

## 五、使用说明

### 5.1 默认行为

**默认启用字段过滤**，无需修改代码：

```python
# 自动过滤低质量字段（完整率<50%）
X_train, y_train, feature_names = feature_engineering.prepare_features(
    train_df, label_column='label_up'
)
```

### 5.2 自定义配置

**调整完整率阈值**:

```python
# 只保留完整率>=70%的字段（更严格）
X_train, y_train, feature_names = feature_engineering.prepare_features(
    train_df,
    label_column='label_up',
    min_completeness=0.7
)

# 只保留完整率>=30%的字段（更宽松）
X_train, y_train, feature_names = feature_engineering.prepare_features(
    train_df,
    label_column='label_up',
    min_completeness=0.3
)
```

**禁用字段过滤**:

```python
# 使用所有字段（不过滤）
X_train, y_train, feature_names = feature_engineering.prepare_features(
    train_df,
    label_column='label_up',
    filter_by_completeness=False
)
```

**自定义关键字段**:

```python
# 指定额外的关键字段
X_train, y_train, feature_names = feature_engineering.prepare_features(
    train_df,
    label_column='label_up',
    critical_fields=['close_price', 'open_price', 'high_price', 'low_price', 
                     'volume', 'ma5', 'ma20']  # 添加ma5和ma20为关键字段
)
```

---

## 六、与数据质量检查的集成

### 6.1 自动集成

字段过滤功能与之前实现的 `check_training_data_quality()` 方法配合使用：

1. **数据加载时**: 自动检查数据质量
2. **特征准备时**: 根据完整率自动过滤字段

### 6.2 完整流程

```python
# 1. 加载数据
train_df = data_loader.load_training_data_from_history(...)

# 2. 检查数据质量（自动执行）
quality_report = data_loader.check_training_data_quality(train_df)
# 输出: 字段 main_net_inflow 完整率仅 30.00%，低于阈值 50.00%

# 3. 准备特征（自动过滤低质量字段）
X_train, y_train, feature_names = feature_engineering.prepare_features(train_df)
# 输出: 根据数据完整性过滤字段：从 50 个特征中移除了 5 个低质量字段，保留 45 个特征
```

---

## 七、验证方法

### 7.1 运行训练脚本

```bash
py scripts/train_base_model.py \
  --train-start 2021-01-01 \
  --train-end 2024-12-31 \
  --val-start 2025-01-01 \
  --val-end 2025-06-30
```

### 7.2 查看日志输出

训练时会自动输出：
- 数据质量检查结果
- 字段过滤信息
- 最终使用的特征数量

### 7.3 对比优化前后

- **优化前**: 使用所有50个特征
- **优化后**: 只使用高质量特征（如45个）
- **对比**: 模型性能和训练时间

---

## 八、配置建议

### 8.1 推荐配置

**生产环境**:
```python
# 使用默认配置（完整率>=50%）
filter_by_completeness=True,
min_completeness=0.5
```

**严格模式**:
```python
# 只保留完整率>=70%的字段
filter_by_completeness=True,
min_completeness=0.7
```

**宽松模式**:
```python
# 保留完整率>=30%的字段
filter_by_completeness=True,
min_completeness=0.3
```

### 8.2 关键字段建议

**默认关键字段**（始终保留）:
- `close_price`, `open_price`, `high_price`, `low_price`, `volume`

**可选关键字段**（根据需求添加）:
- `ma5`, `ma20` - 如果这些指标对预测很重要
- `rsi` - 如果RSI是核心指标

---

## 九、总结

### ✅ 已完成

1. **实现字段动态过滤功能** - 根据数据完整率自动过滤低质量字段
2. **集成到特征准备流程** - 默认启用，无需修改调用代码
3. **支持自定义配置** - 可以调整阈值和关键字段
4. **完善的日志输出** - 清晰显示过滤结果

### 📊 预期效果

- ✅ **减少噪声特征** - 自动移除低质量字段
- ✅ **提升模型性能** - 减少模型学到错误模式的风险
- ✅ **优化训练效率** - 特征数减少，训练可能更快

### 🔄 下一步

1. 运行训练脚本验证效果
2. 对比优化前后的模型性能
3. 根据实际效果调整阈值配置

---

**优化完成时间**: 2026-01-16  
**状态**: ✅ 已完成并集成到训练流程
