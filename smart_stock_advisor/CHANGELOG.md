# 更新日志 (CHANGELOG)

本文档记录 Smart Stock Advisor 项目的所有更新历史。

---

## [2026-01-11] - 设置页面功能扩展：实时交易策略配置

### 新增功能
- ✅ **实时交易策略配置界面**（`templates/settings.html` - 参数设置面板）：
  - 在参数设置面板中添加了"实时交易策略配置"子面板
  - **信号阈值配置**：
    - 买入信号阈值（buy_signal_threshold: 0.65）
    - 强烈买入阈值（strong_buy_threshold: 0.75）
    - 卖出信号阈值（sell_signal_threshold: 0.60）
    - 强烈卖出阈值（strong_sell_threshold: 0.70）
    - 最低置信度（min_confidence: 0.55）
    - 高置信度（high_confidence: 0.70）
  - **风险控制参数**：
    - 止损比例（stop_loss_pct: -5.0%）
    - 止盈比例（take_profit_pct: 8.0%）
    - 移动止损比例（trailing_stop_pct: 3.0%）
    - 追高警告阈值（chase_high_threshold: 5.0%）
    - 抄底机会阈值（catch_low_threshold: -5.0%）
    - 启用风险控制开关（enable_risk_control）
  - **仓位管理**：
    - 单只股票最大仓位（max_position_pct: 30.0%）
    - 总仓位上限（max_total_position_pct: 80.0%）
    - 建仓步进（position_step: 10.0%）
    - 最大相关性（max_correlation: 0.8）
  - **实时数据权重和监控设置**：
    - 资金流向权重（capital_flow_weight: 0.25）
    - 买卖盘权重（bid_ask_weight: 0.15）
    - 盘中涨跌调整权重（intraday_weight: 0.10）
    - 监控间隔（monitor_interval: 60秒）
    - 信号变化提醒开关（alert_on_signal_change）
  - 配置项分组显示（信号阈值、风险控制、仓位管理、实时数据权重和监控）
  - 支持配置保存、加载、激活（使用现有的预测参数配置API）

### 代码变更
- `templates/settings.html`：
  - 添加实时交易策略配置HTML结构（在技术指标参数配置之后）
  - 更新 `loadConfigValues()` 函数：添加trading配置的加载逻辑
  - 更新 `getCurrentConfigValues()` 函数：添加trading配置的获取逻辑
  - 更新 `loadDefaultConfig()` 函数：添加trading配置的默认值加载
  - 修复ID冲突：使用 `trading_capital_flow_weight`, `trading_bid_ask_weight`, `trading_intraday_weight` 避免与预测权重配置冲突

### 技术说明
- 实时交易策略配置通过现有的预测参数配置系统存储，使用 `values.trading` 字段
- 配置验证函数暂时不验证trading配置（可选分类），但不影响保存和读取
- 配置可以与其他配置（prediction、indicator）一起保存、加载、激活

### 配置文件
- 默认值来自 `config.py` 中的 `TRADING_CONFIG`（第85-125行）

---

## [2024] - 统一错误处理机制实施

### 新增功能
- ✅ **统一异常类系统** (`utils/exceptions.py`)
  - `BaseAPIException`: API异常基类，提供统一接口
  - `ValidationError`: 输入验证错误（400）
  - `AuthenticationError`: 认证错误（401）
  - `AuthorizationError`: 授权错误（403）
  - `NotFoundError`: 资源未找到错误（404）
  - `DatabaseError`: 数据库操作错误（500）
  - `ExternalAPIError`: 外部API调用错误（502）
  - `BusinessLogicError`: 业务逻辑错误（400）
  - `ConfigurationError`: 配置错误（500）

- ✅ **错误处理工具模块** (`utils/error_handler.py`)
  - `@handle_api_error`: API错误处理装饰器，自动捕获异常并转换
  - `@validate_json_request`: JSON请求验证装饰器
  - `success_response()`: 创建成功响应的工具函数
  - `error_response()`: 创建错误响应的工具函数
  - `log_and_handle_error()`: 记录错误并返回统一响应的工具函数

- ✅ **Flask全局错误处理器**
  - 在 `web_app.py` 中注册全局错误处理器
  - 自定义异常处理 (`BaseAPIException`)
  - 404错误处理（API和页面请求分别处理）
  - 500错误处理（统一错误响应格式）

### 优化内容
- **统一错误响应格式**：
  ```json
  {
    "success": false,
    "error_code": "ERROR_CODE",
    "message": "错误消息",
    "details": {}
  }
  ```

- **错误日志记录**：
  - 自动记录所有API异常
  - 记录未预期异常的详细堆栈信息
  - 区分警告级别和错误级别日志

### 使用方法

#### 1. 使用装饰器处理错误
```python
from utils.error_handler import handle_api_error
from utils.exceptions import ValidationError

@app.route('/api/example')
@handle_api_error
def api_example():
    # 抛出异常会自动转换为JSON响应
    if not request.json:
        raise ValidationError("请求数据不能为空")
    return success_response(data={})
```

#### 2. 使用异常类
```python
from utils.exceptions import NotFoundError, DatabaseError

if not resource:
    raise NotFoundError("资源未找到", resource_type="stock", resource_id=symbol)

try:
    # 数据库操作
except Exception as e:
    raise DatabaseError("数据库操作失败", details={'error': str(e)})
```

#### 3. 使用工具函数
```python
from utils.error_handler import success_response, error_response

# 成功响应
return success_response(data=result, message="操作成功")

# 错误响应
return error_response("操作失败", error_code="OPERATION_FAILED", status_code=400)
```

### 后续计划
- [ ] 逐步迁移现有API端点使用新的错误处理机制
- [ ] 前端统一错误展示（可选）
- [ ] 添加更多业务场景的错误处理示例

---

## [未发布] - 新闻系统改进优化

### 新增功能

1. **新闻任务调度统一**
   - 将新闻抓取任务统一使用 `ScheduledTaskManager` 进行调度
   - 支持 `interval` 类型的间隔调度（用于新闻抓取）
   - 保持 `NewsTaskManager` API不变，确保向后兼容
   - 文件：`smart_stock_advisor/utils/news_task_manager.py`

2. **情感分析优化**
   - 引入jieba分词库（可选，如果不存在则回退到简单分词）
   - 增加新闻重要性评分功能（基于关键词、来源、内容长度等因素）
   - 优化否定词处理逻辑，提高情感分析准确性
   - 文件：`quant_trading_platform/news/sentiment_analyzer.py`

3. **推送功能完善**
   - 支持自定义推送规则（用户可配置阈值和条件）
   - 实现推送去重功能（内存缓存+数据库检查，支持可配置的时间窗口）
   - 添加推送历史记录查询功能
   - 添加推送规则配置API
   - 文件：`smart_stock_advisor/utils/news_notification.py`
   - API接口：
     - `GET /api/news/notifications` - 获取推送通知列表
     - `GET /api/news/notifications/history` - 获取推送历史记录
     - `GET /api/news/notifications/rules` - 获取推送规则配置
     - `POST /api/news/notifications/rules` - 更新推送规则配置

### 依赖更新

- 新增依赖：`jieba>=0.42.1`（中文分词，用于情感分析优化）
   - 文件：`smart_stock_advisor/requirements.txt`

### 改进说明

- **任务调度统一**：新闻抓取任务现在使用统一的调度器，与其他任务（如股票数据收集、模型学习）保持一致，便于管理和监控。
- **情感分析增强**：jieba分词可以提高中文文本的分词准确性，从而提升情感分析的准确度。如果jieba不可用，系统会自动回退到简单分词，不影响现有功能。
- **重要性评分**：新增的新闻重要性评分可以帮助用户更好地识别重要新闻，推送系统可以根据重要性评分来决定是否推送。
- **推送规则配置**：用户可以根据自己的需求自定义推送规则，包括最低置信度、最低情感得分、最低重要性评分等阈值，提高推送的针对性和准确性。
- **推送去重**：通过内存缓存和数据库检查，确保同一新闻在指定时间窗口内不会重复推送，避免打扰用户。
- **推送历史**：用户可以查看推送历史记录，了解已推送的新闻和推送时间。

### 后续计划

- 实现浏览器通知（Web Notification API）
- 支持用户级别的推送规则配置（保存到数据库）
- 考虑引入BERT等深度学习模型进行更准确的情感分析
- 支持cron表达式配置（使用APScheduler库）

---

## [2026-01-10] - 交易成本优化和交易记录管理实施

### 优化内容

#### 1. 交易成本管理模块 ✅
- **新增模块** (`utils/trading_cost_manager.py`)：
  - ✅ `TradingCostManager`: 交易成本管理器类
    - 实现精确交易成本计算（考虑不同券商费率）
    - 实现交易频率限制（避免过度交易）
    - 实现交易成本统计和分析
    - 实现交易记录管理功能（手动录入真实交易）

#### 2. 精确交易成本计算 ✅
- ✅ `calculate_trading_cost()`: 精确计算交易成本
  - 支持不同券商费率配置（佣金费率、最低佣金、印花税、过户费等）
  - 买入成本：佣金 + 过户费 + 滑点成本
  - 卖出成本：佣金 + 印花税 + 过户费 + 滑点成本
  - 自动应用最低佣金限制（默认5元）
  - 计算成本率（总成本/总金额）
  - 提供详细的成本明细说明

#### 3. 交易频率限制 ✅
- ✅ `check_trading_frequency()`: 检查交易频率限制
  - 支持自定义检查天数（默认7天）和最大交易次数（默认3次）
  - 按股票代码和交易方向分别检查
  - 提供警告信息（接近限制时警告，超过限制时阻止）
  - 避免过度交易，降低交易成本

#### 4. 交易成本统计和分析 ✅
- ✅ `get_trading_cost_statistics()`: 获取交易成本统计
  - 总交易次数、总成本、平均成本率
  - 按方向统计（买入/卖出成本对比）
  - 按股票统计（每只股票的交易成本、交易次数、成本率）
  - 成本趋势分析（按日期统计每日交易成本）
  - 成本组成分析（佣金、印花税、过户费、滑点的占比和百分比）

#### 5. 交易记录管理功能 ✅
- ✅ `record_trading_transaction()`: 记录真实交易（用于手动录入）
  - 自动计算交易成本并保存到数据库
  - 支持关联决策ID（可选，关联实时交易决策）
  - 支持备注信息
  - 保存完整的交易信息（股票代码、方向、价格、数量、成本明细等）
  
- ✅ `get_transaction_history()`: 查询交易记录历史
  - 支持按股票代码、时间范围筛选
  - 支持限制返回记录数
  - 按交易时间倒序排列

#### 6. 数据库表设计 ✅
- ✅ 创建交易记录表 (`database/trading_transactions_table.sql`)
  - `trading_transactions` 表：存储真实交易记录
  - 包含交易基本信息（股票代码、方向、价格、数量、金额、日期时间）
  - 包含成本明细（佣金、印花税、过户费、滑点、总成本、成本率）
  - 包含券商信息和备注
  - 支持关联决策ID，便于后续分析预测决策与真实交易的关系
  - 创建必要的索引（股票代码、交易日期、交易方向、决策ID）

### 技术特点
- 精确计算：考虑所有交易成本（佣金、印花税、过户费、滑点）
- 券商配置：支持不同券商费率配置，可扩展
- 频率限制：防止过度交易，降低交易成本
- 统计分析：多维度统计交易成本，便于分析和优化
- 记录管理：支持手动录入真实交易，方便后续分析与决策

### 影响范围
- **文件修改**：
  - `smart_stock_advisor/utils/trading_cost_manager.py`（新增）
  - `smart_stock_advisor/database/trading_transactions_table.sql`（新增）
  - `smart_stock_advisor/项目完整报告.md`（更新状态）

### 使用说明
- **交易后手动录入**：
  ```python
  from utils.trading_cost_manager import get_trading_cost_manager
  manager = get_trading_cost_manager()
  result = manager.record_trading_transaction(
      symbol='600519',
      direction='buy',
      price=1800.0,
      quantity=100,
      notes='根据系统建议买入'
  )
  ```

- **查看交易统计**：
  ```python
  statistics = manager.get_trading_cost_statistics(days=30, symbol='600519')
  ```

- **查看交易历史**：
  ```python
  history = manager.get_transaction_history(symbol='600519', days=30)
  ```

- **检查交易频率**：
  ```python
  frequency_check = manager.check_trading_frequency('600519', 'buy', days=7, max_trades=3)
  ```

- **计算交易成本**（交易前评估）：
  ```python
  cost = manager.calculate_trading_cost('600519', 1800.0, 100, 'buy')
  ```

---

## [2026-01-10] - 实时交易策略风险控制优化实施

### 优化内容

#### 1. 风险管理模块 ✅
- **新增模块** (`utils/risk_manager.py`)：
  - ✅ `RiskManager`: 风险管理器类
    - 实现动态止损/止盈（根据波动率调整）
    - 实现组合风险控制（相关性检查、HHI指数）
    - 实现仓位管理优化（基于风险评分）
    - 实现风险限额管理

#### 2. 动态止损/止盈 ✅
- ✅ `calculate_dynamic_stop_loss_take_profit()`: 根据波动率调整止损/止盈
  - 计算历史波动率（使用收益率标准差，默认20天）
  - 根据波动率/基准波动率（2%）计算调整因子（范围0.5-2.0）
  - 波动率高时扩大止损/止盈幅度，低时缩小
  - 限制止损范围（-15%到-2%），止盈范围（3%到20%）
  - 提供详细的调整说明

#### 3. 组合风险控制 ✅
- ✅ `calculate_portfolio_risk()`: 计算组合风险
  - HHI指数（赫芬达尔-赫希曼指数）：衡量组合集中度（范围0-1，越高越集中）
  - 相关性矩阵：计算股票之间的相关性（使用60天历史数据）
  - 分散化得分：综合考虑HHI（60%）和相关性（40%）
  - 提供风险警告和优化建议：
    - HHI > 0.5: 集中度风险警告
    - 最大相关性 > 0.8: 高度相关警告
    - 平均相关性 > 0.6: 相关性较高警告

#### 4. 仓位管理优化 ✅
- ✅ `optimize_position_size()`: 基于风险评分优化仓位
  - 风险因子权重：
    - 信号强度风险（30%）：信号越强，风险越低
    - 置信度风险（25%）：置信度越高，风险越低
    - 波动率风险（25%）：波动率越高，风险越大
    - 组合集中度风险（20%）：集中度越高，风险越大
  - 根据风险评分动态调整建议仓位（风险高时降低仓位）
  - 考虑总仓位限制和单股仓位限制
  - 提供详细的仓位建议理由和风险因子分析

#### 5. 风险限额管理 ✅
- ✅ `check_risk_limits()`: 检查风险限额
  - 总仓位限制：检查总仓位是否超过上限（默认80%）
  - 单股仓位限制：检查单只股票仓位是否超过上限（默认30%）
  - 单股亏损限制：检查单只股票亏损是否超过限制（默认-10%）
  - 相关性限制：检查组合最大相关性是否超过限制（默认0.8）
  - 支持新持仓建议的前置检查（避免添加新持仓后违规）
  - 提供违规列表、警告列表和建议列表

#### 6. RealtimeTradingAdvisor 集成 ✅
- ✅ 更新 `_make_trading_decision()` 方法：
  - 集成动态止损/止盈功能
  - 自动根据波动率调整止损/止盈阈值
  - 保留市场状态调整逻辑，在此基础上叠加波动率调整
  - 将动态调整结果保存到决策中
  - 所有功能都有回退机制，确保在模块不可用时不影响主流程

### 技术特点
- 波动率计算：使用历史收益率标准差，支持自定义计算周期
- 相关性计算：使用pandas计算相关性矩阵，支持多只股票
- 风险评分：多因子加权计算，权重可配置
- 风险限额：多层次检查，包含总仓位、单股仓位、亏损、相关性等
- 回退机制：所有功能都有完善的异常处理和回退逻辑

### 影响范围
- **文件修改**：
  - `smart_stock_advisor/utils/risk_manager.py`（新增）
  - `smart_stock_advisor/predictor/realtime_trading_advisor.py`（修改）
  - `smart_stock_advisor/项目完整报告.md`（更新状态）

### 使用说明
- 风险管理器自动启用，无需额外配置
- 动态止损/止盈会在交易决策时自动应用（如果风险管理器可用）
- 可以通过 `get_risk_manager().calculate_portfolio_risk()` 手动计算组合风险
- 可以通过 `get_risk_manager().optimize_position_size()` 手动优化仓位大小
- 可以通过 `get_risk_manager().check_risk_limits()` 手动检查风险限额

---

## [2026-01-10] - 实时交易策略信号生成优化实施

### 优化内容

#### 1. 信号分析器模块 ✅
- **新增模块** (`utils/signal_analyzer.py`)：
  - ✅ `SignalAnalyzer`: 信号分析器类
    - 实现信号准确率统计（按信号类型、按股票、按信号强度）
    - 实现根据历史表现动态调整信号阈值
    - 实现信号强度评分说明功能

#### 2. 信号准确率统计 ✅
- ✅ `get_signal_accuracy_statistics()`: 获取信号准确率统计
  - 按信号类型统计（BUY/SELL/ADD/REDUCE/HOLD）
  - 按股票统计（每只股票的信号表现）
  - 按信号强度统计（STRONG/MODERATE/NEUTRAL/WEAK）
  - 统计指标：总数量、命中数、未命中数、准确率、平均盈利/亏损百分比
  - 支持按股票代码和信号类型筛选
  - 支持自定义统计天数（默认30天）
  - 实现缓存机制（TTL=2小时）减少数据库查询

#### 3. 动态阈值调整 ✅
- ✅ `get_optimized_thresholds()`: 根据历史表现动态调整信号阈值
  - 买入阈值优化：准确率<55%时提高阈值（最多+0.05），>70%时降低阈值（最多-0.03）
  - 强烈买入阈值优化：基于买入信号准确率调整（±0.02）
  - 卖出阈值优化：同样的逻辑
  - 强烈卖出阈值优化：基于卖出信号准确率调整（±0.02）
  - 提供详细的调整原因和建议
  - 支持最小样本数限制（默认20）确保统计有效性

#### 4. 信号强度评分说明 ✅
- ✅ `generate_signal_explanation()`: 生成信号强度评分说明
  - 详细分解各因子得分和权重：
    - 预测得分（权重50%）
    - 资金流向（权重25%）
    - 买卖盘（权重15%）
    - 盘中调整（权重10%）
  - 按贡献度排序展示各因子的作用
  - 提供文字说明和改进建议
  - 解释信号强度的含义（强烈/较强/中等/较弱/很弱）
  - 描述各因子的状态（看涨/看跌、净流入/流出、买盘强/卖盘强等）

#### 5. RealtimeTradingAdvisor 集成 ✅
- ✅ 更新 `__init__()` 方法：
  - 自动加载优化后的信号阈值（基于历史表现）
  - 在初始化时尝试获取优化阈值并更新配置
  - 保留基础配置作为回退机制
- ✅ 更新 `get_realtime_decision()` 方法：
  - 生成信号强度评分说明
  - 将信号说明添加到决策结果中
- ✅ 更新 `_print_decision_summary()` 方法：
  - 输出信号强度评分说明
  - 展示各因子的贡献度和解释

### 技术特点
- 数据库查询：自动查询历史交易决策数据进行分析
- 缓存机制：减少重复查询，提升性能（TTL=2小时）
- 回退机制：信号分析器不可用时自动回退到基础配置
- 详细日志：提供调试信息，便于问题排查
- 智能调整：基于历史准确率自动优化阈值，持续改进信号质量

### 影响范围
- **文件修改**：
  - `smart_stock_advisor/utils/signal_analyzer.py`（新增）
  - `smart_stock_advisor/predictor/realtime_trading_advisor.py`（修改）
  - `smart_stock_advisor/项目完整报告.md`（更新状态）

### 使用说明
- 信号分析器自动启用，无需额外配置
- 信号阈值会在初始化时自动优化（如果数据库中有足够的历史数据）
- 每次交易决策都会生成信号强度评分说明（如果信号分析器可用）
- 可以通过 `get_signal_analyzer().get_signal_accuracy_statistics()` 手动获取统计信息

---

## [2026-01-10] - 置信度计算优化实施

### 优化内容

#### 1. 增强的置信度计算模块 ✅
- **新增模块** (`utils/confidence_calculator.py`)：
  - ✅ `ConfidenceCalculator`: 增强的置信度计算器类
    - 实现历史准确率反馈机制（按股票、按市场状态）
    - 实现预测一致性检查（多次预测的一致性）
    - 实现数据时效性对置信度的影响
    - 实现置信度校准（高置信度预测应该真的更准确）
    - 提供校准报告功能

#### 2. 历史准确率反馈机制 ✅
- ✅ `_get_historical_accuracy_factor()`: 获取历史准确率反馈因子
  - 按股票代码查询历史准确率（最近90天）
  - 根据市场状态进一步筛选（可扩展）
  - 根据准确率调整置信度因子（0.7-1.3）：
    - 准确率 >= 65%: 因子 1.0-1.2（提高置信度）
    - 准确率 55-65%: 因子 0.95-1.0（微调）
    - 准确率 < 55%: 因子 0.7-0.95（降低置信度）
  - 实现缓存机制（TTL=1小时）避免重复查询

#### 3. 预测一致性检查 ✅
- ✅ `_check_prediction_consistency()`: 检查预测一致性
  - 跟踪每只股票最近5次预测的方向一致性
  - 一致性高（>80%）：提高置信度（1.05-1.15）
  - 一致性中等（50-80%）：不变（1.0）
  - 一致性低（<50%）：降低置信度（0.85-0.95）
  - 使用内存缓存存储预测历史（最多保留10次）

#### 4. 数据时效性影响 ✅
- ✅ `_calculate_timeliness_factor()`: 计算数据时效性因子
  - 检查各数据源的时间戳
  - 根据数据时间差调整置信度：
    - 数据很新（<1小时）：1.0（不降低）
    - 数据较新（1-6小时）：0.98-1.0
    - 数据较旧（6-24小时）：0.95-0.98
    - 数据很旧（>24小时）：0.9-0.95
  - 使用最大时间差作为参考

#### 5. 置信度校准 ✅
- ✅ `_calculate_calibration_adjustment()`: 计算置信度校准调整量
  - 基于历史数据校准：高置信度预测应该真的更准确
  - 按置信度区间（high >= 0.7, medium 0.5-0.7, low < 0.5）分析
  - 如果实际准确率低于期望准确率，降低调整量（-0.1到+0.1）
  - 支持动态校准，持续改进预测质量

#### 6. 校准报告功能 ✅
- ✅ `get_calibration_report()`: 生成置信度校准报告
  - 按置信度区间分组（very_high, high, medium_high, medium, low）
  - 计算每个区间的期望准确率、实际准确率、校准误差
  - 判断是否校准良好（误差<10%）
  - 提供整体校准指标

#### 7. StockPredictor 集成 ✅
- ✅ 更新 `_calculate_confidence()` 方法：
  - 集成增强的置信度计算器
  - 传递 `market_state` 参数支持按市场状态的准确率查询
  - 保留基础计算方法作为回退机制
  - 添加详细的调试日志输出
