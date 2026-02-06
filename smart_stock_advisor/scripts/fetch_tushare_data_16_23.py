#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从Tushare获取股票数据脚本（2026-01-16 至 2026-01-23）

功能：
1. 检查数据库中已有的数据
2. 只获取缺失的数据
3. 从Tushare获取并保存到数据库
"""
import os
import sys
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_storage import StockHistoryStorage
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


class RateLimiter:
    """速率限制器（每分钟最多50次请求）"""
    
    def __init__(self, max_requests_per_minute: int = 50):
        self.max_requests = max_requests_per_minute
        self.request_times = deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """如果需要，等待直到可以发送请求"""
        with self.lock:
            now = time.time()
            # 移除1分钟之前的请求记录
            while self.request_times and now - self.request_times[0] > 60:
                self.request_times.popleft()
            
            # 如果已达到限制，等待
            if len(self.request_times) >= self.max_requests:
                # 等待直到最早的请求超过1分钟
                wait_time = 60 - (now - self.request_times[0]) + 0.1  # 加0.1秒缓冲
                if wait_time > 0:
                    return wait_time
            
            # 记录本次请求时间
            self.request_times.append(now)
            return 0
    
    def get_min_delay(self) -> float:
        """计算最小延迟时间（秒）"""
        return 60.0 / self.max_requests


class TushareDataFetcher:
    """Tushare数据获取器"""
    
    def __init__(self):
        self.logger = logger
        self.storage = StockHistoryStorage()
        self.db = DatabaseConnection()
        
        # 速率限制器（每分钟50次）
        self.rate_limiter = RateLimiter(max_requests_per_minute=50)
        
        # 初始化Tushare
        try:
            import tushare as ts
            from config import TUSHARE_TOKEN
            
            if not TUSHARE_TOKEN:
                raise ValueError("Tushare token未配置，请在config.py中设置TUSHARE_TOKEN")
            
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
            self.logger.info("Tushare初始化成功")
            self.logger.info(f"速率限制: 每分钟最多 {self.rate_limiter.max_requests} 次请求")
        except ImportError:
            raise ImportError("请安装tushare: pip install tushare")
        except Exception as e:
            raise Exception(f"Tushare初始化失败: {str(e)}")
    
    def get_existing_data(self, start_date: str, end_date: str) -> Dict[str, Set[str]]:
        """
        查询数据库中已有的数据
        
        Returns:
            {symbol: set(trade_dates)} - 每个股票已有的交易日期集合
        """
        self.logger.info(f"查询数据库中已有的数据: {start_date} 至 {end_date}")
        
        # 优化：只查询需要的字段，添加索引提示（如果数据库支持）
        # 优化：尝试使用索引提示（MySQL支持，如果索引存在）
        # 注意：如果数据库不支持索引提示或索引不存在，会回退到普通查询
        try:
            # 尝试使用索引提示（MySQL语法）
            sql = """
                SELECT symbol, trade_date 
                FROM stock_history_data 
                WHERE trade_date >= %s AND trade_date <= %s
                ORDER BY symbol, trade_date
            """
            # 如果数据库有 (symbol, trade_date) 或 (trade_date, symbol) 的索引，查询会自动使用
            # MySQL的查询优化器会自动选择最佳索引
        except Exception:
            # 如果索引提示失败，使用普通查询
            sql = """
                SELECT symbol, trade_date 
                FROM stock_history_data 
                WHERE trade_date >= %s AND trade_date <= %s
                ORDER BY symbol, trade_date
            """
        
        # 注意：确保数据库中有 (symbol, trade_date) 或 (trade_date, symbol) 的索引以提升查询性能
        
        results = self.db.execute_query(sql, (start_date, end_date))
        
        existing_data = {}
        for row in results:
            symbol = str(row['symbol']).zfill(6)
            trade_date = str(row['trade_date'])
            
            if symbol not in existing_data:
                existing_data[symbol] = set()
            existing_data[symbol].add(trade_date)
        
        total_records = sum(len(dates) for dates in existing_data.values())
        self.logger.info(f"数据库中已有 {len(existing_data)} 只股票的数据，共 {total_records} 条记录")
        
        return existing_data
    
    def get_stock_name(self, symbol: str, ts_code: str = None) -> str:
        """
        获取股票名称
        
        优先级：
        1. 从数据库获取（最快）
        2. 从Tushare stock_basic接口获取
        3. 从StockDataSource获取
        4. 返回股票代码（最后备选）
        
        Args:
            symbol: 股票代码（6位数字）
            ts_code: Tushare格式的股票代码（可选）
        
        Returns:
            股票名称
        """
        # 1. 优先从数据库获取
        try:
            sql = """
                SELECT DISTINCT name 
                FROM stock_history_data 
                WHERE symbol = %s AND name IS NOT NULL AND name != '' AND name != symbol
                ORDER BY trade_date DESC
                LIMIT 1
            """
            results = self.db.execute_query(sql, (symbol,))
            if results and len(results) > 0:
                stock_name = str(results[0].get('name', '')).strip()
                if stock_name and stock_name != symbol:
                    return stock_name
        except Exception as e:
            self.logger.debug(f"从数据库获取股票名称失败 {symbol}: {str(e)}")
        
        # 2. 从Tushare stock_basic接口获取（需要积分，但通常免费）
        if ts_code:
            try:
                # 速率限制：等待直到可以发送请求
                wait_time = self.rate_limiter.wait_if_needed()
                if wait_time > 0:
                    time.sleep(wait_time)
                
                # 调用stock_basic接口
                df = self.pro.stock_basic(
                    exchange='',
                    list_status='L',
                    fields='ts_code,symbol,name'
                )
                
                if df is not None and not df.empty:
                    # 查找对应的股票
                    stock_row = df[df['ts_code'] == ts_code]
                    if not stock_row.empty:
                        stock_name = str(stock_row.iloc[0]['name']).strip()
                        if stock_name and stock_name != symbol:
                            return stock_name
            except Exception as e:
                self.logger.debug(f"从Tushare stock_basic获取股票名称失败 {symbol}: {str(e)}")
        
        # 3. 如果都失败，返回股票代码（至少不是空值）
        # 注意：不再使用StockDataSource，只使用Tushare
        return symbol
    
    def _batch_get_stock_names(self, symbols: List[str]) -> Dict[str, str]:
        """
        批量获取股票名称映射
        
        Args:
            symbols: 股票代码列表
        
        Returns:
            {symbol: stock_name} 字典
        """
        name_map = {}
        
        # 1. 从数据库批量获取
        try:
            if symbols:
                placeholders = ','.join(['%s'] * len(symbols))
                sql = f"""
                    SELECT DISTINCT symbol, name 
                    FROM stock_history_data 
                    WHERE symbol IN ({placeholders}) 
                    AND name IS NOT NULL 
                    AND name != '' 
                    AND name != symbol
                    ORDER BY symbol, trade_date DESC
                """
                results = self.db.execute_query(sql, symbols)
                for row in results:
                    symbol = str(row['symbol']).zfill(6)
                    name = str(row.get('name', '')).strip()
                    if name and name != symbol and symbol not in name_map:
                        name_map[symbol] = name
        except Exception as e:
            self.logger.debug(f"从数据库批量获取股票名称失败: {str(e)}")
        
        # 2. 对于数据库中没有的股票，从Tushare stock_basic批量获取
        missing_symbols = [s for s in symbols if s not in name_map]
        if missing_symbols:
            try:
                # 速率限制：等待直到可以发送请求
                wait_time = self.rate_limiter.wait_if_needed()
                if wait_time > 0:
                    time.sleep(wait_time)
                
                # 调用stock_basic接口获取所有股票
                df = self.pro.stock_basic(
                    exchange='',
                    list_status='L',
                    fields='ts_code,symbol,name'
                )
                
                if df is not None and not df.empty:
                    # 构建symbol到ts_code的映射
                    symbol_to_ts_code = {}
                    for s in missing_symbols:
                        symbol_to_ts_code[s] = self.convert_ts_code(s)
                    
                    # 查找对应的股票名称
                    for symbol in missing_symbols:
                        ts_code = symbol_to_ts_code[symbol]
                        stock_row = df[df['ts_code'] == ts_code]
                        if not stock_row.empty:
                            stock_name = str(stock_row.iloc[0]['name']).strip()
                            if stock_name and stock_name != symbol:
                                name_map[symbol] = stock_name
            except Exception as e:
                self.logger.debug(f"从Tushare stock_basic批量获取股票名称失败: {str(e)}")
        
        # 3. 对于仍然没有名称的股票，返回时使用股票代码
        # 注意：不再使用StockDataSource，只使用Tushare
        
        return name_map
    
    def _batch_get_valuation_from_akshare(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        从AkShare批量获取PE/PB/市值数据（专门负责这4个字段）
        
        Args:
            symbols: 股票代码列表
        
        Returns:
            {symbol: {'pe_ratio': ..., 'pb_ratio': ..., 'total_market_cap': ..., 'float_market_cap': ...}} 字典
        """
        valuation_map = {}
        
        try:
            import akshare as ak
            
            self.logger.info(f"从AkShare批量获取 {len(symbols)} 只股票的估值数据（PE/PB/总市值/流通市值）...")
            
            # 使用AkShare的实时行情接口，一次性获取所有股票的数据
            # ak.stock_zh_a_spot_em() 可以获取所有A股的实时行情，包括PE/PB/市值
            # 使用_call_akshare_without_proxy禁用代理，避免代理连接错误
            try:
                from data_source.stock_data_source import _call_akshare_without_proxy
                df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
                
                if df is not None and not df.empty:
                    # 查找代码列和估值列
                    code_col = None
                    pe_col = None
                    pb_col = None
                    total_mv_col = None
                    circ_mv_col = None
                    
                    for col in df.columns:
                        col_str = str(col)
                        col_lower = col_str.lower()
                        if '代码' in col_str or 'code' in col_lower:
                            code_col = col
                        elif '市盈率' in col_str and ('动态' in col_str or 'pe' in col_lower):
                            pe_col = col
                        elif '市净率' in col_str or ('pb' in col_lower and '市净' in col_str):
                            pb_col = col
                        elif '总市值' in col_str:
                            total_mv_col = col
                        elif '流通市值' in col_str:
                            circ_mv_col = col
                    
                    if code_col:
                        # 遍历需要的股票代码
                        for symbol in symbols:
                            symbol_str = str(symbol).zfill(6)
                            stock_data = df[df[code_col] == symbol_str]
                            
                            if not stock_data.empty:
                                row = stock_data.iloc[0]
                                valuation_data = {}
                                
                                # 获取PE（市盈率）
                                if pe_col and pe_col in df.columns:
                                    try:
                                        pe_value = row[pe_col]
                                        if pd.notna(pe_value):
                                            pe_str = str(pe_value).replace('倍', '').replace(',', '').replace('--', '').strip()
                                            if pe_str and pe_str != 'nan' and pe_str != '-' and pe_str:
                                                pe_float = float(pe_str)
                                                if pe_float > 0:  # PE应该大于0
                                                    valuation_data['pe_ratio'] = pe_float
                                    except Exception as e:
                                        self.logger.debug(f"解析PE失败 {symbol}: {str(e)}")
                                
                                # 获取PB（市净率）
                                if pb_col and pb_col in df.columns:
                                    try:
                                        pb_value = row[pb_col]
                                        if pd.notna(pb_value):
                                            pb_str = str(pb_value).replace('倍', '').replace(',', '').replace('--', '').strip()
                                            if pb_str and pb_str != 'nan' and pb_str != '-' and pb_str:
                                                pb_float = float(pb_str)
                                                if pb_float > 0:  # PB应该大于0
                                                    valuation_data['pb_ratio'] = pb_float
                                    except Exception as e:
                                        self.logger.debug(f"解析PB失败 {symbol}: {str(e)}")
                                
                                # 获取总市值（单位：元）
                                if total_mv_col and total_mv_col in df.columns:
                                    try:
                                        total_mv_value = row[total_mv_col]
                                        if pd.notna(total_mv_value):
                                            total_mv_str = str(total_mv_value).replace(',', '').replace('元', '').replace('万', '').strip()
                                            if total_mv_str and total_mv_str != 'nan' and total_mv_str != '-':
                                                total_mv_float = float(total_mv_str)
                                                # 如果原值包含"万"，需要乘以10000
                                                if '万' in str(total_mv_value):
                                                    total_mv_float = total_mv_float * 10000
                                                if total_mv_float > 0:
                                                    valuation_data['total_market_cap'] = total_mv_float
                                    except Exception as e:
                                        self.logger.debug(f"解析总市值失败 {symbol}: {str(e)}")
                                
                                # 获取流通市值（单位：元）
                                if circ_mv_col and circ_mv_col in df.columns:
                                    try:
                                        circ_mv_value = row[circ_mv_col]
                                        if pd.notna(circ_mv_value):
                                            circ_mv_str = str(circ_mv_value).replace(',', '').replace('元', '').replace('万', '').strip()
                                            if circ_mv_str and circ_mv_str != 'nan' and circ_mv_str != '-':
                                                circ_mv_float = float(circ_mv_str)
                                                # 如果原值包含"万"，需要乘以10000
                                                if '万' in str(circ_mv_value):
                                                    circ_mv_float = circ_mv_float * 10000
                                                if circ_mv_float > 0:
                                                    valuation_data['float_market_cap'] = circ_mv_float
                                    except Exception as e:
                                        self.logger.debug(f"解析流通市值失败 {symbol}: {str(e)}")
                                
                                # 只要有任何一个字段，就添加到映射中
                                if valuation_data:
                                    valuation_map[symbol] = valuation_data
                        
                        self.logger.info(f"从AkShare成功获取 {len(valuation_map)} 只股票的估值数据")
                    else:
                        self.logger.warning("AkShare返回的数据中未找到代码列")
            except Exception as e:
                self.logger.warning(f"从AkShare获取估值数据失败: {str(e)}")
                import traceback
                self.logger.debug(traceback.format_exc())
        
        except ImportError:
            self.logger.warning("AkShare未安装，无法获取估值数据")
        except Exception as e:
            self.logger.warning(f"从AkShare批量获取估值数据异常: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
        
        return valuation_map
    
    def get_all_stock_list(self, use_database: bool = True) -> List[str]:
        """
        获取所有A股股票代码列表
        
        Args:
            use_database: 是否优先从数据库获取（默认True，避免网络问题）
        """
        symbols = []
        
        # 优先从数据库获取已有股票的列表
        if use_database:
            try:
                self.logger.info("从数据库获取股票列表...")
                sql = "SELECT DISTINCT symbol FROM stock_history_data ORDER BY symbol"
                results = self.db.execute_query(sql)
                symbols = [str(row['symbol']).zfill(6) for row in results if row.get('symbol')]
                
                if symbols:
                    self.logger.info(f"从数据库获取到 {len(symbols)} 只股票")
                    return symbols
                else:
                    self.logger.warning("数据库中暂无股票数据，尝试从API获取...")
            except Exception as e:
                self.logger.warning(f"从数据库获取股票列表失败: {str(e)}，尝试从API获取...")
        
        # 如果数据库没有数据，从API获取
        try:
            from data_source.stock_data_source import StockDataSource
            data_source = StockDataSource()
            self.logger.info("从API获取股票列表...")
            all_stocks = data_source.get_all_stock_list(limit=None, sort_by_turnover=False, use_cache=True)
            symbols = [str(s.get('symbol')).zfill(6) for s in all_stocks if s.get('symbol')]
            self.logger.info(f"从API获取到 {len(symbols)} 只股票")
            return symbols
        except Exception as e:
            self.logger.error(f"从API获取股票列表失败: {str(e)}")
            # 如果API也失败，返回数据库中的股票列表（即使为空）
            return symbols
    
    def convert_ts_code(self, symbol: str) -> str:
        """转换股票代码为Tushare格式"""
        symbol = str(symbol).zfill(6)
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        elif symbol.startswith(('0', '3')):
            return f"{symbol}.SZ"
        else:
            return symbol
    
    def fetch_stock_data_from_tushare(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从Tushare获取股票数据（带速率限制控制）
        
        根据Tushare官方文档：
        - 接口：pro.daily()
        - 参数：ts_code（股票代码，如000001.SZ）, start_date（YYYYMMDD）, end_date（YYYYMMDD）
        - 返回字段：ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
        - 注意：amount单位是千元，vol单位是手
        - 速率限制：每分钟最多50次请求（由rate_limiter自动处理）
        
        Args:
            ts_code: Tushare格式的股票代码（如：000001.SZ）
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
        
        Returns:
            DataFrame或None（如果遇到速率限制，返回None）
        """
        try:
            # 速率限制：等待直到可以发送请求（自动处理，不重试）
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                time.sleep(wait_time)
            
            # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
            start_date_str = start_date.replace('-', '')
            end_date_str = end_date.replace('-', '')
            
            # 调用Tushare API
            # 根据官方文档：pro.daily(ts_code='000001.SZ', start_date='20180701', end_date='20180718')
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            if df is None or df.empty:
                return None
            
            # 验证返回的字段
            expected_fields = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']
            missing_fields = [f for f in expected_fields if f not in df.columns]
            if missing_fields:
                self.logger.warning(f"Tushare返回的DataFrame缺少字段: {missing_fields}")
                self.logger.debug(f"实际返回的字段: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 检测速率限制错误
            is_rate_limit = any(keyword in error_str for keyword in [
                'rate limit', '429', 'too many requests', 
                '每分钟最多', '访问该接口', '权限的具体详情',
                '请求过于频繁', '访问频率', '请求次数'
            ])
            
            if is_rate_limit:
                # 遇到速率限制，直接返回None，不重试
                # 速率限制器会在下次请求时自动等待
                self.logger.debug(f"速率限制: {ts_code}，跳过本次请求（速率限制器会自动处理）")
                return None
            elif 'permission' in error_str or '权限' in error_str:
                raise Exception(f"权限不足: {str(e)}")
            else:
                raise Exception(f"获取数据失败: {str(e)}")
    
    def fetch_all_stocks_by_date(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        按日期批量获取所有股票的数据（优化：一次API调用获取所有股票）
        
        根据Tushare官方文档：
        - 接口：pro.daily(trade_date='20180810')
        - 可以获取所有股票在指定日期的数据
        - 单次最大返回6000条数据
        - 基础积分每分钟内可调取500次
        
        Args:
            trade_date: 交易日期（YYYY-MM-DD格式）
        
        Returns:
            DataFrame或None
        """
        try:
            # 速率限制：等待直到可以发送请求
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                time.sleep(wait_time)
            
            # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
            trade_date_str = trade_date.replace('-', '')
            
            # 调用Tushare API：不传ts_code，只传trade_date，获取所有股票的数据
            df = self.pro.daily(trade_date=trade_date_str)
            
            if df is None or df.empty:
                return None
            
            # 验证返回的字段
            expected_fields = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']
            missing_fields = [f for f in expected_fields if f not in df.columns]
            if missing_fields:
                self.logger.warning(f"Tushare返回的DataFrame缺少字段: {missing_fields}")
                self.logger.debug(f"实际返回的字段: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = any(keyword in error_str for keyword in [
                'rate limit', '429', 'too many requests', 
                '每分钟最多', '访问该接口', '权限的具体详情',
                '请求过于频繁', '访问频率', '请求次数'
            ])
            
            if is_rate_limit:
                self.logger.debug(f"速率限制: {trade_date}，跳过本次请求")
                return None
            else:
                self.logger.error(f"获取所有股票数据失败 {trade_date}: {str(e)}")
                return None
    
    def fetch_all_stocks_daily_basic_by_date(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        按日期批量获取所有股票的基本面数据（优化：一次API调用获取所有股票）
        
        根据Tushare官方文档：
        - 接口：pro.daily_basic(ts_code='', trade_date='20180726')
        - 可以获取所有股票在指定日期的基本面数据
        - 单次最大返回6000条数据
        - 需要至少2000积分
        
        Args:
            trade_date: 交易日期（YYYY-MM-DD格式）
        
        Returns:
            DataFrame或None
        """
        try:
            # 速率限制：等待直到可以发送请求
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                time.sleep(wait_time)
            
            # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
            trade_date_str = trade_date.replace('-', '')
            
            # 调用Tushare API：不传ts_code（传空字符串），只传trade_date，获取所有股票的数据
            df = self.pro.daily_basic(ts_code='', trade_date=trade_date_str)
            
            if df is None or df.empty:
                return None
            
            return df
            
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = any(keyword in error_str for keyword in [
                'rate limit', '429', 'too many requests', 
                '每分钟最多', '访问该接口', '权限的具体详情',
                '请求过于频繁', '访问频率', '请求次数'
            ])
            
            if is_rate_limit:
                self.logger.debug(f"daily_basic速率限制: {trade_date}，跳过本次请求")
                return None
            elif 'permission' in error_str or '权限' in error_str or '积分' in error_str or '2000' in error_str:
                self.logger.debug(f"daily_basic接口权限不足 {trade_date}: {str(e)} (需要至少2000积分)")
                return None
            else:
                self.logger.debug(f"获取daily_basic数据失败 {trade_date}: {str(e)}")
                return None
    
    def fetch_daily_basic_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从Tushare获取每日基本面数据（换手率等，不包含PE/PB/市值）
        
        注意：
        - daily_basic接口需要至少2000积分才能调用
        - PE/PB/市值由AkShare专门负责，这里只获取换手率等其他数据
        
        Args:
            ts_code: Tushare格式的股票代码
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
        
        Returns:
            DataFrame或None
        """
        try:
            # 速率限制：等待直到可以发送请求（自动处理，不重试）
            wait_time = self.rate_limiter.wait_if_needed()
            if wait_time > 0:
                time.sleep(wait_time)
            
            # 转换日期格式
            start_date_str = start_date.replace('-', '')
            end_date_str = end_date.replace('-', '')
            
            # 调用daily_basic接口
            # 根据官方文档，字段包括：ts_code, trade_date, turnover_rate, volume_ratio等
            # 注意：PE/PB/市值由AkShare专门负责，这里只获取换手率等其他数据
            df = self.pro.daily_basic(
                ts_code=ts_code,
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            if df is None or df.empty:
                self.logger.debug(f"daily_basic返回空数据 {ts_code}")
                return None
            
            # 验证返回的字段（只检查换手率，PE/PB/市值由AkShare负责）
            expected_fields = ['ts_code', 'trade_date', 'turnover_rate']
            available_fields = [f for f in expected_fields if f in df.columns]
            missing_fields = [f for f in expected_fields if f not in df.columns]
            
            if missing_fields:
                self.logger.debug(f"daily_basic返回的字段不完整 {ts_code}: 缺少 {missing_fields}, 可用字段: {available_fields}")
            
            return df
        except Exception as e:
            error_str = str(e).lower()
            
            # 检测速率限制错误
            is_rate_limit = any(keyword in error_str for keyword in [
                'rate limit', '429', 'too many requests', 
                '每分钟最多', '访问该接口', '权限的具体详情',
                '请求过于频繁', '访问频率', '请求次数'
            ])
            
            if is_rate_limit:
                # 遇到速率限制，直接返回None，不重试
                # 速率限制器会在下次请求时自动等待
                self.logger.debug(f"daily_basic速率限制: {ts_code}，跳过本次请求（速率限制器会自动处理）")
                return None
            # daily_basic需要至少2000积分，如果权限不足会报错
            elif 'permission' in error_str or '权限' in error_str or '积分' in error_str or '2000' in error_str:
                self.logger.debug(f"daily_basic接口权限不足 {ts_code}: {str(e)} (需要至少2000积分)")
                return None
            else:
                self.logger.debug(f"获取daily_basic数据失败 {ts_code}: {str(e)}")
                return None
    
    def get_historical_data_for_indicators(self, symbol: str, trade_date: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取历史数据用于计算技术指标
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期
            days: 需要的历史天数
        
        Returns:
            DataFrame（包含close, volume等字段）或None
        """
        try:
            # 从数据库获取历史数据
            # 注意：使用 trade_date < %s 而不是 trade_date <= %s
            # 原因：避免历史数据包含当前日期，导致在calculate_technical_indicators中重复添加current_close
            sql = """
                SELECT trade_date, close_price, volume
                FROM stock_history_data
                WHERE symbol = %s AND trade_date < %s
                ORDER BY trade_date DESC
                LIMIT %s
            """
            results = self.db.execute_query(sql, (symbol, trade_date, days))
            
            if not results:
                return None
            
            # 转换为DataFrame
            data = []
            for row in results:
                data.append({
                    'trade_date': str(row['trade_date']),
                    'close': float(row['close_price']) if row.get('close_price') else None,
                    'volume': int(row['volume']) if row.get('volume') else None
                })
            
            df = pd.DataFrame(data)
            if df.empty:
                return None
            
            # 按日期排序（从旧到新）
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            df = df.set_index('trade_date')
            
            return df
        except Exception as e:
            self.logger.debug(f"获取历史数据失败 {symbol} {trade_date}: {str(e)}")
            return None
    
    def calculate_technical_indicators(self, history_df: pd.DataFrame, current_close: float) -> Dict:
        """
        计算技术指标
        
        Args:
            history_df: 历史数据DataFrame（包含close和volume列）
            current_close: 当前收盘价
        
        Returns:
            包含技术指标的字典
        """
        indicators = {
            'ma5': None,
            'ma10': None,
            'ma20': None,
            'ma60': None,
            'rsi': None,
            'macd': None,
            'macd_signal': None,
            'macd_hist': None,
            'x2': None
        }
        
        if history_df is None or history_df.empty or 'close' not in history_df.columns:
            return indicators
        
        try:
            closes = history_df['close'].dropna()
            if len(closes) == 0:
                return indicators
            
            # 添加当前收盘价
            closes = pd.concat([closes, pd.Series([current_close])])
            
            # 计算移动平均线
            if len(closes) >= 5:
                indicators['ma5'] = float(closes.tail(5).mean())
            if len(closes) >= 10:
                indicators['ma10'] = float(closes.tail(10).mean())
            if len(closes) >= 20:
                indicators['ma20'] = float(closes.tail(20).mean())
            if len(closes) >= 60:
                indicators['ma60'] = float(closes.tail(60).mean())
            
            # 计算RSI（14周期）
            if len(closes) >= 14:
                delta = closes.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                indicators['rsi'] = float(rsi.iloc[-1]) if not rsi.empty else None
            
            # 计算MACD
            if len(closes) >= 26:
                ema12 = closes.ewm(span=12, adjust=False).mean()
                ema26 = closes.ewm(span=26, adjust=False).mean()
                macd = ema12 - ema26
                macd_signal = macd.ewm(span=9, adjust=False).mean()
                macd_hist = macd - macd_signal
                indicators['macd'] = float(macd.iloc[-1]) if not macd.empty else None
                indicators['macd_signal'] = float(macd_signal.iloc[-1]) if not macd_signal.empty else None
                indicators['macd_hist'] = float(macd_hist.iloc[-1]) if not macd_hist.empty else None
            
            # 计算X2指标（收盘价在20日价格区间中的相对位置，0-100）
            if len(closes) >= 20:
                recent_20 = closes.tail(20)
                high_20 = recent_20.max()
                low_20 = recent_20.min()
                if high_20 > low_20:
                    x2 = ((current_close - low_20) / (high_20 - low_20)) * 100
                    indicators['x2'] = float(x2)
        except Exception as e:
            self.logger.debug(f"计算技术指标失败: {str(e)}")
        
        return indicators
    
    def calculate_limit_prices(self, symbol: str, pre_close: float) -> Dict:
        """
        计算涨跌停价
        
        Args:
            symbol: 股票代码
            pre_close: 昨收价
        
        Returns:
            包含涨跌停信息的字典
        """
        if pre_close is None or pre_close <= 0:
            return {
                'limit_up': None,
                'limit_down': None,
                'limit_pct': None,
                'is_limit_up': False,
                'is_limit_down': False
            }
        
        # 判断股票类型，确定涨跌停幅度
        symbol_str = str(symbol).zfill(6)
        if symbol_str.startswith('688') or symbol_str.startswith('300'):
            # 科创板/创业板：20%
            limit_pct = 20.0
        elif symbol_str.startswith('8') or symbol_str.startswith('4'):
            # 北交所：30%
            limit_pct = 30.0
        else:
            # 普通股票：10%
            limit_pct = 10.0
        
        limit_up = round(pre_close * (1 + limit_pct / 100), 2)
        limit_down = round(pre_close * (1 - limit_pct / 100), 2)
        
        return {
            'limit_up': limit_up,
            'limit_down': limit_down,
            'limit_pct': limit_pct
        }
    
    def calculate_volume_ratio(self, symbol: str, trade_date: str, current_volume: int) -> Optional[float]:
        """
        计算量比（当前成交量/过去5日平均成交量）
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期
            current_volume: 当前成交量
        
        Returns:
            量比或None
        """
        if current_volume is None or current_volume <= 0:
            return None
        
        try:
            # 获取过去5个交易日的数据
            sql = """
                SELECT volume
                FROM stock_history_data
                WHERE symbol = %s AND trade_date < %s AND volume IS NOT NULL AND volume > 0
                ORDER BY trade_date DESC
                LIMIT 5
            """
            results = self.db.execute_query(sql, (symbol, trade_date))
            
            if not results or len(results) < 1:
                return None
            
            volumes = [int(row['volume']) for row in results if row.get('volume')]
            if not volumes:
                return None
            
            avg_volume = sum(volumes) / len(volumes)
            if avg_volume > 0:
                return round(current_volume / avg_volume, 4)
        except Exception as e:
            self.logger.debug(f"计算量比失败 {symbol} {trade_date}: {str(e)}")
        
        return None
    
    def convert_tushare_to_storage_format(self, df: pd.DataFrame, symbol: str, name: str = None, 
                                         daily_basic_df: Optional[pd.DataFrame] = None,
                                         akshare_valuation: Dict = None) -> List[Dict]:
        """
        将Tushare数据转换为存储格式
        
        Args:
            df: Tushare返回的DataFrame
            symbol: 股票代码（6位数字）
            name: 股票名称（可选）
            daily_basic_df: Tushare daily_basic接口返回的DataFrame（可选，只包含换手率等）
            akshare_valuation: 从AkShare获取的估值数据字典（可选，包含pe_ratio, pb_ratio, total_market_cap, float_market_cap）
        
        Returns:
            数据字典列表
        """
        data_list = []
        
        # 优化：一次性获取所有需要的历史数据（避免在循环中重复查询数据库）
        # 获取最早日期，一次性获取足够的历史数据（从最早日期往前60天）
        history_df_all = None
        if not df.empty:
            # 获取日期范围
            dates_in_df = []
            for _, row in df.iterrows():
                trade_date = str(row.get('trade_date', ''))
                if len(trade_date) == 8:
                    trade_date_formatted = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
                    dates_in_df.append(trade_date_formatted)
            
            if dates_in_df:
                # 获取最早日期，用于一次性获取历史数据
                earliest_date = min(dates_in_df)
                
                # 一次性获取足够的历史数据（从最早日期往前60天）
                # 这样可以为所有日期提供足够的历史数据来计算技术指标
                history_df_all = self.get_historical_data_for_indicators(symbol, earliest_date, days=60)
                
                # 如果获取失败，history_df_all 为 None，后续会为每个日期单独获取（兜底方案）
                if history_df_all is None or history_df_all.empty:
                    self.logger.debug(f"{symbol}: 无法一次性获取历史数据，将逐日获取")
                    history_df_all = None
        
        # 按日期排序（从早到晚），确保技术指标计算的连续性
        # 这样可以为每个日期逐步累积历史数据，提高MACD计算的准确性
        df_sorted = df.copy()
        if 'trade_date' in df_sorted.columns:
            # 转换日期格式用于排序
            def parse_date(x):
                x_str = str(x)
                if len(x_str) == 8:
                    return pd.to_datetime(f"{x_str[:4]}-{x_str[4:6]}-{x_str[6:8]}")
                else:
                    return pd.to_datetime(x_str)
            
            df_sorted['_sort_date'] = df_sorted['trade_date'].apply(parse_date)
            df_sorted = df_sorted.sort_values('_sort_date')
        
        # 累积历史数据（用于逐步计算技术指标）
        cumulative_history_df = history_df_all.copy() if history_df_all is not None else None
        
        for _, row in df_sorted.iterrows():
            # 根据Tushare官方文档，daily接口返回的字段：
            # ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
            # 注意：vol是成交量（手），amount是成交额（千元），需要转换为元
            
            # 1. 处理交易日期
            trade_date = str(row.get('trade_date', ''))
            # 转换日期格式：YYYYMMDD -> YYYY-MM-DD
            if len(trade_date) == 8:
                trade_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
            elif len(trade_date) == 10 and '-' in trade_date:
                # 如果已经是YYYY-MM-DD格式，保持不变
                pass
            else:
                self.logger.warning(f"日期格式异常: {trade_date}，跳过该条记录")
                continue
            
            # 2. 获取股票名称
            # 如果传入了name参数，优先使用
            if name and name != symbol:
                stock_name = name
            else:
                # 从Tushare DataFrame中获取ts_code
                ts_code_for_name = None
                if 'ts_code' in df.columns and pd.notna(row.get('ts_code')):
                    ts_code_for_name = str(row.get('ts_code'))
                elif symbol:
                    # 如果没有ts_code，根据symbol构造
                    ts_code_for_name = self.convert_ts_code(symbol)
                
                # 获取股票名称（从数据库或API）
                stock_name = self.get_stock_name(symbol, ts_code_for_name)
            
            # 3. 价格数据（直接映射）
            open_price = float(row.get('open')) if pd.notna(row.get('open')) else None
            close_price = float(row.get('close')) if pd.notna(row.get('close')) else None
            high_price = float(row.get('high')) if pd.notna(row.get('high')) else None
            low_price = float(row.get('low')) if pd.notna(row.get('low')) else None
            pre_close = float(row.get('pre_close')) if pd.notna(row.get('pre_close')) else None
            
            # 4. 涨跌额（优先使用change字段，否则计算）
            change_amount = None
            if pd.notna(row.get('change')):
                change_amount = float(row.get('change'))
            elif close_price is not None and pre_close is not None:
                change_amount = close_price - pre_close
            
            # 5. 涨跌幅（优先使用pct_chg字段，否则计算）
            change_pct = None
            if pd.notna(row.get('pct_chg')):
                change_pct = float(row.get('pct_chg'))
            elif close_price is not None and pre_close is not None and pre_close > 0:
                change_pct = ((close_price - pre_close) / pre_close) * 100
            
            # 6. 成交量（vol单位是手，直接使用）
            volume_shou = None
            if pd.notna(row.get('vol')):
                volume_shou = int(row.get('vol'))
            
            # 7. 成交额（amount单位是千元，需要转换为元）
            amount_yuan = None
            if pd.notna(row.get('amount')):
                amount_yuan = float(row.get('amount')) * 1000  # 千元转元
            
            # 8. 计算振幅（基于最高价、最低价和昨收价）
            amplitude = None
            if high_price is not None and low_price is not None and pre_close is not None and pre_close > 0:
                amplitude = ((high_price - low_price) / pre_close) * 100
            
            # 9. 计算价格区间（最高价-最低价）
            price_range = None
            if high_price is not None and low_price is not None:
                price_range = high_price - low_price
            
            # 10. 从daily_basic获取基本面数据（如果提供）
            # 注意：PE/PB/市值由AkShare专门获取，这里只获取换手率等其他数据
            turnover_rate = None
            
            if daily_basic_df is not None and not daily_basic_df.empty:
                # 查找对应日期的数据（daily_basic的trade_date也是YYYYMMDD格式）
                trade_date_str = str(row.get('trade_date'))  # YYYYMMDD格式
                if len(trade_date_str) == 8:
                    # 匹配daily_basic中的trade_date（也是YYYYMMDD格式）
                    basic_row = daily_basic_df[daily_basic_df['trade_date'] == trade_date_str]
                    if not basic_row.empty:
                        basic_row = basic_row.iloc[0]
                        
                        # 换手率（%）
                        if 'turnover_rate' in daily_basic_df.columns and pd.notna(basic_row.get('turnover_rate')):
                            turnover_rate = float(basic_row.get('turnover_rate'))
            
            # 11. 从AkShare获取PE/PB/市值数据（专门由AkShare负责）
            pe_ratio = None
            pb_ratio = None
            total_market_cap = None
            float_market_cap = None
            
            if akshare_valuation:
                pe_ratio = akshare_valuation.get('pe_ratio')
                pb_ratio = akshare_valuation.get('pb_ratio')
                total_market_cap = akshare_valuation.get('total_market_cap')
                float_market_cap = akshare_valuation.get('float_market_cap')
            
            # 12. 计算涨跌停价
            limit_info = self.calculate_limit_prices(symbol, pre_close)
            is_limit_up = False
            is_limit_down = False
            if close_price is not None and limit_info['limit_up'] is not None:
                is_limit_up = abs(close_price - limit_info['limit_up']) < 0.01
            if close_price is not None and limit_info['limit_down'] is not None:
                is_limit_down = abs(close_price - limit_info['limit_down']) < 0.01
            
            # 13. 计算量比（需要历史数据，这里先设为None，后续在保存时计算）
            volume_ratio = None
            
            # 14. 获取历史数据并计算技术指标（优化：使用预获取的历史数据，逐步累积）
            trade_date_obj = pd.to_datetime(trade_date)
            
            if cumulative_history_df is not None and not cumulative_history_df.empty:
                # 使用累积的历史数据，只包含当前日期之前的数据
                # 过滤出当前日期之前的历史数据（使用 trade_date < %s 的逻辑）
                history_df = cumulative_history_df[cumulative_history_df.index < trade_date_obj].copy()
                
                # 如果预获取的历史数据不足，尝试单独获取（兜底方案）
                if history_df.empty or len(history_df) < 26:
                    self.logger.debug(f"{symbol} {trade_date}: 累积历史数据不足（{len(history_df)}条），单独获取")
                    history_df = self.get_historical_data_for_indicators(symbol, trade_date, days=60)
                    # 更新累积历史数据
                    if history_df is not None and not history_df.empty:
                        cumulative_history_df = pd.concat([cumulative_history_df, history_df]).drop_duplicates().sort_index()
            else:
                # 如果预获取失败，为每个日期单独获取（兜底方案）
                history_df = self.get_historical_data_for_indicators(symbol, trade_date, days=60)
                # 更新累积历史数据
                if history_df is not None and not history_df.empty:
                    if cumulative_history_df is None or cumulative_history_df.empty:
                        cumulative_history_df = history_df.copy()
                    else:
                        cumulative_history_df = pd.concat([cumulative_history_df, history_df]).drop_duplicates().sort_index()
            
            # 计算技术指标（确保历史数据不包含当前日期）
            technical_indicators = self.calculate_technical_indicators(history_df, close_price or 0)
            
            # 将当前日期的数据添加到累积历史数据中（用于下一个日期的计算）
            if close_price is not None and cumulative_history_df is not None:
                current_row = pd.DataFrame({
                    'close': [close_price],
                    'volume': [volume_shou] if volume_shou else [None]
                }, index=[trade_date_obj])
                cumulative_history_df = pd.concat([cumulative_history_df, current_row]).sort_index()
            
            # 15. Level2数据（历史数据通常没有，设为None）
            # 外盘、内盘、买卖盘等数据需要实时行情，历史数据无法获取
            outer_volume = None
            inner_volume = None
            bid_ask_ratio = None
            bid_levels = None
            ask_levels = None
            bid_total_volume = None
            ask_total_volume = None
            cost_distribution = None
            cost_distribution_history = None
            cost_distribution_intraday = None
            
            # 16. 资金流向数据（历史数据通常没有，设为None）
            main_net_inflow = None
            super_large_inflow = None
            large_inflow = None
            medium_inflow = None
            small_inflow = None
            
            # 17. 融资融券数据（需要其他接口，设为None）
            margin_balance = None
            short_balance = None
            margin_ratio = None
            
            # 18. 额外数据（JSON格式）
            extra_data = None
            
            # 构建完整数据字典（按照数据库表字段顺序）
            data = {
                'symbol': symbol,
                'name': stock_name,
                'trade_date': trade_date,
                'period_type': 'daily',
                # 基本价格数据
                'open_price': open_price,
                'close_price': close_price,
                'high_price': high_price,
                'low_price': low_price,
                'pre_close': pre_close,
                'change_amount': change_amount,
                'change_pct': change_pct,
                # 成交数据
                'volume': volume_shou,  # 单位：手
                'amount': amount_yuan,   # 单位：元（已从千元转换）
                'turnover_rate': turnover_rate,  # 换手率（%）
                'volume_ratio': volume_ratio,  # 量比（后续计算）
                # 盘口数据（历史数据通常没有）
                'outer_volume': outer_volume,
                'inner_volume': inner_volume,
                'bid_ask_ratio': bid_ask_ratio,
                'bid_levels': bid_levels,
                'ask_levels': ask_levels,
                'bid_total_volume': bid_total_volume,
                'ask_total_volume': ask_total_volume,
                # 成本分布数据（历史数据通常没有）
                'cost_distribution': cost_distribution,
                'cost_distribution_history': cost_distribution_history,
                'cost_distribution_intraday': cost_distribution_intraday,
                # 市值和估值
                'total_market_cap': total_market_cap,  # 总市值（元）
                'float_market_cap': float_market_cap,  # 流通市值（元）
                'pe_ratio': pe_ratio,  # 市盈率
                'pb_ratio': pb_ratio,  # 市净率
                # 涨跌停信息
                'limit_up': limit_info['limit_up'],
                'limit_down': limit_info['limit_down'],
                'limit_pct': limit_info['limit_pct'],
                'is_limit_up': 1 if is_limit_up else 0,
                'is_limit_down': 1 if is_limit_down else 0,
                # 振幅和波动
                'amplitude': amplitude,
                'price_range': price_range,
                # 技术指标
                'ma5': technical_indicators['ma5'],
                'ma10': technical_indicators['ma10'],
                'ma20': technical_indicators['ma20'],
                'ma60': technical_indicators['ma60'],
                'rsi': technical_indicators['rsi'],
                'macd': technical_indicators['macd'],
                'macd_signal': technical_indicators['macd_signal'],
                'macd_hist': technical_indicators['macd_hist'],
                'x2': technical_indicators['x2'],
                # 资金流向数据（历史数据通常没有）
                'main_net_inflow': main_net_inflow,
                'super_large_inflow': super_large_inflow,
                'large_inflow': large_inflow,
                'medium_inflow': medium_inflow,
                'small_inflow': small_inflow,
                # 融资融券数据（需要其他接口）
                'margin_balance': margin_balance,
                'short_balance': short_balance,
                'margin_ratio': margin_ratio,
                # 其他数据
                'extra_data': extra_data,
                # 元数据
                'data_source': 'tushare',
                'data_quality_score': 1.0,
                'is_valid': 1
            }
            
            data_list.append(data)
        
        return data_list
    
    def _process_single_date(self, trade_date: str, existing_data: Dict[str, Set[str]], 
                             stock_name_map: Dict[str, str], valuation_map: Dict[str, Dict]) -> Dict:
        """
        处理单个日期的数据（按日期批量获取优化）
        
        Args:
            trade_date: 交易日期（YYYY-MM-DD格式）
            existing_data: 已有数据字典 {symbol: set(trade_dates)}
            stock_name_map: 股票名称映射字典
            valuation_map: 估值数据映射字典
        
        Returns:
            处理结果字典
        """
        result = {
            'trade_date': trade_date,
            'success_count': 0,
            'fail_count': 0,
            'skip_count': 0
        }
        
        try:
            # 1. 批量获取所有股票在该日期的数据
            df = self.fetch_all_stocks_by_date(trade_date)
            if df is None or df.empty:
                self.logger.warning(f"  ⚠ {trade_date}: 无法获取股票数据")
                result['fail_count'] = 1
                return result
            
            # 2. 批量获取所有股票在该日期的基本面数据
            daily_basic_df = self.fetch_all_stocks_daily_basic_by_date(trade_date)
            if daily_basic_df is None or daily_basic_df.empty:
                self.logger.debug(f"  - {trade_date}: 无法获取基本面数据（可能需要更高权限）")
            
            # 3. 转换ts_code为symbol（6位数字）
            df['symbol'] = df['ts_code'].apply(lambda x: x.split('.')[0].zfill(6))
            
            # 4. 过滤出需要保存的股票（只保存缺失的数据）
            if existing_data:
                # 过滤出在该日期缺失数据的股票
                symbols_to_save = []
                for symbol in df['symbol'].unique():
                    existing_dates = existing_data.get(symbol, set())
                    if trade_date not in existing_dates:
                        symbols_to_save.append(symbol)
                df = df[df['symbol'].isin(symbols_to_save)]
            
            if df.empty:
                result['skip_count'] = 0
                self.logger.info(f"  ✓ {trade_date}: 所有股票数据已存在，跳过")
                return result
            
            # 5. 按股票分组处理数据
            all_data_list = []
            for symbol in df['symbol'].unique():
                symbol_df = df[df['symbol'] == symbol]
                if symbol_df.empty:
                    continue
                
                # 获取股票名称
                stock_name = stock_name_map.get(symbol, symbol)
                
                # 获取估值数据
                akshare_valuation = valuation_map.get(symbol, {})
                
                # 获取该股票的基本面数据
                symbol_daily_basic = None
                if daily_basic_df is not None and not daily_basic_df.empty:
                    symbol_ts_code = self.convert_ts_code(symbol)
                    symbol_daily_basic = daily_basic_df[daily_basic_df['ts_code'] == symbol_ts_code].copy()
                    if symbol_daily_basic.empty:
                        symbol_daily_basic = None
                
                # 转换为存储格式（只处理该日期的数据）
                data_list = self.convert_tushare_to_storage_format(
                    symbol_df, symbol, name=stock_name,
                    daily_basic_df=symbol_daily_basic,
                    akshare_valuation=akshare_valuation
                )
                
                # 只保存该日期的数据
                for data in data_list:
                    if data['trade_date'] == trade_date:
                        all_data_list.append((symbol, trade_date, data))
            
            # 6. 批量保存数据
            if all_data_list:
                try:
                    save_result = self.storage.save_stock_daily_data_batch(
                        all_data_list,
                        batch_size=1000,
                        skip_existence_check=True
                    )
                    result['success_count'] = save_result.get('success_count', 0)
                    result['fail_count'] = save_result.get('fail_count', 0)
                    result['skip_count'] = len(all_data_list) - result['success_count'] - result['fail_count']
                except Exception as e:
                    self.logger.error(f"  ✗ {trade_date}: 批量保存失败 - {str(e)}")
                    result['fail_count'] = len(all_data_list)
            
        except Exception as e:
            self.logger.error(f"  ✗ {trade_date}: 处理失败 - {str(e)}")
            result['fail_count'] = 1
        
        return result
    
    def _process_single_stock(self, symbol: str, missing_dates: List[str], 
                              start_date: str, end_date: str, delay: float,
                              success_lock: threading.Lock, fail_lock: threading.Lock,
                              rate_limit_lock: threading.Lock,
                              stock_name_map: Dict[str, str] = None,
                              valuation_map: Dict[str, Dict] = None) -> Dict:
        """
        处理单只股票的数据获取（多线程工作函数）
        
        Args:
            symbol: 股票代码
            missing_dates: 缺失的日期列表
            start_date: 开始日期
            end_date: 结束日期
            delay: 延迟时间（秒）
            success_lock: 成功计数锁
            fail_lock: 失败计数锁
            rate_limit_lock: 速率限制计数锁
            stock_name_map: 股票名称映射字典（可选，用于批量获取）
            valuation_map: 估值数据映射字典（可选，用于批量获取PE/PB/市值）
        
        Returns:
            处理结果字典
        """
        result = {
            'symbol': symbol,
            'success_count': 0,
            'fail_count': 0,
            'rate_limit': False,
            'error': None,
            'empty_data': False,  # 标记是否返回空数据（需要重试）
            'missing_dates': missing_dates  # 保存缺失日期列表，用于重试
        }
        
        ts_code = self.convert_ts_code(symbol)
        
        # 获取股票名称（优先使用传入的映射，否则单独获取）
        if stock_name_map and symbol in stock_name_map:
            stock_name = stock_name_map[symbol]
        else:
            stock_name = self.get_stock_name(symbol, ts_code)
        
        try:
            # 获取日线数据
            df = self.fetch_stock_data_from_tushare(ts_code, start_date, end_date)
            
            if df is None or df.empty:
                self.logger.warning(f"  ⚠ {symbol}: Tushare返回空数据（将记录用于重试）")
                result['empty_data'] = True  # 标记为返回空数据，需要重试
                with fail_lock:
                    result['fail_count'] = 1
                return result
            
            # 检查必要字段是否存在（数据完整性检查）
            required_fields = ['open', 'close', 'high', 'low', 'trade_date']
            missing_fields = [f for f in required_fields if f not in df.columns]
            if missing_fields:
                self.logger.warning(f"  ⚠ {symbol}: 数据缺少必要字段: {missing_fields}（将记录用于重试）")
                result['empty_data'] = True  # 标记为数据不完整，需要重试
                result['error'] = f"缺少必要字段: {missing_fields}"
                result['error_type'] = 'data_format_error'
                with fail_lock:
                    result['fail_count'] = 1
                return result
            
            # 获取基本面数据（daily_basic接口，需要至少2000积分）
            daily_basic_df = None
            try:
                daily_basic_df = self.fetch_daily_basic_data(ts_code, start_date, end_date)
                if daily_basic_df is not None and not daily_basic_df.empty:
                    # 检查是否有有效数据（只检查换手率，PE/PB/市值由AkShare负责）
                    has_valid_data = False
                    if 'turnover_rate' in daily_basic_df.columns and daily_basic_df['turnover_rate'].notna().any():
                        has_valid_data = True
                    if has_valid_data:
                        self.logger.debug(f"  ✓ {symbol}: 成功获取基本面数据（换手率等，{len(daily_basic_df)}条记录）")
                    else:
                        self.logger.debug(f"  - {symbol}: daily_basic返回数据但无有效字段")
                else:
                    self.logger.debug(f"  - {symbol}: daily_basic返回空数据（可能需要更高权限或数据不存在）")
            except Exception as e:
                self.logger.debug(f"  - {symbol}: 获取基本面数据异常: {str(e)}")
            
            # 转换为存储格式（传入基本面数据、股票名称和估值数据）
            akshare_valuation = valuation_map.get(symbol, {}) if valuation_map else {}
            data_list = self.convert_tushare_to_storage_format(
                df, symbol, name=stock_name, 
                daily_basic_df=daily_basic_df,
                akshare_valuation=akshare_valuation
            )
            
            # 计算量比（需要历史数据，在保存前计算）
            for data in data_list:
                if data['trade_date'] in missing_dates and data.get('volume'):
                    volume_ratio = self.calculate_volume_ratio(symbol, data['trade_date'], data['volume'])
                    data['volume_ratio'] = volume_ratio
            
            # 只保存缺失日期的数据（优化：批量保存）
            saved_count = 0
            batch_data = []
            for data in data_list:
                if data['trade_date'] in missing_dates:
                    batch_data.append((data['trade_date'], data))
            
            # 批量保存（减少数据库操作次数）
            if batch_data:
                try:
                    # 使用批量保存方法（如果可用）
                    if hasattr(self.storage, 'save_stock_daily_data_batch'):
                        batch_save_data = [(symbol, date_str, data_item) for date_str, data_item in batch_data]
                        save_result = self.storage.save_stock_daily_data_batch(
                            batch_save_data, 
                            batch_size=100,  # 每批100条
                            skip_existence_check=False  # 检查是否存在
                        )
                        saved_count = save_result.get('success_count', 0)
                    else:
                        # 回退到逐条保存
                        for date_str, data_item in batch_data:
                            if self.storage.save_stock_daily_data(
                                symbol=symbol,
                                date=date_str,
                                data=data_item,
                                use_full_fields=False  # 历史数据使用41个字段
                            ):
                                saved_count += 1
                except Exception as e:
                    self.logger.warning(f"批量保存失败 {symbol}，回退到逐条保存: {str(e)}")
                    # 记录批量保存失败的原因
                    result['save_error'] = str(e)
                    result['save_error_type'] = 'batch_save_failed'
                    # 回退到逐条保存
                    for date_str, data_item in batch_data:
                        if self.storage.save_stock_daily_data(
                            symbol=symbol,
                            date=date_str,
                            data=data_item,
                            use_full_fields=False
                        ):
                            saved_count += 1
            
            if saved_count > 0:
                with success_lock:
                    result['success_count'] = saved_count
                self.logger.info(f"  ✓ {symbol}: 成功保存 {saved_count} 条数据")
            else:
                self.logger.debug(f"  - {symbol}: 数据已存在或无需保存")
            
            # 延迟，避免API限制（RateLimiter已控制总体速率，这里只需要最小延迟）
            # 对于多线程模式，延迟可以适当减少
            actual_delay = max(delay * 0.5, 0.1)  # 至少0.1秒，多线程模式下减少延迟
            time.sleep(actual_delay)
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 分类错误处理
            # 1. API限流错误
            is_rate_limit = any(keyword in error_str for keyword in [
                'rate limit', '429', 'too many requests', 
                '每分钟最多', '访问该接口', '权限的具体详情',
                '请求过于频繁', '访问频率', '请求次数'
            ])
            
            # 2. 网络错误
            is_network_error = any(keyword in error_str for keyword in [
                'connection', 'timeout', 'network', '网络', '连接',
                'socket', 'dns', 'resolve', 'unreachable'
            ])
            
            # 3. 数据格式错误
            is_data_format_error = any(keyword in error_str for keyword in [
                'json', 'format', 'parse', 'decode', 'invalid',
                '格式', '解析', '解码', '无效'
            ])
            
            # 4. 数据库错误
            is_database_error = any(keyword in error_str for keyword in [
                'database', 'mysql', 'sql', 'db', 'table',
                '数据库', '表', '字段', '约束'
            ])
            
            if is_rate_limit:
                # API限流错误：自动等待后继续（不重试，由RateLimiter处理）
                with rate_limit_lock:
                    result['rate_limit'] = True
                result['error_type'] = 'rate_limit'
                self.logger.error(f"  ✗ {symbol}: API速率限制 - {str(e)}")
                # 速率限制时等待更长时间（至少60秒）
                wait_time = max(delay * 3, 60)
                self.logger.warning(f"  ⚠ 等待 {wait_time} 秒后继续...")
                time.sleep(wait_time)
            elif is_network_error:
                # 网络错误：短暂延迟后继续（不重试，由外层重试机制处理）
                with fail_lock:
                    result['fail_count'] = 1
                result['error_type'] = 'network_error'
                result['error'] = str(e)
                self.logger.error(f"  ✗ {symbol}: 网络错误 - {str(e)}")
                time.sleep(delay * 1.5)  # 网络错误时稍微增加延迟
            elif is_data_format_error:
                # 数据格式错误：记录并跳过
                with fail_lock:
                    result['fail_count'] = 1
                result['error_type'] = 'data_format_error'
                result['error'] = str(e)
                self.logger.error(f"  ✗ {symbol}: 数据格式错误 - {str(e)}")
                time.sleep(delay)
            elif is_database_error:
                # 数据库错误：记录并回退到逐条保存（已在批量保存中处理）
                with fail_lock:
                    result['fail_count'] = 1
                result['error_type'] = 'database_error'
                result['error'] = str(e)
                self.logger.error(f"  ✗ {symbol}: 数据库错误 - {str(e)}")
                time.sleep(delay)
            else:
                # 其他错误：记录并继续
                with fail_lock:
                    result['fail_count'] = 1
                result['error_type'] = 'unknown_error'
                result['error'] = str(e)
                self.logger.error(f"  ✗ {symbol}: 未知错误 - {str(e)}")
                time.sleep(delay)
        
        return result
    
    def fetch_and_save_missing_data(self, start_date: str, end_date: str, 
                                     batch_size: int = 50, delay: float = 2.0,
                                     max_stocks: int = None, max_workers: int = 10,
                                     symbols: Optional[List[str]] = None,
                                     use_date_batch_mode: bool = True) -> Dict:
        """
        获取并保存缺失的数据（优化：支持按日期批量获取）
        
        优化策略：
        - use_date_batch_mode=True（默认）：按日期循环，一次API调用获取所有股票数据
          - 性能提升约2500倍（对于5000只股票，5天数据）
          - API调用次数：从25000次减少到10次
        - use_date_batch_mode=False：按股票循环（兜底方案，兼容旧代码）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            batch_size: 批次大小（已废弃，保留用于兼容）
            delay: 每只股票之间的延迟（秒，仅在非批量模式下使用）
            max_stocks: 最大股票数量（None表示全部，仅在非批量模式下使用）
            max_workers: 最大线程数（默认10，仅在非批量模式下使用）
            symbols: 指定股票列表（None表示处理所有股票）
            use_date_batch_mode: 是否使用按日期批量获取模式（默认True，推荐）
        
        Returns:
            统计结果
        """
        self.logger.info("=" * 80)
        if use_date_batch_mode:
            self.logger.info("从Tushare获取股票数据 - 按日期批量获取模式（优化）")
        else:
            self.logger.info("从Tushare获取股票数据 - 多线程模式（按股票循环）")
        self.logger.info("=" * 80)
        self.logger.info(f"日期范围: {start_date} 至 {end_date}")
        if use_date_batch_mode:
            self.logger.info("模式: 按日期批量获取（一次API调用获取所有股票）")
        else:
            self.logger.info(f"线程数: {max_workers}")
            self.logger.info(f"股票间延迟: {delay} 秒")
            if max_stocks:
                self.logger.info(f"最大股票数量: {max_stocks}")
        self.logger.info("=" * 80)
        
        # 如果使用按日期批量获取模式，使用优化路径
        if use_date_batch_mode:
            return self._fetch_and_save_by_date(start_date, end_date, symbols)
        
        # 否则使用原有的按股票循环方式（兜底方案）
        return self._fetch_and_save_by_stock(start_date, end_date, batch_size, delay, max_stocks, max_workers, symbols)
    
    def _fetch_and_save_by_date(self, start_date: str, end_date: str, 
                                 symbols: Optional[List[str]] = None) -> Dict:
        """
        按日期批量获取数据（优化路径）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 指定股票列表（None表示处理所有股票）
        
        Returns:
            统计结果
        """
        # 1. 查询已有数据
        existing_data = self.get_existing_data(start_date, end_date)
        
        # 2. 获取股票列表（用于名称映射和估值数据）
        if symbols:
            # 如果指定了股票列表，只处理这些股票
            all_symbols = [str(s).zfill(6) for s in symbols]
            self.logger.info(f"使用指定的股票列表: {len(all_symbols)} 只股票")
        else:
            # 从数据库或API获取所有股票列表（优先从数据库获取，避免网络问题）
            all_symbols = self.get_all_stock_list(use_database=True)
            
            if not all_symbols:
                self.logger.error("未能获取到股票列表，脚本终止")
                return {
                    'total_stocks': 0,
                    'need_fetch_stocks': 0,
                    'total_missing_records': 0,
                    'success_count': 0,
                    'fail_count': 0,
                    'skip_count': 0,
                    'error': '未能获取股票列表'
                }
        
        # 3. 生成日期列表
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        date_list = []
        current = start
        while current <= end:
            # 跳过周末（简单判断，实际应该考虑节假日）
            if current.weekday() < 5:  # 0-4是周一到周五
                date_list.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        self.logger.info(f"目标日期列表: {len(date_list)} 个交易日")
        
        # 4. 统计需要获取的日期（过滤出有缺失数据的日期）
        need_fetch_dates = []
        for trade_date in date_list:
            # 检查是否有股票在该日期缺失数据
            has_missing = False
            for symbol in all_symbols:
                existing_dates = existing_data.get(symbol, set())
                if trade_date not in existing_dates:
                    has_missing = True
                    break
            if has_missing:
                need_fetch_dates.append(trade_date)
        
        if not need_fetch_dates:
            self.logger.info("所有数据已存在，无需获取")
            return {
                'total_stocks': len(all_symbols),
                'need_fetch_stocks': 0,
                'total_missing_records': 0,
                'success_count': 0,
                'fail_count': 0,
                'skip_count': len(all_symbols)
            }
        
        self.logger.info(f"\n需要获取数据的日期: {len(need_fetch_dates)} 个交易日")
        
        # 5. 批量获取股票名称映射（优化性能）
        self.logger.info("批量获取股票名称映射...")
        stock_name_map = self._batch_get_stock_names(all_symbols)
        self.logger.info(f"成功获取 {len(stock_name_map)} 只股票的名称")
        
        # 6. 批量获取估值数据（PE/PB/市值）- 从AkShare获取，一次性获取完
        self.logger.info("批量获取估值数据（PE/PB/市值）...")
        valuation_map = self._batch_get_valuation_from_akshare(all_symbols)
        self.logger.info(f"成功获取 {len(valuation_map)} 只股票的估值数据")
        
        # 7. 按日期循环处理（优化：一次API调用获取所有股票）
        self.logger.info(f"\n【按日期批量获取】开始处理 {len(need_fetch_dates)} 个交易日...")
        success_count = 0
        fail_count = 0
        skip_count = 0
        start_time = time.time()
        
        for idx, trade_date in enumerate(need_fetch_dates, 1):
            self.logger.info(f"\n[{idx}/{len(need_fetch_dates)}] 处理日期: {trade_date}")
            result = self._process_single_date(trade_date, existing_data, stock_name_map, valuation_map)
            success_count += result.get('success_count', 0)
            fail_count += result.get('fail_count', 0)
            skip_count += result.get('skip_count', 0)
            
            # 更新已有数据（避免重复查询）
            # 这里简化处理，实际应该根据保存结果更新existing_data
        
        elapsed_time = time.time() - start_time
        self.logger.info("\n" + "=" * 80)
        self.logger.info("【按日期批量获取】处理完成")
        self.logger.info(f"成功: {success_count} 条记录")
        self.logger.info(f"失败: {fail_count} 条记录")
        self.logger.info(f"跳过: {skip_count} 条记录")
        self.logger.info(f"总耗时: {elapsed_time:.1f} 秒")
        self.logger.info("=" * 80)
        
        return {
            'total_stocks': len(all_symbols),
            'need_fetch_stocks': len(all_symbols),
            'total_missing_records': success_count + fail_count + skip_count,
            'success_count': success_count,
            'fail_count': fail_count,
            'skip_count': skip_count,
            'rate_limit_count': 0
        }
    
    def _fetch_and_save_by_stock(self, start_date: str, end_date: str,
                                   batch_size: int = 50, delay: float = 2.0,
                                   max_stocks: int = None, max_workers: int = 10,
                                   symbols: Optional[List[str]] = None) -> Dict:
        """
        按股票循环获取数据（兜底方案，兼容旧代码）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            batch_size: 批次大小（已废弃，保留用于兼容）
            delay: 每只股票之间的延迟（秒）
            max_stocks: 最大股票数量（None表示全部）
            max_workers: 最大线程数（默认10）
            symbols: 指定股票列表（None表示处理所有股票）
        
        Returns:
            统计结果
        """
        # 1. 查询已有数据
        existing_data = self.get_existing_data(start_date, end_date)
        
        # 2. 获取股票列表
        if symbols:
            # 如果指定了股票列表，只处理这些股票
            all_symbols = [str(s).zfill(6) for s in symbols]
            self.logger.info(f"使用指定的股票列表: {len(all_symbols)} 只股票")
        else:
            # 从数据库或API获取所有股票列表（优先从数据库获取，避免网络问题）
            all_symbols = self.get_all_stock_list(use_database=True)
            
            if not all_symbols:
                self.logger.error("未能获取到股票列表，脚本终止")
                return {
                    'total_stocks': 0,
                    'need_fetch_stocks': 0,
                    'total_missing_records': 0,
                    'success_count': 0,
                    'fail_count': 0,
                    'skip_count': 0,
                    'error': '未能获取股票列表'
                }
        
        # 如果指定了max_stocks，限制数量
        if max_stocks:
            all_symbols = all_symbols[:max_stocks]
            self.logger.info(f"限制为前 {max_stocks} 只股票")
        
        # 3. 生成日期列表
        
        # 7. 多线程获取数据（第一轮）
        success_count = 0
        fail_count = 0
        rate_limit_count = 0
        failed_symbols = {}  # 记录返回空数据的股票：{symbol: missing_dates}
        
        # 错误统计（分类统计）
        error_stats = {
            'rate_limit_count': 0,
            'network_error_count': 0,
            'data_format_error_count': 0,
            'database_error_count': 0,
            'unknown_error_count': 0
        }
        
        # 线程安全的锁
        success_lock = threading.Lock()
        fail_lock = threading.Lock()
        rate_limit_lock = threading.Lock()
        failed_lock = threading.Lock()  # 用于记录失败股票的锁
        completed_lock = threading.Lock()
        
        symbols_list = list(need_fetch.keys())
        total_symbols = len(symbols_list)
        completed_count = 0
        start_time = time.time()  # 记录开始时间，用于计算预计剩余时间
        
        # 计算跳过数量（在整个处理过程中是固定的）
        skip_count = len(all_symbols) - len(need_fetch)
        
        self.logger.info(f"\n【第一轮】开始多线程处理 {total_symbols} 只股票（使用 {max_workers} 个线程）...")
        
        # 使用线程池并行处理（第一轮）
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务（传入股票名称映射）
            future_to_symbol = {
                executor.submit(
                    self._process_single_stock,
                    symbol,
                    need_fetch[symbol],
                    start_date,
                    end_date,
                    delay,
                    success_lock,
                    fail_lock,
                    rate_limit_lock,
                    stock_name_map,
                    valuation_map
                ): symbol
                for symbol in symbols_list
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed_count += 1
                
                try:
                    result = future.result()
                    
                    # 更新统计
                    with success_lock:
                        success_count += result.get('success_count', 0)
                    with fail_lock:
                        fail_count += result.get('fail_count', 0)
                    if result.get('rate_limit', False):
                        with rate_limit_lock:
                            rate_limit_count += 1
                            error_stats['rate_limit_count'] += 1
                    
                    # 更新错误统计
                    error_type = result.get('error_type')
                    if error_type:
                        if error_type == 'network_error':
                            error_stats['network_error_count'] += 1
                        elif error_type == 'data_format_error':
                            error_stats['data_format_error_count'] += 1
                        elif error_type == 'database_error':
                            error_stats['database_error_count'] += 1
                        elif error_type == 'unknown_error':
                            error_stats['unknown_error_count'] += 1
                    
                    # 记录返回空数据的股票（用于第二轮重试）
                    if result.get('empty_data', False):
                        missing_dates_for_retry = result.get('missing_dates', need_fetch.get(symbol, []))
                        with failed_lock:
                            failed_symbols[symbol] = missing_dates_for_retry
                    
                    # 根据线程数动态调整进度报告频率（线程数越多，报告频率可以降低）
                    report_interval = 50 if max_workers < 20 else 100 if max_workers < 30 else 150
                    if completed_count % report_interval == 0 or completed_count == total_symbols:
                        progress_pct = (completed_count * 100) // total_symbols if total_symbols > 0 else 0
                        elapsed_time = time.time() - start_time
                        avg_time_per_stock = elapsed_time / completed_count if completed_count > 0 else 0
                        remaining_stocks = total_symbols - completed_count
                        estimated_remaining_time = avg_time_per_stock * remaining_stocks
                        
                        # skip_count 已在循环外部定义，直接使用
                        self.logger.info(
                            f"进度: {completed_count}/{total_symbols} ({progress_pct}%) | "
                            f"成功: {success_count} 条记录 | 失败: {fail_count} 只股票 | "
                            f"跳过: {skip_count} 只 | 速率限制: {rate_limit_count} 次 | "
                            f"待重试: {len(failed_symbols)} 只 | "
                            f"已用时间: {elapsed_time:.1f}秒 | "
                            f"预计剩余: {estimated_remaining_time:.1f}秒"
                        )
                    
                except Exception as e:
                    with fail_lock:
                        fail_count += 1
                    self.logger.error(f"  ✗ {symbol}: 处理异常 - {str(e)}")
                    # 异常情况也记录到失败列表，尝试重试
                    with failed_lock:
                        if symbol not in failed_symbols:
                            failed_symbols[symbol] = need_fetch.get(symbol, [])
        
        # 8. 第二轮重试：对返回空数据的股票进行重试
        retry_success_count = 0
        retry_fail_count = 0
        final_failed_symbols = []  # 记录最终仍失败的股票
        
        if failed_symbols:
            self.logger.info(f"\n【第二轮重试】开始重试 {len(failed_symbols)} 只返回空数据的股票...")
            self.logger.info(f"待重试股票列表: {', '.join(list(failed_symbols.keys())[:20])}" + 
                           (f" 等共{len(failed_symbols)}只" if len(failed_symbols) > 20 else ""))
            
            # 重新获取这些股票的估值数据（可能之前没有获取到）
            retry_symbols_list = list(failed_symbols.keys())
            self.logger.info("重新获取待重试股票的估值数据...")
            retry_valuation_map = self._batch_get_valuation_from_akshare(retry_symbols_list)
            self.logger.info(f"成功获取 {len(retry_valuation_map)} 只股票的估值数据")
            
            # 使用线程池并行处理（第二轮重试）
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交重试任务
                retry_future_to_symbol = {
                    executor.submit(
                        self._process_single_stock,
                        symbol,
                        failed_symbols[symbol],
                        start_date,
                        end_date,
                        delay * 1.5,  # 重试时增加延迟，避免再次失败
                        success_lock,
                        fail_lock,
                        rate_limit_lock,
                        stock_name_map,
                        retry_valuation_map if retry_valuation_map else valuation_map
                    ): symbol
                    for symbol in retry_symbols_list
                }
                
                retry_completed_count = 0
                retry_total = len(retry_symbols_list)
                
                # 处理完成的重试任务
                for future in as_completed(retry_future_to_symbol):
                    symbol = retry_future_to_symbol[future]
                    retry_completed_count += 1
                    
                    try:
                        result = future.result()
                        
                        # 更新重试统计
                        retry_success = result.get('success_count', 0)
                        retry_fail = result.get('fail_count', 0)
                        
                        if retry_success > 0:
                            retry_success_count += retry_success
                            self.logger.info(f"  ✓ [重试] {symbol}: 成功获取 {retry_success} 条数据")
                        else:
                            retry_fail_count += retry_fail
                            final_failed_symbols.append(symbol)  # 记录最终仍失败的股票
                            if result.get('empty_data', False):
                                self.logger.warning(f"  ⚠ [重试] {symbol}: 仍然返回空数据，可能该日期无交易数据")
                            else:
                                self.logger.warning(f"  ⚠ [重试] {symbol}: 重试失败")
                        
                        # 报告重试进度
                        if retry_completed_count % 20 == 0 or retry_completed_count == retry_total:
                            retry_progress_pct = (retry_completed_count * 100) // retry_total
                            self.logger.info(f"[重试] 进度: {retry_completed_count}/{retry_total} ({retry_progress_pct}%) - "
                                           f"成功: {retry_success_count} 条记录, 失败: {retry_fail_count} 只股票")
                    
                    except Exception as e:
                        retry_fail_count += 1
                        final_failed_symbols.append(symbol)  # 记录异常失败的股票
                        self.logger.error(f"  ✗ [重试] {symbol}: 处理异常 - {str(e)}")
            
            # 更新总统计
            success_count += retry_success_count
            # 注意：fail_count 保持第一轮的失败计数，重试的结果单独记录
            # 因为重试成功的股票已经从失败中恢复，但重试后仍失败的股票仍然算失败
            
            self.logger.info(f"\n【第二轮重试完成】")
            self.logger.info(f"重试股票数: {len(failed_symbols)} 只")
            self.logger.info(f"重试成功: {retry_success_count} 条记录")
            self.logger.info(f"重试后仍失败: {retry_fail_count} 只股票")
            
            # 记录最终仍失败的股票列表（用于后续分析）
            if final_failed_symbols:
                if len(final_failed_symbols) <= 20:
                    self.logger.warning(f"最终仍失败的股票: {', '.join(final_failed_symbols)}")
                else:
                    self.logger.warning(f"最终仍失败的股票: {', '.join(final_failed_symbols[:20])} 等共{len(final_failed_symbols)}只")
                
                # 保存失败股票列表到文件（可选，用于后续分析）
                try:
                    failed_file = os.path.join(project_root, 'data', f'failed_stocks_{start_date.replace("-", "")}_{end_date.replace("-", "")}.txt')
                    os.makedirs(os.path.dirname(failed_file), exist_ok=True)
                    with open(failed_file, 'w', encoding='utf-8') as f:
                        f.write(f"# 数据获取失败的股票列表\n")
                        f.write(f"# 日期范围: {start_date} 至 {end_date}\n")
                        f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"# 失败股票数: {len(final_failed_symbols)}\n\n")
                        for symbol in final_failed_symbols:
                            f.write(f"{symbol}\n")
                    self.logger.info(f"失败股票列表已保存到: {failed_file}")
                except Exception as e:
                    self.logger.debug(f"保存失败股票列表失败: {str(e)}")
        else:
            self.logger.info("\n【无需重试】所有股票在第一轮都成功获取到数据")
        
        # 错误统计报告
        if any(error_stats.values()):
            self.logger.info(f"\n【错误统计】")
            if error_stats['rate_limit_count'] > 0:
                self.logger.warning(f"  API速率限制: {error_stats['rate_limit_count']} 次")
            if error_stats['network_error_count'] > 0:
                self.logger.warning(f"  网络错误: {error_stats['network_error_count']} 次")
            if error_stats['data_format_error_count'] > 0:
                self.logger.warning(f"  数据格式错误: {error_stats['data_format_error_count']} 次")
            if error_stats['database_error_count'] > 0:
                self.logger.warning(f"  数据库错误: {error_stats['database_error_count']} 次")
            if error_stats['unknown_error_count'] > 0:
                self.logger.warning(f"  未知错误: {error_stats['unknown_error_count']} 次")
        
        # 如果触发速率限制，给出建议
        if rate_limit_count > 0:
            self.logger.warning(f"\n⚠ 共触发 {rate_limit_count} 次速率限制")
            if rate_limit_count >= total_symbols * 0.1:  # 如果超过10%的股票触发限制
                self.logger.warning(f"⚠ 速率限制较频繁，建议：")
                self.logger.warning(f"   1. 增加延迟时间（当前: {delay}秒，建议: {delay * 2}秒）")
                self.logger.warning(f"   2. 减少线程数（当前: {max_workers}，建议: {max_workers // 2}）")
        
        # 9. 统计结果
        result = {
            'total_stocks': len(all_symbols),
            'need_fetch_stocks': len(need_fetch),
            'total_missing_records': total_missing,
            'success_count': success_count,
            'fail_count': fail_count,
            'rate_limit_count': rate_limit_count,
            'skip_count': len(all_symbols) - len(need_fetch),
            'retry_count': len(failed_symbols) if 'failed_symbols' in locals() else 0,  # 重试的股票数
            'retry_success_count': retry_success_count if 'retry_success_count' in locals() else 0,  # 重试成功的记录数
            'retry_fail_count': retry_fail_count if 'retry_fail_count' in locals() else 0,  # 重试后仍失败的股票数
            'final_failed_symbols': final_failed_symbols if 'final_failed_symbols' in locals() else [],  # 最终仍失败的股票列表
            'error_stats': error_stats,  # 错误统计
            'total_duration_seconds': time.time() - start_time  # 总耗时
        }
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("数据获取完成")
        self.logger.info("=" * 80)
        self.logger.info(f"总股票数: {result['total_stocks']}")
        self.logger.info(f"需要获取: {result['need_fetch_stocks']} 只股票，{result['total_missing_records']} 条记录")
        self.logger.info(f"成功获取: {result['success_count']} 条记录")
        self.logger.info(f"失败: {result['fail_count']} 只股票")
        self.logger.info(f"速率限制: {result['rate_limit_count']} 次")
        self.logger.info(f"跳过（数据已存在）: {result['skip_count']} 只股票")
        if result.get('retry_count', 0) > 0:
            self.logger.info(f"重试股票数: {result['retry_count']} 只")
            self.logger.info(f"重试成功: {result.get('retry_success_count', 0)} 条记录")
            self.logger.info(f"重试后仍失败: {result.get('retry_fail_count', 0)} 只股票")
        self.logger.info("=" * 80)
        
        return result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从Tushare获取股票数据（2026-01-16 至 2026-01-23）')
    parser.add_argument('--start-date', type=str, default='2026-01-16',
                       help='开始日期（格式：YYYY-MM-DD，默认2026-01-16）')
    parser.add_argument('--end-date', type=str, default='2026-01-23',
                       help='结束日期（格式：YYYY-MM-DD，默认2026-01-23）')
    parser.add_argument('--batch-size', type=int, default=30,
                       help='批次大小（默认30只股票/批次）')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='股票间延迟（秒，默认2.0秒）')
    parser.add_argument('--max-stocks', type=int, default=None,
                       help='最大股票数量（默认：全部）')
    parser.add_argument('--max-workers', type=int, default=10,
                       help='最大线程数（默认10）')
    
    args = parser.parse_args()
    
    try:
        fetcher = TushareDataFetcher()
        result = fetcher.fetch_and_save_missing_data(
            start_date=args.start_date,
            end_date=args.end_date,
            batch_size=args.batch_size,
            delay=args.delay,
            max_stocks=args.max_stocks,
            max_workers=args.max_workers
        )
        
        logger.info("\n脚本执行完成！")
        return result
        
    except Exception as e:
        logger.error(f"脚本执行失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
