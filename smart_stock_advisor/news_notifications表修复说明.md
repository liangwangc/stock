# news_notifications 表修复说明

## 问题描述

在访问 `/api/news/notifications` API 时，出现以下错误：
```
(1146, "Table 'stock_data.news_notifications' doesn't exist")
```

## 原因分析

`news_notifications` 表在数据库中不存在，但代码中使用了这个表来存储和查询新闻推送通知。

## 解决方案

### 1. 创建表

已创建执行脚本 `database/create_news_notifications_table.py`，用于执行 `database/news_notification_table.sql` 创建表。

### 2. 表结构

`news_notifications` 表包含以下字段：
- `id` - 主键
- `news_id` - 新闻ID（外键，关联 `news_articles` 表）
- `notification_type` - 通知类型（important/positive/negative/policy）
- `title` - 新闻标题
- `symbol` - 关联股票代码
- `sentiment` - 情感倾向
- `is_sent` - 是否已发送（1=已发送，0=未发送）
- `sent_at` - 发送时间
- `is_read` - 是否已读（1=已读，0=未读）
- `read_at` - 阅读时间
- `created_at` - 创建时间
- `updated_at` - 更新时间

### 3. 索引

表包含以下索引：
- `idx_news_id` - 新闻ID索引
- `idx_symbol` - 股票代码索引
- `idx_is_sent` - 是否已发送索引
- `idx_is_read` - 是否已读索引
- `idx_notification_type` - 通知类型索引
- `idx_created_at` - 创建时间索引

### 4. 外键约束

- `news_id` 外键关联 `news_articles` 表的 `id` 字段
- 使用 `ON DELETE CASCADE`，删除新闻时自动删除相关通知

## 执行方法

### 方法1：使用Python脚本（推荐）

```bash
cd d:\wjw_work\smart_stock_advisor
py database\create_news_notifications_table.py
```

### 方法2：直接在MySQL中执行

```sql
-- 执行 database/news_notification_table.sql 文件中的SQL语句
```

## 验证

执行脚本后，可以通过以下方式验证表是否创建成功：

```sql
-- 检查表是否存在
SHOW TABLES LIKE 'news_notifications';

-- 查看表结构
DESC news_notifications;

-- 查看索引
SHOW INDEX FROM news_notifications;
```

## 错误处理优化

已优化 `utils/news_notification.py` 中的错误处理：
- 如果表不存在，会记录警告日志并返回空列表，而不是抛出异常
- 提供明确的错误提示，指导用户运行创建表的脚本

## 相关文件

- `database/news_notification_table.sql` - 表结构定义SQL文件
- `database/create_news_notifications_table.py` - 执行脚本
- `utils/news_notification.py` - 新闻通知管理器（已优化错误处理）
- `web_app.py` - API端点（`/api/news/notifications`）

## 功能说明

`news_notifications` 表用于：
1. 存储重要新闻的推送通知记录
2. 跟踪通知的发送状态和阅读状态
3. 支持按股票代码、通知类型等条件查询
4. 提供推送历史记录功能

## 注意事项

1. 表创建后，需要确保 `news_articles` 表已存在（因为有外键约束）
2. 如果 `news_articles` 表不存在，需要先创建该表
3. 外键约束使用 `ON DELETE CASCADE`，删除新闻时会自动删除相关通知
