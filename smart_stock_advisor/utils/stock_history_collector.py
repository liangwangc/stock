"""
股票历史数据采集模块
用于采集和存储股票历史详细数据（近10年），包括每日成交量、外盘、内盘、成本分布、委比等
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os
import time
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_storage import StockHistoryStorage
from data_source.stock_data_source import StockDataSource

logger = get_logger(__name__)


class StockHistoryCollector:
    """股票历史数据采集器"""
    
    def __init__(self):
        self.data_source = StockDataSource()
        self.storage = StockHistoryStorage()
        self.logger = logger
    
    def _get_pe_pb_from_db_or_api(self, symbol: str, date: str) -> Optional[Dict]:
        """
        获取PE/PB数据（优先从数据库获取，如果没有则调用API）
        
        优化策略：
        1. PE/PB优先从数据库今日数据获取（避免重复API调用）
        2. 如果数据库没有，调用API获取（确保PE/PB数据完整）
        
        Args:
            symbol: 股票代码
            date: 交易日期（格式：YYYY-MM-DD）
        
        Returns:
            包含pe_ratio和pb_ratio的字典，如果获取失败返回None
        """
        try:
            # 优先从数据库获取PE/PB
            sql = "SELECT pe_ratio, pb_ratio FROM stock_history_data WHERE symbol = %s AND trade_date = %s LIMIT 1"
            result = self.storage.db.execute_query(sql, (str(symbol).zfill(6), date))
            
            if result and len(result) > 0:
                pe_ratio = result[0].get('pe_ratio')
                pb_ratio = result[0].get('pb_ratio')
                # 如果今日数据已有PE/PB，使用数据库中的值
                if pe_ratio is not None or pb_ratio is not None:
                    self.logger.debug(f"快速模式：从数据库获取PE/PB {symbol}，跳过API调用")
                    return {'pe_ratio': pe_ratio, 'pb_ratio': pb_ratio}
            
            # 数据库中没有PE/PB，调用API获取（确保数据完整）
            try:
                stock_info = self.data_source.get_stock_info(symbol, skip_pe_pb=False)
                if stock_info:
                    self.logger.debug(f"快速模式：数据库中没有PE/PB {symbol}，调用API获取")
                    return stock_info
            except Exception as e:
                self.logger.debug(f"快速模式：调用API获取PE/PB失败 {symbol}: {str(e)}")
                return None
                
        except Exception as e:
            self.logger.debug(f"快速模式：检查数据库PE/PB失败 {symbol}: {str(e)}，尝试调用API获取")
            # 如果数据库查询失败，尝试调用API获取
            try:
                stock_info = self.data_source.get_stock_info(symbol, skip_pe_pb=False)
                if stock_info:
                    self.logger.debug(f"快速模式：数据库查询失败，调用API获取PE/PB {symbol}")
                    return stock_info
            except Exception as e2:
                self.logger.debug(f"快速模式：调用API获取PE/PB失败 {symbol}: {str(e2)}")
                return None
        
        return None
    
    def collect_stock_daily_data(self, symbol: str, date: str, fast_mode: bool = False) -> Optional[Dict]:
        """
        采集股票单日数据
        
        Args:
            symbol: 股票代码
            date: 交易日期（格式：YYYY-MM-DD）
            fast_mode: 快速模式（用于增量更新，跳过不必要的API调用）
        
        Returns:
            采集到的数据字典，如果失败返回None
        """
        try:
            if not fast_mode:
                self.logger.info(f"开始采集 {symbol} {date} 的数据...")
            
            # 转换日期格式
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_str = date_obj.strftime('%Y%m%d')
            
            # 先尝试获取股票名称（快速模式：优先从数据库获取）
            stock_name = ''
            if fast_mode:
                # 快速模式：优先从数据库获取股票名称
                try:
                    sql = "SELECT name FROM stock_history_data WHERE symbol = %s LIMIT 1"
                    result = self.storage.db.execute_query(sql, (str(symbol).zfill(6),))
                    if result and len(result) > 0:
                        stock_name = result[0].get('name', '')
                except Exception as e:
                    self.logger.debug(f"从数据库获取股票名称失败 {symbol}: {str(e)}")
            
            # 获取股票信息（用于获取PE/PB等字段）
            stock_info = None
            if not stock_name or stock_name == '':
                if not fast_mode:
                    # 非快速模式：使用API获取股票信息
                    try:
                        stock_info = self.data_source.get_stock_info(symbol)
                        if stock_info:
                            stock_name = stock_info.get('name', '') or stock_info.get('股票简称', '') or stock_info.get('股票名称', '')
                    except Exception as e:
                        self.logger.debug(f"获取股票信息失败 {symbol}: {str(e)}")
                else:
                    # 快速模式：优先从数据库获取PE/PB，如果没有则调用API获取
                    # 使用公共函数获取PE/PB数据
                    stock_info = self._get_pe_pb_from_db_or_api(symbol, date)
                
                # 如果还是没有获取到名称，从股票列表中获取（快速模式也尝试，但使用缓存）
                if not stock_name or stock_name == '':
                    try:
                        stock_list = self.data_source.get_all_stock_list(limit=None, sort_by_turnover=False, use_cache=True)
                        for stock in stock_list:
                            if str(stock.get('symbol', '')).strip() == str(symbol).strip():
                                stock_name = stock.get('name', '')
                                break
                    except Exception as e:
                        self.logger.debug(f"从股票列表获取名称失败 {symbol}: {str(e)}")
            else:
                # 快速模式下，如果已有股票名称，PE/PB优先从数据库获取，如果没有则调用API
                if fast_mode:
                    # 快速模式：优先从数据库获取PE/PB，如果没有则调用API获取
                    # 使用公共函数获取PE/PB数据
                    stock_info = self._get_pe_pb_from_db_or_api(symbol, date)
            
            data = {
                'symbol': symbol,
                'name': stock_name if stock_name else symbol,  # 如果获取不到名称，使用代码
                'trade_date': date,  # 添加交易日期
                'period_type': 'daily',  # 添加周期类型，默认为日线
                'data_source': 'akshare',
                'data_quality_score': 1.0,
                'is_valid': True,
                # 初始化这些字段为None，后续会尝试获取
                'pe_ratio': None,
                'pb_ratio': None,
                'total_market_cap': None,
                'float_market_cap': None
            }
            
            # 如果已经从stock_info获取到PE/PB，设置到data中
            if stock_info:
                if stock_info.get('pe_ratio'):
                    data['pe_ratio'] = stock_info.get('pe_ratio')
                if stock_info.get('pb_ratio'):
                    data['pb_ratio'] = stock_info.get('pb_ratio')
            
            # 1. 获取基本K线数据
            try:
                if fast_mode:
                    # 快速模式：优先从数据库获取历史数据（用于计算技术指标）
                    # 只获取当日数据从API，历史数据从数据库获取
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    # 获取当日数据（只获取当日，不获取前后10天）
                    days_data = self.data_source.get_stock_data(symbol, start_date=date, end_date=date)
                    
                    # 从数据库获取历史数据（用于计算技术指标，排除当日数据）
                    # 需要90天历史数据（与batch_update_technical_indicators.py一致，用于计算MACD和MA60）
                    try:
                        history_start = (date_obj - timedelta(days=90)).strftime('%Y-%m-%d')
                        history_end = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')  # 排除当日
                        history_data = self.storage.get_stock_history_data(
                            symbol=symbol,
                            start_date=history_start,
                            end_date=history_end,  # 只获取历史数据，不包含当日
                            limit=None
                        )
                        if history_data and len(history_data) > 0:
                            # 转换为DataFrame格式（与API返回格式一致）
                            history_records = []
                            for row in history_data:
                                history_records.append({
                                    'date': pd.to_datetime(row.get('trade_date')),
                                    'open': float(row.get('open_price', 0)) if row.get('open_price') else None,
                                    'high': float(row.get('high_price', 0)) if row.get('high_price') else None,
                                    'low': float(row.get('low_price', 0)) if row.get('low_price') else None,
                                    'close': float(row.get('close_price', 0)) if row.get('close_price') else None,
                                    'volume': float(row.get('volume', 0)) if row.get('volume') else None,
                                })
                            history_df = pd.DataFrame(history_records)
                            if not history_df.empty:
                                history_df.set_index('date', inplace=True)
                                # 合并当日数据和历史数据
                                if not days_data.empty:
                                    days_data = pd.concat([history_df, days_data])
                                else:
                                    days_data = history_df
                    except Exception as e:
                        self.logger.debug(f"从数据库获取历史数据失败 {symbol}: {str(e)}，将使用API获取")
                        # 回退到API获取
                        # 如果计算技术指标，需要90天历史数据；如果快速模式，只需要10天
                        if fast_mode:
                            start_date = (date_obj - timedelta(days=10)).strftime('%Y-%m-%d')
                        else:
                            start_date = (date_obj - timedelta(days=90)).strftime('%Y-%m-%d')  # 90天历史数据用于计算技术指标
                        end_date = (date_obj + timedelta(days=10)).strftime('%Y-%m-%d')
                        days_data = self.data_source.get_stock_data(symbol, start_date=start_date, end_date=end_date)
                else:
                    # 普通模式：从API获取
                    # 如果计算技术指标，需要90天历史数据（与batch_update_technical_indicators.py一致）
                    # 如果快速模式，只需要前后10天
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    if fast_mode:
                        start_date = (date_obj - timedelta(days=10)).strftime('%Y-%m-%d')
                    else:
                        start_date = (date_obj - timedelta(days=90)).strftime('%Y-%m-%d')  # 90天历史数据用于计算技术指标
                    end_date = (date_obj + timedelta(days=10)).strftime('%Y-%m-%d')
                    days_data = self.data_source.get_stock_data(symbol, start_date=start_date, end_date=end_date)
                target_row = None
                
                if not days_data.empty:
                    # 查找目标日期（必须精确匹配，不允许使用最近的日期）
                    date_idx = pd.to_datetime(date)
                    if date_idx in days_data.index:
                        target_row = days_data.loc[date_idx]
                    else:
                        # 如果找不到精确日期，返回None（不获取数据）
                        self.logger.warning(f"无法找到 {symbol} {date} 的精确数据，跳过该股票该日期的数据获取")
                        target_row = None
                
                if target_row is not None:
                    data['open_price'] = float(target_row.get('open', 0)) if pd.notna(target_row.get('open')) else None
                    data['close_price'] = float(target_row.get('close', 0)) if pd.notna(target_row.get('close')) else None
                    data['high_price'] = float(target_row.get('high', 0)) if pd.notna(target_row.get('high')) else None
                    data['low_price'] = float(target_row.get('low', 0)) if pd.notna(target_row.get('low')) else None
                    data['volume'] = int(target_row.get('volume', 0)) if pd.notna(target_row.get('volume')) else None
                    
                    # 添加成交额（如果API返回了成交额字段）
                    if 'amount' in days_data.columns and pd.notna(target_row.get('amount')):
                        data['amount'] = float(target_row.get('amount'))
                    elif data.get('close_price') and data.get('volume'):
                        # 如果没有成交额，计算近似值：成交额 = 收盘价 * 成交量（手转股：1手=100股）
                        data['amount'] = float(data['close_price'] * data['volume'] * 100)
                    
                    # 计算涨跌幅（如果有昨收价）
                    if 'close' in days_data.columns and len(days_data) > 1:
                        # 查找前一天的收盘价作为昨收
                        prev_date = date_idx - timedelta(days=1)
                        while prev_date >= days_data.index.min():
                            if prev_date in days_data.index:
                                data['pre_close'] = float(days_data.loc[prev_date, 'close'])
                                break
                            prev_date -= timedelta(days=1)
                        
                        if data.get('pre_close') and data.get('close_price'):
                            data['change_amount'] = data['close_price'] - data['pre_close']
                            data['change_pct'] = (data['change_amount'] / data['pre_close']) * 100 if data['pre_close'] > 0 else 0
                    
                    # 计算价格区间
                    if data.get('high_price') and data.get('low_price'):
                        data['price_range'] = data['high_price'] - data['low_price']
                    
                    # 计算振幅
                    if data.get('pre_close') and data.get('high_price') and data.get('low_price'):
                        amplitude = ((data['high_price'] - data['low_price']) / data['pre_close']) * 100 if data['pre_close'] > 0 else 0
                        data['amplitude'] = round(amplitude, 2)
                
            except Exception as e:
                self.logger.warning(f"获取基本K线数据失败 {symbol} {date}: {str(e)}")
            
            # 2. 获取实时行情数据（快速模式：跳过，只从K线数据获取价格信息）
            if not fast_mode:
                # 非快速模式：获取实时行情数据（包含更多信息）
                try:
                    realtime_quote = self.data_source.get_realtime_quote(symbol)
                    if realtime_quote:
                        # 更新价格数据（如果基本数据缺失）
                        if not data.get('open_price') and realtime_quote.get('open_price'):
                            data['open_price'] = realtime_quote.get('open_price')
                        if not data.get('close_price') and realtime_quote.get('current_price'):
                            data['close_price'] = realtime_quote.get('current_price')
                        if not data.get('high_price') and realtime_quote.get('high_price'):
                            data['high_price'] = realtime_quote.get('high_price')
                        if not data.get('low_price') and realtime_quote.get('low_price'):
                            data['low_price'] = realtime_quote.get('low_price')
                        if not data.get('pre_close') and realtime_quote.get('pre_close'):
                            data['pre_close'] = realtime_quote.get('pre_close')
                        if not data.get('volume') and realtime_quote.get('volume'):
                            data['volume'] = int(realtime_quote.get('volume', 0))
                        
                        # 其他数据
                        if realtime_quote.get('amount'):
                            data['amount'] = realtime_quote.get('amount')
                        if realtime_quote.get('turnover_rate'):
                            data['turnover_rate'] = realtime_quote.get('turnover_rate')
                        if realtime_quote.get('change_pct'):
                            data['change_pct'] = realtime_quote.get('change_pct')
                        if realtime_quote.get('change_amount'):
                            data['change_amount'] = realtime_quote.get('change_amount')
                        if realtime_quote.get('amplitude'):
                            data['amplitude'] = realtime_quote.get('amplitude')
                        if realtime_quote.get('pe_ratio'):
                            data['pe_ratio'] = realtime_quote.get('pe_ratio')
                        if realtime_quote.get('pb_ratio'):
                            data['pb_ratio'] = realtime_quote.get('pb_ratio')
                        if realtime_quote.get('total_value'):
                            data['total_market_cap'] = realtime_quote.get('total_value')
                        if realtime_quote.get('float_value'):
                            data['float_market_cap'] = realtime_quote.get('float_value')
                        if realtime_quote.get('limit_up'):
                            data['limit_up'] = realtime_quote.get('limit_up')
                        if realtime_quote.get('limit_down'):
                            data['limit_down'] = realtime_quote.get('limit_down')
                        if realtime_quote.get('limit_pct'):
                            data['limit_pct'] = realtime_quote.get('limit_pct')
                        # 更新股票名称（如果实时行情中有名称，优先使用）
                        if realtime_quote.get('name'):
                            data['name'] = realtime_quote.get('name')
                        # 如果之前没有获取到名称，尝试从实时行情获取
                        elif not data.get('name') or data.get('name') == symbol:
                            if realtime_quote.get('name'):
                                data['name'] = realtime_quote.get('name')
                        
                        # 判断是否涨跌停
                        if data.get('close_price') and data.get('limit_up'):
                            data['is_limit_up'] = abs(data['close_price'] - data['limit_up']) < 0.01
                        if data.get('close_price') and data.get('limit_down'):
                            data['is_limit_down'] = abs(data['close_price'] - data['limit_down']) < 0.01
                        
                except Exception as e:
                    self.logger.warning(f"获取实时行情数据失败 {symbol} {date}: {str(e)}")
            else:
                # 快速模式：跳过实时行情，只从K线数据获取价格信息
                # 但是仍然尝试获取市值数据（total_market_cap, float_market_cap）
                # 这些数据只能从实时行情获取，所以快速模式下会缺失
                # 如果需要这些数据，可以后续批量获取或使用非快速模式
                
                # 如果K线数据已有价格信息，计算成交额和涨跌停价
                if data.get('close_price') and data.get('volume'):
                    # 计算成交额（如果缺失）
                    if not data.get('amount'):
                        data['amount'] = float(data['close_price'] * data['volume'] * 100)  # 1手=100股
                
                # 计算涨跌停价（如果缺失）
                if data.get('pre_close') and not data.get('limit_up'):
                    pre_close = data['pre_close']
                    # ST股票涨跌停5%，普通股票10%，科创板/创业板20%
                    if symbol.startswith('688') or symbol.startswith('300'):
                        limit_pct = 0.20
                    else:
                        limit_pct = 0.10  # 默认10%
                    
                    data['limit_up'] = round(pre_close * (1 + limit_pct), 2)
                    data['limit_down'] = round(pre_close * (1 - limit_pct), 2)
                    data['limit_pct'] = limit_pct * 100
                    
                    # 判断是否涨跌停
                    if data.get('close_price'):
                        if abs(data['close_price'] - data['limit_up']) < 0.01:
                            data['is_limit_up'] = True
                        elif abs(data['close_price'] - data['limit_down']) < 0.01:
                            data['is_limit_down'] = True
                
                # 快速模式下，完全跳过get_realtime_quote（性能优化）
                # 注意：get_realtime_quote 很慢（约32秒），严重影响性能
                # 市值数据（total_market_cap, float_market_cap）可以：
                # 1. 后续批量获取（单独的任务）
                # 2. 从数据库历史数据获取（如果存在）
                # 3. 或使用get_stock_info API（更快，约1-2秒）
                # 为了大幅提升性能，快速模式下完全跳过get_realtime_quote
                
                # 尝试从数据库获取市值数据（如果存在）
                try:
                    sql = "SELECT total_market_cap, float_market_cap FROM stock_history_data WHERE symbol = %s AND trade_date < %s ORDER BY trade_date DESC LIMIT 1"
                    result = self.storage.db.execute_query(sql, (str(symbol).zfill(6), date))
                    if result and len(result) > 0:
                        if result[0].get('total_market_cap'):
                            data['total_market_cap'] = result[0].get('total_market_cap')
                        if result[0].get('float_market_cap'):
                            data['float_market_cap'] = result[0].get('float_market_cap')
                except Exception as e:
                    self.logger.debug(f"从数据库获取市值数据失败 {symbol}: {str(e)}")
                
            # 快速模式下不再调用get_realtime_quote（性能优化）
            # 如果需要市值数据，可以后续批量获取或使用get_stock_info API
            
            # 检查是否有必要的价格数据（如果没有价格数据，返回None，避免保存空数据）
            if not data.get('close_price') and not data.get('open_price'):
                # 如果没有收盘价和开盘价，说明没有获取到有效的K线数据
                self.logger.warning(f"{symbol} {date} 没有获取到有效的价格数据，跳过保存")
                return None
            
            # 3. 获取买卖盘数据（快速模式：跳过，这些数据历史数据不可用）
            data['outer_volume'] = None
            data['inner_volume'] = None
            data['bid_levels'] = None
            data['ask_levels'] = None
            data['bid_total_volume'] = None
            data['ask_total_volume'] = None
            data['bid_ask_ratio'] = None
            
            if not fast_mode:
                try:
                    bid_ask = self.data_source.get_bid_ask_data(symbol)
                    if bid_ask:
                        bids = bid_ask.get('bids', [])
                        asks = bid_ask.get('asks', [])
                        
                        if bids:
                            data['bid_levels'] = bids
                            data['bid_total_volume'] = sum(b.get('volume', 0) for b in bids)
                        
                        if asks:
                            data['ask_levels'] = asks
                            data['ask_total_volume'] = sum(a.get('volume', 0) for a in asks)
                        
                        if data.get('bid_total_volume') and data.get('ask_total_volume'):
                            total = data['bid_total_volume'] + data['ask_total_volume']
                            if total > 0:
                                data['bid_ask_ratio'] = ((data['bid_total_volume'] - data['ask_total_volume']) / total) * 100
                        
                        if bid_ask.get('outer_volume'):
                            data['outer_volume'] = bid_ask.get('outer_volume')
                        elif bid_ask.get('外盘'):
                            data['outer_volume'] = bid_ask.get('外盘')
                        if bid_ask.get('inner_volume'):
                            data['inner_volume'] = bid_ask.get('inner_volume')
                        elif bid_ask.get('内盘'):
                            data['inner_volume'] = bid_ask.get('内盘')
                except Exception as e:
                    self.logger.debug(f"获取买卖盘数据失败 {symbol} {date}: {str(e)}")
            
            # 4. 获取成本分布数据（快速模式：跳过，成本分布计算很慢）
            data['cost_distribution'] = None
            data['cost_distribution_history'] = None
            data['cost_distribution_intraday'] = None
            
            if not fast_mode:
                try:
                    if hasattr(self.data_source, 'get_cost_distribution'):
                        cost_dist = self.data_source.get_cost_distribution(symbol)
                        if cost_dist:
                            data['cost_distribution_history'] = cost_dist
                        
                        if hasattr(self.data_source, 'get_intraday_cost_distribution'):
                            intraday_cost = self.data_source.get_intraday_cost_distribution(symbol)
                            if intraday_cost:
                                data['cost_distribution_intraday'] = intraday_cost
                        
                        if cost_dist or data.get('cost_distribution_intraday'):
                            data['cost_distribution'] = {
                                'history': cost_dist or {},
                                'intraday': data.get('cost_distribution_intraday') or {}
                            }
                except Exception as e:
                    self.logger.debug(f"获取成本分布数据失败 {symbol} {date}: {str(e)}")
            
            # 5. 获取资金流向数据（快速模式：跳过，这些数据历史数据不可用）
            data['main_net_inflow'] = None
            data['super_large_inflow'] = None
            data['large_inflow'] = None
            data['medium_inflow'] = None
            data['small_inflow'] = None
            
            if not fast_mode:
                try:
                    if hasattr(self.data_source, 'get_realtime_capital_flow'):
                        capital_flow = self.data_source.get_realtime_capital_flow(symbol)
                        if capital_flow:
                            if capital_flow.get('main_net_inflow'):
                                data['main_net_inflow'] = capital_flow.get('main_net_inflow')
                            if capital_flow.get('super_large_net_inflow'):
                                data['super_large_inflow'] = capital_flow.get('super_large_net_inflow')
                            if capital_flow.get('large_net_inflow'):
                                data['large_inflow'] = capital_flow.get('large_net_inflow')
                            if capital_flow.get('medium_net_inflow'):
                                data['medium_inflow'] = capital_flow.get('medium_net_inflow')
                            if capital_flow.get('small_net_inflow'):
                                data['small_inflow'] = capital_flow.get('small_net_inflow')
                except Exception as e:
                    self.logger.debug(f"获取资金流向数据失败 {symbol} {date}: {str(e)}")
            
            # 6. 获取融资融券数据（快速模式：跳过，可以后续批量获取）
            data['margin_balance'] = None
            data['short_balance'] = None
            data['margin_ratio'] = None
            
            if not fast_mode:
                try:
                    if hasattr(self.data_source, 'get_margin_trading_data'):
                        margin_data = self.data_source.get_margin_trading_data(symbol)
                        if margin_data:
                            if margin_data.get('margin_balance'):
                                data['margin_balance'] = margin_data.get('margin_balance')
                            if margin_data.get('short_balance'):
                                data['short_balance'] = margin_data.get('short_balance')
                            if margin_data.get('margin_ratio'):
                                data['margin_ratio'] = margin_data.get('margin_ratio')
                except Exception as e:
                    self.logger.debug(f"获取融资融券数据失败 {symbol} {date}: {str(e)}")
            
            # 7. 从API获取技术指标（使用talib库，与证券公司算法一致）
            try:
                # 尝试使用talib库计算技术指标（行业标准，与证券公司算法一致）
                try:
                    import talib
                    TALIB_AVAILABLE = True
                except ImportError:
                    TALIB_AVAILABLE = False
                    self.logger.warning("talib库未安装，将使用pandas计算技术指标（可能与证券公司值不一致）。建议安装talib: pip install TA-Lib")
                
                # 计算技术指标需要至少90天历史数据（与batch_update_technical_indicators.py一致）
                # MACD需要至少26天，MA60需要至少60天，为了确保一致性，使用90天
                if not days_data.empty and len(days_data) >= 26:
                    closes = days_data['close'].values
                    highs = days_data['high'].values
                    lows = days_data['low'].values
                    
                    if TALIB_AVAILABLE:
                        # 使用talib库计算技术指标（与证券公司算法一致）
                        # MA（移动平均线）
                        ma5_values = talib.MA(closes, timeperiod=5)
                        ma10_values = talib.MA(closes, timeperiod=10)
                        ma20_values = talib.MA(closes, timeperiod=20)
                        ma60_values = talib.MA(closes, timeperiod=60)
                        
                        data['ma5'] = float(ma5_values[-1]) if pd.notna(ma5_values[-1]) else None
                        data['ma10'] = float(ma10_values[-1]) if pd.notna(ma10_values[-1]) else None
                        data['ma20'] = float(ma20_values[-1]) if pd.notna(ma20_values[-1]) else None
                        data['ma60'] = float(ma60_values[-1]) if pd.notna(ma60_values[-1]) else None
                        
                        # RSI（相对强弱指标，使用Wilder平滑，与证券公司一致）
                        if len(closes) >= 14:
                            rsi_values = talib.RSI(closes, timeperiod=14)
                            data['rsi'] = float(rsi_values[-1]) if pd.notna(rsi_values[-1]) else None
                        else:
                            data['rsi'] = None
                        
                        # MACD（使用标准参数：12, 26, 9）
                        if len(closes) >= 26:
                            macd_values, macd_signal_values, macd_hist_values = talib.MACD(
                                closes, 
                                fastperiod=12, 
                                slowperiod=26, 
                                signalperiod=9
                            )
                            data['macd'] = float(macd_values[-1]) if pd.notna(macd_values[-1]) else None
                            data['macd_signal'] = float(macd_signal_values[-1]) if pd.notna(macd_signal_values[-1]) else None
                            data['macd_hist'] = float(macd_hist_values[-1]) if pd.notna(macd_hist_values[-1]) else None
                        else:
                            data['macd'] = None
                            data['macd_signal'] = None
                            data['macd_hist'] = None
                        
                        # X2指标（自定义指标，talib没有，使用pandas计算）
                        if len(days_data) >= 20:
                            current_close = data.get('close_price')
                            if current_close is not None:
                                llv_low = lows[-20:].min()
                                hhv_high = highs[-20:].max()
                                range_width = hhv_high - llv_low
                                if range_width > 0:
                                    x2_value = (current_close - llv_low) / range_width * 100
                                    data['x2'] = float(round(x2_value, 4))
                                else:
                                    data['x2'] = 50.0
                            else:
                                data['x2'] = None
                        else:
                            data['x2'] = None
                    else:
                        # talib不可用，使用pandas计算（可能与证券公司值不一致）
                        closes_series = days_data['close']
                        
                        # 计算均线（根据各自所需的天数）
                        data['ma5'] = float(closes_series.tail(5).mean()) if len(closes_series) >= 5 else None
                        data['ma10'] = float(closes_series.tail(10).mean()) if len(closes_series) >= 10 else None
                        data['ma20'] = float(closes_series.tail(20).mean()) if len(closes_series) >= 20 else None
                        data['ma60'] = float(closes_series.tail(60).mean()) if len(closes_series) >= 60 else None
                        
                        # 计算RSI（需要至少14日数据）
                        if len(closes_series) >= 14:
                            delta = closes_series.diff()
                            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                            rs = gain / loss
                            rsi = 100 - (100 / (1 + rs))
                            data['rsi'] = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
                        else:
                            data['rsi'] = None
                        
                        # 计算MACD（证券行业标准计算方法）
                        # MACD标准计算：EMA12 - EMA26，Signal = EMA9(MACD)，Histogram = MACD - Signal
                        # EMA计算公式：EMA_t = (Price_t × α) + (EMA_{t-1} × (1-α))，其中α = 2/(N+1)
                        # pandas的ewm(span=N, adjust=False)使用标准EMA公式，α = 2/(span+1)
                        # 证券行业标准：初始值使用SMA，然后使用EMA公式递归计算
                        if len(closes_series) >= 26:
                            # 证券行业标准MACD计算
                            # 1. 计算EMA12（快速EMA）
                            # 标准方法：使用SMA12作为初始值，然后使用EMA公式
                            # pandas的ewm默认使用第一个值作为初始值，但标准方法使用SMA
                            # 为了与证券公司一致，我们使用ewm，它已经实现了标准EMA公式
                            # 注意：adjust=False表示使用标准EMA公式（α = 2/(N+1)）
                            ema12 = closes_series.ewm(span=12, adjust=False).mean()
                            
                            # 2. 计算EMA26（慢速EMA）
                            ema26 = closes_series.ewm(span=26, adjust=False).mean()
                            
                            # 3. MACD线 = EMA12 - EMA26
                            # 只计算有EMA26值的部分（从第26个数据点开始）
                            macd = ema12 - ema26
                            
                            # 4. Signal线 = MACD的9日EMA
                            # 标准方法：使用SMA9作为初始值，然后使用EMA公式
                            signal = macd.ewm(span=9, adjust=False).mean()
                            
                            # 5. Histogram = MACD - Signal
                            histogram = macd - signal
                            
                            # 取最后一个有效值（确保有足够的数据）
                            if len(macd) > 0 and pd.notna(macd.iloc[-1]):
                                data['macd'] = float(macd.iloc[-1])
                            else:
                                data['macd'] = None
                            
                            if len(signal) > 0 and pd.notna(signal.iloc[-1]):
                                data['macd_signal'] = float(signal.iloc[-1])
                            else:
                                data['macd_signal'] = None
                            
                            if len(histogram) > 0 and pd.notna(histogram.iloc[-1]):
                                data['macd_hist'] = float(histogram.iloc[-1])
                            else:
                                data['macd_hist'] = None
                        else:
                            data['macd'] = None
                            data['macd_signal'] = None
                            data['macd_hist'] = None
                        
                        # 计算X_2指标（收盘价在20日价格区间中的相对位置，至少需要20日数据）
                        if len(days_data) >= 20:
                            highs_series = days_data['high']
                            lows_series = days_data['low']
                            current_close = data.get('close_price')
                            if current_close is not None:
                                llv_low = lows_series.tail(20).min()
                                hhv_high = highs_series.tail(20).max()
                                range_width = hhv_high - llv_low
                                if range_width > 0:
                                    x2_value = (current_close - llv_low) / range_width * 100
                                    data['x2'] = float(round(x2_value, 4))
                                else:
                                    data['x2'] = 50.0
                            else:
                                data['x2'] = None
                        else:
                            data['x2'] = None
                else:
                    # 数据不足，设置为None
                    data['ma5'] = None
                    data['ma10'] = None
                    data['ma20'] = None
                    data['ma60'] = None
                    data['rsi'] = None
                    data['macd'] = None
                    data['macd_signal'] = None
                    data['macd_hist'] = None
                    data['x2'] = None
                    
            except Exception as e:
                self.logger.error(f"获取/计算技术指标失败 {symbol} {date}: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                # 失败时设置为None
                data['ma5'] = None
                data['ma10'] = None
                data['ma20'] = None
                data['ma60'] = None
                data['rsi'] = None
                data['macd'] = None
                data['macd_signal'] = None
                data['macd_hist'] = None
                data['x2'] = None
            
            # 8. 计算量比
            try:
                if not days_data.empty and len(days_data) >= 5 and data.get('volume'):
                    avg_volume = days_data['volume'].tail(5).mean()
                    if avg_volume > 0:
                        data['volume_ratio'] = data['volume'] / avg_volume
            except Exception as e:
                self.logger.debug(f"计算量比失败 {symbol} {date}: {str(e)}")
            
            # 优化：在数据构建时就序列化JSON字段，避免保存时重复序列化
            # 序列化JSON字段（如果存在）
            if 'bid_levels' in data and data['bid_levels']:
                data['bid_levels_json'] = json.dumps(data['bid_levels'], ensure_ascii=False)
            if 'ask_levels' in data and data['ask_levels']:
                data['ask_levels_json'] = json.dumps(data['ask_levels'], ensure_ascii=False)
            if 'cost_distribution' in data and data['cost_distribution']:
                data['cost_distribution_json'] = json.dumps(data['cost_distribution'], ensure_ascii=False)
            if 'cost_distribution_history' in data and data['cost_distribution_history']:
                data['cost_distribution_history_json'] = json.dumps(data['cost_distribution_history'], ensure_ascii=False)
            if 'cost_distribution_intraday' in data and data['cost_distribution_intraday']:
                data['cost_distribution_intraday_json'] = json.dumps(data['cost_distribution_intraday'], ensure_ascii=False)
            if 'extra_data' in data and data['extra_data']:
                data['extra_data_json'] = json.dumps(data['extra_data'], ensure_ascii=False)
            
            # 记录实际保存的字段数量（用于调试）
            # 实际保存41个字段：已注释掉16个历史数据不可用的字段
            # 注释掉的字段：turnover_rate(1), outer_volume/inner_volume/bid_ask_ratio(3), bid_levels/ask_levels/bid_total_volume/ask_total_volume(4), 
            # cost_distribution_intraday(1), total_market_cap/float_market_cap(2), main_net_inflow/super_large_inflow/large_inflow/medium_inflow/small_inflow(5)
            actual_fields_count = 41
            if not fast_mode:
                self.logger.debug(f"成功采集 {symbol} {date} 的数据，实际保存字段数量: {actual_fields_count} 个（已注释掉16个历史数据不可用的字段）")
                self.logger.info(f"成功采集 {symbol} {date} 的数据")
            return data
            
        except Exception as e:
            self.logger.error(f"采集股票数据失败 {symbol} {date}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def collect_stock_history_data(self, symbol: str, years: float = 10, 
                                   force_refresh: bool = False, 
                                   use_batch_mode: bool = True) -> Dict:
        """
        采集股票历史数据（近N年）
        
        Args:
            symbol: 股票代码
            years: 采集多少年的数据（默认10年，可以是小数，例如0.1表示约36天）
            force_refresh: 是否强制刷新（重新采集已存在的数据）
            use_batch_mode: 是否使用批量模式（默认True，大幅提升效率）
        
        Returns:
            采集结果字典
        """
        try:
            # 计算实际天数（支持小数年数）
            days = int(years * 365)
            if years < 1:
                # 对于小于1年的情况，使用更精确的计算
                days = int(years * 365.25)  # 考虑闰年
            elif years >= 1:
                # 对于大于等于1年的情况，使用整数天数
                days = int(years * 365)
            
            # 格式化显示
            if years >= 1:
                display_str = f"{years:.1f}年" if years != int(years) else f"{int(years)}年"
            elif years >= 1/12:
                months = years * 12
                display_str = f"{months:.1f}个月" if months != int(months) else f"{int(months)}个月"
            elif years >= 1/52:
                weeks = years * 52
                display_str = f"{weeks:.1f}周" if weeks != int(weeks) else f"{int(weeks)}周"
            else:
                display_str = f"{days}天"
            
            self.logger.info(f"开始采集 {symbol} 近{display_str}（{days}天）的历史数据（批量模式: {use_batch_mode}）...")
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # 获取缺失的日期列表
            if force_refresh:
                # 强制刷新，生成所有日期
                missing_dates = []
                current = start_date
                while current <= end_date:
                    if current.weekday() < 5:  # 跳过周末
                        missing_dates.append(current.strftime('%Y-%m-%d'))
                    current += timedelta(days=1)
            else:
                missing_dates = self.storage.get_missing_dates(symbol, start_date_str, end_date_str)
            
            if not missing_dates:
                self.logger.info(f"{symbol} 数据已完整，无需采集")
                return {
                    'symbol': symbol,
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'total_dates': 0,
                    'success_count': 0,
                    'fail_count': 0,
                    'success_rate': 1.0,
                    'success': True,
                    'message': '数据已完整'
                }
            
            self.logger.info(f"{symbol} 需要采集 {len(missing_dates)} 天的数据")
            
            # 使用批量模式（优化版）
            if use_batch_mode and len(missing_dates) > 10:
                return self._collect_stock_history_batch(symbol, missing_dates, start_date_str, end_date_str)
            
            # 使用逐日模式（兼容旧版本）
            success_count = 0
            fail_count = 0
            
            # 采集数据
            for i, date in enumerate(missing_dates, 1):
                try:
                    # 采集单日数据
                    data = self.collect_stock_daily_data(symbol, date)
                    
                    if data:
                        # 保存数据
                        if self.storage.save_stock_daily_data(symbol, date, data):
                            success_count += 1
                            if i % 50 == 0 or i == len(missing_dates):  # 每50条或最后一条才打印日志
                                self.logger.info(f"[{i}/{len(missing_dates)}] {symbol} 已保存 {success_count} 条数据")
                        else:
                            fail_count += 1
                            self.logger.warning(f"[{i}/{len(missing_dates)}] {symbol} {date} 数据保存失败")
                    else:
                        fail_count += 1
                        if i % 50 == 0:  # 减少日志输出
                            self.logger.warning(f"[{i}/{len(missing_dates)}] {symbol} {date} 数据采集失败")
                    
                    # 避免请求过快，添加延迟（多线程模式下减少延迟）
                    if i < len(missing_dates):
                        time.sleep(0.3)  # 减少延迟到0.3秒
                        
                except Exception as e:
                    fail_count += 1
                    if i % 50 == 0:  # 减少日志输出
                        self.logger.error(f"[{i}/{len(missing_dates)}] {symbol} {date} 采集异常: {str(e)}")
                    time.sleep(0.5)  # 出错后等待时间也减少
            
            result = {
                'symbol': symbol,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'total_dates': len(missing_dates),
                'success_count': success_count,
                'fail_count': fail_count,
                'success_rate': success_count / len(missing_dates) if missing_dates else 0,
                'success': success_count > 0
            }
            
            self.logger.info(f"{symbol} 历史数据采集完成: 成功 {success_count}/{len(missing_dates)}, 失败 {fail_count}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"采集股票历史数据失败 {symbol}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e)
            }
    
    def _collect_stock_history_batch(self, symbol: str, missing_dates: List[str], 
                                     start_date_str: str, end_date_str: str) -> Dict:
        """
        批量采集股票历史数据（优化版）
        
        优化点：
        1. 一次性获取整个日期范围的历史K线数据
        2. 减少不必要的API调用（历史数据不需要实时行情、买卖盘等）
        3. 批量保存数据
        
        Args:
            symbol: 股票代码
            missing_dates: 缺失的日期列表
            start_date_str: 开始日期
            end_date_str: 结束日期
        
        Returns:
            采集结果字典
        """
        try:
            self.logger.info(f"{symbol} 使用批量模式采集 {len(missing_dates)} 天的数据...")
            
            # 1. 批量获取历史K线数据（一次性获取整个日期范围）
            # 计算实际需要获取的日期范围（包含缺失日期的范围）
            if missing_dates:
                min_date = min(missing_dates)
                max_date = max(missing_dates)
            else:
                min_date = start_date_str
                max_date = end_date_str
            
            # 扩展日期范围，确保能获取到所有数据（前后各加5天）
            min_date_obj = datetime.strptime(min_date, '%Y-%m-%d') - timedelta(days=5)
            max_date_obj = datetime.strptime(max_date, '%Y-%m-%d') + timedelta(days=5)
            extended_start = min_date_obj.strftime('%Y-%m-%d')
            extended_end = max_date_obj.strftime('%Y-%m-%d')
            
            self.logger.info(f"{symbol} 批量获取K线数据: {extended_start} 至 {extended_end}")
            
            # 一次性获取整个日期范围的数据
            kline_data = self.data_source.get_stock_data(
                symbol=symbol,
                start_date=extended_start,
                end_date=extended_end
            )
            
            if kline_data.empty:
                self.logger.warning(f"{symbol} 批量获取K线数据失败，回退到逐日模式")
                return self._collect_stock_history_daily(symbol, missing_dates, start_date_str, end_date_str)
            
            # 2. 处理数据并批量保存
            success_count = 0
            fail_count = 0
            missing_dates_set = set(missing_dates)
            
            # 获取股票基本信息（只需要获取一次）
            # 优化：历史数据收集时跳过PE/PB获取，提升性能（PE/PB历史数据通常不可用）
            stock_info = self.data_source.get_stock_info(symbol, skip_pe_pb=True)
            
            # 提取股票名称（尝试多个来源）
            stock_name = ''
            if stock_info:
                # 优先从 stock_info 获取
                stock_name = stock_info.get('name', '') or stock_info.get('股票简称', '') or stock_info.get('股票名称', '')
            
            # 如果还是没有获取到名称，从股票列表中获取（使用字典索引优化）
            if not stock_name or stock_name == '':
                try:
                    stock_list = self.data_source.get_all_stock_list(limit=None, sort_by_turnover=False, use_cache=True)
                    # 构建字典索引，避免重复遍历
                    stock_dict = {str(stock.get('symbol', '')).strip(): stock.get('name', '') for stock in stock_list}
                    stock_name = stock_dict.get(str(symbol).strip(), '')
                except Exception as e:
                    self.logger.debug(f"从股票列表获取名称失败 {symbol}: {str(e)}")
            
            # 如果还是没有，使用股票代码作为名称
            if not stock_name or stock_name == '':
                stock_name = symbol
                self.logger.warning(f"{symbol} 无法获取股票名称，使用代码作为名称")
            
            # 获取股票估值指标（PE、PB等，历史数据可能不可用，但尝试获取）
            pe_ratio = stock_info.get('pe_ratio') if stock_info else None
            pb_ratio = stock_info.get('pb_ratio') if stock_info else None
            
            # 延迟成本分布计算（历史数据收集时跳过，可以后续批量计算）
            # 成本分布计算较慢，历史数据收集时跳过可以大幅提升性能
            cost_distribution_history = None
            # 注释掉成本分布获取，提升性能
            # try:
            #     if hasattr(self.data_source, 'get_cost_distribution'):
            #         # 获取最近60天的成本分布（基于历史K线数据计算）
            #         cost_dist = self.data_source.get_cost_distribution(symbol, days=60)
            #         if cost_dist and cost_dist.get('levels'):
            #             cost_distribution_history = cost_dist
            # except Exception as e:
            #     self.logger.debug(f"{symbol} 获取成本分布失败: {str(e)}")
            
            # 优化：一次性计算所有日期的技术指标（避免重复计算）
            # 在处理数据之前，先计算所有日期的技术指标
            technical_indicators = {}  # {date_str: {ma5: ..., rsi: ..., ...}}
            # 先定义closes变量，确保后续可以使用（即使技术指标计算失败）
            closes = kline_data['close'] if 'close' in kline_data.columns and len(kline_data) > 0 else pd.Series(dtype=float)
            
            if len(kline_data) >= 60:
                try:
                    self.logger.debug(f"{symbol} 一次性计算所有技术指标（{len(missing_dates)}天）...")
                    highs = kline_data['high']
                    lows = kline_data['low']
                    volumes = kline_data['volume'] if 'volume' in kline_data.columns else None
                    
                    # 尝试使用talib库计算技术指标（行业标准，与证券公司算法一致）
                    try:
                        import talib
                        TALIB_AVAILABLE = True
                    except ImportError:
                        TALIB_AVAILABLE = False
                        self.logger.warning("talib库未安装，将使用pandas计算技术指标（可能与证券公司值不一致）。建议安装talib: pip install TA-Lib")
                    
                    if TALIB_AVAILABLE:
                        # 使用talib计算（与证券公司算法一致）
                        closes_array = closes.values
                        highs_array = highs.values
                        lows_array = lows.values
                        
                        # 计算移动平均线（一次性计算所有日期的MA）
                        ma5_series = pd.Series(talib.MA(closes_array, timeperiod=5), index=kline_data.index)
                        ma10_series = pd.Series(talib.MA(closes_array, timeperiod=10), index=kline_data.index)
                        ma20_series = pd.Series(talib.MA(closes_array, timeperiod=20), index=kline_data.index)
                        ma60_series = pd.Series(talib.MA(closes_array, timeperiod=60), index=kline_data.index)
                        
                        # 计算RSI（使用Wilder平滑，与证券公司一致）
                        rsi_series = None
                        if len(closes_array) >= 14:
                            rsi_array = talib.RSI(closes_array, timeperiod=14)
                            rsi_series = pd.Series(rsi_array, index=kline_data.index)
                        
                        # 计算MACD（使用标准参数：12, 26, 9）
                        macd_series = None
                        macd_signal_series = None
                        macd_hist_series = None
                        if len(closes_array) >= 26:
                            macd_array, macd_signal_array, macd_hist_array = talib.MACD(
                                closes_array,
                                fastperiod=12,
                                slowperiod=26,
                                signalperiod=9
                            )
                            macd_series = pd.Series(macd_array, index=kline_data.index)
                            macd_signal_series = pd.Series(macd_signal_array, index=kline_data.index)
                            macd_hist_series = pd.Series(macd_hist_array, index=kline_data.index)
                    else:
                        # 使用pandas计算（可能与证券公司值不一致）
                        # 计算移动平均线（一次性计算所有日期的MA）
                        ma5_series = closes.rolling(window=5, min_periods=1).mean()
                        ma10_series = closes.rolling(window=10, min_periods=1).mean()
                        ma20_series = closes.rolling(window=20, min_periods=1).mean()
                        ma60_series = closes.rolling(window=60, min_periods=1).mean()
                        
                        # 计算RSI
                        rsi_series = None
                        if len(closes) >= 14:
                            delta = closes.diff()
                            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
                            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
                            rs = gain / loss
                            rsi_series = 100 - (100 / (1 + rs))
                        
                        # 计算MACD
                        macd_series = None
                        macd_signal_series = None
                        macd_hist_series = None
                        if len(closes) >= 26:
                            ema12 = closes.ewm(span=12, adjust=False).mean()
                            ema26 = closes.ewm(span=26, adjust=False).mean()
                            macd_series = ema12 - ema26
                            macd_signal_series = macd_series.ewm(span=9, adjust=False).mean()
                            macd_hist_series = macd_series - macd_signal_series
                    
                    # 计算X2指标（向量化优化）
                    x2_series = None
                    if len(kline_data) >= 20:
                        llv_low = lows.rolling(window=20, min_periods=1).min()
                        hhv_high = highs.rolling(window=20, min_periods=1).max()
                        range_width = hhv_high - llv_low
                        # 使用numpy向量化操作，避免循环
                        x2_series = pd.Series(
                            np.where(range_width > 0,
                                    (closes - llv_low) / range_width * 100,
                                    50.0),
                            index=kline_data.index
                        )
                    
                    # 计算量比
                    volume_ratio_series = None
                    if volumes is not None and len(volumes) >= 5:
                        avg_volume = volumes.rolling(window=5, min_periods=1).mean()
                        volume_ratio_series = volumes / avg_volume
                    
                    # 优化：使用向量化操作一次性提取所有日期的技术指标（避免循环和多次.loc[]访问）
                    # 将缺失日期转换为datetime索引，然后一次性提取所有指标值
                    missing_dates_objs = [pd.to_datetime(d) for d in missing_dates]
                    missing_dates_in_kline = [d for d in missing_dates_objs if d in kline_data.index]
                    
                    if missing_dates_in_kline:
                        # 创建DataFrame，一次性提取所有指标值
                        indicators_df = pd.DataFrame(index=missing_dates_in_kline)
                        
                        # 批量提取移动平均线
                        if len(ma5_series) > 0:
                            indicators_df['ma5'] = ma5_series.reindex(missing_dates_in_kline)
                            indicators_df['ma10'] = ma10_series.reindex(missing_dates_in_kline)
                            indicators_df['ma20'] = ma20_series.reindex(missing_dates_in_kline)
                            indicators_df['ma60'] = ma60_series.reindex(missing_dates_in_kline)
                        
                        # 批量提取RSI
                        if rsi_series is not None and len(rsi_series) > 0:
                            indicators_df['rsi'] = rsi_series.reindex(missing_dates_in_kline)
                        
                        # 批量提取MACD
                        if macd_series is not None and len(macd_series) > 0:
                            indicators_df['macd'] = macd_series.reindex(missing_dates_in_kline)
                            indicators_df['macd_signal'] = macd_signal_series.reindex(missing_dates_in_kline)
                            indicators_df['macd_hist'] = macd_hist_series.reindex(missing_dates_in_kline)
                        
                        # 批量提取X2
                        if x2_series is not None and len(x2_series) > 0:
                            indicators_df['x2'] = x2_series.reindex(missing_dates_in_kline)
                        
                        # 批量提取量比
                        if volume_ratio_series is not None and len(volume_ratio_series) > 0:
                            indicators_df['volume_ratio'] = volume_ratio_series.reindex(missing_dates_in_kline)
                        
                        # 转换为字典格式，只保留非空值
                        for date_obj in missing_dates_in_kline:
                            date_str = date_obj.strftime('%Y-%m-%d')
                            indicators = {}
                            
                            row = indicators_df.loc[date_obj]
                            if pd.notna(row.get('ma5')):
                                indicators['ma5'] = float(row['ma5'])
                            if pd.notna(row.get('ma10')):
                                indicators['ma10'] = float(row['ma10'])
                            if pd.notna(row.get('ma20')):
                                indicators['ma20'] = float(row['ma20'])
                            if pd.notna(row.get('ma60')):
                                indicators['ma60'] = float(row['ma60'])
                            if pd.notna(row.get('rsi')):
                                indicators['rsi'] = float(row['rsi'])
                            if pd.notna(row.get('macd')):
                                indicators['macd'] = float(row['macd'])
                            if pd.notna(row.get('macd_signal')):
                                indicators['macd_signal'] = float(row['macd_signal'])
                            if pd.notna(row.get('macd_hist')):
                                indicators['macd_hist'] = float(row['macd_hist'])
                            if pd.notna(row.get('x2')):
                                indicators['x2'] = float(round(row['x2'], 4))
                            if pd.notna(row.get('volume_ratio')):
                                indicators['volume_ratio'] = float(row['volume_ratio'])
                            
                            if indicators:
                                technical_indicators[date_str] = indicators
                    
                    self.logger.debug(f"{symbol} 技术指标预计算完成（{len(technical_indicators)}天）")
                except Exception as e:
                    self.logger.warning(f"{symbol} 预计算技术指标失败: {str(e)}")
                    # 继续处理，后续会在批量保存时计算
            
            # 优化：使用shift()方法一次性计算所有日期的前一日收盘价（避免循环中的重复查找）
            # 确保closes变量已定义且不为空
            if len(closes) > 0:
                pre_close_series = closes.shift(1)  # 前一日收盘价
            else:
                # 如果closes为空，创建一个空的Series
                pre_close_series = pd.Series(dtype=float)
            
            # 批量处理数据
            batch_data = []
            # 优化：增大批次大小，收集完所有数据后再一次性保存（从100改为1000）
            batch_size = 1000  # 每批保存1000条（减少SQL构建和执行次数）
            
            for date_str in missing_dates:
                try:
                    # 从批量获取的数据中查找对应日期的数据
                    date_obj = pd.to_datetime(date_str)
                    
                    if date_obj in kline_data.index:
                        row = kline_data.loc[date_obj]
                        
                        # 构建数据字典（只包含基本K线数据，历史数据不需要实时行情等）
                        data = {
                            'symbol': symbol,
                            'name': stock_name,
                            'trade_date': date_str,
                            'period_type': 'daily',
                            'data_source': 'akshare',
                            'data_quality_score': 1.0,
                            'is_valid': True,
                            'open_price': float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
                            'close_price': float(row.get('close', 0)) if pd.notna(row.get('close')) else None,
                            'high_price': float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
                            'low_price': float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
                            'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
                        }
                        
                        # 添加成交额（如果API返回了成交额字段）
                        if 'amount' in kline_data.columns and pd.notna(row.get('amount')):
                            data['amount'] = float(row.get('amount'))
                        elif data.get('close_price') and data.get('volume'):
                            # 如果没有成交额，计算近似值：成交额 = 收盘价 * 成交量（手转股：1手=100股）
                            data['amount'] = float(data['close_price'] * data['volume'] * 100)
                        
                        # 添加换手率（如果API返回了换手率字段）
                        if 'turnover_rate' in kline_data.columns and pd.notna(row.get('turnover_rate')):
                            data['turnover_rate'] = float(row.get('turnover_rate'))
                        # 注意：换手率需要流通股本数据才能准确计算，历史数据通常不可用
                        
                        # 优化：使用预计算的pre_close_series，避免重复查找前一日数据
                        if date_obj in pre_close_series.index and pd.notna(pre_close_series.loc[date_obj]):
                            prev_close = pre_close_series.loc[date_obj]
                            if data.get('close_price'):
                                data['pre_close'] = float(prev_close)
                                data['change_amount'] = data['close_price'] - data['pre_close']
                                data['change_pct'] = (data['change_amount'] / data['pre_close']) * 100 if data['pre_close'] > 0 else 0
                        
                        # 计算价格区间和振幅
                        if data.get('high_price') and data.get('low_price'):
                            data['price_range'] = data['high_price'] - data['low_price']
                        
                        if data.get('pre_close') and data.get('high_price') and data.get('low_price'):
                            amplitude = ((data['high_price'] - data['low_price']) / data['pre_close']) * 100 if data['pre_close'] > 0 else 0
                            data['amplitude'] = round(amplitude, 2)
                        
                        # 添加估值指标（PE、PB，历史数据可能不可用，但尝试添加）
                        if pe_ratio is not None:
                            data['pe_ratio'] = pe_ratio
                        if pb_ratio is not None:
                            data['pb_ratio'] = pb_ratio
                        
                        # 计算涨跌停价（基于昨收价）
                        if data.get('pre_close'):
                            pre_close = data['pre_close']
                            # ST股票涨跌停5%，普通股票10%，科创板/创业板20%
                            if symbol.startswith('688') or symbol.startswith('300'):
                                limit_pct = 0.20
                            else:
                                # 检查是否是ST股票（需要从股票名称判断，这里简化处理）
                                limit_pct = 0.10  # 默认10%
                            
                            data['limit_up'] = round(pre_close * (1 + limit_pct), 2)
                            data['limit_down'] = round(pre_close * (1 - limit_pct), 2)
                            data['limit_pct'] = limit_pct * 100
                            
                            # 判断是否涨跌停
                            if data.get('close_price'):
                                if abs(data['close_price'] - data['limit_up']) < 0.01:
                                    data['is_limit_up'] = True
                                elif abs(data['close_price'] - data['limit_down']) < 0.01:
                                    data['is_limit_down'] = True
                        
                        # 添加成本分布（历史成本分布可以计算，当日成本分布历史数据不可用）
                        if cost_distribution_history:
                            data['cost_distribution_history'] = cost_distribution_history
                            data['cost_distribution'] = {
                                'history': cost_distribution_history,
                                'intraday': {}  # 历史数据无法获取当日成本分布
                            }
                        
                        # 注意：total_market_cap 和 float_market_cap 历史数据通常不可用
                        # 这些字段需要从实时行情获取，历史数据收集时保持为NULL
                        
                        # 添加预计算的技术指标
                        if date_str in technical_indicators:
                            data.update(technical_indicators[date_str])
                        
                        # 优化：在数据构建时就序列化JSON字段，避免批量保存时重复序列化
                        # 序列化JSON字段（如果存在）
                        if 'bid_levels' in data and data['bid_levels']:
                            data['bid_levels_json'] = json.dumps(data['bid_levels'], ensure_ascii=False)
                        if 'ask_levels' in data and data['ask_levels']:
                            data['ask_levels_json'] = json.dumps(data['ask_levels'], ensure_ascii=False)
                        if 'cost_distribution' in data and data['cost_distribution']:
                            data['cost_distribution_json'] = json.dumps(data['cost_distribution'], ensure_ascii=False)
                        if 'cost_distribution_history' in data and data['cost_distribution_history']:
                            data['cost_distribution_history_json'] = json.dumps(data['cost_distribution_history'], ensure_ascii=False)
                        if 'cost_distribution_intraday' in data and data['cost_distribution_intraday']:
                            data['cost_distribution_intraday_json'] = json.dumps(data['cost_distribution_intraday'], ensure_ascii=False)
                        if 'extra_data' in data and data['extra_data']:
                            data['extra_data_json'] = json.dumps(data['extra_data'], ensure_ascii=False)
                        
                        batch_data.append((date_str, data))
                        
                        # 记录实际保存的字段数量（用于调试，只在第一条记录时记录）
                        if len(batch_data) == 1:
                            # 统计实际会保存到数据库的字段数量（排除被注释的字段）
                            # 实际保存41个字段：已注释掉16个历史数据不可用的字段
                            actual_fields_count = 41  # symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close, change_amount, change_pct, volume, amount, volume_ratio, cost_distribution, cost_distribution_history, pe_ratio, pb_ratio, limit_up, limit_down, limit_pct, is_limit_up, is_limit_down, amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2, margin_balance, short_balance, margin_ratio, extra_data, data_source, data_quality_score, is_valid
                            self.logger.debug(f"{symbol} 数据构建完成，实际保存字段数量: {actual_fields_count} 个（已注释掉16个历史数据不可用的字段）")
                        
                    else:
                        # 如果批量数据中没有，标记为失败
                        fail_count += 1
                        if fail_count <= 10:  # 只记录前10个失败的日志
                            self.logger.warning(f"{symbol} {date_str} 在批量数据中未找到")
                        
                except Exception as e:
                    fail_count += 1
                    if fail_count <= 10:
                        self.logger.error(f"{symbol} {date_str} 处理异常: {str(e)}")
            
            # 优化：收集完所有数据后，一次性批量保存（减少SQL构建和执行次数）
            if batch_data:
                try:
                    # 技术指标已在处理数据前一次性计算完成，直接保存
                    # 批量保存（使用批量INSERT优化，批次大小调整为1000，平衡性能和内存使用）
                    # 对于新数据（首次收集），跳过存在性检查，直接使用ON DUPLICATE KEY UPDATE，性能提升3-5倍
                    batch_save_data = [(symbol, date_str_item, data_item) for date_str_item, data_item in batch_data]
                    # skip_existence_check=True: 跳过查询，直接使用ON DUPLICATE KEY UPDATE（对于新数据，性能更好）
                    save_result = self.storage.save_stock_daily_data_batch(batch_save_data, batch_size=1000, skip_existence_check=True)
                    
                    success_count += save_result.get('success_count', 0)
                    fail_count += save_result.get('fail_count', 0)
                    
                    # 打印保存进度
                    # 注意：进度条显示的57个字段是akshare API返回的字段数量，实际保存到数据库的字段数量是41个（已注释掉16个历史数据不可用的字段）
                    self.logger.info(f"{symbol} 批量保存完成: {success_count}/{len(missing_dates)} 条记录（实际保存41个字段，进度条显示的57个字段是API返回的字段数量）")
                
                except Exception as e:
                    self.logger.error(f"{symbol} 批量保存失败: {str(e)}")
                    fail_count += len(batch_data)
            
            result = {
                'symbol': symbol,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'total_dates': len(missing_dates),
                'success_count': success_count,
                'fail_count': fail_count,
                'success_rate': success_count / len(missing_dates) if missing_dates else 0,
                'success': success_count > 0,
                'message': f'批量模式采集完成'
            }
            
            # 注意：进度条显示的57个字段是akshare API返回的字段数量，实际保存到数据库的字段数量是41个（已注释掉16个历史数据不可用的字段）
            self.logger.info(f"{symbol} 批量采集完成: 成功 {success_count}/{len(missing_dates)}, 失败 {fail_count}（实际保存41个字段，进度条显示的57个字段是API返回的字段数量）")
            
            return result
            
        except Exception as e:
            self.logger.error(f"{symbol} 批量采集失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 回退到逐日模式
            self.logger.info(f"{symbol} 回退到逐日模式...")
            return self._collect_stock_history_daily(symbol, missing_dates, start_date_str, end_date_str)
    
    def _collect_stock_history_daily(self, symbol: str, missing_dates: List[str], 
                                     start_date_str: str, end_date_str: str) -> Dict:
        """
        逐日采集股票历史数据（兼容旧版本）
        
        Args:
            symbol: 股票代码
            missing_dates: 缺失的日期列表
            start_date_str: 开始日期
            end_date_str: 结束日期
        
        Returns:
            采集结果字典
        """
        success_count = 0
        fail_count = 0
        
        for i, date in enumerate(missing_dates, 1):
            try:
                data = self.collect_stock_daily_data(symbol, date)
                
                if data:
                    if self.storage.save_stock_daily_data(symbol, date, data):
                        success_count += 1
                        if i % 50 == 0 or i == len(missing_dates):
                            self.logger.info(f"[{i}/{len(missing_dates)}] {symbol} 已保存 {success_count} 条数据")
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
                
                if i < len(missing_dates):
                    time.sleep(0.3)
                    
            except Exception as e:
                fail_count += 1
                if i % 50 == 0:
                    self.logger.error(f"[{i}/{len(missing_dates)}] {symbol} {date} 采集异常: {str(e)}")
                time.sleep(0.5)
        
        return {
            'symbol': symbol,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'total_dates': len(missing_dates),
            'success_count': success_count,
            'fail_count': fail_count,
            'success_rate': success_count / len(missing_dates) if missing_dates else 0,
            'success': success_count > 0
        }
    
    def incremental_update_today(self, symbols: List[str] = None, max_workers: int = 50, batch_size: int = 500, 
                                additional_dates: List[str] = None, use_batch_api: bool = True) -> Dict:
        """
        增量更新今日数据（收盘后调用）- 优化版，支持多线程并发和批量API获取
        
        Args:
            symbols: 股票代码列表（如果为None，则更新所有股票的最新日期到今日的数据）
            max_workers: 最大并发线程数（默认50，设置为1则使用单线程模式，避免API限流）
            batch_size: 批量保存的批次大小（默认500）
            additional_dates: 额外需要更新的日期列表（例如：['2026-01-12', '2026-01-13', '2026-01-14']）
            use_batch_api: 是否使用批量API获取当天数据（默认True，使用ak.stock_zh_a_spot_em一次性获取所有股票）
        
        Returns:
            更新结果字典
        """
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from threading import Lock
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 合并今日和额外日期（如果指定了additional_dates）
            if additional_dates:
                target_dates = [today] + additional_dates
                target_dates = list(set(target_dates))  # 去重
            else:
                # 如果没有指定additional_dates，只处理今日数据
                target_dates = [today]
            
            # 如果只更新今天的数据且启用批量API，使用批量接口一次性获取所有股票数据
            if use_batch_api and len(target_dates) == 1 and target_dates[0] == today:
                return self._incremental_update_today_batch(symbols, batch_size)
            
            # 如果未指定股票列表，获取所有已有数据的股票
            if symbols is None:
                # 从数据库获取所有不重复的股票代码
                sql = "SELECT DISTINCT symbol FROM stock_history_data"
                results = self.storage.db.execute_query(sql)
                symbols = [r['symbol'] for r in results]
            
            symbol_count = len(symbols)
            
            # 根据股票数量自动调整线程数和批次大小（保守策略：避免API限流）
            if symbol_count > 5000:
                # 超大量股票：线程数50-80，批次大小600
                if max_workers < 40:
                    max_workers = min(80, max(50, symbol_count // 80))
                if batch_size < 400:
                    batch_size = 600
                self.logger.info(f"检测到 {symbol_count} 只股票（超大量），自动调整线程数为 {max_workers}，批次大小为 {batch_size}")
            elif symbol_count > 3000:
                # 大量股票：线程数40-60，批次大小500
                if max_workers < 30:
                    max_workers = min(60, max(40, symbol_count // 80))
                if batch_size < 300:
                    batch_size = 500
                self.logger.info(f"检测到 {symbol_count} 只股票（大量），自动调整线程数为 {max_workers}，批次大小为 {batch_size}")
            elif symbol_count > 1000:
                # 中等数量：线程数30-50，批次大小400
                if max_workers < 25:
                    max_workers = min(50, max(30, symbol_count // 100))
                if batch_size < 200:
                    batch_size = 400
                self.logger.info(f"检测到 {symbol_count} 只股票（中等），自动调整线程数为 {max_workers}，批次大小为 {batch_size}")
            # 少于1000只股票使用传入的参数或默认值
            
            self.logger.info(f"开始增量更新数据: {target_dates}（股票数: {symbol_count}, 线程数: {max_workers}, 批次大小: {batch_size}）")
            
            # 批量查询目标日期数据已存在的股票（优化：减少数据库查询次数）
            # 使用字典记录每个股票在每个日期是否存在：{symbol: {date: True/False}}
            existing_data_map = {}
            if len(symbols) > 0:
                self.logger.info(f"批量查询目标日期数据已存在的股票...")
                try:
                    # 根据股票数量动态调整查询批次大小（性能优化）
                    if symbol_count > 5000:
                        query_batch_size = 5000  # 超大量股票使用更大的批次
                    elif symbol_count > 3000:
                        query_batch_size = 4000  # 大量股票使用较大批次
                    elif symbol_count > 2000:
                        query_batch_size = 3000  # 中等数量使用中等批次
                    else:
                        query_batch_size = 2000  # 少量股票使用默认批次
                    for query_start in range(0, len(symbols), query_batch_size):
                        query_end = min(query_start + query_batch_size, len(symbols))
                        query_batch = symbols[query_start:query_end]
                        
                        # 构建IN条件查询（查询所有目标日期）
                        placeholders = ','.join(['%s'] * len(query_batch))
                        date_placeholders = ','.join(['%s'] * len(target_dates))
                        sql = f"""
                            SELECT DISTINCT symbol, trade_date
                            FROM stock_history_data 
                            WHERE symbol IN ({placeholders}) 
                              AND trade_date IN ({date_placeholders})
                              AND period_type = 'daily'
                        """
                        params = [str(s).zfill(6) for s in query_batch] + target_dates
                        results = self.storage.db.execute_query(sql, tuple(params))
                        
                        for result in results:
                            symbol = str(result.get('symbol', '')).strip()
                            date = str(result.get('trade_date', ''))
                            if symbol not in existing_data_map:
                                existing_data_map[symbol] = {}
                            existing_data_map[symbol][date] = True
                    
                    # 找出需要处理的股票和日期组合
                    pending_tasks = []  # [(symbol, date), ...]
                    skip_count = 0
                    
                    for symbol in symbols:
                        symbol_str = str(symbol).strip()
                        for date in target_dates:
                            if existing_data_map.get(symbol_str, {}).get(date, False):
                                skip_count += 1
                            else:
                                pending_tasks.append((symbol_str, date))
                    
                    self.logger.info(f"批量查询完成: 已存在 {skip_count} 条数据，待处理 {len(pending_tasks)} 条数据（{len(set(s[0] for s in pending_tasks))} 只股票）")
                except Exception as e:
                    self.logger.warning(f"批量查询已存在数据失败: {str(e)}，将处理所有股票的所有日期")
                    # 回退：为所有股票的所有日期创建任务
                    pending_tasks = [(str(s).strip(), date) for s in symbols for date in target_dates]
                    skip_count = 0
            else:
                pending_tasks = []
                skip_count = 0
            
            if not pending_tasks:
                self.logger.info(f"所有股票的目标日期数据已存在，无需处理")
                return {
                    'dates': target_dates,
                    'total_symbols': len(symbols),
                    'success_count': 0,
                    'fail_count': 0,
                    'skip_count': skip_count
                }
            
            # 单线程模式（兼容旧代码）
            if max_workers <= 1:
                # 单线程模式：处理所有待处理任务
                return self._incremental_update_dates_single_thread(pending_tasks, skip_count, target_dates)
            
            # 多线程模式
            start_time = datetime.now()
            success_count = 0
            fail_count = 0
            
            # 用于线程安全的计数器和数据收集
            success_lock = Lock()
            fail_lock = Lock()
            collected_data = []  # 收集到的数据，用于批量保存
            data_lock = Lock()
            
            def process_task(task: tuple) -> Dict:
                """处理单个任务的工作函数（symbol, date）"""
                symbol, date = task
                try:
                    # 采集数据（使用快速模式，跳过不必要的API调用）
                    data = self.collect_stock_daily_data(symbol, date, fast_mode=True)
                    
                    if data:
                        # 添加到批量保存列表
                        with data_lock:
                            collected_data.append((symbol, date, data))
                        return {'success': True, 'symbol': symbol, 'date': date}
                    else:
                        with fail_lock:
                            fail_count += 1
                        return {'success': False, 'symbol': symbol, 'date': date, 'message': '数据采集失败'}
                        
                except Exception as e:
                    with fail_lock:
                        fail_count += 1
                    self.logger.error(f"{symbol} {date} 更新异常: {str(e)}")
                    return {'success': False, 'symbol': symbol, 'date': date, 'message': str(e)}
            
            # 使用线程池并行处理
            self.logger.info(f"开始多线程处理 {len(pending_tasks)} 个任务（{len(set(s[0] for s in pending_tasks))} 只股票，{len(target_dates)} 个日期）...")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_task = {
                    executor.submit(process_task, task): task
                    for task in pending_tasks
                }
                
                # 处理完成的任务
                completed = 0
                for future in as_completed(future_to_task):
                    completed += 1
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        if result.get('success', False):
                            with success_lock:
                                success_count += 1
                            # 根据任务数量动态调整进度日志频率（减少日志开销）
                            log_interval = max(100, len(pending_tasks) // 50)  # 至少每100个，最多50次日志
                            if completed % log_interval == 0 or completed == len(pending_tasks):
                                self.logger.info(f"进度: {completed}/{len(pending_tasks)} ({completed*100//len(pending_tasks)}%) - 成功: {success_count}, 失败: {fail_count}")
                        else:
                            self.logger.debug(f"  [失败] {result.get('symbol')} {result.get('date')}: {result.get('message', '未知错误')}")
                    except Exception as e:
                        with fail_lock:
                            fail_count += 1
                        self.logger.error(f"  [异常] {task[0]} {task[1]}: {str(e)}")
            
            # 批量保存数据
            if collected_data:
                self.logger.info(f"开始批量保存 {len(collected_data)} 条数据...")
                save_result = self.storage.save_stock_daily_data_batch(
                    collected_data, 
                    batch_size=batch_size,
                    skip_existence_check=True  # 已经检查过了，跳过存在性检查
                )
                
                # 更新成功和失败计数
                actual_success = save_result.get('success_count', 0)
                actual_fail = save_result.get('fail_count', 0)
                
                # 如果批量保存有失败，调整计数
                if actual_success < len(collected_data):
                    success_count = actual_success
                    fail_count += (len(collected_data) - actual_success)
                
                self.logger.info(f"批量保存完成: 成功 {actual_success}, 失败 {actual_fail}")
            
            total_duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'dates': target_dates,
                'total_symbols': len(symbols),
                'success_count': success_count,
                'fail_count': fail_count,
                'skip_count': skip_count,
                'total_duration_seconds': total_duration
            }
            
            self.logger.info(f"增量更新完成: 成功 {success_count}, 失败 {fail_count}, 跳过 {skip_count}, 总耗时 {total_duration:.1f}秒")
            
            return result
            
        except Exception as e:
            self.logger.error(f"增量更新失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }
    
    def _incremental_update_today_batch(self, symbols: List[str] = None, batch_size: int = 500) -> Dict:
        """
        使用批量API一次性获取所有股票的当天数据（优化版）
        
        Args:
            symbols: 股票代码列表（如果为None，则更新所有股票）
            batch_size: 批量保存的批次大小（默认500）
        
        Returns:
            更新结果字典
        """
        try:
            import akshare as ak
            from data_source.stock_data_source import _call_akshare_without_proxy
            
            today = datetime.now().strftime('%Y-%m-%d')
            self.logger.info(f"使用批量API一次性获取所有股票的当天数据（{today}）...")
            
            # 如果未指定股票列表，获取所有已有数据的股票
            if symbols is None:
                sql = "SELECT DISTINCT symbol FROM stock_history_data"
                results = self.storage.db.execute_query(sql)
                symbols = [r['symbol'] for r in results]
            
            symbol_count = len(symbols)
            self.logger.info(f"需要更新 {symbol_count} 只股票的数据")
            
            # 批量查询今天已存在的数据
            existing_symbols = set()
            if len(symbols) > 0:
                try:
                    placeholders = ','.join(['%s'] * len(symbols))
                    sql = f"""
                        SELECT DISTINCT symbol
                        FROM stock_history_data 
                        WHERE symbol IN ({placeholders}) 
                          AND trade_date = %s
                          AND period_type = 'daily'
                    """
                    params = [str(s).zfill(6) for s in symbols] + [today]
                    results = self.storage.db.execute_query(sql, tuple(params))
                    existing_symbols = {str(r['symbol']).strip() for r in results}
                except Exception as e:
                    self.logger.warning(f"批量查询已存在数据失败: {str(e)}")
            
            skip_count = len(existing_symbols)
            need_update_symbols = [s for s in symbols if str(s).strip() not in existing_symbols]
            
            self.logger.info(f"已存在 {skip_count} 只股票的数据，需要更新 {len(need_update_symbols)} 只股票的数据")
            
            if not need_update_symbols:
                self.logger.info(f"所有股票今天的数据已存在，无需处理")
                return {
                    'dates': [today],
                    'total_symbols': symbol_count,
                    'success_count': 0,
                    'fail_count': 0,
                    'skip_count': skip_count,
                    'total_duration_seconds': 0
                }
            
            # 批量获取所有股票的实时行情数据
            start_time = datetime.now()
            try:
                self.logger.info(f"开始批量获取所有股票的实时行情数据...")
                # 增加超时时间，批量API可能需要更长时间
                import time
                time.sleep(1)  # 延迟1秒，避免请求过快
                df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
                
                if df is None or df.empty:
                    self.logger.error("批量获取实时行情数据失败，返回空数据")
                    return {
                        'dates': [today],
                        'total_symbols': symbol_count,
                        'success_count': 0,
                        'fail_count': len(need_update_symbols),
                        'skip_count': skip_count,
                        'total_duration_seconds': (datetime.now() - start_time).total_seconds(),
                        'error': '批量API返回空数据'
                    }
                
                self.logger.info(f"成功获取 {len(df)} 只股票的实时行情数据")
                
                # 识别代码列和名称列
                code_col = None
                name_col = None
                for col in df.columns:
                    col_s = str(col)
                    if code_col is None and ('代码' in col_s or col_s.lower() in ['code', 'symbol']):
                        code_col = col
                    if name_col is None and ('名称' in col_s or col_s.lower() in ['name']):
                        name_col = col
                
                if code_col is None:
                    self.logger.error("无法识别股票代码列")
                    return {
                        'dates': [today],
                        'total_symbols': symbol_count,
                        'success_count': 0,
                        'fail_count': len(need_update_symbols),
                        'skip_count': skip_count,
                        'total_duration_seconds': (datetime.now() - start_time).total_seconds()
                    }
                
                # 构建股票代码到数据的映射
                symbol_data_map = {}
                for _, row in df.iterrows():
                    symbol = str(row[code_col]).strip()
                    symbol_data_map[symbol] = row
                
                # 转换数据格式并批量保存
                collected_data = []
                success_count = 0
                fail_count = 0
                
                # 列名映射
                column_mappings = {
                    'open_price': ['今开', '开盘价', 'open'],
                    'close_price': ['最新价', '现价', 'price', '收盘价'],
                    'high_price': ['最高', '最高价', 'high'],
                    'low_price': ['最低', '最低价', 'low'],
                    'pre_close': ['昨收', '昨日收盘', 'pre_close'],
                    'volume': ['成交量', 'volume'],
                    'amount': ['成交额', 'amount'],
                    'change_pct': ['涨跌幅', 'change_pct', 'pct_change'],
                    'change_amount': ['涨跌额', 'change'],
                    'turnover_rate': ['换手率', 'turnover'],
                    'amplitude': ['振幅', 'amplitude'],
                    'pe_ratio': ['市盈率-动态', '市盈率', 'pe'],
                    'pb_ratio': ['市净率', 'pb'],
                    'total_market_cap': ['总市值', 'market_cap', 'total_value'],
                    'float_market_cap': ['流通市值', 'float_cap', 'float_value']
                }
                
                for symbol in need_update_symbols:
                    symbol_str = str(symbol).strip().zfill(6)
                    if symbol_str not in symbol_data_map:
                        fail_count += 1
                        self.logger.debug(f"未找到股票 {symbol_str} 的实时数据")
                        continue
                    
                    row = symbol_data_map[symbol_str]
                    
                    # 构建数据字典
                    data = {
                        'symbol': symbol_str,
                        'name': str(row.get(name_col, symbol_str)) if name_col else symbol_str,
                        'trade_date': today,
                        'period_type': 'daily',
                        'data_source': 'akshare',
                        'data_quality_score': 1.0,
                        'is_valid': True
                    }
                    
                    # 映射字段
                    for field, possible_cols in column_mappings.items():
                        for col in possible_cols:
                            if col in df.columns:
                                try:
                                    value = row[col]
                                    if pd.notna(value):
                                        if field in ['open_price', 'close_price', 'high_price', 'low_price', 'pre_close', 'change_amount']:
                                            data[field] = float(value)
                                        elif field in ['volume', 'amount', 'total_market_cap', 'float_market_cap']:
                                            data[field] = float(value)
                                        elif field in ['change_pct', 'turnover_rate', 'amplitude', 'pe_ratio', 'pb_ratio']:
                                            data[field] = float(value)
                                except:
                                    pass
                                break
                    
                    # 计算涨跌额和涨跌幅（如果没有）
                    if data.get('close_price') and data.get('pre_close') and data['pre_close'] > 0:
                        if 'change_amount' not in data:
                            data['change_amount'] = data['close_price'] - data['pre_close']
                        if 'change_pct' not in data:
                            data['change_pct'] = (data['change_amount'] / data['pre_close']) * 100
                    
                    # 计算成交额（如果没有）
                    if not data.get('amount') and data.get('close_price') and data.get('volume'):
                        data['amount'] = float(data['close_price'] * data['volume'] * 100)  # 1手=100股
                    
                    # 计算涨跌停价
                    if data.get('pre_close'):
                        pre_close = data['pre_close']
                        if symbol_str.startswith('688') or symbol_str.startswith('300'):
                            limit_pct = 0.20
                        else:
                            limit_pct = 0.10
                        data['limit_up'] = round(pre_close * (1 + limit_pct), 2)
                        data['limit_down'] = round(pre_close * (1 - limit_pct), 2)
                        data['limit_pct'] = limit_pct * 100
                        
                        # 判断是否涨跌停
                        if data.get('close_price'):
                            if abs(data['close_price'] - data['limit_up']) < 0.01:
                                data['is_limit_up'] = True
                            elif abs(data['close_price'] - data['limit_down']) < 0.01:
                                data['is_limit_down'] = True
                    
                    # 计算价格区间和振幅
                    if data.get('high_price') and data.get('low_price'):
                        data['price_range'] = data['high_price'] - data['low_price']
                    if data.get('pre_close') and data.get('high_price') and data.get('low_price'):
                        amplitude = ((data['high_price'] - data['low_price']) / data['pre_close']) * 100 if data['pre_close'] > 0 else 0
                        data['amplitude'] = round(amplitude, 2)
                    
                    # 检查是否有必要的价格数据
                    if not data.get('close_price') and not data.get('open_price'):
                        fail_count += 1
                        self.logger.debug(f"{symbol_str} 没有获取到有效的价格数据，跳过保存")
                        continue
                    
                    # 清理NaN值
                    from utils.stock_history_storage import clean_nan_value
                    for key in ['open_price', 'close_price', 'high_price', 'low_price', 'pre_close', 
                               'change_amount', 'change_pct', 'volume', 'amount', 'turnover_rate', 
                               'amplitude', 'pe_ratio', 'pb_ratio', 'total_market_cap', 'float_market_cap',
                               'limit_up', 'limit_down', 'limit_pct', 'price_range']:
                        if key in data:
                            data[key] = clean_nan_value(data[key])
                    
                    collected_data.append((symbol_str, today, data))
                    success_count += 1
                
                # 批量保存数据
                if collected_data:
                    self.logger.info(f"开始批量保存 {len(collected_data)} 条数据...")
                    save_result = self.storage.save_stock_daily_data_batch(
                        collected_data, 
                        batch_size=batch_size,
                        skip_existence_check=True
                    )
                    
                    actual_success = save_result.get('success_count', 0)
                    actual_fail = save_result.get('fail_count', 0)
                    
                    self.logger.info(f"批量保存完成: 成功 {actual_success}, 失败 {actual_fail}")
                    
                    # 更新计数
                    success_count = actual_success
                    fail_count += (len(collected_data) - actual_success) + (len(need_update_symbols) - len(collected_data))
                else:
                    fail_count = len(need_update_symbols)
                
                total_duration = (datetime.now() - start_time).total_seconds()
                
                result = {
                    'dates': [today],
                    'total_symbols': symbol_count,
                    'success_count': success_count,
                    'fail_count': fail_count,
                    'skip_count': skip_count,
                    'total_duration_seconds': total_duration
                }
                
                self.logger.info(f"批量更新完成: 成功 {success_count}, 失败 {fail_count}, 跳过 {skip_count}, 总耗时 {total_duration:.1f}秒")
                return result
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"批量获取数据失败: {error_msg}")
                import traceback
                self.logger.error(traceback.format_exc())
                
                # 检查是否是网络错误
                is_network_error = (
                    'Connection' in error_msg or
                    'RemoteDisconnected' in error_msg or
                    'timeout' in error_msg.lower() or
                    'ECONNRESET' in error_msg
                )
                
                error_type = '网络错误' if is_network_error else 'API错误'
                
                return {
                    'dates': [today],
                    'total_symbols': symbol_count,
                    'success_count': 0,
                    'fail_count': len(need_update_symbols),
                    'skip_count': skip_count,
                    'total_duration_seconds': (datetime.now() - start_time).total_seconds(),
                    'error': error_msg,
                    'error_type': error_type
                }
                
        except Exception as e:
            self.logger.error(f"批量更新失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }
    
    def _incremental_update_dates_single_thread(self, pending_tasks: List[tuple], skip_count: int, target_dates: List[str]) -> Dict:
        """单线程模式（处理多个日期）"""
        success_count = 0
        fail_count = 0
        collected_data = []
        
        for i, (symbol, date) in enumerate(pending_tasks, 1):
            try:
                # 采集数据（使用快速模式，跳过不必要的API调用）
                data = self.collect_stock_daily_data(symbol, date, fast_mode=True)
                
                if data:
                    collected_data.append((symbol, date, data))
                    success_count += 1
                    if i % 100 == 0 or i == len(pending_tasks):
                        self.logger.info(f"进度: {i}/{len(pending_tasks)} ({i*100//len(pending_tasks)}%) - 成功 {success_count}, 失败 {fail_count}")
                else:
                    fail_count += 1
                    self.logger.warning(f"[{i}/{len(pending_tasks)}] {symbol} {date} 数据采集失败")
                
                # 避免请求过快（单线程模式保留延迟）
                if i < len(pending_tasks):
                    time.sleep(0.1)  # 减少延迟到0.1秒
                    
            except Exception as e:
                fail_count += 1
                self.logger.error(f"[{i}/{len(pending_tasks)}] {symbol} {date} 更新异常: {str(e)}")
                time.sleep(0.5)
        
        # 批量保存数据
        if collected_data:
            self.logger.info(f"开始批量保存 {len(collected_data)} 条数据...")
            save_result = self.storage.save_stock_daily_data_batch(
                collected_data,
                batch_size=100,
                skip_existence_check=True
            )
            actual_success = save_result.get('success_count', 0)
            actual_fail = save_result.get('fail_count', 0)
            if actual_success < len(collected_data):
                success_count = actual_success
                fail_count += (len(collected_data) - actual_success)
            self.logger.info(f"批量保存完成: 成功 {actual_success}, 失败 {actual_fail}")
        
        return {
            'dates': target_dates,
            'total_symbols': len(set(s[0] for s in pending_tasks)),
            'success_count': success_count,
            'fail_count': fail_count,
            'skip_count': skip_count
        }
    
    def _incremental_update_today_single_thread(self, symbols: List[str], today: str, skip_count: int) -> Dict:
        """单线程模式（兼容旧代码）"""
        success_count = 0
        fail_count = 0
        
        for i, symbol in enumerate(symbols, 1):
            try:
                # 采集今日数据（使用快速模式，跳过不必要的API调用）
                data = self.collect_stock_daily_data(symbol, today, fast_mode=True)
                
                if data:
                    # 保存数据
                    if self.storage.save_stock_daily_data(symbol, today, data):
                        success_count += 1
                        if i % 100 == 0 or i == len(symbols):
                            self.logger.info(f"进度: {i}/{len(symbols)} ({i*100//len(symbols)}%) - 成功 {success_count}, 失败 {fail_count}")
                    else:
                        fail_count += 1
                        self.logger.warning(f"[{i}/{len(symbols)}] {symbol} 今日数据保存失败")
                else:
                    fail_count += 1
                    self.logger.warning(f"[{i}/{len(symbols)}] {symbol} 今日数据采集失败")
                
                # 避免请求过快（单线程模式保留延迟）
                if i < len(symbols):
                    time.sleep(0.1)  # 减少延迟到0.1秒
                    
            except Exception as e:
                fail_count += 1
                self.logger.error(f"[{i}/{len(symbols)}] {symbol} 更新异常: {str(e)}")
                time.sleep(0.5)
        
        return {
            'date': today,
            'total_symbols': len(symbols) + skip_count,
            'success_count': success_count,
            'fail_count': fail_count,
            'skip_count': skip_count
        }
    
    def batch_collect_stocks_history(self, symbols: List[str], years: int = 10) -> Dict:
        """
        批量采集多只股票的历史数据
        
        Args:
            symbols: 股票代码列表
            years: 采集多少年的数据
        
        Returns:
            批量采集结果
        """
        try:
            self.logger.info(f"开始批量采集 {len(symbols)} 只股票的历史数据...")
            
            results = []
            for i, symbol in enumerate(symbols, 1):
                self.logger.info(f"\n[{i}/{len(symbols)}] 采集 {symbol} 的历史数据...")
                result = self.collect_stock_history_data(symbol, years=years)
                results.append(result)
                
                # 每只股票采集完成后稍作休息
                if i < len(symbols):
                    time.sleep(2)
            
            total_success = sum(r.get('success_count', 0) for r in results)
            total_fail = sum(r.get('fail_count', 0) for r in results)
            total_dates = sum(r.get('total_dates', 0) for r in results)
            
            summary = {
                'total_symbols': len(symbols),
                'total_dates': total_dates,
                'total_success': total_success,
                'total_fail': total_fail,
                'success_rate': total_success / total_dates if total_dates > 0 else 0,
                'details': results
            }
            
            self.logger.info(f"\n批量采集完成:")
            self.logger.info(f"  股票数量: {len(symbols)}")
            self.logger.info(f"  总数据条数: {total_dates}")
            self.logger.info(f"  成功: {total_success}")
            self.logger.info(f"  失败: {total_fail}")
            self.logger.info(f"  成功率: {summary['success_rate']:.1%}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"批量采集失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }
