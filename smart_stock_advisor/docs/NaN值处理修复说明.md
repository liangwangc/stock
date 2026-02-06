# NaN值处理修复说明

**创建日期**：2026-01-22  
**问题**：`nan can not be used with MySQL` 错误

---

## 一、问题分析

### 1.1 错误信息

```
pymysql.err.ProgrammingError: nan can not be used with MySQL
```

### 1.2 问题原因

- **pandas/numpy的NaN值**：pandas DataFrame中的NaN值（numpy.nan）不能直接用于MySQL
- **MySQL不支持NaN**：MySQL不支持NaN值，需要使用NULL
- **数据采集时产生NaN**：从API获取的数据可能包含NaN值（例如：某些字段缺失）

---

## 二、解决方案

### 2.1 添加清理函数

**代码位置**：`utils/stock_history_storage.py:22-45`

**函数**：`clean_nan_value(value)`

**功能**：
- 将pandas/numpy的NaN值转换为None（MySQL的NULL）
- 处理字符串形式的NaN
- 保持其他值不变

**实现**：
```python
def clean_nan_value(value):
    """
    清理NaN值，将NaN/None转换为None（MySQL兼容）
    """
    if value is None:
        return None
    
    # 处理pandas/numpy的NaN值
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    
    # 处理numpy的NaN值
    try:
        if isinstance(value, (float, np.floating)):
            if np.isnan(value):
                return None
    except (TypeError, ValueError):
        pass
    
    # 处理字符串形式的NaN
    if isinstance(value, str):
        if value.lower() in ['nan', 'none', '']:
            return None
    
    return value
```

---

### 2.2 应用到参数构建

**修改位置**：
1. `save_stock_daily_data()` 方法（第287-345行和第348-405行）
2. `save_stock_daily_data_batch()` 方法（第670-705行和第838-870行）

**修改内容**：
- 所有 `data.get('field_name')` 改为 `clean_nan_value(data.get('field_name'))`
- 确保所有数值字段都经过NaN清理

**示例**：
```python
# 修改前
params = (
    data.get('open_price'),
    data.get('close_price'),
    ...
)

# 修改后
params = (
    clean_nan_value(data.get('open_price')),
    clean_nan_value(data.get('close_price')),
    ...
)
```

---

## 三、修改范围

### 3.1 单条保存（save_stock_daily_data）

**实时数据参数列表**（58个字段）：
- ✅ 所有数值字段都使用 `clean_nan_value()`
- ✅ 字符串字段（name）也使用 `clean_nan_value()`
- ✅ JSON字段不需要清理（已经是字符串）

**历史数据参数列表**（41个字段）：
- ✅ 所有数值字段都使用 `clean_nan_value()`
- ✅ 字符串字段（name）也使用 `clean_nan_value()`

---

### 3.2 批量保存（save_stock_daily_data_batch）

**INSERT部分**：
- ✅ 实时数据参数列表（第670-689行）
- ✅ 历史数据参数列表（第691-705行）

**UPDATE部分**：
- ✅ 实时数据参数列表（第838-858行）
- ✅ 历史数据参数列表（第859-870行）

---

## 四、处理的字段类型

### 4.1 数值字段

- `open_price`, `close_price`, `high_price`, `low_price`
- `pre_close`, `change_amount`, `change_pct`
- `volume`, `amount`, `turnover_rate`, `volume_ratio`
- `pe_ratio`, `pb_ratio`
- `limit_up`, `limit_down`, `limit_pct`
- `amplitude`, `price_range`
- `ma5`, `ma10`, `ma20`, `ma60`
- `rsi`, `macd`, `macd_signal`, `macd_hist`
- `main_net_inflow`, `super_large_inflow`, `large_inflow`, `medium_inflow`, `small_inflow`
- `margin_balance`, `short_balance`, `margin_ratio`
- `data_quality_score`

### 4.2 字符串字段

- `name`

### 4.3 不需要清理的字段

- JSON字段（`bid_levels_json`, `ask_levels_json`等）- 已经是字符串
- 布尔字段（`is_limit_up`, `is_limit_down`, `is_valid`）- 已转换为0/1
- 固定值字段（`symbol`, `date`, `period_type`, `data_source`）

---

## 五、验证方法

### 5.1 测试清理函数

```python
from utils.stock_history_storage import clean_nan_value
import pandas as pd
import numpy as np

# 测试NaN值
assert clean_nan_value(np.nan) is None
assert clean_nan_value(pd.NA) is None
assert clean_nan_value(float('nan')) is None

# 测试正常值
assert clean_nan_value(123.45) == 123.45
assert clean_nan_value(0) == 0
assert clean_nan_value('test') == 'test'

# 测试字符串NaN
assert clean_nan_value('nan') is None
assert clean_nan_value('NaN') is None
```

---

## 六、总结

### 6.1 修复内容

- ✅ 添加 `clean_nan_value()` 函数
- ✅ 应用到所有参数构建位置
- ✅ 处理pandas/numpy的NaN值
- ✅ 处理字符串形式的NaN

### 6.2 修复效果

- ✅ 避免 `nan can not be used with MySQL` 错误
- ✅ 确保所有NaN值转换为NULL
- ✅ 保持数据完整性

---

**文档完成时间**：2026-01-22  
**状态**：✅ 修复完成
