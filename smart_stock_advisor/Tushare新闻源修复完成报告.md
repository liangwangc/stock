# Tushare新闻源修复完成报告

**日期**：2026-01-16  
**问题**：Tushare API获取的新闻不对版

---

## 一、问题分析

### 1.1 原问题

用户反馈：当前Tushare根据API获取到的新闻不对版

### 1.2 原因分析

1. **使用了错误的API接口**：
   - 原代码使用 `cctv_news` 接口（央视新闻）
   - 应该使用 `news` 接口，支持多个新闻源

2. **字段名不匹配**：
   - 原代码查找 `publish_time` 字段
   - 实际返回的字段是 `datetime`

3. **缺少多新闻源支持**：
   - 原代码只支持单一新闻源
   - 用户需要支持多个新闻源（yicai、fenghuang、10jqka等）

---

## 二、修复内容

### 2.1 改用正确的API接口

**修改前**：
```python
df = self.pro.cctv_news(symbol=symbol, limit=limit)
```

**修改后**：
```python
df = self.pro.news(src=src, start_date=start_date, end_date=end_date)
```

### 2.2 支持多个新闻源

新增支持的新闻源：
- `yicai` - 第一财经
- `fenghuang` - 凤凰财经
- `10jqka` - 同花顺
- `jinrongjie` - 金融界
- `sina` - 新浪财经
- `yuncaijing` - 云财经
- `eastmoney` - 东方财富
- `cctv` - 央视新闻（备用）

### 2.3 修正字段名

**修改前**：
```python
for field in ['publish_time', 'time', 'date', 'datetime']:
```

**修改后**：
```python
for field in ['datetime', 'publish_time', 'time', 'date']:  # datetime优先
```

### 2.4 添加API频率限制处理

- 检测频率限制错误
- 在 `get_market_news()` 中，每次调用后等待60秒
- 在 `get_stock_news()` 中，只从第一个新闻源获取（避免等待时间过长）

---

## 三、测试结果

### 3.1 成功测试

**第一财经（yicai）**：
- ✅ 成功获取到 415 条新闻
- ✅ 数据字段：`datetime`, `content`, `title`
- ✅ 数据格式正确

### 3.2 API频率限制

**限制说明**：
- 每分钟最多访问1次
- 每小时最多访问2次（某些源）

**影响**：
- 连续调用多个新闻源会受到限制
- 代码已添加等待机制，但会显著增加获取时间

**建议**：
- 如果需要获取多个新闻源，建议分批获取或增加等待时间
- 或者只使用一个主要的新闻源（如第一财经）

---

## 四、代码改进

### 4.1 数据字段解析

根据实际测试结果，正确解析以下字段：
- `datetime` - 发布时间（优先）
- `title` - 标题
- `content` - 内容

### 4.2 错误处理

- 检测频率限制错误并记录警告
- 单个新闻源失败不影响其他源
- 详细的错误日志

### 4.3 性能优化

- `get_market_news()`：依次调用各个新闻源，每次等待60秒
- `get_stock_news()`：只从第一个新闻源获取，避免长时间等待

---

## 五、使用说明

### 5.1 基本使用

代码已自动集成，您的配置中已有 `TUSHARE_TOKEN`，系统会自动使用修复后的代码。

### 5.2 获取市场新闻

```python
from quant_trading_platform.news.tushare_news_source import TuShareNewsSource

source = TuShareNewsSource(token=YOUR_TOKEN)
news = source.get_market_news(limit=20)  # 会依次调用各个新闻源，需要等待
```

### 5.3 获取股票新闻

```python
news = source.get_stock_news("000001", limit=10)  # 只从第一个新闻源获取
```

---

## 六、注意事项

### 6.1 API频率限制

- **限制**：每分钟最多1次，每小时最多2次
- **影响**：获取多个新闻源需要较长时间
- **建议**：根据实际需求选择使用单个或多个新闻源

### 6.2 权限要求

- `news` 接口可能需要足够的积分等级
- 如果提示"无权限"，需要检查Tushare账号的积分等级

### 6.3 数据格式

- 返回的数据包含：`datetime`, `title`, `content`
- 如果没有标题，会设置为空字符串（按您的要求）

---

## 七、测试验证

### 7.1 测试脚本

已创建测试脚本：
- `scripts/test_tushare_news_sources.py` - 测试各个新闻源
- `scripts/test_tushare_api_news.py` - 测试修复后的新闻源类

### 7.2 测试结果

✅ **第一财经（yicai）**：成功获取415条新闻  
⚠️ **其他新闻源**：受API频率限制影响

---

## 八、总结

### 8.1 修复完成

- ✅ 改用正确的 `news` 接口
- ✅ 支持多个新闻源
- ✅ 修正字段名（datetime）
- ✅ 添加频率限制处理
- ✅ 改进错误处理和日志

### 8.2 当前状态

- ✅ 代码已修复并可用
- ✅ 第一财经新闻源测试成功
- ⚠️ 受API频率限制影响，获取多个新闻源需要等待

### 8.3 建议

1. **日常使用**：主要使用第一财经新闻源（yicai），数据量大且稳定
2. **批量获取**：如果需要多个新闻源，建议分批获取或增加等待时间
3. **权限升级**：如果需要更高频率的API调用，可以考虑升级Tushare账号积分等级

---

**最后更新**：2026-01-16
