# 项目全面分析与PK功能设计方案

## 一、项目全面梳理与检查

### 1.1 项目架构分析

#### 技术栈
- **前端**：HTML5 + CSS3 + JavaScript (原生)
- **后端**：PHP (原生，无框架)
- **数据库**：MySQL/MariaDB
- **图表库**：Chart.js
- **存储**：localStorage (前端会话管理)

#### 文件结构
```
yier/
├── index.html          # 主页面（用户端）
├── admin.html          # 后台管理页面
├── api.php             # 后端API（所有接口）
├── 数据库相关SQL文件
└── 各种说明文档
```

---

### 1.2 安全性检查

#### ✅ 已实现的安全措施

1. **SQL注入防护**
   - ✅ 大部分查询使用 `prepare()` + `bind_param()` 参数化查询
   - ✅ 有 `prepare_check()` 辅助函数统一处理

2. **错误处理**
   - ✅ 设置了全局错误处理器，返回JSON格式错误
   - ✅ 异常处理机制完善

3. **密码安全**
   - ✅ 使用MD5加密（虽然MD5已不安全，但比明文好）

#### ⚠️ 发现的安全问题

1. **SQL注入风险（中等）**
   ```php
   // api.php 第1313行、1321行
   $today_date = $conn->real_escape_string($raw_date);
   $target_words[] = "'".$conn->real_escape_string($w)."'";
   ```
   **问题**：`batch_pass` API中使用了字符串拼接，虽然用了`real_escape_string`，但不够安全
   **建议**：改为参数化查询

2. **SQL注入风险（低）**
   ```php
   // api.php 第1008行
   $res = $conn->query("SELECT * FROM words WHERE $where");
   ```
   **问题**：`export_json` API中直接拼接WHERE条件
   **建议**：改为参数化查询

3. **CORS配置过于宽松**
   ```php
   header("Access-Control-Allow-Origin: *");
   ```
   **问题**：允许所有来源访问，存在CSRF风险
   **建议**：生产环境限制为特定域名

4. **密码加密方式不安全**
   - 使用MD5加密，容易被破解
   **建议**：升级为 `password_hash()` + `password_verify()`

5. **Session管理缺失**
   - 前端使用localStorage存储用户信息，没有服务端Session验证
   **问题**：用户可以伪造用户ID，访问其他用户数据
   **建议**：实现服务端Session验证

---

### 1.3 代码质量问题

#### ⚠️ 发现的问题

1. **代码重复**
   - `getStreakDates()` 和 `calculateCheckInStreak()` 有重复逻辑
   - 多个API中重复的权限检查代码

2. **硬编码**
   - 数据库配置硬编码在 `api.php` 中
   - 默认值硬编码（如 `daily_goal = 5`）

3. **错误处理不一致**
   - 部分API返回格式不统一
   - 部分错误没有记录日志

4. **性能问题**
   - `get_home_data` API中的智能复习抽取逻辑复杂，可能影响性能
   - 没有缓存机制，每次都要查询数据库

5. **代码可维护性**
   - `api.php` 文件过大（1696行），建议拆分
   - 函数命名不够规范（如 `prepare_check`）

---

### 1.4 功能逻辑检查

#### ✅ 功能完整性

1. **用户管理**：✅ 登录、注册（管理员）、账户管理
2. **单词管理**：✅ 添加、学习、复习、删除
3. **学习系统**：✅ 学习模式、听写模式、智能复习
4. **统计功能**：✅ 学习统计、图表展示、数据导出
5. **单词库**：✅ 年级单词库、自动导入

#### ⚠️ 发现的不合理之处

1. **学习统计逻辑**
   - `today_learned_count` 只统计 `date_added = today`，不包括复习的单词
   - **问题**：用户复习单词不算在学习量中
   - **建议**：应该统计今天所有学习的单词（包括复习）

2. **复习队列逻辑**
   - 智能复习抽取逻辑复杂，可能影响性能
   - **建议**：考虑使用缓存或定时任务预计算

