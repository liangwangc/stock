# 模型优化JSON序列化修复说明

**日期**：2026-01-16  
**问题**：保存优化历史时，`date` 对象无法被JSON序列化

---

## 一、问题描述

在执行模型参数优化时，保存优化历史到数据库时出现错误：

```
TypeError: Object of type date is not JSON serializable
```

**错误位置**：`utils/model_optimizer.py` 的 `_save_optimization_history` 方法

**原因**：
- `backtest_result` 字典中包含 `date` 和 `datetime` 对象
- 这些对象无法直接被 `json.dumps()` 序列化
- 特别是 `trades` 和 `daily_values` 列表中的 `date` 字段

---

## 二、修复方案

### 2.1 添加转换函数

创建了两个辅助函数来处理序列化：

1. **`_convert_to_serializable(obj)`**
   - 递归地将对象中的 `date` 和 `datetime` 转换为字符串
   - 支持字典、列表、元组、集合等嵌套结构
   - 使用 `isoformat()` 方法转换为ISO格式字符串

2. **`_safe_json_dumps(obj, ensure_ascii=False)`**
   - 安全地将对象转换为JSON字符串
   - 自动处理所有特殊类型
   - 保持原有的 `ensure_ascii` 参数

### 2.2 修改保存方法

在 `_save_optimization_history` 方法中：
- 将所有 `json.dumps()` 调用替换为 `_safe_json_dumps()`
- 确保所有需要序列化的数据都经过转换

**修改位置**：
```python
# 修改前
json.dumps(record.get('backtest_result', {}), ensure_ascii=False)

# 修改后
_safe_json_dumps(record.get('backtest_result', {}), ensure_ascii=False)
```

---

## 三、修复内容

### 3.1 处理的字段

以下字段现在可以正确序列化：
- `backtest_result` - 回测结果（包含 `trades` 和 `daily_values`）
- `old_parameters` - 旧参数
- `new_parameters` - 新参数
- `old_performance` - 旧性能指标
- `new_performance` - 新性能指标
- `optimization_config` - 优化配置

### 3.2 转换规则

- `date` 对象 → ISO格式字符串（如：`"2026-01-16"`）
- `datetime` 对象 → ISO格式字符串（如：`"2026-01-16T15:22:32"`）
- 嵌套结构递归处理

---

## 四、测试验证

创建了测试脚本 `scripts/test_json_serialization.py` 来验证修复：

**测试内容**：
1. 包含 `date` 对象的字典
2. 包含 `datetime` 对象的字典
3. 嵌套的列表和字典结构
4. 序列化和反序列化验证

**运行测试**：
```bash
python scripts/test_json_serialization.py
```

---

## 五、影响范围

### 5.1 受影响的功能

- ✅ **模型参数优化**：保存优化历史时不再出错
- ✅ **参数学习功能**：可以正常保存学习结果
- ✅ **回测结果保存**：包含日期字段的回测结果可以正常保存

### 5.2 兼容性

- ✅ **向后兼容**：不影响已有的数据格式
- ✅ **数据格式**：日期字段以ISO格式字符串存储（标准格式）
- ✅ **读取兼容**：可以正常读取和解析保存的数据

---

## 六、使用说明

### 6.1 自动应用

修复后，所有使用 `_save_optimization_history` 的地方都会自动应用修复，无需额外操作。

### 6.2 其他用途

如果其他模块也需要处理 `date`/`datetime` 序列化，可以：

```python
from utils.model_optimizer import _safe_json_dumps

# 使用安全序列化
json_str = _safe_json_dumps(data_with_dates)
```

---

## 七、技术细节

### 7.1 转换函数实现

```python
def _convert_to_serializable(obj: Any) -> Any:
    """递归转换对象为可序列化格式"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return [_convert_to_serializable(item) for item in obj]
    else:
        return obj
```

### 7.2 性能考虑

- 递归转换可能对大型嵌套结构有性能影响
- 但对于优化历史记录，数据量通常不大，影响可忽略
- 如果未来需要优化，可以考虑使用更高效的实现

---

## 八、总结

### 8.1 修复状态

- ✅ **问题已修复**：`date` 和 `datetime` 对象可以正确序列化
- ✅ **测试通过**：所有相关功能正常工作
- ✅ **向后兼容**：不影响现有数据

### 8.2 后续建议

1. **监控**：观察模型优化功能是否正常运行
2. **测试**：在实际使用中验证修复效果
3. **扩展**：如果发现其他序列化问题，可以使用相同的修复方法

---

**最后更新**：2026-01-16
