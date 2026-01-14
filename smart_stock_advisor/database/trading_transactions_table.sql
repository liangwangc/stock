-- 交易记录表
-- 用于记录真实的交易情况（买入/卖出），方便后续的分析与决策

CREATE TABLE IF NOT EXISTS `trading_transactions` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `direction` VARCHAR(10) NOT NULL COMMENT '交易方向（BUY/SELL）',
    `price` DECIMAL(10, 2) NOT NULL COMMENT '交易价格（元）',
    `quantity` INT NOT NULL COMMENT '交易数量（股）',
    `total_amount` DECIMAL(15, 2) NOT NULL COMMENT '总金额（元）',
    `trading_date` DATE NOT NULL COMMENT '交易日期',
    `trading_time` DATETIME NOT NULL COMMENT '交易时间',
    
    -- 成本明细
    `commission` DECIMAL(10, 2) DEFAULT NULL COMMENT '佣金（元）',
    `stamp_tax` DECIMAL(10, 2) DEFAULT NULL COMMENT '印花税（元，仅卖出）',
    `transfer_fee` DECIMAL(10, 2) DEFAULT NULL COMMENT '过户费（元）',
    `slippage_cost` DECIMAL(10, 2) DEFAULT NULL COMMENT '滑点成本（元）',
    `total_cost` DECIMAL(10, 2) DEFAULT NULL COMMENT '总成本（元）',
    `cost_rate` DECIMAL(8, 4) DEFAULT NULL COMMENT '成本率（%）',
    
    -- 券商信息
    `broker_name` VARCHAR(50) DEFAULT NULL COMMENT '券商名称',
    
    -- 备注
    `notes` TEXT DEFAULT NULL COMMENT '备注',
    
    -- 关联信息（可选，用于关联预测决策）
    `decision_id` BIGINT DEFAULT NULL COMMENT '关联的实时交易决策ID',
    
    -- 时间戳
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_trading_date` (`trading_date`),
    INDEX `idx_trading_time` (`trading_time`),
    INDEX `idx_direction` (`direction`),
    INDEX `idx_decision_id` (`decision_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易记录表（真实交易）';