3. **单词状态管理**
   - `status` 字段有 `new`, `learning`, `review`, `mastered` 四种状态
   - **问题**：状态转换逻辑可能不够清晰
   - **建议**：明确状态转换规则

4. **数据一致性**
   - `forgot_count`, `vague_count`, `remembered_count` 和 `word_review_logs` 表的数据可能不一致
   - **建议**：定期同步或只使用一个数据源

---

### 1.5 用户体验检查

#### ✅ 已优化的地方

1. **响应式设计**：✅ 移动端适配良好
2. **交互反馈**：✅ Toast提示、动画效果
3. **数据可视化**：✅ Chart.js图表展示

#### ⚠️ 需要优化的地方

1. **加载性能**
   - 首页加载时可能查询较多数据
   - **建议**：使用懒加载、分页加载

2. **错误提示**
   - 部分错误提示不够友好
   - **建议**：统一错误提示格式

3. **操作反馈**
   - 部分操作没有加载状态提示
   - **建议**：添加loading动画

---

## 二、学习PK功能设计方案

### 2.1 功能需求分析

#### 核心需求
1. **排名显示**：按天、周、月、年显示用户学习排名
2. **前三名突出**：用图标和特殊样式突出前三名
3. **排名变化**：显示每个用户相比前一天的排名变化（上升/下降）
4. **新建页面**：独立的PK页面

#### 排名指标
- **主要指标**：学习单词数（包括新学和复习）
- **辅助指标**：连续打卡天数、掌握单词数、学习完成率

---

### 2.2 数据库设计

#### 2.2.1 创建排名快照表

```sql
CREATE TABLE IF NOT EXISTS user_rankings (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    ranking_date DATE NOT NULL COMMENT '排名日期',
    period_type ENUM('daily', 'weekly', 'monthly', 'yearly') NOT NULL COMMENT '排名周期类型',
    period_start DATE NOT NULL COMMENT '周期开始日期',
    period_end DATE NOT NULL COMMENT '周期结束日期',
    rank_position INT NOT NULL COMMENT '排名位置',
    total_words INT DEFAULT 0 COMMENT '学习单词总数',
    new_words INT DEFAULT 0 COMMENT '新学单词数',
    review_words INT DEFAULT 0 COMMENT '复习单词数',
    study_days INT DEFAULT 0 COMMENT '学习天数',
    streak_days INT DEFAULT 0 COMMENT '连续打卡天数',
    mastered_words INT DEFAULT 0 COMMENT '掌握单词数',
    completion_rate DECIMAL(5,2) DEFAULT 0 COMMENT '学习完成率',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_period (user_id, ranking_date, period_type, period_start),
    KEY idx_ranking_date (ranking_date),
    KEY idx_period_type (period_type),
    KEY idx_rank_position (rank_position),
    CONSTRAINT fk_ranking_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户排名快照表';
```

#### 2.2.2 创建排名历史表（用于计算排名变化）

```sql
CREATE TABLE IF NOT EXISTS user_ranking_history (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    ranking_date DATE NOT NULL COMMENT '排名日期',
    period_type ENUM('daily', 'weekly', 'monthly', 'yearly') NOT NULL COMMENT '排名周期类型',
    rank_position INT NOT NULL COMMENT '排名位置',
    total_words INT DEFAULT 0 COMMENT '学习单词总数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_user_date_type (user_id, ranking_date, period_type),
    KEY idx_ranking_date (ranking_date),
    CONSTRAINT fk_history_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户排名历史表';
```

---

### 2.3 API设计

#### 2.3.1 获取排名数据 API

**接口**：`api.php?action=get_rankings`

**参数**：
- `uid`：当前用户ID（可选，用于高亮显示）
- `period`：排名周期（`daily`, `weekly`, `monthly`, `yearly`）
- `date`：排名日期（可选，默认今天）

