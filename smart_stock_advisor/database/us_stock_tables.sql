-- 美股数据库表结构定义
-- 参考A股数据库模式，设计美股相关的数据表

-- 1. 美股板块表
CREATE TABLE IF NOT EXISTS `us_sectors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `sector_code` VARCHAR(20) NOT NULL COMMENT '板块代码（GICS Sector Code）',
    `sector_name_en` VARCHAR(100) NOT NULL COMMENT '板块名称（英文）',
    `sector_name_cn` VARCHAR(100) DEFAULT NULL COMMENT '板块名称（中文）',
    `sector_description` TEXT DEFAULT NULL COMMENT '板块描述',
    `parent_sector_code` VARCHAR(20) DEFAULT NULL COMMENT '父板块代码',
    `gics_level` INT DEFAULT 1 COMMENT 'GICS层级（1=Sector, 2=Industry Group, 3=Industry, 4=Sub-Industry）',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否活跃（1=是, 0=否）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_sector_code` (`sector_code`),
    INDEX `idx_sector_name_en` (`sector_name_en`),
    INDEX `idx_gics_level` (`gics_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='美股板块表（GICS分类）';

-- 2. 美股行业表
CREATE TABLE IF NOT EXISTS `us_industries` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `industry_code` VARCHAR(20) NOT NULL COMMENT '行业代码（GICS Industry Code）',
    `industry_name_en` VARCHAR(100) NOT NULL COMMENT '行业名称（英文）',
    `industry_name_cn` VARCHAR(100) DEFAULT NULL COMMENT '行业名称（中文）',
    `industry_description` TEXT DEFAULT NULL COMMENT '行业描述',
    `sector_code` VARCHAR(20) DEFAULT NULL COMMENT '所属板块代码',
    `gics_level` INT DEFAULT 3 COMMENT 'GICS层级',
    `parent_industry_code` VARCHAR(20) DEFAULT NULL COMMENT '父行业代码',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否活跃（1=是, 0=否）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_industry_code` (`industry_code`),
    INDEX `idx_sector_code` (`sector_code`),
    INDEX `idx_industry_name_en` (`industry_name_en`),
    INDEX `idx_gics_level` (`gics_level`),
    FOREIGN KEY (`sector_code`) REFERENCES `us_sectors`(`sector_code`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='美股行业表（GICS分类）';

-- 3. 美股股票基本信息表
CREATE TABLE IF NOT EXISTS `us_stock_info` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（如：AAPL）',
    `name_en` VARCHAR(200) DEFAULT NULL COMMENT '公司名称（英文）',
    `name_cn` VARCHAR(200) DEFAULT NULL COMMENT '公司名称（中文）',
    `exchange` VARCHAR(20) DEFAULT NULL COMMENT '交易所（NASDAQ/NYSE/AMEX等）',
    `market_cap` DECIMAL(20, 2) DEFAULT NULL COMMENT '市值（美元）',
    `sector_code` VARCHAR(20) DEFAULT NULL COMMENT '所属板块代码',
    `industry_code` VARCHAR(20) DEFAULT NULL COMMENT '所属行业代码',
    `sub_industry_code` VARCHAR(20) DEFAULT NULL COMMENT '所属子行业代码',
    `country` VARCHAR(50) DEFAULT 'US' COMMENT '国家',
    `currency` VARCHAR(10) DEFAULT 'USD' COMMENT '货币',
    `ipo_date` DATE DEFAULT NULL COMMENT 'IPO日期',
    `description` TEXT DEFAULT NULL COMMENT '公司描述',
    `website` VARCHAR(500) DEFAULT NULL COMMENT '公司官网',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否活跃交易（1=是, 0=否）',
    `is_delisted` TINYINT(1) DEFAULT 0 COMMENT '是否已退市（1=是, 0=否）',
    `delisted_date` DATE DEFAULT NULL COMMENT '退市日期',
    `data_source` VARCHAR(50) DEFAULT 'yfinance' COMMENT '数据来源',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_symbol` (`symbol`),
    INDEX `idx_sector_code` (`sector_code`),
    INDEX `idx_industry_code` (`industry_code`),
    INDEX `idx_exchange` (`exchange`),
    INDEX `idx_is_active` (`is_active`),
    FOREIGN KEY (`sector_code`) REFERENCES `us_sectors`(`sector_code`) ON DELETE SET NULL,
    FOREIGN KEY (`industry_code`) REFERENCES `us_industries`(`industry_code`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='美股股票基本信息表';

-- 4. 美股历史数据表（参考A股的stock_history_data表结构）
CREATE TABLE IF NOT EXISTS `us_stock_history_data` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 基本信息
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（如：AAPL）',
    `name` VARCHAR(200) DEFAULT NULL COMMENT '股票名称',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `exchange` VARCHAR(20) DEFAULT NULL COMMENT '交易所',
    
    -- 基本价格数据
    `open_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '开盘价（美元）',
    `close_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '收盘价（美元）',
    `high_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '最高价（美元）',
    `low_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '最低价（美元）',
    `adj_close_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '调整后收盘价（美元，复权价格）',
    `pre_close` DECIMAL(12, 4) DEFAULT NULL COMMENT '昨收价（美元）',
    `change_amount` DECIMAL(12, 4) DEFAULT NULL COMMENT '涨跌额（美元）',
    `change_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '涨跌幅（%）',
    
    -- 成交数据
    `volume` BIGINT DEFAULT NULL COMMENT '成交量（股）',
    `amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '成交额（美元）',
    `turnover_rate` DECIMAL(8, 4) DEFAULT NULL COMMENT '换手率（%）',
    `volume_ratio` DECIMAL(8, 4) DEFAULT NULL COMMENT '量比',
    
    -- 盘口数据（如果可用）
    `bid_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '买一价（美元）',
    `ask_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '卖一价（美元）',
    `bid_volume` BIGINT DEFAULT NULL COMMENT '买一量（股）',
    `ask_volume` BIGINT DEFAULT NULL COMMENT '卖一量（股）',
    
    -- 五档买卖盘数据（JSON格式）
    `bid_levels` JSON DEFAULT NULL COMMENT '五档买盘数据（JSON格式：[{price, volume}, ...]）',
    `ask_levels` JSON DEFAULT NULL COMMENT '五档卖盘数据（JSON格式：[{price, volume}, ...]）',
    
    -- 市值和估值
    `market_cap` DECIMAL(20, 2) DEFAULT NULL COMMENT '市值（美元）',
    `enterprise_value` DECIMAL(20, 2) DEFAULT NULL COMMENT '企业价值（美元）',
    `pe_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '市盈率（TTM）',
    `forward_pe` DECIMAL(10, 4) DEFAULT NULL COMMENT '前瞻市盈率',
    `pb_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '市净率',
    `ps_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '市销率',
    `ev_ebitda` DECIMAL(10, 4) DEFAULT NULL COMMENT 'EV/EBITDA',
    `dividend_yield` DECIMAL(8, 4) DEFAULT NULL COMMENT '股息率（%）',
    
    -- 振幅和波动
    `amplitude` DECIMAL(8, 4) DEFAULT NULL COMMENT '振幅（%）',
    `price_range` DECIMAL(12, 4) DEFAULT NULL COMMENT '价格区间（最高价-最低价）',
    `volatility` DECIMAL(8, 4) DEFAULT NULL COMMENT '波动率（%）',
    
    -- 技术指标（收盘时计算）
    `ma5` DECIMAL(12, 4) DEFAULT NULL COMMENT 'MA5均线',
    `ma10` DECIMAL(12, 4) DEFAULT NULL COMMENT 'MA10均线',
    `ma20` DECIMAL(12, 4) DEFAULT NULL COMMENT 'MA20均线',
    `ma50` DECIMAL(12, 4) DEFAULT NULL COMMENT 'MA50均线',
    `ma200` DECIMAL(12, 4) DEFAULT NULL COMMENT 'MA200均线',
    `rsi` DECIMAL(8, 4) DEFAULT NULL COMMENT 'RSI指标',
    `macd` DECIMAL(12, 4) DEFAULT NULL COMMENT 'MACD',
    `macd_signal` DECIMAL(12, 4) DEFAULT NULL COMMENT 'MACD Signal',
    `macd_hist` DECIMAL(12, 4) DEFAULT NULL COMMENT 'MACD Histogram',
    
    -- 资金流向数据（如果可用）
    `net_inflow` DECIMAL(20, 2) DEFAULT NULL COMMENT '净流入（美元）',
    `institutional_flow` DECIMAL(20, 2) DEFAULT NULL COMMENT '机构资金流（美元）',
    `retail_flow` DECIMAL(20, 2) DEFAULT NULL COMMENT '散户资金流（美元）',
    
    -- 期权数据（如果可用）
    `put_call_ratio` DECIMAL(8, 4) DEFAULT NULL COMMENT 'Put/Call比率',
    `implied_volatility` DECIMAL(8, 4) DEFAULT NULL COMMENT '隐含波动率（%）',
    
    -- 其他数据（JSON格式，用于存储额外信息）
    `extra_data` JSON DEFAULT NULL COMMENT '其他数据（JSON格式，用于存储未来可能增加的字段）',
    
    -- 元数据
    `data_source` VARCHAR(50) DEFAULT 'yfinance' COMMENT '数据来源（yfinance/akshare/其他）',
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
    INDEX `idx_change_pct` (`change_pct`),
    INDEX `idx_exchange` (`exchange`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='美股历史数据表（近10年详细数据）';

-- 5. 美股板块股票映射表（多对多关系）
CREATE TABLE IF NOT EXISTS `us_sector_stock_map` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `sector_code` VARCHAR(20) NOT NULL COMMENT '板块代码',
    `weight` DECIMAL(8, 4) DEFAULT NULL COMMENT '权重（如果是ETF或指数成分股）',
    `is_primary` TINYINT(1) DEFAULT 1 COMMENT '是否主要板块（1=是, 0=否，一只股票可能属于多个板块）',
    `start_date` DATE DEFAULT NULL COMMENT '开始日期',
    `end_date` DATE DEFAULT NULL COMMENT '结束日期（如果股票退出该板块）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_symbol_sector` (`symbol`, `sector_code`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_sector_code` (`sector_code`),
    FOREIGN KEY (`symbol`) REFERENCES `us_stock_info`(`symbol`) ON DELETE CASCADE,
    FOREIGN KEY (`sector_code`) REFERENCES `us_sectors`(`sector_code`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='美股板块股票映射表';

-- 6. 美股行业股票映射表（多对多关系）
CREATE TABLE IF NOT EXISTS `us_industry_stock_map` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `industry_code` VARCHAR(20) NOT NULL COMMENT '行业代码',
    `weight` DECIMAL(8, 4) DEFAULT NULL COMMENT '权重',
    `is_primary` TINYINT(1) DEFAULT 1 COMMENT '是否主要行业',
    `start_date` DATE DEFAULT NULL COMMENT '开始日期',
    `end_date` DATE DEFAULT NULL COMMENT '结束日期',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_symbol_industry` (`symbol`, `industry_code`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_industry_code` (`industry_code`),
    FOREIGN KEY (`symbol`) REFERENCES `us_stock_info`(`symbol`) ON DELETE CASCADE,
    FOREIGN KEY (`industry_code`) REFERENCES `us_industries`(`industry_code`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='美股行业股票映射表';

-- 7. 美股板块指数表（存储板块指数的历史数据）
CREATE TABLE IF NOT EXISTS `us_sector_index_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `sector_code` VARCHAR(20) NOT NULL COMMENT '板块代码',
    `index_symbol` VARCHAR(50) DEFAULT NULL COMMENT '指数代码（如：XLK for Technology）',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `open_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '开盘价',
    `close_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '收盘价',
    `high_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '最高价',
    `low_price` DECIMAL(12, 4) DEFAULT NULL COMMENT '最低价',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量',
    `change_pct` DECIMAL(8, 4) DEFAULT NULL COMMENT '涨跌幅（%）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_sector_date` (`sector_code`, `trade_date`),
    INDEX `idx_sector_code` (`sector_code`),
    INDEX `idx_trade_date` (`trade_date`),
    FOREIGN KEY (`sector_code`) REFERENCES `us_sectors`(`sector_code`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='美股板块指数历史数据表';
