# web_app.py 运行错误修复说明

**修复日期**：2026-01-14

---

## 修复的问题

### 1. `model_optimizer.py` 中缺少 `config_manager` 初始化 ✅

**问题**：`ModelOptimizer.__init__()` 方法中缺少 `self.config_manager` 的初始化

**修复**：
```python
def __init__(self):
    self.db = DatabaseConnection()
    self.logger = logger
    self.backtest_engine = BacktestEngine()
    self.config_manager = PredictionConfigManager()  # 添加此行
```

**位置**：`utils/model_optimizer.py` 第31行

---

### 2. `optimize_weights_grid_search` 方法中 `current_score` 未定义 ✅

**问题**：在循环中使用了 `current_score`，但在循环之后才定义

**修复**：
- 移除了循环中对 `current_score` 的引用
- 在循环之后获取当前参数性能并计算 `current_score`

**位置**：`utils/model_optimizer.py` 第153行

---

### 3. `optimize_weights_grid_search` 返回值缺少交叉验证信息 ✅

**问题**：返回值没有包含交叉验证相关信息

**修复**：
- 添加 `optimization_method` 字段
- 如果使用交叉验证，添加 `use_cross_validation`、`train_ratio`、`best_validation_score` 字段

**位置**：`utils/model_optimizer.py` 第207-227行

---

### 4. `optimize_weights_bayesian` 方法缺失 ✅

**问题**：`optimize_weights_bayesian` 方法没有被正确添加到文件中

**修复**：
- 添加完整的 `optimize_weights_bayesian` 方法
- 支持贝叶斯优化和时间序列交叉验证
- 如果 scikit-optimize 不可用，自动回退到网格搜索

**位置**：`utils/model_optimizer.py` 第238-458行

---

### 5. `scheduled_task_manager.py` 中缺少优化方法选择逻辑 ✅

**问题**：`_execute_model_optimization` 方法没有使用新的优化方法选择逻辑

**修复**：
- 添加 `_check_bayesian_available()` 方法
- 修改 `_execute_model_optimization` 方法，支持选择优化方法（auto/grid_search/bayesian）
- 默认使用交叉验证

**位置**：
- `utils/scheduled_task_manager.py` 第741-747行（`_check_bayesian_available` 方法）
- `utils/scheduled_task_manager.py` 第700-720行（`_execute_model_optimization` 方法）

---

## 验证方法

### 1. 检查语法错误

```bash
python -m py_compile utils/model_optimizer.py
python -m py_compile utils/scheduled_task_manager.py
python -m py_compile web_app.py
```

### 2. 检查导入

```python
from utils.model_optimizer import ModelOptimizer
from utils.scheduled_task_manager import ScheduledTaskManager
import web_app
```

### 3. 检查方法是否存在

```python
optimizer = ModelOptimizer()
assert hasattr(optimizer, 'optimize_weights_grid_search')
assert hasattr(optimizer, 'optimize_weights_bayesian')

manager = ScheduledTaskManager()
assert hasattr(manager, '_check_bayesian_available')
```

---

## 如果仍然报错

### 常见错误及解决方法

1. **ImportError: No module named 'skopt'**
   - **原因**：scikit-optimize 未安装
   - **解决**：`pip install scikit-optimize` 或忽略（会自动回退到网格搜索）

2. **AttributeError: 'ModelOptimizer' object has no attribute 'config_manager'**
   - **原因**：`__init__` 方法中缺少初始化
   - **解决**：已修复，确保代码是最新的

3. **NameError: name 'current_score' is not defined**
   - **原因**：在定义前使用了变量
   - **解决**：已修复，移除了循环中的引用

4. **TypeError: optimize_weights_bayesian() missing 1 required positional argument**
   - **原因**：方法不存在或签名错误
   - **解决**：已添加完整的方法实现

---

## 测试步骤

1. **测试导入**：
   ```python
   python -c "from utils.model_optimizer import ModelOptimizer; print('OK')"
   ```

2. **测试实例化**：
   ```python
   python -c "from utils.model_optimizer import ModelOptimizer; o = ModelOptimizer(); print('OK')"
   ```

3. **测试方法存在**：
   ```python
   python -c "from utils.model_optimizer import ModelOptimizer; o = ModelOptimizer(); print(hasattr(o, 'optimize_weights_bayesian'))"
   ```

4. **运行web_app**：
   ```bash
   python web_app.py
   ```

---

## 修改的文件列表

1. ✅ `utils/model_optimizer.py`
   - 添加 `config_manager` 初始化
   - 修复 `current_score` 未定义问题
   - 添加 `optimize_weights_bayesian` 方法
   - 优化返回值结构

2. ✅ `utils/scheduled_task_manager.py`
   - 添加 `_check_bayesian_available` 方法
   - 修改 `_execute_model_optimization` 方法

3. ✅ `utils/model_performance_evaluator.py`
   - 优化查询SQL，关联配置表

4. ✅ `utils/stock_prediction_db.py`
   - 添加新字段的保存支持

5. ✅ `predictor/stock_predictor.py`
   - 添加学习分析字段的计算和记录

---

**状态**：✅ 所有修复已完成  
**下一步**：运行 `python web_app.py` 验证是否正常启动
