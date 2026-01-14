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
    
    def collect_stock_daily_data(self, symbol: str, date: str) -> Optional[Dict]:
        """
        采集股票单日数据
        
        Args:
            symbol: 股票代码
            date: 交易日期（格式：YYYY-MM-DD）
        
        Returns:
            采集到的数据字典，如果失败返回None
        """
        try:
            self.logger.info(f"开始采集 {symbol} {date} 的数据...")
            
            # 转换日期格式
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_str = date_obj.strftime('%Y%m%d')
            
            # 先尝试获取股票名称
            stock_name = ''
            try:
                stock_info = self.data_source.get_stock_info(symbol)
                if stock_info:
                    stock_name = stock_info.get('name', '') or stock_info.get('股票简称', '') or stock_info.get('股票名称', '')
            except Exception as e:
                self.logger.debug(f"获取股票信息失败 {symbol}: {str(e)}")
            
            # 如果还是没有获取到名称，从股票列表中获取
            if not stock_name or stock_name == '':
                try:
                    stock_list = self.data_source.get_all_stock_list(limit=None, sort_by_turnover=False, use_cache=True)
                    for stock in stock_list:
                        if str(stock.get('symbol', '')).strip() == str(symbol).strip():
                            stock_name = stock.get('name', '')
                            break
                except Exception as e:
                    self.logger.debug(f"从股票列表获取名称失败 {symbol}: {str(e)}")
            
            data = {
                'symbol': symbol,
                'name': stock_name if stock_name else symbol,  # 如果获取不到名称，使用代码
                'trade_date': date,  # 添加交易日期
                'period_type': 'daily',  # 添加周期类型，默认为日线
                'data_source': 'akshare',
                'data_quality_score': 1.0,
                'is_valid': True
            }
            
            # 1. 获取基本K线数据
            try:
                # 获取包含目标日期的数据（前后各10天以确保包含目标日期）
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                start_date = (date_obj - timedelta(days=10)).strftime('%Y-%m-%d')
                end_date = (date_obj + timedelta(days=10)).strftime('%Y-%m-%d')
                
                # 使用指定的日期范围获取数据
                days_data = self.data_source.get_stock_data(symbol, start_date=start_date, end_date=end_date)
                target_row = None
                
                if not days_data.empty:
                    # 查找目标日期
                    date_idx = pd.to_datetime(date)
                    if date_idx in days_data.index:
                        target_row = days_data.loc[date_idx]
                    elif len(days_data) > 0:
                        # 如果找不到精确日期，使用最近的日期
                        closest_idx = days_data.index[days_data.index.get_indexer([date_idx], method='nearest')[0]]
                        target_row = days_data.loc[closest_idx]
                
                if target_row is not None:
                    data['open_price'] = float(target_row.get('open', 0)) if pd.notna(target_row.get('open')) else None
                    data['close_price'] = float(target_row.get('close', 0)) if pd.notna(target_row.get('close')) else None
                    data['high_price'] = float(target_row.get('high', 0)) if pd.notna(target_row.get('high')) else None
                    data['low_price'] = float(target_row.get('low', 0)) if pd.notna(target_row.get('low')) else None
                    data['volume'] = int(target_row.get('volume', 0)) if pd.notna(target_row.get('volume')) else None
                    
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
            
            # 2. 获取实时行情数据（包含更多信息）
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
            
            # 3. 获取买卖盘数据（包含外盘、内盘、委比）
            # 注意：这些数据通常只能获取实时数据，历史数据不可用，设置为None
            data['outer_volume'] = None
            data['inner_volume'] = None
            data['bid_levels'] = None
            data['ask_levels'] = None
            data['bid_total_volume'] = None
            data['ask_total_volume'] = None
            data['bid_ask_ratio'] = None
            
            try:
                # 尝试获取实时买卖盘数据（仅对实时数据有效）
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
                    
                    # 计算委比
                    if data.get('bid_total_volume') and data.get('ask_total_volume'):
                        total = data['bid_total_volume'] + data['ask_total_volume']
                        if total > 0:
                            data['bid_ask_ratio'] = ((data['bid_total_volume'] - data['ask_total_volume']) / total) * 100
                    
                    # 外盘和内盘（如果有，注意：akshare可能不提供历史的外盘内盘数据）
                    # 外盘：主动买入成交量（以卖出价成交）
                    # 内盘：主动卖出成交量（以买入价成交）
                    # 这些数据通常需要Level-2行情，历史数据可能不可用
                    if bid_ask.get('outer_volume'):
                        data['outer_volume'] = bid_ask.get('outer_volume')
                    elif bid_ask.get('外盘'):
                        data['outer_volume'] = bid_ask.get('外盘')
                    if bid_ask.get('inner_volume'):
                        data['inner_volume'] = bid_ask.get('inner_volume')
                    elif bid_ask.get('内盘'):
                        data['inner_volume'] = bid_ask.get('内盘')
                    
            except Exception as e:
                self.logger.debug(f"获取买卖盘数据失败 {symbol} {date}: {str(e)} (历史数据通常不可用，已设置为None)")
            
            # 4. 获取成本分布数据
            try:
                # 检查是否有get_cost_distribution方法
                if hasattr(self.data_source, 'get_cost_distribution'):
                    cost_dist = self.data_source.get_cost_distribution(symbol)
                    if cost_dist:
                        data['cost_distribution_history'] = cost_dist
                    
                    # 检查是否有get_intraday_cost_distribution方法
                    if hasattr(self.data_source, 'get_intraday_cost_distribution'):
                        intraday_cost = self.data_source.get_intraday_cost_distribution(symbol)
                        if intraday_cost:
                            data['cost_distribution_intraday'] = intraday_cost
                    
                    # 合并成本分布
                    if cost_dist or data.get('cost_distribution_intraday'):
                        data['cost_distribution'] = {
                            'history': cost_dist or {},
                            'intraday': data.get('cost_distribution_intraday') or {}
                        }
            except Exception as e:
                self.logger.warning(f"获取成本分布数据失败 {symbol} {date}: {str(e)}")
            
            # 5. 获取资金流向数据（如果可用）
            # 注意：这些数据通常只能获取实时数据，历史数据不可用，设置为None
            data['main_net_inflow'] = None
            data['super_large_inflow'] = None
            data['large_inflow'] = None
            data['medium_inflow'] = None
            data['small_inflow'] = None
            
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
                self.logger.debug(f"获取资金流向数据失败 {symbol} {date}: {str(e)} (历史数据通常不可用，已设置为None)")
            
            # 6. 获取融资融券数据（如果可用）
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
            
            # 7. 计算技术指标（如果有多日数据）
            try:
                if not days_data.empty and len(days_data) >= 60:
                    # 计算均线
                    closes = days_data['close']
                    data['ma5'] = float(closes.tail(5).mean()) if len(closes) >= 5 else None
                    data['ma10'] = float(closes.tail(10).mean()) if len(closes) >= 10 else None
                    data['ma20'] = float(closes.tail(20).mean()) if len(closes) >= 20 else None
                    data['ma60'] = float(closes.tail(60).mean()) if len(closes) >= 60 else None
                    
                    # 计算RSI
                    if len(closes) >= 14:
                        delta = closes.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        data['rsi'] = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
                    
                    # 计算MACD
                    if len(closes) >= 26:
                        ema12 = closes.ewm(span=12, adjust=False).mean()
                        ema26 = closes.ewm(span=26, adjust=False).mean()
                        macd = ema12 - ema26
                        signal = macd.ewm(span=9, adjust=False).mean()
                        histogram = macd - signal
                        data['macd'] = float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None
                        data['macd_signal'] = float(signal.iloc[-1]) if pd.notna(signal.iloc[-1]) else None
                        data['macd_hist'] = float(histogram.iloc[-1]) if pd.notna(histogram.iloc[-1]) else None
                    
                    # 计算X_2指标（收盘价在20日价格区间中的相对位置）
                    if len(days_data) >= 20:
                        highs = days_data['high']
                        lows = days_data['low']
                        current_close = data.get('close_price')
                        if current_close is not None:
                            # 计算20日最低价（LLV）
                            llv_low = lows.tail(20).min()
                            # 计算20日最高价（HHV）
                            hhv_high = highs.tail(20).max()
                            # 计算区间宽度
                            range_width = hhv_high - llv_low
                            # 计算X_2，处理除零错误
                            if range_width > 0:
                                x2_value = (current_close - llv_low) / range_width * 100
                                data['x2'] = float(round(x2_value, 4))
                            else:
                                # 如果区间宽度为0（价格没有波动），设置为50（中间位置）
                                data['x2'] = 50.0
                    
            except Exception as e:
                self.logger.debug(f"计算技术指标失败 {symbol} {date}: {str(e)}")
            
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
            self.logger.debug(f"成功采集 {symbol} {date} 的数据，实际保存字段数量: {actual_fields_count} 个（已注释掉16个历史数据不可用的字段）")
            self.logger.info(f"成功采集 {symbol} {date} 的数据")
            return data
            
        except Exception as e:
            self.logger.error(f"采集股票数据失败 {symbol} {date}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def collect_stock_history_data(self, symbol: str, years: int = 10, 
                                   force_refresh: bool = False, 
                                   use_batch_mode: bool = True) -> Dict:
        """
        采集股票历史数据（近N年）
        
        Args:
            symbol: 股票代码
            years: 采集多少年的数据（默认10年）
            force_refresh: 是否强制刷新（重新采集已存在的数据）
            use_batch_mode: 是否使用批量模式（默认True，大幅提升效率）
        
        Returns:
            采集结果字典
        """
        try:
            self.logger.info(f"开始采集 {symbol} 近{years}年的历史数据（批量模式: {use_batch_mode}）...")
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            
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
                    # 批量保存（使用批量INSERT优化，批次大小调整为200，平衡性能和内存使用）
                    # 使用executemany后，可以适当增大批次大小，但考虑到内存和错误恢复，保持200-300较合适
                    batch_save_data = [(symbol, date_str_item, data_item) for date_str_item, data_item in batch_data]
                    save_result = self.storage.save_stock_daily_data_batch(batch_save_data, batch_size=1000)
                    
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
    
    def incremental_update_today(self, symbols: List[str] = None) -> Dict:
        """
        增量更新今日数据（收盘后调用）
        
        Args:
            symbols: 股票代码列表（如果为None，则更新所有股票的最新日期到今日的数据）
        
        Returns:
            更新结果字典
        """
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            self.logger.info(f"开始增量更新今日数据: {today}")
            
            # 如果未指定股票列表，获取所有已有数据的股票
            if symbols is None:
                # 从数据库获取所有不重复的股票代码
                sql = "SELECT DISTINCT symbol FROM stock_history_data"
                results = self.storage.db.execute_query(sql)
                symbols = [r['symbol'] for r in results]
            
            self.logger.info(f"需要更新 {len(symbols)} 只股票的数据")
            
            success_count = 0
            fail_count = 0
            skip_count = 0
            
            for i, symbol in enumerate(symbols, 1):
                try:
                    # 检查今日数据是否已存在
                    if not self.storage.check_data_exists(symbol, today):
                        # 采集今日数据
                        data = self.collect_stock_daily_data(symbol, today)
                        
                        if data:
                            # 保存数据
                            if self.storage.save_stock_daily_data(symbol, today, data):
                                success_count += 1
                                self.logger.info(f"[{i}/{len(symbols)}] {symbol} 今日数据更新成功")
                            else:
                                fail_count += 1
                                self.logger.warning(f"[{i}/{len(symbols)}] {symbol} 今日数据保存失败")
                        else:
                            fail_count += 1
                            self.logger.warning(f"[{i}/{len(symbols)}] {symbol} 今日数据采集失败")
                        
                        # 避免请求过快
                        time.sleep(0.5)
                    else:
                        skip_count += 1
                        self.logger.debug(f"[{i}/{len(symbols)}] {symbol} 今日数据已存在，跳过")
                        
                except Exception as e:
                    fail_count += 1
                    self.logger.error(f"[{i}/{len(symbols)}] {symbol} 更新异常: {str(e)}")
                    time.sleep(1)
            
            result = {
                'date': today,
                'total_symbols': len(symbols),
                'success_count': success_count,
                'fail_count': fail_count,
                'skip_count': skip_count
            }
            
            self.logger.info(f"增量更新完成: 成功 {success_count}, 失败 {fail_count}, 跳过 {skip_count}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"增量更新失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
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
