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
PREDICTION_CONFIG = {
    # 核心因素（60%）
    "news_weight": 0.25,          # 新闻情感权重（包含政策新闻）
    "capital_flow_weight": 0.18,  # 资金流向权重（新增：北向资金、融资融券、主力资金）
    "market_weight": 0.17,        # 市场情绪权重（改进：包含大盘指数影响）
    
    # 技术分析（25%）
    "technical_weight": 0.20,     # 技术指标权重（降低）
    "sector_rotation_weight": 0.05, # 板块轮动权重（新增）
    
    # 辅助因素（15%）
    "history_weight": 0.08,       # 历史模式权重（略降）
    "us_sector_weight": 0.05,     # 美股板块权重（降低）
    "valuation_weight": 0.02,     # 估值指标权重（降低）
    
    # 其他配置
    "min_confidence": 0.5,        # 最小置信度
    "lookback_days": 60           # 回看天数
    
    # 权重总和：100%
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
    "cci_period": 14      # CCI周期
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

# 日志配置
LOG_LEVEL = "INFO"

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
    "max_workers": 10,                  # 同时分析的股票数量（多线程并发数）
                                      # 建议值：3-5（取决于网络和API限制）
                                      # 如果API有频率限制，建议设置为较小值
                                      # 如果网络和服务器性能好，可以设置更大值（如 5-10）
    "enable_parallel": True,           # 是否启用多线程并行分析
}