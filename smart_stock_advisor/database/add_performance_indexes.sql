-- 数据库性能优化：添加索引
-- 本脚本用于优化常用查询的性能，添加缺失的索引
-- 执行方式：mysql -u root -p stock_data < add_performance_indexes.sql
-- 或使用Python：source database/add_performance_indexes.sql

-- ==================== 股票预测结果表索引优化 ====================

-- 1. 为 stock_predictions 表添加复合索引
-- 用途：加速"按股票+日期"查询（最常见查询）
-- 示例：SELECT * FROM stock_predictions WHERE symbol='000001' AND prediction_date='2024-01-01'
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_symbol_prediction_date` (`symbol`, `prediction_date`) 
COMMENT '股票代码+预测日期复合索引';

-- 用途：加速"获取某股票最新预测"查询
-- 示例：SELECT * FROM stock_predictions WHERE symbol='000001' ORDER BY prediction_date DESC LIMIT 1
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_symbol_prediction_time` (`symbol`, `prediction_time`) 
COMMENT '股票代码+预测时间复合索引';

-- 用途：加速"按日期获取所有预测"查询
-- 示例：SELECT * FROM stock_predictions WHERE prediction_date='2024-01-01' ORDER BY final_score DESC
ALTER TABLE `stock_predictions` 
ADD INDEX `idx_prediction_date_score` (`prediction_date`, `final_score`) 
COMMENT '预测日期+最终得分复合索引';

-- ==================== 实时交易决策表索引优化 ====================

-- 2. 为 realtime_trading_decisions 表添加复合索引
-- 用途：加速"按股票+日期"查询
ALTER TABLE `realtime_trading_decisions` 
ADD INDEX `idx_symbol_date` (`symbol`, `date`) 
COMMENT '股票代码+日期复合索引';

-- 用途：加速"按日期范围查询"（配合ORDER BY使用）
ALTER TABLE `realtime_trading_decisions` 
ADD INDEX `idx_date_timestamp` (`date`, `timestamp`) 
COMMENT '日期+时间戳复合索引';

-- 用途：加速"按信号强度查询"
ALTER TABLE `realtime_trading_decisions` 
ADD INDEX `idx_signal_strength` (`signal_strength`) 
COMMENT '信号强度索引';

-- 用途：加速"按操作建议查询"
ALTER TABLE `realtime_trading_decisions` 
ADD INDEX `idx_action` (`action`) 
COMMENT '操作建议索引';

-- ==================== 新闻表索引优化 ====================

-- 3. 为 news_articles 表添加复合索引
-- 用途：加速"按股票+发布时间"查询
ALTER TABLE `news_articles` 
ADD INDEX `idx_symbol_publish_time` (`symbol`, `publish_time`) 
COMMENT '股票代码+发布时间复合索引';

-- 用途：加速"按情感查询"
ALTER TABLE `news_articles` 
ADD INDEX `idx_sentiment_score` (`sentiment_score`) 
COMMENT '情感得分索引';

-- 用途：加速"按重要性评分查询"
ALTER TABLE `news_articles` 
ADD INDEX `idx_importance_score` (`importance_score`) 
COMMENT '重要性评分索引（如果字段存在）';

-- ==================== 定时任务历史表索引优化 ====================

-- 4. 为 scheduled_task_history 表添加复合索引
-- 用途：加速"按任务ID+开始时间"查询（查询某任务的执行历史）
ALTER TABLE `scheduled_task_history` 
ADD INDEX `idx_task_id_start_time` (`task_id`, `start_time`) 
COMMENT '任务ID+开始时间复合索引';

-- 用途：加速"按状态+开始时间"查询
ALTER TABLE `scheduled_task_history` 
ADD INDEX `idx_status_start_time` (`status`, `start_time`) 
COMMENT '状态+开始时间复合索引';

-- ==================== 新闻通知表索引优化 ====================

-- 5. 为 news_notifications 表添加索引
-- 用途：加速"查询待推送通知"（最常见查询）
-- 示例：SELECT * FROM news_notifications WHERE is_sent=0 ORDER BY created_at DESC
ALTER TABLE `news_notifications` 
ADD INDEX `idx_is_sent_created` (`is_sent`, `created_at`) 
COMMENT '是否已发送+创建时间复合索引';

-- 用途：加速"按新闻ID查询通知"
ALTER TABLE `news_notifications` 
ADD INDEX `idx_news_id` (`news_id`) 
COMMENT '新闻ID索引';

-- ==================== 用户会话表索引优化 ====================

-- 6. 为 user_sessions 表添加索引（如果表存在）
-- 用途：加速"按会话ID验证"查询
-- 示例：SELECT * FROM user_sessions WHERE session_id='xxx' AND is_active=1
-- 注意：需要先检查表是否存在，如果不存在则跳过
ALTER TABLE `user_sessions` 
ADD INDEX `idx_session_id_active` (`session_id`, `is_active`) 
COMMENT '会话ID+是否激活复合索引';

-- 用途：加速"按用户ID查询会话"
ALTER TABLE `user_sessions` 
ADD INDEX `idx_user_id_active` (`user_id`, `is_active`) 
COMMENT '用户ID+是否激活复合索引';

-- ==================== 预测因子表索引优化 ====================

-- 7. 为 prediction_factors 表添加复合索引
-- 用途：加速"按日期+股票查询因子"
ALTER TABLE `prediction_factors` 
ADD INDEX `idx_date_symbol_score` (`date`, `symbol`, `final_score`) 
COMMENT '日期+股票+最终得分复合索引';

-- ==================== 交易记录表索引优化 ====================

-- 8. 为 trading_transactions 表添加索引（如果表存在）
-- 用途：加速"按股票查询交易记录"
ALTER TABLE `trading_transactions` 
ADD INDEX `idx_symbol_trade_date` (`symbol`, `trade_date`) 
COMMENT '股票代码+交易日期复合索引';

-- 用途：加速"按交易类型查询"
ALTER TABLE `trading_transactions` 
ADD INDEX `idx_transaction_type` (`transaction_type`) 
COMMENT '交易类型索引';
