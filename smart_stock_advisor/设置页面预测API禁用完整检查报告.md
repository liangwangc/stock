# 设置页面股票预测分析 - API禁用完整检查报告

## 检查时间
2026-02-02

## 检查范围
设置页面 - 股票预测分析功能（手动点击和定时任务）

---

## 一、已修复的API调用点

### ✅ 1. 市场指数数据 (`get_market_index_data`)
- **状态**: 已修复
- **修复内容**: 添加 `use_db_only` 参数，当 `use_db_only=True` 时只从数据库获取
- **位置**: `data_source/stock_data_source.py:918`
- **数据库表**: `stock_history_data`（指数代码作为symbol）

### ✅ 2. 北向资金数据 (`get_north_bound_capital`)
- **状态**: 已修复
- **修复内容**: 添加 `use_db_only` 参数，当 `use_db_only=True` 时只从数据库获取
- **位置**: `data_source/stock_data_source.py:1294`
- **数据库表**: `north_bound_capital`
- **无数据时**: 返回中性值（0.0）

### ✅ 3. 融资融券数据 (`get_margin_trading_data`)
- **状态**: 已修复
- **修复内容**: 添加 `use_db_only` 参数，当 `use_db_only=True` 时只从数据库获取
- **位置**: `data_source/stock_data_source.py:1500`
- **数据库表**: `margin_trading`
- **无数据时**: 返回中性值（0.0）

### ✅ 4. 主力资金数据 (`get_main_force_capital`)
- **状态**: 已修复
- **修复内容**: 添加 `use_db_only` 参数，当 `use_db_only=True` 时只从数据库获取
- **位置**: `data_source/stock_data_source.py:1863`
- **数据库表**: `main_force_capital`
- **无数据时**: 返回中性值（0.0）

### ✅ 5. 美股板块数据 (`get_us_sector_data`)
- **状态**: 已修复
- **修复内容**: 添加 `use_db_only` 参数，当 `use_db_only=True` 时只从数据库获取
- **位置**: `data_source/stock_data_source.py:1121`
- **数据库表**: `us_sector_index_history`
- **无数据时**: 返回空DataFrame

### ✅ 6. 市场统计数据 (`get_market_statistics`)
- **状态**: 已修复
- **修复内容**: 添加 `use_db_only` 参数，当 `use_db_only=True` 时只从数据库获取
- **位置**: `data_source/stock_data_source.py:3277`
- **数据库表**: `stock_history_data`（统计当天所有股票）
- **无数据时**: 返回中性值（各比例0.5）

### ✅ 7. 股票行业信息 (`get_stock_industry_info`)
- **状态**: 已修复
- **修复内容**: 已有 `use_db_only` 参数，当 `use_db_only=True` 时只从数据库获取
- **位置**: `data_source/stock_data_source.py:502`
- **数据库表**: `stock_industry_info`
- **无数据时**: 返回空数据（industry='', concepts=[]）

### ✅ 8. 板块表现数据 (`get_sector_performance`)
- **状态**: 已修复（通过 `calculate_sector_rotation_score` 控制）
- **修复内容**: `calculate_sector_rotation_score` 在 `use_api=False` 时不调用 `get_sector_performance`
- **位置**: `predictor/stock_predictor.py:2070`
- **无数据时**: 使用空数据（industry_sectors={}, concept_sectors={}）

---

## 二、预测方法中的参数传递

### ✅ 1. `predict` 方法
- **位置**: `predictor/stock_predictor.py:3234`
- **参数**: `use_api: bool = True`
- **状态**: ✅ 已正确传递

### ✅ 2. `predict_market_overall` 方法
- **位置**: `predictor/stock_predictor.py:2367`
- **参数**: `use_api: bool = True`
- **状态**: ✅ 已正确传递

### ✅ 3. `calculate_news_score` 方法
- **位置**: `predictor/stock_predictor.py:905`
- **参数**: `use_api: bool = True`
- **状态**: ✅ 已正确传递，且支持预加载数据

### ✅ 4. `calculate_capital_flow_score` 方法
- **位置**: `predictor/stock_predictor.py:1932`
- **参数**: `use_api: bool = True`
- **状态**: ✅ 已正确传递

### ✅ 5. `calculate_us_sector_score` 方法
- **位置**: `predictor/stock_predictor.py:1662`
- **参数**: `use_api: bool = True`
- **状态**: ✅ 已正确传递

### ✅ 6. `calculate_sector_rotation_score` 方法
- **位置**: `predictor/stock_predictor.py:2070`
- **参数**: `use_api: bool = True`
- **状态**: ✅ 已正确传递

### ✅ 7. `calculate_market_sentiment_index` 方法
- **位置**: `predictor/stock_predictor.py:1529`
- **参数**: `use_api: bool = True`
- **状态**: ✅ 已修复，已添加参数

### ✅ 8. `calculate_market_score` 方法
- **位置**: `predictor/stock_predictor.py:1374`
- **参数**: `use_api: bool = True`
- **状态**: ✅ 已正确传递

### ✅ 9. `calculate_technical_score` 方法
- **位置**: `predictor/stock_predictor.py:190`
- **参数**: 无（只使用传入的data，不调用API）
- **状态**: ✅ 无需修改

### ✅ 10. `calculate_history_score` 方法
- **位置**: `predictor/stock_predictor.py:2871`
- **参数**: 无（只使用传入的data，不调用API）
- **状态**: ✅ 无需修改

---

## 三、独立任务配置检查

