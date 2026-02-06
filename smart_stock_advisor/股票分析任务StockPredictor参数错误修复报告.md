# 股票分析任务StockPredictor参数错误修复报告

## 一、问题描述

**错误信息**：
```
执行失败: StockPredictor.__init__() got an unexpected keyword argument 'data_source'
```

**问题位置**：设置页面 -> 股票分析 -> 定时任务执行

## 二、问题分析

### 2.1 错误原因

在 `utils/scheduled_task_manager.py` 的 `_execute_stock_analysis()` 方法中，代码尝试这样调用：

```python
data_source = StockDataSource()
predictor = StockPredictor(data_source=data_source)
```

但是 `StockPredictor.__init__()` 方法（在 `predictor/stock_predictor.py` 第81行）不接受任何参数：

```python
def __init__(self):
    self.data_source = StockDataSource()
    ...
```

### 2.2 问题根源

`StockPredictor` 类在初始化时会自动创建 `StockDataSource` 实例，不需要外部传入。

## 三、修复方案

### 3.1 修复内容

**文件**：`utils/scheduled_task_manager.py`
**方法**：`_execute_stock_analysis()`（第636-671行）

**修改1**：移除 `data_source` 参数
```python
# 修复前
data_source = StockDataSource()
predictor = StockPredictor(data_source=data_source)

# 修复后
predictor = StockPredictor()
```

**修改2**：使用 `predictor.data_source` 访问数据源
```python
# 修复前
stock_list = data_source.get_all_stock_list(limit=limit, sort_by_turnover=(sort_type == 'turnover'))

# 修复后
stock_list = predictor.data_source.get_all_stock_list(limit=limit, sort_by_turnover=(sort_type == 'turnover'))
```

**修改3**：移除不必要的导入
```python
# 修复前
from data_source.stock_data_source import StockDataSource
from predictor.stock_predictor import StockPredictor

# 修复后
from predictor.stock_predictor import StockPredictor
```

## 四、修复后的代码

```python
def _execute_stock_analysis(self, task: Dict) -> Dict:
    """执行股票分析任务"""
    try:
        # 通过模块导入的方式调用
        try:
            from predictor.stock_predictor import StockPredictor
            from visualizer.prediction_visualizer import PredictionVisualizer
            
            if StockPredictor is None:
                return {
                    'success': False,
                    'message': '股票分析模块未导入',
                    'error': '模块未导入'
                }
            
            # StockPredictor内部会自动创建StockDataSource实例，不需要传入
            predictor = StockPredictor()
            success_count = 0
            fail_count = 0
            
            # 如果指定了股票代码列表（个股分析）
            if symbols and isinstance(symbols, list) and len(symbols) > 0:
                # ... 个股分析逻辑
            else:
                # 全量分析：使用predictor内部的data_source
                stock_list = predictor.data_source.get_all_stock_list(limit=limit, sort_by_turnover=(sort_type == 'turnover'))
                # ... 全量分析逻辑
```

## 五、验证

### 5.1 修复验证

- ✅ 移除了 `data_source` 参数
- ✅ 使用 `predictor.data_source` 访问数据源
- ✅ 移除了不必要的 `StockDataSource` 导入
- ✅ 代码通过 linter 检查

### 5.2 功能验证

修复后，股票分析任务应该能够正常执行：
1. 创建股票分析定时任务
2. 启动任务
3. 任务应该能够正常执行，不再报错

## 六、注意事项

1. **StockPredictor 设计**：`StockPredictor` 类在初始化时会自动创建 `StockDataSource` 实例，这是其设计的一部分
2. **数据源访问**：如果需要访问数据源，应该使用 `predictor.data_source`，而不是单独创建实例
3. **一致性**：其他地方的代码（如 `web_app.py`）已经正确使用了 `StockPredictor()`，这次修复使其保持一致

---

**修复完成时间**：2026-01-26
**修改文件**：`utils/scheduled_task_manager.py`
**影响范围**：设置页面 -> 股票分析 -> 定时任务执行
