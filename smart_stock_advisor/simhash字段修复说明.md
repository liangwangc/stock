# SimHash字段修复说明

## 问题描述

在运行新闻抓取任务时，出现以下错误：
```
Unknown column 'simhash' in 'field list'
```

这是因为数据库表 `news_articles` 中缺少 `simhash` 字段。

## 解决方案

### 方案1：添加simhash字段（推荐）

运行以下SQL脚本添加 `simhash` 字段：

```sql
-- 文件位置：database/add_simhash_field.sql
ALTER TABLE `news_articles` 
ADD COLUMN `simhash` BIGINT UNSIGNED DEFAULT NULL COMMENT 'SimHash值（用于相似度检测）' AFTER `duplicate_of`;

ALTER TABLE `news_articles` 
ADD INDEX `idx_simhash` (`simhash`);
```

**执行方法：**
1. 使用MySQL客户端连接到数据库
2. 选择对应的数据库
3. 执行 `database/add_simhash_field.sql` 文件中的SQL语句

或者使用命令行：
```bash
mysql -u用户名 -p数据库名 < database/add_simhash_field.sql
```

### 方案2：代码已自动兼容（临时方案）

代码已经修改为自动兼容缺少 `simhash` 字段的情况：
- 如果 `simhash` 字段不存在，代码会自动使用不包含 `simhash` 的SQL语句
- 新闻仍然可以正常保存，但SimHash相似度检测功能将不可用
- 系统会记录警告日志，提示需要添加字段

**注意：** 虽然代码可以兼容，但建议尽快添加 `simhash` 字段，以启用完整的新闻去重功能。

## 功能说明

`simhash` 字段用于：
- **新闻去重**：基于内容相似度检测重复新闻（不仅限于标题和来源）
- **相似度检测**：使用SimHash算法计算新闻内容的相似度
- **提高准确性**：比仅基于标题和来源的去重更准确

## 验证

添加字段后，可以运行新闻抓取任务验证：
1. 新闻应该可以正常保存
2. 日志中不应该再出现 "Unknown column 'simhash'" 错误
3. SimHash相似度检测功能应该正常工作