### ✅ `independent_tasks` 配置
- **位置**: `predictor/stock_predictor.py:3524`
- **状态**: ✅ 所有任务都正确传递了 `use_api` 参数：
  - `market_overall`: ✅ 传递 `use_api=use_api`
  - `news`: ✅ 传递 `use_api=use_api`
  - `capital_flow`: ✅ 传递 `use_api=use_api`
  - `valuation`: ✅ 使用 `_calculate_valuation_score_from_db`（不调用API）
  - `us_sector`: ✅ 传递 `use_api=use_api`
  - `sector_rotation`: ✅ 传递 `use_api=use_api`
  - `market_sentiment_index`: ✅ 传递 `use_api=use_api`

### ✅ `data_dependent_tasks` 配置
- **位置**: `predictor/stock_predictor.py:3535`
- **状态**: ✅ 所有任务都正确传递了参数：
  - `technical`: ✅ 不调用API（只使用data）
  - `market`: ✅ 传递 `use_api=use_api`
  - `history`: ✅ 不调用API（只使用data）

---

## 四、调用入口检查

### ✅ 1. 设置页面手动点击 (`web_app.py`)
- **位置**: `web_app.py:2568`
- **调用**: `thread_predictor.predict(..., use_api=False, ...)`
- **状态**: ✅ 已正确传递 `use_api=False`

### ✅ 2. 定时任务 (`scheduled_task_manager.py`)
- **位置**: `scheduled_task_manager.py:754, 837`
- **调用**: `predictor.predict(..., use_api=False)`
- **状态**: ✅ 已修复，已添加 `use_api=False`

---

## 五、数据预加载优化

### ✅ 1. 市场指数数据预加载
- **位置**: `web_app.py:2450`
- **方法**: `get_all_market_indices(days=20, use_db_only=True)`
- **状态**: ✅ 已实现

### ✅ 2. 股票历史数据批量预加载
- **位置**: `web_app.py:2462`
- **方法**: `get_stocks_history_data_batch(...)`
- **状态**: ✅ 已实现

### ✅ 3. PE/PB数据批量预加载
- **位置**: `web_app.py:2401`
- **方法**: 批量查询 `stock_history_data` 表
- **状态**: ✅ 已实现

### ✅ 4. 市场整体预测结果预计算
- **位置**: `web_app.py:2439`
- **方法**: `predict_market_overall(use_api=False)`
- **状态**: ✅ 已实现

### ✅ 5. 新闻数据批量预加载
- **位置**: `web_app.py:2529`
- **方法**: `get_today_news_by_symbol`, `get_today_market_news`
- **状态**: ✅ 已实现

### ✅ 6. 行业信息批量预加载
- **位置**: `web_app.py:2549`
- **方法**: 批量查询 `stock_industry_info` 表
- **状态**: ✅ 已实现

---

## 六、无数据时的处理策略

### ✅ 所有方法统一策略
- **数据库无数据时**: 返回中性值或空数据，**不调用API**
- **中性值示例**:
  - 资金流向: `{'score': 0.0, 'trend': 'neutral'}`
  - 市场情绪: `{'fear_index': 50.0, 'greed_index': 50.0, 'sentiment': 'neutral'}`
  - 预测结果: `{'prediction': '震荡', 'up_probability': 0.5, 'down_probability': 0.5}`

---

## 七、检查清单

- [x] `get_market_index_data` - 添加 `use_db_only` 支持
- [x] `get_north_bound_capital` - 添加 `use_db_only` 支持
- [x] `get_margin_trading_data` - 添加 `use_db_only` 支持
- [x] `get_main_force_capital` - 添加 `use_db_only` 支持
- [x] `get_us_sector_data` - 添加 `use_db_only` 支持
- [x] `get_market_statistics` - 添加 `use_db_only` 支持
- [x] `get_stock_industry_info` - 已有 `use_db_only` 支持
- [x] `calculate_capital_flow_score` - 传递 `use_api` 参数
- [x] `calculate_us_sector_score` - 传递 `use_api` 参数
- [x] `calculate_sector_rotation_score` - 传递 `use_api` 参数
- [x] `calculate_market_sentiment_index` - 添加 `use_api` 参数
- [x] `calculate_market_score` - 传递 `use_api` 参数
- [x] `calculate_news_score` - 传递 `use_api` 参数
- [x] `predict` 方法 - 传递 `use_api` 参数
- [x] `predict_market_overall` - 传递 `use_api` 参数
- [x] `independent_tasks` - 所有任务传递 `use_api` 参数
- [x] `data_dependent_tasks` - 所有任务传递 `use_api` 参数
- [x] 设置页面调用 - 传递 `use_api=False`
- [x] 定时任务调用 - 传递 `use_api=False`
- [x] 无数据时返回中性值，不调用API

---

## 八、预期效果

### ✅ 设置页面股票预测分析现在应：
1. **完全禁用API调用** - 所有数据都从数据库获取
2. **数据库无数据时返回中性值** - 不尝试调用API
3. **性能优化** - 批量预加载数据，减少数据库查询次数
4. **功能正常** - 预测结果仍然准确，只是数据来源不同

### ✅ 如果仍有API调用，可能的原因：
1. 数据库中没有对应的数据表或数据
2. 某些方法内部仍有遗漏的API调用
3. 第三方库（如akshare）的内部调用

---

## 九、测试建议

1. **功能测试**: 确保预测结果仍然正常
2. **性能测试**: 对比优化前后的性能
3. **日志检查**: 检查是否还有API调用日志
4. **数据库检查**: 确保相关数据表有数据

---

**报告生成时间**: 2026-02-02
**检查人员**: AI Assistant
**状态**: ✅ 所有API调用点已修复
