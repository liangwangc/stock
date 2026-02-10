# max_drawdown 与夏普比率功能展示位置

## 一、设置页面 → 模型学习 → 性能评估

**路径**：设置 → 模型学习与优化 → 点击「执行评估」按钮

**展示内容**：
- **方向准确率**：预测方向命中率
- **总收益率**：交易评估总收益（%）
- **胜率**：盈利交易占比
- **最大回撤**：从交易收益率序列计算的最大回撤（%）
- **夏普比率**：基于交易收益的风险调整后收益指标

**数据来源**：`/api/model/evaluate` → `ModelPerformanceEvaluator.evaluate_trading_performance`（基于 `realtime_trading_decisions` 表）

---

## 二、设置页面 → 模型学习 → 回测功能

**路径**：设置 → 模型学习与优化 → 回测/自动回测

**展示内容**：
- 回测结果中的 `metrics` 包含：总收益率、夏普比率、最大回撤、胜率、盈亏比
- 回测可视化（`backtest_visualizer`）会渲染最大回撤曲线图

**数据来源**：`BacktestEngine.backtest_predictions`（基于 `stock_predictions` 表）

---

## 三、模型优化

**路径**：设置 → 模型学习 → 参数优化

**使用方式**：`model_optimizer` 的综合评分会用到 `sharpe_ratio`、`max_drawdown`（权重 30%、20%），用于筛选更优参数组合。

---

## 四、数据库

- **model_performance** 表：保存评估结果时写入 `sharpe_ratio`、`max_drawdown` 字段
