# 新闻处理迁移到 news-analysis-system-main 方案

**创建日期**：2026-01-23  
**目标**：将所有新闻处理功能统一到 news-analysis-system-main

---

## 一、当前情况分析

### 1.1 news-analysis-system-main 现状

**✅ 已有功能**：
- 财联社新闻获取（`get_cls_news.py`）
- 新闻存储到数据库（`news` 表）
- LLM深度分析（分类、关键词、情感、总结）
- 分析结果存储（`analysis_results` 表）

**❌ 缺失功能**：
- **无股票关联**：`news` 表和 `analysis_results` 表都没有股票代码字段
- **单一新闻源**：只支持财联社
- **无股票匹配逻辑**：无法自动识别新闻关联的股票

**数据库表结构**：
```sql
-- news 表（当前）
CREATE TABLE `news` (
   `id` int unsigned NOT NULL AUTO_INCREMENT,
   `title` text NOT NULL,
   `content` text NOT NULL,
   `publish_date` date DEFAULT NULL,
   `publish_time` time DEFAULT NULL,
   `content_hash` varchar(64) DEFAULT NULL,
   `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
   PRIMARY KEY (`id`),
   UNIQUE KEY `hash` (`content_hash`)
)

-- analysis_results 表（当前）
CREATE TABLE `analysis_results` (
   `id` int NOT NULL AUTO_INCREMENT,
   `news_index` int DEFAULT NULL,
   `date` date DEFAULT NULL,
   `category` text,
   `subcategory` text,
   `is_market_relevant` int DEFAULT NULL,
   `keywords` text,
   `sentiment` float DEFAULT NULL,
   `impact_markets` text,  -- 可能受影响的市场/品种，但不是股票代码
   `summary` text,
   PRIMARY KEY (`id`)
)
```

---

### 1.2 smart_stock_advisor 新闻系统现状

**✅ 已有功能**：
- 多源新闻获取（13个新闻源）
- 股票关联（symbol, sector, industry）
- 关键词情感分析
- 新闻去重（SimHash）
- 股票匹配逻辑（`NewsStockMapper`）

**数据库表结构**：
```sql
-- news_articles 表
CREATE TABLE `news_articles` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(500) NOT NULL,
    `content` TEXT,
    `symbol` VARCHAR(10) DEFAULT NULL,  -- 关联股票代码
    `sector` VARCHAR(100) DEFAULT NULL,  -- 关联板块
    `industry` VARCHAR(100) DEFAULT NULL,  -- 关联行业
    `sentiment` VARCHAR(20) DEFAULT NULL,
    `sentiment_score` DECIMAL(8, 4) DEFAULT NULL,
    -- ... 其他字段
)
```

---

## 二、迁移方案设计

### 2.1 数据库表扩展

#### 方案A：扩展 news 表（推荐）

**优点**：
- 保持数据一致性
- 查询方便
- 与 smart_stock_advisor 的 `news_articles` 表结构对齐

**实施步骤**：
1. 为 `news` 表添加股票关联字段
2. 为 `analysis_results` 表添加股票关联字段（可选）
3. 创建股票关联表（多对多关系）

**SQL脚本**：
```sql
-- 1. 扩展 news 表
ALTER TABLE `news` 
ADD COLUMN `symbol` VARCHAR(10) DEFAULT NULL COMMENT '关联股票代码',
ADD COLUMN `sector` VARCHAR(100) DEFAULT NULL COMMENT '关联板块',
ADD COLUMN `industry` VARCHAR(100) DEFAULT NULL COMMENT '关联行业',
ADD COLUMN `concept` VARCHAR(200) DEFAULT NULL COMMENT '关联概念',
ADD COLUMN `source` VARCHAR(50) DEFAULT '财联社' COMMENT '新闻来源',
ADD COLUMN `source_url` VARCHAR(1000) DEFAULT NULL COMMENT '新闻URL',
ADD INDEX `idx_symbol` (`symbol`),
ADD INDEX `idx_sector` (`sector`),
ADD INDEX `idx_industry` (`industry`);

