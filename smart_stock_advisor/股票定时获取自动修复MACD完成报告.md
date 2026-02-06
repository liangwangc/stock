# 股票定时获取自动修复MACD完成报告

## 一、需求描述

用户希望在设置页面的股票定时获取完成后，自动执行MACD修复脚本：
- 执行脚本：`fix_macd_values_after_16.py --start-date <动态日期> --threads 10`
- 日期应该是动态的（从任务配置中获取）

## 二、实现方案

### 2.1 实现位置

**文件**：`utils/scheduled_task_manager.py`
**方法**：`_execute_cn_stock_data_collection()`（第839行）

### 2.2 实现逻辑

在数据收集完成后，自动调用MACD修复脚本：

1. **调用时机**：在数据收集完成、更新预测表真实价格字段之后
2. **动态日期**：使用 `start_date` 作为修复的起始日期（从任务配置中获取）
3. **线程数**：使用 `max_workers` 作为线程数（如果小于10则使用10）

### 2.3 代码修改

**位置**：`utils/scheduled_task_manager.py` 第914-928行

```python
# 数据收集完成后，修复MACD值（使用动态日期）
try:
    self.logger.info(f"开始修复MACD值（日期范围: {start_date} 及之后）...")
    # 导入MACD修复脚本（从scripts目录导入）
    # scripts_path已经在前面添加到sys.path了
    from fix_macd_values_after_16 import MACDFixer
    macd_fixer = MACDFixer()
    
    # 使用start_date作为修复的起始日期（动态日期）
    # 使用max_workers作为线程数（默认10，如果max_workers>=10则使用max_workers，否则使用10）
    fix_threads = max(max_workers, 10) if max_workers > 0 else 10
    fix_result = macd_fixer.fix_all_after_date(start_date=start_date, max_workers=fix_threads)
    
    self.logger.info(f"MACD修复完成: 总计 {fix_result.get('total', 0)}, 成功 {fix_result.get('success', 0)}, 失败 {fix_result.get('failed', 0)}")
except Exception as e:
    self.logger.warning(f"修复MACD值失败: {str(e)}")
    import traceback
    self.logger.warning(traceback.format_exc())
```

## 三、功能说明

### 3.1 动态日期

**增量更新模式**：
- `start_date` = 当天日期（动态）
- 修复该日期及之后的所有MACD值

**全量收集模式**：
- `start_date` = 开始日期（从任务配置中获取）
- 修复该日期及之后的所有MACD值

### 3.2 线程数

- 如果 `max_workers >= 10`：使用 `max_workers`
- 如果 `max_workers < 10`：使用 10（确保有足够的线程数）

### 3.3 错误处理

- 如果MACD修复失败，只记录警告日志，不影响主任务的成功状态
- 使用 `try-except` 包裹，确保异常不会中断主流程

## 四、执行流程

```
设置页面 -> 创建定时任务 -> 启动任务
  ↓
定时执行或立即执行
  ↓
_execute_cn_stock_data_collection()
  ↓
1. 获取股票数据（fetch_and_save_missing_data）
  ↓
2. 更新预测表真实价格字段
  ↓
3. 修复MACD值（fix_all_after_date）
  ↓
返回结果
```

## 五、日志输出

**成功时**：
```
开始修复MACD值（日期范围: 2026-01-26 及之后）...
MACD修复完成: 总计 1000, 成功 980, 失败 20
```

**失败时**：
```
修复MACD值失败: <错误信息>
<堆栈跟踪>
```

## 六、注意事项

1. **导入路径**：MACD修复脚本从 `scripts` 目录导入，该路径已在方法开始时添加到 `sys.path`
2. **性能影响**：MACD修复会额外消耗时间，但可以确保数据准确性
3. **错误隔离**：MACD修复失败不会影响主任务的成功状态

## 七、测试建议

1. **功能测试**：
   - 创建定时任务并执行
   - 验证MACD修复是否自动执行
   - 验证日期是否正确（动态日期）

2. **性能测试**：
   - 测试MACD修复的耗时
   - 验证是否影响主任务的执行时间

3. **错误测试**：
   - 测试MACD修复失败时的处理
   - 验证主任务是否仍然成功

---

**完成时间**：2026-01-26
**修改文件**：`utils/scheduled_task_manager.py`
**影响范围**：设置页面 -> 股票数据获取 -> 定时任务获取收盘后的数据
