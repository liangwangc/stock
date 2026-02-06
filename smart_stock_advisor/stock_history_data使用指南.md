# stock_history_data 表使用指南

## 一、数据表概述

### 表结构
- **表名**：`stock_history_data`
- **数据量**：近10年的历史股票数据
- **数据粒度**：日线数据（daily）
- **唯一索引**：`(symbol, trade_date, period_type)` - 确保每天每个股票只有一条记录

### 主要字段

#### 1. 基本信息
- `symbol` - 股票代码（如：600519）
- `name` - 股票名称
- `trade_date` - 交易日期
- `period_type` - 周期类型（daily/weekly/monthly/yearly）

#### 2. 价格数据
- `open_price` - 开盘价
- `close_price` - 收盘价
- `high_price` - 最高价
- `low_price` - 最低价
- `pre_close` - 昨收价
- `change_amount` - 涨跌额
- `change_pct` - 涨跌幅

#### 3. 成交数据
- `volume` - 成交量（手）
- `amount` - 成交额（元）
- `turnover_rate` - 换手率（%）
- `volume_ratio` - 量比

#### 4. 技术指标（已计算）
- `ma5`, `ma10`, `ma20`, `ma60` - 移动平均线
- `rsi` - 相对强弱指标
- `macd`, `macd_signal`, `macd_hist` - MACD指标
- `x2` - X2指标

#### 5. 资金流向
- `main_net_inflow` - 主力净流入
- `super_large_inflow` - 超大单净流入
- `large_inflow` - 大单净流入
- `medium_inflow` - 中单净流入
- `small_inflow` - 小单净流入

#### 6. 估值指标
- `pe_ratio` - 市盈率
- `pb_ratio` - 市净率
- `total_market_cap` - 总市值
- `float_market_cap` - 流通市值

---

## 二、数据获取方法

### 1. 使用 StockHistoryStorage 类

```python
from utils.stock_history_storage import StockHistoryStorage

# 初始化
storage = StockHistoryStorage()

# 获取单只股票的历史数据
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01',
    limit=None,  # 不限制条数
    period_type='daily'
)

# 返回格式：List[Dict]
# 每个Dict包含该股票某一天的所有字段
```

### 2. 使用 StockDataSource 类（推荐）

```python
from data_source.stock_data_source import StockDataSource

# 初始化
data_source = StockDataSource()

# 获取股票数据（自动优先从数据库获取）
df = data_source.get_stock_data(
    symbol='600519',
    days=365,  # 获取最近365天
    start_date='2020-01-01',  # 可选：指定开始日期
    end_date='2024-01-01'  # 可选：指定结束日期
)

# 返回格式：pandas.DataFrame
# 列名：date, open, high, low, close, volume
```

---

## 三、在模型学习中的使用场景

### 1. 回测分析 ✅ **已使用**

**用途**：使用历史价格数据模拟交易，评估参数表现

**代码位置**：
- `utils/backtest_engine.py` - `backtest_with_parameters()` 方法
- `utils/backtest_engine.py` - `backtest_predictions()` 方法

**使用方式**：
```python
from utils.backtest_engine import BacktestEngine

engine = BacktestEngine()

# 使用历史数据回测
result = engine.backtest_with_parameters(
    start_date='2020-01-01',
    end_date='2024-01-01',
    parameters={
        'technical_weight': 0.2,
        'news_weight': 0.25,
        # ... 其他权重参数
    }
)

# 返回回测结果：总收益率、胜率、最大回撤等
```

**数据需求**：
- 需要 `stock_history_data` 表的历史价格数据（`close_price`）
- 需要 `stock_predictions` 表的预测数据
- 时间范围：建议至少90-365天

---

### 2. 市场状态识别 ✅ **已使用**

**用途**：根据历史价格数据识别市场状态（牛市/熊市/震荡市）

**代码位置**：
- `utils/model_performance_evaluator.py` - `_identify_market_condition()` 方法
- `utils/adaptive_learning_strategy.py` - 市场状态识别

**使用方式**：
```python
from utils.stock_history_storage import StockHistoryStorage

storage = StockHistoryStorage()

# 获取市场指数历史数据（如：000001 上证指数）
index_data = storage.get_stock_history_data(
    symbol='000001',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 计算市场状态
# 1. 计算移动平均线趋势
# 2. 计算波动率
# 3. 识别牛市/熊市/震荡市
```

**数据需求**：
- 需要市场指数（如000001上证指数）的历史价格数据
- 时间范围：建议至少30-90天

