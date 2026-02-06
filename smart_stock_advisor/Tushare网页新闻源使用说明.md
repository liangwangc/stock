# Tushare网页新闻源使用说明

**日期**：2026-01-16  
**说明**：新增从Tushare新闻聚合页面获取数据的功能

---

## 一、功能概述

新增了 `TushareWebNewsSource` 新闻源类，可以从以下Tushare新闻聚合页面获取数据：

1. **第一财经** - https://tushare.pro/news/yicai
2. **凤凰财经** - https://tushare.pro/news/fenghuang
3. **同花顺** - https://tushare.pro/news/10jqka
4. **金融界** - https://tushare.pro/news/jinrongjie
5. **新浪财经** - https://tushare.pro/news/sina
6. **云财经** - https://tushare.pro/news/yuncaijing
7. **东方财富** - https://tushare.pro/news/eastmoney

---

## 二、实现特点

### 2.1 智能解析

- **多种选择器**：自动尝试多种常见的HTML选择器来定位新闻项
- **灵活的时间解析**：支持多种时间格式，包括绝对时间和相对时间（如"1小时前"、"昨天"等）
- **容错处理**：如果某个页面解析失败，不影响其他页面的数据获取

### 2.2 数据提取

- **标题提取**：优先从链接、标题标签中提取，如果没有标题则为空字符串
- **内容提取**：从内容、摘要、描述等字段提取
- **时间提取**：从时间、日期标签或文本中提取，支持多种格式
- **URL提取**：自动处理相对URL和绝对URL

### 2.3 数据聚合

- **多源聚合**：从所有配置的新闻源页面获取数据并聚合
- **自动去重**：基于标题进行去重
- **时间排序**：按时间倒序排列（最新的在前）

---

## 三、使用方法

### 3.1 直接使用

```python
from news.tushare_web_news_source import TushareWebNewsSource

# 创建新闻源实例
source = TushareWebNewsSource()

# 获取市场新闻
market_news = source.get_market_news(limit=20)

# 获取股票相关新闻（通过关键词筛选）
stock_news = source.get_stock_news("000001", limit=10)
```

### 3.2 通过统一新闻源使用

`TushareWebNewsSource` 已自动集成到 `UnifiedNewsSource` 中，无需额外配置：

```python
from news.unified_news_source import UnifiedNewsSource

# 创建统一新闻源（会自动包含Tushare网页新闻源）
unified = UnifiedNewsSource()

# 获取市场新闻（会自动从所有新闻源聚合，包括Tushare网页新闻源）
market_news = unified.get_market_news(limit=20)

# 获取股票新闻（会自动从所有新闻源聚合）
stock_news = unified.get_stock_news("000001", limit=10)
```

---

## 四、数据结构

每条新闻包含以下字段：

```python
{
    'title': str,        # 标题（如果没有则为空字符串）
    'content': str,      # 内容/摘要
    'time': datetime,    # 发布时间
    'url': str,          # 新闻链接
    'source': str,       # 新闻源名称（如"第一财经"、"凤凰财经"等）
    'type': str          # 新闻类型（固定为'market'）
}
```

---

## 五、配置说明

### 5.1 新闻源配置

新闻源配置在 `TushareWebNewsSource.NEWS_SOURCES` 字典中：

```python
NEWS_SOURCES = {
    'yicai': '第一财经',
    'fenghuang': '凤凰财经',
    '10jqka': '同花顺',
    'jinrongjie': '金融界',
    'sina': '新浪财经',
    'yuncaijing': '云财经',
    'eastmoney': '东方财富'
}
```

### 5.2 添加新新闻源

如果需要添加新的新闻源，只需：

1. 在 `NEWS_SOURCES` 字典中添加新的映射
2. 确保URL格式为 `https://tushare.pro/news/{source_key}`

---

## 六、解析策略

### 6.1 HTML结构识别

代码会按以下顺序尝试识别新闻列表：

1. **通过类名查找**：尝试常见的类名（如 `news-list`、`news-item`、`item` 等）
2. **通过标签查找**：查找 `article`、`div`、`li` 等标签
3. **通过时间模式查找**：查找包含时间信息的元素

### 6.2 字段提取

- **标题**：优先从 `a`、`h1-h4`、`.title` 等元素提取
- **内容**：从 `.content`、`.summary`、`.desc`、`p` 等元素提取
- **时间**：从 `.time`、`.date`、`time` 标签或文本中提取
- **URL**：从 `a` 标签的 `href` 属性提取

### 6.3 时间解析

支持的时间格式：

- `%Y-%m-%d %H:%M:%S`
- `%Y-%m-%d %H:%M`
- `%Y-%m-%d`
- `%Y/%m/%d %H:%M:%S`
- 相对时间：`1分钟前`、`2小时前`、`3天前`、`昨天`、`今天`

---

## 七、测试

### 7.1 运行测试脚本

```bash
cd smart_stock_advisor
python scripts/test_tushare_web_news.py
```

### 7.2 测试内容

- 初始化新闻源
- 获取市场新闻（从所有配置的页面）
- 获取股票相关新闻（通过关键词筛选）
- 验证数据格式和内容

---

## 八、注意事项

### 8.1 依赖要求

- `requests`：用于HTTP请求
- `beautifulsoup4`：用于HTML解析

安装命令：
```bash
pip install requests beautifulsoup4
```

### 8.2 性能考虑

- 每个页面请求有15秒超时限制
- 如果某个页面解析失败，会继续处理其他页面
- 建议合理设置 `limit` 参数，避免获取过多数据

### 8.3 错误处理

- 网络错误：会记录警告日志，但不中断其他页面的处理
- 解析错误：会记录调试日志，跳过无法解析的新闻项
- 超时：会记录警告日志，跳过超时的页面

---

## 九、日志

新闻源会记录以下日志：

- **INFO级别**：成功获取的新闻数量
- **DEBUG级别**：解析过程中的详细信息
- **WARNING级别**：网络错误、超时等警告信息

---

## 十、示例输出

```
从 第一财经 (https://tushare.pro/news/yicai) 提取到 15 条新闻
从 凤凰财经 (https://tushare.pro/news/fenghuang) 提取到 12 条新闻
从 同花顺 (https://tushare.pro/news/10jqka) 提取到 18 条新闻
...
从Tushare网页聚合获取到 20 条市场新闻（去重后）
```

---

**最后更新**：2026-01-16