**返回格式**：
```json
{
    "period": "daily",
    "date": "2026-01-29",
    "rankings": [
        {
            "user_id": 1,
            "username": "用户1",
            "rank": 1,
            "rank_change": 0,  // 排名变化：正数上升，负数下降，0不变
            "total_words": 50,
            "new_words": 30,
            "review_words": 20,
            "study_days": 7,
            "streak_days": 5,
            "mastered_words": 100,
            "completion_rate": 85.5,
            "is_current_user": false
        },
        ...
    ],
    "current_user_rank": 3,  // 当前用户排名
    "total_users": 10
}
```

#### 2.3.2 计算排名变化逻辑

```php
function calculateRankChange($conn, $user_id, $period_type, $current_date) {
    // 获取当前排名
    $current_rank = getCurrentRank($conn, $user_id, $period_type, $current_date);
    
    // 获取前一天排名
    $previous_date = date('Y-m-d', strtotime("$current_date -1 day"));
    $previous_rank = getPreviousRank($conn, $user_id, $period_type, $previous_date);
    
    if ($previous_rank === null) {
        return null; // 没有历史排名
    }
    
    return $previous_rank - $current_rank; // 正数上升，负数下降
}
```

---

### 2.4 前端页面设计

#### 2.4.1 PK页面结构

```html
<div id="tab-pk" class="hidden">
    <!-- 排名周期选择 -->
    <div class="card">
        <div style="display:flex; gap:10px;">
            <button onclick="app.loadRankings('daily')" class="period-btn active">今日</button>
            <button onclick="app.loadRankings('weekly')" class="period-btn">本周</button>
            <button onclick="app.loadRankings('monthly')" class="period-btn">本月</button>
            <button onclick="app.loadRankings('yearly')" class="period-btn">本年</button>
        </div>
    </div>
    
    <!-- 排名列表 -->
    <div class="card">
        <h3>🏆 学习排行榜</h3>
        <div id="rankings-list">
            <!-- 动态生成排名列表 -->
        </div>
    </div>
</div>
```

#### 2.4.2 排名列表项样式

**前三名样式**：
- 🥇 第一名：金色背景、大图标
- 🥈 第二名：银色背景、大图标
- 🥉 第三名：铜色背景、大图标

**排名变化图标**：
- ⬆️ 上升：绿色箭头
- ⬇️ 下降：红色箭头
- ➡️ 不变：灰色箭头
- 🆕 新上榜：蓝色图标

---

### 2.5 排名计算逻辑

#### 2.5.1 每日排名

**计算时间**：每天凌晨0点（或用户首次访问时）

**排名指标**：
1. 主要：当天学习的单词总数（包括新学和复习）
2. 次要：连续打卡天数、学习完成率

**SQL查询**：
```sql
SELECT 
    u.id,
    u.username,
    COUNT(DISTINCT w.id) as total_words,
    COUNT(DISTINCT CASE WHEN w.status = 'new' THEN w.id END) as new_words,
    COUNT(DISTINCT CASE WHEN w.status != 'new' THEN w.id END) as review_words,
    COUNT(DISTINCT DATE(w.date_added)) as study_days,
    -- 计算连续打卡天数
    -- 计算掌握单词数
    -- 计算学习完成率
FROM users u
LEFT JOIN words w ON u.id = w.user_id AND w.date_added = ?
WHERE u.is_active = 1
GROUP BY u.id
ORDER BY total_words DESC, streak_days DESC, completion_rate DESC
```

#### 2.5.2 每周排名

**计算时间**：每周一凌晨（或用户首次访问时）

**排名指标**：本周（周一到今天）学习的单词总数

#### 2.5.3 每月排名

**计算时间**：每月1号凌晨（或用户首次访问时）

**排名指标**：本月（1号到今天）学习的单词总数

#### 2.5.4 每年排名

**计算时间**：每年1月1号凌晨（或用户首次访问时）

**排名指标**：本年（1月1号到今天）学习的单词总数