-- 2. 创建新闻股票关联表（支持一条新闻关联多个股票）
CREATE TABLE `news_stock_relation` (
   `id` int unsigned NOT NULL AUTO_INCREMENT,
   `news_id` int unsigned NOT NULL COMMENT '新闻ID',
   `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
   `relevance_score` DECIMAL(5,4) DEFAULT 1.0 COMMENT '相关性得分（0-1）',
   `relation_type` VARCHAR(20) DEFAULT 'direct' COMMENT '关联类型（direct/industry/market）',
   `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
   PRIMARY KEY (`id`),
   UNIQUE KEY `uk_news_symbol` (`news_id`, `symbol`),
   INDEX `idx_symbol` (`symbol`),
   INDEX `idx_news_id` (`news_id`),
   FOREIGN KEY (`news_id`) REFERENCES `news`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻股票关联表';
```

---

### 2.2 股票关联功能实现

#### 2.2.1 创建股票匹配模块

**文件**：`src/data_processing/stock_mapper.py`

**功能**：
- 从新闻标题和内容中提取股票代码
- 匹配股票名称
- 识别板块和行业
- 计算相关性得分

**实现思路**：
1. **股票代码提取**：正则表达式匹配（如：000001、600519）
2. **股票名称匹配**：从股票名称库中匹配
3. **板块识别**：基于关键词匹配板块
4. **行业识别**：基于关键词匹配行业

---

### 2.3 集成到新闻处理流程

#### 2.3.1 修改新闻获取流程

**文件**：`src/data_processing/get_cls_news.py`

**修改点**：
```python
def fetch_and_store_news():
    # ... 现有代码 ...
    
    # 添加股票关联
    from ..data_processing.stock_mapper import StockMapper
    stock_mapper = StockMapper()
    
    # 对每条新闻进行股票匹配
    for idx, row in new_news_df.iterrows():
        stock_info = stock_mapper.map_news_to_stocks(
            title=row['title'],
            content=row['content']
        )
        # 添加股票信息到 DataFrame
        new_news_df.at[idx, 'symbol'] = stock_info.get('primary_symbol')
        new_news_df.at[idx, 'sector'] = stock_info.get('sector')
        new_news_df.at[idx, 'industry'] = stock_info.get('industry')
    
    # 保存到数据库
    new_news_df.to_sql(name='news', con=engine, if_exists='append', index=False)
    
    # 保存股票关联关系
    stock_mapper.save_stock_relations(new_news_df)
```

---

#### 2.3.2 修改LLM分析流程

**文件**：`src/analysis/main.py`

**修改点**：
- LLM分析时，可以基于已关联的股票信息增强分析
- 分析结果中可以包含股票相关性的评估

---

### 2.4 同步到 smart_stock_advisor

#### 2.4.1 增强同步功能

**文件**：`smart_stock_advisor/utils/news_sync_from_cls.py`

**修改点**：
- 同步新闻时，同时同步股票关联信息
- 更新 `news_articles` 表的 symbol, sector, industry 字段
- 同步 `news_stock_relation` 表的数据（如果存在）

---

## 三、实施步骤

### 步骤1：扩展数据库表结构

**文件**：`news-analysis-system-main/src/config/add_stock_fields.sql`

```sql
-- 扩展 news 表
ALTER TABLE `news` 
ADD COLUMN `symbol` VARCHAR(10) DEFAULT NULL COMMENT '关联股票代码',
ADD COLUMN `sector` VARCHAR(100) DEFAULT NULL COMMENT '关联板块',
ADD COLUMN `industry` VARCHAR(100) DEFAULT NULL COMMENT '关联行业',
ADD COLUMN `concept` VARCHAR(200) DEFAULT NULL COMMENT '关联概念',
ADD COLUMN `source` VARCHAR(50) DEFAULT '财联社' COMMENT '新闻来源',
ADD COLUMN `source_url` VARCHAR(1000) DEFAULT NULL COMMENT '新闻URL',
ADD INDEX `idx_symbol` (`symbol`),
ADD INDEX `idx_sector` (`sector`),
ADD INDEX `idx_industry` (`industry`);

-- 创建新闻股票关联表
CREATE TABLE IF NOT EXISTS `news_stock_relation` (
   `id` int unsigned NOT NULL AUTO_INCREMENT,
   `news_id` int unsigned NOT NULL COMMENT '新闻ID',
   `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
   `relevance_score` DECIMAL(5,4) DEFAULT 1.0 COMMENT '相关性得分（0-1）',
   `relation_type` VARCHAR(20) DEFAULT 'direct' COMMENT '关联类型（direct/industry/market）',
   `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
   PRIMARY KEY (`id`),
   UNIQUE KEY `uk_news_symbol` (`news_id`, `symbol`),
   INDEX `idx_symbol` (`symbol`),
   INDEX `idx_news_id` (`news_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻股票关联表';
```

---

### 步骤2：创建股票匹配模块

**文件**：`news-analysis-system-main/src/data_processing/stock_mapper.py`

**功能**：
- 股票代码提取
- 股票名称匹配
- 板块/行业识别
- 相关性计算

---

### 步骤3：集成股票匹配到新闻获取

**修改**：`src/data_processing/get_cls_news.py`

---

### 步骤4：更新同步脚本

**修改**：`smart_stock_advisor/utils/news_sync_from_cls.py`

- 同步股票关联信息
- 更新 `news_articles` 表的股票字段

---

### 步骤5：测试验证

1. 测试股票匹配准确性
2. 测试数据同步
3. 验证股票关联正确性

---

## 四、功能对比

### 4.1 迁移前后对比

| 功能 | news-analysis-system-main（迁移前） | news-analysis-system-main（迁移后） | smart_stock_advisor（当前） |
|------|-----------------------------------|-----------------------------------|---------------------------|
| 新闻获取 | ✅ 财联社 | ✅ 财联社 + 其他源（可扩展） | ✅ 13个新闻源 |
| LLM分析 | ✅ 深度分析 | ✅ 深度分析 | ❌ 仅关键词分析 |
| 股票关联 | ❌ 无 | ✅ 自动匹配 | ✅ 支持 |
| 板块识别 | ❌ 无 | ✅ 自动识别 | ✅ 支持 |
| 行业识别 | ❌ 无 | ✅ 自动识别 | ✅ 支持 |
| 数据同步 | ❌ 无 | ✅ 同步到主数据库 | ✅ 统一管理 |

---

## 五、优势分析

### 5.1 统一处理优势

✅ **单一数据源**：
- 所有新闻处理逻辑集中在 news-analysis-system-main
- 避免重复代码和逻辑不一致

✅ **深度分析**：
- LLM提供更准确的分类和情感分析
- 结合股票关联，提供更精准的预测信号

✅ **易于维护**：
- 新闻处理逻辑集中，便于维护和优化
- smart_stock_advisor 专注于股票预测

---

## 六、注意事项

### 6.1 数据一致性

⚠️ **确保同步**：
- 新闻获取后立即同步到主数据库
- 分析完成后同步分析结果

### 6.2 股票匹配准确性

⚠️ **匹配策略**：
- 优先使用股票代码匹配（最准确）
- 股票名称匹配需要处理同义词
- 板块/行业匹配需要维护关键词库

### 6.3 性能考虑

⚠️ **批量处理**：
- 股票匹配可以批量处理
- 使用缓存提高匹配速度

---

**文档完成时间**：2026-01-23  
**状态**：✅ 方案设计完成，待实施