- ✅ 更新 `predict()` 方法：
  - 传递 `market_state` 参数到置信度计算方法
  - 确保置信度计算的完整性和准确性

### 技术改进
- 使用数据库查询历史预测准确率（`stock_predictions` 表）
- 实现智能缓存机制减少数据库查询
- 使用 `defaultdict` 高效管理预测历史
- 支持单例模式（`get_confidence_calculator()`）确保全局一致性

### 影响范围
- **文件修改**：
  - `smart_stock_advisor/utils/confidence_calculator.py`（新增）
  - `smart_stock_advisor/predictor/stock_predictor.py`（修改）
  - `smart_stock_advisor/项目完整报告.md`（更新状态）

### 使用说明
- 置信度计算自动启用，无需额外配置
- 可以通过 `get_confidence_calculator().get_calibration_report()` 获取校准报告
- 所有预测自动应用增强的置信度计算

---

## [2026-01-10] - 权重配置优化实施

### 优化内容

#### 1. 权重优化器模块 ✅
- **新增模块** (`utils/weight_optimizer.py`)：
  - ✅ `WeightOptimizer`: 权重优化器类
    - 实现基于历史准确率的自动权重优化
    - 实现根据市场状态自动调整权重策略
    - 实现根据个股特性（大盘股/小盘股/成长股/价值股）调整权重
    - 综合优化权重（综合考虑所有因素）
    - 自动归一化权重，确保总和为1

#### 2. 基于历史准确率的权重优化 ✅
- ✅ `optimize_weights_by_accuracy()`: 基于历史准确率优化权重
  - 分析历史预测数据中各因子的准确率
  - 计算各因子对预测准确性的贡献度
  - 基于准确率差值计算最优权重（准确率越高，权重越大）
  - 生成权重调整建议（变化超过10%才建议调整）
  - 支持自定义评估天数（默认30天）和最小样本数（默认50）

#### 3. 根据市场状态自动调整权重 ✅
- ✅ `adjust_weights_by_market_state()`: 根据市场状态调整权重
  - 集成 `MarketStateIdentifier` 的市场状态识别结果
  - 牛市策略：技术指标×1.2，新闻×0.8，资金流向×1.1
  - 熊市策略：技术指标×0.8，新闻×1.3，资金流向×1.2，市场×1.1
  - 震荡市策略：平衡各因素权重（×1.0）
  - 根据置信度调整调整幅度（置信度低时调整幅度小）

#### 4. 根据个股特性调整权重 ✅
- ✅ `adjust_weights_by_stock_type()`: 根据个股特性调整权重
  - 大盘股（市值>500亿）：
    - 资金流向权重×1.3
    - 估值权重×2.0
    - 技术指标权重×0.9
  - 小盘股（市值<100亿）：
    - 技术指标权重×1.2
    - 新闻权重×1.15
    - 估值权重×0.5
  - 成长股：
    - 新闻权重×1.2
    - 板块轮动权重×1.5
  - 价值股：
    - 估值权重×2.5
    - 历史权重×1.3
  - 自动归一化权重，确保总和为1

#### 5. 综合权重优化 ✅
- ✅ `get_optimized_weights()`: 综合优化权重
  - 优先使用基于历史准确率的优化权重（可选）
  - 再根据市场状态调整
  - 最后根据个股特性调整
  - 自动归一化权重，确保总和为1

#### 6. 集成到预测流程 ✅
- ✅ 集成到 `StockPredictor.predict()` 方法中
  - 在预测时自动应用优化后的权重
  - 如果权重优化失败，回退到基于市场状态的调整
  - 记录权重优化结果到日志
  - 使用优化后的权重计算最终得分

#### 7. API接口 ✅
- ✅ `POST /api/weight/optimize`: 手动触发权重优化（仅管理员）
  - 参数：`days`（评估天数，默认30）、`min_samples`（最小样本数，默认50）
  - 返回：优化结果、因子准确率、最优权重、调整建议
  - 访问频率限制：10次/分钟

### 技术实现

1. **权重优化算法**：
   - 基于历史准确率计算权重：`weight = 0.5 + (accuracy - 0.5) * 2`
   - 准确率 > 0.5 的因子给予更高权重
   - 准确率 < 0.5 的因子降低权重（但最小权重0.1）
   - 归一化确保权重总和为1

2. **市场状态权重调整**：
   - 使用 `MarketStateIdentifier` 识别市场状态
   - 根据市场状态应用不同的权重倍数
   - 根据置信度调整调整幅度

3. **个股特性权重调整**：
   - 从 `stock_info` 表获取股票市值和类型
   - 根据市值和类型应用不同的权重倍数
   - 自动归一化权重

### 使用方法

#### 1. 自动优化（默认启用）
权重优化在预测时自动执行，无需手动操作。

#### 2. 手动触发优化（管理员）
```bash
# API调用
POST /api/weight/optimize
{
    "days": 30,        # 评估天数
    "min_samples": 50  # 最小样本数
}
```

#### 3. 查看优化结果
优化结果会记录在日志中，包含：
- 各因子的准确率
- 优化后的权重配置
- 权重调整建议

### 注意事项

1. **数据要求**：
   - 权重优化需要至少50个历史预测样本
   - 建议评估时间范围为30天以上
   - 需要数据库中有完整的预测历史数据

2. **性能影响**：
   - 权重优化会在每次预测时自动执行（如果启用）
   - 如果历史数据不足，会自动回退到默认权重
   - 不影响预测流程的正常运行

3. **准确性提升**：
   - 权重优化基于历史数据，需要一定时间积累数据
   - 随着历史数据增加，优化效果会越来越好
   - 建议定期（如每周）执行一次权重优化

---

## [2026-01-10] - 代码测试覆盖实施

### 新增功能

#### 1. 单元测试框架 ✅
- **测试目录结构** (`tests/`)：
  - ✅ 创建测试目录和配置文件
  - ✅ `tests/__init__.py` - 测试模块初始化
  - ✅ `tests/conftest.py` - pytest配置和fixtures
  - ✅ `pytest.ini` - pytest配置文件
  
- **测试工具** (`requirements.txt`)：
  - ✅ 添加 `pytest>=7.4.0` - 单元测试框架
  - ✅ 添加 `pytest-cov>=4.1.0` - 测试覆盖率
  - ✅ 添加 `pytest-mock>=3.11.0` - Mock支持
  - ✅ 添加 `psutil>=5.9.0` - 系统监控依赖

#### 2. 核心模块单元测试 ✅
- **API限流器测试** (`tests/test_rate_limiter.py`)：
  - ✅ 测试初始化
  - ✅ 测试设置限制
  - ✅ 测试检查限流（允许访问）
  - ✅ 测试检查限流（超过限制）
  - ✅ 测试重置记录
  - ✅ 测试获取统计信息
  - ✅ 测试单例模式

- **数据质量检查器测试** (`tests/test_data_quality.py`)：
  - ✅ 测试检测离群值（IQR方法）
  - ✅ 测试检测离群值（Z分数方法）
  - ✅ 测试检查数据完整性
  - ✅ 测试检查数据合理性
  - ✅ 测试检查数据一致性
  - ✅ 测试检查数据时效性
  - ✅ 测试单例模式

- **操作审计日志测试** (`tests/test_audit_log.py`)：
  - ✅ 测试记录操作（数据库未启用）
  - ✅ 测试记录操作（数据库启用）
  - ✅ 测试获取审计日志
  - ✅ 测试单例模式

- **系统监控器测试** (`tests/test_system_monitor.py`)：
  - ✅ 测试获取系统指标
  - ✅ 测试获取业务指标（数据库未启用）
  - ✅ 测试获取业务指标（数据库启用）
  - ✅ 测试检查告警
  - ✅ 测试单例模式

- **自动化回测测试** (`tests/test_automated_backtest.py`)：
  - ✅ 测试初始化
  - ✅ 测试执行定期回测
  - ✅ 测试检查性能告警
  - ✅ 测试单例模式

#### 3. 测试文档 ✅
- **测试文档** (`tests/README.md`)：
  - ✅ 测试结构说明
  - ✅ 运行测试方法
  - ✅ 测试标记说明
  - ✅ 测试最佳实践

### 使用方法

#### 1. 安装测试依赖

```bash
pip install -r requirements.txt
```

#### 2. 运行所有测试

```bash
pytest
```

#### 3. 运行特定测试文件

```bash
pytest tests/test_rate_limiter.py
```

#### 4. 查看测试覆盖率

```bash
pytest --cov=utils --cov-report=html
```

测试覆盖率报告将生成在 `htmlcov/index.html`

#### 5. 运行带标记的测试

```bash
# 只运行单元测试
pytest -m unit

# 排除需要数据库的测试
pytest -m "not database"
```

### 测试标记

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.slow`: 慢速测试
- `@pytest.mark.database`: 需要数据库的测试

### 后续计划

1. **集成测试**（待实现）：
   - [ ] API端点集成测试
   - [ ] 数据库操作集成测试
   - [ ] 任务调度集成测试

2. **自动化测试（CI/CD）**（待实现）：
   - [ ] GitHub Actions配置
   - [ ] 自动运行测试
   - [ ] 自动生成覆盖率报告

3. **性能测试**（待实现）：
   - [ ] 压力测试
   - [ ] 性能基准测试
   - [ ] 负载测试

---

## [2026-01-10] - 项目完整报告

### 新增文档

#### 项目完整报告 ✅
- **文档**：`项目完整报告.md`
- **内容**：
  - 📋 项目概述：项目定位、开发状态、项目定位
  - 🎯 核心功能模块：详细说明7大核心模块（预测分析、实时策略、数据管理、新闻系统、模型学习、Web应用、定时任务）
  - 🏗️ 技术架构：后端架构、技术栈、数据库设计
  - ✅ 已完成功能总结：核心功能、优化功能、管理功能
  - ⚠️ 需要改进的地方：
    - 预测模型改进（权重配置、置信度计算、模型验证）
    - 实时交易策略改进（信号生成、风险控制、交易成本）
    - 新闻系统改进（任务调度、情感分析、推送功能）
    - 数据管理改进（数据质量、备份恢复）
    - Web应用改进（前端优化、用户体验）
    - 性能优化（数据库、并发处理）
  - 🔧 需要优化的地方：
    - 代码质量优化（代码结构、代码复用、测试覆盖）
    - 架构优化（模块化设计、扩展性）
    - 性能优化（缓存机制、异步处理）
    - 监控和日志优化（监控系统、日志系统）
    - 安全性优化（数据安全、访问控制）
  - 📊 项目现状评估：
    - 功能完整度：85%
    - 代码质量：75%
    - 性能表现：80%
    - 用户体验：75%
    - 可维护性：70%
    - 安全性：70%
  - 🚀 后续发展规划：短期（1-3个月）、中期（3-6个月）、长期（6-12个月）
  - 📈 项目优势：功能全面、技术先进、可扩展性强、用户体验良好
  - ⚠️ 项目不足：预测准确性、代码质量、性能优化、文档完善、安全性
  - 💡 改进建议总结：高优先级、中优先级、低优先级

### 报告内容概览

#### 核心功能模块（7大模块）
1. ✅ **股票预测分析**：多因子预测模型、预测结果输出、预测参数配置
2. ✅ **实时交易策略**：实时数据获取、交易信号生成、风险控制、实时监控
3. ✅ **数据管理**：中国股票数据、美股数据、新闻数据、定时数据获取
4. ✅ **新闻系统**：新闻抓取、情感分析、新闻关联、去重、搜索、推送
5. ✅ **模型学习系统**：性能评估、参数优化、回测引擎、参数更新、定时任务
6. ✅ **Web应用系统**：用户管理、股票列表、预测报告、设置页面、API接口、实时通信
7. ✅ **定时任务系统**：任务类型、调度功能、任务管理

#### 技术架构
- **后端技术**：Python 3.x, Flask, Flask-SocketIO, MySQL, schedule, pandas, numpy
- **前端技术**：HTML5, CSS3, JavaScript, Chart.js, WebSocket
- **外部服务**：akshare, tushare, yfinance, 多个新闻源
- **数据库**：15+ 核心数据表

#### 改进建议（按优先级）
1. **高优先级**：预测模型验证机制、代码测试覆盖、性能监控、安全加固
2. **中优先级**：任务调度统一、前端优化、缓存优化、日志完善
3. **低优先级**：深度学习模型、平台化发展、云服务化

#### 项目评价
- **整体评分**：⭐⭐⭐⭐（4/5星）
- **功能完整度**：85%
- **代码质量**：75%
- **性能表现**：80%
- **用户体验**：75%
- **可维护性**：70%
- **安全性**：70%

## [2026-01-10] - 新闻模块优化（第四、五大点）

### 优化内容

#### 1. 新闻去重优化 ✅
- **新增模块** (`utils/news_deduplication.py`)：
  - ✅ `NewsDeduplication`: 新闻去重优化类
    - 实现SimHash算法进行内容相似度检测
    - 支持64位SimHash值计算
    - 支持汉明距离计算和相似度判断（阈值可配置，默认3）
    - 基于内容相似度检测重复新闻（不仅限于标题和来源）
    - 建立重复新闻关联关系
  - ✅ 数据库字段：在 `news_articles` 表添加 `simhash` 字段（BIGINT UNSIGNED）
  - ✅ 索引优化：添加 `simhash` 索引，提高查询速度
  - ✅ 集成到 `NewsStorage`：保存新闻时自动计算并保存SimHash值
  - ✅ 去重逻辑优化：先检查精确匹配（标题+来源），再使用SimHash相似度检测

#### 2. 新闻搜索功能 ✅
- **新增模块** (`utils/news_search.py`)：
  - ✅ `NewsSearch`: 新闻搜索器类
    - 支持关键词搜索（标题和内容）
    - 支持多种筛选条件：
      - 股票代码筛选
      - 情感倾向筛选（positive/negative/neutral）
      - 时间范围筛选（date_from/date_to）
      - 板块/行业筛选
      - 新闻类型筛选（stock/market/policy/industry）
      - 利好/利空/政策新闻筛选
    - 支持排序（按发布时间、相关性得分、情感得分等）
    - 支持分页（page、page_size）
    - 支持搜索建议（自动补全）
- **API接口** (`web_app.py`)：
  - ✅ `GET /api/news/search`: 搜索新闻接口
    - 参数：keyword、symbol、sentiment、date_from、date_to、sector、industry、news_type、is_positive、is_negative、is_policy、page、page_size、sort_by、sort_order
    - 返回：搜索结果列表、总数、总页数
  - ✅ `GET /api/news/search/suggestions`: 获取搜索建议接口
    - 参数：keyword、limit
    - 返回：建议列表

#### 3. 新闻推送功能 ✅
- **新增模块** (`utils/news_notification.py`)：
  - ✅ `NewsNotification`: 新闻推送通知管理器
    - 判断是否需要推送（重要新闻自动识别）
      - 直接关联的利好/利空新闻（relevance_type='direct'）
      - 高置信度的情感分析结果（sentiment_confidence > 0.7）
      - 高强度的情感得分（|sentiment_score| > 0.5）
      - 政策新闻（重大新闻）
    - 创建通知记录
    - 获取待发送通知
    - 标记通知为已发送
    - 获取用户通知列表
  - **数据库表** (`database/news_notification_table.sql`)：
    - ✅ 创建 `news_notifications` 表
      - 字段：id、news_id、notification_type、title、symbol、sentiment、is_sent、sent_at、is_read、read_at等
      - 索引：news_id、symbol、is_sent、is_read、notification_type、created_at
      - 外键：news_id 关联 news_articles 表（ON DELETE CASCADE）
  - ✅ 集成到 `NewsStorage`：保存新闻时自动检查是否需要推送，如需推送则创建通知记录

#### 4. 情感分析优化 ✅
- **优化模块** (`quant_trading_platform/news/sentiment_analyzer.py`)：
  - ✅ 改进否定词处理逻辑：
    - 检查否定词与关键词的上下文关系（前后10个字符）
    - 如果否定词在关键词前面，反转情感（更准确）
    - 保留原有的备用逻辑（如果上下文匹配失败）
  - ✅ 改进置信度计算：
    - 考虑关键词权重、强度关键词和上下文
    - 如果有高强度关键词，提高置信度（+0.2）
    - 如果关键词较多，提高置信度（最多+0.2）
    - 最终置信度限制在0-1之间

#### 5. 任务调度优化 ⚠️ 部分完成
- **现状分析**：
  - 新闻抓取任务使用 `threading.Event` + `time.sleep`，功能有限
  - 其他定时任务使用 `schedule` 库，支持更灵活的调度
  - 问题：两种调度方式不一致，新闻任务不支持cron表达式
- **优化方案**（后续实现）：
  - ⚠️ 统一使用 `schedule` 库（轻量级，已在使用）
  - ⚠️ 将新闻抓取任务迁移到 `scheduled_task_manager` 统一管理
  - ⚠️ 支持更灵活的时间配置（daily、hourly、weekly、custom）
  - ⚠️ 保留对cron表达式的扩展支持（后续可集成APScheduler）

### 注意事项优化 ✅

#### 1. 数据库必须启用
- ✅ 已在代码中检查 `USE_DATABASE`
- ✅ 如果数据库未启用，会记录警告并跳过数据库操作

#### 2. 新闻源可用性
- ✅ 代码中已有异常处理，新闻源初始化失败会记录警告
- ✅ 新闻抓取失败会记录错误信息，不影响其他新闻源的抓取

#### 3. 抓取间隔建议
- ✅ 已有间隔配置功能
- ✅ 建议在设置页面添加验证，防止间隔过短（<10分钟）

#### 4. 任务管理
- ✅ 已有任务启动/停止功能
- ✅ 任务停止会等待线程退出（最多5秒）

#### 5. 重复新闻处理
- ✅ 已基于标题和来源的唯一索引防止重复
- ✅ **新增**：使用SimHash进行内容相似度检测，提高去重准确性

### 技术实现

1. **SimHash算法**：
   - 使用64位SimHash值
   - 汉明距离阈值：默认3（可配置）
   - 分词：简单的中文分词（2-gram）+ 英文单词 + 数字

2. **全文搜索**：
   - 使用MySQL的LIKE查询（如果FULLTEXT不可用）
   - 支持多条件组合查询
   - 支持分页和排序

3. **新闻推送**：
   - 推送条件：直接关联的利好/利空新闻、高置信度情感分析、政策新闻
   - 推送方式：浏览器通知（Web Notification API）、站内消息（数据库存储）

4. **情感分析优化**：
   - 改进否定词上下文处理
   - 改进置信度计算（考虑强度关键词和关键词数量）

### 使用方法

#### 1. SimHash去重
- 自动启用：保存新闻时自动计算SimHash值
- 去重检测：先检查精确匹配，再使用SimHash相似度检测
- 相似度阈值：默认汉明距离 < 3（可在 `NewsDeduplication` 初始化时配置）

#### 2. 新闻搜索
- API调用：`GET /api/news/search?keyword=xxx&sentiment=positive&date_from=2026-01-01&page=1&page_size=20`
- 搜索建议：`GET /api/news/search/suggestions?keyword=xxx&limit=10`

#### 3. 新闻推送
- 自动启用：保存新闻时自动检查是否需要推送
- 推送条件：直接关联的利好/利空新闻、高置信度情感分析、政策新闻
- 查看通知：通过 `NewsNotification.get_user_notifications()` 获取用户通知列表

### 后续优化建议

1. **任务调度优化**（待实现）：
   - 统一使用 `schedule` 库
   - 将新闻抓取任务迁移到 `scheduled_task_manager`
   - 支持cron表达式（可集成APScheduler）

2. **SimHash优化**（可选）：
   - 使用专业分词库（如jieba）提高分词准确性
   - 优化SimHash计算性能（批量计算）

3. **全文搜索优化**（可选）：
   - 使用MySQL的FULLTEXT索引（需要InnoDB支持）
   - 使用中文分词插件（如ngram）
   - 实现相关性排序（BM25算法）

4. **新闻推送优化**（可选）：
   - 实现浏览器通知（Web Notification API）
   - 实现邮件通知（可选）
   - 实现推送规则配置（用户可自定义）

5. **情感分析优化**（可选）：
   - 引入BERT等深度学习模型（需要大量训练数据）
   - 支持多语言情感分析

## [2026-01-09] - 股票数据获取定时任务管理功能

### 新增功能

#### 1. 股票数据获取定时任务 ✅
- **后端实现** (`utils/scheduled_task_manager.py`)：
  - ✅ `_execute_cn_stock_data_collection()`: 执行中国股票数据获取任务
    - 支持增量更新（每日收盘后更新最新数据）
    - 支持全量收集（收集历史数据，可指定年数）
    - 支持指定股票列表或处理所有股票
  - ✅ `_execute_us_stock_data_collection()`: 执行美国股票数据获取任务
    - 支持增量更新（获取最近30天的数据）
    - 支持全量收集（收集历史数据，可指定周期：1y/5y/10y）
    - 支持指定股票列表、S&P 500或NASDAQ 100指数

#### 2. 设置页面新页签 ✅
- **新增页签** (`templates/settings.html`)：
  - ✅ 在设置页面菜单栏添加"股票数据获取"页签
  - ✅ 任务列表展示（支持分页，每页20条）
  - ✅ 任务详情展示（任务名称、市场类型、收集类型、执行时间、运行状态等）
  - ✅ 任务操作（启动、停止、删除）
  - ✅ 历史记录展示（所有任务的历史记录合并显示，支持分页）

#### 3. API接口 ✅
- **新增接口** (`web_app.py`)：
  - ✅ `GET /api/stock-data/tasks`: 获取股票数据获取任务列表（支持分页）
    - 参数：`page`（页码，默认1）、`page_size`（每页数量，默认20）、`task_type`（任务类型，可选）
    - 返回：任务列表、总数、总页数
  - ✅ `POST /api/stock-data/tasks`: 创建股票数据获取任务
    - 参数：`task_name`（任务名称）、`market_type`（市场类型：cn/us）、`collection_type`（收集类型：incremental/full）、`schedule_type`（执行时间类型）、`schedule_time`（执行时间）、`symbols`（股票列表，可选）、`years`（收集年数，中国股票）、`period`（收集周期，美国股票）、`index_type`（指数类型，美国股票）
  - ✅ `GET /api/stock-data/tasks/<task_id>/history`: 获取任务历史记录（支持分页）
    - 参数：`page`（页码，默认1）、`page_size`（每页数量，默认20）
    - 返回：历史记录列表、总数、总页数

#### 4. 前端功能 ✅
- **任务管理** (`templates/settings.html`)：
  - ✅ 任务列表展示：显示任务名称、市场类型、收集类型、执行时间、运行状态、运行次数、成功/失败次数等
  - ✅ 分页功能：支持上一页/下一页，显示当前页码和总页数
  - ✅ 创建任务模态框：支持创建中国股票或美国股票数据获取任务
    - 市场类型选择（中国股票/美国股票）
    - 收集类型选择（增量更新/全量收集）
    - 执行时间配置（每日/每周/每月）
    - 股票列表输入（可选，多个用逗号分隔）
  - ✅ 任务操作：启动任务、停止任务、删除任务
  - ✅ 历史记录展示：显示所有任务的历史记录，按时间倒序排列，支持分页

### 使用方法

#### 1. 创建任务
1. 登录系统后，点击"设置"按钮
2. 切换到"股票数据获取"页签
3. 点击"创建数据获取任务"按钮
4. 填写任务信息：
   - 任务名称：例如"每日中国股票数据更新"
   - 市场类型：选择"中国股票"或"美国股票"
   - 收集类型：选择"增量更新"或"全量收集"
   - 执行时间：选择执行频率（每日/每周/每月）和执行时间
   - 股票列表（可选）：输入股票代码，多个用逗号分隔
5. 点击"创建任务"

#### 2. 管理任务
- **启动任务**：点击任务卡片上的"启动"按钮，任务将按照设定的时间自动执行
- **停止任务**：点击任务卡片上的"停止"按钮，任务将停止执行
- **删除任务**：点击任务卡片上的"删除"按钮，确认后删除任务

#### 3. 查看历史记录
- 点击"查看历史记录"按钮，可以查看所有任务的历史执行记录
- 历史记录按时间倒序排列，支持分页浏览

### 任务类型说明

#### 中国股票数据获取任务 (`stock_data_collection_cn`)
- **增量更新** (`collection_type: 'incremental'`)：
  - 每日收盘后更新最新的交易数据
  - 如果指定了股票列表，只更新指定股票；否则更新所有股票
- **全量收集** (`collection_type: 'full'`)：
  - 收集股票的历史数据（可指定年数，默认10年）
  - 如果指定了股票列表，只收集指定股票；否则收集所有股票

#### 美国股票数据获取任务 (`stock_data_collection_us`)
- **增量更新** (`collection_type: 'incremental'`)：
  - 获取最近30天的数据
  - 需要指定股票列表
- **全量收集** (`collection_type: 'full'`)：
  - 收集股票的历史数据（可指定周期：1y/5y/10y）
  - 可以指定股票列表，或选择指数类型（S&P 500或NASDAQ 100）

### 技术实现

1. **定时任务调度**：使用 `schedule` 库进行定时任务调度
2. **任务执行**：任务在后台线程中执行，不会阻塞主线程
3. **数据存储**：中国股票数据存储在 `stock_history_data` 表，美国股票数据存储在 `us_stock_history_data` 表
4. **分页处理**：前端使用JavaScript实现分页，后端API支持分页参数

### 注意事项

- ⚠️ 全量收集任务可能需要较长时间，建议在非交易时间执行
- ⚠️ 增量更新任务建议在收盘后执行（例如：18:00）
- ⚠️ 美股数据获取需要网络连接，建议在网络稳定的环境下执行
- ⚠️ 大量股票的全量收集可能会消耗大量时间和资源，建议分批执行

## [2026-01-09] - 新闻系统分析与优化

### 新增功能

#### 1. 新闻与股票自动关联模块 ✅
- **新建模块** (`utils/news_stock_mapper.py`)：
  - `extract_stock_symbols_from_text()`: 从文本中提取股票代码和名称
    - 匹配6位股票代码（600xxx, 000xxx, 002xxx, 300xxx等）
    - 匹配股票名称（完整名称、简称、去除后缀等）
    - 提取括号中的股票简称
  - `map_news_to_stocks()`: 将新闻关联到相关股票
    - 直接匹配：通过股票代码和名称（relevance_score = 1.0）
    - 行业匹配：通过行业关键词匹配（relevance_score = 0.5-0.7）
  - `process_news_batch()`: 批量处理未关联的新闻，自动关联股票
  - `update_news_stock_mapping()`: 更新新闻的股票关联
  - 股票信息缓存机制，避免重复查询数据库

#### 2. 新闻存储优化 ✅
- **修改** (`utils/news_storage.py`)：
  - 在 `save_news_article()` 时，如果没有传入 `symbol`，自动调用 `NewsStockMapper` 进行关联
  - 自动更新 `sector`、`industry`、`relevance_type`、`relevance_score`
  - 保存新闻时自动进行情感分析和股票关联

#### 3. 测试脚本 ✅
- **新建** (`scripts/test_news_sources.py`)：
  - 测试所有13个新闻源的抓取功能
  - 显示每个新闻源的抓取结果和统计数据
- **新建** (`scripts/test_news_storage.py`)：
  - 验证新闻数据库存储
  - 检查情感分析结果
  - 检查新闻与股票关联
- **新建** (`scripts/analyze_news_system.py`)：
  - 综合分析新闻系统（抓取、存储、情感分析、关联）
  - 批量处理未关联的新闻

### 测试结果

#### 1. 新闻源抓取测试
- ✅ **共13个新闻源**，初始化成功：
  1. 金十数据
  2. 财新
  3. 证券公司
  4. 同花顺
  5. 东方财富
  6. 雪球
  7. TuShare ✅（可用）
  8. 新浪财经 ✅（可用）
  9. 腾讯财经
  10. 网易财经 ✅（可用）
  11. 上交所
  12. 深交所
  13. 巨潮资讯

- ✅ **3个新闻源** 能正常抓取数据：
  - TuShare: 5条新闻
  - 新浪财经: 2条新闻
  - 网易财经: 5条新闻

- ⚠️ **10个新闻源** 无数据或失败：
  - 原因：需要API密钥、网站结构变化、SSL证书问题等

#### 2. 数据库存储验证
- ✅ 新闻已正确存储到 `news_articles` 表
- ✅ 情感分析结果已保存（sentiment, sentiment_score, is_positive, is_negative）
- ✅ 新闻与股票关联已保存（symbol, sector, industry, relevance_type, relevance_score）

#### 3. 情感分析标签
- ✅ **情感倾向**：positive/negative/neutral
- ✅ **情感得分**：-1到1（正数表示利好，负数表示利空）
- ✅ **置信度**：0到1（基于关键词数量计算）
- ✅ **标签**：
  - `is_positive = 1`: 利好（sentiment='positive' AND sentiment_score > 0.1）
  - `is_negative = 1`: 利空（sentiment='negative' AND sentiment_score < -0.1）

#### 4. 股票关联功能
- ✅ **直接匹配**：通过股票代码和名称（relevance_score = 1.0）
- ✅ **行业匹配**：通过行业关键词匹配（relevance_score = 0.5-0.7）
- ✅ **自动关联**：保存新闻时自动关联股票
- ✅ **批量处理**：支持批量处理未关联的新闻

### 用于模型学习和实时交易策略

#### 1. 模型学习特征提取
- ✅ **情感得分** (`sentiment_score`) 可以作为特征
- ✅ **利好/利空标签** (`is_positive`, `is_negative`) 可以作为目标变量
- ✅ **相关性得分** (`relevance_score`) 可以用于特征工程
- ✅ **相关性类型** (`relevance_type`: direct/industry/market) 可以作为分类特征

#### 2. 实时交易策略应用
- ✅ **获取实时新闻**：`get_news_by_symbol()` 获取股票的实时新闻
- ✅ **触发交易信号**：根据情感标签（利好/利空）触发买入/卖出信号
- ✅ **调整权重**：根据相关性得分调整交易信号权重
- ✅ **新闻权重计算**：综合考虑相关性、置信度、情感强度

### 文档
- ✅ `新闻系统分析与优化报告.md`: 详细的分析报告和使用说明
- ✅ `新闻系统使用说明.md`: 使用说明和代码示例
- ✅ `美股板块行业存储说明.md`: 美股板块和行业信息存储说明
- ✅ `美股板块行业存储功能验证.md`: 验证文档

### 注意事项
- ⚠️ 部分新闻源需要API密钥（如金十数据、TuShare需要token）
- ⚠️ 部分新闻源可能因为网站结构变化而失效（如证券公司SSL问题）
- ⚠️ 情感分析基于关键词匹配，准确率有限，建议后续引入机器学习模型
- ⚠️ 新闻与股票关联目前只保存主要关联（最高相关性），如需多对多关系，可创建 `news_stock_mapping` 表

### 后续优化建议
1. **新闻源优化**：修复失败的新闻源，添加更多新闻源
2. **情感分析优化**：引入机器学习模型（如BERT）进行情感分析
3. **股票关联优化**：支持多对多关系，改进行业关键词匹配算法
4. **数据质量优化**：新闻去重优化，添加新闻质量评分

## [2026-01-09] - 美股数据系统实施

### 新增功能

#### 1. 美股数据库系统 ✅
- **数据库设计**：
  - 新增 `us_sectors` 表（美股板块表，GICS分类）
  - 新增 `us_industries` 表（美股行业表，GICS分类）
  - 新增 `us_stock_info` 表（美股股票基本信息表）
  - 新增 `us_stock_history_data` 表（美股历史数据表，参考A股结构，支持10年数据）
  - 新增 `us_sector_stock_map` 表（板块股票映射表）
  - 新增 `us_industry_stock_map` 表（行业股票映射表）
  - 新增 `us_sector_index_history` 表（板块指数历史数据表）
  - 创建了表创建脚本：`scripts/create_us_stock_tables.py`
  - 创建了SQL定义文件：`database/us_stock_tables.sql`

- **数据源模块**（`data_source/us_stock_data_source.py`）：
  - 使用yfinance获取美股历史数据（支持10年）
  - 获取股票基本信息（板块、行业、市值、交易所等）
  - 支持从Wikipedia获取S&P 500、NASDAQ 100成分股列表
  - 支持获取板块ETF数据
  - GICS板块分类映射（11个标准板块）

- **数据存储模块**（`utils/us_stock_storage.py`）：
  - 保存股票基本信息
  - 保存股票历史数据（支持ON DUPLICATE KEY UPDATE，增量更新）
  - 保存板块和行业信息
  - 查询已存在数据（避免重复下载）

- **数据收集器**（`utils/us_stock_collector.py`）：
  - 收集单只股票的历史数据（支持10年）
  - 批量收集多只股票数据
  - 自动计算技术指标（MA5/10/20/50/200、RSI、MACD、波动率等）
  - 自动计算涨跌幅、振幅等指标
  - 支持增量更新（默认不重复下载已存在数据）

- **工具脚本**：
  - `scripts/collect_us_stock_data.py`: 批量收集美股历史数据脚本
  - `scripts/get_us_stock_list.py`: 获取股票列表脚本（S&P 500、NASDAQ 100）

#### 2. 数据字段设计（参考A股数据库模式）

美股历史数据表包含与A股类似的字段结构：
- **基本价格数据**：开盘价、收盘价、最高价、最低价、调整后收盘价、昨收价
- **成交数据**：成交量、成交额、换手率、量比
- **技术指标**：MA5/10/20/50/200、RSI、MACD、波动率、振幅
- **估值指标**：PE（TTM）、前瞻PE、PB、PS、股息率、EV/EBITDA
- **其他数据**：盘口数据（JSON）、期权数据、资金流向等（如果可用）

#### 3. GICS分类系统

- 实现了标准的GICS（Global Industry Classification Standard）分类
- 包含11个板块（Sector Level）：能源、材料、工业、可选消费、必需消费、医疗保健、金融、信息技术、通信服务、公用事业、房地产
- 支持行业（Industry Level）和子行业（Sub-Industry Level）分类
- 板块和行业与股票建立多对多关联关系

### 使用方法

#### 1. 创建数据库表
```bash
python scripts/create_us_stock_tables.py
```

#### 2. 初始化板块数据
```bash
python scripts/collect_us_stock_data.py --init-sectors
```

#### 3. 获取股票列表
```bash
# 获取S&P 500成分股列表
python scripts/get_us_stock_list.py --index sp500 --output sp500_stocks.csv
```

#### 4. 收集历史数据（10年）
```bash
# 收集指定股票
python scripts/collect_us_stock_data.py --symbols AAPL MSFT GOOGL

