"""
配置文件
"""

# 数据源配置
DATA_SOURCE = "akshare"  # 数据源：akshare

# 新闻源配置
NEWS_SOURCES = [
    "jin10",      # 金十数据
    "caixin",     # 财新
    "securities", # 证券公司（包括广发证券等）
    "tonghuashun", # 同花顺
    "eastmoney",  # 东方财富
    "xueqiu"      # 雪球
]

# 预测模型配置
# 架构：ML模型主导（35%） + 传统因子辅助（65%） = 100%
PREDICTION_CONFIG = {
    # 传统因子权重（合计65%）
    "technical_weight": 0.20,      # 技术指标权重（MACD、RSI、KDJ、MA、CCI、X2）
    "news_weight": 0.16,           # 新闻情感权重（包含政策新闻）
    "capital_flow_weight": 0.13,   # 资金流向权重（北向资金、融资融券、主力资金）
    "market_weight": 0.11,         # 市场情绪权重（大盘指数影响）
    "history_weight": 0.05,        # 历史模式权重（历史相似模式识别）
    
    # 已移除的因子（保留配置兼容性）
    "sector_rotation_weight": 0.0, # 板块轮动（已移除）
    "us_sector_weight": 0.0,       # 美股板块（已移除）
    "valuation_weight": 0.0,       # 估值指标（已移除）
    
    # ML模型配置（默认占35%，根据模型性能动态调整）
    "ml_default_weight": 0.35,     # ML模型默认权重（77%准确率，主导因子）
    "ml_min_weight": 0.10,         # ML模型最小权重（性能差时降低）
    "ml_max_weight": 0.50,         # ML模型最大权重上限（性能好时提升）
    "ml_high_accuracy_threshold": 0.60,   # 高准确率阈值
    "ml_medium_accuracy_threshold": 0.50, # 中等准确率阈值
    
    # 异常检测参数
    "st_stock_confidence_reduction": 0.20,        # ST股票置信度降低比例
    "limit_up_down_confidence_reduction": 0.10,   # 涨跌停置信度降低比例
    "suspended_stock_action": "skip_prediction",  # 停牌股票处理方式
    
    # 其他配置
    "min_confidence": 0.5,         # 最小置信度
    "lookback_days": 60,           # 回看天数
    
    # 传统因子65% + ML模型35% = 100%
}

# 技术指标参数
INDICATOR_CONFIG = {
    "ma_short": 5,        # 短期均线
    "ma_long": 20,        # 长期均线
    "rsi_period": 14,     # RSI周期（默认）
    "rsi_short": 6,       # RSI短周期
    "rsi_mid": 12,        # RSI中周期
    "macd_fast": 12,      # MACD快线
    "macd_slow": 26,      # MACD慢线
    "macd_signal": 9,     # MACD信号线
    "kdj_period": 9,      # KDJ周期
    "kdj_k_period": 3,    # KDJ K值平滑周期
    "kdj_d_period": 3,    # KDJ D值平滑周期
    "cci_period": 14,     # CCI周期
    "x2_period": 20       # X2指标周期（收盘价在N日价格区间中的相对位置，0-100）
}

# 新闻分析配置
NEWS_CONFIG = {
    "news_count": 15,             # 分析的新闻数量（增加以包含行业相关新闻）
    "sentiment_threshold": 0.3,   # 情感阈值
    "confidence_threshold": 0.5,  # 置信度阈值
    "include_industry_news": True, # 是否包含行业相关新闻
    "industry_weight": 0.7        # 行业相关新闻的权重（相对于直接相关新闻）
}

# TuShare 配置
# 已由用户申请的 TuShare token，用于通过 TuShare 获取数据和新闻
TUSHARE_TOKEN = "773d7c4add914e2632426899d9ee52296e059334223a467e8cd07870"

# Tushare网页登录配置（可选，用于网页方式获取新闻）
# 如果配置了账号密码，系统会尝试登录后从网页获取新闻
TUSHARE_USERNAME = None  # Tushare账号（手机或邮箱）
TUSHARE_PASSWORD = None  # Tushare密码

# 日志配置
LOG_LEVEL = "INFO"
LOG_FILE = "logs/app.log"  # 项目运行日志文件（增量追加，相对于项目根目录）

# 默认股票代码（如果命令行未指定，将使用此代码）
DEFAULT_STOCK_SYMBOL = "000592"  # 可以在这里修改默认股票代码

# 可视化配置
VISUALIZATION_CONFIG = {
    "figure_size": (14, 10),
    "dpi": 100,
    "style": "seaborn-v0_8",
    "save_format": "png"
}

