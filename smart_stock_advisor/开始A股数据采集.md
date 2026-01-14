# A股10年数据采集说明

## 采集参数

- **市场类型**: A股 (--market cn)
- **采集年限**: 10年 (--years 10)
- **批次大小**: 50只股票/批次 (--batch-size 50)
- **批次延迟**: 1.0秒 (--delay 1.0)
- **线程数**: 建议3-5个线程 (--threads 3-5)

## 执行命令

### 单线程模式（稳定，但较慢）
```cmd
py scripts\batch_collect_10years_data.py --market cn --years 10 --batch-size 50 --delay 1.0
```

### 多线程模式（推荐，速度更快）
```cmd
py scripts\batch_collect_10years_data.py --market cn --years 10 --batch-size 50 --delay 1.0 --threads 3
```

## 注意事项

1. **时间估计**：
   - 单线程：约需要数小时到数十小时（取决于股票数量和网络速度）
   - 3线程：速度提升约2-3倍
   - 5线程：速度提升约3-4倍，但可能触发API限流

2. **断点续传**：
   - 如果中断，可以使用 `--resume` 参数继续之前的进度
   - 进度文件保存在：`data/collection_progress/collect_progress_cn.json`

3. **数据存储**：
   - 数据实时存储到数据库
   - 每只股票采集完成后立即保存
   - 支持重复运行（已存在的数据会更新）

4. **API限流**：
   - 如果遇到限流，脚本会自动处理错误
   - 失败的股票会记录到进度文件中
   - 可以使用 `--resume` 参数重新运行失败的股票

## 进度查看

采集进度会实时显示在控制台，包括：
- 当前批次进度
- 已完成的股票数量
- 失败的股票数量
- 预计剩余时间

进度文件位置：`data/collection_progress/collect_progress_cn.json`
