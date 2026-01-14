# Alpha Vantage API 配置说明

## ✅ API密钥已配置

**API密钥**: `F2HOLBGJCDQBIE7W`

**状态**: ✅ 已测试，可以正常获取数据

## 测试结果

- ✅ 成功获取 AAPL 数据：100条记录
- ✅ 成功获取 MSFT 数据：100条记录  
- ✅ 成功获取 GOOGL 数据：100条记录

**数据日期范围**: 2025-08-19 到 2026-01-09（最近100个交易日）

## 配置方式

### 方式1：使用环境变量（推荐）

**Windows PowerShell**:
```powershell
# 当前会话
$env:ALPHA_VANTAGE_API_KEY = "F2HOLBGJCDQBIE7W"

# 永久设置（需要管理员权限）
[System.Environment]::SetEnvironmentVariable('ALPHA_VANTAGE_API_KEY', 'F2HOLBGJCDQBIE7W', 'User')
```

**Windows CMD**:
```cmd
setx ALPHA_VANTAGE_API_KEY "F2HOLBGJCDQBIE7W"
```

**Linux/Mac**:
```bash
export ALPHA_VANTAGE_API_KEY="F2HOLBGJCDQBIE7W"
# 或添加到 ~/.bashrc 或 ~/.zshrc
echo 'export ALPHA_VANTAGE_API_KEY="F2HOLBGJCDQBIE7W"' >> ~/.bashrc
```

### 方式2：使用配置文件

已创建配置文件：`config_us_stock_api.py`

```python
# 直接导入使用
from config_us_stock_api import ALPHA_VANTAGE_API_KEY

from data_source.us_stock_data_source_enhanced import EnhancedUSStockDataSource

ds = EnhancedUSStockDataSource(alpha_vantage_api_key=ALPHA_VANTAGE_API_KEY)
```

### 方式3：直接传入密钥

```python
from data_source.us_stock_data_source_enhanced import EnhancedUSStockDataSource

ds = EnhancedUSStockDataSource(alpha_vantage_api_key="F2HOLBGJCDQBIE7W")
df = ds.get_stock_data('AAPL', period='1y')
```

## 使用说明

### 自动切换机制

增强版数据源会按以下优先级自动尝试：
1. **akshare**（优先）
2. **yfinance**（备用）
3. **Alpha Vantage**（备用，已配置）
4. **Polygon.io**（可选）
5. **Finnhub**（可选）

如果前面的数据源失败，会自动切换到下一个。

### 免费版限制

- **每分钟**: 最多5次请求
- **每天**: 最多500次请求
- **数据量**: 每次请求最多返回最近100条数据（`outputsize=compact`）

### 注意事项

1. **速率限制**: 系统已自动处理，每次请求后等待12秒
2. **数据量限制**: 免费版只能获取最近100个交易日的数据
3. **数据完整性**: 如果需要更多历史数据，建议：
   - 使用付费版（`outputsize=full`）
   - 或结合其他数据源（akshare、yfinance）

## 测试脚本

运行测试脚本验证配置：

```bash
py scripts\test_alpha_vantage.py
```

## 集成到现有系统

如果需要将Alpha Vantage集成到现有的`USStockDataSource`，可以：

1. **修改现有代码**，在`us_stock_data_source.py`中导入增强版：
```python
from data_source.us_stock_data_source_enhanced import EnhancedUSStockDataSource

# 使用增强版
ds = EnhancedUSStockDataSource(alpha_vantage_api_key="F2HOLBGJCDQBIE7W")
```

2. **或者**直接替换`USStockDataSource`为`EnhancedUSStockDataSource`

## 总结

✅ **API密钥已配置并测试通过**
✅ **可以正常获取美股数据**
✅ **已集成到增强版数据源**
✅ **自动切换机制已启用**

现在系统可以在akshare和yfinance都失败时，自动使用Alpha Vantage获取数据！
