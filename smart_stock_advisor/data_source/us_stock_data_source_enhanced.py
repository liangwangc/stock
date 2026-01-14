"""
增强版美股数据源模块
支持多个数据源：akshare、yfinance、Alpha Vantage、Polygon.io、Finnhub
自动切换和重试机制
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import time
import requests

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入各种数据源
YFINANCE_AVAILABLE = False
AKSHARE_AVAILABLE = False
ALPHA_VANTAGE_AVAILABLE = False
POLYGON_AVAILABLE = False
FINNHUB_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    logger.debug("yfinance未安装")

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    logger.debug("akshare未安装")

# Alpha Vantage 不需要特殊库，使用 requests
ALPHA_VANTAGE_AVAILABLE = True

# Polygon.io 不需要特殊库，使用 requests
POLYGON_AVAILABLE = True

# Finnhub 不需要特殊库，使用 requests
FINNHUB_AVAILABLE = True


class EnhancedUSStockDataSource:
    """增强版美股数据源，支持多个备用接口"""
    
    def __init__(self, alpha_vantage_api_key: str = None, 
                 polygon_api_key: str = None,
                 finnhub_api_key: str = None):
        """
        初始化数据源
        
        Args:
            alpha_vantage_api_key: Alpha Vantage API密钥（免费注册：https://www.alphavantage.co/support/#api-key）
            polygon_api_key: Polygon.io API密钥（免费注册：https://polygon.io/）
            finnhub_api_key: Finnhub API密钥（免费注册：https://finnhub.io/）
        """
        self.logger = logger
        self.yfinance_available = YFINANCE_AVAILABLE
        self.akshare_available = AKSHARE_AVAILABLE
        self.alpha_vantage_available = ALPHA_VANTAGE_AVAILABLE
        self.polygon_available = POLYGON_AVAILABLE
        self.finnhub_available = FINNHUB_AVAILABLE
        
        # API密钥
        self.alpha_vantage_api_key = alpha_vantage_api_key or os.getenv('ALPHA_VANTAGE_API_KEY')
        self.polygon_api_key = polygon_api_key or os.getenv('POLYGON_API_KEY')
        self.finnhub_api_key = finnhub_api_key or os.getenv('FINNHUB_API_KEY')
        
        # 数据源优先级列表（按顺序尝试）
        self.data_sources = []
        
        if self.akshare_available:
            self.data_sources.append('akshare')
        if self.yfinance_available:
            self.data_sources.append('yfinance')
        if self.alpha_vantage_available and self.alpha_vantage_api_key:
            self.data_sources.append('alpha_vantage')
        if self.polygon_available and self.polygon_api_key:
            self.data_sources.append('polygon')
        if self.finnhub_available and self.finnhub_api_key:
            self.data_sources.append('finnhub')
        
        self.logger.info(f"可用数据源: {', '.join(self.data_sources)}")
    
    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None, 
                      period: str = "10y") -> pd.DataFrame:
        """
        获取美股历史数据（自动尝试多个数据源）
        
        Args:
            symbol: 股票代码（如：AAPL）
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）
            period: 时间周期（如果未提供日期）
        
        Returns:
            DataFrame with columns: date, open, high, low, close, adj_close, volume
        """
        # 计算日期范围
        if not start_date or not end_date:
            end_date_obj = datetime.now().date()
            if period == "10y":
                start_date_obj = end_date_obj - timedelta(days=365 * 10)
            elif period == "5y":
                start_date_obj = end_date_obj - timedelta(days=365 * 5)
            elif period == "1y":
                start_date_obj = end_date_obj - timedelta(days=365)
            else:
                start_date_obj = end_date_obj - timedelta(days=365 * 10)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        # 按优先级尝试各个数据源
        for source in self.data_sources:
            try:
                self.logger.info(f"尝试使用 {source} 获取 {symbol} 数据...")
                
                if source == 'akshare':
                    df = self._get_data_from_akshare(symbol, start_date, end_date)
                elif source == 'yfinance':
                    df = self._get_data_from_yfinance(symbol, start_date, end_date, period)
                elif source == 'alpha_vantage':
                    df = self._get_data_from_alpha_vantage(symbol, start_date, end_date)
                elif source == 'polygon':
                    df = self._get_data_from_polygon(symbol, start_date, end_date)
                elif source == 'finnhub':
                    df = self._get_data_from_finnhub(symbol, start_date, end_date)
                else:
                    continue
                
                if df is not None and not df.empty:
                    self.logger.info(f"成功使用 {source} 获取 {symbol} 数据，共 {len(df)} 条记录")
                    return df
                else:
                    self.logger.warning(f"{source} 返回空数据，尝试下一个数据源...")
                    
            except Exception as e:
                error_str = str(e)
                is_rate_limit = (
                    'Rate limited' in error_str or 
                    'Too Many Requests' in error_str or
                    '429' in error_str or
                    'rate limit' in error_str.lower() or
                    'YFRateLimitError' in error_str
                )
                
                if is_rate_limit:
                    self.logger.warning(f"{source} 遇到速率限制: {error_str}，尝试下一个数据源...")
                else:
                    self.logger.warning(f"{source} 获取数据失败: {error_str}，尝试下一个数据源...")
                continue
        
        self.logger.error(f"所有数据源均失败，无法获取 {symbol} 数据")
        return pd.DataFrame()
    
    def _get_data_from_akshare(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从akshare获取数据"""
        if not self.akshare_available:
            return None
        
        try:
            start_date_str = start_date.replace('-', '')
            end_date_str = end_date.replace('-', '')
            
            df = ak.stock_us_hist(symbol=symbol, period="daily", 
                                 start_date=start_date_str, 
                                 end_date=end_date_str, 
                                 adjust="qfq")
            
            if df.empty:
                return None
            
            # 标准化列名
            column_mapping = {
                '日期': 'date', 'Date': 'date',
                '开盘': 'open', 'Open': 'open',
                '收盘': 'close', 'Close': 'close',
                '最高': 'high', 'High': 'high',
                '最低': 'low', 'Low': 'low',
                '成交量': 'volume', 'Volume': 'volume',
            }
            
            df.columns = [col.strip() for col in df.columns]
            rename_dict = {old: new for old, new in column_mapping.items() if old in df.columns}
            df = df.rename(columns=rename_dict)
            
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            
            if 'adj_close' not in df.columns and 'close' in df.columns:
                df['adj_close'] = df['close']
            
            return df
            
        except Exception as e:
            raise Exception(f"akshare错误: {str(e)}")
    
    def _get_data_from_yfinance(self, symbol: str, start_date: str, end_date: str, period: str) -> Optional[pd.DataFrame]:
        """从yfinance获取数据（带重试）"""
        if not self.yfinance_available:
            return None
        
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = retry_delay * (2 ** (attempt - 1))
                    self.logger.debug(f"yfinance重试 {attempt}/{max_retries}，等待 {wait_time:.1f}秒...")
                    time.sleep(wait_time)
                
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date) if start_date and end_date else ticker.history(period=period)
                
                if df.empty:
                    return None
                
                df.reset_index(inplace=True)
                df.columns = [col.strip() for col in df.columns]
                
                column_mapping = {
                    'Date': 'date', 'Open': 'open', 'High': 'high',
                    'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close',
                    'Volume': 'volume'
                }
                
                rename_dict = {old: new for old, new in column_mapping.items() if old in df.columns}
                df = df.rename(columns=rename_dict)
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                
                return df
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"yfinance错误: {str(e)}")
                continue
        
        return None
    
    def _get_data_from_alpha_vantage(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从Alpha Vantage获取数据（免费API，每分钟5次请求）"""
        if not self.alpha_vantage_api_key:
            return None
        
        try:
            # Alpha Vantage 免费版限制：每分钟5次请求，每天500次
            # 注意：TIME_SERIES_DAILY_ADJUSTED是付费端点，使用TIME_SERIES_DAILY（免费）
            # 注意：outputsize=full是付费功能，免费版只能使用compact（最近100条）
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_DAILY',  # 使用免费端点
                'symbol': symbol,
                'apikey': self.alpha_vantage_api_key,
                'outputsize': 'compact'  # 免费版只能使用compact（最近100条数据）
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 检查错误信息
            if 'Error Message' in data:
                error_msg = data.get('Error Message', '')
                raise Exception(f"Alpha Vantage错误: {error_msg}")
            
            if 'Note' in data:
                note_msg = data.get('Note', '')
                # 如果是速率限制提示，等待后重试
                if 'premium' in note_msg.lower() or 'subscription' in note_msg.lower():
                    self.logger.warning(f"Alpha Vantage提示: {note_msg}")
                    raise Exception(f"Alpha Vantage提示: {note_msg}")
                else:
                    self.logger.warning(f"Alpha Vantage提示: {note_msg}")
                    raise Exception(f"Alpha Vantage提示: {note_msg}")
            
            if 'Information' in data:
                info_msg = data.get('Information', '')
                if 'premium' in info_msg.lower():
                    self.logger.warning(f"Alpha Vantage信息: {info_msg}")
                    raise Exception(f"Alpha Vantage信息: {info_msg}")
            
            if 'Time Series (Daily)' not in data:
                self.logger.warning(f"Alpha Vantage返回数据中没有'Time Series (Daily)'字段")
                self.logger.warning(f"Alpha Vantage响应键: {list(data.keys())}")
                # 打印前几个键的值以便调试
                for key in list(data.keys())[:3]:
                    self.logger.debug(f"  {key}: {str(data[key])[:200]}")
                return None
            
            time_series = data['Time Series (Daily)']
            if not time_series:
                self.logger.warning(f"Alpha Vantage返回的时间序列为空")
                return None
            
            records = []
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            
            for date_str, values in time_series.items():
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    date_obj_date = date_obj.date()
                    
                    # 日期过滤
                    if start_date_obj and date_obj_date < start_date_obj:
                        continue
                    if end_date_obj and date_obj_date > end_date_obj:
                        continue
                    
                    # TIME_SERIES_DAILY返回的字段名（免费端点）
                    records.append({
                        'date': date_obj,
                        'open': float(values['1. open']),
                        'high': float(values['2. high']),
                        'low': float(values['3. low']),
                        'close': float(values['4. close']),
                        'adj_close': float(values['4. close']),  # 免费端点没有调整后价格，使用收盘价
                        'volume': int(values['5. volume'])
                    })
                except Exception as e:
                    self.logger.warning(f"解析日期 {date_str} 失败: {str(e)}")
                    continue
            
            if not records:
                self.logger.warning(f"Alpha Vantage过滤后没有符合日期范围的数据（日期范围: {start_date} 到 {end_date}）")
                # 如果过滤后没有数据，返回所有数据（不进行日期过滤）
                if start_date_obj or end_date_obj:
                    self.logger.info(f"尝试返回所有数据（不进行日期过滤）")
                    records = []
                    for date_str, values in time_series.items():
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                            records.append({
                                'date': date_obj,
                                'open': float(values['1. open']),
                                'high': float(values['2. high']),
                                'low': float(values['3. low']),
                                'close': float(values['4. close']),
                                'adj_close': float(values['4. close']),
                                'volume': int(values['5. volume'])
                            })
                        except Exception as e:
                            self.logger.warning(f"解析日期 {date_str} 失败: {str(e)}")
                            continue
                
                if not records:
                    return None
            
            df = pd.DataFrame(records)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # 避免速率限制
            time.sleep(12)  # 免费版限制：每分钟5次，所以每次请求后等待12秒
            
            return df
            
        except Exception as e:
            raise Exception(f"Alpha Vantage错误: {str(e)}")
    
    def _get_data_from_polygon(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从Polygon.io获取数据（免费版：每分钟5次请求）"""
        if not self.polygon_api_key:
            return None
        
        try:
            # Polygon.io 免费版限制：每分钟5次请求
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
            params = {
                'adjusted': 'true',
                'sort': 'asc',
                'limit': 50000,
                'apiKey': self.polygon_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'OK' or 'results' not in data:
                error_msg = data.get('error', '未知错误')
                raise Exception(f"Polygon错误: {error_msg}")
            
            results = data['results']
            if not results:
                return None
            
            records = []
            for item in results:
                timestamp_ms = item['t']
                date_obj = datetime.fromtimestamp(timestamp_ms / 1000)
                
                records.append({
                    'date': date_obj,
                    'open': float(item['o']),
                    'high': float(item['h']),
                    'low': float(item['l']),
                    'close': float(item['c']),
                    'adj_close': float(item.get('c', item['c'])),  # Polygon返回的价格已经是调整后的
                    'volume': int(item['v'])
                })
            
            df = pd.DataFrame(records)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # 避免速率限制
            time.sleep(12)  # 免费版限制：每分钟5次
            
            return df
            
        except Exception as e:
            raise Exception(f"Polygon错误: {str(e)}")
    
    def _get_data_from_finnhub(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从Finnhub获取数据（免费版：每分钟60次请求）"""
        if not self.finnhub_api_key:
            return None
        
        try:
            # Finnhub 免费版限制：每分钟60次请求
            # 注意：Finnhub的免费版可能不提供完整的历史数据，主要用于实时数据
            url = "https://finnhub.io/api/v1/stock/candle"
            
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())
            
            params = {
                'symbol': symbol,
                'resolution': 'D',  # 日线
                'from': start_timestamp,
                'to': end_timestamp,
                'token': self.finnhub_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('s') != 'ok':
                error_msg = data.get('error', '未知错误')
                raise Exception(f"Finnhub错误: {error_msg}")
            
            if 'c' not in data or not data['c']:
                return None
            
            # Finnhub返回的数据格式：{'c': [close], 'h': [high], 'l': [low], 'o': [open], 's': 'ok', 't': [timestamp], 'v': [volume]}
            timestamps = data['t']
            opens = data['o']
            highs = data['h']
            lows = data['l']
            closes = data['c']
            volumes = data['v']
            
            records = []
            for i in range(len(timestamps)):
                date_obj = datetime.fromtimestamp(timestamps[i])
                records.append({
                    'date': date_obj,
                    'open': float(opens[i]),
                    'high': float(highs[i]),
                    'low': float(lows[i]),
                    'close': float(closes[i]),
                    'adj_close': float(closes[i]),  # Finnhub可能不提供调整后价格
                    'volume': int(volumes[i])
                })
            
            df = pd.DataFrame(records)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # 避免速率限制
            time.sleep(1)  # 免费版限制：每分钟60次，所以每次请求后等待1秒
            
            return df
            
        except Exception as e:
            raise Exception(f"Finnhub错误: {str(e)}")
