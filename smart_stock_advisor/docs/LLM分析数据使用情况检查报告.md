# LLM分析数据使用情况检查报告

## 一、检查范围

检查股票预测和新闻处理模块是否使用了 `news_articles` 表中 `llm_*` 开头的字段（LLM分析结果）。

---

## 二、数据库字段情况

### 2.1 LLM分析字段

`news_articles` 表中已存在以下LLM分析字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `llm_category` | VARCHAR(50) | LLM分类（宏观经济/商品期货/金融市场/地缘政治/行业政策/非金融类） |
| `llm_subcategory` | VARCHAR(100) | LLM子分类 |
| `llm_keywords` | TEXT (JSON) | LLM提取的关键词（JSON格式） |
| `llm_sentiment_score` | DECIMAL(8,4) | LLM情感得分（-1到1） |
| `llm_summary` | TEXT | LLM生成的总结 |
| `llm_impact_markets` | VARCHAR(200) | 影响的市场/品种 |
| `llm_is_market_relevant` | TINYINT(1) | 是否与金融市场相关 |
| `llm_analyzed_at` | DATETIME | LLM分析时间 |

### 2.2 同步字段

LLM分析结果还会同步更新到股票预测使用的字段：

| LLM字段 | 同步到字段 | 说明 |
|---------|-----------|------|
| `llm_sentiment_score` | `sentiment_score` | 情感得分（优先使用LLM结果） |
| `llm_sentiment_score` | `sentiment` | 情感倾向（positive/negative/neutral） |
| `llm_sentiment_score` | `is_positive` | 是否正面（基于得分>0.1） |
| `llm_sentiment_score` | `is_negative` | 是否负面（基于得分<-0.1） |
| `llm_keywords` | `keywords` | 关键词（如果LLM有关键词） |

**注意**：根据 `news-analysis-system-main/src/database/db_handle.py` 的 `import_results` 函数，LLM分析结果会同时更新LLM字段和股票预测字段。

---

## 三、当前使用情况

### 3.1 新闻数据获取流程

**文件**：`smart_stock_advisor/predictor/stock_predictor.py`  
**方法**：`calculate_news_score()` (第885-1211行)

**流程**：
1. 从数据库获取新闻（第924-960行）
   - 调用 `NewsStorage.get_today_news_by_symbol()` 获取股票当天新闻
   - 调用 `NewsStorage.get_today_market_news()` 获取市场新闻
   - 使用 `SELECT * FROM news_articles` 查询（会包含所有字段，包括LLM字段）

2. 数据格式转换（第657-673行，`news_storage.py`）
   ```python
   news = {
       'title': row.get('title', ''),
       'content': row.get('content', '') or row.get('summary', ''),
       'time': row.get('publish_time'),
       'url': row.get('source_url', ''),
       'source': row.get('source', 'unknown'),
       'sentiment': row.get('sentiment', 'neutral'),  # ← 使用同步字段
       'sentiment_score': float(row.get('sentiment_score', 0.0)),  # ← 使用同步字段
       'sentiment_confidence': float(row.get('sentiment_confidence', 0.0)),
       'is_policy': bool(row.get('is_policy', False)),
       'relevance_type': row.get('relevance_type', 'direct'),
       'relevance_score': float(row.get('relevance_score', 1.0)),
   }
   ```

3. 情感分析（第1076行）
   ```python
   sentiment_results = self.sentiment_analyzer.analyze_batch(news_list)
   ```
   - **问题**：使用 `sentiment_analyzer` 重新分析新闻内容，而不是使用已有的LLM分析结果

### 3.2 当前问题

#### ❌ 问题1：未直接使用LLM字段

虽然数据库查询会返回所有字段（包括 `llm_*` 字段），但在格式转换时：
- **只使用了同步字段**（`sentiment_score`, `sentiment`）
- **未使用LLM字段**（`llm_sentiment_score`, `llm_category`, `llm_summary` 等）

#### ❌ 问题2：重复分析

在 `calculate_news_score()` 方法中：
- 第1076行：调用 `sentiment_analyzer.analyze_batch(news_list)` 重新分析新闻
- 即使数据库中已有LLM分析结果，也会重新进行关键词分析

#### ✅ 间接使用（通过同步字段）

虽然未直接使用LLM字段，但通过同步机制：
- LLM分析结果会更新到 `sentiment_score` 字段
- 股票预测会使用 `sentiment_score` 字段
- **因此，LLM分析结果实际上被间接使用了**

---

## 四、如何使用LLM分析数据

### 4.1 优先使用LLM情感得分

**位置**：`smart_stock_advisor/utils/news_storage.py`  
**方法**：`get_today_news_by_symbol()` 和 `get_today_market_news()`

