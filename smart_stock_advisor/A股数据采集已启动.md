# A股10年数据采集已启动

## 启动信息

- **启动时间**: 刚刚启动
- **市场类型**: A股
- **采集年限**: 10年
- **批次大小**: 50只股票/批次
- **批次延迟**: 1.0秒
- **线程数**: 3个线程（多线程模式）

## 采集状态

数据采集任务已在后台启动运行。

## 进度查看方式

### 1. 查看控制台输出
采集进度会实时显示在控制台，包括：
- 当前批次信息
- 每只股票的采集状态
- 已完成的股票数量
- 失败的股票数量

### 2. 查看进度文件
进度文件位置：`data/collection_progress/collect_progress_cn.json`

进度文件包含：
- `completed_symbols`: 已完成的股票列表
- `failed_symbols`: 失败的股票列表（含错误信息）
- `current_batch`: 当前批次号
- `total_symbols`: 总股票数
- `start_time`: 开始时间
- `last_update`: 最后更新时间

### 3. 查看数据库
可以直接查询数据库 `stock_history_data` 表查看已保存的数据：
```sql
SELECT COUNT(*) as total_records, COUNT(DISTINCT symbol) as total_stocks 
FROM stock_history_data;
```

## 中断和恢复

### 如果需要中断
按 `Ctrl+C` 中断采集，进度会自动保存。

### 恢复采集
使用 `--resume` 参数可以继续之前的进度：
```cmd
py scripts\batch_collect_10years_data.py --market cn --years 10 --batch-size 50 --delay 1.0 --threads 3 --resume
```

## 预计时间

- **总股票数**: 约5000只A股（取决于数据源）
- **单只股票**: 约10年数据，约2500个交易日
- **预计时间**: 
  - 3线程模式：约20-40小时（取决于网络速度和API响应）
  - 单线程模式：约60-120小时

## 注意事项

1. **数据实时保存**: 每只股票采集完成后立即保存到数据库
2. **支持断点续传**: 中断后可以继续，不会重复采集已完成的数据
3. **错误处理**: 失败的股票会记录到进度文件，可以后续重新运行
4. **API限流**: 如果遇到限流，脚本会记录错误并继续下一只股票

## 验证采集结果

采集完成后，可以运行以下命令查看统计信息：
```sql
-- 查看总记录数
SELECT COUNT(*) FROM stock_history_data;

-- 查看已采集的股票数量
SELECT COUNT(DISTINCT symbol) FROM stock_history_data;

-- 查看每只股票的数据量
SELECT symbol, COUNT(*) as record_count 
FROM stock_history_data 
GROUP BY symbol 
ORDER BY record_count DESC;
```
