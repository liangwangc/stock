"""
股票历史数据存储模块
用于存储和管理股票历史详细数据（近10年），包括每日成交量、外盘、内盘、成本分布、委比等
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


class StockHistoryStorage:
    """股票历史数据存储管理器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        
        # 确保表存在
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """确保数据表存在，如果不存在则创建"""
        try:
            sql_file = os.path.join(project_root, "database", "stock_history_table.sql")
            if os.path.exists(sql_file):
                with open(sql_file, 'r', encoding='utf-8') as f:
                    create_sql = f.read()
                    # 执行创建表语句
                    try:
                        self.db.execute_update(create_sql)
                        self.logger.info("股票历史数据表已创建或已存在")
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            self.logger.warning(f"创建表时出错（可能已存在）: {str(e)}")
        except Exception as e:
            self.logger.warning(f"检查数据表时出错: {str(e)}")
    
    def save_stock_daily_data(self, symbol: str, date: str, data: Dict, use_full_fields: bool = None) -> bool:
        """
        保存股票单日数据
        
        Args:
            symbol: 股票代码
            date: 交易日期（格式：YYYY-MM-DD）
            data: 股票数据字典（包含所有字段）
            use_full_fields: 是否使用全量字段（True=58个字段，False=41个字段，None=自动判断）
                            - None: 自动判断（今日或最近3天的数据使用全量字段，历史数据使用41个字段）
                            - True: 强制使用全量字段（实时数据）
                            - False: 强制使用41个字段（历史数据）
        
        Returns:
            是否保存成功
        """
        try:
            # 自动判断是否使用全量字段
            if use_full_fields is None:
                # 判断日期是否是今天或最近3天（实时数据）
                today = datetime.now().date()
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                days_diff = (today - date_obj).days
                # 今日或最近3天的数据，且数据中包含实时数据字段，使用全量字段
                use_full_fields = (days_diff <= 3) and (
                    data.get('turnover_rate') is not None or
                    data.get('outer_volume') is not None or
                    data.get('inner_volume') is not None or
                    data.get('bid_levels') is not None or
                    data.get('ask_levels') is not None or
                    data.get('main_net_inflow') is not None or
                    data.get('total_market_cap') is not None or
                    data.get('float_market_cap') is not None
                )
            
            # 根据use_full_fields选择SQL语句
            if use_full_fields:
                # 实时数据：使用全量字段（58个字段）
                sql = """
                    INSERT INTO stock_history_data 
                    (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
                     change_amount, change_pct, volume, amount, turnover_rate, volume_ratio,
                     outer_volume, inner_volume, bid_ask_ratio,
                     bid_levels, ask_levels, bid_total_volume, ask_total_volume,
                     cost_distribution, cost_distribution_history, cost_distribution_intraday,
                     total_market_cap, float_market_cap, pe_ratio, pb_ratio,
                     limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
                     amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                     main_net_inflow, super_large_inflow, large_inflow, medium_inflow, small_inflow,
                     margin_balance, short_balance, margin_ratio,
                     extra_data, data_source, data_quality_score, is_valid)
                    VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, %s, %s, %s)
                """
                update_sql = """
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    period_type = VALUES(period_type),
                    open_price = VALUES(open_price),
                    close_price = VALUES(close_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    pre_close = VALUES(pre_close),
                    change_amount = VALUES(change_amount),
                    change_pct = VALUES(change_pct),
                    volume = VALUES(volume),
                    amount = VALUES(amount),
                    turnover_rate = VALUES(turnover_rate),
                    volume_ratio = VALUES(volume_ratio),
                    outer_volume = VALUES(outer_volume),
                    inner_volume = VALUES(inner_volume),
                    bid_ask_ratio = VALUES(bid_ask_ratio),
                    bid_levels = VALUES(bid_levels),
                    ask_levels = VALUES(ask_levels),
                    bid_total_volume = VALUES(bid_total_volume),
                    ask_total_volume = VALUES(ask_total_volume),
                    cost_distribution = VALUES(cost_distribution),
                    cost_distribution_history = VALUES(cost_distribution_history),
                    cost_distribution_intraday = VALUES(cost_distribution_intraday),
                    total_market_cap = VALUES(total_market_cap),
                    float_market_cap = VALUES(float_market_cap),
                    pe_ratio = VALUES(pe_ratio),
                    pb_ratio = VALUES(pb_ratio),
                    limit_up = VALUES(limit_up),
                    limit_down = VALUES(limit_down),
                    limit_pct = VALUES(limit_pct),
                    is_limit_up = VALUES(is_limit_up),
                    is_limit_down = VALUES(is_limit_down),
                    amplitude = VALUES(amplitude),
                    price_range = VALUES(price_range),
                    ma5 = VALUES(ma5),
                    ma10 = VALUES(ma10),
                    ma20 = VALUES(ma20),
                    ma60 = VALUES(ma60),
                    rsi = VALUES(rsi),
                    x2 = VALUES(x2),
                    macd = VALUES(macd),
                    macd_signal = VALUES(macd_signal),
                    macd_hist = VALUES(macd_hist),
                    main_net_inflow = VALUES(main_net_inflow),
                    super_large_inflow = VALUES(super_large_inflow),
                    large_inflow = VALUES(large_inflow),
                    medium_inflow = VALUES(medium_inflow),
                    small_inflow = VALUES(small_inflow),
                    margin_balance = VALUES(margin_balance),
                    short_balance = VALUES(short_balance),
                    margin_ratio = VALUES(margin_ratio),
                    extra_data = VALUES(extra_data),
                    data_quality_score = VALUES(data_quality_score),
                    is_valid = VALUES(is_valid),
                    updated_at = CURRENT_TIMESTAMP
                """
            else:
                # 历史数据：使用优化后的字段（41个字段）
                sql = """
                    INSERT INTO stock_history_data 
                    (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
                     change_amount, change_pct, volume, amount, 
                     -- turnover_rate,  -- 历史数据不可用：需要流通股本数据，历史数据通常不可用
                     volume_ratio,
                     -- outer_volume, inner_volume, bid_ask_ratio,  -- 历史数据不可用：盘口数据是实时数据，历史数据不可用
                     -- bid_levels, ask_levels, bid_total_volume, ask_total_volume,  -- 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                     cost_distribution, cost_distribution_history, 
                     -- cost_distribution_intraday,  -- 历史数据不可用：当日成本分布历史数据不可用
                     -- total_market_cap, float_market_cap,  -- 历史数据不可用：市值数据历史数据通常不可用
                     pe_ratio, pb_ratio,
                     limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
                     amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                     -- main_net_inflow, super_large_inflow, large_inflow, medium_inflow, small_inflow,  -- 历史数据不可用：资金流向是实时数据，历史数据不可用
                     margin_balance, short_balance, margin_ratio,
                     extra_data, data_source, data_quality_score, is_valid)
                    VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                update_sql = """
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    period_type = VALUES(period_type),
                    open_price = VALUES(open_price),
                    close_price = VALUES(close_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    pre_close = VALUES(pre_close),
                    change_amount = VALUES(change_amount),
                    change_pct = VALUES(change_pct),
                    volume = VALUES(volume),
                    amount = VALUES(amount),
                    -- turnover_rate = VALUES(turnover_rate),  -- 历史数据不可用：需要流通股本数据，历史数据通常不可用
                    volume_ratio = VALUES(volume_ratio),
                    -- outer_volume = VALUES(outer_volume),  -- 历史数据不可用：盘口数据是实时数据，历史数据不可用
                    -- inner_volume = VALUES(inner_volume),  -- 历史数据不可用：盘口数据是实时数据，历史数据不可用
                    -- bid_ask_ratio = VALUES(bid_ask_ratio),  -- 历史数据不可用：盘口数据是实时数据，历史数据不可用
                    -- bid_levels = VALUES(bid_levels),  -- 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                    -- ask_levels = VALUES(ask_levels),  -- 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                    -- bid_total_volume = VALUES(bid_total_volume),  -- 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                    -- ask_total_volume = VALUES(ask_total_volume),  -- 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                    cost_distribution = VALUES(cost_distribution),
                    cost_distribution_history = VALUES(cost_distribution_history),
                    -- cost_distribution_intraday = VALUES(cost_distribution_intraday),  -- 历史数据不可用：当日成本分布历史数据不可用
                    -- total_market_cap = VALUES(total_market_cap),  -- 历史数据不可用：市值数据历史数据通常不可用
                    -- float_market_cap = VALUES(float_market_cap),  -- 历史数据不可用：市值数据历史数据通常不可用
                    pe_ratio = VALUES(pe_ratio),
                    pb_ratio = VALUES(pb_ratio),
                    limit_up = VALUES(limit_up),
                    limit_down = VALUES(limit_down),
                    limit_pct = VALUES(limit_pct),
                    is_limit_up = VALUES(is_limit_up),
                    is_limit_down = VALUES(is_limit_down),
                    amplitude = VALUES(amplitude),
                    price_range = VALUES(price_range),
                    ma5 = VALUES(ma5),
                    ma10 = VALUES(ma10),
                    ma20 = VALUES(ma20),
                    ma60 = VALUES(ma60),
                    rsi = VALUES(rsi),
                    x2 = VALUES(x2),
                    macd = VALUES(macd),
                    macd_signal = VALUES(macd_signal),
                    macd_hist = VALUES(macd_hist),
                    -- main_net_inflow = VALUES(main_net_inflow),  -- 历史数据不可用：资金流向是实时数据，历史数据不可用
                    -- super_large_inflow = VALUES(super_large_inflow),  -- 历史数据不可用：资金流向是实时数据，历史数据不可用
                    -- large_inflow = VALUES(large_inflow),  -- 历史数据不可用：资金流向是实时数据，历史数据不可用
                    -- medium_inflow = VALUES(medium_inflow),  -- 历史数据不可用：资金流向是实时数据，历史数据不可用
                    -- small_inflow = VALUES(small_inflow),  -- 历史数据不可用：资金流向是实时数据，历史数据不可用
                    margin_balance = VALUES(margin_balance),
                    short_balance = VALUES(short_balance),
                    margin_ratio = VALUES(margin_ratio),
                    extra_data = VALUES(extra_data),
                    data_quality_score = VALUES(data_quality_score),
                    is_valid = VALUES(is_valid),
                    updated_at = CURRENT_TIMESTAMP
                """
            
            # 合并SQL语句
            sql = sql + update_sql
            
            # 优化：优先使用预序列化的JSON字段，如果没有则序列化（兼容旧代码）
            bid_levels_json = data.get('bid_levels_json') or (json.dumps(data.get('bid_levels', []), ensure_ascii=False) if data.get('bid_levels') else None)
            ask_levels_json = data.get('ask_levels_json') or (json.dumps(data.get('ask_levels', []), ensure_ascii=False) if data.get('ask_levels') else None)
            cost_distribution_json = data.get('cost_distribution_json') or (json.dumps(data.get('cost_distribution', {}), ensure_ascii=False) if data.get('cost_distribution') else None)
            cost_distribution_history_json = data.get('cost_distribution_history_json') or (json.dumps(data.get('cost_distribution_history', {}), ensure_ascii=False) if data.get('cost_distribution_history') else None)
            cost_distribution_intraday_json = data.get('cost_distribution_intraday_json') or (json.dumps(data.get('cost_distribution_intraday', {}), ensure_ascii=False) if data.get('cost_distribution_intraday') else None)
            extra_data_json = data.get('extra_data_json') or (json.dumps(data.get('extra_data', {}), ensure_ascii=False) if data.get('extra_data') else None)
            
            # 获取period_type，默认为'daily'
            period_type = data.get('period_type', 'daily')
            
            # 根据use_full_fields构建不同的参数列表
            if use_full_fields:
                # 实时数据：全量字段（58个参数）
                params = (
                    str(symbol).zfill(6),
                    data.get('name'),
                    date,
                    period_type,
                    data.get('open_price'),
                    data.get('close_price'),
                    data.get('high_price'),
                    data.get('low_price'),
                    data.get('pre_close'),
                    data.get('change_amount'),
                    data.get('change_pct'),
                    data.get('volume'),
                    data.get('amount'),
                    data.get('turnover_rate'),  # 实时数据可用
                    data.get('volume_ratio'),
                    data.get('outer_volume'),  # 实时数据可用
                    data.get('inner_volume'),  # 实时数据可用
                    data.get('bid_ask_ratio'),  # 实时数据可用
                    bid_levels_json,  # 实时数据可用
                    ask_levels_json,  # 实时数据可用
                    data.get('bid_total_volume'),  # 实时数据可用
                    data.get('ask_total_volume'),  # 实时数据可用
                    cost_distribution_json,
                    cost_distribution_history_json,
                    cost_distribution_intraday_json,  # 实时数据可用
                    data.get('total_market_cap'),  # 实时数据可用
                    data.get('float_market_cap'),  # 实时数据可用
                    data.get('pe_ratio'),
                    data.get('pb_ratio'),
                    data.get('limit_up'),
                    data.get('limit_down'),
                    data.get('limit_pct'),
                    1 if data.get('is_limit_up', False) else 0,
                    1 if data.get('is_limit_down', False) else 0,
                    data.get('amplitude'),
                    data.get('price_range'),
                    data.get('ma5'),
                    data.get('ma10'),
                    data.get('ma20'),
                    data.get('ma60'),
                    data.get('rsi'),
                    data.get('x2'),
                    data.get('macd'),
                    data.get('macd_signal'),
                    data.get('macd_hist'),
                    data.get('main_net_inflow'),  # 实时数据可用
                    data.get('super_large_inflow'),  # 实时数据可用
                    data.get('large_inflow'),  # 实时数据可用
                    data.get('medium_inflow'),  # 实时数据可用
                    data.get('small_inflow'),  # 实时数据可用
                    data.get('margin_balance'),
                    data.get('short_balance'),
                    data.get('margin_ratio'),
                    extra_data_json,
                    data.get('data_source', 'akshare'),
                    data.get('data_quality_score', 1.0),
                    1 if data.get('is_valid', True) else 0
                )
            else:
                # 历史数据：优化后的字段（41个参数）
                params = (
                    str(symbol).zfill(6),
                    data.get('name'),
                    date,
                    period_type,
                    data.get('open_price'),
                    data.get('close_price'),
                    data.get('high_price'),
                    data.get('low_price'),
                    data.get('pre_close'),
                    data.get('change_amount'),
                    data.get('change_pct'),
                    data.get('volume'),
                    data.get('amount'),
                    # data.get('turnover_rate'),  # 历史数据不可用：需要流通股本数据，历史数据通常不可用
                    data.get('volume_ratio'),
                    # data.get('outer_volume'),  # 历史数据不可用：盘口数据是实时数据，历史数据不可用
                    # data.get('inner_volume'),  # 历史数据不可用：盘口数据是实时数据，历史数据不可用
                    # data.get('bid_ask_ratio'),  # 历史数据不可用：盘口数据是实时数据，历史数据不可用
                    # bid_levels_json,  # 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                    # ask_levels_json,  # 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                    # data.get('bid_total_volume'),  # 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                    # data.get('ask_total_volume'),  # 历史数据不可用：五档买卖盘是实时数据，历史数据不可用
                    cost_distribution_json,
                    cost_distribution_history_json,
                    # cost_distribution_intraday_json,  # 历史数据不可用：当日成本分布历史数据不可用
                    # data.get('total_market_cap'),  # 历史数据不可用：市值数据历史数据通常不可用
                    # data.get('float_market_cap'),  # 历史数据不可用：市值数据历史数据通常不可用
                    data.get('pe_ratio'),
                    data.get('pb_ratio'),
                    data.get('limit_up'),
                    data.get('limit_down'),
                    data.get('limit_pct'),
                    1 if data.get('is_limit_up', False) else 0,
                    1 if data.get('is_limit_down', False) else 0,
                    data.get('amplitude'),
                    data.get('price_range'),
                    data.get('ma5'),
                    data.get('ma10'),
                    data.get('ma20'),
                    data.get('ma60'),
                    data.get('rsi'),
                    data.get('x2'),
                    data.get('macd'),
                    data.get('macd_signal'),
                    data.get('macd_hist'),
                    # data.get('main_net_inflow'),  # 历史数据不可用：资金流向是实时数据，历史数据不可用
                    # data.get('super_large_inflow'),  # 历史数据不可用：资金流向是实时数据，历史数据不可用
                    # data.get('large_inflow'),  # 历史数据不可用：资金流向是实时数据，历史数据不可用
                    # data.get('medium_inflow'),  # 历史数据不可用：资金流向是实时数据，历史数据不可用
                    # data.get('small_inflow'),  # 历史数据不可用：资金流向是实时数据，历史数据不可用
                    data.get('margin_balance'),
                    data.get('short_balance'),
                    data.get('margin_ratio'),
                    extra_data_json,
                    data.get('data_source', 'akshare'),
                    data.get('data_quality_score', 1.0),
                    1 if data.get('is_valid', True) else 0
                )
            
            # 调试：检查参数数量
            placeholder_count = sql.count('%s')
            param_count = len(params)
            if placeholder_count != param_count:
                self.logger.error(f"参数数量不匹配！SQL占位符数量: {placeholder_count}, 参数数量: {param_count}, use_full_fields: {use_full_fields}, symbol: {symbol}, date: {date}")
                self.logger.error(f"SQL片段: {sql[:200]}...")
                raise ValueError(f"参数数量不匹配：SQL占位符数量={placeholder_count}, 参数数量={param_count}")
            
            affected_rows = self.db.execute_update(sql, params)
            return affected_rows > 0
            
        except Exception as e:
            self.logger.error(f"保存股票历史数据失败 {symbol} {date}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def save_stock_daily_data_batch(self, batch_data: List[Tuple[str, str, Dict]], batch_size: int = 200) -> Dict:
        """
        批量保存股票历史数据（优化版，分离INSERT和UPDATE避免唯一索引锁竞争）
        
        优化策略：
        1. 先批量查询哪些数据已存在
        2. 分离为"需要插入"和"需要更新"两部分
        3. 分别批量INSERT和UPDATE，避免ON DUPLICATE KEY UPDATE的唯一索引检查锁竞争
        
        Args:
            batch_data: 数据列表，每个元素为 (symbol, date, data) 元组
            batch_size: 每批插入的记录数（默认200，使用executemany后可以适当增大，但考虑到内存和错误恢复，200较合适）
        
        Returns:
            保存结果字典：
            {
                'success_count': 成功数量,
                'fail_count': 失败数量,
                'total_count': 总数量
            }
        """
        if not batch_data:
            return {'success_count': 0, 'fail_count': 0, 'total_count': 0}
        
        success_count = 0
        fail_count = 0
        total_count = len(batch_data)
        
        try:
            # 优化：先批量查询哪些数据已存在，避免ON DUPLICATE KEY UPDATE的唯一索引检查锁竞争
            # 如果查询失败，回退到原方案（ON DUPLICATE KEY UPDATE）
            use_separate_insert_update = True
            existing_keys = set()
            
            try:
                # 收集所有唯一的(symbol, trade_date, period_type)组合
                unique_keys = []
                for symbol, date, data in batch_data:
                    period_type = data.get('period_type', 'daily')
                    unique_keys.append((str(symbol).zfill(6), date, period_type))
                
                # 批量查询已存在的记录（分批查询，避免SQL过长）
                if unique_keys:
                    query_batch_size = 500
                    for query_start in range(0, len(unique_keys), query_batch_size):
                        query_end = min(query_start + query_batch_size, len(unique_keys))
                        query_keys = unique_keys[query_start:query_end]
                        
                        # 构建OR条件查询
                        conditions = []
                        params = []
                        for symbol, date, period in query_keys:
                            conditions.append('(symbol = %s AND trade_date = %s AND period_type = %s)')
                            params.extend([symbol, date, period])
                        
                        sql = f"""
                            SELECT symbol, trade_date, period_type 
                            FROM stock_history_data 
                            WHERE {' OR '.join(conditions)}
                        """
                        
                        results = self.db.execute_query(sql, tuple(params))
                        for result in results:
                            symbol = str(result.get('symbol', '')).zfill(6)
                            trade_date = result.get('trade_date')
                            if isinstance(trade_date, datetime):
                                trade_date = trade_date.strftime('%Y-%m-%d')
                            elif isinstance(trade_date, str):
                                trade_date = trade_date.split()[0]
                            period_type = result.get('period_type', 'daily')
                            existing_keys.add((symbol, trade_date, period_type))
            except Exception as e:
                self.logger.warning(f"批量查询已存在数据失败: {str(e)}，将使用ON DUPLICATE KEY UPDATE")
                use_separate_insert_update = False
            
            # 分离为"需要插入"和"需要更新"两部分
            insert_batch = []
            update_batch = []
            
            if use_separate_insert_update:
                for symbol, date, data in batch_data:
                    period_type = data.get('period_type', 'daily')
                    key = (str(symbol).zfill(6), date, period_type)
                    
                    if key in existing_keys:
                        update_batch.append((symbol, date, data))
                    else:
                        insert_batch.append((symbol, date, data))
            else:
                # 查询失败，使用原方案（ON DUPLICATE KEY UPDATE）
                insert_batch = batch_data
            
            # 分批处理，避免SQL语句过长
            for batch_start in range(0, total_count, batch_size):
                batch_end = min(batch_start + batch_size, total_count)
                current_batch = batch_data[batch_start:batch_end]
                
                # 分离当前批次
                if use_separate_insert_update:
                    # 构建查找集合（基于(symbol, date, period_type)键）
                    insert_keys = set()
                    for symbol, date, data in insert_batch:
                        period_type = data.get('period_type', 'daily')
                        insert_keys.add((str(symbol).zfill(6), date, period_type))
                    
                    update_keys = set()
                    for symbol, date, data in update_batch:
                        period_type = data.get('period_type', 'daily')
                        update_keys.add((str(symbol).zfill(6), date, period_type))
                    
                    current_insert = []
                    current_update = []
                    for symbol, date, data in current_batch:
                        period_type = data.get('period_type', 'daily')
                        key = (str(symbol).zfill(6), date, period_type)
                        if key in insert_keys:
                            current_insert.append((symbol, date, data))
                        elif key in update_keys:
                            current_update.append((symbol, date, data))
                        else:
                            # 如果不在任何集合中，默认作为INSERT（新数据）
                            current_insert.append((symbol, date, data))
                else:
                    current_insert = current_batch
                    current_update = []
                
                try:
                    # 判断批次中是否有实时数据（用于决定使用哪种SQL模板）
                    # 检查第一条数据是否是实时数据
                    first_symbol, first_date, first_data = current_batch[0]
                    today = datetime.now().date()
                    try:
                        first_date_obj = datetime.strptime(first_date, '%Y-%m-%d').date()
                        days_diff = (today - first_date_obj).days
                    except Exception as e:
                        self.logger.warning(f"解析日期失败 {first_date}: {str(e)}，默认使用历史数据模板")
                        days_diff = 999  # 设置为很大的值，确保使用历史数据模板
                    
                    # 判断第一条数据是否是实时数据
                    # 注意：历史数据收集时，即使数据中有实时字段，也应该使用历史数据模板
                    # 只有明确是最近3天的数据且包含实时字段时，才使用实时数据模板
                    first_is_realtime = (days_diff <= 3) and (
                        first_data.get('turnover_rate') is not None or
                        first_data.get('outer_volume') is not None or
                        first_data.get('inner_volume') is not None or
                        first_data.get('bid_levels') is not None or
                        first_data.get('ask_levels') is not None or
                        first_data.get('main_net_inflow') is not None or
                        first_data.get('total_market_cap') is not None or
                        first_data.get('float_market_cap') is not None
                    )
                    
                    # 如果批次中有实时数据，需要分别处理（这里简化处理：如果第一条是实时数据，整批都使用全量字段）
                    # 注意：批量保存主要用于历史数据收集，实时数据通常使用单条保存
                    # 为了确保历史数据收集不受影响，只有在明确是最近3天的实时数据时才使用全量字段
                    use_full_fields_batch = first_is_realtime and days_diff <= 3
                    
                    self.logger.debug(f"批次判断: days_diff={days_diff}, first_is_realtime={first_is_realtime}, use_full_fields_batch={use_full_fields_batch}")
                    
                    # 优化：分离INSERT和UPDATE，避免唯一索引锁竞争
                    # 如果use_separate_insert_update=True，分离处理；否则使用原方案（ON DUPLICATE KEY UPDATE）
                    if use_separate_insert_update:
                        # 1. 先处理INSERT部分（纯INSERT，不需要检查唯一索引）
                        insert_sql = None  # 初始化为None，确保变量存在
                        if current_insert:
                            # 构建INSERT SQL（不包含ON DUPLICATE KEY UPDATE）
                            if use_full_fields_batch:
                                insert_sql = """
                                INSERT INTO stock_history_data 
                                (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
                                 change_amount, change_pct, volume, amount, turnover_rate, volume_ratio,
                                 outer_volume, inner_volume, bid_ask_ratio,
                                 bid_levels, ask_levels, bid_total_volume, ask_total_volume,
                                 cost_distribution, cost_distribution_history, cost_distribution_intraday,
                                 total_market_cap, float_market_cap, pe_ratio, pb_ratio,
                                 limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
                                 amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                                 main_net_inflow, super_large_inflow, large_inflow, medium_inflow, small_inflow,
                                 margin_balance, short_balance, margin_ratio,
                                 extra_data, data_source, data_quality_score, is_valid)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                        else:
                            insert_sql = """
                                INSERT INTO stock_history_data 
                                (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
                                 change_amount, change_pct, volume, amount, volume_ratio,
                                 cost_distribution, cost_distribution_history, pe_ratio, pb_ratio,
                                 limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
                                 amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                                 margin_balance, short_balance, margin_ratio,
                                 extra_data, data_source, data_quality_score, is_valid)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                        
                        # 准备INSERT参数列表
                        insert_params_list = []
                        for symbol, date, data in current_insert:
                            # JSON序列化（复用之前的逻辑）
                            bid_levels_json = data.get('bid_levels_json')
                            if bid_levels_json is None and data.get('bid_levels'):
                                bid_levels_json = json.dumps(data.get('bid_levels', []), ensure_ascii=False)
                            
                            ask_levels_json = data.get('ask_levels_json')
                            if ask_levels_json is None and data.get('ask_levels'):
                                ask_levels_json = json.dumps(data.get('ask_levels', []), ensure_ascii=False)
                            
                            cost_distribution_json = data.get('cost_distribution_json')
                            if cost_distribution_json is None and data.get('cost_distribution'):
                                cost_distribution_json = json.dumps(data.get('cost_distribution', {}), ensure_ascii=False)
                            
                            cost_distribution_history_json = data.get('cost_distribution_history_json')
                            if cost_distribution_history_json is None and data.get('cost_distribution_history'):
                                cost_distribution_history_json = json.dumps(data.get('cost_distribution_history', {}), ensure_ascii=False)
                            
                            cost_distribution_intraday_json = data.get('cost_distribution_intraday_json')
                            if cost_distribution_intraday_json is None and data.get('cost_distribution_intraday'):
                                cost_distribution_intraday_json = json.dumps(data.get('cost_distribution_intraday', {}), ensure_ascii=False)
                            
                            extra_data_json = data.get('extra_data_json')
                            if extra_data_json is None and data.get('extra_data'):
                                extra_data_json = json.dumps(data.get('extra_data', {}), ensure_ascii=False)
                            
                            period_type = data.get('period_type', 'daily')
                            
                            if use_full_fields_batch:
                                params = (
                                    str(symbol).zfill(6), data.get('name'), date, period_type,
                                    data.get('open_price'), data.get('close_price'), data.get('high_price'), data.get('low_price'),
                                    data.get('pre_close'), data.get('change_amount'), data.get('change_pct'),
                                    data.get('volume'), data.get('amount'), data.get('turnover_rate'), data.get('volume_ratio'),
                                    data.get('outer_volume'), data.get('inner_volume'), data.get('bid_ask_ratio'),
                                    bid_levels_json, ask_levels_json, data.get('bid_total_volume'), data.get('ask_total_volume'),
                                    cost_distribution_json, cost_distribution_history_json, cost_distribution_intraday_json,
                                    data.get('total_market_cap'), data.get('float_market_cap'), data.get('pe_ratio'), data.get('pb_ratio'),
                                    data.get('limit_up'), data.get('limit_down'), data.get('limit_pct'),
                                    1 if data.get('is_limit_up', False) else 0, 1 if data.get('is_limit_down', False) else 0,
                                    data.get('amplitude'), data.get('price_range'), data.get('ma5'), data.get('ma10'),
                                    data.get('ma20'), data.get('ma60'), data.get('rsi'), data.get('x2'),
                                    data.get('macd'), data.get('macd_signal'), data.get('macd_hist'),
                                    data.get('main_net_inflow'), data.get('super_large_inflow'), data.get('large_inflow'),
                                    data.get('medium_inflow'), data.get('small_inflow'),
                                    data.get('margin_balance'), data.get('short_balance'), data.get('margin_ratio'),
                                    extra_data_json, data.get('data_source', 'akshare'), data.get('data_quality_score', 1.0),
                                    1 if data.get('is_valid', True) else 0
                                )
                            else:
                                params = (
                                    str(symbol).zfill(6), data.get('name'), date, period_type,
                                    data.get('open_price'), data.get('close_price'), data.get('high_price'), data.get('low_price'),
                                    data.get('pre_close'), data.get('change_amount'), data.get('change_pct'),
                                    data.get('volume'), data.get('amount'), data.get('volume_ratio'),
                                    cost_distribution_json, cost_distribution_history_json,
                                    data.get('pe_ratio'), data.get('pb_ratio'), data.get('limit_up'), data.get('limit_down'),
                                    data.get('limit_pct'), 1 if data.get('is_limit_up', False) else 0,
                                    1 if data.get('is_limit_down', False) else 0, data.get('amplitude'), data.get('price_range'),
                                    data.get('ma5'), data.get('ma10'), data.get('ma20'), data.get('ma60'),
                                    data.get('rsi'), data.get('x2'), data.get('macd'), data.get('macd_signal'), data.get('macd_hist'),
                                    data.get('margin_balance'), data.get('short_balance'), data.get('margin_ratio'),
                                    extra_data_json, data.get('data_source', 'akshare'), data.get('data_quality_score', 1.0),
                                    1 if data.get('is_valid', True) else 0
                                )
                            insert_params_list.append(params)
                        
                        # 执行批量INSERT（不需要检查唯一索引，避免锁竞争）
                        if insert_sql and insert_params_list:
                            try:
                                affected_rows = self.db.execute_many(insert_sql, insert_params_list)
                                if affected_rows > 0:
                                    success_count += len(current_insert)
                                    self.logger.debug(f"批量INSERT成功: {len(current_insert)} 条记录（避免唯一索引检查）")
                                else:
                                    # 如果没有受影响的行，记录警告并回退
                                    self.logger.warning(f"批量INSERT未影响任何行，回退到ON DUPLICATE KEY UPDATE")
                                    current_update.extend(current_insert)
                            except Exception as e_insert:
                                self.logger.error(f"批量INSERT失败: {str(e_insert)}，回退到ON DUPLICATE KEY UPDATE")
                                import traceback
                                self.logger.error(f"INSERT异常详情: {traceback.format_exc()}")
                                # INSERT失败，将这部分数据加入UPDATE批次，使用ON DUPLICATE KEY UPDATE
                                current_update.extend(current_insert)
                        elif current_insert:
                            # 如果insert_sql未定义但有数据需要INSERT，回退到逐条插入
                            self.logger.warning(f"insert_sql未定义，但有待INSERT的数据 {len(current_insert)} 条，回退到逐条插入")
                            for symbol, date, data in current_insert:
                                try:
                                    if self.save_stock_daily_data(symbol, date, data):
                                        success_count += 1
                                    else:
                                        fail_count += 1
                                except Exception as e2:
                                    fail_count += 1
                                    self.logger.error(f"逐条INSERT失败 {symbol} {date}: {str(e2)}")
                        
                        # 2. 处理UPDATE部分（使用ON DUPLICATE KEY UPDATE，但数据量少，锁竞争减少）
                        update_sql = None  # 初始化为None，确保变量存在
                        if current_update:
                            # 构建UPDATE SQL（使用ON DUPLICATE KEY UPDATE）
                            if use_full_fields_batch:
                                update_sql = """
                                INSERT INTO stock_history_data 
                                (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
                                 change_amount, change_pct, volume, amount, turnover_rate, volume_ratio,
                                 outer_volume, inner_volume, bid_ask_ratio,
                                 bid_levels, ask_levels, bid_total_volume, ask_total_volume,
                                 cost_distribution, cost_distribution_history, cost_distribution_intraday,
                                 total_market_cap, float_market_cap, pe_ratio, pb_ratio,
                                 limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
                                 amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                                 main_net_inflow, super_large_inflow, large_inflow, medium_inflow, small_inflow,
                                 margin_balance, short_balance, margin_ratio,
                                 extra_data, data_source, data_quality_score, is_valid)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                name = VALUES(name), period_type = VALUES(period_type), open_price = VALUES(open_price),
                                close_price = VALUES(close_price), high_price = VALUES(high_price), low_price = VALUES(low_price),
                                pre_close = VALUES(pre_close), change_amount = VALUES(change_amount), change_pct = VALUES(change_pct),
                                volume = VALUES(volume), amount = VALUES(amount), turnover_rate = VALUES(turnover_rate),
                                volume_ratio = VALUES(volume_ratio), outer_volume = VALUES(outer_volume), inner_volume = VALUES(inner_volume),
                                bid_ask_ratio = VALUES(bid_ask_ratio), bid_levels = VALUES(bid_levels), ask_levels = VALUES(ask_levels),
                                bid_total_volume = VALUES(bid_total_volume), ask_total_volume = VALUES(ask_total_volume),
                                cost_distribution = VALUES(cost_distribution), cost_distribution_history = VALUES(cost_distribution_history),
                                cost_distribution_intraday = VALUES(cost_distribution_intraday), total_market_cap = VALUES(total_market_cap),
                                float_market_cap = VALUES(float_market_cap), pe_ratio = VALUES(pe_ratio), pb_ratio = VALUES(pb_ratio),
                                limit_up = VALUES(limit_up), limit_down = VALUES(limit_down), limit_pct = VALUES(limit_pct),
                                is_limit_up = VALUES(is_limit_up), is_limit_down = VALUES(is_limit_down), amplitude = VALUES(amplitude),
                                price_range = VALUES(price_range), ma5 = VALUES(ma5), ma10 = VALUES(ma10), ma20 = VALUES(ma20),
                                ma60 = VALUES(ma60), rsi = VALUES(rsi), x2 = VALUES(x2), macd = VALUES(macd),
                                macd_signal = VALUES(macd_signal), macd_hist = VALUES(macd_hist), main_net_inflow = VALUES(main_net_inflow),
                                super_large_inflow = VALUES(super_large_inflow), large_inflow = VALUES(large_inflow),
                                medium_inflow = VALUES(medium_inflow), small_inflow = VALUES(small_inflow),
                                margin_balance = VALUES(margin_balance), short_balance = VALUES(short_balance),
                                margin_ratio = VALUES(margin_ratio), extra_data = VALUES(extra_data),
                                data_source = VALUES(data_source), data_quality_score = VALUES(data_quality_score),
                                is_valid = VALUES(is_valid), updated_at = CURRENT_TIMESTAMP
                            """
                        else:
                            update_sql = """
                                INSERT INTO stock_history_data 
                                (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
                                 change_amount, change_pct, volume, amount, volume_ratio,
                                 cost_distribution, cost_distribution_history, pe_ratio, pb_ratio,
                                 limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
                                 amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                                 margin_balance, short_balance, margin_ratio,
                                 extra_data, data_source, data_quality_score, is_valid)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                name = VALUES(name), period_type = VALUES(period_type), open_price = VALUES(open_price),
                                close_price = VALUES(close_price), high_price = VALUES(high_price), low_price = VALUES(low_price),
                                pre_close = VALUES(pre_close), change_amount = VALUES(change_amount), change_pct = VALUES(change_pct),
                                volume = VALUES(volume), amount = VALUES(amount), volume_ratio = VALUES(volume_ratio),
                                cost_distribution = VALUES(cost_distribution), cost_distribution_history = VALUES(cost_distribution_history),
                                pe_ratio = VALUES(pe_ratio), pb_ratio = VALUES(pb_ratio), limit_up = VALUES(limit_up),
                                limit_down = VALUES(limit_down), limit_pct = VALUES(limit_pct), is_limit_up = VALUES(is_limit_up),
                                is_limit_down = VALUES(is_limit_down), amplitude = VALUES(amplitude), price_range = VALUES(price_range),
                                ma5 = VALUES(ma5), ma10 = VALUES(ma10), ma20 = VALUES(ma20), ma60 = VALUES(ma60),
                                rsi = VALUES(rsi), x2 = VALUES(x2), macd = VALUES(macd), macd_signal = VALUES(macd_signal),
                                macd_hist = VALUES(macd_hist), margin_balance = VALUES(margin_balance),
                                short_balance = VALUES(short_balance), margin_ratio = VALUES(margin_ratio),
                                extra_data = VALUES(extra_data), data_source = VALUES(data_source),
                                data_quality_score = VALUES(data_quality_score), is_valid = VALUES(is_valid), updated_at = CURRENT_TIMESTAMP
                            """
                        
                        # 准备UPDATE参数列表
                        update_params_list = []
                        for symbol, date, data in current_update:
                            # JSON序列化（复用之前的逻辑）
                            bid_levels_json = data.get('bid_levels_json')
                            if bid_levels_json is None and data.get('bid_levels'):
                                bid_levels_json = json.dumps(data.get('bid_levels', []), ensure_ascii=False)
                            
                            ask_levels_json = data.get('ask_levels_json')
                            if ask_levels_json is None and data.get('ask_levels'):
                                ask_levels_json = json.dumps(data.get('ask_levels', []), ensure_ascii=False)
                            
                            cost_distribution_json = data.get('cost_distribution_json')
                            if cost_distribution_json is None and data.get('cost_distribution'):
                                cost_distribution_json = json.dumps(data.get('cost_distribution', {}), ensure_ascii=False)
                            
                            cost_distribution_history_json = data.get('cost_distribution_history_json')
                            if cost_distribution_history_json is None and data.get('cost_distribution_history'):
                                cost_distribution_history_json = json.dumps(data.get('cost_distribution_history', {}), ensure_ascii=False)
                            
                            cost_distribution_intraday_json = data.get('cost_distribution_intraday_json')
                            if cost_distribution_intraday_json is None and data.get('cost_distribution_intraday'):
                                cost_distribution_intraday_json = json.dumps(data.get('cost_distribution_intraday', {}), ensure_ascii=False)
                            
                            extra_data_json = data.get('extra_data_json')
                            if extra_data_json is None and data.get('extra_data'):
                                extra_data_json = json.dumps(data.get('extra_data', {}), ensure_ascii=False)
                            
                            period_type = data.get('period_type', 'daily')
                            
                            if use_full_fields_batch:
                                params = (
                                    str(symbol).zfill(6), data.get('name'), date, period_type,
                                    data.get('open_price'), data.get('close_price'), data.get('high_price'), data.get('low_price'),
                                    data.get('pre_close'), data.get('change_amount'), data.get('change_pct'),
                                    data.get('volume'), data.get('amount'), data.get('turnover_rate'), data.get('volume_ratio'),
                                    data.get('outer_volume'), data.get('inner_volume'), data.get('bid_ask_ratio'),
                                    bid_levels_json, ask_levels_json, data.get('bid_total_volume'), data.get('ask_total_volume'),
                                    cost_distribution_json, cost_distribution_history_json, cost_distribution_intraday_json,
                                    data.get('total_market_cap'), data.get('float_market_cap'), data.get('pe_ratio'), data.get('pb_ratio'),
                                    data.get('limit_up'), data.get('limit_down'), data.get('limit_pct'),
                                    1 if data.get('is_limit_up', False) else 0, 1 if data.get('is_limit_down', False) else 0,
                                    data.get('amplitude'), data.get('price_range'), data.get('ma5'), data.get('ma10'),
                                    data.get('ma20'), data.get('ma60'), data.get('rsi'), data.get('x2'),
                                    data.get('macd'), data.get('macd_signal'), data.get('macd_hist'),
                                    data.get('main_net_inflow'), data.get('super_large_inflow'), data.get('large_inflow'),
                                    data.get('medium_inflow'), data.get('small_inflow'),
                                    data.get('margin_balance'), data.get('short_balance'), data.get('margin_ratio'),
                                    extra_data_json, data.get('data_source', 'akshare'), data.get('data_quality_score', 1.0),
                                    1 if data.get('is_valid', True) else 0
                                )
                            else:
                                params = (
                                    str(symbol).zfill(6), data.get('name'), date, period_type,
                                    data.get('open_price'), data.get('close_price'), data.get('high_price'), data.get('low_price'),
                                    data.get('pre_close'), data.get('change_amount'), data.get('change_pct'),
                                    data.get('volume'), data.get('amount'), data.get('volume_ratio'),
                                    cost_distribution_json, cost_distribution_history_json,
                                    data.get('pe_ratio'), data.get('pb_ratio'), data.get('limit_up'), data.get('limit_down'),
                                    data.get('limit_pct'), 1 if data.get('is_limit_up', False) else 0,
                                    1 if data.get('is_limit_down', False) else 0, data.get('amplitude'), data.get('price_range'),
                                    data.get('ma5'), data.get('ma10'), data.get('ma20'), data.get('ma60'),
                                    data.get('rsi'), data.get('x2'), data.get('macd'), data.get('macd_signal'), data.get('macd_hist'),
                                    data.get('margin_balance'), data.get('short_balance'), data.get('margin_ratio'),
                                    extra_data_json, data.get('data_source', 'akshare'), data.get('data_quality_score', 1.0),
                                    1 if data.get('is_valid', True) else 0
                                )
                            update_params_list.append(params)
                        
                        # 执行批量UPDATE（使用ON DUPLICATE KEY UPDATE，但数据量少，锁竞争减少）
                        if update_sql and update_params_list:
                            try:
                                affected_rows = self.db.execute_many(update_sql, update_params_list)
                                if affected_rows > 0:
                                    success_count += len(current_update)
                                    self.logger.debug(f"批量UPDATE成功: {len(current_update)} 条记录（使用ON DUPLICATE KEY UPDATE）")
                                else:
                                    # 如果没有受影响的行，记录警告并回退
                                    self.logger.warning(f"批量UPDATE未影响任何行，回退到逐条更新")
                                    for symbol, date, data in current_update:
                                        try:
                                            if self.save_stock_daily_data(symbol, date, data):
                                                success_count += 1
                                            else:
                                                fail_count += 1
                                        except Exception as e2:
                                            fail_count += 1
                                            self.logger.error(f"逐条更新失败 {symbol} {date}: {str(e2)}")
                            except Exception as e_update:
                                self.logger.error(f"批量UPDATE失败: {str(e_update)}，回退到逐条更新")
                                import traceback
                                self.logger.error(f"UPDATE异常详情: {traceback.format_exc()}")
                                for symbol, date, data in current_update:
                                    try:
                                        if self.save_stock_daily_data(symbol, date, data):
                                            success_count += 1
                                        else:
                                            fail_count += 1
                                    except Exception as e2:
                                        fail_count += 1
                                        self.logger.error(f"逐条更新失败 {symbol} {date}: {str(e2)}")
                        elif current_update:
                            # 如果update_sql未定义但有数据需要UPDATE，回退到逐条更新
                            self.logger.warning(f"update_sql未定义，但有待UPDATE的数据 {len(current_update)} 条，回退到逐条更新")
                            for symbol, date, data in current_update:
                                try:
                                    if self.save_stock_daily_data(symbol, date, data):
                                        success_count += 1
                                    else:
                                        fail_count += 1
                                except Exception as e2:
                                    fail_count += 1
                                    self.logger.error(f"逐条更新失败 {symbol} {date}: {str(e2)}")
                    
                    # 如果没有分离INSERT和UPDATE，使用原方案（ON DUPLICATE KEY UPDATE）
                    base_sql = None  # 初始化为None，确保变量存在
                    params_list = []
                    
                    if not use_separate_insert_update:
                        # 使用原方案（ON DUPLICATE KEY UPDATE）
                        if use_full_fields_batch:
                            base_sql = """
                                INSERT INTO stock_history_data 
                                (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
                                 change_amount, change_pct, volume, amount, turnover_rate, volume_ratio,
                                 outer_volume, inner_volume, bid_ask_ratio,
                                 bid_levels, ask_levels, bid_total_volume, ask_total_volume,
                                 cost_distribution, cost_distribution_history, cost_distribution_intraday,
                                 total_market_cap, float_market_cap, pe_ratio, pb_ratio,
                                 limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
                                 amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                                 main_net_inflow, super_large_inflow, large_inflow, medium_inflow, small_inflow,
                                 margin_balance, short_balance, margin_ratio,
                                 extra_data, data_source, data_quality_score, is_valid)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                name = VALUES(name), period_type = VALUES(period_type), open_price = VALUES(open_price),
                                close_price = VALUES(close_price), high_price = VALUES(high_price), low_price = VALUES(low_price),
                                pre_close = VALUES(pre_close), change_amount = VALUES(change_amount), change_pct = VALUES(change_pct),
                                volume = VALUES(volume), amount = VALUES(amount), turnover_rate = VALUES(turnover_rate),
                                volume_ratio = VALUES(volume_ratio), outer_volume = VALUES(outer_volume), inner_volume = VALUES(inner_volume),
                                bid_ask_ratio = VALUES(bid_ask_ratio), bid_levels = VALUES(bid_levels), ask_levels = VALUES(ask_levels),
                                bid_total_volume = VALUES(bid_total_volume), ask_total_volume = VALUES(ask_total_volume),
                                cost_distribution = VALUES(cost_distribution), cost_distribution_history = VALUES(cost_distribution_history),
                                cost_distribution_intraday = VALUES(cost_distribution_intraday), total_market_cap = VALUES(total_market_cap),
                                float_market_cap = VALUES(float_market_cap), pe_ratio = VALUES(pe_ratio), pb_ratio = VALUES(pb_ratio),
                                limit_up = VALUES(limit_up), limit_down = VALUES(limit_down), limit_pct = VALUES(limit_pct),
                                is_limit_up = VALUES(is_limit_up), is_limit_down = VALUES(is_limit_down), amplitude = VALUES(amplitude),
                                price_range = VALUES(price_range), ma5 = VALUES(ma5), ma10 = VALUES(ma10), ma20 = VALUES(ma20),
                                ma60 = VALUES(ma60), rsi = VALUES(rsi), x2 = VALUES(x2), macd = VALUES(macd),
                                macd_signal = VALUES(macd_signal), macd_hist = VALUES(macd_hist), main_net_inflow = VALUES(main_net_inflow),
                                super_large_inflow = VALUES(super_large_inflow), large_inflow = VALUES(large_inflow),
                                medium_inflow = VALUES(medium_inflow), small_inflow = VALUES(small_inflow),
                                margin_balance = VALUES(margin_balance), short_balance = VALUES(short_balance),
                                margin_ratio = VALUES(margin_ratio), extra_data = VALUES(extra_data),
                                data_source = VALUES(data_source), data_quality_score = VALUES(data_quality_score),
                                is_valid = VALUES(is_valid), updated_at = CURRENT_TIMESTAMP
                            """
                        else:
                            base_sql = """
                                INSERT INTO stock_history_data 
                                (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
                                 change_amount, change_pct, volume, amount, volume_ratio,
                                 cost_distribution, cost_distribution_history, pe_ratio, pb_ratio,
                                 limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
                                 amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                                 margin_balance, short_balance, margin_ratio,
                                 extra_data, data_source, data_quality_score, is_valid)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                name = VALUES(name), period_type = VALUES(period_type), open_price = VALUES(open_price),
                                close_price = VALUES(close_price), high_price = VALUES(high_price), low_price = VALUES(low_price),
                                pre_close = VALUES(pre_close), change_amount = VALUES(change_amount), change_pct = VALUES(change_pct),
                                volume = VALUES(volume), amount = VALUES(amount), volume_ratio = VALUES(volume_ratio),
                                cost_distribution = VALUES(cost_distribution), cost_distribution_history = VALUES(cost_distribution_history),
                                pe_ratio = VALUES(pe_ratio), pb_ratio = VALUES(pb_ratio), limit_up = VALUES(limit_up),
                                limit_down = VALUES(limit_down), limit_pct = VALUES(limit_pct), is_limit_up = VALUES(is_limit_up),
                                is_limit_down = VALUES(is_limit_down), amplitude = VALUES(amplitude), price_range = VALUES(price_range),
                                ma5 = VALUES(ma5), ma10 = VALUES(ma10), ma20 = VALUES(ma20), ma60 = VALUES(ma60),
                                rsi = VALUES(rsi), x2 = VALUES(x2), macd = VALUES(macd), macd_signal = VALUES(macd_signal),
                                macd_hist = VALUES(macd_hist), margin_balance = VALUES(margin_balance),
                                short_balance = VALUES(short_balance), margin_ratio = VALUES(margin_ratio),
                                extra_data = VALUES(extra_data), data_source = VALUES(data_source),
                                data_quality_score = VALUES(data_quality_score), is_valid = VALUES(is_valid), updated_at = CURRENT_TIMESTAMP
                            """
                        
                        # 准备参数列表（用于executemany）
                        for symbol, date, data in current_batch:
                            # 优化：优先使用预序列化的JSON字段（已在数据构建时序列化），避免重复序列化
                            # 如果*_json字段存在且不为None，直接使用；否则才序列化（兼容旧代码）
                            bid_levels_json = data.get('bid_levels_json')
                            if bid_levels_json is None and data.get('bid_levels'):
                                bid_levels_json = json.dumps(data.get('bid_levels', []), ensure_ascii=False)
                            
                            ask_levels_json = data.get('ask_levels_json')
                            if ask_levels_json is None and data.get('ask_levels'):
                                ask_levels_json = json.dumps(data.get('ask_levels', []), ensure_ascii=False)
                            
                            cost_distribution_json = data.get('cost_distribution_json')
                            if cost_distribution_json is None and data.get('cost_distribution'):
                                cost_distribution_json = json.dumps(data.get('cost_distribution', {}), ensure_ascii=False)
                            
                            cost_distribution_history_json = data.get('cost_distribution_history_json')
                            if cost_distribution_history_json is None and data.get('cost_distribution_history'):
                                cost_distribution_history_json = json.dumps(data.get('cost_distribution_history', {}), ensure_ascii=False)
                            
                            cost_distribution_intraday_json = data.get('cost_distribution_intraday_json')
                            if cost_distribution_intraday_json is None and data.get('cost_distribution_intraday'):
                                cost_distribution_intraday_json = json.dumps(data.get('cost_distribution_intraday', {}), ensure_ascii=False)
                            
                            extra_data_json = data.get('extra_data_json')
                            if extra_data_json is None and data.get('extra_data'):
                                extra_data_json = json.dumps(data.get('extra_data', {}), ensure_ascii=False)
                            period_type = data.get('period_type', 'daily')
                            
                            # 确保SQL模板与参数匹配
                            # 根据base_sql模板类型选择对应的参数（不再根据单个数据项判断）
                            # 历史数据收集时，统一使用历史数据模板（41个字段），即使数据中有实时字段也忽略
                            if base_sql and 'turnover_rate' in base_sql and use_full_fields_batch:
                                # 实时数据SQL模板：58个参数（仅在明确使用全量字段时）
                                params = (
                                    str(symbol).zfill(6), data.get('name'), date, period_type,
                                    data.get('open_price'), data.get('close_price'), data.get('high_price'), data.get('low_price'),
                                    data.get('pre_close'), data.get('change_amount'), data.get('change_pct'),
                                    data.get('volume'), data.get('amount'), data.get('turnover_rate'), data.get('volume_ratio'),
                                    data.get('outer_volume'), data.get('inner_volume'), data.get('bid_ask_ratio'),
                                    bid_levels_json, ask_levels_json, data.get('bid_total_volume'), data.get('ask_total_volume'),
                                    cost_distribution_json, cost_distribution_history_json, cost_distribution_intraday_json,
                                    data.get('total_market_cap'), data.get('float_market_cap'), data.get('pe_ratio'), data.get('pb_ratio'),
                                    data.get('limit_up'), data.get('limit_down'), data.get('limit_pct'),
                                    1 if data.get('is_limit_up', False) else 0, 1 if data.get('is_limit_down', False) else 0,
                                    data.get('amplitude'), data.get('price_range'), data.get('ma5'), data.get('ma10'),
                                    data.get('ma20'), data.get('ma60'), data.get('rsi'), data.get('x2'),
                                    data.get('macd'), data.get('macd_signal'), data.get('macd_hist'),
                                    data.get('main_net_inflow'), data.get('super_large_inflow'), data.get('large_inflow'),
                                    data.get('medium_inflow'), data.get('small_inflow'),
                                    data.get('margin_balance'), data.get('short_balance'), data.get('margin_ratio'),
                                    extra_data_json, data.get('data_source', 'akshare'), data.get('data_quality_score', 1.0),
                                    1 if data.get('is_valid', True) else 0
                                )
                            else:
                                # 历史数据SQL模板：41个参数（默认使用，历史数据收集时统一使用此模板）
                                # 注意：即使数据中有实时字段（如turnover_rate），也使用历史数据模板，这些字段会被忽略
                                params = (
                                    str(symbol).zfill(6), data.get('name'), date, period_type,
                                    data.get('open_price'), data.get('close_price'), data.get('high_price'), data.get('low_price'),
                                    data.get('pre_close'), data.get('change_amount'), data.get('change_pct'),
                                    data.get('volume'), data.get('amount'), data.get('volume_ratio'),
                                    cost_distribution_json, cost_distribution_history_json,
                                    data.get('pe_ratio'), data.get('pb_ratio'), data.get('limit_up'), data.get('limit_down'),
                                    data.get('limit_pct'), 1 if data.get('is_limit_up', False) else 0,
                                    1 if data.get('is_limit_down', False) else 0, data.get('amplitude'), data.get('price_range'),
                                    data.get('ma5'), data.get('ma10'), data.get('ma20'), data.get('ma60'),
                                    data.get('rsi'), data.get('x2'), data.get('macd'), data.get('macd_signal'), data.get('macd_hist'),
                                    data.get('margin_balance'), data.get('short_balance'), data.get('margin_ratio'),
                                    extra_data_json, data.get('data_source', 'akshare'), data.get('data_quality_score', 1.0),
                                    1 if data.get('is_valid', True) else 0
                                )
                            params_list.append(params)
                    
                    # 使用executemany执行批量插入（比构建长SQL更快）
                    if base_sql and params_list:
                        try:
                            affected_rows = self.db.execute_many(base_sql, params_list)
                            if affected_rows > 0:
                                success_count += len(current_batch)
                                # 记录实际保存的字段数量（41个字段，已注释掉16个历史数据不可用的字段）
                                if len(current_batch) == 1:  # 只在单条记录时显示字段数量，避免日志过多
                                    self.logger.debug(f"批量保存成功: {len(current_batch)} 条记录，每条记录包含 41 个字段")
                            else:
                                # 如果没有受影响的行，可能是数据已存在或SQL执行失败，回退到逐条插入
                                self.logger.warning(f"批量保存未影响任何行（affected_rows={affected_rows}），本批 {len(current_batch)} 条记录，回退到逐条插入")
                                for symbol, date, data in current_batch:
                                    try:
                                        if self.save_stock_daily_data(symbol, date, data):
                                            success_count += 1
                                        else:
                                            fail_count += 1
                                    except Exception as e2:
                                        fail_count += 1
                                        self.logger.error(f"逐条保存失败 {symbol} {date}: {str(e2)}")
                        except Exception as e_executemany:
                            # executemany失败，回退到逐条插入
                            self.logger.error(f"executemany失败，回退到逐条插入: {str(e_executemany)}")
                            import traceback
                            self.logger.error(f"executemany异常详情: {traceback.format_exc()}")
                            for symbol, date, data in current_batch:
                                try:
                                    if self.save_stock_daily_data(symbol, date, data):
                                        success_count += 1
                                    else:
                                        fail_count += 1
                                except Exception as e2:
                                    fail_count += 1
                                    self.logger.error(f"逐条保存失败 {symbol} {date}: {str(e2)}")
                    elif not use_separate_insert_update:
                        # 如果base_sql未定义且不使用分离INSERT/UPDATE，回退到逐条插入
                        self.logger.warning(f"base_sql未定义，回退到逐条插入，本批 {len(current_batch)} 条记录")
                        for symbol, date, data in current_batch:
                            try:
                                if self.save_stock_daily_data(symbol, date, data):
                                    success_count += 1
                                else:
                                    fail_count += 1
                            except Exception as e2:
                                fail_count += 1
                                self.logger.error(f"逐条保存失败 {symbol} {date}: {str(e2)}")
                
                except Exception as e:
                    # 批量插入失败，回退到逐条插入
                    self.logger.warning(f"批量插入失败，回退到逐条插入: {str(e)}")
                    for symbol, date, data in current_batch:
                        try:
                            if self.save_stock_daily_data(symbol, date, data):
                                success_count += 1
                            else:
                                fail_count += 1
                        except Exception as e2:
                            fail_count += 1
                            self.logger.error(f"逐条保存失败 {symbol} {date}: {str(e2)}")
            
            return {
                'success_count': success_count,
                'fail_count': fail_count,
                'total_count': total_count
            }
            
        except Exception as e:
            self.logger.error(f"批量保存股票历史数据失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'success_count': 0, 'fail_count': total_count, 'total_count': total_count}
    
    def update_stock_daily_data(self, symbol: str, date: str, update_data: Dict) -> bool:
        """
        更新股票单日数据的部分字段（只更新提供的字段，不覆盖已有数据）
        
        Args:
            symbol: 股票代码
            date: 交易日期（格式：YYYY-MM-DD）
            update_data: 要更新的字段字典（只包含要更新的字段）
        
        Returns:
            是否更新成功
        """
        try:
            symbol = str(symbol).zfill(6)
            
            # 构建UPDATE语句，只更新提供的字段
            set_clauses = []
            params = []
            
            # 基本字段
            if 'name' in update_data:
                set_clauses.append("name = %s")
                params.append(update_data['name'])
            
            if 'open_price' in update_data:
                set_clauses.append("open_price = %s")
                params.append(update_data['open_price'])
            
            if 'close_price' in update_data:
                set_clauses.append("close_price = %s")
                params.append(update_data['close_price'])
            
            if 'high_price' in update_data:
                set_clauses.append("high_price = %s")
                params.append(update_data['high_price'])
            
            if 'low_price' in update_data:
                set_clauses.append("low_price = %s")
                params.append(update_data['low_price'])
            
            if 'pre_close' in update_data:
                set_clauses.append("pre_close = %s")
                params.append(update_data['pre_close'])
            
            if 'change_amount' in update_data:
                set_clauses.append("change_amount = %s")
                params.append(update_data['change_amount'])
            
            if 'change_pct' in update_data:
                set_clauses.append("change_pct = %s")
                params.append(update_data['change_pct'])
            
            if 'volume' in update_data:
                set_clauses.append("volume = %s")
                params.append(update_data['volume'])
            
            if 'amount' in update_data:
                set_clauses.append("amount = %s")
                params.append(update_data['amount'])
            
            if 'turnover_rate' in update_data:
                set_clauses.append("turnover_rate = %s")
                params.append(update_data['turnover_rate'])
            
            if 'volume_ratio' in update_data:
                set_clauses.append("volume_ratio = %s")
                params.append(update_data['volume_ratio'])
            
            # 技术指标字段
            if 'amplitude' in update_data:
                set_clauses.append("amplitude = %s")
                params.append(update_data['amplitude'])
            
            if 'price_range' in update_data:
                set_clauses.append("price_range = %s")
                params.append(update_data['price_range'])
            
            if 'ma5' in update_data:
                set_clauses.append("ma5 = %s")
                params.append(update_data['ma5'])
            
            if 'ma10' in update_data:
                set_clauses.append("ma10 = %s")
                params.append(update_data['ma10'])
            
            if 'ma20' in update_data:
                set_clauses.append("ma20 = %s")
                params.append(update_data['ma20'])
            
            if 'ma60' in update_data:
                set_clauses.append("ma60 = %s")
                params.append(update_data['ma60'])
            
            if 'rsi' in update_data:
                set_clauses.append("rsi = %s")
                params.append(update_data['rsi'])
            
            if 'macd' in update_data:
                set_clauses.append("macd = %s")
                params.append(update_data['macd'])
            
            if 'macd_signal' in update_data:
                set_clauses.append("macd_signal = %s")
                params.append(update_data['macd_signal'])
            
            if 'macd_hist' in update_data:
                set_clauses.append("macd_hist = %s")
                params.append(update_data['macd_hist'])
            
            if 'x2' in update_data:
                set_clauses.append("x2 = %s")
                params.append(update_data['x2'])
            
            if 'volume_ratio' in update_data:
                set_clauses.append("volume_ratio = %s")
                params.append(update_data['volume_ratio'])
            
            # 成本分布字段（JSON格式）
            if 'cost_distribution' in update_data:
                cost_dist_json = json.dumps(update_data['cost_distribution'], ensure_ascii=False) if update_data['cost_distribution'] else None
                set_clauses.append("cost_distribution = %s")
                params.append(cost_dist_json)
            
            if 'cost_distribution_history' in update_data:
                cost_dist_history_json = json.dumps(update_data['cost_distribution_history'], ensure_ascii=False) if update_data['cost_distribution_history'] else None
                set_clauses.append("cost_distribution_history = %s")
                params.append(cost_dist_history_json)
            
            if 'cost_distribution_intraday' in update_data:
                cost_dist_intraday_json = json.dumps(update_data['cost_distribution_intraday'], ensure_ascii=False) if update_data['cost_distribution_intraday'] else None
                set_clauses.append("cost_distribution_intraday = %s")
                params.append(cost_dist_intraday_json)
            
            if not set_clauses:
                self.logger.warning(f"没有要更新的字段 {symbol} {date}")
                return False
            
            # 添加更新时间
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            # 构建SQL
            sql = f"""
                UPDATE stock_history_data 
                SET {', '.join(set_clauses)}
                WHERE symbol = %s AND trade_date = %s AND period_type = 'daily'
            """
            
            params.extend([symbol, date])
            
            affected_rows = self.db.execute_update(sql, tuple(params))
            return affected_rows > 0
            
        except Exception as e:
            self.logger.error(f"更新股票历史数据失败 {symbol} {date}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def get_stock_history_data(self, symbol: str, start_date: str = None, 
                               end_date: str = None, limit: int = None, 
                               period_type: str = 'daily') -> List[Dict]:
        """
        获取股票历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）
            limit: 限制返回条数
            period_type: 周期类型（daily/weekly/monthly/yearly），默认daily
        
        Returns:
            历史数据列表
        """
        try:
            symbol = str(symbol).zfill(6)
            conditions = ["symbol = %s"]
            params = [symbol]
            
            # 添加period_type过滤条件
            conditions.append("period_type = %s")
            params.append(period_type)
            
            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)
            
            where_clause = " AND ".join(conditions)
            
            sql = f"""
                SELECT * FROM stock_history_data 
                WHERE {where_clause}
                ORDER BY trade_date DESC
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            results = self.db.execute_query(sql, tuple(params))
            
            # 解析JSON字段
            for record in results:
                if record.get('bid_levels'):
                    try:
                        record['bid_levels'] = json.loads(record['bid_levels']) if isinstance(record['bid_levels'], str) else record['bid_levels']
                    except:
                        record['bid_levels'] = []
                if record.get('ask_levels'):
                    try:
                        record['ask_levels'] = json.loads(record['ask_levels']) if isinstance(record['ask_levels'], str) else record['ask_levels']
                    except:
                        record['ask_levels'] = []
                if record.get('cost_distribution'):
                    try:
                        record['cost_distribution'] = json.loads(record['cost_distribution']) if isinstance(record['cost_distribution'], str) else record['cost_distribution']
                    except:
                        record['cost_distribution'] = {}
            
            return results
            
        except Exception as e:
            self.logger.error(f"获取股票历史数据失败 {symbol}: {str(e)}")
            return []
    
    def get_latest_date(self, symbol: str = None, period_type: str = 'daily') -> Optional[str]:
        """
        获取最新数据的日期
        
        Args:
            symbol: 股票代码（如果提供，则获取该股票的最新日期；否则获取所有股票的最新日期）
            period_type: 周期类型（daily/weekly/monthly/yearly），默认daily
        
        Returns:
            最新日期（格式：YYYY-MM-DD），如果无数据返回None
        """
        try:
            if symbol:
                sql = "SELECT MAX(trade_date) as latest_date FROM stock_history_data WHERE symbol = %s AND period_type = %s"
                params = (str(symbol).zfill(6), period_type)
            else:
                sql = "SELECT MAX(trade_date) as latest_date FROM stock_history_data WHERE period_type = %s"
                params = (period_type,)
                params = None
            
            results = self.db.execute_query(sql, params)
            if results and results[0].get('latest_date'):
                latest_date = results[0]['latest_date']
                if isinstance(latest_date, datetime):
                    return latest_date.strftime('%Y-%m-%d')
                elif isinstance(latest_date, str):
                    return latest_date.split()[0]  # 提取日期部分
                return str(latest_date)
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取最新日期失败: {str(e)}")
            return None
    
    def check_data_exists(self, symbol: str, date: str, period_type: str = 'daily') -> bool:
        """
        检查数据是否存在
        
        Args:
            symbol: 股票代码
            date: 交易日期
            period_type: 周期类型（daily/weekly/monthly/yearly），默认daily
        
        Returns:
            是否存在
        """
        try:
            sql = "SELECT COUNT(*) as count FROM stock_history_data WHERE symbol = %s AND trade_date = %s AND period_type = %s"
            results = self.db.execute_query(sql, (str(symbol).zfill(6), date, period_type))
            if results and results[0].get('count', 0) > 0:
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"检查数据是否存在失败 {symbol} {date}: {str(e)}")
            return False
    
    def scan_stock_data_status(self, symbol: str, start_date: str, end_date: str, period_type: str = 'daily') -> Dict:
        """
        扫描股票数据状态（已有数据、缺失数据统计）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）
            period_type: K线周期类型（daily/weekly/monthly/yearly），默认为'daily'
        
        Returns:
            数据状态字典，包含：
            - total_dates: 总日期数
            - existing_dates: 已有日期数
            - missing_dates: 缺失日期数
            - existing_date_list: 已有日期列表
            - missing_date_list: 缺失日期列表
            - earliest_date: 最早日期
            - latest_date: 最晚日期
            - completeness_rate: 完整度（0-1）
        """
        try:
            symbol = str(symbol).zfill(6)
            
            # 生成日期范围
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            all_dates = []
            current = start
            while current <= end:
                # 跳过周末（周六和周日）
                if current.weekday() < 5:  # 0-4 是周一到周五
                    all_dates.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
            
            # 获取已存在的日期
            sql = "SELECT trade_date FROM stock_history_data WHERE symbol = %s AND trade_date BETWEEN %s AND %s AND period_type = %s ORDER BY trade_date"
            existing_results = self.db.execute_query(sql, (symbol, start_date, end_date, period_type))
            existing_dates = set()
            existing_date_list = []
            for result in existing_results:
                date = result.get('trade_date')
                if isinstance(date, datetime):
                    date_str = date.strftime('%Y-%m-%d')
                elif isinstance(date, str):
                    date_str = date.split()[0]
                else:
                    date_str = str(date)
                existing_dates.add(date_str)
                existing_date_list.append(date_str)
            
            # 找出缺失的日期
            missing_date_list = [d for d in all_dates if d not in existing_dates]
            
            # 计算统计信息
            total_dates = len(all_dates)
            existing_count = len(existing_dates)
            missing_count = len(missing_date_list)
            completeness_rate = existing_count / total_dates if total_dates > 0 else 0
            
            # 找出最早和最晚日期
            earliest_date = existing_date_list[0] if existing_date_list else None
            latest_date = existing_date_list[-1] if existing_date_list else None
            
            return {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'total_dates': total_dates,
                'existing_count': existing_count,
                'missing_count': missing_count,
                'existing_date_list': existing_date_list,
                'missing_date_list': missing_date_list,
                'earliest_date': earliest_date,
                'latest_date': latest_date,
                'completeness_rate': completeness_rate
            }
            
        except Exception as e:
            self.logger.error(f"扫描股票数据状态失败 {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'total_dates': 0,
                'existing_count': 0,
                'missing_count': 0,
                'existing_date_list': [],
                'missing_date_list': [],
                'earliest_date': None,
                'latest_date': None,
                'completeness_rate': 0.0
            }
    
    def get_missing_dates(self, symbol: str, start_date: str, end_date: str, period_type: str = 'daily') -> List[str]:
        """
        获取缺失的日期列表
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）
            period_type: K线周期类型（daily/weekly/monthly/yearly），默认为'daily'
        
        Returns:
            缺失的日期列表
        """
        try:
            symbol = str(symbol).zfill(6)
            
            # 生成日期范围
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            all_dates = []
            current = start
            while current <= end:
                # 跳过周末（周六和周日）
                if current.weekday() < 5:  # 0-4 是周一到周五
                    all_dates.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
            
            # 获取已存在的日期
            sql = "SELECT trade_date FROM stock_history_data WHERE symbol = %s AND trade_date BETWEEN %s AND %s AND period_type = %s"
            existing_results = self.db.execute_query(sql, (symbol, start_date, end_date, period_type))
            existing_dates = set()
            for result in existing_results:
                date = result.get('trade_date')
                if isinstance(date, datetime):
                    existing_dates.add(date.strftime('%Y-%m-%d'))
                elif isinstance(date, str):
                    existing_dates.add(date.split()[0])
                else:
                    existing_dates.add(str(date))
            
            # 找出缺失的日期
            missing_dates = [d for d in all_dates if d not in existing_dates]
            
            return missing_dates
            
        except Exception as e:
            self.logger.error(f"获取缺失日期失败 {symbol}: {str(e)}")
            return []