---

### 2.6 排名更新策略

#### 方案A：实时计算（推荐用于小规模用户）

**优点**：
- 数据实时准确
- 不需要定时任务

**缺点**：
- 用户量大时性能问题
- 每次访问都要计算

**实现**：
- 用户访问PK页面时实时计算排名
- 使用缓存（Redis或内存缓存）减少计算次数

#### 方案B：定时任务预计算（推荐用于大规模用户）

**优点**：
- 性能好，响应快
- 可以批量计算

**缺点**：
- 需要定时任务
- 数据可能有延迟

**实现**：
- 每天凌晨计算前一天的排名
- 存储到 `user_rankings` 表
- 用户访问时直接查询

---

### 2.7 排名变化计算

#### 逻辑设计

1. **获取当前排名**：从 `user_rankings` 表查询
2. **获取前一天排名**：从 `user_ranking_history` 表查询
3. **计算变化**：`rank_change = previous_rank - current_rank`
   - 正数：排名上升
   - 负数：排名下降
   - 0：排名不变
   - null：新上榜

#### 特殊情况处理

1. **新用户**：没有历史排名，显示"新上榜"
2. **并列排名**：相同单词数时，按连续打卡天数、完成率排序
3. **数据缺失**：如果前一天没有排名数据，显示"-"

---

### 2.8 前端实现细节

#### 2.8.1 排名列表渲染

```javascript
function renderRankings(data) {
    const list = document.getElementById('rankings-list');
    list.innerHTML = '';
    
    data.rankings.forEach((user, index) => {
        const rank = index + 1;
        const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
        const rankClass = rank <= 3 ? 'top-three' : '';
        const changeIcon = getRankChangeIcon(user.rank_change);
        
        const item = `
            <div class="ranking-item ${rankClass}" data-user-id="${user.user_id}">
                <div class="rank-number">${medal || rank}</div>
                <div class="user-info">
                    <div class="username">${user.username}</div>
                    <div class="user-stats">
                        <span>学习 ${user.total_words} 个单词</span>
                        <span>连续打卡 ${user.streak_days} 天</span>
                    </div>
                </div>
                <div class="rank-change">${changeIcon}</div>
            </div>
        `;
        list.innerHTML += item;
    });
}
```

#### 2.8.2 排名变化图标

```javascript
function getRankChangeIcon(change) {
    if (change === null) return '🆕';
    if (change > 0) return `⬆️ ${change}`;
    if (change < 0) return `⬇️ ${Math.abs(change)}`;
    return '➡️';
}
```

---

### 2.9 性能优化建议

1. **缓存机制**
   - 使用Redis缓存排名数据
   - 缓存时间：每日排名1小时，每周排名6小时，每月排名12小时

2. **数据库优化**
   - 为 `user_rankings` 表添加合适的索引
   - 定期归档历史排名数据（保留最近1年）

3. **查询优化**
   - 使用视图（VIEW）简化复杂查询
   - 使用存储过程（Stored Procedure）提高性能

4. **前端优化**
   - 使用虚拟滚动（Virtual Scrolling）处理大量用户
   - 懒加载排名数据

---

### 2.10 用户体验优化

1. **动画效果**
   - 排名变化时添加动画效果
   - 前三名进入时添加特效

2. **交互功能**
   - 点击用户可查看详细信息
   - 支持搜索用户
   - 支持筛选（只看好友、只看同年级等）

3. **激励功能**
   - 显示"距离上一名还差X个单词"
   - 显示"再学习X个单词就能超过下一名"
   - 显示成就徽章（如"连续7天第一"）

---

## 三、优化建议总结

### 3.1 安全性优化（高优先级）

1. **修复SQL注入风险**
   - `batch_pass` API改为参数化查询
   - `export_json` API改为参数化查询

2. **升级密码加密**
   - 使用 `password_hash()` + `password_verify()`
   - 迁移现有MD5密码

