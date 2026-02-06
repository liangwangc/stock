# LLM分析结果存储和时间范围设置说明

---

## 一、LLM分析结果存储位置

### 1. 数据库表

**表名**：`news_articles`  
**数据库**：`stock_data`

### 2. 存储字段

LLM分析结果存储在 `news_articles` 表的以下字段：

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `llm_category` | VARCHAR(50) | 主分类 | "宏观经济类" |
| `llm_subcategory` | VARCHAR(100) | 子分类 | "央行政策" |
| `llm_keywords` | TEXT (JSON) | 关键词（JSON格式） | `["降息", "货币政策", "流动性"]` |
| `llm_sentiment_score` | DECIMAL(8,4) | 情感得分（-1到1） | 0.65 |
| `llm_summary` | TEXT | 新闻总结 | "央行宣布降息0.25个百分点..." |
| `llm_impact_markets` | VARCHAR(200) | 影响市场/品种 | "A股,债券市场" |
| `llm_is_market_relevant` | TINYINT(1) | 是否与金融市场相关 | 1（是）/ 0（否） |
| `llm_analyzed_at` | DATETIME | 分析时间（自动设置） | 2026-01-23 15:30:00 |

### 3. 同步字段

LLM分析结果还会同步更新到股票预测使用的字段：

| LLM字段 | 同步到字段 | 说明 |
|---------|-----------|------|
| `llm_sentiment_score` | `sentiment_score` | 情感得分（优先使用LLM结果） |
| `llm_sentiment_score` | `sentiment` | 情感倾向（positive/negative/neutral） |
| `llm_sentiment_score` | `is_positive` | 是否正面（基于得分>0.1） |
| `llm_sentiment_score` | `is_negative` | 是否负面（基于得分<-0.1） |
| `llm_keywords` | `keywords` | 关键词（如果LLM有关键词） |

### 4. 备份文件

分析结果还会备份到本地JSON文件：

**位置**：`news-analysis-system-main/data/backup_results/`  
**文件名格式**：`analysis_results_YYYYMMDD_HHMMSS_{last_hash}.json`

---

## 二、查询LLM分析结果

### SQL查询示例

#### 1. 查询所有已分析的新闻

```sql
SELECT 
    id, title, publish_time,
    llm_category, llm_subcategory, 
    llm_sentiment_score, llm_summary,
    llm_analyzed_at
FROM news_articles
WHERE llm_analyzed_at IS NOT NULL
ORDER BY llm_analyzed_at DESC;
```

#### 2. 查询特定时间范围的LLM分析结果

```sql
SELECT 
    id, title, publish_time,
    llm_category, llm_sentiment_score,
    llm_analyzed_at
FROM news_articles
WHERE llm_analyzed_at IS NOT NULL
  AND llm_analyzed_at >= '2026-01-23 00:00:00'
  AND llm_analyzed_at <= '2026-01-23 23:59:59'
ORDER BY llm_analyzed_at DESC;
```

#### 3. 查询特定分类的LLM分析结果

```sql
SELECT 
    id, title, llm_category, llm_subcategory,
    llm_sentiment_score, llm_summary
FROM news_articles
WHERE llm_category = '宏观经济类'
  AND llm_analyzed_at IS NOT NULL
ORDER BY llm_analyzed_at DESC;
```

#### 4. 统计LLM分析情况

```sql
SELECT 
    COUNT(*) as total_news,
    SUM(CASE WHEN llm_analyzed_at IS NOT NULL THEN 1 ELSE 0 END) as analyzed_count,
    SUM(CASE WHEN llm_analyzed_at IS NULL THEN 1 ELSE 0 END) as unanalyzed_count,
    SUM(CASE WHEN llm_sentiment_score > 0.1 THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN llm_sentiment_score < -0.1 THEN 1 ELSE 0 END) as negative_count
FROM news_articles;
```

---

## 三、时间范围设置功能

### 当前状态

**当前代码**：只分析 `llm_analyzed_at IS NULL` 的新闻（未分析的），**不支持按新闻发布时间过滤**。

