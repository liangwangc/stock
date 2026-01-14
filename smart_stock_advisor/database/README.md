# 数据库使用说明

## 概述

系统已支持MySQL数据库存储，所有数据将从CSV文件迁移到MySQL数据库。

## 数据库配置

### 1. 配置文件
编辑 `config_db.py` 文件，修改数据库连接信息：

```python
DB_CONFIG = {
    'host': 'localhost',      # 数据库主机
    'port': 3307,             # 数据库端口
    'user': 'root',           # 用户名
    'password': 'root',       # 密码
    'database': 'stock_data', # 数据库名
    'charset': 'utf8mb4',
    'autocommit': True,
    'connect_timeout': 10,
}

USE_DATABASE = True  # 是否启用数据库（False则使用CSV模式）
```

### 2. 创建数据库
在MySQL中创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS stock_data DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 初始化数据库

### 1. 安装依赖
确保已安装 `pymysql`：

```bash
pip install pymysql
```

### 2. 初始化数据库表
运行初始化脚本创建所有数据表：

```bash
py database/init_database.py
```

这将创建11个数据表：
- `stock_predictions` - 股票预测结果
- `north_bound_capital` - 北向资金数据
- `margin_trading` - 融资融券数据
- `main_force_capital` - 主力资金数据
- `sector_rotation` - 板块轮动数据
- `technical_indicators` - 技术指标数据
- `news_sentiment` - 新闻情感数据
- `market_sentiment` - 市场情绪数据
- `prediction_factors` - 预测因子数据
- `cost_distribution` - 成本分布数据
- `realtime_trading_decisions` - 实时交易决策数据

## 数据迁移

### 迁移现有CSV数据到数据库
如果您已有CSV数据，可以迁移到数据库：

```bash
py database/migrate_csv_to_db.py
```

**注意**：
- 迁移脚本目前只迁移 `stock_predictions.csv`
- 其他数据文件的迁移需要根据具体数据结构实现
- 建议：使用现有的保存方法重新保存数据（数据会同时保存到数据库）

## 使用方式

### 启用数据库模式
在 `config_db.py` 中设置：
```python
USE_DATABASE = True
```

### 禁用数据库模式（回退到CSV）
在 `config_db.py` 中设置：
```python
USE_DATABASE = False
```

## 兼容性

- **自动回退**：如果数据库连接失败，系统会自动回退到CSV模式
- **向后兼容**：所有CSV文件仍然保留，可以随时切换
- **数据迁移**：可以随时将CSV数据迁移到数据库

## 优势

1. **性能**：数据库查询比CSV读取快很多
2. **并发**：支持多线程并发访问
3. **数据完整性**：数据库约束保证数据一致性
4. **查询能力**：支持复杂SQL查询和数据分析
5. **扩展性**：易于添加新的查询和分析功能
6. **备份**：数据库备份比文件备份更方便

## 表结构说明

详细的表结构定义请参考 `database/init_database.sql` 文件。

每个表都包含：
- `created_at` - 创建时间（自动）
- `updated_at` - 更新时间（自动更新）
- 适当的索引和唯一键约束

## 故障排查

### 1. 连接失败
- 检查MySQL服务是否启动
- 检查 `config_db.py` 中的配置是否正确
- 检查数据库 `stock_data` 是否已创建

### 2. 表不存在
- 运行 `py database/init_database.py` 初始化数据库

### 3. 数据未保存
- 检查 `USE_DATABASE` 是否为 `True`
- 检查数据库连接是否正常
- 查看日志中的错误信息