3. **实现Session验证**
   - 服务端Session管理
   - 前端每次请求验证Session

4. **限制CORS**
   - 生产环境限制为特定域名

### 3.2 代码质量优化（中优先级）

1. **代码重构**
   - 拆分 `api.php` 为多个文件
   - 提取公共函数到独立文件

2. **统一错误处理**
   - 统一错误返回格式
   - 添加错误日志记录

3. **性能优化**
   - 添加缓存机制
   - 优化数据库查询

### 3.3 功能优化（中优先级）

1. **学习统计优化**
   - 修复 `today_learned_count` 统计逻辑
   - 包括复习单词的学习量

2. **数据一致性**
   - 统一使用 `word_review_logs` 表
   - 定期同步统计数据

### 3.4 用户体验优化（低优先级）

1. **加载性能**
   - 添加loading动画
   - 使用懒加载

2. **错误提示**
   - 统一错误提示格式
   - 添加友好的错误信息

---

## 四、PK功能实施计划

### 阶段1：数据库准备（1天）
1. 创建 `user_rankings` 表
2. 创建 `user_ranking_history` 表
3. 添加必要的索引

### 阶段2：后端API开发（2-3天）
1. 实现 `get_rankings` API
2. 实现排名计算逻辑
3. 实现排名变化计算

### 阶段3：前端页面开发（2天）
1. 创建PK页面
2. 实现排名列表渲染
3. 实现排名变化显示

### 阶段4：定时任务（1天）
1. 实现排名预计算任务
2. 实现排名历史记录

### 阶段5：测试和优化（2天）
1. 功能测试
2. 性能优化
3. 用户体验优化

---

## 五、潜在问题和解决方案

### 问题1：排名计算性能

**问题**：用户量大时，实时计算排名可能很慢

**解决方案**：
- 使用定时任务预计算
- 使用缓存减少计算次数
- 优化SQL查询，添加索引

### 问题2：排名并列

**问题**：多个用户学习单词数相同，如何排序？

**解决方案**：
- 主要指标：学习单词数
- 次要指标：连续打卡天数
- 第三指标：学习完成率
- 第四指标：掌握单词数

### 问题3：数据一致性

**问题**：排名数据和实际学习数据可能不一致

**解决方案**：
- 定期校验排名数据
- 使用事务保证数据一致性
- 添加数据校验机制

### 问题4：隐私保护

**问题**：是否显示所有用户的排名？

**解决方案**：
- 提供隐私设置选项
- 支持隐藏排名
- 支持只看好友排名

---

## 六、总结

### 6.1 项目现状

**优点**：
- ✅ 功能完整，覆盖学习、复习、统计等核心功能
- ✅ 代码结构清晰，易于理解
- ✅ 用户体验良好，界面美观

**需要改进**：
- ⚠️ 安全性需要加强（SQL注入、Session管理）
- ⚠️ 代码质量需要提升（代码重复、硬编码）
- ⚠️ 性能需要优化（缓存、查询优化）

### 6.2 PK功能价值

1. **激励学习**：排名机制可以激励用户学习
2. **社交功能**：增加用户之间的互动
3. **数据分析**：可以分析用户学习行为

### 6.3 实施建议

1. **优先修复安全问题**：SQL注入、Session管理
2. **然后实施PK功能**：排名、前三突出、排名变化
3. **最后优化性能**：缓存、查询优化

---

## 七、详细技术方案

### 7.1 排名计算SQL（每日排名示例）

