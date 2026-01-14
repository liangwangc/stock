# 自动买卖股票功能说明

## ✅ 已实现的功能

我已经为你的量化交易平台添加了**实盘交易模块框架**，包括：

### 1. 交易接口框架
- **BaseTrader**（`trading/base_trader.py`）：交易接口基类，定义了买入、卖出、查询持仓等标准接口
- **SimulatedTrader**（`trading/simulated_trader.py`）：模拟交易接口，用于测试，不涉及真实资金

### 2. 实时交易管理器
- **RealtimeTrader**（`trading/realtime_trader.py`）：实时监控市场信号并自动执行交易

### 3. 运行方式

#### 模拟交易（测试用）

```bash
# 首先安装新依赖
pip install schedule

# 运行模拟实时交易
python realtime_trading.py
```

## ⚠️ 重要说明

### 当前状态：模拟交易模式

**当前实现使用的是模拟交易接口（SimulatedTrader），不涉及真实资金！**

特点：
- ✅ 完全模拟的交易环境
- ✅ 包含手续费、滑点等真实交易成本
- ✅ 可用于测试交易逻辑和策略
- ❌ **不涉及真实资金**
- ❌ **不会在真实市场执行交易**

### 要实现真实自动交易需要：

1. **开通支持API的券商账户**
   - 华泰证券、东方财富等部分券商支持API交易
   - 需要申请API接口权限

2. **实现券商API接口**
   - 需要根据券商提供的API文档实现具体的交易接口
   - 替换 `SimulatedTrader` 为真实的券商API接口

3. **风险评估和合规**
   - 实盘交易存在资金损失风险
   - 需要遵守相关法律法规
   - 建议先在模拟环境充分测试

## 使用示例

### 模拟交易测试

```python
from trading.simulated_trader import SimulatedTrader
from data_source import AkshareDataSource

# 创建模拟交易接口
data_source = AkshareDataSource()
trader = SimulatedTrader(
    initial_cash=1000000,  # 初始资金100万
    commission=0.0003,      # 手续费万三
    slippage=0.001,        # 滑点0.1%
    data_source=data_source
)

# 买入股票
result = trader.buy("600519", amount=50000)  # 买入5万元
print(result)

# 查询持仓
position = trader.get_position("600519")
print(position)

# 卖出股票
result = trader.sell("600519", shares=100)
print(result)

# 查询账户余额
balance = trader.get_balance()
print(balance)
```

### 实时自动交易（模拟模式）

运行 `python realtime_trading.py`，系统会：
- 每5分钟检查一次交易信号
- 根据策略自动执行买入/卖出
- 显示账户状态和交易记录

## 接入真实券商API（示例框架）

如果你要接入真实券商API，需要创建类似这样的接口：

```python
# trading/broker_trader.py
from trading.base_trader import BaseTrader

class BrokerTrader(BaseTrader):
    """真实券商API交易接口"""
    
    def __init__(self, api_key, api_secret, broker_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.broker_url = broker_url
        # 初始化券商API连接...
    
    def buy(self, symbol, amount, price=None):
        # 调用券商API执行买入
        # 返回真实的交易结果
        pass
    
    def sell(self, symbol, shares, price=None):
        # 调用券商API执行卖出
        pass
    
    # 实现其他必需的方法...
```

然后在 `realtime_trading.py` 中使用：

```python
from trading.broker_trader import BrokerTrader

# 使用真实交易接口
trader = BrokerTrader(
    api_key="your_api_key",
    api_secret="your_api_secret",
    broker_url="https://api.broker.com"
)
```

## 风险提示

1. **市场风险**：股票价格波动可能导致资金损失
2. **技术风险**：系统故障可能导致交易失败
3. **策略风险**：策略可能失效，导致持续亏损
4. **建议**：
   - 充分回测后再考虑实盘
   - 先用小额资金测试
   - 设置止损和风险控制
   - 实时监控系统运行

## 文件结构

```
trading/
├── __init__.py              # 模块初始化
├── base_trader.py           # 交易接口基类
├── simulated_trader.py      # 模拟交易接口（测试用）
└── realtime_trader.py       # 实时交易管理器

realtime_trading.py          # 实时交易主程序
实盘交易说明.md              # 详细说明文档
```

## 总结

✅ **已实现**：完整的交易接口框架和模拟交易系统  
⚠️ **需要接入**：真实的券商API才能进行实盘交易  
📝 **建议**：先在模拟环境充分测试策略和交易逻辑

更多详细信息请查看 `实盘交易说明.md` 文件。