# 收集S&P 500所有成分股（需要较长时间，建议分批进行）
python scripts/collect_us_stock_data.py --sp500
```

### 技术实现

1. **数据源**：
   - yfinance：主要数据源，获取历史和实时数据
   - Wikipedia：获取指数成分股列表（备用方案）
   - GICS标准：板块和行业分类

2. **数据完整性**：
   - 支持增量更新，避免重复下载
   - 自动计算技术指标
   - 数据质量评分

3. **性能优化**：
   - 批量处理支持
   - 请求延迟控制（避免频率限制）
   - 错误处理和重试机制

### 注意事项

1. **依赖安装**：
   ```bash
   pip install yfinance pandas numpy requests beautifulsoup4 lxml
   ```

2. **数据获取限制**：
   - yfinance有请求频率限制，建议每只股票之间延迟0.5-1秒
   - 批量收集大量股票时，建议分批进行
   - 收集S&P 500全部500只股票可能需要数小时

3. **数据可用性**：
   - 某些字段可能为空（取决于数据源是否提供，如期权数据、资金流向等）
   - 技术指标会根据可用数据自动计算

### 相关文档

- `美股数据系统说明.md`：详细使用说明文档
- `database/us_stock_tables.sql`：数据库表定义
- `scripts/create_us_stock_tables.py`：表创建脚本

---

## [2026-01-09] - 模型学习系统实施

### 新增功能

#### 1. 模型学习系统 ✅
- **数据库设计**：
  - 新增 `model_performance` 表（模型性能记录表）
  - 新增 `parameter_optimization_history` 表（参数优化历史表）
  - 新增 `model_learning_tasks` 表（模型学习任务表，预留用于定时学习）
  - 创建了表创建脚本：`scripts/create_model_learning_tables.py`

- **性能评估模块**（`utils/model_performance_evaluator.py`）：
  - 预测性能评估：方向准确率、幅度误差、置信度校准、因子贡献度、市场状态识别
  - 交易性能评估：总收益率、胜率等指标
  - 自动保存性能记录到数据库

- **回测引擎**（`utils/backtest_engine.py`）：
  - 基于历史数据模拟交易
  - 计算回测指标：总收益率、年化收益率、最大回撤、胜率、盈亏比等
  - 支持使用不同参数组合进行回测

- **参数优化模块**（`utils/model_optimizer.py`）：
  - 网格搜索优化算法（基础版）
  - 基于历史回测结果自动优化权重参数
  - 自动保存优化历史记录

- **参数更新模块**（`utils/model_parameter_updater.py`）：
  - 应用优化后的参数
  - 支持参数回滚
  - 自动创建新配置并激活

- **Web界面集成**（`templates/settings.html` - 模型学习面板）：
  - 性能评估结果可视化（性能指标卡片、趋势图表、因子贡献度图）
  - 参数优化功能（手动触发、显示结果、一键应用）
  - 优化历史展示（显示所有优化记录、支持查看详情和应用）

- **后端API端点**（`web_app.py`）：
  - `GET /api/model/evaluate` - 执行模型性能评估
  - `POST /api/model/optimize` - 执行参数优化
  - `GET /api/model/optimization-history` - 获取优化历史记录
  - `POST /api/model/apply-optimization/<id>` - 应用优化后的参数

#### 2. 股票信息表扩展 ✅
- 为 `stock_predictions` 表添加字段：
  - `industry`：所属行业
  - `concepts`：概念板块（JSON格式）
  - `main_concept`：主要概念板块
  - `market`：所属市场（A股/港股/美股）
- 添加了相应索引
- 修改 `StockPredictor.predict()` 和 `StockPredictionDB.save_prediction()` 以支持保存行业和板块信息
- 创建了字段添加脚本：`scripts/add_stock_info_fields.py`

### 相关文档

- `模型学习系统分析与设计.md`：系统设计文档
- `模型学习系统实施总结.md`：实施总结文档
- `股票信息字段添加说明.md`：字段添加说明文档

### 待完成功能

- 定时学习任务（每日/每周/每月自动评估和优化）
- 高级优化算法（贝叶斯优化、遗传算法、强化学习）

---

## [2026-01-XX] - 预测参数配置功能完善

### 新增功能

#### 1. 预测参数配置管理系统 ✅
- **数据库设计**：
  - 新增 `prediction_config` 表（配置主表）
  - 新增 `prediction_config_values` 表（配置值表，支持prediction/indicator/news/trading四类配置）
  - 新增 `prediction_config_history` 表（配置变更历史表）
  
- **配置管理器**（`utils/prediction_config_manager.py`）：
  - 单例模式实现，支持配置缓存
  - 配置验证功能：权重总和验证（必须为100%，允许±0.01误差）、参数范围验证
  - 配置CRUD操作：创建、读取、更新、删除
  - 配置激活机制：支持激活/取消激活，自动管理激活状态
  - 配置历史记录：记录所有配置变更操作（create/update/delete/activate）
  - 自动表创建：首次使用时自动创建数据表

- **后端API端点**（`web_app.py`）：
  - `GET /api/prediction/configs` - 获取所有配置列表
  - `GET /api/prediction/config/<id>` - 获取指定配置详情（包含info和values）
  - `GET /api/prediction/config/active` - 获取当前激活的配置
  - `POST /api/prediction/config` - 创建新配置（支持配置名称、描述、是否默认）
  - `PUT /api/prediction/config/<id>` - 更新配置（支持部分更新）
  - `DELETE /api/prediction/config/<id>` - 删除配置（不能删除激活的配置）
  - `POST /api/prediction/config/<id>/activate` - 激活配置（自动取消其他激活状态）
  - `POST /api/prediction/config/validate` - 验证配置值是否正确
  - `GET /api/prediction/config/<id>/history` - 获取配置变更历史

- **前端界面**（`templates/settings.html` - 参数设置面板）：
  - **预测因子权重配置**：
    - 8个权重因子滑块+输入框（新闻情感、资金流向、市场情绪、技术指标、板块轮动、历史模式、美股板块、估值指标）
    - 实时权重总和显示（0.00/1.00，颜色标识：绿色=正确，红色=错误）
    - 一键平衡权重功能（自动按比例调整使总和为1.0）
    - 权重分组显示（核心因素、技术分析、辅助因素、其他设置）
  - **技术指标参数配置**：
    - MA参数（短期、长期）
    - RSI参数（默认、短期、中期）
    - MACD参数（快线、慢线、信号线）
    - KDJ参数（周期、K值平滑、D值平滑）
    - CCI周期
  - **置信度设置**：
    - 最小置信度阈值
    - 回看天数
  - **配置管理功能**：
    - 配置列表模态框（显示所有配置，标记激活状态）
    - 创建新配置
    - 加载配置到表单
    - 激活配置
    - 删除配置
  - **操作按钮**：
    - 加载当前配置（从激活配置或默认值）
    - 配置管理（打开配置列表）
    - 验证配置（实时验证权重总和和参数范围）
    - 保存配置（保存为新配置）
    - 保存并激活（保存并立即激活）
    - 重置为默认值（恢复到config.py默认值）

- **动态配置加载**（`predictor/stock_predictor.py`）：
  - 修改 `StockPredictor.__init__()` 支持从数据库动态加载配置
  - 新增 `_load_prediction_config()` 方法：优先从数据库加载，否则使用config.py
  - 新增 `_load_indicator_config()` 方法：优先从数据库加载，否则使用config.py
  - 新增 `refresh_config()` 方法：支持配置热更新（无需重启服务）
  - 配置优先级：数据库激活配置 > config.py默认配置

- **数据迁移脚本**（`scripts/migrate_config_to_db.py`）：
  - 自动将 `config.py` 中的 `PREDICTION_CONFIG`、`INDICATOR_CONFIG`、`NEWS_CONFIG`、`TRADING_CONFIG` 导入数据库
  - 创建名为"默认配置"的配置记录
  - 如果已存在默认配置，则更新它
  - 自动激活导入的配置

#### 2. 功能特性
- **配置独立性**：配置存储在数据库中，与代码完全解耦
- **灵活性**：支持多个配置方案，可随时切换
- **热更新**：配置修改后立即生效，无需重启服务
- **向后兼容**：如果没有激活的数据库配置，自动使用 `config.py` 中的默认值
- **配置验证**：实时验证权重总和、参数范围，确保配置正确性
- **配置历史**：完整记录所有配置变更历史，支持追溯

#### 3. 新增文件
- `database/prediction_config_table.sql` - 预测参数配置表结构SQL脚本
- `utils/prediction_config_manager.py` - 预测参数配置管理器（单例模式）
- `scripts/migrate_config_to_db.py` - 配置迁移脚本（将config.py配置导入数据库）
- `预测参数配置功能分析报告.md` - 功能分析和设计文档

#### 4. 修改文件
- `web_app.py`：
  - 添加 `PredictionConfigManager` 导入和延迟初始化
  - 添加 `get_prediction_config_manager()` 函数
  - 添加8个预测参数配置API端点
  
- `templates/settings.html`：
  - 完善参数设置面板HTML界面（权重配置、指标参数配置）
  - 添加完整的JavaScript函数（配置加载、保存、验证、激活等）
  - 添加配置管理模态框
  
- `predictor/stock_predictor.py`：
  - 修改配置加载逻辑，支持从数据库动态加载
  - 添加配置刷新方法支持热更新
  
- `database/init_database.sql`：
  - 添加预测参数配置表的说明注释

### 技术改进

1. **配置管理架构**：
   - 采用单例模式确保配置管理器唯一实例
   - 配置缓存机制提高性能
   - 线程安全的配置操作

2. **用户体验**：
   - 实时权重总和验证和颜色提示
   - 一键平衡权重功能
   - 配置管理界面直观易用

3. **代码质量**：
   - 完善的错误处理和日志记录
   - 配置验证确保数据正确性
   - 向后兼容保证平滑升级

### 使用说明

1. **初始化数据库表**：
   ```bash
   # 方法1：直接执行SQL文件
   mysql -u root -p stock_data < database/prediction_config_table.sql
   
   # 方法2：通过Python脚本（自动创建）
   python -c "from utils.prediction_config_manager import PredictionConfigManager; PredictionConfigManager()"
   ```

2. **导入默认配置**：
   ```bash
   python scripts/migrate_config_to_db.py
   ```

3. **访问配置页面**：
   - 登录系统（admin/admin@123）
   - 点击顶部导航栏的"设置"按钮（仅管理员可见）
   - 选择"参数设置"菜单项

4. **修改配置**：
   - 修改权重或参数后，实时显示权重总和
   - 点击"验证配置"检查配置是否正确
   - 点击"保存配置"保存为新配置方案
   - 点击"保存并激活"保存并立即激活配置
   - 配置激活后立即生效，新的预测任务将使用新配置

5. **管理配置**：
   - 点击"配置管理"查看所有配置
   - 可以加载、激活、删除已有配置
   - 不能删除激活的配置

---

## [2026-01-08] - 定时任务统一管理功能测试与修复

### 修复的问题

#### 1. 前端函数参数问题 ✅
- **问题**：`startScheduledTask()` 和 `stopScheduledTask()` 函数没有传递 `task_source` 参数
- **修复**：更新函数签名，支持传递任务来源参数，根据来源调用相应的后端API

#### 2. 前端显示逻辑优化 ✅
- **问题**：任务信息显示不够完善，没有区分不同来源和类型
- **修复**：
  - 根据任务类型和调度类型动态显示信息（间隔执行、一次性任务等）
  - 正确显示任务来源标识
  - 根据任务来源显示不同的操作选项（原任务不能删除）

#### 3. 任务类型名称映射完善 ✅
- **问题**：缺少 `stock_analysis` 和部分调度类型的名称映射
- **修复**：添加了完整的任务类型和调度类型名称映射

#### 4. 执行状态显示优化 ✅
- **问题**：没有正确处理 `completed` 和 `cancelled` 状态
- **修复**：添加了对 `completed` 和 `cancelled` 状态的支持和显示

### 测试结果

✅ **功能测试通过**：
- `get_all_tasks()` 能够正确整合所有任务
- 前端能够正确显示所有任务类型
- 启动/停止功能能够根据任务来源正确调用相应逻辑
- 任务信息显示完整且准确

### 文件变更

1. `templates/settings.html` - 修复前端函数参数和显示逻辑
2. `功能测试报告.md` - 新建测试报告文档

---

## [2026-01-08] - 定时任务统一管理：整合所有定时任务到统一管理系统

### 新增功能

#### 1. 统一任务管理 ✅
- **整合所有定时任务**：
  - **股票历史数据更新任务**：从`scheduled_tasks`表管理
  - **股票分析任务**：从`analysis_tasks`表读取并显示
  - **新闻抓取任务**：从`news_crawl_tasks`表读取并显示
  - 所有任务在"定时任务管理"界面中统一显示和管理

#### 2. 定时任务管理器增强 ✅
- **支持多种任务类型** (`utils/scheduled_task_manager.py`)：
  - `stock_history_update`：股票历史数据更新
  - `stock_analysis`：股票分析（一次性任务）
  - `news_crawl`：新闻抓取（间隔执行）
  - 扩展`_execute_stock_analysis()`方法执行股票分析任务
  - 扩展`_execute_news_crawl()`方法执行新闻抓取任务

- **统一获取所有任务**：
  - `get_all_tasks()`方法现在会：
    - 从`scheduled_tasks`表获取定时任务
    - 从`news_crawl_tasks`表获取新闻抓取任务并转换为统一格式
    - 从`analysis_tasks`表获取股票分析任务并转换为统一格式
    - 所有任务统一返回，带有`_source`字段标识来源

- **启动/停止任务增强**：
  - `start_task()`和`stop_task()`方法支持`task_source`参数
  - 根据任务来源调用不同的处理逻辑
  - 新闻抓取任务：调用`NewsTaskManager`
  - 股票分析任务：在新线程中执行
  - 其他任务：加入调度器

#### 3. 前端界面增强 ✅
- **统一任务列表显示** (`templates/settings.html`)：
  - 显示所有类型的任务（股票历史数据更新、股票分析、新闻抓取）
  - 任务卡片显示：
    - 任务名称、类型、来源
    - 调度配置（时间、星期、间隔等）
    - 执行统计（执行次数、成功、失败）
    - 上次/下次执行时间
    - 运行状态（运行中/已停止）
  - 统一的启动/停止按钮
  - 根据任务来源显示不同的操作选项

- **创建任务弹窗增强**：
  - 支持选择任务类型（股票历史数据更新、股票分析、新闻抓取）
  - 根据任务类型动态显示配置选项：
    - **股票分析**：分析数量、排序方式
    - **新闻抓取**：抓取类型、股票代码、抓取间隔
    - **股票历史数据更新**：股票代码列表、执行时间、执行星期
  - 隐藏不需要的配置项（如一次性任务不需要调度时间）

#### 4. 后端API增强 ✅
- **启动/停止API增强** (`web_app.py`)：
  - 支持`source`查询参数，识别任务来源
  - 根据不同来源调用相应的处理逻辑
  - 股票分析任务：通过现有的任务管理机制处理
  - 新闻抓取任务：调用`NewsTaskManager`
  - 其他任务：调用`ScheduledTaskManager`

### 技术实现细节

1. **任务来源识别**：
   - 每个任务都带有`_source`字段（`scheduled_tasks`、`news_crawl_tasks`、`analysis_tasks`）
   - 前端在启动/停止时传递来源信息
   - 后端根据来源选择相应的处理方式

2. **任务格式统一**：
   - 所有任务转换为统一的格式，包含相同的字段
   - 原始数据保存在`task_config`中
   - 前端统一渲染，无需关心任务来源

3. **执行逻辑**：
   - 定时任务：加入调度器，按时间执行
   - 间隔任务：立即执行一次，然后定期执行
   - 一次性任务：立即执行，不加入调度器

### 文件变更

1. `utils/scheduled_task_manager.py` - 增强任务管理器，支持多种任务类型和统一管理
2. `templates/settings.html` - 增强前端界面，统一显示和管理所有任务
3. `web_app.py` - 增强API端点，支持多种任务来源
4. `CHANGELOG.md` - 记录所有变更

### 使用示例

1. **查看所有任务**：
   - 设置页面 → 任务管理 → 定时任务管理
   - 可以看到所有任务（股票历史数据更新、股票分析、新闻抓取）

2. **创建新任务**：
   - 点击"创建定时任务"
   - 选择任务类型（股票分析/新闻抓取/股票历史数据更新）
   - 根据类型填写相应的配置
   - 点击"创建"

3. **管理任务**：
   - 所有任务都可以在统一界面中启动/停止
   - 查看执行历史和统计信息

---

## [2026-01-08] - 定时任务管理功能：在设置页面开启与停止定时任务

### 新增功能

#### 1. 定时任务管理表 ✅
- **新建数据库表** (`database/scheduled_tasks_table.sql`)：
  - `scheduled_tasks` 表：存储定时任务配置和状态
    - 字段：任务名称、任务类型、调度配置、启用状态、执行统计、上次/下次执行时间等
    - 支持daily/hourly/weekly/custom等调度类型
    - 支持指定执行时间、执行星期
  - `scheduled_task_history` 表：存储任务执行历史
    - 字段：执行时间、执行时长、状态、消息、结果数据、错误信息等

#### 2. 定时任务管理器 ✅
- **新建模块** (`utils/scheduled_task_manager.py`)：
  - `ScheduledTaskManager` 类：管理定时任务的创建、启动、停止、调度
  - 主要功能：
    - `create_task()`：创建定时任务
    - `start_task()`：启动定时任务（加入调度器）
    - `stop_task()`：停止定时任务（从调度器移除）
    - `get_task()` / `get_all_tasks()`：获取任务信息
    - `get_task_history()`：获取任务执行历史
    - `delete_task()`：删除定时任务
  - **调度器集成**：
    - 使用`schedule`库实现定时调度
    - 后台线程运行调度器循环
    - 支持每天指定时间执行（默认15:05，收盘后5分钟）
    - 支持指定星期执行（如：1,2,3,4,5表示周一到周五）
  - **任务执行**：
    - 自动执行股票历史数据增量更新任务
    - 记录执行开始时间、结束时间、状态、消息
    - 统计执行次数、成功次数、失败次数
    - 计算下次执行时间

#### 3. 设置页面定时任务管理 ✅
- **前端界面** (`templates/settings.html`)：
  - 在"任务管理"面板中添加"定时任务管理"部分
  - 功能：
    - 创建定时任务（弹窗）
    - 启动/停止定时任务
    - 查看任务状态（运行中/已停止）
    - 查看执行统计（执行次数、成功、失败）
    - 查看上次/下次执行时间
    - 查看执行历史
    - 删除定时任务
  - 实时显示任务状态和执行信息

#### 4. 后端API ✅
- **新建API端点** (`web_app.py`)：
  - `GET /api/scheduled/tasks`：获取所有定时任务
  - `POST /api/scheduled/tasks`：创建定时任务
  - `POST /api/scheduled/tasks/<id>/start`：启动定时任务
  - `POST /api/scheduled/tasks/<id>/stop`：停止定时任务
  - `GET /api/scheduled/tasks/<id>`：获取任务信息
  - `DELETE /api/scheduled/tasks/<id>`：删除定时任务
  - `GET /api/scheduled/tasks/<id>/history`：获取任务执行历史
  - 所有API都需要登录验证

### 技术实现细节

1. **调度器实现**：
   - 使用`schedule`库实现轻量级定时调度
   - 后台线程运行调度循环（每秒检查一次待执行任务）
   - 支持每天指定时间、指定星期执行

2. **任务执行**：
   - 任务在独立线程中执行，不阻塞调度器
   - 记录执行历史（开始时间、结束时间、状态、消息、错误信息）
   - 自动计算下次执行时间

3. **数据库状态同步**：
   - 任务状态存储在数据库中
   - 启动/停止时更新数据库状态
   - 执行时更新执行统计和历史记录

### 文件变更

1. `database/scheduled_tasks_table.sql` - 新建定时任务管理表
2. `utils/scheduled_task_manager.py` - 新建定时任务管理器模块
3. `templates/settings.html` - 添加定时任务管理界面
4. `web_app.py` - 添加定时任务管理API端点
5. `CHANGELOG.md` - 记录所有变更

### 使用示例

1. **创建定时任务**：
   - 在设置页面的"定时任务管理"部分点击"创建定时任务"
   - 设置任务名称、类型（股票历史数据更新）、执行时间（默认15:05）、执行星期（默认1-5）

2. **启动/停止任务**：
   - 在任务列表中点击"启动"或"停止"按钮
   - 任务状态会实时更新（运行中/已停止）

3. **查看执行历史**：
   - 点击任务的"执行历史"按钮
   - 查看历史执行记录（时间、状态、消息）

### 注意事项

1. **依赖库**：
   - 需要安装`schedule`库：`pip install schedule`

2. **任务执行**：
   - 任务在后台线程中执行，不会阻塞Web服务
   - 如果任务执行时间较长，不会影响下次调度

3. **数据库状态**：
   - 任务状态存储在数据库中，服务重启后会自动恢复
   - 已启用的任务在服务启动时会自动加入调度器

---

## [2026-01-08] - 新建股票历史数据存储表（近10年详细数据）

### 新增功能

#### 1. 股票历史数据表 ✅
- **新建数据库表** (`database/stock_history_table.sql`)：
  - 表名：`stock_history_data`
  - 存储近10年每只股票的详细历史数据
  - 包含字段：
    - **基本信息**：股票代码、股票名称、交易日期
    - **价格数据**：开盘价、收盘价、最高价、最低价、昨收价、涨跌额、涨跌幅
    - **成交数据**：成交量、成交额、换手率、量比
    - **盘口数据**：外盘、内盘、委比、五档买卖盘（JSON格式）
    - **成本分布**：历史成本分布、当日成本分布（JSON格式）
    - **市值和估值**：总市值、流通市值、市盈率、市净率
    - **涨跌停信息**：涨停价、跌停价、是否涨停/跌停
    - **技术指标**：MA5/10/20/60、RSI、MACD、MACD Signal、MACD Histogram
    - **资金流向**：主力净流入、超大单/大单/中单/小单净流入
    - **融资融券**：融资余额、融券余额、融资融券余额占比
    - **其他数据**：振幅、价格区间、其他扩展数据（JSON格式）
  - **唯一索引**：`(symbol, trade_date)` 确保每天每个股票只有一条记录
  - **索引优化**：为常用查询字段创建索引（symbol、trade_date、volume、change_pct等）

#### 2. 数据存储模块 ✅
- **新建模块** (`utils/stock_history_storage.py`)：
  - `StockHistoryStorage` 类：管理股票历史数据的存储和查询
  - 主要方法：
    - `save_stock_daily_data()`：保存股票单日数据（支持ON DUPLICATE KEY UPDATE）
    - `get_stock_history_data()`：获取股票历史数据（支持日期范围和数量限制）
    - `get_latest_date()`：获取最新数据的日期
    - `check_data_exists()`：检查数据是否存在
    - `get_missing_dates()`：获取缺失的日期列表（排除周末）
  - 自动解析JSON字段（五档买卖盘、成本分布等）
  - 自动创建表（如果不存在）

#### 3. 数据采集模块 ✅
- **新建模块** (`utils/stock_history_collector.py`)：
  - `StockHistoryCollector` 类：采集股票历史数据
  - 主要方法：
    - `collect_stock_daily_data()`：采集股票单日数据（整合多个数据源）
    - `collect_stock_history_data()`：采集股票历史数据（近N年）
    - `incremental_update_today()`：增量更新今日数据（收盘后调用）
    - `batch_collect_stocks_history()`：批量采集多只股票的历史数据
  - **数据采集流程**：
    1. 获取基本K线数据（开盘、收盘、最高、最低、成交量）
    2. 获取实时行情数据（包含更多信息：PE、PB、市值、换手率等）
    3. 获取买卖盘数据（五档买卖盘、委比，外盘内盘如果可用）
    4. 获取成本分布数据（历史成本分布、当日成本分布）
    5. 获取资金流向数据（主力净流入、各档位净流入）
    6. 获取融资融券数据（融资余额、融券余额）
    7. 计算技术指标（MA、RSI、MACD等）
    8. 计算量比、振幅等衍生指标
  - **错误处理**：每个数据源独立处理异常，确保部分数据缺失不影响整体采集
  - **请求限速**：每次请求间隔0.5秒，避免请求过快被限制

#### 4. 数据采集脚本 ✅
- **初始数据采集脚本** (`scripts/collect_stock_history.py`)：
  - 用于采集近10年历史数据（首次使用或补充历史数据）
  - 支持参数：
    - `--symbol`：单只股票代码
    - `--symbols`：多只股票代码列表
    - `--years`：采集多少年的数据（默认10年）
    - `--limit`：限制股票数量
    - `--sort-by-turnover`：按成交量排序
  - 自动识别缺失日期，只采集缺失的数据
  - 支持强制刷新（重新采集已存在的数据）

- **每日增量更新脚本** (`scripts/update_stock_history_daily.py`)：
  - 用于每日收盘后增量更新今日数据
  - 支持参数：
    - `--symbol`：单只股票代码
    - `--symbols`：多只股票代码列表
    - 如果不指定，则更新所有股票的数据
  - 自动跳过已存在的数据，避免重复采集
  - 适合设置为定时任务（每天收盘后自动执行）

#### 5. 表创建脚本 ✅
- **新建脚本** (`database/create_stock_history_table.py`)：
  - 用于创建股票历史数据表
  - 可以独立运行，也可被其他模块调用
  - 自动检查表是否已存在，避免重复创建

#### 6. 使用文档 ✅
- **新建文档** (`database/stock_history_README.md`)：
  - 详细说明数据库表结构
  - 使用方法（命令行、Python API）
  - 定时任务设置（Linux/Mac crontab、Windows任务计划程序）
  - 注意事项和故障排查

### 技术实现细节

1. **数据库设计**：
   - 使用`ON DUPLICATE KEY UPDATE`确保数据不重复
   - JSON字段存储复杂数据（五档买卖盘、成本分布等）
   - 为常用查询字段创建索引，提高查询效率

2. **数据采集**：
   - 整合多个数据源（akshare的不同接口）
   - 自动计算技术指标和衍生指标
   - 错误隔离：每个数据源独立处理异常

3. **增量更新**：
   - 自动识别缺失日期（排除周末）
   - 支持补全历史数据
   - 支持强制刷新

### 文件变更

1. `database/stock_history_table.sql` - 新建数据库表结构
2. `database/create_stock_history_table.py` - 新建表创建脚本
3. `utils/stock_history_storage.py` - 新建数据存储模块
4. `utils/stock_history_collector.py` - 新建数据采集模块
5. `scripts/collect_stock_history.py` - 新建初始数据采集脚本
6. `scripts/update_stock_history_daily.py` - 新建每日增量更新脚本
7. `database/stock_history_README.md` - 新建使用文档
8. `database/init_database.sql` - 添加注释说明
9. `CHANGELOG.md` - 记录所有变更

### 使用示例

```bash
# 1. 创建表
python database/create_stock_history_table.py

