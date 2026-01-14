# akshare 美股数据使用说明

## 概述

akshare 是一个用于获取金融数据的 Python 库，支持获取美股历史数据。现在系统已经优先使用 akshare 获取美股数据，yfinance 作为备用数据源。

## 基本用法

### 1. 直接使用 akshare 获取美股数据

```python
import akshare as ak

# 获取美股历史数据
df = ak.stock_us_hist(
    symbol='AAPL',           # 股票代码（如：AAPL, MSFT, GOOGL）
    period='daily',          # 周期：daily（日线）
    start_date='20240101',   # 开始日期：YYYYMMDD格式
    end_date='20241231',     # 结束日期：YYYYMMDD格式
    adjust='qfq'             # 复权类型：qfq（前复权）、hfq（后复权）、''（不复权）
)

print(df.head())
```

### 2. 使用 USStockDataSource 类（推荐）

系统已经封装了 `USStockDataSource` 类，会自动优先使用 akshare，失败时自动切换到 yfinance：

```python
from data_source.us_stock_data_source import USStockDataSource

ds = USStockDataSource()

# 方式1: 指定日期范围（推荐）
df = ds.get_stock_data(
    symbol='AAPL',
    start_date='2024-01-01',  # YYYY-MM-DD格式
    end_date='2024-12-31'
)

# 方式2: 使用period参数
df = ds.get_stock_data(
    symbol='AAPL',
    period='10y'  # 10年数据
)
```

## 参数说明

### akshare.stock_us_hist() 参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| symbol | str | 股票代码 | 'AAPL', 'MSFT', 'GOOGL' |
| period | str | 数据周期 | 'daily'（日线） |
| start_date | str | 开始日期 | '20240101'（YYYYMMDD格式） |
| end_date | str | 结束日期 | '20241231'（YYYYMMDD格式） |
| adjust | str | 复权类型 | 'qfq'（前复权）、'hfq'（后复权）、''（不复权） |

### USStockDataSource.get_stock_data() 参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| symbol | str | 股票代码 | 'AAPL' |
| start_date | str | 开始日期（可选） | '2024-01-01'（YYYY-MM-DD格式） |
| end_date | str | 结束日期（可选） | '2024-12-31'（YYYY-MM-DD格式） |
| period | str | 时间周期（可选） | '10y', '5y', '1y' |

**注意**：如果提供了 `start_date` 和 `end_date`，则使用它们；否则使用 `period` 参数。

## 返回数据格式

返回的 DataFrame 包含以下列：

- `date`: 日期（索引）
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `adj_close`: 调整后收盘价（复权价格）
- `volume`: 成交量

## 测试脚本

运行测试脚本验证 akshare 是否正常工作：

```bash
py test_akshare_us_stock.py
```

这个脚本会：
1. 测试直接使用 akshare 获取数据
2. 测试使用 USStockDataSource 类获取数据
3. 测试多个股票的数据获取

## 批量收集数据

使用批量收集脚本时，系统会自动使用 akshare（如果可用）：

```bash
# 收集美股10年数据
py scripts\batch_collect_10years_data.py --market us --years 10 --batch-size 20 --delay 1.0 --threads 2
```

## 注意事项

1. **日期格式**：
   - akshare 需要 `YYYYMMDD` 格式（如：'20240101'）
   - USStockDataSource 接受 `YYYY-MM-DD` 格式（如：'2024-01-01'），会自动转换

2. **复权类型**：
   - `qfq`：前复权（推荐，价格经过调整，便于历史对比）
   - `hfq`：后复权
   - `''`：不复权（原始价格）

3. **错误处理**：
   - 如果 akshare 获取失败，系统会自动尝试使用 yfinance
   - 如果两者都失败，返回空 DataFrame

4. **数据源优先级**：
   - 优先使用 akshare
   - akshare 失败时使用 yfinance（带重试机制）
   - 两者都失败时返回空 DataFrame

## 常见问题

### Q: akshare 获取数据失败怎么办？

A: 系统会自动切换到 yfinance。如果 yfinance 也失败，检查：
- 股票代码是否正确
- 日期范围是否合理
- 网络连接是否正常

### Q: 如何获取实时数据？

A: 目前 akshare 主要用于获取历史数据。实时数据可能需要使用其他API或数据源。

### Q: 支持哪些股票代码？

A: 支持所有在美股市场交易的股票代码，如：
- 纳斯达克：AAPL, MSFT, GOOGL, AMZN, TSLA
- 纽交所：JPM, JNJ, WMT, KO
- 其他：BRK-B（注意使用 '-' 而不是 '.'）

## 示例代码

### 示例1：获取单只股票数据

```python
from data_source.us_stock_data_source import USStockDataSource

ds = USStockDataSource()
df = ds.get_stock_data('AAPL', start_date='2024-01-01', end_date='2024-12-31')
print(df.head())
```

### 示例2：批量获取多只股票

```python
from data_source.us_stock_data_source import USStockDataSource

ds = USStockDataSource()
symbols = ['AAPL', 'MSFT', 'GOOGL']

for symbol in symbols:
    df = ds.get_stock_data(symbol, period='1y')
    print(f"{symbol}: {len(df)} 条记录")
```

### 示例3：获取10年数据

```python
from data_source.us_stock_data_source import USStockDataSource

ds = USStockDataSource()
df = ds.get_stock_data('AAPL', period='10y')
print(f"共获取 {len(df)} 条记录")
print(df.tail())  # 查看最后几条
```
