# publish_time 字段修复说明

## 问题描述

`publish_time` 字段没有正确获取到新闻发布时间。

## 问题原因

在 `smart_stock_advisor/utils/news_storage.py` 的 `save_news_article` 方法中，代码只从 `news.get('time')` 获取发布时间：

```python
publish_time = news.get('time')
```

但实际上，不同的新闻源可能使用不同的字段名来存储发布时间：
- `time` - 统一新闻源接口使用的字段名
- `publish_time` - 某些新闻源使用的字段名
- `pub_time` - 某些新闻源使用的字段名

而在 `news_crawler.py` 和 `unified_news_source.py` 中，检查时间时使用的是：
```python
news_time = news.get('time') or news.get('publish_time') or news.get('pub_time')
```

这导致保存时可能无法正确获取到发布时间。

## 修复方案

修改 `smart_stock_advisor/utils/news_storage.py` 中的 `save_news_article` 方法：

### 1. 尝试多个时间字段

```python
# 优化：尝试多个时间字段，与news_crawler.py中的逻辑保持一致
publish_time = news.get('time') or news.get('publish_time') or news.get('pub_time')
```

### 2. 改进时间解析逻辑

```python
# 转换发布时间
if publish_time:
    if isinstance(publish_time, str):
        try:
            # 尝试多种日期格式
            publish_time = datetime.strptime(publish_time, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                publish_time = datetime.strptime(publish_time, '%Y-%m-%d')
            except:
                # 如果所有解析都失败，使用当前时间
                self.logger.debug(f"无法解析发布时间: {publish_time}，使用当前时间")
                publish_time = datetime.now()
    elif isinstance(publish_time, datetime):
        # 已经是datetime对象，直接使用
        pass
    else:
        # 其他类型，使用当前时间
        self.logger.debug(f"发布时间类型不支持: {type(publish_time)}，使用当前时间")
        publish_time = datetime.now()
else:
    # 没有时间信息，使用当前时间
    self.logger.debug(f"新闻没有时间信息，使用当前时间: {title[:50]}...")
    publish_time = datetime.now()
```

## 修复效果

1. **正确获取发布时间**：现在会尝试从 `time`、`publish_time`、`pub_time` 三个字段中获取发布时间
2. **与检查逻辑一致**：与 `news_crawler.py` 和 `unified_news_source.py` 中的时间检查逻辑保持一致
3. **更好的错误处理**：如果无法解析时间，会记录日志并使用当前时间作为默认值
4. **支持多种时间格式**：支持 `'%Y-%m-%d %H:%M:%S'` 和 `'%Y-%m-%d'` 两种格式

## 相关文件

1. `smart_stock_advisor/utils/news_storage.py`
   - `save_news_article` 方法

2. `smart_stock_advisor/utils/news_crawler.py`
   - `crawl_all_news` 方法中的时间检查逻辑

3. `quant_trading_platform/news/unified_news_source.py`
   - `get_stock_news` 和 `get_market_news` 方法中的时间检查逻辑

## 测试建议

1. **测试不同新闻源**：
   - 检查各个新闻源返回的时间字段名
   - 验证 `publish_time` 字段是否正确保存到数据库

2. **测试时间解析**：
   - 测试不同格式的时间字符串
   - 验证时间解析失败时的处理逻辑

3. **检查数据库**：
   - 查询 `news_articles` 表，检查 `publish_time` 字段是否正确填充
   - 对比 `fetch_time` 和 `publish_time`，确保时间合理

---

## 修复日期
2026-01-14