**建议修改**：
```python
# 在格式转换时，优先使用LLM情感得分
sentiment_score = (
    float(row.get('llm_sentiment_score', 0.0)) 
    if row.get('llm_sentiment_score') is not None 
    else float(row.get('sentiment_score', 0.0))
)

# 如果LLM有分析结果，使用LLM的情感倾向
if row.get('llm_sentiment_score') is not None:
    if row.get('llm_sentiment_score') > 0.1:
        sentiment = 'positive'
    elif row.get('llm_sentiment_score') < -0.1:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
else:
    sentiment = row.get('sentiment', 'neutral')
```

### 4.2 使用LLM分类筛选新闻

**位置**：`smart_stock_advisor/predictor/stock_predictor.py`  
**方法**：`calculate_news_score()`

**建议修改**：
```python
# 只使用与金融市场相关的新闻
if row.get('llm_is_market_relevant') == 0:
    continue  # 跳过非金融类新闻

# 按LLM分类筛选
llm_category = row.get('llm_category')
if llm_category == '非金融类':
    continue  # 跳过非金融类新闻
```

### 4.3 使用LLM总结增强预测

**位置**：`smart_stock_advisor/predictor/stock_predictor.py`  
**方法**：`predict()` 和 `predict_before_close()`

**建议修改**：
```python
# 在预测结果中包含LLM总结
if news.get('llm_summary'):
    prediction_report['news_summary'] = news['llm_summary']
    prediction_report['news_category'] = news.get('llm_category')
    prediction_report['news_subcategory'] = news.get('llm_subcategory')
```

### 4.4 跳过已分析的新闻

**位置**：`smart_stock_advisor/predictor/stock_predictor.py`  
**方法**：`calculate_news_score()`

**建议修改**：
```python
# 如果新闻已有LLM分析结果，跳过重新分析
if row.get('llm_analyzed_at') is not None:
    # 直接使用LLM分析结果，不调用 sentiment_analyzer
    sentiment_score = float(row.get('llm_sentiment_score', 0.0))
    sentiment = 'positive' if sentiment_score > 0.1 else ('negative' if sentiment_score < -0.1 else 'neutral')
else:
    # 如果没有LLM分析结果，使用关键词分析
    sentiment_results = self.sentiment_analyzer.analyze_batch([news])
```

---

## 五、结论

### 5.1 当前状态

✅ **间接使用**：
- LLM分析结果通过同步机制更新到 `sentiment_score` 字段
- 股票预测使用 `sentiment_score` 字段，因此间接使用了LLM分析结果

❌ **未直接使用**：
- 未直接使用 `llm_sentiment_score`、`llm_category`、`llm_summary` 等字段
- 即使有LLM分析结果，仍会重新进行关键词分析

### 5.2 优化建议

1. **优先使用LLM情感得分**
   - 在 `news_storage.py` 中，优先使用 `llm_sentiment_score`
   - 如果LLM有分析结果，直接使用，不重新分析

2. **使用LLM分类筛选**
   - 只使用 `llm_is_market_relevant = 1` 的新闻
   - 跳过 `llm_category = '非金融类'` 的新闻

3. **使用LLM总结增强预测**
   - 在预测结果中包含 `llm_summary`、`llm_category` 等信息
   - 提高预测报告的可读性和准确性

4. **避免重复分析**
   - 如果 `llm_analyzed_at IS NOT NULL`，跳过 `sentiment_analyzer.analyze_batch()`
   - 直接使用LLM分析结果

### 5.3 预期效果

- ✅ **提高准确性**：LLM分析比关键词分析更准确
- ✅ **提高效率**：避免重复分析，减少计算开销
- ✅ **增强可解释性**：使用LLM总结和分类，提高预测报告的可读性
- ✅ **更好的筛选**：使用LLM分类，只分析相关的金融新闻

---

## 六、修改优先级

| 优先级 | 修改项 | 影响 | 难度 |
|--------|--------|------|------|
| 🔴 **高** | 优先使用LLM情感得分 | 提高准确性，避免重复分析 | 低 |
| 🟡 **中** | 使用LLM分类筛选 | 提高相关性，减少噪音 | 中 |
| 🟢 **低** | 使用LLM总结增强预测 | 提高可读性 | 低 |

---

## 七、相关文件

- `smart_stock_advisor/utils/news_storage.py` - 新闻数据获取和格式转换
- `smart_stock_advisor/predictor/stock_predictor.py` - 股票预测主逻辑
- `news-analysis-system-main/src/database/db_handle.py` - LLM分析结果存储逻辑

---

**报告生成时间**：2026-01-23  
**检查范围**：股票预测和新闻处理模块  
**结论**：LLM分析数据被间接使用（通过同步字段），但未直接使用LLM字段，存在优化空间。