---

### 3. 技术指标计算 ✅ **已计算并存储**

**用途**：技术指标已计算并存储在 `stock_history_data` 表中

**可用指标**：
- `ma5`, `ma10`, `ma20`, `ma60` - 移动平均线
- `rsi` - 相对强弱指标
- `macd`, `macd_signal`, `macd_hist` - MACD指标
- `x2` - X2指标

**使用方式**：
```python
from utils.stock_history_storage import StockHistoryStorage

storage = StockHistoryStorage()

# 获取历史数据（包含技术指标）
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 直接使用技术指标
for record in data:
    ma5 = record.get('ma5')
    rsi = record.get('rsi')
    macd = record.get('macd')
    # ... 使用这些指标进行分析
```

---

### 4. 参数优化中的历史数据使用 ✅ **已使用**

**用途**：在参数优化过程中，使用历史数据回测不同权重组合的表现

**代码位置**：
- `utils/model_optimizer.py` - `optimize_weights_grid_search()` 方法
- `utils/model_optimizer.py` - `optimize_weights_bayesian()` 方法

**使用流程**：
1. 获取历史预测数据（`stock_predictions` 表）
2. 获取历史价格数据（`stock_history_data` 表）
3. 使用回测引擎测试不同权重组合
4. 选择表现最好的权重组合

**数据需求**：
- 需要 `stock_history_data` 表的历史价格数据
- 需要 `stock_predictions` 表的预测数据
- 时间范围：建议至少30-90天

---

### 5. 因子贡献度分析 ✅ **已使用**

**用途**：分析各技术指标因子对预测准确率的贡献

**代码位置**：
- `utils/model_performance_evaluator.py` - `_calculate_factor_contributions()` 方法

**使用方式**：
```python
from utils.stock_history_storage import StockHistoryStorage
from utils.model_performance_evaluator import ModelPerformanceEvaluator

storage = StockHistoryStorage()
evaluator = ModelPerformanceEvaluator()

# 获取历史数据（包含技术指标）
history_data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 分析因子贡献度
# 1. 获取预测数据
# 2. 关联历史价格和技术指标数据
# 3. 分析各因子得分与预测准确率的关系
```

---

## 四、实际使用示例

### 示例1：获取股票历史价格数据

```python
from utils.stock_history_storage import StockHistoryStorage
from datetime import datetime, timedelta

storage = StockHistoryStorage()

# 获取最近1年的数据
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365)

data = storage.get_stock_history_data(
    symbol='600519',
    start_date=start_date.strftime('%Y-%m-%d'),
    end_date=end_date.strftime('%Y-%m-%d')
)

# 处理数据
for record in data:
    date = record.get('trade_date')
    close_price = record.get('close_price')
    ma5 = record.get('ma5')
    rsi = record.get('rsi')
    print(f"{date}: 收盘价={close_price}, MA5={ma5}, RSI={rsi}")
```

### 示例2：计算股票收益率

```python
from utils.stock_history_storage import StockHistoryStorage

storage = StockHistoryStorage()

# 获取历史数据
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 按日期排序（从早到晚）
data_sorted = sorted(data, key=lambda x: x.get('trade_date'))

# 计算收益率
if len(data_sorted) >= 2:
    start_price = data_sorted[0].get('close_price')
    end_price = data_sorted[-1].get('close_price')
    
    if start_price and end_price:
        total_return = (end_price - start_price) / start_price * 100
        print(f"总收益率: {total_return:.2f}%")
```

### 示例3：分析技术指标趋势

```python
from utils.stock_history_storage import StockHistoryStorage
import pandas as pd

storage = StockHistoryStorage()

# 获取历史数据
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 转换为DataFrame
df = pd.DataFrame(data)

# 分析MA5和MA20的关系（金叉/死叉）
if 'ma5' in df.columns and 'ma20' in df.columns:
    df['ma5_above_ma20'] = df['ma5'] > df['ma20']
    
    # 找出金叉点（MA5上穿MA20）
    golden_cross = (df['ma5_above_ma20'] == True) & (df['ma5_above_ma20'].shift(1) == False)
    print(f"金叉次数: {golden_cross.sum()}")
```

### 示例4：在回测中使用历史数据