# 2. 采集单只股票的历史数据（近10年）
python scripts/collect_stock_history.py --symbol 600519 --years 10

# 3. 每日增量更新（收盘后执行）
python scripts/update_stock_history_daily.py

# 4. 设置定时任务（Linux/Mac）
# crontab -e
# 5 15 * * 1-5 cd /path/to/smart_stock_advisor && python scripts/update_stock_history_daily.py
```

---

## [2026-01-08] - 实施低优先级优化：市场状态识别、动态权重调整

### 已实现优化

#### 1. 市场状态识别 ✅
- **新建市场状态识别模块** (`utils/market_state_identifier.py`)：
  - `MarketStateIdentifier` 类：识别当前市场状态（牛市/熊市/震荡市）
  - 基于多个指标综合判断：
    - **趋势判断**：基于20日均线，判断趋势方向（向上/向下/中性）
    - **波动率判断**：计算日收益率标准差，判断波动率水平（高/中/低）
    - **成交量趋势**：分析成交量变化趋势（增加/减少/稳定）
    - **涨跌天数比例**：计算上涨天数和下跌天数比例

- **市场状态判断逻辑**：
  - **牛市**：趋势向上 + 低/中波动 + 放量/稳定 + 上涨天数>60%
  - **熊市**：趋势向下 + 高波动 + 放量/稳定 + 下跌天数>60%
  - **震荡市**：其他情况

- **置信度计算**：
  - 基于趋势强度、波动率一致性、成交量趋势一致性、涨跌天数比例一致性
  - 返回市场状态置信度（0-1）

#### 2. 动态权重调整 ✅
- **根据市场状态调整权重**：
  - **牛市**：
    - 技术指标权重 × 1.2（技术分析在牛市中更有效）
    - 新闻权重 × 0.8（情绪主导，新闻影响相对较小）
    - 资金流向权重 × 1.1
  - **熊市**：
    - 技术指标权重 × 0.8（技术分析在熊市中失效更快）
    - 新闻权重 × 1.3（政策面影响大）
    - 资金流向权重 × 1.2
    - 市场情绪权重 × 1.1
  - **震荡市**：
    - 保持默认权重（不调整）

- **权重归一化**：
  - 动态调整后的权重会进行归一化，确保总和为1
  - 避免权重调整导致最终得分偏差

- **集成到预测器**：
  - 在 `StockPredictor.predict()` 中集成市场状态识别
  - 根据市场状态动态调整各因子权重
  - 市场状态信息包含在预测结果中

#### 3. 策略动态调整 ✅
- **根据市场状态调整止损止盈**：
  - **牛市**：
    - 止盈目标提高20%（趋势向上，可能继续上涨）
    - 止损放宽20%（给更多上涨空间）
  - **熊市**：
    - 止盈目标降低20%（趋势向下，风险较大）
    - 止损收紧20%（快速止损，避免更大损失）
  - **震荡市**：
    - 使用默认止损止盈阈值

- **集成到实时交易决策**：
  - 在 `RealtimeTradingAdvisor._make_trading_decision()` 中根据市场状态调整策略
  - 市场状态信息显示在决策理由中
  - 止损止盈阈值根据市场状态动态调整

#### 4. 页面优化 ✅
- **实时策略页面增强** (`templates/realtime_strategy.html`)：
  - 添加市场状态显示区域：
    - 显示市场状态（牛市🐂/熊市🐻/震荡市📊）
    - 使用不同颜色标识（绿色/红色/黄色）
    - 显示市场状态描述和置信度

- **JavaScript更新**：
  - 在 `renderAdvice()` 函数中添加市场状态渲染逻辑
  - 根据市场状态使用不同颜色显示

#### 5. 预测结果增强 ✅
- **预测结果包含市场状态**：
  - 在预测结果中添加 `market_state` 字段
  - 包含市场状态、置信度、趋势、波动率、成交量趋势等信息
  - 在预测摘要中显示市场状态信息

### 技术实现细节

1. **市场状态识别流程**：
   ```
   获取指数数据 → 计算趋势 → 计算波动率 → 计算成交量趋势 → 
   计算涨跌天数比例 → 综合判断 → 计算置信度 → 返回市场状态
   ```

2. **动态权重调整公式**：
   ```python
   # 根据市场状态获取权重倍数
   multipliers = identifier.get_weight_adjustment(market_state)
   
   # 调整权重
   adjusted_weight = base_weight * multiplier
   
   # 归一化
   normalized_weight = adjusted_weight / total_adjusted_weight
   ```

3. **策略调整逻辑**：
   ```python
   if market_state == 'bull_market':
       take_profit *= 1.2  # 提高止盈
       stop_loss *= 1.2    # 放宽止损
   elif market_state == 'bear_market':
       take_profit *= 0.8  # 降低止盈
       stop_loss *= 0.8    # 收紧止损
   ```

### 文件变更

1. `utils/market_state_identifier.py` - 新建市场状态识别模块
2. `predictor/stock_predictor.py` - 集成市场状态识别和动态权重调整
3. `predictor/realtime_trading_advisor.py` - 根据市场状态调整策略
4. `templates/realtime_strategy.html` - 添加市场状态显示
5. `CHANGELOG.md` - 记录所有变更

### 优化效果

1. **适应性提升**：根据市场状态动态调整权重和策略，提高预测准确性
2. **风险管理**：牛市时更积极，熊市时更保守，震荡市时平衡
3. **用户体验**：在页面中显示市场状态，帮助用户理解当前市场环境

---

## [2026-01-08] - 实施中优先级优化：置信度计算优化、交易成本考虑

### 已实现优化

#### 1. 置信度计算优化 ✅
- **改进的置信度计算方法**：
  - 在 `StockPredictor` 中添加 `_calculate_confidence()` 方法
  - 考虑多个因素综合计算置信度：
    - **基础置信度**（40%权重）：基于得分绝对值
    - **因子一致性**（30%权重）：所有因子方向一致时提高置信度
    - **数据质量**（20%权重）：数据质量得分
    - **历史准确率**（10%权重）：历史预测准确率（预留接口）

- **因子一致性计算**：
  - `_calculate_factor_consistency()` 方法：计算各因子方向的一致性
  - 如果所有因子都指向同一方向（都看涨或都看跌），一致性得分更高
  - 一致性得分范围 0-1，50%一致性对应0.5，100%一致性对应1.0

- **效果**：
  - 置信度计算更加准确和可靠
  - 当所有因子方向一致时，置信度会显著提高
  - 数据质量差时，置信度会相应降低

#### 2. 交易成本考虑 ✅
- **交易成本计算**：
  - 在 `RealtimeTradingAdvisor` 中添加交易成本计算逻辑
  - 考虑的成本：
    - **手续费**（0.03%）：买入和卖出都收
    - **印花税**（0.1%）：仅卖出时收
    - **滑点**（0.1%）：买入和卖出都有
  - **总成本率**：买入成本 + 卖出成本 ≈ 0.23%

- **成本影响决策**：
  - 计算预期净收益 = 预期收益 - 交易成本
  - 如果净预期收益 < 最小盈利阈值（默认1%），不建议买入
  - 避免频繁小额交易，实际收益被成本侵蚀

- **价格建议优化**：
  - 买入价格建议考虑买入成本（手续费+滑点）
  - 目标价建议考虑卖出成本（手续费+印花税+滑点）
  - 确保扣除成本后仍能达到预期收益

- **配置更新** (`config.py`)：
  - 在 `TRADING_CONFIG` 中添加交易成本配置：
    - `commission_rate`: 手续费率（默认0.0003）
    - `stamp_tax_rate`: 印花税率（默认0.001）
    - `slippage_rate`: 滑点率（默认0.001）
    - `min_profit_threshold`: 最小盈利阈值（默认0.01，即1%）
    - `enable_cost_consideration`: 是否启用交易成本考虑（默认True）

- **决策结果增强**：
  - 在决策结果中添加 `cost_analysis` 字段：
    - `total_cost_rate`: 总成本率
    - `expected_return`: 预期收益
    - `net_expected_return`: 净预期收益
    - `cost_breakdown`: 成本明细
  - 在决策理由中显示成本信息和净预期收益

### 技术实现细节

1. **置信度计算方法**：
   ```python
   confidence = (
       base_confidence * 0.40 +      # 基础置信度
       factor_consistency * 0.30 +   # 因子一致性
       quality_score * 0.20 +        # 数据质量
       historical_weight * 0.10      # 历史准确率
   )
   ```

2. **交易成本计算**：
   ```python
   # 买入成本
   buy_cost_rate = commission_rate + slippage_rate
   
   # 卖出成本
   sell_cost_rate = commission_rate + stamp_tax_rate + slippage_rate
   
   # 总成本
   total_cost_rate = buy_cost_rate + sell_cost_rate
   
   # 净预期收益
   net_expected_return = expected_return - total_cost_rate
   ```

### 文件变更

1. `predictor/stock_predictor.py` - 添加置信度计算方法
2. `predictor/realtime_trading_advisor.py` - 添加交易成本考虑
3. `config.py` - 添加交易成本配置

---

## [2026-01-08] - 实施高优先级优化：预测缓存、数据质量检查、风险控制

### 已实现优化

#### 1. 实时策略效率优化 ✅
- **预测结果缓存机制**：
  - 在 `RealtimeTradingAdvisor` 中添加了预测结果缓存
  - 缓存时长默认10分钟（600秒），可配置
  - 避免每次刷新都执行完整的预测分析（耗时5-10秒）
  - 预计响应时间从5-10秒降低到1秒以内
  - 使用线程安全锁保证并发安全

- **缓存方法**：
  - `_get_cached_prediction()`: 获取缓存的预测结果，如果缓存不存在或已过期则执行新预测
  - `clear_prediction_cache()`: 清除预测缓存（支持清除单个或全部）

#### 2. 数据质量检查 ✅
- **新建数据验证模块** (`utils/data_validator.py`)：
  - `DataValidator` 类：提供全面的数据质量验证
  - 数据完整性检查：检查数据点数量、必需列、缺失值比例
  - 价格合理性检查：检查价格范围、单日涨跌幅
  - 成交量合理性检查：检查负成交量、成交量异常放大
  - 数据一致性检查：检查 high >= low, close 在高低价范围内等
  - 异常值检测：使用Z分数方法检测价格异常值
  - 数据时效性检查：检查数据年龄

- **实时行情验证**：
  - `validate_realtime_quote()`: 验证实时行情数据的质量
  - 返回质量得分、警告和错误信息

- **集成到实时交易决策**：
  - 在 `RealtimeTradingAdvisor.get_realtime_decision()` 中集成数据验证
  - 验证结果包含在返回的决策结果中

#### 3. 风险控制增强 ✅
- **新建风险控制模块** (`utils/risk_controller.py`)：
  - `RiskController` 类：提供组合风险控制功能
  - 仓位限制检查：检查单只股票仓位和总仓位限制
  - 相关性检查：检查股票之间的相关性，避免持有相关性过高的股票
  - 组合风险计算：计算总仓位、仓位集中度（HHI指数）、风险得分
  - 风险建议生成：根据风险指标生成风险建议

- **配置更新** (`config.py`)：
  - 在 `TRADING_CONFIG` 中添加风险控制配置：
    - `max_total_position_pct`: 总仓位上限（默认80%）
    - `max_single_position_pct`: 单只股票最大仓位（默认30%）
    - `max_correlation`: 最大相关性（默认0.8）
    - `enable_risk_control`: 是否启用风险控制（默认True）

- **集成到实时策略API**：
  - 在 `/api/realtime_strategy` 中计算并返回风险控制数据
  - 包含风险得分、总仓位、持仓数量、仓位集中度、警告和建议

#### 4. 页面优化 ✅
- **实时策略页面增强** (`templates/realtime_strategy.html`)：
  - 添加"数据质量"显示区域：
    - 显示数据有效性状态（✓ 数据有效 / ✗ 数据异常）
    - 显示质量得分（百分比）
    - 显示警告信息
  - 添加"风险控制"显示区域：
    - 显示风险等级（低风险/中风险/高风险）
    - 显示风险得分（百分比）
    - 显示总仓位和持仓数量
    - 显示风险警告和建议

- **JavaScript更新**：
  - 在 `renderAdvice()` 函数中添加数据质量和风险控制的渲染逻辑
  - 根据数据质量和风险等级使用不同颜色显示（绿色/黄色/红色）

### 技术实现细节

1. **缓存机制**：
   ```python
   # 缓存格式
   {
       symbol: {
           'prediction': {...},
           'timestamp': datetime,
           'cache_duration': 600
       }
   }
   ```

2. **数据验证流程**：
   - 完整性检查 → 价格合理性 → 成交量合理性 → 数据一致性 → 异常值检测
   - 返回质量得分（0-1）和详细报告

3. **风险控制流程**：
   - 仓位限制检查 → 相关性检查 → 组合风险计算 → 风险建议生成

### 下一步计划

- [ ] 中优先级优化：置信度计算优化、交易成本考虑、自动化回测系统
- [ ] 低优先级优化：动态权重调整、自动学习机制、市场状态识别

---

## [2026-01-08] - 预测与实时策略缺陷分析与优化建议

### 分析报告
- ✅ **创建缺陷分析报告**：
  - 新建 `预测与实时策略缺陷分析与优化建议.md`
  - 全面分析预测模型和实时交易策略的缺陷
  - 提出详细的优化建议和实施优先级

### 主要发现

#### 预测模型缺陷
1. **权重配置问题**：
   - 权重固定，无法根据市场状态动态调整
   - 所有股票使用相同权重，未考虑个股特性
   - 缺少理论依据和回测验证

2. **置信度计算过于简单**：
   - 仅基于得分绝对值，未考虑数据质量和因子一致性
   - 未考虑历史预测准确率

3. **缺少模型验证和回测机制**：
   - 没有自动化的回测系统
   - 无法评估预测模型的整体表现
   - 无法识别模型在哪些市场条件下表现好/差

4. **概率转换方法单一**：
   - 仅使用sigmoid函数，放大系数是经验值
   - 未考虑不同市场状态下的概率分布差异
   - 概率可能不够校准

5. **缺少异常情况处理**：
   - 未处理停牌、涨跌停、ST股票等特殊情况
   - 未处理数据异常（价格突变、成交量异常）

#### 实时交易策略缺陷
1. **效率问题**：
   - 每次刷新都执行完整预测分析，耗时5-10秒
   - 导致实时策略页面响应慢

2. **缺少交易成本考虑**：
   - 决策中未考虑手续费、印花税、滑点
   - 可能导致频繁交易，实际收益被成本侵蚀

3. **风险控制不足**：
   - 只有单只股票的止损止盈，没有组合风险控制
   - 没有总仓位控制
   - 没有考虑相关性风险

4. **决策逻辑过于简单**：
   - 决策规则是硬编码的if-else，缺乏灵活性
   - 未考虑市场状态和个股特性对决策的影响

5. **缺少市场状态识别**：
   - 未识别当前市场状态（牛市/熊市/震荡市）
   - 所有市场状态下使用相同的决策逻辑

6. **价格建议不够精确**：
   - 价格建议过于简单，仅基于今日涨跌幅
   - 未考虑支撑位、阻力位、买卖盘深度

#### 数据质量与错误处理缺陷
1. **数据质量检查不足**：
   - 没有系统性的数据质量检查
   - API返回异常数据时可能直接使用

2. **API失败处理不足**：
   - API失败时直接返回错误，没有降级策略
   - 没有重试机制

3. **缺少数据时效性检查**：
   - 未检查数据的时效性
   - 可能使用过时的数据进行预测

#### 模型学习与优化缺陷
1. **缺少自动学习机制**：
   - 虽然有保存实时决策数据，但没有自动学习机制
   - 权重配置需要手动调整
   - 无法根据历史表现自动优化

2. **缺少特征工程**：
   - 使用的特征都是原始特征，没有进行特征工程
   - 未考虑特征之间的交互作用

### 优化建议优先级

#### 高优先级（立即实施）🔴
1. **实时策略效率优化**：预测结果缓存，避免重复计算
2. **风险控制增强**：添加总仓位控制和相关性检查
3. **数据质量检查**：添加数据验证和异常检测

#### 中优先级（近期实施）🟡
4. **置信度计算优化**：改进置信度计算，考虑多因素
5. **交易成本考虑**：在决策中考虑交易成本
6. **自动化回测系统**：定期回测评估模型表现

#### 低优先级（长期优化）🟢
7. **动态权重调整**：根据市场状态动态调整权重
8. **自动学习机制**：根据历史表现自动优化
9. **市场状态识别**：识别市场状态，调整策略

### 实施建议
- **阶段一**（1-2周）：基础优化（缓存、数据检查、风险控制）
- **阶段二**（2-4周）：功能增强（置信度、成本、回测）
- **阶段三**（1-2个月）：智能化优化（动态权重、市场状态、自动学习）

---

## [2026-01-08] - 优化实时策略功能：添加设置弹窗，动态展示当日走势和实时交易建议

### 功能优化
- ✅ **创建实时策略HTML页面**：
  - 新建 `templates/realtime_strategy.html` 页面
  - 左侧展示当日走势图（使用Plotly绘制价格、均价、成交量）
  - 右侧展示实时交易建议（操作建议、决策理由、价格建议、风险警告、仓位建议等）
  - 每10秒自动刷新一次数据

- ✅ **添加设置弹窗**：
  - 修改 `stock_list.html` 中的"实时策略"按钮
  - 点击按钮后弹出设置窗口，可以设置：
    - 持仓状态（已持仓/未持仓）
    - 持仓成本价（如果已持仓）
  - 点击确认后跳转到实时策略页面

- ✅ **创建实时策略API接口**：
  - 新增 `/realtime_strategy` 路由：渲染实时策略页面
  - 新增 `/api/realtime_strategy` API接口：
    - 调用 `RealtimeTradingAdvisor.get_realtime_decision()` 获取实时交易决策
    - 从数据源获取分时数据（当日走势）
    - 支持传入持仓状态和持仓成本价参数
    - 结合批量预测数据（持仓成本、指标、新闻等）生成实时建议

### 技术实现
- **前端技术**：
  - 使用 Plotly.js 绘制当日走势图（价格线、均价线、成交量柱状图）
  - 使用 JavaScript 定时器每10秒自动刷新数据
  - 使用模态框实现设置窗口

- **后端技术**：
  - 调用 `RealtimeTradingAdvisor.get_realtime_decision()` 获取实时交易决策
  - 从 `StockDataSource.get_intraday_data()` 获取分时数据
  - 结合预测数据、实时行情、资金流向、买卖盘等生成综合建议

### 实时策略模型
- **数据来源**：
  - 批量预测数据（技术指标、新闻情感、市场情绪等）
  - 实时行情数据（当前价格、涨跌幅等）
  - 实时资金流向数据
  - 买卖盘数据
  - 持仓信息（成本价、盈亏等）

- **决策逻辑**：
  - 综合预测得分、资金流向、买卖盘强度、盘中涨跌等因素
  - 根据持仓状态给出不同建议（买入/卖出/加仓/减仓/持有/观望）
  - 提供价格建议（理想买入价、最高买入价、止损价、目标价等）
  - 考虑风险控制（止损、止盈、移动止损）

### 相关文件
- `smart_stock_advisor/templates/realtime_strategy.html` - 新建实时策略页面
- `smart_stock_advisor/web_app.py` - 新增 `/realtime_strategy` 路由和 `/api/realtime_strategy` API接口
- `smart_stock_advisor/stock_list.html` - 修改实时策略按钮，添加设置弹窗

### 数据流程
1. 用户点击"实时策略"按钮，弹出设置窗口
2. 用户设置持仓状态和成本价，点击确认
3. 跳转到 `/realtime_strategy` 页面，传入参数
4. 页面通过 `/api/realtime_strategy` API获取实时数据
5. API调用 `RealtimeTradingAdvisor.get_realtime_decision()` 生成实时建议
6. 页面每10秒自动刷新，更新数据和图表

---

## [2026-01-08] - 优化历史预测功能：从数据库动态生成HTML页面，展示预测与实际对比

### 功能优化
- ✅ **创建历史预测HTML页面**：
  - 新建 `templates/history.html` 页面，展示历史预测记录
  - 参考 `history_600519.html` 的内容结构
  - 包含预测时间、预测日期、目标日期、预测方向、概率、置信度等
  - **重要：展示预测与实际对比**，包括：
    - 预测方向 vs 实际方向
    - 预测时价格 vs 实际收盘价
    - 实际涨跌幅
    - 预测命中情况（命中/未命中）
  - 支持展开查看每条预测的详细内容（预测摘要、因子详情等）

- ✅ **创建历史预测API接口**：
  - 新增 `/history` 路由：渲染历史预测页面
  - 新增 `/api/history` API接口，从数据库获取历史预测数据
  - **自动更新实际数据**：在获取数据前自动调用 `_update_historical_actual_data()` 更新所有历史记录的实际价格、涨跌幅、方向和命中情况
  - 支持获取 `stock_predictions` 表的所有历史记录
  - 支持获取 `prediction_factors` 表的因子数据

- ✅ **修改历史预测按钮**：
  - 修改 `stock_list.html` 中的"历史预测"按钮
  - 按钮现在指向 `/history?symbol=xxx&name=xxx` 页面
  - 不再依赖静态HTML文件路径

### 技术实现
- **前端技术**：
  - 使用原生JavaScript动态加载数据并渲染表格
  - 支持展开/收起详情面板
  - 使用颜色区分预测方向、实际方向和命中情况
  - 突出显示预测与实际对比部分

- **后端技术**：
  - 从 `stock_predictions` 表获取所有历史预测记录
  - 从 `prediction_factors` 表获取各因子得分和权重
  - 自动调用 `_update_historical_actual_data()` 更新实际数据
  - 数据已通过 `stock_predictor.py` 和 `prediction_visualizer.py` 自动保存到数据库

### 数据对比功能
- **预测与实际对比**：
  - 预测方向 vs 实际方向（颜色区分）
  - 预测时价格 vs 实际收盘价
  - 实际涨跌幅（带颜色标识）
  - 预测命中情况（命中/未命中/未知，带颜色标识）
  - 在详情面板中突出显示对比信息

### 相关文件
- `smart_stock_advisor/templates/history.html` - 新建历史预测页面
- `smart_stock_advisor/web_app.py` - 新增 `/history` 路由和 `/api/history` API接口
- `smart_stock_advisor/stock_list.html` - 修改历史预测按钮链接

### 数据流程
1. 股票分析时，`stock_predictor.py` 的 `predict` 方法会调用 `self.data_storage.save_prediction_factors` 保存因子数据
2. `prediction_visualizer.py` 的 `save_stock_record` 方法会调用 `db.save_prediction` 保存预测结果，并自动调用 `_update_historical_actual_data()` 更新历史实际数据
3. 用户点击"历史预测"按钮时，跳转到 `/history` 页面
4. 页面通过 `/api/history` API获取数据，API会自动更新历史实际数据
5. 页面渲染历史记录表格，突出显示预测与实际对比

---

## [2026-01-08] - 优化文字详情功能：从数据库动态生成HTML报告

### 功能优化
- ✅ **创建文字详情HTML页面**：
  - 新建 `templates/text_detail.html` 页面，展示完整的文字分析报告
  - 包含市场整体行情预测、个股预测分析、交易建议、实时行情与交易决策等部分
  - 参考之前生成的完整HTML报告内容结构
  - 响应式设计，支持滚动查看完整内容

- ✅ **创建文字详情API接口**：
  - 新增 `/api/text_detail` API接口，从数据库获取文字详情数据
  - 支持获取 `stock_predictions` 表的预测结果和摘要
  - 支持获取 `prediction_factors` 表的因子得分和权重
  - 支持获取 `news_sentiment` 表的新闻情感详细数据
  - 支持获取成本分布数据（历史 & 当日）
  - 支持获取实时行情和交易决策数据（如果市场开盘）

- ✅ **修改文字详情按钮**：
  - 修改 `stock_list.html` 中的"文字详情"按钮
  - 按钮现在指向 `/text_detail?symbol=xxx&name=xxx` 页面
  - 不再依赖静态HTML文件路径

### 技术实现
- **前端技术**：
  - 使用原生JavaScript动态加载数据并渲染内容
  - 支持滚动查看个股预测分析完整内容
  - 实时数据展示（如果市场开盘）

- **后端技术**：
  - 从 `stock_predictions` 表获取预测结果和摘要
  - 从 `prediction_factors` 表获取各因子得分和权重
  - 从 `news_sentiment` 表获取新闻情感详细数据
  - 从数据源获取成本分布和实时数据
  - 数据已通过 `stock_predictor.py` 和 `prediction_visualizer.py` 自动保存到数据库

### 相关文件
- `smart_stock_advisor/templates/text_detail.html` - 新建文字详情页面
- `smart_stock_advisor/web_app.py` - 新增 `/text_detail` 路由和 `/api/text_detail` API接口
- `smart_stock_advisor/stock_list.html` - 修改文字详情按钮链接

### 数据流程
1. 股票分析时，`stock_predictor.py` 的 `predict` 方法会调用 `self.data_storage.save_prediction_factors` 保存因子数据
2. `prediction_visualizer.py` 的 `save_stock_record` 方法会调用 `db.save_prediction` 保存预测结果和摘要
3. 用户点击"文字详情"按钮时，跳转到 `/text_detail` 页面
4. 页面通过 `/api/text_detail` API获取数据并渲染内容

---

## [2026-01-08] - 优化图形报告功能：从数据库动态生成HTML图表

### 功能优化
- ✅ **创建图形报告HTML页面**：
  - 新建 `templates/graph_report.html` 页面，使用 Plotly 和 Chart.js 展示图表
  - 包含涨跌概率饼图、各因素得分雷达图、涨跌概率对比柱状图、30天价格趋势图
  - 响应式设计，支持不同屏幕尺寸
  - 从数据库动态获取数据，实时展示最新预测结果

- ✅ **创建图形报告API接口**：
  - 新增 `/api/graph_report` API接口，从数据库获取预测数据和因子数据
  - 支持获取 `stock_predictions` 表的预测结果
  - 支持获取 `prediction_factors` 表的因子得分和权重
  - 支持获取30天价格趋势数据

- ✅ **修改图形报告按钮**：
  - 修改 `stock_list.html` 中的"图形报告"按钮
  - 按钮现在指向 `/graph_report?symbol=xxx&name=xxx` 页面
  - 不再依赖静态PNG文件或HTML文件路径

### 技术实现
- **前端技术**：
  - 使用 Plotly.js 绘制饼图和雷达图
  - 使用 Chart.js 绘制柱状图
  - 使用 JavaScript 动态加载数据并渲染图表

- **后端技术**：
  - 从 `stock_predictions` 表获取预测结果
  - 从 `prediction_factors` 表获取各因子得分和权重
  - 从数据源获取30天价格趋势数据
  - 数据已通过 `stock_predictor.py` 的 `predict` 方法自动保存到数据库

### 相关文件
- `smart_stock_advisor/templates/graph_report.html` - 新建图形报告页面
- `smart_stock_advisor/web_app.py` - 新增 `/graph_report` 路由和 `/api/graph_report` API接口
- `smart_stock_advisor/stock_list.html` - 修改图形报告按钮链接

### 数据流程
1. 股票分析时，`stock_predictor.py` 的 `predict` 方法会调用 `self.data_storage.save_prediction_factors` 保存因子数据
2. `prediction_visualizer.py` 的 `save_stock_record` 方法会调用 `db.save_prediction` 保存预测结果
3. 用户点击"图形报告"按钮时，跳转到 `/graph_report` 页面
4. 页面通过 `/api/graph_report` API获取数据并渲染图表

---

## [2026-01-08] - 修复批量分析时线程池错误：cannot schedule new futures after interpreter shutdown

### 问题修复
- ✅ **修复线程池错误**：
  - 问题：批量分析时出现 `RuntimeError: cannot schedule new futures after interpreter shutdown`
  - 原因：在解释器关闭过程中，线程池无法提交新任务
  - 修复：添加解释器关闭检测，如果检测到解释器正在关闭，自动切换到单线程模式

### 技术实现
- **解释器关闭检测**：
  - 在创建线程池前，先尝试创建一个测试线程池
  - 如果捕获到 `RuntimeError: cannot schedule new futures after interpreter shutdown`，切换到单线程模式
  - 在 `with ThreadPoolExecutor` 块中也添加异常处理

- **降级策略**：
  - 如果线程池不可用，自动使用单线程顺序执行所有分析任务
  - 确保分析功能在解释器关闭时仍能正常工作
  - 记录警告日志，但不影响分析结果

### 相关文件
- `smart_stock_advisor/predictor/stock_predictor.py` - 修复 `predict` 方法中的线程池使用逻辑

---

## [2026-01-08] - 检查并修复新闻抓取页面功能和底层逻辑

### 功能优化
- ✅ **完善编辑任务功能**：
  - 实现 `editNewsTask` 函数，支持编辑任务名称、类型、股票代码、抓取间隔
  - 添加编辑模态框，提供友好的编辑界面
  - 运行中的任务不允许编辑配置（只能编辑名称），需要先停止

- ✅ **优化任务启动逻辑**：
  - 检查任务线程状态，避免重复启动
  - 如果数据库状态与线程状态不一致，自动同步
  - 首次执行立即抓取一次，然后按间隔执行

- ✅ **优化任务停止逻辑**：
  - 先更新数据库状态，再发送停止信号
  - 等待线程结束（最多5秒），确保任务完全停止
  - 改进错误处理和日志记录

- ✅ **改进抓取循环逻辑**：
  - 修复 `stop_flag.wait()` 的使用方式，确保正确等待和响应停止信号
  - 首次执行立即抓取，后续按间隔执行
  - 增强日志记录，记录每次抓取的结果统计

- ✅ **改进数据库操作**：
  - 在 `create_task` 中添加事务回滚处理
  - 改进错误处理和连接管理

### 技术改进
- **线程安全**：
  - 检查线程状态避免重复启动
  - 改进停止逻辑，确保线程正确结束

- **错误处理**：
  - 增强异常处理和日志记录
  - 添加详细的错误信息

- **用户体验**：
  - 完善编辑功能，提供完整的任务编辑界面
  - 添加运行状态检查，防止误操作

### 相关文件
- `smart_stock_advisor/utils/news_crawler.py` - 优化抓取循环逻辑和错误处理
- `smart_stock_advisor/utils/news_task_manager.py` - 优化任务启动/停止逻辑，完善更新功能
- `smart_stock_advisor/templates/settings.html` - 实现编辑任务功能

---

## [2026-01-08] - 优化大盘指标显示：收盘后仍显示数据并添加提示

### 功能优化
- ✅ **大盘指标收盘后显示优化**：
  - 收盘后仍然显示最后一次获取的大盘指数数据
  - 在数据后面添加"（已收盘，已停止更新）"提示
  - 不再清空数据，保留最后一次的指数信息供用户查看

### 技术实现
- **后端修改**：
  - 修改 `api_get_market_index` 函数，收盘后仍然返回数据
  - 添加 `market_closed` 和 `message` 字段标识收盘状态
  - 收盘后仍然获取并返回最后一次的指数数据

- **前端修改**：
  - 修改 `updateMarketInfo` 函数，收盘后保留数据
  - 在指数数据后面添加收盘提示信息
  - 停止定时更新，但保留最后一次显示的数据

### 相关文件
- `smart_stock_advisor/web_app.py` - 修改 `api_get_market_index` 函数
- `smart_stock_advisor/stock_list.html` - 修改 `updateMarketInfo` 函数

---

## [2026-01-08] - 股票预测列表只显示当日预测数据

### 功能优化
- ✅ **股票预测列表过滤**：
  - 修改 `/api/stocks` API，只返回当日（`prediction_date = 今天`）的预测数据
  - 过滤掉所有历史预测数据
  - 页面标题改为"股票预测列表（当日）"

### 技术实现
- **日期过滤逻辑**：
  - 在 `api_get_stocks` 函数中添加日期过滤
  - 获取当前日期（`YYYY-MM-DD` 格式）
  - 只保留 `prediction_date` 等于今天的记录
  - 支持 datetime 对象和字符串格式的日期比较

### 相关文件
- `smart_stock_advisor/web_app.py` - 修改 `api_get_stocks` 函数，添加日期过滤
- `smart_stock_advisor/stock_list.html` - 页面标题已更新为"股票预测列表（当日）"

---

## [2026-01-08] - 优化大盘指数显示逻辑：收盘后停止更新并屏蔽中证500错误

### 功能优化
- ✅ **收盘后停止定时获取**：
  - 添加 `is_market_open()` 函数判断A股市场是否开盘
  - A股交易时间：上午 9:30-11:30，下午 13:00-15:00
  - 收盘后API返回 `market_closed: true` 状态
  - 前端检测到收盘状态后自动停止定时更新
  - 显示"已收盘，已停止更新"提示

- ✅ **屏蔽中证500错误**：
  - 注释掉中证500(000905.SH)的获取代码（权限不足）
  - 屏蔽权限相关的错误提示（包括"抱歉，您没有接口访问权限"）
  - 静默跳过中证500的数据获取，不影响其他指数显示

### 技术改进
- **交易时间判断**：
  - 判断是否为交易日（周一到周五）
  - 判断是否在交易时段（排除午休时间）
  - 返回详细的市场状态信息

- **前端优化**：
  - 使用全局变量 `marketInfoInterval` 管理定时器
  - 检测到收盘状态后自动清除定时器
  - 显示友好的收盘提示信息

- **错误处理**：
  - 屏蔽中证500相关的所有错误提示
  - 屏蔽权限相关的错误信息
  - 其他指数的错误正常记录和显示

### 相关文件
- `smart_stock_advisor/web_app.py` - 添加 `is_market_open()` 函数，修改 `api_get_market_index` 函数
- `smart_stock_advisor/stock_list.html` - 修改大盘信息更新逻辑，添加收盘检测

---

## [2026-01-08] - 优化服务启动逻辑：使用Tushare获取大盘指数数据

### 功能优化
- ✅ **优化服务器启动逻辑**：
  - 服务启动时不再获取中国股市大盘数据
  - 只在用户登录后才获取大盘指数数据
  - 减少启动时的资源消耗和网络请求

- ✅ **使用Tushare API获取指数数据**：
  - 修改 `/api/market/index` API，改用Tushare获取指数数据
  - 支持的指数（5个）：
    - 上证指数（000001.SH）
    - 深证成指（399001.SZ）
    - 沪深300（000300.SH）
    - 中证500（000905.SH）
    - 创业板指（399006.SZ）
  - 优先使用Tushare获取最新交易日数据
  - 如果Tushare失败，回退到akshare作为备用方案

- ✅ **登录状态检查**：
  - `api_get_market_index` API添加登录检查，未登录用户无法获取数据
  - `stock_list.html` 修改为只在登录后才更新大盘信息
  - 未登录时显示"请先登录查看大盘信息"提示

### 技术改进
- **添加pandas导入**：在 `web_app.py` 中添加 `import pandas as pd` 用于处理Tushare返回的DataFrame数据
- **错误处理**：增强Tushare API调用的错误处理和日志记录
- **数据获取逻辑**：
  - 优先获取当天交易数据
  - 如果当天无数据（非交易日），自动获取最近交易日数据
  - 计算涨跌幅时使用前一个交易日数据作为对比

### 相关文件
- `smart_stock_advisor/web_app.py` - 修改 `api_get_market_index` 函数
- `smart_stock_advisor/stock_list.html` - 修改大盘信息更新逻辑

---

## [2026-01-08] - 服务启动时数据存储模式说明文档

### 文档新增
- ✅ **创建服务启动时数据存储模式说明文档**：
  - 详细说明 `py web_app.py` 启动时数据存储模块的初始化过程
  - 说明延迟初始化（Lazy Initialization）机制
  - 明确启动时**不会**执行的操作（不连接数据库、不创建表、不运行任务）
  - 说明数据库连接的实际创建时机（首次使用时）
  - 说明当前数据存储模式：数据库模式（`USE_DATABASE = True`）
  - 相关文档：`服务启动时数据存储模式说明.md`

### 关键发现
- **启动时行为**：只读取配置和导入模块，不执行任何数据库操作
- **连接创建时机**：使用延迟初始化，首次访问数据库功能时才会创建连接
- **存储模式**：当前使用数据库模式，所有数据存储在MySQL数据库
- **自动任务**：服务启动时不会自动运行任何分析或抓取任务

---

## [2026-01-08] - 修复股票列表页面日期显示格式

### 用户体验优化
- ✅ **修复日期显示格式**：
  - 在 `stock_list.html` 中添加 `formatDateToChinese()` 函数
  - 将日期格式从英文格式（"2026-01-08"）转换为中文格式（"2026年1月8日"）
  - 优化了 `prediction_date` 和 `target_date` 的显示格式，更符合中文用户习惯

---

## [2026-01-08] - 修复批量股票分析数据保存问题

### Bug修复
- ✅ **修复批量分析任务数据保存不完整问题**：
  - 在`predict`方法的返回结果中添加`name`字段（股票名称）
  - 在`predict`方法的返回结果中添加`prediction_date`字段（预测日期，当前日期）
  - 修改`predict`方法，自动从股票列表或股票信息中获取股票名称
  - 在批量分析任务中，如果`result`中没有`name`，从`stock_info`中获取并补充
  - 确保数据库保存时包含完整的股票信息（name、prediction_date、target_date等）

### 技术细节
- **股票名称获取**：优先从股票列表中匹配，如果失败则从`get_stock_info`获取
- **预测日期**：使用当前日期（`datetime.now().strftime('%Y-%m-%d')`）
- **兼容性**：如果获取名称失败，使用默认值'未知'，确保程序不会崩溃

---

## [2026-01-08] - 批量股票分析定时任务检查

### 检查结果
- ✅ **确认：批量股票分析中没有定时任务**
- 股票分析任务是一次性执行任务，完成后立即结束
- 没有循环、定时器或调度逻辑
- 任务必须通过Web界面手动启动
- 详细检查报告见：`批量股票分析定时任务检查报告.md`

### 对比说明
- **新闻抓取任务**：有定时任务功能（使用 `while` 循环 + `time.sleep`）
- **股票分析任务**：无定时任务功能（一次性执行）

### 如需定时任务
如需定时执行批量股票分析，建议：
1. 使用外部调度器（Cron/任务计划程序）定时调用API
2. 或参考新闻抓取任务实现，添加定时循环逻辑
3. 或集成 Celery + Redis 实现分布式任务队列

---

## [2026-01-08] - 股票分析多线程优化与数据库存储迁移

### 重大优化
- ✅ **多线程并行分析优化**：
  - 修改`web_app.py`中的`run_stock_analysis_task`函数，支持多线程并行分析多个股票
  - 使用`ThreadPoolExecutor`实现多个股票同时分析，不再顺序执行
  - 每个线程创建独立的实例（`StockPredictor`、`PredictionVisualizer`），避免资源竞争
  - 支持通过`BATCH_ANALYSIS_CONFIG`配置并发数（`max_workers`，默认3）
  - 保持单线程模式作为备选（可通过配置禁用并行）
  - 指标分析已在`stock_predictor.py`内部使用两阶段并行（6个独立任务 + 3个依赖任务）

- ✅ **移除文件生成逻辑**：
  - `visualize_no_display_v2`：不再生成PNG图片和HTML报告文件，返回空字典
  - `save_stock_record`：移除所有CSV/Excel保存逻辑，只保留数据库保存
  - `create_stock_list_page`：不再生成HTML页面，返回空结果（前端通过API动态获取）
  - `create_stock_history_page`：不再生成HTML页面，返回None（前端通过API动态获取）
  - `_update_historical_actual_data`：改为从数据库读取和更新，移除CSV文件操作

- ✅ **数据库存储优化**：
  - 所有预测数据只保存到MySQL数据库，不再保存CSV/Excel文件
  - 所有图表和报告数据存储在数据库中，不再生成PNG/HTML文件
  - 前端通过API从数据库动态获取数据并渲染
  - 历史实际数据更新逻辑改为从数据库读取和更新

### 技术细节
- **多线程实现**：使用`concurrent.futures.ThreadPoolExecutor`和`as_completed`实现并行执行和实时监控
- **线程安全**：使用`threading.Lock`保护共享状态（进度、计数等）
- **错误处理**：每个线程独立处理异常，不影响其他线程
- **停止机制**：支持通过`stop_event`优雅停止正在运行的任务
- **实时进度**：使用WebSocket实时推送每个线程的进度更新

### 性能提升
- **多股票并行分析**：理论上可提升N倍速度（N为并发数，默认3）
- **指标并行分析**：在`stock_predictor.py`内部已实现，多个指标同时计算
- **数据实时保存**：每个股票分析完成后立即保存到数据库，不需要等待全部完成

### 代码变更
- `smart_stock_advisor/web_app.py`：重构`run_stock_analysis_task`函数，添加多线程支持
- `smart_stock_advisor/visualizer/prediction_visualizer.py`：
  - `visualize_no_display_v2`：移除文件生成逻辑
  - `save_stock_record`：移除CSV保存逻辑，只保留数据库保存
  - `create_stock_list_page`：移除HTML生成逻辑
  - `create_stock_history_page`：移除HTML生成逻辑
  - `_update_historical_actual_data`：改为从数据库读取和更新

### 注意事项
- 所有数据现在必须保存到数据库，不再支持CSV文件
- 前端页面通过API动态获取数据，不再依赖静态HTML文件
- 确保`USE_DATABASE=True`且数据库连接正常
- 并发数可根据服务器性能调整（`BATCH_ANALYSIS_CONFIG['max_workers']`）

### Bug修复
- ✅ **修复 analysis_tasks 表不存在错误**：
  - 在`api_get_task_history`函数中添加表存在性检查
  - 如果表不存在，自动创建`analysis_tasks`表
  - 自动创建逻辑会在首次访问任务历史时执行
  - 确保表结构和索引正确创建
  - 创建了独立脚本`database/create_analysis_tasks_table.py`用于手动创建表
  - 如果自动创建失败，可以运行`python database/create_analysis_tasks_table.py`手动创建

- ✅ **修复开始分析时登录验证错误**：
  - 优化`check_session`函数，添加异常处理机制
  - 对于API请求（`/api/*`），返回JSON错误响应而不是重定向到登录页
  - 对于页面请求，重定向到登录页
  - 如果数据库验证出错（如表不存在、数据库连接失败等），记录错误但不清除session，避免因数据库问题导致所有用户被踢出
  - 优化`validate_session`函数的错误处理，详细记录错误信息（包括表不存在的情况）
  - 排除不需要验证的端点（login、static、favicon）
  - 添加traceback导入，确保错误堆栈信息完整记录

## [2026-01-08] - 股票分析任务按钮状态优化

### 功能增强
- ✅ **中止任务按钮优化**：
  - 将"停止任务"按钮改名为"中止任务"，更加明确操作意图
  - 任务开始执行时自动显示"中止任务"按钮
  - 任务运行中（status === 'running'）时确保"中止任务"按钮可用
  - 任务完成、取消或失败时自动隐藏"中止任务"按钮
  - 点击"中止任务"时禁用按钮，显示"中止中..."，防止重复点击

- ✅ **开始分析按钮防重复提交**：
  - 点击"开始分析"后立即禁用按钮，防止重复提交
  - 在函数开始时检查按钮状态，如果已禁用则提示用户
  - 检查是否有正在运行的任务，如有则提示用户先中止
  - 任务启动失败或异常时自动恢复按钮状态

- ✅ **按钮状态统一管理**：
  - 在`updateTaskProgress`函数中根据任务状态统一管理按钮状态
  - 任务运行中：禁用"开始分析"，显示并启用"中止任务"
  - 任务完成/取消/失败：启用"开始分析"，隐藏"中止任务"
  - 添加按钮禁用时的视觉反馈（透明度降低、鼠标样式变化）

## [2026-01-08] - 任务管理功能增强与后台日志优化

### 重大更新
- ✅ **任务停止功能**：
  - 添加停止任务按钮，可以中断正在执行的分析任务
  - 在分析循环中添加停止标志检查，支持安全停止
  - 任务停止后自动保存任务历史记录（状态为"已取消"）

- ✅ **实时数据保存**：
  - 每个股票分析完成后立即保存到数据库，不需要等待全部完成
  - 优化数据保存逻辑，确保数据实时性

- ✅ **按钮状态控制**：
  - 点击"开始分析"后，按钮自动禁用，防止重复提交
  - 任务完成、取消或失败后，按钮自动恢复可用状态
  - 添加"停止任务"按钮，任务运行时显示

- ✅ **实时状态刷新**：
  - 使用WebSocket和定时轮询双重机制，实时更新任务进度
  - 任务完成后自动刷新任务历史列表

- ✅ **任务历史记录**：
  - 创建 `analysis_tasks` 表，存储任务执行记录
  - 记录任务ID、执行人、分析数量、排序方式、状态、成功/失败数量、开始/结束时间、耗时等信息
  - 在设置页面任务管理下方以表格形式显示任务历史列表
  - 支持刷新列表功能

- ✅ **后台日志增强**：
  - 在分析任务的关键步骤添加详细日志输出
  - 记录任务启动信息（任务ID、分析数量、排序方式、启动时间）
  - 记录每只股票的分析进度、预测结果、文件生成、保存状态
  - 记录任务完成信息（总股票数、成功率、耗时）
  - 记录所有错误和异常的详细信息（包含traceback）
  - 使用统一的分隔符和标签格式，便于日志查看和分析

- ✅ **股票分析任务优化**：
  - 合并"开始全量分析"和"分析部分股票"为一个"开始分析"按钮
  - 调整分析数量范围：0-10000（0表示分析全部股票）
  - 添加排序方式选择：按当天交易量排序（从高到低）或随机排序
  - 优化任务详情显示，显示分析数量和排序方式

- ✅ **数据源排序功能增强**：
  - `get_all_stock_list` 方法新增 `random_sort` 参数支持随机排序
  - 优化按交易量排序逻辑，直接在DataFrame层面排序，提高性能
  - 随机排序使用 `random.shuffle()` 打乱列表

- ✅ **分析代码错误处理优化**：
  - 增强错误处理，即使可视化失败也尝试保存基本预测数据
  - 添加更详细的错误日志，包括traceback信息
  - 每只股票分析后自动生成历史页面
  - 改进任务完成时的股票列表页面更新逻辑

### 技术细节
- 前端：修改 `startAnalysis()` 函数，统一处理分析任务启动
- 后端：修改 `api_start_task()` 和 `run_stock_analysis_task()` 函数，支持新的参数结构
- 数据源：优化排序逻辑，先排序DataFrame再构建记录，提高性能

---

## [2026-01-08] - 用户管理功能

### 重大更新
- ✅ **用户管理数据库设计**：
  - 创建 `users` 表，存储用户信息（用户名、密码哈希、角色、邮箱等）
  - 创建 `user_sessions` 表，存储用户登录会话信息
  - 支持用户激活/禁用状态管理
  - 记录最后登录时间和IP地址

- ✅ **用户管理模块**：
  - 创建 `utils/user_manager.py` 模块
  - 实现用户CRUD操作（创建、查询、更新、删除）
  - 实现密码验证和哈希存储
  - 实现会话管理功能

- ✅ **单点登录（SSO）实现**：
  - 一个账户只能在一个地方登录
  - 新登录会自动使旧会话失效
  - 通过 `@app.before_request` 装饰器验证每个请求的会话有效性
  - 会话失效后自动重定向到登录页

- ✅ **Web应用集成**：
  - 修改 `web_app.py`，使用数据库用户管理替代硬编码用户字典
  - 实现用户登录时创建会话
  - 实现用户退出时使会话失效
  - 如果数据库未启用，自动回退到内存用户字典

- ✅ **用户管理API接口**：
  - `GET /api/users` - 获取用户列表（仅管理员）
  - `POST /api/users` - 创建新用户（仅管理员）
  - `PUT /api/users/<id>` - 更新用户信息（仅管理员）
  - `DELETE /api/users/<id>` - 删除用户（仅管理员，不能删除自己）

- ✅ **设置页面用户管理界面**：
  - 在设置页面添加"用户管理"标签页
  - 显示用户列表（用户名、角色、邮箱、状态、最后登录时间）
  - 支持添加新用户（用户名、密码、角色、邮箱）
  - 支持编辑用户（修改密码、角色、邮箱、激活状态）
  - 支持删除用户（软删除，设置为非激活状态）
  - 防止删除最后一个管理员账户

- ✅ **数据库初始化**：
  - 更新 `database/init_database.py`，自动包含用户表SQL脚本
  - 创建 `database/user_tables.sql`，包含用户表和会话表定义
  - 首次启动时自动创建默认admin用户（如果不存在）

### 技术细节
- 使用 `werkzeug.security` 进行密码哈希存储
- 使用 `secrets.token_urlsafe()` 生成唯一的会话ID
- 会话表通过外键关联用户表，支持级联删除
- 实现会话过期清理功能（可配置过期时间）

### 使用说明
1. **初始化数据库**：
   ```bash
   py database/init_database.py
   ```
   会自动创建用户表和会话表，并创建默认admin用户（用户名：admin，密码：admin123）

2. **用户管理**：
   - 登录系统后，进入"设置"页面
   - 点击"用户管理"标签页
   - 管理员可以添加、编辑、删除用户

3. **单点登录**：
   - 如果用户在其他地方登录，当前会话会自动失效
   - 需要重新登录才能继续使用

---

## [2026-01-08] - 新闻模块优化

### 重大更新
- ✅ **新闻数据库表设计**：
  - 创建 `news_articles` 表，存储详细的新闻文章信息
  - 创建 `news_crawl_tasks` 表，存储新闻抓取任务信息
  - 包含标题、内容、时间、抓取地址、板块、行业、领域等详细信息
  - 支持情感分析结果存储（利好/利空标记）

- ✅ **新闻存储模块**：
  - 创建 `utils/news_storage.py` 模块
  - 自动进行情感分析并标记利好/利空
  - 支持批量保存新闻
  - 支持查询和统计功能

- ✅ **定时任务系统**：
  - 创建 `utils/news_crawler.py` 新闻抓取模块
  - 创建 `utils/news_task_manager.py` 任务管理模块
  - 支持创建、启动、停止、删除新闻抓取任务
  - 支持设置抓取间隔（分钟）
  - 任务状态持久化到数据库

- ✅ **设置页面集成**：
  - 在设置页面添加"新闻抓取"标签页
  - 支持创建新闻抓取任务
  - 支持启动/停止任务
  - 显示任务运行统计信息

### 新增功能

1. **新闻文章表（news_articles）**：
   - 存储新闻标题、内容、时间、来源、URL等详细信息
   - 关联股票代码、板块、行业、概念
   - 存储情感分析结果（sentiment、sentiment_score、is_positive、is_negative）
   - 支持重复新闻检测（基于标题和来源的唯一索引）

2. **新闻抓取任务表（news_crawl_tasks）**：
   - 存储任务配置（名称、类型、间隔、股票代码等）
   - 记录任务运行状态（运行次数、成功次数、失败次数）
   - 记录最后运行时间和下次运行时间
   - 记录错误信息

3. **新闻存储功能**：
   - `save_news_article()`: 保存单条新闻，自动进行情感分析
   - `save_news_batch()`: 批量保存新闻
   - `get_news_by_symbol()`: 获取股票相关新闻
   - `get_news_statistics()`: 获取新闻统计信息

4. **新闻抓取功能**：
   - `crawl_market_news()`: 抓取市场新闻
   - `crawl_stock_news()`: 抓取股票新闻
   - 自动关联股票行业信息（板块、行业）

5. **定时任务管理**：
   - 创建任务：设置任务名称、类型、间隔、股票代码
   - 启动任务：开始定时抓取
   - 停止任务：停止定时抓取
   - 删除任务：删除任务配置
   - 查看统计：运行次数、成功/失败统计

6. **API接口**：
   - `GET /api/news/tasks` - 获取所有任务
   - `POST /api/news/tasks` - 创建任务
   - `GET /api/news/tasks/<id>` - 获取任务信息
   - `PUT /api/news/tasks/<id>` - 更新任务
   - `DELETE /api/news/tasks/<id>` - 删除任务
   - `POST /api/news/tasks/<id>/start` - 启动任务
   - `POST /api/news/tasks/<id>/stop` - 停止任务
   - `GET /api/news/articles` - 获取新闻文章
   - `GET /api/news/statistics` - 获取统计信息

### 新增文件

- **`database/news_table.sql`**：新闻表SQL脚本
- **`utils/news_storage.py`**：新闻存储模块
- **`utils/news_crawler.py`**：新闻抓取模块
- **`utils/news_task_manager.py`**：任务管理模块
- **`新闻模块优化说明.md`**：详细使用说明

### 修改文件

- **`database/init_database.py`**：自动包含新闻表SQL脚本
- **`web_app.py`**：添加新闻任务管理API接口
- **`templates/settings.html`**：添加"新闻抓取"标签页和任务管理界面

### 使用方式

1. **初始化数据库**：
   ```bash
   py database/init_database.py
   ```

2. **创建抓取任务**：
   - 访问设置页面：http://localhost:5000/settings
   - 点击"新闻抓取"标签页
   - 点击"创建新任务"
   - 填写任务信息并创建
   - 点击"启动"按钮开始抓取

3. **查看抓取结果**：
   - 任务列表显示运行统计
   - 通过API查询新闻文章

### 技术细节

- **定时任务实现**：使用Python `threading` 模块，每个任务独立线程
- **情感分析**：集成现有的 `NewsSentimentAnalyzer`，自动分析并标记
- **重复检测**：基于标题和来源的唯一索引
- **任务持久化**：任务状态保存到数据库，重启后可通过API恢复

---

## [2026-01-08] - Web应用化改造

### 重大更新
- ✅ **Web应用化改造**：
  - 从命令行工具改造为完整的Web应用
  - 通过浏览器访问，提供友好的用户界面
  - 支持用户登录/退出功能
  - 主入口为 `stock_list.html` 页面

### 新增功能

1. **用户认证系统**：
   - 新增用户登录页面（`templates/login.html`）
   - 简单的Session认证机制
   - 默认账号：`admin` / `admin123`
   - 支持用户退出登录功能

2. **导航栏和设置功能**：
   - 在所有页面顶部添加导航栏
   - 导航栏包含：系统标题、设置按钮、退出按钮
   - 设置按钮点击进入设置页面

3. **设置页面**（`templates/settings.html`）：
   - 菜单栏设计（任务管理、参数设置）
   - **任务管理功能**：
     - 支持启动全量股票分析任务
     - 支持启动部分股票分析任务（可设置数量）
     - 实时显示任务进度（进度条、成功数、失败数）
     - 显示当前正在分析的股票
     - 使用WebSocket实时推送任务状态更新
   
4. **主页面实时大盘信息显示**：
   - 在主页面（`stock_list.html`）顶部添加大盘信息栏
   - 显示主要指数：上证指数、深证成指、创业板指
   - 实时显示：当前点位、涨跌额、涨跌幅
   - 每秒自动刷新一次（局部刷新，不刷新整个页面）
   - 涨跌颜色区分（红色上涨、绿色下跌）

5. **个股预测图表HTML化**：
   - 优先使用HTML交互式图表（Plotly）替代PNG静态图片
   - 支持鼠标悬停查看详细信息
   - 支持缩放、平移等交互操作
   - 如果HTML图表不存在，自动回退到PNG图片

### 新增文件

- **`web_app.py`**：Flask Web应用主文件
  - 路由处理：登录、股票列表、设置、API接口
  - WebSocket支持：实时任务状态推送
  - 后台任务管理：股票分析任务队列和执行

- **`templates/login.html`**：用户登录页面
- **`templates/settings.html`**：系统设置页面
- **`static/common.css`**：通用样式文件
- **`start_web.bat`**：Windows启动脚本
- **`start_web.sh`**：Linux/Mac启动脚本

### API接口

新增RESTful API接口：
- `GET /api/stocks` - 获取股票列表
- `GET /api/market/index` - 获取大盘指数实时数据
- `POST /api/tasks/start` - 启动分析任务
- `GET /api/tasks/<task_id>` - 获取任务状态
- `GET /api/tasks` - 获取所有任务列表

### WebSocket事件

- `task_started` - 任务启动
- `task_progress` - 任务进度更新
- `task_completed` - 任务完成

### 使用方式

1. **启动Web应用**：
   ```bash
   # Windows
   start_web.bat
   
   # Linux/Mac
   chmod +x start_web.sh
   ./start_web.sh
   
   # 或直接运行
   py web_app.py
   ```

2. **访问应用**：
   - 浏览器打开：http://localhost:5000
   - 默认账号：`admin` / `admin123`

3. **功能使用**：
   - 登录后进入股票列表页面
   - 点击导航栏"设置"按钮进入设置页面
   - 在设置页面可以启动股票分析任务
   - 主页面顶部实时显示大盘信息

### 技术实现

- **Web框架**：Flask + Flask-SocketIO
- **前端技术**：HTML + CSS + JavaScript
- **实时通信**：WebSocket（Socket.IO）
- **图表库**：Plotly（交互式HTML图表）
- **认证方式**：Session-based认证（简单实现）

### 依赖更新

新增依赖包（已添加到 `requirements.txt`）：
- `flask>=2.3.0`
- `flask-socketio>=5.3.0`
- `werkzeug>=2.3.0`

### 优势

- **用户体验**：友好的Web界面，无需命令行操作
- **实时性**：大盘信息实时更新，任务进度实时推送
- **交互性**：HTML交互式图表，支持多种交互操作
- **可扩展性**：易于添加新的功能和页面

---

## [2026-01-08] - 数据存储迁移到MySQL数据库

### 功能重大更新
- ✅ **数据库支持**：
  - 所有数据存储从CSV文件迁移到MySQL数据库
  - 数据库配置：本地MySQL，库名 `stock_data`，端口3307
  - 支持自动回退：如果数据库不可用，自动回退到CSV模式
  - 配置项：`config_db.py` 中的 `USE_DATABASE` 控制是否启用数据库

### 新增文件
- ✅ **`config_db.py`**：数据库配置文件
  - 包含MySQL连接配置（host, port, user, password, database）
  - `USE_DATABASE` 开关控制是否启用数据库
  
- ✅ **`utils/db_connection.py`**：数据库连接管理模块
  - 线程安全的数据库连接管理（每个线程一个连接）
  - 自动重连机制
  - 支持查询、更新、批量操作、事务操作
  
- ✅ **`utils/db_storage.py`**：数据库存储模块
  - 实现所有数据类型的数据库保存方法
  - 支持INSERT ... ON DUPLICATE KEY UPDATE（更新已存在记录）
  
- ✅ **`utils/stock_prediction_db.py`**：股票预测记录数据库访问模块
  - 提供预测记录的保存、更新、查询方法
  - 支持获取最新预测、单个股票历史等查询

- ✅ **`database/init_database.sql`**：数据库初始化SQL脚本
  - 包含所有11个数据表的CREATE TABLE语句
  - 定义完整的表结构、索引、唯一键

- ✅ **`database/init_database.py`**：数据库初始化Python脚本
  - 自动执行SQL脚本创建所有表
  - 使用方法：`py database/init_database.py`

- ✅ **`database/migrate_csv_to_db.py`**：CSV数据迁移脚本
  - 将现有CSV数据迁移到数据库
  - 使用方法：`py database/migrate_csv_to_db.py`

### 数据库表结构
创建了11个数据表：
1. **stock_predictions** - 股票预测结果表
2. **north_bound_capital** - 北向资金数据表
3. **margin_trading** - 融资融券数据表
4. **main_force_capital** - 主力资金数据表
5. **sector_rotation** - 板块轮动数据表
6. **technical_indicators** - 技术指标数据表
7. **news_sentiment** - 新闻情感数据表
8. **market_sentiment** - 市场情绪数据表
9. **prediction_factors** - 预测因子数据表
10. **cost_distribution** - 成本分布数据表
11. **realtime_trading_decisions** - 实时交易决策数据表

### 代码修改
- ✅ **`utils/data_storage.py`**：
  - 修改所有 `save_*` 方法，优先使用数据库，失败时回退到CSV
  - 保持向后兼容，不影响现有功能

- ✅ **`visualizer/prediction_visualizer.py`**：
  - `save_stock_record()` 方法支持数据库保存
  - `create_stock_list_page()` 方法从数据库读取数据
  - `create_stock_history_page()` 方法从数据库读取数据
  - `_update_historical_actual_data()` 方法支持数据库更新

- ✅ **`api_server.py`**：
  - `handle_get_stocks()` 方法从数据库读取数据
  - `handle_get_stock()` 方法从数据库读取数据

- ✅ **`predictor/stock_predictor.py`**：
  - 修改 `save_prediction_factors()` 调用，传递 `prediction_result` 参数

### 使用说明
1. **初始化数据库**：
   ```bash
   # 1. 确保MySQL服务已启动，数据库stock_data已创建
   # 2. 修改 config_db.py 中的数据库配置（如果需要）
   # 3. 运行初始化脚本创建所有表
   py database/init_database.py
   ```

2. **启用数据库**：
   - 在 `config_db.py` 中设置 `USE_DATABASE = True`
   - 如果设置为 `False`，系统会回退到CSV模式

3. **迁移现有数据**（可选）：
   ```bash
   py database/migrate_csv_to_db.py
   ```

### 优势
- **性能**：数据库查询比CSV读取快很多
- **并发**：支持多线程并发访问
- **数据完整性**：数据库约束保证数据一致性
- **查询能力**：支持复杂SQL查询和数据分析
- **扩展性**：易于添加新的查询和分析功能
- **备份**：数据库备份比文件备份更方便

### 兼容性
- 如果数据库不可用或未启用，系统会自动回退到CSV模式
- 所有CSV文件仍然保留，可以随时切换回CSV模式
- 数据迁移是可选的，不影响现有功能

---

## [2026-01-08] - 股票列表页面改为动态加载数据

### 功能改进
- ✅ **股票列表页面改为动态加载数据**：
  - 之前：`stock_list.html` 是静态生成的，所有股票数据都嵌入在HTML中，需要重新生成HTML才能看到最新数据
  - 现在：`stock_list.html` 通过JavaScript动态从API获取数据，无需重新生成HTML即可看到最新数据
  - 页面加载时自动从API获取最新数据
  - 支持自动刷新（每30秒刷新一次）
  - 如果API服务器未运行，会自动使用备用静态数据

- ✅ **新增API服务器**：
  - 创建 `api_server.py`，提供RESTful API接口
  - API端点：`GET /api/stocks` - 获取所有股票预测数据
  - API端点：`GET /api/stock?symbol=xxx` - 获取单个股票数据
  - 支持CORS，允许跨域访问
  - 支持静态文件服务（HTML、CSS、JS等）

### 使用方式
1. **启动API服务器**：
   ```bash
   py api_server.py
   ```
   - 默认端口：8888
   - 访问地址：http://localhost:8888/stock_list.html
   - API地址：http://localhost:8888/api/stocks

2. **在浏览器中打开**：
   - 通过API服务器访问：http://localhost:8888/stock_list.html（推荐，数据实时更新）
   - 或直接打开文件：`stock_list.html`（会使用备用静态数据）

### 技术实现
- `api_server.py`：
  - 使用Python内置的 `http.server` 模块
  - 读取 `stock_predictions.csv` 并转换为JSON返回
  - 提供静态文件服务
  - 支持CORS头，允许跨域请求

- `visualizer/prediction_visualizer.py`：
  - 修改 `_generate_stock_list_html()` 方法
  - 不再在HTML中嵌入所有股票数据
  - 添加JavaScript代码，通过 `fetch` API动态加载数据
  - 添加加载指示器和错误提示
  - 保留静态数据作为备用（如果API不可用）

### 优势
- **实时性**：数据始终是最新的，无需重新生成HTML
- **性能**：HTML文件更小，加载更快
- **灵活性**：可以随时更新CSV，页面自动显示最新数据
- **兼容性**：如果API服务器未运行，仍可使用静态数据

### 文件变更
- 新增 `api_server.py`：API服务器脚本
- 修改 `visualizer/prediction_visualizer.py`：改为动态加载数据

---

## [2026-01-08] - 实时监控功能增强

### 功能新增
- ✅ **股票列表页面集成实时监控入口**：
  - 在 `stock_list.html` 中，每个股票行新增"🔴 实时监控"按钮
  - 点击按钮弹出设置对话框，可配置监控参数
  - 支持设置持仓成本、刷新间隔等关键参数

- ✅ **监控设置模态框**：
  - 提供友好的UI界面设置监控参数
  - 可设置参数：
    - **持仓成本价**：如果已持有该股票，可输入买入成本价（用于计算盈亏）
    - **刷新间隔**：支持 10秒/30秒/60秒/120秒/300秒 五种刷新频率（默认30秒）
    - **是否持有**：通过复选框控制是否已持有该股票
  - 模态框包含确认和取消按钮，操作简单直观

- ✅ **实时监控页面**：
  - 新增 `PredictionVisualizer.create_realtime_monitor_page()` 方法
  - 生成专用监控页面：`reports/monitor_{symbol}.html`
  - 页面包含完整的实时数据展示区域：
    - 📊 实时行情数据（当前价格、涨跌幅、开高低收、换手率、振幅等）
    - 💰 实时资金流向（主力净流入、总净流入、资金趋势）
    - 🎯 实时交易决策（操作建议、决策理由、价格建议、仓位建议、风险警告）
    - 💼 持仓信息（如已设置持仓成本，显示盈亏情况）
  - 页面自动刷新功能（根据设置的间隔自动刷新）
  - 显示刷新倒计时和最后更新时间

- ✅ **JavaScript交互功能**：
  - 实现模态框的显示/隐藏逻辑
  - 从URL参数读取监控设置
  - 页面跳转和参数传递
  - 倒计时显示功能

### 监控模式集成优化
- ✅ **监控模式HTML生成**：
  - 监控模式启动时自动生成初始监控页面
  - 每次数据更新时覆盖同一个HTML文件（固定文件名：`monitor_{symbol}.html`）
  - 页面根据设置的间隔自动刷新，确保数据实时性
  - 在日志中输出HTML文件路径，方便用户打开

- ✅ **用户体验优化**：
  - 监控页面包含详细的使用说明
  - 显示启动监控服务的完整命令（包含所有参数）
  - 如果监控服务未启动，页面会显示友好的提示信息
  - 返回股票列表的快捷链接

### 代码变更
- `visualizer/prediction_visualizer.py`：
  - 新增 `create_realtime_monitor_page()` 方法：生成实时监控页面HTML
  - 修改 `_generate_stock_list_html()` 方法：
    - 为每个股票添加"实时监控"按钮
    - 添加监控设置模态框的HTML和CSS样式
    - 添加JavaScript代码处理按钮点击、模态框交互和页面跳转
  - 优化模态框样式，提供现代化的UI设计

- `predictor/realtime_trading_advisor.py`：
  - 优化 `monitor_realtime()` 方法：
    - 在监控启动时生成初始监控页面
    - 每次更新时覆盖同一个HTML文件
    - 在日志中输出HTML文件路径，方便用户打开
    - 增强错误处理和日志输出

### 使用流程
1. 打开 `stock_list.html` 股票列表页面
2. 点击任意股票的"🔴 实时监控"按钮
3. 在弹出对话框中设置监控参数：
   - 选择刷新间隔（建议30-60秒）
   - 如果已持有，勾选"我已持有该股票"并输入成本价
4. 点击"开始监控"按钮
5. 系统跳转到实时监控页面：`reports/monitor_{symbol}.html`
6. 按照页面提示，在命令行运行监控命令：
   ```bash
   py main.py --monitor --symbol {symbol} --interval {interval} [--holding --cost {cost}]
   ```
7. 监控服务启动后，HTML页面会自动刷新并显示最新实时数据

### 技术特点
- **固定文件名策略**：监控页面使用固定文件名，每次更新覆盖同一个文件，避免产生大量文件
- **自动刷新机制**：使用HTML `<meta http-equiv="refresh">` 标签实现自动刷新
- **参数传递**：通过URL参数传递监控设置，确保页面显示正确的配置信息
- **用户友好**：提供清晰的提示信息和操作指引，降低使用门槛

### 文件变更清单
- `visualizer/prediction_visualizer.py`：
  - 新增 `create_realtime_monitor_page()` 方法（约150行）
  - 修改 `_generate_stock_list_html()` 方法（添加按钮、模态框、JavaScript）
- `predictor/realtime_trading_advisor.py`：
  - 优化 `monitor_realtime()` 方法（初始页面生成、日志优化）

---

## [2026-01-07] - 批量分析多线程优化

### 性能优化
- ✅ **批量分析支持多线程并行模式**：
  - 可以同时分析多个股票，大幅提升批量分析效率
  - 在 `config.py` 中可自由设置同时分析的股票数量（`BATCH_ANALYSIS_CONFIG.max_workers`）
  - 默认配置：同时分析 3 只股票（可根据网络和API限制调整）
  - **预期性能提升：约 2-3 倍**（取决于并发数和网络I/O时间）

### 新增配置
- ✅ **批量分析配置项**（`config.py`）：
  - `BATCH_ANALYSIS_CONFIG.max_workers`: 同时分析的股票数量（默认 3）
    - 建议值：3-5（取决于网络和API限制）
    - 如果API有频率限制，建议设置为较小值
    - 如果网络和服务器性能好，可以设置更大值（如 5-10）
  - `BATCH_ANALYSIS_CONFIG.enable_parallel`: 是否启用多线程并行分析（默认 True）
    - 设置为 `False` 可切换回单线程顺序分析模式

### 技术改进
- `main.py` 批量分析逻辑重构：
  - 创建 `analyze_single_stock()` 函数处理单只股票分析
  - 使用 `ThreadPoolExecutor` 实现多线程并行分析
  - 每个线程使用独立的预测器实例（`StockPredictor`、`PredictionVisualizer`、`StockDataSource`），避免线程竞争
  - 使用线程安全计数器（`threading.Lock`）统计成功数、失败数、完成数
  - 使用锁保护共享资源（如 `stock_list.html` 更新），避免并发写入冲突

### 线程安全
- ✅ **线程安全保证**：
  - 每个线程创建独立的预测器实例，避免资源竞争
  - 使用 `threading.Lock` 保护共享计数器（成功数、失败数、完成数）
  - 使用锁保护 `stock_list.html` 更新操作，确保同一时间只有一个线程更新页面
  - 异常处理确保单个线程失败不影响其他线程

### 进度显示优化
- ✅ **多线程环境下的进度显示**：
  - 实时显示当前进度、成功数、失败数
  - 每个线程完成时立即更新进度信息
  - 进度信息包含：`[进度: 已完成数/总数] (百分比%) | 成功: x | 失败: y`

### 代码变更
- `config.py`：
  - 新增 `BATCH_ANALYSIS_CONFIG` 配置项
  - 支持配置并发数和是否启用并行模式
- `main.py`：
  - 导入 `concurrent.futures.ThreadPoolExecutor`、`as_completed` 和 `threading`
  - 导入 `BATCH_ANALYSIS_CONFIG` 配置
  - 重构批量分析逻辑，支持多线程并行和单线程顺序两种模式
  - 创建 `analyze_single_stock()` 函数，封装单只股票的分析逻辑
  - 使用线程安全计数器和锁保护共享资源

### 使用说明
- **配置方式**（在 `config.py` 中修改）：
  ```python
  BATCH_ANALYSIS_CONFIG = {
      "max_workers": 3,        # 同时分析的股票数量（建议 3-5）
      "enable_parallel": True, # 是否启用多线程并行分析
  }
  ```
- **运行方式**：
  - 多线程并行分析：`py main.py --all --limit 50`（默认，同时分析3只股票）
  - 如需修改并发数，在 `config.py` 中调整 `max_workers`
  - 如需禁用多线程，设置 `enable_parallel: False`

### 性能对比
- **单线程模式**：总时间 = 各股票分析时间之和
- **多线程模式（3并发）**：总时间 ≈ 最慢股票分析时间 × (总股票数 / 3)
- **实际性能提升**：取决于网络I/O和API响应时间，通常在 2-3 倍左右

---

## [2026-01-07] - 多线程并行分析优化

### 性能优化
- ✅ **多线程并行分析多个指标**：
  - 使用 `ThreadPoolExecutor` 实现并行分析，大幅提升单只股票分析效率
  - 第一阶段：并行执行 6 个独立分析任务（不依赖股票历史数据）：
    - 市场整体行情分析
    - 新闻情感分析
    - 资金流向分析
    - 估值指标分析（PE/PB）
    - 美股板块分析
    - 板块轮动分析
  - 第二阶段：并行执行 3 个依赖股票数据的分析任务：
    - 技术指标分析
    - 市场情绪分析
    - 历史模式分析
  - **预期性能提升：约 3-5 倍**（取决于网络 I/O 和 API 响应时间）

### 技术改进
- `StockPredictor.predict()` 方法重构，采用两阶段并行分析策略
- 添加异常处理机制，确保单个任务失败不影响其他任务
- 优化日志输出，清晰显示并行分析进度和结果
- 使用线程池管理并发任务，避免线程创建开销

### 批量分析进度优化
- ✅ **批量分析进度显示增强**：
  - 显示当前进度：`[进度: i/总数] (百分比%) | 成功: x | 失败: y`
  - 显示正在分析的第几个股票
  - 每完成一只股票后显示完成信息和进度百分比
  - 批量分析完成后显示完整总结（总计、成功数、失败数及百分比）

### 股票列表页面实时更新
- ✅ **批量分析时实时更新 `stock_list.html`**：
  - 每完成一只股票的预测后，立即更新股票列表页面
  - 无需等待全部股票分析完成即可查看最新数据
  - 在日志中记录更新内容：总记录数、总股票数、最新更新的股票代码

### 代码变更
- `predictor/stock_predictor.py`：
  - 导入 `concurrent.futures.ThreadPoolExecutor` 和 `as_completed`
  - 重构 `predict()` 方法，实现两阶段并行分析
  - 添加任务失败时的默认值处理逻辑
- `main.py`：
  - 增强批量分析进度显示
  - 每完成一只股票后立即调用 `create_stock_list_page()` 更新页面
  - 优化进度日志输出格式
- `visualizer/prediction_visualizer.py`：
  - `create_stock_list_page()` 方法返回详细的更新信息（记录数、股票数、最新股票等）
  - 使用 logger 替代 print，优化日志输出

### 使用说明
- 无需修改使用方式，代码自动使用多线程并行分析
- 单股票预测：`py main.py --symbol 600519`（自动并行分析，速度更快）
- 批量预测：`py main.py --all --limit 50`（实时更新股票列表页面，进度清晰显示）

---

## [2026-01-07] - 预测图表实时数据展示优化

### 新增功能
- ✅ **预测图表集成实时数据展示**：
  - 在预测图表中新增实时交易决策面板（第一行右侧）
  - 新增实时数据面板（第三行全宽），显示：
    - 实时行情：当前价格、涨跌幅、开盘/最高/最低价、换手率、振幅
    - 资金流向：主力净流入、总净流入、资金流向趋势
    - 交易时段：当前交易时段信息
  - 图表布局优化：从3行改为4行，增加实时数据展示空间
  
- ✅ **HTML报告集成实时数据**：
  - 在HTML报告中新增"实时行情与交易决策"部分
  - 展示实时行情数据（价格、涨跌幅、开高低收等）
  - 展示实时资金流向数据
  - 展示实时交易决策（操作建议、决策理由、价格建议）
  - 展示交易时段信息

### 技术改进
- `visualize()` 方法新增 `realtime_data` 参数
- `visualize_no_display_v2()` 方法支持实时数据传递
- `_create_interactive_html_report()` 方法集成实时数据展示
- `main.py` 在所有预测模式下自动获取并传递实时数据

### 使用说明
- 单股票预测模式：自动获取实时数据并展示
- 批量预测模式：自动获取实时数据并保存到图表
- 实时模式：生成包含实时决策的可视化图表

---

## [2026-01-07] - 实时交易决策系统

### 新增功能
- ✅ **实时交易决策模块** (`predictor/realtime_trading_advisor.py`)：
  - 开盘时间实时获取数据，预测明天走势
  - 综合分析：预测结果 + 实时资金流向 + 买卖盘强度 + 盘中涨跌
  - 智能决策：买入/卖出/加仓/减仓/持有观望
  - 支持持仓状态：根据成本价计算盈亏，给出止损止盈建议
  
- ✅ **实时数据获取** (`data_source/stock_data_source.py`)：
  - `get_realtime_quote()`: 获取实时行情（当前价、涨跌幅、换手率等）
  - `get_intraday_data()`: 获取盘中分时数据
  - `get_realtime_capital_flow()`: 获取实时资金流向
  - `get_bid_ask_data()`: 获取五档买卖盘数据
  - `is_trading_time()`: 判断当前交易时段

- ✅ **三种运行模式**：
  1. **实时模式** (`--realtime`): 单次获取实时决策
  2. **监控模式** (`--monitor`): 持续监控，信号变化时提醒
  3. **扫描模式** (`--scan`): 批量扫描找出最佳买入机会

### 使用方法
```bash
# 实时决策（未持仓）
py main.py --realtime --symbol 600519

# 实时决策（已持仓）cost 持仓金额
py main.py --realtime --symbol 600519 --holding --cost 1800

# 持续监控（每30秒更新）
py main.py --monitor --symbol 600519 --interval 30

# 批量扫描（找买入机会）
py main.py --scan --limit 50
```

### 决策逻辑
- **买入信号**: 上涨概率 > 65% + 置信度 > 55% + 资金净流入
- **强烈买入**: 上涨概率 > 75% + 置信度 > 70%
- **卖出信号**: 下跌概率 > 60% 或 触发止损线
- **止损止盈**: 默认止损-5%，止盈+8%，移动止损3%

### 配置更新 (`config.py`)
- 新增 `TRADING_CONFIG`: 交易决策参数配置
- 新增 `TRADING_TIME_CONFIG`: 交易时间配置

---

## [2026-01-07] - 预测结果文件组织优化

### 改进
- ✅ **创建reports目录统一存放预测结果**：
  - 新建 `reports/` 目录，所有预测结果文件（PNG、HTML）都保存在此目录
  - PNG图形报告：`reports/prediction_{symbol}_{timestamp}.png`
  - 交互式图表：`reports/prediction_{symbol}_{timestamp}_interactive.html`
  - 完整HTML报告：`reports/prediction_{symbol}_{timestamp}_full_report.html`
  
- ✅ **HTML文件路径引用优化**：
  - `stock_list.html` 和 `history_*.html` 中的文件链接自动使用相对路径
  - 从根目录指向 `reports/` 目录：`reports/prediction_*.png`
  - 确保HTML文件在浏览器中能正确打开链接的文件
  
- ✅ **目录结构清晰化**：
  - 根目录只保留主要文件：`stock_list.html`、`history_*.html`、`stock_predictions.csv`
  - 所有预测结果文件统一存放在 `reports/` 目录
  - 方便备份、管理和清理历史预测文件

### 技术细节
- `PredictionVisualizer.__init__()` 自动创建 `reports/` 目录
- 所有文件保存路径自动转换为 `reports/` 目录下的相对路径
- HTML生成时自动处理路径转换（绝对路径 -> 相对路径）

---

## [2026-01-07] - 数据存储功能（所有指标数据保存到CSV）

### 新增功能
- ✅ **数据存储模块** (`utils/data_storage.py`)：
  - 自动保存所有指标数据到CSV文件，供后续学习和分析使用
  - 8种数据类型分别存储：北向资金、融资融券、主力资金、板块轮动、技术指标、新闻情感、市场情绪、预测因子
  - 所有数据文件保存在 `data/` 目录下

- ✅ **自动数据保存**：
  - 每次预测时自动保存所有获取的指标数据
  - 支持数据去重和更新（同一天同一股票的数据会更新而不是重复）
  - 使用UTF-8-sig编码，Excel可直接打开

### 数据文件
- `data/north_bound_capital_data.csv` - 北向资金数据
- `data/margin_trading_data.csv` - 融资融券数据
- `data/main_force_capital_data.csv` - 主力资金数据
- `data/sector_rotation_data.csv` - 板块轮动数据
- `data/technical_indicators_data.csv` - 技术指标数据
- `data/news_sentiment_data.csv` - 新闻情感数据
- `data/market_sentiment_data.csv` - 市场情绪数据
- `data/prediction_factors_data.csv` - 预测因子数据（包含所有因子和最终结果）

### 使用场景
- 数据积累：每天运行预测，自动积累历史数据
- 模型训练：使用历史数据训练机器学习模型
- 数据分析：分析各指标与股价涨跌的相关性
- 数据验证：验证数据获取的准确性和预测逻辑

---

## [2026-01-07] - 批量预测功能（按成交额排序）

### 新增功能
- ✅ **批量预测模式**：
  - 新增 `--all` 参数：预测全部A股（非交互、仅保存CSV，不弹出图表窗口）
  - 新增 `--limit N` 参数：限制预测数量，默认按成交额从高到低排序取前N只
  - 使用方式：`py main.py --all --limit 5`（预测成交额最高的5只股票）
  - 批量模式下自动保存所有预测到 `stock_predictions.csv`
  - 批量完成后自动生成 `stock_list.html` 和所有 `history_{symbol}.html`

- ✅ **股票列表按成交额排序**：
  - `StockDataSource.get_all_stock_list()` 新增 `limit` 和 `sort_by_turnover` 参数
  - 默认按成交额降序排序，优先预测活跃度高的股票
  - 自动识别AkShare返回的"成交额"或"成交量"列进行排序

### 技术细节
- 批量模式不调用 `plt.show()` 或生成PNG/HTML报告，避免阻塞
- 每只股票预测后立即保存到CSV，确保进度不丢失
- 所有股票预测完成后统一生成列表页和历史页

### 使用示例
```bash
# 预测成交额最高的5只股票
py main.py --all --limit 5

# 预测全部A股（耗时较长）
py main.py --all

# 单股预测（保持原有功能）
py main.py --symbol 000592
```

---

## [2026-01-07] - 新闻指标显示优化

### 改进
- ✅ **HTML报告新闻信息增强**：
  - 在"个股预测分析"部分的"新闻情感"中，新增显示"直接相关"和"行业相关"新闻数量
  - 更清晰地展示新闻来源分类（直接提到股票的新闻 vs 行业相关新闻）
  - 保留原有的利好消息/利空消息数量和权重调整信息

### 验证结果
- ✅ **新闻源集成验证**：
  - 确认系统已成功初始化13个新闻源（包括新添加的TuShare、新浪财经、腾讯财经、网易财经、上交所、深交所、巨潮资讯等）
  - 确认 `calculate_news_score` 方法正确遍历所有新闻源获取新闻
  - 确认新闻数据（包括 `direct_news_count`、`industry_news_count`、`positive_count`、`negative_count`、`weight_multiplier` 等）正确传递到HTML报告

### 技术细节
- 在 `_create_interactive_html_report` 方法中，增强新闻情感显示部分
- 显示格式：直接相关: X 条 | 行业相关: Y 条
- 所有新闻源数据已正确集成到预测分析流程中

---

## [2026-01-07] - 批量预测（全A股）模式

### 新增功能
- ✅ **新增批量预测入口**：`main.py` 新增 `--all` 参数，支持非交互批量预测全部A股。
- ✅ **支持限制数量测试**：新增 `--limit N`，用于快速冒烟测试（例如 `--all --limit 20`）。

### 行为说明
- 批量模式 **仅保存预测结果到 `stock_predictions.csv`**，不会生成 PNG/HTML 报告，也不会弹出 matplotlib 窗口（避免 `plt.show()` 阻塞）。
- 批量跑完后会统一生成/更新 `stock_list.html`，并为每只股票生成 `history_{symbol}.html`。

### 技术细节
- 新增 `StockDataSource.get_all_stock_list()`，基于 AkShare `stock_zh_a_spot_em()` 获取全量A股代码与名称，并确保 `symbol` 以字符串保存（保留前导零）。

---

## [2026-01-07] - 新闻源备用方案机制

### 改进
- ✅ **添加备用URL机制**：
  - 新浪财经新闻源：添加了3个备用URL，如果主要URL失败，自动尝试备用URL
  - 每个新闻源支持多个URL尝试，提高成功率
  - 自动跳过失败的URL，尝试下一个备用方案

- ✅ **测试脚本优化**：
  - 创建了详细的测试脚本 `test_all_sources.py`
  - 可以单独测试每个新闻源的可用性
  - 记录测试结果和错误信息
  - 生成测试报告

### 技术细节
- 使用URL列表，按顺序尝试直到成功或全部失败
- 如果某个URL成功获取到新闻，立即停止尝试其他URL
- 详细的日志记录每个URL的尝试结果
- 优雅的错误处理，不影响其他新闻源

### 下一步计划
- 为其他新闻源（腾讯财经、网易财经等）添加备用URL
- 添加重试机制（网络错误时自动重试）
- 添加请求延迟（避免请求过快被封禁）

---

## [2026-01-07] - 新闻源大幅扩展

### 新增功能
- ✅ **新增7个新闻源**：
  1. **TuShare新闻源** (`tushare_news_source.py`)：
     - 使用TuShare API获取新闻（如果tushare库可用）
     - 支持cctv_news接口
     - 如果API不可用，尝试网页爬虫方式
  
  2. **新浪财经新闻源** (`sina_news_source.py`)：
     - 爬取新浪财经股票新闻和市场新闻
     - 智能解析时间格式（支持"今天"、"昨天"、"X分钟前"等）
     - 自动处理相对路径URL
  
  3. **腾讯财经新闻源** (`tencent_news_source.py`)：
     - 爬取腾讯财经股票新闻和市场新闻
     - 支持多种时间格式解析
     - 自动处理URL转换
  
  4. **网易财经新闻源** (`netease_news_source.py`)：
     - 爬取网易财经股票新闻和市场新闻
     - 智能时间解析
     - 自动URL处理
  
  5. **上交所新闻源** (`sse_news_source.py`)：
     - 获取上海证券交易所公告和市场新闻
     - 支持股票公告查询
     - 官方公告数据源
  
  6. **深交所新闻源** (`szse_news_source.py`)：
     - 获取深圳证券交易所公告和市场新闻
     - 支持股票公告查询
     - 官方公告数据源
  
  7. **巨潮资讯新闻源** (`cninfo_news_source.py`)：
     - 获取巨潮资讯网公告和市场新闻
     - 官方信息披露平台
     - 权威的上市公司公告数据源

### 改进
- ✅ **统一新闻源集成**：
  - 所有新新闻源已集成到`UnifiedNewsSource`
  - 自动处理初始化失败（优雅降级）
  - 支持通过参数传入TuShare token
  - 每个新闻源独立错误处理，不会影响其他源

- ✅ **新闻源可用性检查**：
  - 使用try-except包裹每个新闻源的导入和初始化
  - 如果某个新闻源不可用，不影响其他新闻源
  - 记录详细的初始化日志

### 技术细节
- 所有新闻源继承自`BaseNewsSource`基类
- 实现`get_stock_news()`和`get_market_news()`方法
- 统一返回格式：`{'title', 'content', 'time', 'url', 'source'}`
- 使用BeautifulSoup进行HTML解析
- 智能时间解析支持多种格式
- 自动URL转换（相对路径转绝对路径）

### 注意事项
- TuShare需要安装`tushare`库：`pip install tushare`
- 部分新闻源可能需要网络访问权限
- 爬虫方式可能受到网站结构变化影响
- 建议在使用时测试每个新闻源的可用性

---

## [2026-01-07] - 预测结果保存时机优化（实时保存）

### 改进
- ✅ **预测完成后立即保存**：
  - 在预测分析完成后立即保存到CSV，无需等待可视化完成
  - 生成PNG图表后自动更新记录，添加PNG文件路径
  - 生成HTML报告后自动更新记录，添加HTML报告路径
  - 即使可视化失败或用户关闭窗口，预测数据也已经保存

- ✅ **批量预测时同样处理**：
  - 每个股票预测完成后立即保存
  - 不等待所有股票预测完成再统一保存
  - 实时更新CSV，方便随时查看预测结果

### 技术细节
- 在`main.py`中，预测完成后立即调用`save_stock_record`（基本数据）
- 在`visualize`方法中，保存PNG后更新CSV记录（添加PNG路径）
- HTML报告生成后，再次更新CSV记录（添加HTML路径）
- 使用动态导入logger，确保日志记录正常工作
- 保证数据的实时性和可靠性

---

## [2026-01-07] - PNG图表中个股预测分析格式优化

### 改进
- ✅ **个股预测分析显示格式优化**：
  - 参考"市场整体行情预测"的格式，每个指标一行显示
  - 技术指标、新闻情感、市场情绪、历史模式、美股板块、估值指标各占一行
  - 综合预测结果单独一行，加粗突出显示
  - 使用统一的字体大小（9号）和行高（0.08）
  - 自动换行处理，确保内容完整显示

### 显示格式
- **技术指标**: `技术指标: 得分XX（偏多/偏空/中性，趋势：up/down/neutral）`
- **新闻情感**: `新闻情感: XX（得分XX，新闻条数XX，利好消息X条，利空消息X条，权重调整XX%）`
- **市场情绪**: `市场情绪: 得分XX（趋势：XX）`
- **历史模式**: `历史模式: 得分XX（模式描述）`
- **美股板块**: `美股板块: XX（得分XX，趋势：XX，涨跌幅XX%）`
- **估值指标**: `估值指标: 得分XX（估值：XX，PE：XX，PB：XX）`
- **综合预测**: `综合预测: XX，上涨概率XX%，下跌概率XX%，置信度XX%`（加粗）

### 技术细节
- 与"市场整体行情预测"格式保持一致
- 使用textwrap自动换行，确保长文本正确显示
- 统一的视觉风格和布局

---

## [2026-01-07] - 历史预测功能增强

### 新增功能
- ✅ **自动获取实际数据并对比**：
  - 历史预测页面自动获取目标日期的实际收盘价
  - 自动计算实际涨跌幅和方向
  - 自动判断预测是否命中（成功/失败）
  - 实际数据会自动保存回CSV文件

- ✅ **详细预测内容展示**：
  - 每条历史预测可点击"查看详情"展开
  - 展示预测时间、日期、价格、概率等详细信息
  - 展示预测分析摘要
  - 显示实际数据对比（如果有）
  - 提供图形报告和完整报告的快速链接

- ✅ **自动生成历史页面**：
  - 生成列表页面时，自动为每个股票生成历史预测页面
  - 支持从CSV正确读取数据并展示

### 改进
- 历史预测页面从CSV读取数据
- 自动处理NaN值和数据类型转换
- 预测命中判断逻辑：上涨/下跌/震荡与实际情况对比
- 页面样式优化，支持展开/收起详情

---

## [2026-01-07] - CSV存储逻辑优化

### 改进
- ✅ **股票名称获取优化**：
  - 修复股票名称获取不正确的问题
  - 支持多种名称字段（名称、股票简称、股票名称等）
  - 如果基本信息获取失败，从股票列表中查找

- ✅ **CSV字段完善**：
  - 字段按逻辑顺序排列：股票代码、名称、预测日期、目标日期、当前价格、预测方向、概率等
  - 确保所有数值字段正确转换（float类型）
  - 所有字符串字段进行strip()处理
  - 实际数据字段（actual_price、actual_change_pct、actual_direction、prediction_hit）正确保留

- ✅ **数据完整性**：
  - 更新记录时，保留原有的实际数据字段（如果已有）
  - 确保CSV包含所有必需字段，缺失字段用空字符串填充
  - 保存时输出详细信息用于调试

---

## [2026-01-07] - 个股预测分析显示优化

### 改进
- ✅ **HTML报告中个股预测分析格式优化**：
  - 按每个指标一行排列显示
  - 包含：技术指标、新闻情感、市场情绪、历史模式、美股板块、估值指标
  - 每个指标显示：得分、权重、趋势/状态
  - 显示子信息（如技术指标信号、利空/利好统计、权重调整等）
  - 综合预测结果单独一行突出显示
  - 详细分析摘要单独展示

### 显示特点
- 结构清晰，每个指标独立一行
- 主指标信息突出，子信息缩进显示
- 使用颜色区分权重提升/降低
- 综合预测用分隔线突出显示

---

## [2026-01-07] - HTML报告自动打开控制

### 改进
- ✅ **禁用HTML自动打开**：
  - 修改 `write_html` 方法的 `auto_open` 参数为 `False`
  - 关闭预测图后不会自动弹出HTML文件
  - HTML文件仍会保存到本地，可通过列表页面按钮查看

---

## [2026-01-06] - 数据存储方式优化：仅使用CSV

### 改进
- ✅ **数据存储方式变更**：
  - 移除 JSON 和 Excel 文件格式，仅使用 CSV 文件存储预测数据
  - CSV 文件：`stock_predictions.csv`
  - 数据字段包括：股票代码、名称、价格、预测结果、概率、文件路径等

- ✅ **数据读取优化**：
  - `create_stock_list_page()` 方法改为从 CSV 读取数据
  - `create_stock_history_page()` 方法改为从 CSV 读取数据
  - 自动处理 CSV 中的 NaN 值，确保数据完整性

- ✅ **运行逻辑优化**：
  - 每次运行（单个股票或全部股票）都自动保存预测记录到 CSV
  - 每次运行后自动生成/更新股票列表页面
  - 无论是否生成图表，都会保存预测记录

### 技术细节
- 使用 pandas 处理 CSV 文件读写
- CSV 文件使用 UTF-8-sig 编码，支持中文显示
- 同一天对同一股票的预测会替换，不同天的预测会新增

---

## [2026-01-06] - 股票列表页面四个按钮功能完善

### 新增功能
- ✅ **股票列表页面按钮完善**：
  - 📝 **文字报告按钮**（绿色）：点击展开/收起当前股票行下方的摘要内容，不跳转页面
  - 📊 **图形报告按钮**（蓝色）：链接到 PNG 静态图片，在新标签页打开；如果 PNG 不存在则按钮灰色禁用
  - 📄 **文字详情按钮**（橙色）：链接到完整 HTML 预测报告，在新标签页打开
  - 📚 **历史预测按钮**（灰蓝色）：链接到该股票的历史预测页面，显示所有历史预测记录

### 新增方法
- `PredictionVisualizer.save_stock_record()`: 保存股票预测记录到 JSON、CSV 和 Excel 文件
- `PredictionVisualizer.create_stock_list_page()`: 创建股票预测列表页面
- `PredictionVisualizer.create_stock_history_page()`: 创建单个股票的历史预测页面
- `PredictionVisualizer._generate_stock_list_html()`: 生成股票列表 HTML 内容
- `PredictionVisualizer._generate_empty_stock_list_html()`: 生成空列表 HTML

### 改进
- `PredictionVisualizer.visualize()` 方法现在返回包含 `png_file` 和 `full_report_html` 的字典
- `PredictionVisualizer._create_interactive_html_report()` 方法现在返回 HTML 文件名
- 股票预测记录中新增 `png_file` 和 `full_report_html` 字段

### 数据存储
- 预测记录保存在 `stock_predictions.json` 文件中
- 同一天对同一股票的预测会替换，不同天的预测会新增

---

## [2026-01-06] - 新闻指标分析逻辑优化

### 新增功能
- ✅ **更智能的行业/板块相关性判断**：
  - 新增 `_check_news_industry_relevance()` 方法
  - 多维度相关性判断：关键词匹配、行业名称完整匹配、概念板块匹配、行业相关词汇识别
  - 支持多关键词同时出现时的增强判断

- ✅ **根据利空/利好动态调整新闻权重**：
  - 统计利空/利好消息的数量和强度
  - 动态权重调整规则：
    - 强烈利好（≥3条，强度>0.5）：权重倍数 1.5（增加50%）
    - 中等利好（≥2条，强度>0.3）：权重倍数 1.3（增加30%）
    - 轻微利好（≥1条，强度>0.2）：权重倍数 1.1（增加10%）
    - 强烈利空（≥3条，强度>0.5）：权重倍数 1.5（增加50%）
    - 消息矛盾：权重倍数 0.7（降低30%）
    - 无明确信号：权重倍数 0.6（降低40%）

### 改进
- `calculate_news_score()` 方法重构，实现更智能的新闻筛选和分析
- 根据新闻与行业的相关性调整情感强度
- 日志输出增强，显示利空/利好消息的详细统计
- 预测结果中新增新闻权重倍数、利空/利好统计等详细信息

### 技术细节
- 分别获取直接相关和行业相关新闻
- 使用智能相关性判断筛选行业相关新闻（相关性得分 > 0.3）
- 根据相关性得分调整情感强度：`adjusted_score = score * (0.5 + relevance_score * 0.5)`

---

## [2026-01-06] - 美股板块行情集成

### 新增功能
- ✅ **美股板块行情数据获取**：
  - `StockDataSource.get_us_sector_data()`: 获取美股板块 ETF 数据
  - `StockDataSource.get_us_sector_mapping()`: 获取 A 股与美股板块的映射关系

- ✅ **美股板块得分计算**：
  - `StockPredictor.calculate_us_sector_score()`: 根据股票所属行业，匹配对应美股板块，计算板块得分
  - 支持多个细分主题板块：半导体、芯片、云计算、新能源等

### 改进
- 预测模型集成美股板块得分，权重为 0.12
- 预测总结中包含美股板块行情信息

---

## [2026-01-06] - 新闻功能增强

### 新增功能
- ✅ **新增财经新闻源**：
  - 东方财富新闻源 (`eastmoney_news_source.py`)
  - 雪球新闻源 (`xueqiu_news_source.py`)

- ✅ **行业相关新闻筛选**：
  - `StockDataSource.get_stock_industry_info()`: 获取股票行业和概念板块信息
  - `UnifiedNewsSource.get_stock_news()`: 支持 `industry_keywords` 参数，筛选行业相关新闻

### 改进
- 新闻源从 4 个增加到 6 个
- 不仅获取直接提到股票的新闻，还自动筛选包含行业/概念关键词的市场新闻
- 新闻标记相关性：`direct`（直接相关）、`industry`（行业相关）

---

## [2026-01-06] - 可视化功能增强

### 新增功能
- ✅ **完整 HTML 报告生成**：
  - `PredictionVisualizer._create_interactive_html_report()`: 创建包含所有图表和详细分析的完整 HTML 报告
  - 报告包含：涨跌概率饼图、各因素得分雷达图、市场行情预测、个股预测分析、30天趋势图等

- ✅ **交互式图表**：
  - 使用 Plotly 生成交互式 30 天价格走势图
  - 支持鼠标悬停查看详细数据

### 改进
- 图表布局优化，使用 3 行 4 列网格布局
- "个股预测分析"部分字体大小和换行优化，防止文字重叠
- HTML 报告设置 `auto_open=False`，避免自动打开浏览器

---

## [2026-01-06] - 初始版本

### 核心功能
- ✅ 股票数据获取（基于 akshare）
- ✅ 多维度预测模型：
  - 技术指标分析（MACD、RSI、MA、KDJ、CCI 等）
  - 新闻情感分析
  - 市场情绪分析
  - 历史模式分析
  - 估值指标分析（PE/PB）
- ✅ 预测结果可视化（Matplotlib）
- ✅ 交易建议计算（买入价、卖出价、竞价建议等）

### 项目结构
- `data_source/`: 数据源模块
- `predictor/`: 预测模型
- `visualizer/`: 可视化模块
- `utils/`: 工具函数
- `config.py`: 配置文件

---

## 更新说明

### 版本号规则
- 格式：`YYYY-MM-DD`（日期）
- 每次更新记录日期和详细内容

### 更新类型
- **新增功能**：✅ 新功能或特性
- **改进**：优化现有功能
- **修复**：🐛 修复 bug
- **文档**：📝 文档更新

---

## 未来计划

- [ ] 添加更多新闻源（证券时报、中国证券报等）
- [ ] 实现新闻信息缓存机制
- [ ] 机器学习模型优化
- [ ] 实时数据推送功能
- [ ] 批量预测性能优化
- [ ] 添加更多技术指标

