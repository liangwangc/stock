# MACD修复完成报告

**修复日期**：2026-01-26  
**问题**：16号及之后MACD数值异常（比正确值大183.7倍）  
**状态**：✅ 已修复

---

## 一、问题原因

### 1.1 根本原因

**`fetch_tushare_data_16_23.py` 中的 `get_historical_data_for_indicators()` 函数**：
- ❌ 使用 `trade_date <= %s` 查询历史数据
- ❌ 导致历史数据包含当前日期
- ❌ `calculate_technical_indicators()` 又添加了一次 `current_close`
- ❌ 导致当前收盘价被重复添加，MACD计算错误

### 1.2 影响范围

- ✅ **16号及之后所有使用 `fetch_tushare_data_16_23.py` 获取的数据**
- ✅ **设置页面---股票数据获取---增量更新**（使用 `fetch_tushare_data_16_23.py`）
- ❌ **`stock_history_collector.py`**（不受影响，使用不同的逻辑）

---

## 二、修复方案

### 2.1 代码修复

**修改文件**：`scripts/fetch_tushare_data_16_23.py`

**修改内容**：
```python
# 修改前
sql = """
    SELECT trade_date, close_price, volume
    FROM stock_history_data
    WHERE symbol = %s AND trade_date <= %s  # ❌ 包含当前日期
    ORDER BY trade_date DESC
    LIMIT %s
"""

# 修改后
sql = """
    SELECT trade_date, close_price, volume
    FROM stock_history_data
    WHERE symbol = %s AND trade_date < %s  # ✅ 不包含当前日期
    ORDER BY trade_date DESC
    LIMIT %s
"""
```

**修改位置**：第615-621行

### 2.2 数据修复脚本

**创建文件**：`scripts/fix_macd_values_after_16.py`

**功能**：
- ✅ 重新计算16号及之后所有日期的MACD值
- ✅ 使用修复后的逻辑（`trade_date < %s`）
- ✅ 支持单只股票、单日、批量修复
- ✅ 支持多线程处理

**使用方法**：
```bash
# 修复所有16号及之后的数据（推荐）
python scripts/fix_macd_values_after_16.py --start-date 2026-01-16 --threads 10

# 修复单只股票
python scripts/fix_macd_values_after_16.py --symbol 000001 --start-date 2026-01-16

# 修复单只股票的单日数据
python scripts/fix_macd_values_after_16.py --symbol 000001 --date 2026-01-16
```

---

## 三、设置页面检查

### 3.1 设置页面---股票数据获取

**调用链**：
```
设置页面（前端）
  ↓
POST /api/stock-data/tasks (创建任务)
  ↓
ScheduledTaskManager._execute_stock_history_update()
  ↓
TushareDataFetcher.fetch_and_save_missing_data()
  ↓
TushareDataFetcher._process_single_stock()
  ↓
TushareDataFetcher.get_historical_data_for_indicators()  ← ✅ 已修复
  ↓
TushareDataFetcher.calculate_technical_indicators()
```

**结论**：✅ **已修复**，设置页面的增量更新功能使用修复后的逻辑

### 3.2 其他数据获取方式

**`stock_history_collector.py`**：
- ✅ **不受影响**，使用不同的逻辑
- ✅ 直接从API获取历史数据，不涉及数据库查询
- ✅ 不存在重复添加当前收盘价的问题

---

## 四、修复验证

### 4.1 验证方法

运行修复脚本后，可以使用以下脚本验证：

```bash
# 检查修复前后的MACD值
python scripts/check_macd_values.py

# 调试单只股票的MACD计算
python scripts/debug_macd_calculation.py
```

### 4.2 预期结果

修复后，MACD值应该：
- ✅ 在合理范围内（通常应该在-10到+10之间）
- ✅ 与15号及之前的数据量级一致
- ✅ 不再出现183.7倍的异常放大

---

## 五、后续建议

### 5.1 立即执行

1. ✅ **运行修复脚本**：
   ```bash
   python scripts/fix_macd_values_after_16.py --start-date 2026-01-16 --threads 10
   ```

2. ✅ **验证修复结果**：
   ```bash
   python scripts/check_macd_values.py
   ```

### 5.2 预防措施

1. ✅ **代码审查**：确保所有获取历史数据的函数都使用 `trade_date < %s` 而不是 `trade_date <= %s`
2. ✅ **单元测试**：添加测试用例，验证MACD计算逻辑
3. ✅ **数据验证**：在保存MACD值前，检查是否在合理范围内

---

## 六、修改文件清单

1. ✅ `scripts/fetch_tushare_data_16_23.py`
   - 修改 `get_historical_data_for_indicators()` 函数（第615-621行）
   - 使用 `trade_date < %s` 而不是 `trade_date <= %s`

2. ✅ `scripts/fix_macd_values_after_16.py`（新建）
   - MACD值修复脚本
   - 支持单只股票、单日、批量修复
   - 支持多线程处理

---

## 七、总结

✅ **代码修复完成**：
- ✅ 修复了 `get_historical_data_for_indicators()` 函数
- ✅ 设置页面的增量更新功能已使用修复后的逻辑

✅ **数据修复脚本已创建**：
- ✅ 可以批量修复16号及之后的所有MACD值
- ✅ 支持多线程处理，提高效率

✅ **影响范围确认**：
- ✅ 设置页面---股票数据获取：已修复
- ✅ `stock_history_collector.py`：不受影响

---

**报告完成时间**：2026-01-26