```sql
-- 计算每日排名
SELECT 
    u.id as user_id,
    u.username,
    COUNT(DISTINCT w.id) as total_words,
    COUNT(DISTINCT CASE WHEN w.status = 'new' THEN w.id END) as new_words,
    COUNT(DISTINCT CASE WHEN w.status != 'new' THEN w.id END) as review_words,
    COUNT(DISTINCT DATE(w.date_added)) as study_days,
    -- 计算连续打卡天数（需要单独查询）
    -- 计算掌握单词数
    COUNT(DISTINCT CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN w.id END) as mastered_words,
    -- 计算学习完成率
    CASE 
        WHEN u.daily_goal > 0 THEN 
            ROUND((COUNT(DISTINCT w.id) / u.daily_goal) * 100, 2)
        ELSE 0
    END as completion_rate
FROM users u
LEFT JOIN words w ON u.id = w.user_id AND w.date_added = ?
WHERE u.is_active = 1
GROUP BY u.id, u.username, u.daily_goal
ORDER BY total_words DESC, mastered_words DESC, completion_rate DESC
```

### 7.2 排名变化计算SQL

```sql
-- 获取当前排名
SELECT rank_position 
FROM user_rankings 
WHERE user_id = ? AND ranking_date = ? AND period_type = ?

-- 获取前一天排名
SELECT rank_position 
FROM user_ranking_history 
WHERE user_id = ? AND ranking_date = ? AND period_type = ?
```

### 7.3 前端排名列表项HTML结构

```html
<div class="ranking-item top-three" data-user-id="1">
    <div class="rank-number">🥇</div>
    <div class="user-info">
        <div class="username">用户1</div>
        <div class="user-stats">
            <span class="stat-item">📚 学习 50 个单词</span>
            <span class="stat-item">🔥 连续打卡 5 天</span>
            <span class="stat-item">⭐ 掌握 100 个</span>
        </div>
    </div>
    <div class="rank-change up">⬆️ 2</div>
</div>
```

---

## 八、后续扩展建议

1. **好友系统**：支持添加好友，只看好友排名
2. **成就系统**：根据排名发放成就徽章
3. **挑战功能**：用户可以发起学习挑战
4. **排行榜分类**：按年级、按班级分类排名
5. **历史排名**：查看历史排名趋势图

---

## 九、详细问题清单

### 9.1 安全性问题（必须修复）

#### 问题1：SQL注入风险 - batch_pass API
**位置**：`api.php` 第1313-1330行
**问题**：使用字符串拼接SQL
```php
$sql = "SELECT * FROM words WHERE user_id=$uid AND $sql_where";
$res = $conn->query($sql);
```
**风险等级**：中等
**修复建议**：改为参数化查询

#### 问题2：SQL注入风险 - export_json API
**位置**：`api.php` 第1008行
**问题**：直接拼接WHERE条件
```php
$res = $conn->query("SELECT * FROM words WHERE $where");
```
**风险等级**：低（WHERE条件来自固定值，但仍不安全）
**修复建议**：改为参数化查询

#### 问题3：Session管理缺失
**位置**：整个项目
**问题**：前端使用localStorage存储用户信息，没有服务端验证
**风险等级**：高
**修复建议**：实现服务端Session验证

#### 问题4：密码加密不安全
**位置**：`api.php` 登录相关代码
**问题**：使用MD5加密
**风险等级**：中等
**修复建议**：升级为 `password_hash()` + `password_verify()`

#### 问题5：CORS配置过于宽松
**位置**：`api.php` 第6行
**问题**：`Access-Control-Allow-Origin: *`
**风险等级**：低（CSRF风险）
**修复建议**：生产环境限制为特定域名

### 9.2 代码质量问题

#### 问题1：代码重复
- `getStreakDates()` 和 `calculateCheckInStreak()` 有重复逻辑
- 多个API中重复的权限检查代码

#### 问题2：硬编码
- 数据库配置硬编码在 `api.php` 中
- 默认值硬编码（如 `daily_goal = 5`）

#### 问题3：文件过大
- `api.php` 文件1696行，建议拆分为多个文件

#### 问题4：错误处理不一致
- 部分API返回格式不统一
- 部分错误没有记录日志

### 9.3 功能逻辑问题

#### 问题1：学习统计逻辑
- `today_learned_count` 只统计 `date_added = today`，不包括复习的单词
- **建议**：应该统计今天所有学习的单词（包括复习）

