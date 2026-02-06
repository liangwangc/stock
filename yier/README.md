# 付一二（MemoCalendar）- 单词记忆系统

基于艾宾浩斯遗忘曲线的单词记忆网站

## 项目简介

这是一个智能单词记忆系统，帮助用户通过科学的复习算法高效记忆单词。

### 主要功能

1. **用户系统**
   - 用户登录/注册
   - 每日学习目标设置

2. **单词管理**
   - 单词录入（支持有道词典自动查询）
   - 日历打卡显示
   - 补录/预约录入功能

3. **学习系统**
   - 卡片式学习界面
   - 基于艾宾浩斯遗忘曲线的智能复习算法
   - 复习质量评分（1-5分）
   - 语音朗读功能

4. **统计功能**
   - 记忆熟练度分布图表
   - 未来7天复习压力预测
   - 数据导出（CSV格式）

5. **其他功能**
   - 深色模式切换
   - 响应式设计，支持移动端

## 技术栈

- **后端**: PHP 7.4+
- **数据库**: MySQL 5.7+ / MariaDB 10.3+
- **前端**: HTML5, CSS3, JavaScript (原生)
- **图表库**: Chart.js
- **API**: 有道词典API（查词功能）

## 环境要求

- PHP 7.4 或更高版本
- MySQL 5.7 或更高版本（或 MariaDB 10.3+）
- Web服务器（Apache/Nginx）或 PHP内置服务器
- 浏览器支持 ES6+

## 安装步骤

### 1. 数据库设置

#### 方法一：使用提供的SQL备份文件

```bash
# 导入数据库
mysql -u root -p < word_app_backup_20260129.sql
```

#### 方法二：手动创建数据库

```sql
CREATE DATABASE word_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE word_app;

CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    daily_goal INT DEFAULT 5,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE words (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    word VARCHAR(100) NOT NULL,
    pronunciation VARCHAR(100) DEFAULT '',
    meaning TEXT,
    example TEXT,
    date_added DATE NOT NULL,
    next_review DATE NOT NULL,
    interval_days INT DEFAULT 0,
    ef_factor FLOAT DEFAULT 2.5,
    repetitions INT DEFAULT 0,
    status ENUM('new','learning','review','mastered') DEFAULT 'new',
    PRIMARY KEY (id),
    KEY user_id (user_id),
    CONSTRAINT words_ibfk_1 FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 2. 配置数据库连接

编辑 `api.php` 文件，修改数据库配置：

```php
$db_host = 'localhost';      // 数据库主机
$db_user = 'root';           // 数据库用户名
$db_pass = 'root';           // 数据库密码
$db_name = 'word_app';       // 数据库名
```

### 3. 测试数据库连接

#### 方法一：使用Python脚本测试（推荐）

```bash
# 安装依赖
pip install pymysql

# 运行测试
python test_db_connection.py
```

#### 方法二：使用PHP测试脚本

在浏览器中访问：`http://localhost/yier/test_db.php`

#### 方法三：使用PHP内置服务器

```bash
cd yier
php -S localhost:8000
```

然后访问：`http://localhost:8000/test_db.php`

### 4. 启动Web服务器

#### 使用PHP内置服务器（开发环境）

```bash
cd yier
php -S localhost:8000
```

访问：`http://localhost:8000`

#### 使用Apache/Nginx（生产环境）

将项目文件复制到Web服务器目录：
- Apache: `C:\xampp\htdocs\yier\` 或 `/var/www/html/yier/`
- Nginx: 配置虚拟主机指向项目目录

## 数据库连接测试

### 快速测试

运行以下命令测试数据库连接：

```bash
# Python方式（需要安装pymysql）
python test_db_connection.py

# PHP方式（需要Web服务器）
# 访问 http://localhost/yier/test_db.php
```

### 手动测试MySQL连接

```bash
# Windows
mysql -u root -p
# 输入密码后执行
USE word_app;
SHOW TABLES;
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM words;
```

## 项目结构

```
yier/
├── api.php                      # 后端API接口
├── index.html                   # 前端页面
├── test_db.php                  # PHP数据库测试脚本
├── test_db_connection.py        # Python数据库测试脚本
├── word_app_backup_20260129.sql # 数据库备份文件
└── README.md                    # 项目说明文档
```

## API接口说明

### 用户相关
- `POST api.php?action=login` - 用户登录/注册
- `POST api.php?action=update_settings` - 更新用户设置

### 单词相关
- `POST api.php?action=add_word` - 添加单词
- `GET api.php?action=calendar_data` - 获取日历数据
- `GET api.php?action=day_details` - 获取某日详情
- `GET api.php?action=get_home_data` - 获取首页数据

### 学习相关
- `POST api.php?action=submit_review` - 提交复习结果
- `GET api.php?action=get_stats` - 获取统计数据

### 工具相关
- `GET api.php?action=lookup` - 查词代理（有道词典）
- `GET api.php?action=export_csv` - 导出CSV

## 常见问题

### 1. 数据库连接失败

**检查项：**
- MySQL服务是否启动
- 数据库用户名密码是否正确
- 数据库 `word_app` 是否存在
- 防火墙是否阻止了连接

**解决方法：**
```bash
# Windows检查MySQL服务
net start MySQL

# Linux检查MySQL服务
sudo systemctl status mysql
```

### 2. PHP无法连接数据库

**检查项：**
- PHP是否安装了mysqli扩展
- php.ini中是否启用了mysqli

**解决方法：**
```bash
# 检查PHP扩展
php -m | grep mysqli

# 如果没有，编辑php.ini，取消注释：
# extension=mysqli
```

### 3. 时区问题

项目已设置时区为 `Asia/Shanghai`（北京时间），如果仍有问题，检查：
- PHP时区设置
- MySQL时区设置

## 开发说明

### 复习算法

系统使用改进的SM-2算法（SuperMemo 2）：
- 根据复习质量动态调整间隔
- EF因子（易度因子）范围：1.3 - 3.0
- 复习间隔：1天 → 6天 → 递增

### 数据流程

1. 用户录入单词 → 状态设为 `new`
2. 开始学习 → 状态变为 `learning`
3. 复习评分 → 根据评分更新间隔和状态
4. 达到熟练 → 状态变为 `review` 或 `mastered`

## 许可证

本项目仅供学习使用。

## 更新日志

- 2026-01-29: 项目初始版本
  - 基础功能实现
  - 数据库备份文件
  - 测试脚本

## 联系方式

如有问题，请查看代码注释或提交Issue。
