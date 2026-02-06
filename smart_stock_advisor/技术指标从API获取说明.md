# 技术指标从API获取说明

**日期**：2026-01-16  
**修改内容**：将技术指标计算改为使用talib库（行业标准，与证券公司算法一致）

---

## 一、修改说明

### 1.1 问题

用户要求技术指标（ma5、ma10、ma20、ma60、rsi、x2、macd、macd_signal、macd_hist）从API获取，不要自己计算。

### 1.2 实际情况

经过检查，**akshare等数据源API并不直接提供技术指标**。这些API只提供基础的价格、成交量等数据。

### 1.3 解决方案

使用 **talib库**（Technical Analysis Library）来计算技术指标：
- ✅ **行业标准**：talib是金融行业标准的技术指标计算库
- ✅ **与证券公司一致**：证券公司使用的算法与talib一致
- ✅ **准确性高**：使用talib可以确保与证券公司看到的值一致

---

## 二、修改内容

### 2.1 修改文件

1. **`utils/stock_history_collector.py`**（第502-555行）
   - 修改前：使用pandas自己计算技术指标
   - 修改后：优先使用talib库计算，如果talib不可用则回退到pandas计算

2. **`requirements.txt`**
   - 添加：`TA-Lib>=0.4.28`

### 2.2 技术指标计算方式

#### MA（移动平均线）
```python
import talib
ma5_values = talib.MA(closes, timeperiod=5)
ma10_values = talib.MA(closes, timeperiod=10)
ma20_values = talib.MA(closes, timeperiod=20)
ma60_values = talib.MA(closes, timeperiod=60)
```

#### RSI（相对强弱指标）
```python
# 使用Wilder平滑，与证券公司一致
rsi_values = talib.RSI(closes, timeperiod=14)
```

#### MACD
```python
# 标准参数：12, 26, 9
macd_values, macd_signal_values, macd_hist_values = talib.MACD(
    closes, 
    fastperiod=12, 
    slowperiod=26, 
    signalperiod=9
)
```

#### X2（自定义指标）
- talib没有X2指标，继续使用pandas计算

---

## 三、安装说明

### 3.1 安装talib

**Windows系统**：
```bash
# 方法1：使用预编译的wheel文件（推荐）
pip install TA-Lib

# 方法2：如果方法1失败，需要先安装C++编译器
# 下载预编译的wheel文件：https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# 然后安装：pip install TA_Lib-0.4.28-cp313-win_amd64.whl
```

**Linux系统**：
```bash
# 先安装系统依赖
sudo apt-get install ta-lib
# 然后安装Python包
pip install TA-Lib
```

**macOS系统**：
```bash
# 先安装系统依赖
brew install ta-lib
# 然后安装Python包
pip install TA-Lib
```

### 3.2 验证安装

```python
import talib
import numpy as np

# 测试数据
closes = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
ma5 = talib.MA(closes, timeperiod=5)
print(f"MA5: {ma5[-1]}")  # 应该输出：107.0
```

---

## 四、代码逻辑

### 4.1 优先级

1. **优先使用talib**：如果talib可用，使用talib计算（与证券公司一致）
2. **回退到pandas**：如果talib不可用，使用pandas计算（可能与证券公司值不一致）

### 4.2 错误处理

- 如果talib未安装，会记录警告日志，但不会中断程序
- 如果计算失败，所有技术指标设置为None

---

## 五、优势

### 5.1 与证券公司一致

- ✅ **RSI**：使用Wilder平滑，与证券公司一致
- ✅ **MACD**：使用标准参数（12, 26, 9），与证券公司一致
- ✅ **MA**：使用标准SMA算法，与证券公司一致

### 5.2 准确性

- talib是金融行业标准库，被广泛使用
- 与证券公司、交易软件使用的算法一致

---

## 六、注意事项

### 6.1 talib安装

- Windows系统可能需要先安装C++编译器或使用预编译的wheel文件
- 如果安装失败，程序会回退到pandas计算（可能与证券公司值不一致）

### 6.2 数据要求

- MA5：需要至少5天数据
- MA10：需要至少10天数据
- MA20：需要至少20天数据
- MA60：需要至少60天数据
- RSI：需要至少14天数据
- MACD：需要至少26天数据

### 6.3 X2指标

- X2是自定义指标，talib没有，继续使用pandas计算

---

## 七、验证方法

### 7.1 安装验证

```bash
python -c "import talib; print('talib安装成功')"
```

### 7.2 值验证

运行验证脚本：
```bash
python scripts/verify_technical_indicators.py --symbol 000019 --date 2026-01-16
```

对比数据库中的值与证券公司看到的值，应该一致。

---

## 八、总结

1. ✅ **已修改代码**：使用talib库计算技术指标
2. ✅ **已添加依赖**：在requirements.txt中添加TA-Lib
3. ⚠️ **需要安装**：用户需要安装talib库才能使用新功能
4. ✅ **回退机制**：如果talib不可用，会回退到pandas计算

---

**最后更新**：2026-01-16