```python
from utils.backtest_engine import BacktestEngine

engine = BacktestEngine()

# 回测使用历史数据
result = engine.backtest_with_parameters(
    start_date='2020-01-01',
    end_date='2024-01-01',
    parameters={
        'technical_weight': 0.2,
        'news_weight': 0.25,
        'capital_flow_weight': 0.18,
        'market_weight': 0.17,
        'sector_rotation_weight': 0.05,
        'history_weight': 0.08,
        'valuation_weight': 0.02,
        'us_sector_weight': 0.05
    }
)

print(f"总收益率: {result.get('total_return', 0):.2f}%")
print(f"胜率: {result.get('win_rate', 0):.2f}%")
print(f"最大回撤: {result.get('max_drawdown', 0):.2f}%")
```

---

## 五、在模型学习中的具体应用

### 1. 性能评估

**使用历史数据**：
- 获取历史价格数据，计算实际涨跌幅
- 对比预测涨跌幅和实际涨跌幅，计算误差

**代码示例**：
```python
from utils.stock_history_storage import StockHistoryStorage
from utils.model_performance_evaluator import ModelPerformanceEvaluator

storage = StockHistoryStorage()
evaluator = ModelPerformanceEvaluator()

# 获取预测数据
predictions = evaluator.db.execute_query(
    "SELECT * FROM stock_predictions WHERE target_date >= %s AND target_date <= %s",
    ('2020-01-01', '2024-01-01')
)

# 获取历史价格数据
for pred in predictions:
    symbol = pred['symbol']
    target_date = pred['target_date']
    
    # 获取目标日期的实际价格
    history_data = storage.get_stock_history_data(
        symbol=symbol,
        start_date=target_date,
        end_date=target_date,
        limit=1
    )
    
    if history_data:
        actual_price = history_data[0].get('close_price')
        # 计算实际涨跌幅
        # ... 评估预测准确性
```

### 2. 参数优化

**使用历史数据**：
- 使用历史价格数据回测不同权重组合
- 选择表现最好的权重组合

**代码示例**：
```python
from utils.model_optimizer import ModelOptimizer

optimizer = ModelOptimizer()

# 优化权重（内部会使用历史数据回测）
result = optimizer.optimize_weights_grid_search(
    start_date='2020-01-01',
    end_date='2024-01-01',
    optimization_config={
        'use_cross_validation': True,
        'train_ratio': 0.8
    }
)

# 返回最优权重
best_weights = result.get('best_parameters')
```

### 3. 市场状态识别

**使用历史数据**：
- 获取市场指数历史数据
- 计算移动平均线、波动率等指标
- 识别市场状态

**代码示例**：
```python
from utils.stock_history_storage import StockHistoryStorage

storage = StockHistoryStorage()

# 获取上证指数历史数据
index_data = storage.get_stock_history_data(
    symbol='000001',  # 上证指数
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 计算市场状态
# 1. 计算MA20和MA60的关系
# 2. 计算波动率
# 3. 识别牛市/熊市/震荡市
```

---

## 六、数据查询SQL示例

### 1. 查询单只股票的历史数据

```sql
-- 查询600519最近1年的数据
SELECT 
    trade_date,
    close_price,
    ma5, ma10, ma20, ma60,
    rsi,
    macd, macd_signal, macd_hist
FROM stock_history_data
WHERE symbol = '600519'
  AND period_type = 'daily'
  AND trade_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
ORDER BY trade_date DESC;
```

### 2. 查询多只股票的数据

```sql
-- 查询多只股票的数据
SELECT 
    symbol,
    trade_date,
    close_price,
    change_pct,
    volume,
    ma5, ma20
FROM stock_history_data
WHERE symbol IN ('600519', '000001', '000002')
  AND period_type = 'daily'
  AND trade_date >= '2020-01-01'
ORDER BY symbol, trade_date DESC;
```

### 3. 统计股票数据完整性

```sql
-- 统计每只股票的数据条数
SELECT 
    symbol,
    COUNT(*) as record_count,
    MIN(trade_date) as earliest_date,
    MAX(trade_date) as latest_date
FROM stock_history_data
WHERE period_type = 'daily'
GROUP BY symbol
ORDER BY record_count DESC;
```

### 4. 查询技术指标数据

```sql
-- 查询技术指标数据
SELECT 
    symbol,
    trade_date,
    close_price,
    ma5, ma10, ma20, ma60,
    rsi,
    macd, macd_signal, macd_hist,
    x2
FROM stock_history_data
WHERE symbol = '600519'
  AND period_type = 'daily'
  AND trade_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
  AND ma5 IS NOT NULL  -- 确保技术指标已计算
ORDER BY trade_date DESC;
```

