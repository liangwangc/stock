-- 股票预测系统数据库初始化脚本
-- 数据库名：stock_data

-- 注意：
-- 1. stock_history_data 表的创建脚本在 stock_history_table.sql 中
--    如需创建该表，请运行：python database/create_stock_history_table.py
-- 2. prediction_config 相关表的创建脚本在 prediction_config_table.sql 中
--    如需创建该表，请运行：python -c "from utils.prediction_config_manager import PredictionConfigManager; PredictionConfigManager()"
--    或直接执行：source database/prediction_config_table.sql
-- 3. model_learning 相关表的创建脚本在 model_learning_tables.sql 中
--    如需创建该表，请运行：python scripts/create_model_learning_tables.py
--    或者执行：source database/model_learning_tables.sql
-- 4. us_stock 相关表的创建脚本在 us_stock_tables.sql 中
--    如需创建该表，请运行：python scripts/create_us_stock_tables.py
--    或者执行：source database/us_stock_tables.sql

-- 1. 股票预测结果表
CREATE TABLE IF NOT EXISTS `stock_predictions` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `industry` VARCHAR(100) DEFAULT NULL COMMENT '所属行业',
    `concepts` TEXT DEFAULT NULL COMMENT '概念板块（JSON数组格式）',
    `main_concept` VARCHAR(100) DEFAULT NULL COMMENT '主要概念板块',
    `market` VARCHAR(20) DEFAULT 'A股' COMMENT '所属市场（A股/港股/美股）',
    `prediction_date` DATE DEFAULT NULL COMMENT '预测日期',
    `target_date` DATE DEFAULT NULL COMMENT '目标日期',
    `current_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '当前价格',
    `prediction` VARCHAR(10) DEFAULT NULL COMMENT '预测方向（上涨/下跌/震荡）',
    `up_probability` DECIMAL(5, 4) DEFAULT NULL COMMENT '上涨概率',
    `down_probability` DECIMAL(5, 4) DEFAULT NULL COMMENT '下跌概率',
    `confidence` DECIMAL(5, 4) DEFAULT NULL COMMENT '置信度',
    `final_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '最终得分',
    `prediction_time` DATETIME DEFAULT NULL COMMENT '预测时间',
    `png_file` VARCHAR(500) DEFAULT NULL COMMENT 'PNG图形报告路径',
    `interactive_html` VARCHAR(500) DEFAULT NULL COMMENT '交互式图表路径',
    `full_report_html` VARCHAR(500) DEFAULT NULL COMMENT '完整HTML报告路径',
    `summary` TEXT DEFAULT NULL COMMENT '预测分析摘要',
    `actual_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '实际价格',
    `actual_change_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '实际涨跌幅',
    `actual_direction` VARCHAR(10) DEFAULT NULL COMMENT '实际方向',
    `prediction_hit` VARCHAR(10) DEFAULT NULL COMMENT '预测结果（命中/未命中）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_industry` (`industry`),
    INDEX `idx_main_concept` (`main_concept`),
    INDEX `idx_market` (`market`),
    INDEX `idx_prediction_date` (`prediction_date`),
    INDEX `idx_target_date` (`target_date`),
    INDEX `idx_prediction_time` (`prediction_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票预测结果表';

-- 2. 北向资金数据表
CREATE TABLE IF NOT EXISTS `north_bound_capital` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `today_net_inflow` DECIMAL(15, 2) DEFAULT NULL COMMENT '今日净流入（亿元）',
    `avg_net_inflow_5d` DECIMAL(15, 2) DEFAULT NULL COMMENT '5日平均净流入（亿元）',
    `avg_net_inflow_10d` DECIMAL(15, 2) DEFAULT NULL COMMENT '10日平均净流入（亿元）',
    `trend` VARCHAR(20) DEFAULT NULL COMMENT '趋势（inflow/outflow/neutral）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_date` (`date`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='北向资金数据表';

-- 3. 融资融券数据表
CREATE TABLE IF NOT EXISTS `margin_trading` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `margin_balance` DECIMAL(15, 2) DEFAULT NULL COMMENT '融资余额（万元）',
    `margin_change` DECIMAL(15, 2) DEFAULT NULL COMMENT '融资余额变化（万元）',
    `margin_change_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '融资余额变化百分比',
    `short_balance` DECIMAL(15, 2) DEFAULT NULL COMMENT '融券余额（万元）',
    `trend` VARCHAR(20) DEFAULT NULL COMMENT '趋势（increasing/decreasing/stable）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_symbol_date` (`symbol`, `date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='融资融券数据表';

-- 4. 主力资金数据表
CREATE TABLE IF NOT EXISTS `main_force_capital` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `main_net_inflow` DECIMAL(15, 2) DEFAULT NULL COMMENT '主力资金净流入（万元）',
    `main_net_inflow_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '主力资金净流入百分比',
    `trend` VARCHAR(20) DEFAULT NULL COMMENT '趋势（inflow/outflow/neutral）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_symbol_date` (`symbol`, `date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='主力资金数据表';

-- 5. 板块轮动数据表
CREATE TABLE IF NOT EXISTS `sector_rotation` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `sector_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `sector_type` VARCHAR(20) DEFAULT NULL COMMENT '板块类型（industry/concept）',
    `change_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '涨跌幅',
    `capital_flow` DECIMAL(15, 2) DEFAULT NULL COMMENT '资金净流入',
    `heat` DECIMAL(5, 4) DEFAULT NULL COMMENT '热度（0-1）',
    `is_hot` TINYINT(1) DEFAULT 0 COMMENT '是否热门板块（1/0）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_date` (`date`),
    INDEX `idx_sector_name` (`sector_name`),
    INDEX `idx_date_type` (`date`, `sector_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块轮动数据表';

-- 6. 技术指标数据表
CREATE TABLE IF NOT EXISTS `technical_indicators` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `ma5` DECIMAL(10, 2) DEFAULT NULL COMMENT 'MA5',
    `ma10` DECIMAL(10, 2) DEFAULT NULL COMMENT 'MA10',
    `ma20` DECIMAL(10, 2) DEFAULT NULL COMMENT 'MA20',
    `ma60` DECIMAL(10, 2) DEFAULT NULL COMMENT 'MA60',
    `rsi` DECIMAL(8, 4) DEFAULT NULL COMMENT 'RSI',
    `macd` DECIMAL(10, 4) DEFAULT NULL COMMENT 'MACD',
    `macd_signal` DECIMAL(10, 4) DEFAULT NULL COMMENT 'MACD Signal',
    `macd_hist` DECIMAL(10, 4) DEFAULT NULL COMMENT 'MACD Histogram',
    `kdj_k` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ K',
    `kdj_d` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ D',
    `kdj_j` DECIMAL(8, 4) DEFAULT NULL COMMENT 'KDJ J',
    `boll_upper` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL上轨',
    `boll_middle` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL中轨',
    `boll_lower` DECIMAL(10, 2) DEFAULT NULL COMMENT 'BOLL下轨',
    `volume_ratio` DECIMAL(8, 4) DEFAULT NULL COMMENT '量比',
    `turnover_rate` DECIMAL(8, 4) DEFAULT NULL COMMENT '换手率',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_symbol_date` (`symbol`, `date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技术指标数据表';

-- 7. 新闻情感数据表
CREATE TABLE IF NOT EXISTS `news_sentiment` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `symbol` VARCHAR(10) DEFAULT NULL COMMENT '股票代码（NULL表示市场整体）',
    `news_count` INT DEFAULT 0 COMMENT '新闻条数',
    `direct_news_count` INT DEFAULT 0 COMMENT '直接相关新闻数',
    `industry_news_count` INT DEFAULT 0 COMMENT '行业相关新闻数',
    `positive_count` INT DEFAULT 0 COMMENT '利好消息数',
    `negative_count` INT DEFAULT 0 COMMENT '利空消息数',
    `sentiment` VARCHAR(20) DEFAULT NULL COMMENT '情感（positive/negative/neutral）',
    `sentiment_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '情感得分',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_date` (`date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_date_symbol` (`date`, `symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻情感数据表';

-- 8. 市场情绪数据表
CREATE TABLE IF NOT EXISTS `market_sentiment` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `overall_prediction` VARCHAR(20) DEFAULT NULL COMMENT '整体预测（上涨/下跌/震荡）',
    `overall_up_probability` DECIMAL(5, 4) DEFAULT NULL COMMENT '整体上涨概率',
    `overall_down_probability` DECIMAL(5, 4) DEFAULT NULL COMMENT '整体下跌概率',
    `index_predictions` TEXT DEFAULT NULL COMMENT '各指数预测（JSON格式）',
    `trend` VARCHAR(20) DEFAULT NULL COMMENT '趋势（up/down/neutral）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_date` (`date`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场情绪数据表';

-- 9. 预测因子数据表
CREATE TABLE IF NOT EXISTS `prediction_factors` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `technical_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '技术指标得分',
    `technical_weight` DECIMAL(5, 4) DEFAULT NULL COMMENT '技术指标权重',
    `technical_trend` VARCHAR(20) DEFAULT NULL COMMENT '技术指标趋势',
    `news_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '新闻情感得分',
    `news_weight` DECIMAL(5, 4) DEFAULT NULL COMMENT '新闻情感权重',
    `news_sentiment` VARCHAR(20) DEFAULT NULL COMMENT '新闻情感',
    `capital_flow_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '资金流向得分',
    `capital_flow_weight` DECIMAL(5, 4) DEFAULT NULL COMMENT '资金流向权重',
    `capital_flow_trend` VARCHAR(20) DEFAULT NULL COMMENT '资金流向趋势',
    `market_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '市场情绪得分',
    `market_weight` DECIMAL(5, 4) DEFAULT NULL COMMENT '市场情绪权重',
    `market_trend` VARCHAR(20) DEFAULT NULL COMMENT '市场情绪趋势',
    `sector_rotation_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '板块轮动得分',
    `sector_rotation_weight` DECIMAL(5, 4) DEFAULT NULL COMMENT '板块轮动权重',
    `sector_rotation_trend` VARCHAR(20) DEFAULT NULL COMMENT '板块轮动趋势',
    `history_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '历史模式得分',
    `history_weight` DECIMAL(5, 4) DEFAULT NULL COMMENT '历史模式权重',
    `history_pattern` VARCHAR(50) DEFAULT NULL COMMENT '历史模式',
    `valuation_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '估值指标得分',
    `valuation_weight` DECIMAL(5, 4) DEFAULT NULL COMMENT '估值指标权重',
    `pe_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT 'PE比率',
    `pb_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT 'PB比率',
    `us_sector_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '美股板块得分',
    `us_sector_weight` DECIMAL(5, 4) DEFAULT NULL COMMENT '美股板块权重',
    `us_sector_name` VARCHAR(100) DEFAULT NULL COMMENT '美股板块名称',
    `final_score` DECIMAL(8, 4) DEFAULT NULL COMMENT '最终得分',
    `up_probability` DECIMAL(5, 4) DEFAULT NULL COMMENT '上涨概率',
    `down_probability` DECIMAL(5, 4) DEFAULT NULL COMMENT '下跌概率',
    `confidence` DECIMAL(5, 4) DEFAULT NULL COMMENT '置信度',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_date` (`date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_date_symbol` (`date`, `symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测因子数据表';

-- 10. 成本分布数据表
CREATE TABLE IF NOT EXISTS `cost_distribution` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `scope` VARCHAR(20) NOT NULL COMMENT '范围（history/intraday）',
    `levels` TEXT DEFAULT NULL COMMENT '成本分布级别（JSON格式）',
    `top_levels` TEXT DEFAULT NULL COMMENT '主要成本级别（JSON格式）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_symbol_date_scope` (`symbol`, `date`, `scope`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成本分布数据表';

-- 11. 实时交易决策数据表
CREATE TABLE IF NOT EXISTS `realtime_trading_decisions` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL COMMENT '时间戳',
    `date` DATE NOT NULL COMMENT '日期',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `mode` VARCHAR(20) DEFAULT NULL COMMENT '模式（realtime/monitor/scan/single）',
    `holding` TINYINT(1) DEFAULT 0 COMMENT '是否持有（1/0）',
    `cost_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '持仓成本价',
    `current_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '当前价格',
    `change_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '涨跌幅',
    `up_probability` DECIMAL(5, 4) DEFAULT NULL COMMENT '上涨概率',
    `down_probability` DECIMAL(5, 4) DEFAULT NULL COMMENT '下跌概率',
    `confidence` DECIMAL(5, 4) DEFAULT NULL COMMENT '置信度',
    `prediction_direction` VARCHAR(10) DEFAULT NULL COMMENT '预测方向',
    `target_date` DATE DEFAULT NULL COMMENT '目标日期',
    `signal_strength` DECIMAL(8, 4) DEFAULT NULL COMMENT '信号强度',
    `action` VARCHAR(20) DEFAULT NULL COMMENT '操作建议（BUY/SELL/ADD/REDUCE/HOLD/WAIT/AVOID）',
    `action_cn` VARCHAR(20) DEFAULT NULL COMMENT '操作建议（中文）',
    `strength` VARCHAR(20) DEFAULT NULL COMMENT '强度（STRONG/MODERATE/NEUTRAL）',
    `strength_cn` VARCHAR(20) DEFAULT NULL COMMENT '强度（中文）',
    `trading_session` VARCHAR(20) DEFAULT NULL COMMENT '交易时段',
    `trading_message` VARCHAR(200) DEFAULT NULL COMMENT '交易时段消息',
    `main_net_inflow` DECIMAL(15, 2) DEFAULT NULL COMMENT '主力净流入（万元）',
    `total_net_inflow` DECIMAL(15, 2) DEFAULT NULL COMMENT '总净流入（万元）',
    `flow_trend` VARCHAR(20) DEFAULT NULL COMMENT '资金趋势',
    `reasons` TEXT DEFAULT NULL COMMENT '决策理由',
    `risk_warnings` TEXT DEFAULT NULL COMMENT '风险警告',
    `position_advice` TEXT DEFAULT NULL COMMENT '仓位建议',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_date` (`date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_timestamp` (`timestamp`),
    INDEX `idx_mode` (`mode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实时交易决策数据表';
