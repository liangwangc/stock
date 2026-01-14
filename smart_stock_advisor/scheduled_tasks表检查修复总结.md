# scheduled_tasks表检查修复总结

## 问题

**错误信息**：
```
执行查询失败: SELECT * FROM scheduled_tasks WHERE task_type = 'news_crawl' ORDER BY created_at DESC
错误: (1146, "Table 'stock_data.scheduled_tasks' doesn't exist")
```

**问题原因**：
- 虽然之前添加了 `try-except` 错误处理，但 `DBConnection.execute_query()` 在执行查询前会记录 ERROR 级别的日志
- 即使捕获了异常，错误日志仍然会被记录

## 优化方案

**方案**：在查询 `scheduled_tasks` 表之前，先检查表是否存在

**实现**：使用 `information_schema.tables` 查询表是否存在，避免直接查询不存在的表

## 修改内容

### 修改文件：`smart_stock_advisor/utils/news_task_manager.py`

在所有查询 `scheduled_tasks` 表的方法中，添加表存在性检查：

1. **`start_task()` 方法（第234-264行）** ✅ 已修复
   - 在查询前检查表是否存在
   - 如果表不存在，直接使用独立启动方式

2. **`stop_task()` 方法（第325-355行）** ✅ 已修复
   - 在查询前检查表是否存在
   - 如果表不存在，直接使用独立停止方式

3. **`get_task()` 方法（第397-421行）** ✅ 已修复
   - 在查询前检查表是否存在
   - 如果表不存在，直接使用旧表查询

4. **`get_all_tasks()` 方法（第450-478行）** ✅ 已修复
   - 在查询前检查表是否存在
   - 如果表不存在，跳过统一调度表查询

## 代码实现

### 表存在性检查

```python
# 先检查scheduled_tasks表是否存在
try:
    check_sql = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() AND table_name = 'scheduled_tasks'
    """
    table_check = DBConnection.execute_query(check_sql)
    table_exists = table_check and len(table_check) > 0 and table_check[0].get('count', 0) > 0
except:
    table_exists = False

if table_exists:
    # 执行查询
    sql = "SELECT * FROM scheduled_tasks WHERE ..."
    result = DBConnection.execute_query(sql, ...)
else:
    # 表不存在，使用备用方案
    self.logger.debug("scheduled_tasks表不存在，跳过统一调度表查询")
```

## 优势

1. **避免错误日志**：
   - 不会查询不存在的表，因此不会产生 ERROR 级别的日志
   - 只在 DEBUG 级别记录表不存在的信息

2. **性能优化**：
   - 表存在性检查比直接查询失败更快
   - 避免了异常处理的开销

3. **代码清晰**：
   - 逻辑更清晰，先检查后执行
   - 减少异常处理代码的复杂性

## 测试建议

1. **测试表不存在的情况**：
   - 确认不会产生 ERROR 级别的日志
   - 确认功能正常工作（回退到使用 `news_crawl_tasks` 表）

2. **测试表存在的情况**：
   - 确认功能正常工作
   - 确认表存在性检查不影响性能
