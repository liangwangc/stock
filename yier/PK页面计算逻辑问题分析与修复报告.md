# PK页面计算逻辑问题分析与修复报告

## 一、问题分析

### 1.1 学习单词数显示不正确

**问题描述**：
- 新用户只学习了几个单词，但PK页面显示"学习单词: 10个"
- 原因：之前的SQL查询使用的是 `words` 表的 `date_added` 字段，统计的是"添加的单词数"，而不是"实际学习过的单词数"
- 当用户点击"开始学习"时，单词库导入的单词会被添加到 `words` 表，`date_added` 就是今天，所以即使还没学习完，也会被统计进去

**修复方案**：
- 改为使用 `word_review_logs` 表统计实际学习过的单词
- SQL查询：`COUNT(DISTINCT rl.word_id)` - 统计周期内实际学习过的不同单词数
- 这样只有真正学习过的单词才会被统计

### 1.2 完成率显示不正确

**问题描述**：
- 新用户今天学习了3个单词，daily_goal=10，但完成率显示100%
- 原因：之前的逻辑是 `total_words / daily_goal`，但 `total_words` 统计的是"添加的单词数"（包括单词库导入但还没学习的）
- 如果今天添加了10个单词（daily_goal=10），即使只学习了3个，完成率也会显示100%

**修复方案**：
- `total_words` 现在统计的是"实际学习过的单词数"（通过 `word_review_logs` 表）
- 完成率计算：`(实际学习的单词数 / daily_goal) * 100`
- 例如：今天学习了3个单词，daily_goal=10，完成率 = (3/10)*100 = 30%

### 1.3 已掌握单词的逻辑

**当前逻辑**：
```sql
SUM(CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN 1 ELSE 0 END) as mastered_words
```

**说明**：
- 统计周期内学习的单词中，`status='mastered'` 或 `repetitions>=5` 的单词数
- 这个逻辑是正确的，表示"已掌握的单词数"
- 修复后，会基于 `word_review_logs` 表统计，只统计实际学习过的单词中已掌握的

### 1.4 排行榜排序逻辑

**当前排序**：
```sql
ORDER BY total_words DESC, mastered_words DESC, study_days DESC
```

**说明**：
- 主要按"学习单词总数"降序排列
- 其次按"已掌握单词数"降序排列
- 最后按"学习天数"降序排列
- 这个逻辑是合理的，鼓励用户多学习、多掌握

## 二、修复内容

### 2.1 SQL查询修改

**修改前**（统计添加的单词）：
```sql
SELECT 
    COUNT(DISTINCT w.id) as total_words,
    SUM(CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN 1 ELSE 0 END) as mastered_words
FROM users u
LEFT JOIN words w ON u.id = w.user_id 
    AND DATE(w.date_added) >= ? 
    AND DATE(w.date_added) <= ?
```

**修改后**（统计实际学习过的单词）：
```sql
SELECT 
    COUNT(DISTINCT rl.word_id) as total_words,
    COUNT(DISTINCT CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN rl.word_id END) as mastered_words
FROM users u
LEFT JOIN word_review_logs rl ON u.id = rl.user_id 
    AND DATE(rl.review_date) >= ? 
    AND DATE(rl.review_date) <= ?
LEFT JOIN words w ON rl.word_id = w.id
```

### 2.2 兼容性处理

- 如果 `word_review_logs` 表不存在，会回退到使用 `words` 表的 `date_added`（兼容旧数据）
- 这样既保证了新逻辑的正确性，又不会影响没有 `word_review_logs` 表的旧系统

### 2.3 完成率计算说明

**计算公式**：
- 如果有多天数据：`完成率 = (总学习单词数 / 学习天数) / daily_goal * 100`
- 如果只有1天数据：`完成率 = (今天学习的单词数 / daily_goal) * 100`

**示例**：
- 今天学习了3个单词，daily_goal=10 → 完成率 = (3/10)*100 = 30%
- 本周学习了20个单词，学习了3天，daily_goal=10 → 平均每日 = 20/3 = 6.67，完成率 = (6.67/10)*100 = 66.7%

## 三、修复后的效果

### 3.1 学习单词数
- ✅ 只统计实际学习过的单词（通过 `word_review_logs` 表）
- ✅ 不会统计单词库导入但还没学习的单词

### 3.2 完成率
- ✅ 基于实际学习的单词数计算
- ✅ 如果今天只学习了3个单词，daily_goal=10，完成率显示30%（而不是100%）

### 3.3 已掌握单词
- ✅ 统计周期内学习的单词中已掌握的
- ✅ 基于 `word_review_logs` 表，只统计实际学习过的单词

### 3.4 排行榜排序
- ✅ 按实际学习单词数排序
- ✅ 鼓励用户多学习、多掌握

## 四、测试建议

1. **新用户测试**：
   - 创建新用户，设置daily_goal=10
   - 点击"开始学习"，导入单词库（假设导入10个）
   - 只学习3个单词
   - 检查PK页面：学习单词数应该显示3（不是10），完成率应该显示30%（不是100%）

2. **已掌握单词测试**：
   - 学习几个单词，标记为"记住"（repetitions会递增）
   - 当某个单词的repetitions>=5时，检查PK页面的"已掌握"数是否正确

3. **多天数据测试**：
   - 连续学习几天，每天学习不同数量的单词
   - 检查"本周"、"本月"排行榜的数据是否正确

## 五、注意事项

1. **数据迁移**：如果系统之前使用的是 `words` 表的 `date_added`，修复后可能会看到数据变化（因为现在统计的是实际学习过的单词）
2. **word_review_logs表**：确保该表已创建，否则会回退到旧逻辑
3. **性能考虑**：`word_review_logs` 表应该有适当的索引（`idx_user_id`, `idx_review_date`）以保证查询性能