---

## 七、最佳实践建议

### 1. 数据获取优先级

**推荐顺序**：
1. **优先从数据库获取**：使用 `StockHistoryStorage.get_stock_history_data()`
2. **如果数据库没有，再实时获取**：使用 `StockDataSource.get_stock_data()`

**代码示例**：
```python
from utils.stock_history_storage import StockHistoryStorage
from data_source.stock_data_source import StockDataSource

storage = StockHistoryStorage()
data_source = StockDataSource()

# 1. 先尝试从数据库获取
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 2. 如果数据库没有，再实时获取
if not data:
    df = data_source.get_stock_data(
        symbol='600519',
        days=365
    )
```

### 2. 数据缓存策略

**建议**：
- 对于频繁查询的数据，可以缓存到内存
- 使用 `pandas.DataFrame` 进行数据处理和分析

**代码示例**：
```python
import pandas as pd
from utils.stock_history_storage import StockHistoryStorage

storage = StockHistoryStorage()

# 获取数据并转换为DataFrame
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

df = pd.DataFrame(data)

# 缓存DataFrame（可以保存为pickle文件）
df.to_pickle('cache_600519.pkl')

# 后续使用时直接加载
df = pd.read_pickle('cache_600519.pkl')
```

### 3. 批量查询优化

**建议**：
- 对于多只股票，使用批量查询
- 使用 `IN` 子句查询多只股票

**代码示例**：
```sql
-- 批量查询多只股票
SELECT 
    symbol,
    trade_date,
    close_price,
    ma5, ma20
FROM stock_history_data
WHERE symbol IN ('600519', '000001', '000002')
  AND period_type = 'daily'
  AND trade_date >= '2020-01-01'
ORDER BY symbol, trade_date DESC;
```

### 4. 数据完整性检查

**建议**：
- 定期检查数据完整性
- 使用 `scan_stock_data_status()` 方法检查缺失数据

**代码示例**：
```python
from utils.stock_history_storage import StockHistoryStorage

storage = StockHistoryStorage()

# 检查数据状态
status = storage.scan_stock_data_status(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

print(f"总日期数: {status['total_dates']}")
print(f"已有数据: {status['existing_count']}")
print(f"缺失数据: {status['missing_count']}")
print(f"完整率: {status['completeness_rate']:.2f}%")
```

---

## 八、常见使用场景

### 场景1：计算股票收益率

```python
from utils.stock_history_storage import StockHistoryStorage

storage = StockHistoryStorage()

# 获取历史数据
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 计算年化收益率
if len(data) >= 2:
    start_price = data[-1].get('close_price')  # 最早的价格
    end_price = data[0].get('close_price')  # 最新的价格
    
    if start_price and end_price:
        total_return = (end_price - start_price) / start_price
        years = len(data) / 252  # 假设一年252个交易日
        annual_return = (1 + total_return) ** (1 / years) - 1
        print(f"年化收益率: {annual_return * 100:.2f}%")
```

### 场景2：分析技术指标趋势

```python
from utils.stock_history_storage import StockHistoryStorage
import pandas as pd

storage = StockHistoryStorage()

# 获取历史数据
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 转换为DataFrame
df = pd.DataFrame(data)
df['trade_date'] = pd.to_datetime(df['trade_date'])
df = df.sort_values('trade_date')

# 分析MA5和MA20的关系
if 'ma5' in df.columns and 'ma20' in df.columns:
    df['ma5_above_ma20'] = df['ma5'] > df['ma20']
    
    # 找出金叉和死叉
    golden_cross = (df['ma5_above_ma20'] == True) & (df['ma5_above_ma20'].shift(1) == False)
    death_cross = (df['ma5_above_ma20'] == False) & (df['ma5_above_ma20'].shift(1) == True)
    
    print(f"金叉次数: {golden_cross.sum()}")
    print(f"死叉次数: {death_cross.sum()}")
```

### 场景3：计算波动率

```python
from utils.stock_history_storage import StockHistoryStorage
import numpy as np

storage = StockHistoryStorage()

# 获取历史数据
data = storage.get_stock_history_data(
    symbol='600519',
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 计算日收益率
returns = []
for i in range(1, len(data)):
    prev_price = data[i].get('close_price')
    curr_price = data[i-1].get('close_price')
    if prev_price and curr_price:
        daily_return = (curr_price - prev_price) / prev_price
        returns.append(daily_return)

# 计算波动率（年化）
if returns:
    volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
    print(f"年化波动率: {volatility * 100:.2f}%")
```

