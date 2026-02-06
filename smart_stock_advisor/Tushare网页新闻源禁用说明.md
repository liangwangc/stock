# Tushare网页新闻源禁用说明

**日期**：2026-01-16  
**问题**：TushareWebNewsSource 无法获取新闻数据

---

## 一、测试结果

### 1.1 测试所有网页链接

测试了以下7个Tushare新闻聚合页面：

1. ✅ **第一财经** - https://tushare.pro/news/yicai
2. ✅ **凤凰财经** - https://tushare.pro/news/fenghuang
3. ✅ **同花顺** - https://tushare.pro/news/10jqka
4. ✅ **金融界** - https://tushare.pro/news/jinrongjie
5. ✅ **新浪财经** - https://tushare.pro/news/sina
6. ✅ **云财经** - https://tushare.pro/news/yuncaijing
7. ✅ **东方财富** - https://tushare.pro/news/eastmoney

### 1.2 测试结果

**所有7个链接都无法获取新闻数据**

- ❌ **状态码**：200（HTTP请求成功）
- ❌ **页面内容**：登录页面（需要登录才能访问）
- ❌ **新闻数据**：0条

**结论**：这些网页链接都需要登录才能访问，无法通过网页爬虫方式获取数据。

---

## 二、解决方案

### 2.1 已禁用 TushareWebNewsSource

由于所有网页链接都无法获取数据，已在 `UnifiedNewsSource` 中禁用 `TushareWebNewsSource`。

**修改位置**：`quant_trading_platform/news/unified_news_source.py`

**修改内容**：
- 注释掉 `TushareWebNewsSource` 的初始化代码
- 添加说明注释，解释禁用原因

### 2.2 使用 API 方式

**推荐使用**：`TuShareNewsSource`（API方式）

**优势**：
- ✅ 已修复并正常工作
- ✅ 支持多个新闻源（通过API）
- ✅ 第一财经（yicai）测试成功，获取到415条新闻
- ✅ 数据格式正确（datetime, title, content）

**使用方式**：
- 代码已自动集成
- 您的 `TUSHARE_TOKEN` 已配置
- 系统会自动使用 `TuShareNewsSource`（API方式）

---

## 三、当前状态

### 3.1 可用的新闻源

**Tushare API方式**（`TuShareNewsSource`）：
- ✅ 已启用
- ✅ 支持多个新闻源（yicai、fenghuang、10jqka等）
- ✅ 第一财经测试成功

**Tushare网页方式**（`TushareWebNewsSource`）：
- ❌ 已禁用
- ❌ 所有网页链接都需要登录
- ❌ 无法获取数据

### 3.2 其他新闻源

系统还包含以下新闻源（不受影响）：
- 金十数据
- 财新
- 证券公司
- 同花顺
- 东方财富
- 新浪财经
- 腾讯财经
- 网易财经
- 上交所
- 深交所
- 巨潮资讯
- 证券时报
- 中国证券报
- 财联社

---

## 四、建议

### 4.1 日常使用

**推荐**：使用 `TuShareNewsSource`（API方式）
- 数据量大且稳定
- 支持多个新闻源
- 已修复并测试成功

### 4.2 如果需要更多新闻源

如果Tushare API的 `news` 接口支持更多新闻源，可以：

1. **查看Tushare文档**：确认支持的新闻源列表
2. **更新配置**：在 `TuShareNewsSource.NEWS_SOURCES` 中添加新的新闻源
3. **测试验证**：使用测试脚本验证新新闻源是否可用

### 4.3 网页方式

**不建议使用**：
- 所有网页链接都需要登录
- 无法通过网页爬虫获取数据
- 即使使用Selenium等方式，也需要处理登录和动态加载

---

## 五、代码修改

### 5.1 已修改的文件

1. **`quant_trading_platform/news/unified_news_source.py`**
   - 禁用 `TushareWebNewsSource` 的初始化
   - 添加说明注释

### 5.2 保留的文件

以下文件保留但不使用：
- `quant_trading_platform/news/tushare_web_news_source.py` - 代码保留，但已禁用
- `smart_stock_advisor/scripts/test_tushare_web_news.py` - 测试脚本保留
- `smart_stock_advisor/scripts/test_tushare_web_links.py` - 测试脚本保留

如果将来Tushare开放公开访问，可以重新启用。

---

## 六、总结

### 6.1 测试结论

- ✅ **确认**：所有7个Tushare网页链接都无法获取新闻数据（需要登录）
- ✅ **已禁用**：`TushareWebNewsSource` 已从统一新闻源中移除
- ✅ **推荐**：使用 `TuShareNewsSource`（API方式），已修复并可用

### 6.2 当前状态

- ✅ Tushare API方式正常工作
- ✅ 第一财经新闻源测试成功（415条新闻）
- ✅ 其他新闻源受API频率限制，但代码已处理
- ❌ Tushare网页方式已禁用（无法获取数据）

---

**最后更新**：2026-01-16
