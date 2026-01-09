# 沪深股市量化交易平台

一个基于Python的量化交易平台，支持A股市场数据获取、策略回测和交易信号生成。

## 功能特性

- 📈 支持沪深股市历史数据获取（使用akshare）
- 🤖 灵活的策略框架，易于扩展
- 📊 完整的回测引擎，支持多种指标分析
- 💹 技术指标计算（MA、MACD、RSI、布林带等）
- 📉 可视化交易结果和收益曲线
- 💰 支持手续费和滑点模拟
- 📊 性能指标分析（收益率、夏普比率、最大回撤等）

## 快速开始

### Windows用户

双击运行 `快速开始.bat` 文件，脚本会自动检查依赖并启动程序。

### Linux/Mac用户

```bash
chmod +x 快速开始.sh
./快速开始.sh
```

### 手动安装

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

如果安装较慢，可以使用国内镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 2. 运行示例策略

```bash
python main.py
```

或者：

```bash
python run.py
```

### 3. 自定义策略

在 `strategies/` 目录下创建你的策略文件，继承 `BaseStrategy` 类并实现 `generate_signals` 方法。

## 项目结构

```
quant_trading_platform/
├── data/              # 数据存储目录
├── strategies/        # 策略文件目录
├── backtest/          # 回测引擎
├── data_source/       # 数据源模块
├── indicators/        # 技术指标计算
├── utils/             # 工具函数
├── config.py          # 配置文件
├── main.py            # 主程序入口
└── requirements.txt   # 依赖包列表
```

## 使用说明

### 数据获取

平台使用 akshare 库获取A股数据，支持：
- 实时行情
- 历史K线数据
- 股票基本信息

### 策略开发

创建一个新策略：

```python
from strategies.base_strategy import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        # 实现你的交易逻辑
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        # ... 你的交易逻辑
        return signals
```

### 回测

回测引擎支持：
- 买入/卖出信号执行
- 持仓管理
- 收益计算
- 性能指标分析（夏普比率、最大回撤等）

## 系统要求

- Python 3.7 或更高版本
- 网络连接（用于获取股票数据）
- 推荐使用Python 3.8+

## 示例输出

运行程序后，你将看到：

1. 数据获取进度
2. 回测执行过程
3. 性能指标报告：
   - 总收益率
   - 年化收益率
   - 基准收益率（买入持有策略）
   - 最大回撤
   - 波动率
   - 夏普比率
   - 交易次数
4. 交易记录详情
5. 可视化图表（如果支持图形界面）

## 注意事项

1. **数据获取**：需要网络连接，首次运行会下载数据，可能需要一些时间
2. **股票代码格式**：使用6位数字代码，如 "000001"（平安银行）、"600519"（贵州茅台）
3. **数据来源**：使用akshare库获取数据，数据来源于公开市场信息
4. **免责声明**：本平台仅用于学习和研究目的，不构成任何投资建议。实盘交易存在风险，请谨慎决策
5. **数据延迟**：历史数据可能存在延迟，不保证实时性
6. **计算精度**：回测结果仅供参考，实际交易结果可能因滑点、手续费等因素有所不同

## 常见问题

**Q: 如何修改回测的股票？**  
A: 在 `main.py` 中修改 `symbol` 变量，或修改 `config.py` 中的 `DEFAULT_STOCKS`

**Q: 如何添加新的技术指标？**  
A: 在 `indicators/technical_indicators.py` 中添加新的指标函数

**Q: 数据获取失败怎么办？**  
A: 检查网络连接，确保可以访问互联网。如果仍然失败，可能是akshare API更新，需要更新akshare库

**Q: 支持实盘交易吗？**  
A: 当前版本仅支持回测，不包含实盘交易功能

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

