# API调用禁用说明

**创建时间**：2026-01-23  
**说明**：禁用 smart_stock_advisor 自己的新闻获取 API 调用，统一使用 news-analysis-system-main

---

## 📋 修改内容

### 已禁用的功能

**目标**：禁用 smart_stock_advisor 自己的新闻获取 API 调用，统一使用 news-analysis-system-main

**原因**：
- ✅ 统一新闻获取来源
- ✅ 避免重复调用 API
- ✅ 简化系统架构

---

## 🔍 已禁用的位置

### 1. stock_predictor.py - 股票预测时的新闻获取

**文件**：`predictor/stock_predictor.py`

**位置**：`_get_news_for_prediction()` 方法

**原代码**（已禁用）：
```python
# 如果数据库没有新闻，从API获取
if not use_database_news or not market_news:
    try:
        # 获取更多市场新闻用于筛选
        if not market_news:
            market_news = self.news_source.get_market_news(NEWS_CONFIG['news_count'] * 3)
        
        # 获取直接提到股票的新闻
        if not direct_news:
            if hasattr(self.news_source, 'sources'):
                for source_name, source in self.news_source.sources:
                    try:
                        news = source.get_stock_news(symbol, NEWS_CONFIG['news_count'])
                        # ...
                    except Exception as e:
                        self.logger.debug(f"从 {source_name} 获取新闻失败: {str(e)}")
    except Exception as e:
        self.logger.debug(f"从API获取新闻失败: {str(e)}")
```

**修改后**：
```python
# 【已禁用】如果数据库没有新闻，从API获取
# 注意：当前只从 news-analysis-system-main 获取新闻，不再调用 API
# 如果数据库没有新闻，记录警告但不从 API 获取
if not use_database_news or not market_news:
    self.logger.warning(f"数据库中没有找到 {symbol} 的新闻，建议检查 news-analysis-system-main 是否正常运行")
    # 【已禁用】以下代码已禁用，不再从 API 获取新闻
    # ... (原代码已注释)
```

**影响**：
- ⚠️ 如果数据库中没有新闻，股票预测时不会从 API 获取
- ✅ 只从数据库读取新闻（由 news-analysis-system-main 写入）
- ✅ 如果数据库没有新闻，会记录警告日志

---

### 2. scheduled_task_manager.py - 定时任务（已修改）

**文件**：`utils/scheduled_task_manager.py`

**位置**：`_execute_news_crawl()` 方法

**状态**：✅ **已修改为调用 news-analysis-system-main**

**当前实现**：
```python
# 直接调用 news-analysis-system-main 的方法
from src.data_processing.get_cls_news import fetch_and_store_news
fetch_and_store_news()
```

**说明**：
- ✅ 不再调用 `UnifiedNewsSource()` 和 `NewsCrawler()`
- ✅ 直接调用 `news-analysis-system-main.fetch_and_store_news()`

---

## 📊 当前状态

### 新闻获取来源

| 位置 | 原来源 | 当前来源 | 状态 |
|------|--------|---------|------|
| **定时任务** | UnifiedNewsSource API | news-analysis-system-main | ✅ 已修改 |
| **股票预测** | UnifiedNewsSource API（备用） | 仅数据库 | ✅ 已禁用 |

### API调用情况

| 功能 | 是否调用 API | 状态 |
|------|------------|------|
| **定时任务** | ❌ 否 | ✅ 已禁用 |
| **股票预测** | ❌ 否 | ✅ 已禁用 |
| **Web界面** | ❌ 否 | ✅ 只读取数据库 |

---

## ⚠️ 注意事项

### 1. 股票预测时的新闻获取

**当前行为**：
- ✅ 优先从数据库获取新闻
- ⚠️ 如果数据库没有新闻，不会从 API 获取（已禁用）
- ⚠️ 会记录警告日志

**建议**：
- ✅ 确保 news-analysis-system-main 正常运行
- ✅ 确保定时任务正常执行
- ✅ 如果数据库没有新闻，检查 news-analysis-system-main 是否正常运行

### 2. 新闻数据来源

**当前架构**：
```
news-analysis-system-main
  └─ fetch_and_store_news() → 获取新闻 → 写入数据库

smart_stock_advisor
  ├─ 定时任务 → 调用 news-analysis-system-main.fetch_and_store_news()
  └─ 股票预测 → 从数据库读取新闻（不再调用 API）
```

**数据流**：
1. news-analysis-system-main 获取新闻并写入数据库
2. smart_stock_advisor 从数据库读取新闻用于预测

---

## ✅ 验证方法

### 1. 检查是否还有 API 调用

**搜索关键词**：
- `UnifiedNewsSource().get_market_news()`
- `UnifiedNewsSource().get_stock_news()`
- `NewsCrawler().crawl_all_news()`
- `news_source.get_market_news()`
- `news_source.get_stock_news()`

**检查位置**：
- `predictor/stock_predictor.py` ✅ 已禁用
- `utils/scheduled_task_manager.py` ✅ 已修改
- `web_app.py` - 检查是否有手动获取新闻的 API

### 2. 检查日志

**股票预测时**：
- 如果数据库没有新闻，应该看到警告日志：
  ```
  数据库中没有找到 {symbol} 的新闻，建议检查 news-analysis-system-main 是否正常运行
  ```

**定时任务执行时**：
- 应该看到：
  ```
  开始执行新闻抓取任务（使用news-analysis-system-main）
  [news-analysis-system-main] 开始抓取财联社新闻...
  ```

---

## 🔄 恢复方法（如果需要）

如果将来需要恢复 API 调用，可以：

1. **恢复 stock_predictor.py**：
   - 取消注释已禁用的代码
   - 移除警告日志

2. **恢复定时任务**：
   - 修改 `_execute_news_crawl()` 方法
   - 恢复使用 `UnifiedNewsSource()` 和 `NewsCrawler()`

---

## ✅ 总结

### 已完成的修改

1. ✅ **定时任务**：已改为调用 news-analysis-system-main
2. ✅ **股票预测**：已禁用 API 调用，只从数据库读取
3. ✅ **代码保留**：已禁用的代码已注释保留，未删除

### 当前架构

- ✅ **统一来源**：所有新闻都来自 news-analysis-system-main
- ✅ **无 API 调用**：smart_stock_advisor 不再调用自己的新闻获取 API
- ✅ **只读数据库**：smart_stock_advisor 只从数据库读取新闻

---

## 🔄 更新记录

### 2026-01-23（完整禁用）
- ✅ 禁用 `stock_predictor.py` 中的 API 调用
- ✅ 禁用 `news_crawler.py` 中的所有方法（`crawl_market_news`, `crawl_stock_news`, `crawl_all_news`）
- ✅ 禁用 `news_task_manager.py` 中的独立启动模式（`_start_task_legacy`）
- ✅ 保留代码但注释禁用，未删除
- ✅ 添加警告日志
- ✅ 创建文档说明修改内容

### 2026-01-23（初始）
- ✅ 禁用 `stock_predictor.py` 中的 API 调用
- ✅ 保留代码但注释禁用
- ✅ 添加警告日志
- ✅ 创建文档说明修改内容