#### 问题2：数据一致性
- `forgot_count`, `vague_count`, `remembered_count` 和 `word_review_logs` 表的数据可能不一致
- **建议**：统一使用 `word_review_logs` 表，或定期同步

### 9.4 性能问题

#### 问题1：查询性能
- `get_home_data` API中的智能复习抽取逻辑复杂，可能影响性能
- **建议**：使用缓存或定时任务预计算

#### 问题2：没有缓存机制
- 每次都要查询数据库
- **建议**：添加Redis缓存

---

## 十、PK功能详细设计

### 10.1 排名计算详细逻辑

#### 每日排名计算

**时间范围**：当天（00:00:00 - 23:59:59）

**排名指标（优先级顺序）**：
1. **主要指标**：学习单词总数（包括新学和复习）
2. **次要指标**：连续打卡天数
3. **第三指标**：学习完成率（实际学习数/每日目标）
4. **第四指标**：掌握单词数

**SQL实现**：
```sql
SELECT 
    u.id,
    u.username,
    u.daily_goal,
    COUNT(DISTINCT w.id) as total_words,
    COUNT(DISTINCT CASE WHEN w.status = 'new' THEN w.id END) as new_words,
    COUNT(DISTINCT CASE WHEN w.status != 'new' THEN w.id END) as review_words,
    COUNT(DISTINCT CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN w.id END) as mastered_words,
    CASE 
        WHEN u.daily_goal > 0 THEN 
            ROUND((COUNT(DISTINCT w.id) / u.daily_goal) * 100, 2)
        ELSE 0
    END as completion_rate
FROM users u
LEFT JOIN words w ON u.id = w.user_id AND DATE(w.date_added) = ?
LEFT JOIN (
    -- 计算连续打卡天数（子查询）
    SELECT user_id, COUNT(*) as streak_days
    FROM (
        SELECT user_id, date_added,
               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY date_added DESC) as rn
        FROM words
        WHERE date_added <= ?
        GROUP BY user_id, date_added
    ) t
    WHERE rn <= 30
    GROUP BY user_id
) streak ON u.id = streak.user_id
WHERE u.is_active = 1
GROUP BY u.id, u.username, u.daily_goal
ORDER BY total_words DESC, streak_days DESC, completion_rate DESC, mastered_words DESC
```

#### 每周排名计算

**时间范围**：本周一00:00:00 - 今天23:59:59

**排名指标**：同每日排名

#### 每月排名计算

**时间范围**：本月1号00:00:00 - 今天23:59:59

**排名指标**：同每日排名

#### 每年排名计算

**时间范围**：本年1月1号00:00:00 - 今天23:59:59

**排名指标**：同每日排名

### 10.2 排名变化计算

#### 逻辑设计

```php
function calculateRankChange($conn, $user_id, $period_type, $current_date) {
    // 1. 获取当前排名
    $current_rank = getCurrentRank($conn, $user_id, $period_type, $current_date);
    
    // 2. 根据周期类型计算前一天/前一周/前一月/前一年的日期
    $previous_date = getPreviousPeriodDate($current_date, $period_type);
    
    // 3. 获取历史排名
    $previous_rank = getPreviousRank($conn, $user_id, $period_type, $previous_date);
    
    // 4. 计算变化
    if ($previous_rank === null) {
        return null; // 新上榜
    }
    
    $change = $previous_rank - $current_rank;
    
    return [
        'change' => $change,  // 正数上升，负数下降，0不变
        'previous_rank' => $previous_rank,
        'current_rank' => $current_rank
    ];
}

function getPreviousPeriodDate($current_date, $period_type) {
    switch ($period_type) {
        case 'daily':
            return date('Y-m-d', strtotime("$current_date -1 day"));
        case 'weekly':
            return date('Y-m-d', strtotime("$current_date -1 week"));
        case 'monthly':
            return date('Y-m-d', strtotime("$current_date -1 month"));
        case 'yearly':
            return date('Y-m-d', strtotime("$current_date -1 year"));
    }
}
```

