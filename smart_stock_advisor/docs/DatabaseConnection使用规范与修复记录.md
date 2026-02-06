# DatabaseConnection 使用规范与修复记录

**创建日期**：2026-01-22  
**最后更新**：2026-01-22

---

## 一、问题背景

### 1.1 错误信息
```
AttributeError: 'DatabaseConnection' object has no attribute 'conn'
```

### 1.2 错误位置
- 文件：`utils/ml_model_manager.py`
- 方法：`save_model_info()`
- 行号：第101行

### 1.3 错误原因
`DatabaseConnection` 类设计为**纯类方法模式**（所有方法都是 `@classmethod`），不需要创建实例。但代码中错误地创建了实例并尝试使用实例方法，导致属性访问错误。

---

## 二、DatabaseConnection 类设计说明

### 2.1 类设计特点
- **纯类方法设计**：所有数据库操作方法都是 `@classmethod`
- **线程安全**：使用 `threading.local()` 实现每个线程独立的数据库连接
- **自动连接管理**：连接获取、重连、关闭都由类方法自动处理
- **无需实例化**：直接使用类名调用方法即可

### 2.2 正确使用方式

```python
from utils.db_connection import DatabaseConnection

# ✅ 正确：直接使用类方法
results = DatabaseConnection.execute_query("SELECT * FROM table WHERE id = %s", (id,))
affected_rows = DatabaseConnection.execute_update("UPDATE table SET name = %s WHERE id = %s", (name, id))

# ❌ 错误：不要创建实例
db = DatabaseConnection()  # 不要这样做
results = db.execute_query(...)  # 会导致 AttributeError
```

### 2.3 可用方法列表

| 方法 | 类型 | 说明 |
|------|------|------|
| `get_connection()` | 类方法 | 获取当前线程的数据库连接 |
| `close_connection()` | 类方法 | 关闭当前线程的数据库连接 |
| `execute_query(sql, params)` | 类方法 | 执行查询SQL，返回结果列表 |
| `execute_update(sql, params)` | 类方法 | 执行更新SQL（INSERT/UPDATE/DELETE），返回受影响行数 |
| `execute_many(sql, params_list)` | 类方法 | 批量执行SQL |
| `execute_transaction(operations)` | 类方法 | 执行事务（多个操作） |

---

## 三、修复记录

### 3.1 修复的文件
- `utils/ml_model_manager.py`

### 3.2 修复内容

#### 修复1：删除实例创建
**位置**：`MLModelManager.__init__()` 方法（第26行）

**修复前**：
```python
def __init__(self):
    self.db = DatabaseConnection()  # ❌ 错误：创建了实例
    self.logger = logger
    self.models_dir = os.path.join(project_root, 'models')
    self._model_cache = {}
```

**修复后**：
```python
def __init__(self):
    self.logger = logger
    self.models_dir = os.path.join(project_root, 'models')
    self._model_cache = {}
```

#### 修复2：统一使用类方法调用
**位置1**：`get_model_by_id()` 方法（第322行）

**修复前**：
```python
results = self.db.execute_query(sql, (model_id,))  # ❌ 错误：使用实例方法
```

**修复后**：
```python
results = DatabaseConnection.execute_query(sql, (model_id,))  # ✅ 正确：使用类方法
```

**位置2**：`activate_model()` 方法（第371行）

**修复前**：
```python
results = self.db.execute_query(sql, (model_id,))  # ❌ 错误：使用实例方法
```

**修复后**：
```python
results = DatabaseConnection.execute_query(sql, (model_id,))  # ✅ 正确：使用类方法
```

---

## 四、代码审查清单

在编写或修改使用 `DatabaseConnection` 的代码时，请检查：

- [ ] ✅ 是否直接使用 `DatabaseConnection.方法名()` 调用？
- [ ] ✅ 是否避免了创建 `DatabaseConnection()` 实例？
- [ ] ✅ 是否避免了使用 `self.db = DatabaseConnection()` 或 `db = DatabaseConnection()`？
- [ ] ✅ 是否避免了使用 `self.db.方法名()` 或 `db.方法名()`？