### 场景4：识别市场状态

```python
from utils.stock_history_storage import StockHistoryStorage

storage = StockHistoryStorage()

# 获取上证指数历史数据
index_data = storage.get_stock_history_data(
    symbol='000001',  # 上证指数
    start_date='2020-01-01',
    end_date='2024-01-01'
)

# 计算市场状态
if len(index_data) >= 60:
    # 获取最近60天的数据
    recent_data = index_data[:60]
    
    # 计算MA20和MA60
    prices = [r.get('close_price') for r in recent_data if r.get('close_price')]
    if len(prices) >= 60:
        ma20 = sum(prices[:20]) / 20
        ma60 = sum(prices[:60]) / 60
        
        # 判断市场状态
        if ma20 > ma60:
            market_state = '牛市'
        elif ma20 < ma60:
            market_state = '熊市'
        else:
            market_state = '震荡市'
        
        print(f"市场状态: {market_state}")
```

---

## 九、在模型学习中的集成

### 1. 回测引擎集成

**当前实现**：
- `BacktestEngine` 已经使用 `stock_history_data` 表的数据
- 通过 `StockDataSource.get_stock_data()` 获取历史价格数据

**使用方式**：
```python
from utils.backtest_engine import BacktestEngine

engine = BacktestEngine()

# 回测会自动使用stock_history_data表的数据
result = engine.backtest_with_parameters(
    start_date='2020-01-01',
    end_date='2024-01-01',
    parameters={...}
)
```

### 2. 参数优化集成

**当前实现**：
- `ModelOptimizer` 使用 `BacktestEngine` 进行回测
- `BacktestEngine` 会自动使用 `stock_history_data` 表的数据

**使用方式**：
```python
from utils.model_optimizer import ModelOptimizer

optimizer = ModelOptimizer()

# 优化会自动使用stock_history_data表的数据进行回测
result = optimizer.optimize_weights_grid_search(
    start_date='2020-01-01',
    end_date='2024-01-01'
)
```

### 3. 性能评估集成

**当前实现**：
- `ModelPerformanceEvaluator` 可以关联 `stock_history_data` 表的数据
- 用于计算实际涨跌幅和评估预测准确性

**使用方式**：
```python
from utils.model_performance_evaluator import ModelPerformanceEvaluator

evaluator = ModelPerformanceEvaluator()

# 评估会自动关联stock_history_data表的数据
result = evaluator.evaluate_prediction_performance(days=30)
```

---

## 十、数据使用检查清单

### ✅ 数据完整性检查

```sql
-- 1. 检查数据量
SELECT COUNT(*) as total_records FROM stock_history_data;

-- 2. 检查数据时间范围
SELECT 
    MIN(trade_date) as earliest_date,
    MAX(trade_date) as latest_date
FROM stock_history_data;

-- 3. 检查技术指标完整性
SELECT 
    COUNT(*) as total,
    COUNT(ma5) as has_ma5,
    COUNT(rsi) as has_rsi,
    COUNT(macd) as has_macd
FROM stock_history_data
WHERE trade_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR);
```

### ✅ 数据质量检查

```sql
-- 检查价格数据有效性
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN close_price > 0 THEN 1 END) as valid_price,
    COUNT(CASE WHEN volume > 0 THEN 1 END) as valid_volume
FROM stock_history_data
WHERE trade_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR);
```

---

## 十一、总结

### ✅ 已实现的功能

1. **数据存储**：近10年历史数据已存储在 `stock_history_data` 表
2. **数据获取**：`StockHistoryStorage.get_stock_history_data()` 方法可以获取数据
3. **回测集成**：`BacktestEngine` 已使用历史数据进行回测
4. **参数优化**：`ModelOptimizer` 已使用历史数据进行优化
5. **技术指标**：技术指标已计算并存储在表中

### 📊 使用建议

1. **优先使用数据库数据**：避免重复获取实时数据
2. **批量查询优化**：对于多只股票，使用批量查询
3. **数据缓存**：对于频繁查询的数据，使用缓存
4. **数据完整性检查**：定期检查数据完整性

### 🎯 下一步优化建议

1. **增加数据聚合功能**：将日线数据聚合为周线、月线数据
2. **增加数据统计功能**：提供数据统计和分析工具
3. **增加数据可视化**：提供数据可视化功能
4. **增加数据导出功能**：支持导出为CSV、Excel等格式

---

## 修复日期
2026-01-14
