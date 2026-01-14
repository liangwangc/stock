# 股票历史数据存储模块

## 功能说明

该模块用于存储近10年每只股票的详细历史数据，包括：
- **基本价格数据**：开盘价、收盘价、最高价、最低价、昨收价、涨跌额、涨跌幅
- **成交数据**：成交量、成交额、换手率、量比
- **盘口数据**：外盘、内盘、委比、五档买卖盘
- **成本分布**：历史成本分布、当日成本分布
- **市值和估值**：总市值、流通市值、市盈率、市净率
- **涨跌停信息**：涨停价、跌停价、是否涨停/跌停
- **技术指标**：MA5/10/20/60、RSI、MACD等
- **资金流向**：主力净流入、超大单/大单/中单/小单净流入
- **融资融券**：融资余额、融券余额

## 数据库表结构

表名：`stock_history_data`

### 主要字段

- **基本信息**：`symbol`（股票代码）、`name`（股票名称）、`trade_date`（交易日期）
- **价格数据**：`open_price`、`close_price`、`high_price`、`low_price`、`pre_close`
- **成交数据**：`volume`（成交量，手）、`amount`（成交额，元）、`turnover_rate`（换手率，%）、`volume_ratio`（量比）
- **盘口数据**：`outer_volume`（外盘，手）、`inner_volume`（内盘，手）、`bid_ask_ratio`（委比，%）
- **五档买卖盘**：`bid_levels`、`ask_levels`（JSON格式）
- **成本分布**：`cost_distribution`、`cost_distribution_history`、`cost_distribution_intraday`（JSON格式）
- **技术指标**：`ma5`、`ma10`、`ma20`、`ma60`、`rsi`、`macd`等
- **唯一索引**：`(symbol, trade_date)` 确保每天每个股票只有一条记录

## 使用方法

### 1. 创建数据库表

```bash
# 方法1：运行Python脚本
python database/create_stock_history_table.py

# 方法2：直接执行SQL文件
mysql -u root -p stock_data < database/stock_history_table.sql
```

### 2. 初始数据采集（采集近10年历史数据）

```bash
# 采集单只股票的历史数据
python scripts/collect_stock_history.py --symbol 600519 --years 10

# 采集多只股票的历史数据
python scripts/collect_stock_history.py --symbols 600519 000001 000002 --years 10

# 采集所有股票的历史数据（按成交量排序，取前100只）
python scripts/collect_stock_history.py --limit 100 --sort-by-turnover --years 10

# 采集所有股票的历史数据（不限制数量，会花费很长时间）
python scripts/collect_stock_history.py --years 10
```

### 3. 每日增量更新（收盘后执行）

```bash
# 更新所有股票今日数据
python scripts/update_stock_history_daily.py

# 更新指定股票今日数据
python scripts/update_stock_history_daily.py --symbol 600519

# 更新多只股票今日数据
python scripts/update_stock_history_daily.py --symbols 600519 000001 000002
```

### 4. 设置定时任务（每日收盘后自动更新）

#### Linux/Mac (crontab)

```bash
# 编辑crontab
crontab -e

# 添加以下行（每天15:05执行，A股收盘后5分钟）
5 15 * * 1-5 cd /path/to/smart_stock_advisor && /usr/bin/python3 scripts/update_stock_history_daily.py >> logs/update_history.log 2>&1
```

#### Windows (任务计划程序)

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天15:05（周一到周五）
4. 操作：启动程序
   - 程序：`python`
   - 参数：`scripts/update_stock_history_daily.py`
   - 起始于：`D:\wjw_work\smart_stock_advisor`

### 5. 使用Python API

```python
from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage

# 采集单只股票的历史数据
collector = StockHistoryCollector()
result = collector.collect_stock_history_data('600519', years=10)
print(f"采集完成: 成功 {result['success_count']}, 失败 {result['fail_count']}")

# 增量更新今日数据
result = collector.incremental_update_today(['600519', '000001'])
print(f"更新完成: 成功 {result['success_count']}, 失败 {result['fail_count']}")

# 查询历史数据
storage = StockHistoryStorage()
data = storage.get_stock_history_data('600519', start_date='2024-01-01', end_date='2024-12-31')
print(f"查询到 {len(data)} 条记录")

# 获取最新日期
latest_date = storage.get_latest_date('600519')
print(f"最新数据日期: {latest_date}")

# 检查数据是否存在
exists = storage.check_data_exists('600519', '2024-01-15')
print(f"数据是否存在: {exists}")

# 获取缺失的日期列表
missing_dates = storage.get_missing_dates('600519', '2024-01-01', '2024-12-31')
print(f"缺失日期数量: {len(missing_dates)}")
```

## 注意事项

1. **数据采集速度**：
   - 采集历史数据时，为避免请求过快被限制，每只股票每次请求间隔0.5秒
   - 采集大量股票时，建议分批执行或使用`--limit`参数限制数量

2. **外盘和内盘数据**：
   - 外盘和内盘数据需要Level-2行情，历史数据可能不可用
   - 如果无法获取，这些字段会为`NULL`

3. **成本分布数据**：
   - 成本分布数据需要盘中数据，历史数据可能不完整
   - 建议在交易日盘中或收盘后采集，以获得更完整的数据

4. **数据质量**：
   - 系统会自动计算数据质量得分（`data_quality_score`）
   - 数据异常时会标记为无效（`is_valid = 0`）

5. **存储空间**：
   - 每条记录约1-2KB
   - 近10年数据，假设4000只股票，约需要：4000只 × 2500个交易日 × 2KB ≈ 20GB
   - 建议定期备份数据库

## 数据更新策略

1. **初始数据采集**：
   - 首次使用时，采集所有股票近10年的历史数据
   - 建议分批执行，避免一次性采集过多导致服务器压力过大

2. **每日增量更新**：
   - 每天收盘后（15:05）自动更新所有股票今日数据
   - 使用`ON DUPLICATE KEY UPDATE`确保数据不会重复

3. **数据补全**：
   - 如果某天数据缺失，可以手动重新采集
   - 使用`--symbol`参数指定股票，系统会自动识别缺失日期

## 故障排查

1. **数据库连接失败**：
   - 检查`config_db.py`中的数据库配置
   - 确保MySQL服务正在运行
   - 检查数据库用户权限

2. **数据采集失败**：
   - 检查网络连接
   - 检查akshare数据源是否可用
   - 查看日志文件了解详细错误信息

3. **数据不完整**：
   - 某些字段（如外盘、内盘）可能需要Level-2行情，历史数据可能不可用
   - 这是正常现象，不影响其他数据的使用