### 10.3 前端页面详细设计

#### 页面结构

```html
<!-- PK页面 -->
<div id="tab-pk" class="hidden">
    <!-- 周期选择器 -->
    <div class="card">
        <div class="period-selector">
            <button class="period-btn active" data-period="daily">今日</button>
            <button class="period-btn" data-period="weekly">本周</button>
            <button class="period-btn" data-period="monthly">本月</button>
            <button class="period-btn" data-period="yearly">本年</button>
        </div>
    </div>
    
    <!-- 当前用户排名卡片 -->
    <div class="card current-user-rank">
        <div class="rank-info">
            <div class="rank-number">#<span id="current-rank">-</span></div>
            <div class="rank-details">
                <div class="username" id="current-username"></div>
                <div class="rank-stats">
                    <span>学习 <strong id="current-words">0</strong> 个单词</span>
                    <span id="current-change"></span>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 排名列表 -->
    <div class="card">
        <h3>🏆 学习排行榜</h3>
        <div id="rankings-list" class="rankings-list">
            <!-- 动态生成 -->
        </div>
    </div>
</div>
```

#### CSS样式设计

```css
/* 前三名样式 */
.ranking-item.top-three {
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    border: 2px solid #f59e0b;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.ranking-item.top-three.rank-1 {
    background: linear-gradient(135deg, #fbbf24, #f59e0b); /* 金色 */
}

.ranking-item.top-three.rank-2 {
    background: linear-gradient(135deg, #e5e7eb, #9ca3af); /* 银色 */
}

.ranking-item.top-three.rank-3 {
    background: linear-gradient(135deg, #d97706, #b45309); /* 铜色 */
}

/* 排名变化图标 */
.rank-change.up {
    color: #10b981; /* 绿色 */
}

.rank-change.down {
    color: #ef4444; /* 红色 */
}

.rank-change.same {
    color: #94a3b8; /* 灰色 */
}

.rank-change.new {
    color: #3b82f6; /* 蓝色 */
}
```

### 10.4 API详细设计

#### get_rankings API

**请求**：
```
GET api.php?action=get_rankings&uid=1&period=daily&date=2026-01-29
```

**响应**：
```json
{
    "status": "ok",
    "period": "daily",
    "date": "2026-01-29",
    "rankings": [
        {
            "user_id": 1,
            "username": "用户1",
            "rank": 1,
            "rank_change": 0,
            "total_words": 50,
            "new_words": 30,
            "review_words": 20,
            "study_days": 7,
            "streak_days": 5,
            "mastered_words": 100,
            "completion_rate": 85.5,
            "is_current_user": false
        }
    ],
    "current_user": {
        "user_id": 3,
        "username": "当前用户",
        "rank": 3,
        "rank_change": 2,
        "total_words": 40,
        "new_words": 25,
        "review_words": 15,
        "study_days": 6,
        "streak_days": 4,
        "mastered_words": 80,
        "completion_rate": 80.0,
        "is_current_user": true
    },
    "total_users": 10,
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total_pages": 1
    }
}
```

---

## 十一、实施优先级建议

### 高优先级（必须修复）

1. **修复SQL注入风险**
   - `batch_pass` API
   - `export_json` API

2. **实现Session验证**
   - 服务端Session管理
   - 前端请求验证

3. **升级密码加密**
   - 迁移MD5到password_hash

### 中优先级（建议修复）

1. **代码重构**
   - 拆分api.php
   - 提取公共函数

2. **性能优化**
   - 添加缓存机制
   - 优化数据库查询

3. **实施PK功能**
   - 创建数据库表
   - 实现排名API
   - 创建PK页面

### 低优先级（可选优化）

1. **用户体验优化**
   - 添加loading动画
   - 优化错误提示

2. **功能扩展**
   - 好友系统
   - 成就系统

---

**报告完成时间**：2026-01-29