---

## 五、其他文件检查

### 5.1 存在类似问题的文件（待修复）

以下文件也存在类似问题，需要修复：

#### 文件1：`utils/confidence_calculator.py`
- **问题位置**：第97行创建实例，第241、419、537行使用实例方法
- **问题代码**：
  ```python
  self.db = DatabaseConnection() if USE_DATABASE else None  # 第97行
  result = self.db.execute_query(...)  # 第241、419、537行
  ```
- **影响**：如果 `USE_DATABASE=True`，会创建实例并导致同样的错误

#### 文件2：`utils/news_notification.py`
- **问题位置**：第29行创建实例，第139、196、232、236、275、301、327、367、401、441行使用实例方法
- **问题代码**：
  ```python
  self.db = DBConnection()  # 第29行
  result = self.db.execute_query(...)  # 多处使用
  self.db.execute_update(...)  # 多处使用
  ```
- **影响**：会创建实例并导致同样的错误

**修复建议**：
1. 删除 `self.db = DatabaseConnection()` 或 `self.db = DBConnection()` 这一行
2. 将所有 `self.db.execute_xxx()` 改为 `DatabaseConnection.execute_xxx()`
3. 删除 `self.use_database` 相关检查（类方法内部已处理）

### 5.2 建议的修复方式

如果确实需要检查数据库是否可用，可以这样处理：

```python
# ✅ 推荐方式：直接使用类方法，类方法内部会处理 USE_DATABASE 检查
from utils.db_connection import DatabaseConnection

# 直接调用，如果 USE_DATABASE=False，方法会返回空结果或0
results = DatabaseConnection.execute_query(sql, params)
if not results:
    # 处理无结果的情况
    pass
```

---

## 六、最佳实践

### 6.1 导入方式
```python
from utils.db_connection import DatabaseConnection
```

### 6.2 查询操作
```python
# 查询单条记录
sql = "SELECT * FROM table WHERE id = %s"
results = DatabaseConnection.execute_query(sql, (id,))
if results:
    record = results[0]

# 查询多条记录
sql = "SELECT * FROM table WHERE status = %s"
results = DatabaseConnection.execute_query(sql, ('active',))
for record in results:
    # 处理记录
    pass
```

### 6.3 更新操作
```python
# 插入记录
sql = "INSERT INTO table (name, value) VALUES (%s, %s)"
affected_rows = DatabaseConnection.execute_update(sql, (name, value))

# 更新记录
sql = "UPDATE table SET name = %s WHERE id = %s"
affected_rows = DatabaseConnection.execute_update(sql, (name, id))

# 删除记录
sql = "DELETE FROM table WHERE id = %s"
affected_rows = DatabaseConnection.execute_update(sql, (id,))
```

### 6.4 批量操作
```python
# 批量插入
sql = "INSERT INTO table (name, value) VALUES (%s, %s)"
params_list = [('name1', 'value1'), ('name2', 'value2'), ...]
affected_rows = DatabaseConnection.execute_many(sql, params_list)
```

### 6.5 事务操作
```python
operations = [
    ("INSERT INTO table1 (name) VALUES (%s)", ('name1',)),
    ("UPDATE table2 SET value = %s WHERE id = %s", ('value', 1)),
]
success = DatabaseConnection.execute_transaction(operations)
```

---

## 七、相关文件

- `utils/db_connection.py` - DatabaseConnection 类定义
- `utils/ml_model_manager.py` - 已修复的文件
- `config_db.py` - 数据库配置文件

---

## 八、更新日志

- **2026-01-22**：修复 `ml_model_manager.py` 中的 DatabaseConnection 使用错误
  - 删除实例创建
  - 统一使用类方法调用
  - 创建本文档记录修复过程和最佳实践