### 新增功能：按新闻发布时间范围分析

可以添加时间范围参数，只分析指定时间范围内的新闻。

#### 使用方式

修改 `load_news_after_last_processed()` 函数，添加时间范围参数：

```python
def load_news_after_last_processed(start_date=None, end_date=None):
    """
    从最后处理的新闻之后开始加载（适配 news_articles 表）
    
    Args:
        start_date: 开始日期（可选），格式：'2026-01-23' 或 datetime对象
        end_date: 结束日期（可选），格式：'2026-01-23' 或 datetime对象
    """
    # ... 现有代码 ...
    
    # 添加时间范围过滤
    if start_date or end_date:
        time_conditions = []
        if start_date:
            time_conditions.append("publish_time >= %s")
        if end_date:
            time_conditions.append("publish_time <= %s")
        
        time_filter = " AND " + " AND ".join(time_conditions)
    else:
        time_filter = ""
    
    sql = f"""
        SELECT id, publish_time, content, content_hash, title 
        FROM news_articles 
        WHERE llm_analyzed_at IS NULL {time_filter}
        ORDER BY id
    """
```

#### 调用示例

```python
# 只分析2026-01-23的新闻
df = load_news_after_last_processed(
    start_date='2026-01-23 00:00:00',
    end_date='2026-01-23 23:59:59'
)

# 只分析最近7天的新闻
from datetime import datetime, timedelta
end_date = datetime.now()
start_date = end_date - timedelta(days=7)
df = load_news_after_last_processed(start_date=start_date, end_date=end_date)
```

---

## 四、查看分析结果的方法

### 方法1：通过数据库查询

使用MySQL客户端或数据库管理工具（如Navicat、DBeaver）直接查询 `news_articles` 表。

### 方法2：通过smart_stock_advisor前端

如果前端有新闻查询页面，可以通过页面查看LLM分析结果。

### 方法3：使用Python脚本查询

```python
import pandas as pd
from sqlalchemy import create_engine

# 连接数据库
engine = create_engine("mysql+pymysql://user:password@host:port/stock_data")

# 查询LLM分析结果
sql = """
    SELECT 
        id, title, publish_time,
        llm_category, llm_subcategory,
        llm_sentiment_score, llm_summary,
        llm_analyzed_at
    FROM news_articles
    WHERE llm_analyzed_at IS NOT NULL
    ORDER BY llm_analyzed_at DESC
    LIMIT 100
"""

df = pd.read_sql(sql, engine)
print(df)
```

---

## 五、常见问题

### Q1: 分析结果在哪里查看？

A: 分析结果存储在 `stock_data.news_articles` 表的 `llm_*` 字段中。可以通过SQL查询或前端页面查看。

### Q2: 如何知道哪些新闻已经分析过了？

A: 查询 `llm_analyzed_at IS NOT NULL` 的新闻，表示已经分析过。

### Q3: 可以重新分析已分析的新闻吗？

A: 当前代码只分析 `llm_analyzed_at IS NULL` 的新闻。如果需要重新分析，需要先将 `llm_analyzed_at` 设置为 NULL。

### Q4: 如何只分析特定时间范围的新闻？

A: 当前代码不支持时间范围过滤。如果需要此功能，需要修改 `load_news_after_last_processed()` 函数（见上面的示例代码）。

### Q5: 分析结果会覆盖之前的分析吗？

A: 是的，如果重新分析同一条新闻，会覆盖之前的分析结果（更新 `llm_*` 字段和 `llm_analyzed_at` 时间）。

---

## 六、总结

1. **存储位置**：`stock_data.news_articles` 表的 `llm_*` 字段
2. **备份文件**：`news-analysis-system-main/data/backup_results/` 目录
3. **时间范围**：当前不支持按新闻发布时间过滤，只分析未分析的新闻
4. **查询方式**：通过SQL查询 `llm_analyzed_at IS NOT NULL` 的记录

如果需要添加时间范围过滤功能，可以按照上面的示例代码进行修改。
