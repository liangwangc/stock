# DataStorage初始化修复说明

**创建日期**：2026-01-22  
**问题**：`DataStorage.__init__() got an unexpected keyword argument 'use_database'`

---

## 一、问题描述

在执行定时任务"板块轮到每日功获取"时，出现以下错误：

```
TypeError: DataStorage.__init__() got an unexpected keyword argument 'use_database'
```

**错误位置**：`utils/scheduled_task_manager.py` → `_execute_other_data_collection()` 方法

---

## 二、问题原因

`DataStorage` 类的 `__init__` 方法只接受 `base_dir` 参数，不接受 `use_database` 参数。

**DataStorage类的设计**（`utils/data_storage.py:28`）：
```python
def __init__(self, base_dir: str = "data"):
    """
    初始化数据存储管理器
    
    Args:
        base_dir: 数据存储的基础目录（CSV模式使用）
    """
    self.base_dir = base_dir
    self.use_database = USE_DATABASE  # 从配置文件自动读取
    
    # 如果使用数据库，自动初始化数据库存储
    if self.use_database:
        self.db_storage = DatabaseStorage()
```

**说明**：
- `DataStorage` 会自动从配置文件（`config_db.py`）读取 `USE_DATABASE` 配置
- 如果 `USE_DATABASE=True`，会自动初始化 `DatabaseStorage()`
- **不需要**手动传入 `use_database` 参数

---

## 三、修复方案

### 3.1 修复前（错误）

```python
# 错误的调用方式
data_storage = DataStorage(use_database=True, db_storage=db_storage)
```

### 3.2 修复后（正确）

```python
# 正确的调用方式
db_storage = DatabaseStorage()  # 用于直接SQL操作
data_storage = DataStorage()     # 自动检测USE_DATABASE配置
```

**修复位置**：`utils/scheduled_task_manager.py:2125-2127`

---

## 四、修复内容

### 4.1 代码修改

**文件**：`utils/scheduled_task_manager.py`

**方法**：`_execute_other_data_collection()`（第2099行）

**修改内容**（第2124-2127行）：
```python
try:
    # 初始化数据存储
    db_storage = DatabaseStorage()  # 用于直接SQL操作
    # DataStorage会自动检测USE_DATABASE配置并初始化数据库存储（不需要传入参数）
    data_storage = DataStorage()     # 自动检测配置，无需传参
```

---

## 五、相关任务类型

此修复影响以下定时任务类型：

1. ✅ **北向资金获取**（`north_bound_capital`）
2. ✅ **市场指数获取**（`market_index`）
3. ✅ **融资融券获取**（`margin_trading`）
4. ✅ **主力资金获取**（`main_force_capital`）
5. ✅ **股票行业信息获取**（`stock_industry`）
6. ✅ **板块轮动获取**（`sector_rotation`）

---

## 六、验证方法

### 6.1 清理缓存

如果修复后仍然出现错误，可能是Python字节码缓存（.pyc文件）导致的：

**清理方法**：
```powershell
# PowerShell命令
cd d:\wjw_work\smart_stock_advisor
Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force
```

### 6.2 重启应用

清理缓存后，重启应用程序，确保使用最新的代码。

---

## 七、相关文件

| 文件 | 说明 |
|------|------|
| `utils/data_storage.py` | DataStorage类定义 |
| `utils/scheduled_task_manager.py` | 定时任务管理器 |
| `utils/db_storage.py` | DatabaseStorage类定义 |
| `config_db.py` | 数据库配置（USE_DATABASE） |

---

## 八、总结

✅ **问题已修复**：`DataStorage` 的初始化调用已更正  
✅ **修复位置**：`utils/scheduled_task_manager.py:2127`  
✅ **修复方式**：移除 `use_database` 参数，使用默认初始化  
✅ **缓存清理**：已清理所有 `.pyc` 文件

**注意事项**：
- `DataStorage` 会自动检测 `USE_DATABASE` 配置，无需手动传参
- 如果需要直接进行SQL操作，可以单独创建 `DatabaseStorage()` 实例
- 如果修复后仍有问题，请清理Python缓存并重启应用

---

**文档完成时间**：2026-01-22  
**状态**：✅ 已修复
