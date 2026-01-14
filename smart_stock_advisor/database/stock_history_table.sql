-- 股票历史数据表
-- 存储近10年每只股票的详细历史数据，包括每日成交量、外盘、内盘、成本分布、委比等所有信息
-- 每天收盘后增量更新对应数据

CREATE TABLE IF NOT EXISTS `stock_history_data` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 基本信息
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码（如：600519）',
    `name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    
    -- 基本价格数据
    `open_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '开盘价（元）',
    `close_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '收盘价（元）',
    `high_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '最高价（元）',
    `low_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '最低价（元）',
    `pre_close` DECIMAL(10, 2) DEFAULT NULL COMMENT '昨收价（元）',
    `change_amount` DECIMAL(10, 2) DEFAULT NULL COMMENT '涨跌额（元）',
    `change_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '涨跌幅（%）',
    
    -- 成交数据
    `volume` BIGINT DEFAULT NULL COMMENT '成交量（手）',
    `amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '成交额（元）',
    `turnover_rate` DECIMAL(8, 4) DEFAULT NULL COMMENT '换手率（%）',
    `volume_ratio` DECIMAL(8, 4) DEFAULT NULL COMMENT '量比',
    
    -- 盘口数据（外盘、内盘）
    `outer_volume` BIGINT DEFAULT NULL COMMENT '外盘（主动买入成交量，手）',
    `inner_volume` BIGINT DEFAULT NULL COMMENT '内盘（主动卖出成交量，手）',
    `bid_ask_ratio` DECIMAL(8, 4) DEFAULT NULL COMMENT '委比（%）',
    
    -- 五档买卖盘数据（JSON格式）
    `bid_levels` JSON DEFAULT NULL COMMENT '五档买盘数据（JSON格式：[{price, volume}, ...]）',
    `ask_levels` JSON DEFAULT NULL COMMENT '五档卖盘数据（JSON格式：[{price, volume}, ...]）',
    `bid_total_volume` BIGINT DEFAULT NULL COMMENT '买盘总手数',
    `ask_total_volume` BIGINT DEFAULT NULL COMMENT '卖盘总手数',
    
    -- 成本分布数据（JSON格式）
    `cost_distribution` JSON DEFAULT NULL COMMENT '成本分布数据（JSON格式：{price_levels: [{price, volume, pct}, ...], top_levels: [...]}）',
    `cost_distribution_history` JSON DEFAULT NULL COMMENT '历史成本分布数据',
    `cost_distribution_intraday` JSON DEFAULT NULL COMMENT '当日成本分布数据',
    
    -- 市值和估值
    `total_market_cap` DECIMAL(20, 2) DEFAULT NULL COMMENT '总市值（元）',
    `float_market_cap` DECIMAL(20, 2) DEFAULT NULL COMMENT '流通市值（元）',
    `pe_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '市盈率（动态）',
    `pb_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '市净率',
    
    -- 涨跌停信息
    `limit_up` DECIMAL(10, 2) DEFAULT NULL COMMENT '涨停价（元）',
    `limit_down` DECIMAL(10, 2) DEFAULT NULL COMMENT '跌停价（元）',
    `limit_pct` DECIMAL(5, 2) DEFAULT NULL COMMENT '涨跌停幅度（%）',
    `is_limit_up` TINYINT(1) DEFAULT 0 COMMENT '是否涨停（1=涨停，0=未涨停）',
    `is_limit_down` TINYINT(1) DEFAULT 0 COMMENT '是否跌停（1=跌停，0=未跌停）',
    
    -- 振幅和波动
    `amplitude` DECIMAL(8, 4) DEFAULT NULL COMMENT '振幅（%）',
    `price_range` DECIMAL(10, 2) DEFAULT NULL COMMENT '价格区间（最高价-最低价）',
    
    -- 技术指标（收盘时计算）
    `ma5` DECIMAL(10, 2) DEFAULT NULL COMMENT 'MA5均线',
    `ma10` DECIMAL(10, 2) DEFAULT NULL COMMENT 'MA10均线',
    `ma20` DECIMAL(10, 2) DEFAULT NULL COMMENT 'MA20均线',
    `ma60` DECIMAL(10, 2) DEFAULT NULL COMMENT 'MA60均线',
    `rsi` DECIMAL(8, 4) DEFAULT NULL COMMENT 'RSI指标',
    `macd` DECIMAL(10, 4) DEFAULT NULL COMMENT 'MACD',
    `macd_signal` DECIMAL(10, 4) DEFAULT NULL COMMENT 'MACD Signal',
    `macd_hist` DECIMAL(10, 4) DEFAULT NULL COMMENT 'MACD Histogram',
    
    -- 资金流向数据（如果可用）
    `main_net_inflow` DECIMAL(20, 2) DEFAULT NULL COMMENT '主力净流入（元）',
    `super_large_inflow` DECIMAL(20, 2) DEFAULT NULL COMMENT '超大单净流入（元）',
    `large_inflow` DECIMAL(20, 2) DEFAULT NULL COMMENT '大单净流入（元）',
    `medium_inflow` DECIMAL(20, 2) DEFAULT NULL COMMENT '中单净流入（元）',
    `small_inflow` DECIMAL(20, 2) DEFAULT NULL COMMENT '小单净流入（元）',
    
    -- 融资融券数据（如果可用）
    `margin_balance` DECIMAL(20, 2) DEFAULT NULL COMMENT '融资余额（元）',
    `short_balance` DECIMAL(20, 2) DEFAULT NULL COMMENT '融券余额（元）',
    `margin_ratio` DECIMAL(8, 4) DEFAULT NULL COMMENT '融资融券余额占比（%）',
    
    -- 其他数据（JSON格式，用于存储额外信息）
    `extra_data` JSON DEFAULT NULL COMMENT '其他数据（JSON格式，用于存储未来可能增加的字段）',
    
    -- 元数据
    `data_source` VARCHAR(50) DEFAULT 'akshare' COMMENT '数据来源',
    `data_quality_score` DECIMAL(5, 4) DEFAULT 1.0 COMMENT '数据质量得分（0-1）',
    `is_valid` TINYINT(1) DEFAULT 1 COMMENT '数据是否有效（1=有效，0=无效）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 唯一索引：股票代码 + 交易日期（确保每天每个股票只有一条记录）
    UNIQUE KEY `uk_symbol_date` (`symbol`, `trade_date`),
    
    -- 索引：加速查询
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_trade_date` (`trade_date`),
    INDEX `idx_symbol_date` (`symbol`, `trade_date`),
    INDEX `idx_date_range` (`trade_date`, `symbol`),
    INDEX `idx_volume` (`volume`),
    INDEX `idx_change_pct` (`change_pct`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票历史数据表（近10年详细数据）';