# 实时交易决策配置
TRADING_CONFIG = {
    # 买入信号阈值
    "buy_signal_threshold": 0.65,      # 上涨概率超过此值考虑买入
    "strong_buy_threshold": 0.75,      # 强烈买入信号阈值
    
    # 卖出信号阈值
    "sell_signal_threshold": 0.60,     # 下跌概率超过此值考虑卖出
    "strong_sell_threshold": 0.70,     # 强烈卖出信号阈值
    
    # 置信度要求
    "min_confidence": 0.55,            # 最低置信度要求
    "high_confidence": 0.70,           # 高置信度
    
    # 实时数据权重
    "capital_flow_weight": 0.25,       # 实时资金流向权重
    "bid_ask_weight": 0.15,            # 买卖盘分析权重
    "intraday_weight": 0.10,           # 盘中涨跌调整权重
    
    # 止损止盈设置
    "stop_loss_pct": -5.0,             # 止损比例（%）
    "take_profit_pct": 8.0,            # 止盈比例（%）
    "trailing_stop_pct": 3.0,          # 移动止损比例（%）
    
    # 仓位控制
    "max_position_pct": 30.0,          # 单只股票最大仓位（%）
    "position_step": 10.0,             # 建仓步进（%）
    
    # 追涨杀跌风险控制
    "chase_high_threshold": 5.0,       # 追高警告阈值（今日涨幅%）
    "catch_low_threshold": -5.0,       # 抄底机会阈值（今日跌幅%）
    
    # 监控设置
    "monitor_interval": 60,            # 默认监控间隔（秒）
    "alert_on_signal_change": True,    # 信号变化时是否提醒
    
    # 风险控制设置（新增）
    "max_total_position_pct": 80.0,    # 总仓位上限（%）
    "max_single_position_pct": 30.0,   # 单只股票最大仓位（%）
    "max_correlation": 0.8,            # 最大相关性（持有相关性过高的股票时警告）
    "enable_risk_control": True,       # 是否启用风险控制
}

# 交易时间配置
TRADING_TIME_CONFIG = {
    "pre_open_start": "09:15",         # 集合竞价开始
    "pre_open_end": "09:25",           # 集合竞价结束
    "morning_start": "09:30",          # 上午开盘
    "morning_end": "11:30",            # 上午收盘
    "afternoon_start": "13:00",        # 下午开盘
    "afternoon_end": "15:00",          # 下午收盘
}

# 批量分析配置
BATCH_ANALYSIS_CONFIG = {
    "max_workers": 20,                  # 同时分析的股票数量（多线程并发数）
                                      # 设置页面股票分析推荐值：20（数据库模式，无API限制）
                                      # 主页预测推荐值：5-10（实时API模式，有频率限制）
                                      # 如果数据库性能好，可以设置更大值（如 20-30）
    "enable_parallel": True,           # 是否启用多线程并行分析
}

# ============================================================================
# 系统常量定义（用于替换代码中的魔法数字）
# ============================================================================

# 线程池配置常量
THREAD_POOL_CONFIG = {
    "predictor_default": 6,            # 预测器默认线程数
    "predictor_small": 3,              # 预测器小规模线程数
    "ml_training_default": 16,         # ML训练默认线程数
    "ml_training_max": 16,              # ML训练最大线程数
    "data_collection_default": 15,      # 数据收集默认线程数
    "data_collection_single": 1,       # 数据收集单线程
    "scheduled_task_default": 2,       # 定时任务默认线程数
    "web_api_default": 1,              # Web API默认线程数
}

# 置信度阈值常量
CONFIDENCE_THRESHOLDS = {
    "min": 0.5,                        # 最小置信度
    "medium": 0.55,                     # 中等置信度（用于回测和交易决策）
    "high": 0.6,                        # 高置信度（用于买入决策）
    "very_high": 0.7,                   # 非常高置信度（用于强烈信号）
}

# 股票数量阈值常量
SYMBOL_COUNT_THRESHOLDS = {
    "small_batch": 10,                 # 小批量阈值（用于判断是否需要批量处理）
    "medium_batch": 50,                # 中批量阈值（用于API限制检查）
    "large_batch": 100,                # 大批量阈值（用于性能优化）
}

# 概率阈值常量
PROBABILITY_THRESHOLDS = {
    "buy_signal": 0.6,                 # 买入信号概率阈值
    "strong_buy": 0.75,                # 强烈买入信号概率阈值
    "sell_signal": 0.6,                # 卖出信号概率阈值
    "strong_sell": 0.7,                # 强烈卖出信号概率阈值
}