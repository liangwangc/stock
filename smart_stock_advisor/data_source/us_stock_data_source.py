"""
美股数据源模块
用于获取美股股票、板块、行业数据
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance未安装，部分功能将不可用。请执行: pip install yfinance")

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("akshare未安装，部分功能将不可用。请执行: pip install akshare")


class USStockDataSource:
    """美股数据源"""
    
    def __init__(self):
        self.logger = logger
        self.yfinance_available = YFINANCE_AVAILABLE
        self.akshare_available = AKSHARE_AVAILABLE
        
        # GICS板块映射（标准11个板块）
        self.gics_sectors = {
            '10': {'name_en': 'Energy', 'name_cn': '能源'},
            '15': {'name_en': 'Materials', 'name_cn': '材料'},
            '20': {'name_en': 'Industrials', 'name_cn': '工业'},
            '25': {'name_en': 'Consumer Discretionary', 'name_cn': '可选消费'},
            '30': {'name_en': 'Consumer Staples', 'name_cn': '必需消费'},
            '35': {'name_en': 'Health Care', 'name_cn': '医疗保健'},
            '40': {'name_en': 'Financials', 'name_cn': '金融'},
            '45': {'name_en': 'Information Technology', 'name_cn': '信息技术'},
            '50': {'name_en': 'Communication Services', 'name_cn': '通信服务'},
            '55': {'name_en': 'Utilities', 'name_cn': '公用事业'},
            '60': {'name_en': 'Real Estate', 'name_cn': '房地产'}
        }
        
        # 板块ETF映射（SPDR Sector ETFs）
        self.sector_etf_map = {
            'Energy': 'XLE',
            'Materials': 'XLB',
            'Industrials': 'XLI',
            'Consumer Discretionary': 'XLY',
            'Consumer Staples': 'XLP',
            'Health Care': 'XLV',
            'Financials': 'XLF',
            'Information Technology': 'XLK',
            'Communication Services': 'XLC',
            'Utilities': 'XLU',
            'Real Estate': 'XLRE'
        }
        
        # Sector名称到GICS代码的映射（yfinance返回的名称 -> GICS代码）
        self.sector_name_to_code = {
            'Energy': '10',
            'Materials': '15',
            'Industrials': '20',
            'Consumer Cyclical': '25',  # Consumer Discretionary
            'Consumer Defensive': '30',  # Consumer Staples
            'Healthcare': '35',  # Health Care
            'Financial Services': '40',  # Financials
            'Technology': '45',  # Information Technology
            'Communication Services': '50',
            'Utilities': '55',
            'Real Estate': '60',
            # yfinance可能使用的其他名称变体
            'Consumer Discretionary': '25',
            'Consumer Staples': '30',
            'Health Care': '35',
            'Financials': '40',
            'Information Technology': '45'
        }
    
    def _map_sector_name_to_code(self, sector_name: str) -> Optional[str]:
        """
        将sector名称映射到GICS代码
        
        Args:
            sector_name: sector名称（如：'Technology', 'Information Technology'）
        
        Returns:
            GICS sector代码（如：'45'），如果找不到则返回None
        """
        if not sector_name:
            return None
        
        # 精确匹配
        if sector_name in self.sector_name_to_code:
            return self.sector_name_to_code[sector_name]
        
        # 模糊匹配（不区分大小写）
        sector_name_lower = sector_name.lower()
        for name, code in self.sector_name_to_code.items():
            if name.lower() == sector_name_lower:
                return code
        
        # 如果找不到，尝试从GICS sectors中查找
        for code, info in self.gics_sectors.items():
            if info['name_en'].lower() == sector_name_lower:
                return code
        
        self.logger.warning(f"无法映射sector名称到代码: {sector_name}")
        return None
    
    def _generate_industry_code(self, industry_name: str, sector_code: Optional[str] = None) -> Optional[str]:
        """
        生成或查找industry代码
        
        Args:
            industry_name: 行业名称
            sector_code: 所属板块代码
        
        Returns:
            行业代码（如果找不到则返回None，后续可以基于名称生成临时代码）
        """
        # 这个方法可以根据industry_name和sector_code生成或查找industry_code
        # 由于完整的GICS industry代码非常复杂，这里先返回None
        # 后续可以通过数据库查询或API获取完整的GICS分类
        
        # 如果提供了sector_code，可以生成一个临时代码：sector_code + 序号
        # 但这需要从数据库查询或建立完整的映射表
        
        # 暂时返回None，后续在存储层处理
        return None
    
    def map_sector_to_gics_code(self, sector_name: str) -> Optional[str]:
        """
        将sector名称映射到GICS代码（公开方法）
        
        Args:
            sector_name: sector名称
        
        Returns:
            GICS sector代码
        """
        return self._map_sector_name_to_code(sector_name)
    
    def get_stock_list(self, exchange: str = 'all') -> pd.DataFrame:
        """
        获取美股股票列表
        
        Args:
            exchange: 交易所（'NASDAQ'/'NYSE'/'AMEX'/'all'）
        
        Returns:
            DataFrame with columns: symbol, name, exchange, sector, industry
        """
        if not self.yfinance_available:
            self.logger.error("yfinance未安装，无法获取股票列表")
            return pd.DataFrame()
        
        try:
            self.logger.info(f"正在获取美股股票列表（交易所: {exchange}）...")
            
            # 使用yfinance获取股票列表（需要从其他来源，yfinance本身不提供股票列表）
            # 这里我们使用一个常见的股票列表API或从文件读取
            
            # 方法1: 使用ticker信息（需要预先知道股票代码）
            # 方法2: 从S&P 500、NASDAQ 100等指数获取成分股
            # 方法3: 使用akshare（如果有相关接口）
            
            # 暂时返回空DataFrame，后续可以从其他数据源获取
            self.logger.warning("股票列表获取功能待实现，请使用已知股票代码或从其他数据源获取")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"获取美股股票列表失败: {str(e)}")
            return pd.DataFrame()
    
    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None, 
                      period: str = "10y") -> pd.DataFrame:
        """
        获取美股历史数据（优先使用akshare，yfinance作为备用）
        
        Args:
            symbol: 股票代码（如：AAPL）
            start_date: 开始日期（格式：YYYY-MM-DD），如果为None，则使用period
            end_date: 结束日期（格式：YYYY-MM-DD），默认为今天
            period: 时间周期（1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max）
        
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
        
        # 方法1: 优先尝试使用akshare
        if self.akshare_available:
            try:
                self.logger.info(f"使用akshare获取 {symbol} 的历史数据...")
                
                # akshare需要YYYYMMDD格式的日期
                start_date_str = start_date.replace('-', '')
                end_date_str = end_date.replace('-', '')
                
                # 添加重试机制
                max_akshare_retries = 2
                for ak_attempt in range(max_akshare_retries):
                    try:
                        if ak_attempt > 0:
                            time.sleep(2)  # 重试前等待2秒
                        
                        df = ak.stock_us_hist(symbol=symbol, period="daily", 
                                             start_date=start_date_str, 
                                             end_date=end_date_str, 
                                             adjust="qfq")
                        
                        if df is None or df.empty:
                            if ak_attempt < max_akshare_retries - 1:
                                self.logger.debug(f"akshare返回空数据，重试 {ak_attempt + 1}/{max_akshare_retries}...")
                                continue
                            else:
                                raise Exception("akshare返回空数据")
                        
                        # 标准化列名（akshare的美股数据列名可能是中文）
                        df.columns = [col.strip() for col in df.columns]
                        
                        # 映射列名
                        column_mapping = {
                            '日期': 'date',
                            '开盘': 'open',
                            '收盘': 'close',
                            '最高': 'high',
                            '最低': 'low',
                            '成交量': 'volume',
                            '成交额': 'amount',
                            # 英文列名（备用）
                            'Date': 'date',
                            'Open': 'open',
                            'Close': 'close',
                            'High': 'high',
                            'Low': 'low',
                            'Volume': 'volume'
                        }
                        
                        rename_dict = {}
                        for old_col, new_col in column_mapping.items():
                            if old_col in df.columns:
                                rename_dict[old_col] = new_col
                        
                        df = df.rename(columns=rename_dict)
                        
                        # 确保日期列为datetime类型
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            df.set_index('date', inplace=True)
                        
                        # 如果没有adj_close列，使用close作为adj_close
                        if 'adj_close' not in df.columns and 'close' in df.columns:
                            df['adj_close'] = df['close']
                        
                        self.logger.info(f"成功使用akshare获取 {symbol} 数据，共 {len(df)} 条记录")
                        return df
                        
                    except Exception as ak_e:
                        if ak_attempt < max_akshare_retries - 1:
                            self.logger.debug(f"akshare尝试 {ak_attempt + 1} 失败: {str(ak_e)}，重试...")
                            continue
                        else:
                            raise ak_e
                    
            except Exception as e:
                error_str = str(e)
                # 检查是否是接口限制错误
                if '限制' in error_str or 'limit' in error_str.lower() or '429' in error_str:
                    self.logger.warning(f"akshare接口限制，尝试使用yfinance: {error_str}")
                else:
                    self.logger.warning(f"akshare获取 {symbol} 数据失败，尝试使用yfinance: {error_str}")
        
        # 方法2: 使用yfinance作为备用（带重试机制和更长的延迟）
        if self.yfinance_available:
            max_retries = 5  # 增加重试次数
            retry_delay = 5.0  # 增加初始重试延迟（秒）
            
            # 每次请求前添加基础延迟，避免过快请求
            time.sleep(1.0)  # 基础延迟1秒
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        # 重试前等待，使用指数退避策略（对于速率限制错误使用更长的等待时间）
                        wait_time = retry_delay * (2 ** (attempt - 1))  # 5秒、10秒、20秒、40秒、80秒
                        self.logger.info(f"等待 {wait_time:.1f} 秒后重试获取 {symbol} 数据（第 {attempt + 1}/{max_retries} 次）...")
                        time.sleep(wait_time)
                    else:
                        self.logger.info(f"使用yfinance获取 {symbol} 的历史数据...")
                    
                    ticker = yf.Ticker(symbol)
                    
                    if start_date and end_date:
                        df = ticker.history(start=start_date, end=end_date)
                    else:
                        df = ticker.history(period=period)
                    
                    if df.empty:
                        self.logger.warning(f"未获取到 {symbol} 的数据")
                        return pd.DataFrame()
                    
                    # 重置索引，将Date转为列
                    df.reset_index(inplace=True)
                    df.columns = [col.strip() for col in df.columns]
                    
                    # 标准化列名
                    column_mapping = {
                        'Date': 'date',
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Adj Close': 'adj_close',
                        'Volume': 'volume',
                        'Dividends': 'dividends',
                        'Stock Splits': 'stock_splits'
                    }
                    
                    rename_dict = {}
                    for old_col, new_col in column_mapping.items():
                        if old_col in df.columns:
                            rename_dict[old_col] = new_col
                    
                    df = df.rename(columns=rename_dict)
                    
                    # 确保日期列为datetime类型
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                    
                    self.logger.info(f"成功使用yfinance获取 {symbol} 数据，共 {len(df)} 条记录")
                    return df
                    
                except Exception as e:
                    error_str = str(e)
                    error_type = type(e).__name__
                    
                    # 检查是否是速率限制错误
                    is_rate_limit = (
                        'Rate limited' in error_str or 
                        'Too Many Requests' in error_str or
                        '429' in error_str or
                        'rate limit' in error_str.lower() or
                        'YFRateLimitError' in error_type or
                        'RateLimitError' in error_type
                    )
                    
                    if is_rate_limit and attempt < max_retries - 1:
                        # 速率限制错误，使用更长的等待时间（指数退避：5秒、10秒、20秒、40秒、80秒）
                        wait_time = retry_delay * (2 ** attempt)
                        self.logger.warning(f"获取 {symbol} 数据遇到速率限制，等待 {wait_time:.1f} 秒后重试（第 {attempt + 1}/{max_retries} 次）...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 其他错误或重试次数用完
                        if attempt == max_retries - 1:
                            self.logger.error(f"获取 {symbol} 数据失败（已重试 {max_retries} 次）: {error_str}")
                        else:
                            self.logger.error(f"获取 {symbol} 数据失败: {error_str}")
                        if attempt == max_retries - 1:
                            import traceback
                            self.logger.error(traceback.format_exc())
        
        # 如果两种方法都失败
        self.logger.error(f"无法获取 {symbol} 数据：akshare和yfinance均失败")
        return pd.DataFrame()
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        获取股票基本信息（带重试机制，处理速率限制）
        
        Args:
            symbol: 股票代码
        
        Returns:
            股票信息字典
        """
        if not self.yfinance_available:
            self.logger.error("yfinance未安装，无法获取股票信息")
            return None
        
        max_retries = 5  # 增加重试次数
        retry_delay = 5.0  # 增加初始重试延迟（秒）
        
        # 每次请求前添加基础延迟，避免过快请求
        time.sleep(1.0)  # 基础延迟1秒
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # 重试前等待，使用指数退避策略
                    wait_time = retry_delay * (2 ** (attempt - 1))
                    self.logger.info(f"等待 {wait_time:.1f} 秒后重试获取 {symbol} 基本信息（第 {attempt + 1}/{max_retries} 次）...")
                    time.sleep(wait_time)
                else:
                    self.logger.info(f"正在获取 {symbol} 的基本信息...")
                
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if not info:
                    self.logger.warning(f"未获取到 {symbol} 的基本信息")
                    return None
                
                # 提取关键信息
                sector_name = info.get('sector', '')
                industry_name = info.get('industry', '')
                
                # 将sector和industry名称映射到GICS代码
                sector_code = self._map_sector_name_to_code(sector_name) if sector_name else None
                industry_code = self._generate_industry_code(industry_name, sector_code) if industry_name else None
                
                result = {
                    'symbol': symbol,
                    'name_en': info.get('longName') or info.get('shortName', ''),
                    'name_cn': info.get('longName') or info.get('shortName', ''),
                    'exchange': info.get('exchange', ''),
                    'sector': sector_name,  # 保留原始名称
                    'sector_code': sector_code,  # GICS代码
                    'industry': industry_name,  # 保留原始名称
                    'industry_code': industry_code,  # GICS代码（或生成的临时代码）
                    'market_cap': info.get('marketCap'),
                    'country': info.get('country', 'US'),
                    'currency': info.get('currency', 'USD'),
                    'website': info.get('website', ''),
                    'description': info.get('longBusinessSummary', ''),
                    'ipo_date': None,
                    'pe_ratio': info.get('trailingPE'),
                    'forward_pe': info.get('forwardPE'),
                    'pb_ratio': info.get('priceToBook'),
                    'dividend_yield': info.get('dividendYield')
                }
                
                # 处理IPO日期
                if 'firstTradeDateEpochUtc' in info:
                    result['ipo_date'] = datetime.fromtimestamp(info['firstTradeDateEpochUtc']).date()
                
                self.logger.info(f"成功获取 {symbol} 的基本信息")
                return result
                
            except Exception as e:
                error_str = str(e)
                error_type = type(e).__name__
                
                # 检查是否是速率限制错误
                is_rate_limit = (
                    'Rate limited' in error_str or 
                    'Too Many Requests' in error_str or
                    '429' in error_str or
                    'rate limit' in error_str.lower() or
                    'YFRateLimitError' in error_type or
                    'RateLimitError' in error_type
                )
                
                if is_rate_limit and attempt < max_retries - 1:
                    # 速率限制错误，使用更长的等待时间（指数退避：5秒、10秒、20秒、40秒、80秒）
                    wait_time = retry_delay * (2 ** attempt)
                    self.logger.warning(f"获取 {symbol} 基本信息遇到速率限制，等待 {wait_time:.1f} 秒后重试（第 {attempt + 1}/{max_retries} 次）...")
                    time.sleep(wait_time)
                    continue
                else:
                    # 其他错误或重试次数用完
                    if attempt == max_retries - 1:
                        self.logger.error(f"获取 {symbol} 基本信息失败（已重试 {max_retries} 次）: {error_str}")
                    else:
                        self.logger.error(f"获取 {symbol} 基本信息失败: {error_str}")
                    return None
    
    def get_sector_stocks(self, sector_name: str) -> List[str]:
        """
        获取某个板块的所有股票代码列表
        
        Args:
            sector_name: 板块名称（如：'Technology'）
        
        Returns:
            股票代码列表
        """
        # 这个方法需要从指数成分股或其他数据源获取
        # 暂时返回空列表，后续可以实现
        self.logger.warning(f"获取板块 {sector_name} 的股票列表功能待实现")
        return []
    
    def get_sp500_stocks(self) -> List[str]:
        """
        获取S&P 500成分股列表
        
        Returns:
            股票代码列表
        """
        try:
            self.logger.info("正在获取S&P 500成分股列表...")
            
            # 方法1: 从Wikipedia获取
            try:
                import requests
                from bs4 import BeautifulSoup
                import pandas as pd
                
                url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    table = soup.find('table', {'id': 'constituents'})
                    
                    if table:
                        df = pd.read_html(str(table))[0]
                        symbols = df['Symbol'].tolist()
                        # 清理符号（移除可能的后缀）
                        symbols = [s.replace('.', '-').split()[0] for s in symbols]
                        self.logger.info(f"从Wikipedia获取S&P 500成分股，共 {len(symbols)} 只")
                        return symbols
            except Exception as e1:
                self.logger.debug(f"从Wikipedia获取失败: {str(e1)}")
            
            # 方法2: 使用yfinance尝试从ETF获取
            if self.yfinance_available:
                try:
                    spy = yf.Ticker("SPY")
                    holdings = spy.get_holdings()
                    
                    if holdings is not None and not holdings.empty:
                        symbols = holdings.index.tolist()
                        self.logger.info(f"从SPY ETF获取成分股，共 {len(symbols)} 只")
                        return symbols
                except Exception as e2:
                    self.logger.debug(f"从ETF获取失败: {str(e2)}")
            
            # 方法3: 返回一些知名股票作为示例
            self.logger.warning("无法从外部源获取完整列表，返回示例股票")
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ']
                
        except Exception as e:
            self.logger.error(f"获取S&P 500成分股失败: {str(e)}")
            return []
    
    def get_nasdaq100_stocks(self) -> List[str]:
        """
        获取NASDAQ 100成分股列表
        
        Returns:
            股票代码列表
        """
        if not self.yfinance_available:
            return []
        
        try:
            self.logger.info("正在获取NASDAQ 100成分股列表...")
            
            qqq = yf.Ticker("QQQ")
            holdings = qqq.get_holdings()
            
            if holdings is not None and not holdings.empty:
                symbols = holdings.index.tolist()
                self.logger.info(f"成功获取NASDAQ 100成分股，共 {len(symbols)} 只")
                return symbols
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"获取NASDAQ 100成分股失败: {str(e)}")
            return []
    
    def get_sector_etf_data(self, sector_name: str, start_date: str = None, 
                           end_date: str = None, period: str = "10y") -> pd.DataFrame:
        """
        获取板块ETF的历史数据
        
        Args:
            sector_name: 板块名称（如：'Technology'）
            start_date: 开始日期
            end_date: 结束日期
            period: 时间周期
        
        Returns:
            DataFrame
        """
        etf_symbol = self.sector_etf_map.get(sector_name)
        if not etf_symbol:
            self.logger.warning(f"未找到板块 {sector_name} 对应的ETF")
            return pd.DataFrame()
        
        return self.get_stock_data(etf_symbol, start_date, end_date, period)
    
    def get_all_sectors_yesterday_performance(self) -> Dict[str, Dict]:
        """
        获取所有板块前一天的走势数据
        
        Returns:
            字典，键为板块名称（英文），值为包含走势信息的字典
            格式：{
                'Energy': {'change_pct': 1.5, 'close': 85.2, 'volume': 1000000, ...},
                'Materials': {...},
                ...
            }
        """
        result = {}
        
        # 计算前一天的日期
        yesterday = (datetime.now() - timedelta(days=1)).date()
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        # 获取最近3天的数据（以确保能获取到前一天的数据）
        start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        self.logger.info(f"正在获取所有板块前一天的走势数据（日期：{yesterday_str}）...")
        
        for sector_name, etf_symbol in self.sector_etf_map.items():
            try:
                # 获取ETF数据（只获取最近3天）
                df = self.get_stock_data(etf_symbol, start_date=start_date, end_date=end_date)
                
                if df.empty:
                    self.logger.warning(f"板块 {sector_name} ({etf_symbol}) 数据为空")
                    result[sector_name] = {
                        'symbol': etf_symbol,
                        'success': False,
                        'message': '数据为空'
                    }
                    continue
                
                # 查找前一天的数据
                yesterday_data = None
                for date_idx in df.index:
                    if isinstance(date_idx, pd.Timestamp):
                        if date_idx.date() == yesterday:
                            yesterday_data = df.loc[date_idx]
                            break
                    elif isinstance(date_idx, (datetime, type(datetime.now().date()))):
                        if date_idx == yesterday:
                            yesterday_data = df.loc[date_idx]
                            break
                
                if yesterday_data is None or yesterday_data.empty:
                    # 如果找不到前一天的数据，使用最后一条数据
                    if len(df) > 0:
                        yesterday_data = df.iloc[-1]
                        actual_date = df.index[-1]
                        if isinstance(actual_date, pd.Timestamp):
                            actual_date = actual_date.date()
                        self.logger.warning(f"板块 {sector_name} 未找到 {yesterday_str} 的数据，使用最后一条数据（日期：{actual_date}）")
                    else:
                        self.logger.warning(f"板块 {sector_name} 数据为空")
                        result[sector_name] = {
                            'symbol': etf_symbol,
                            'success': False,
                            'message': '未找到前一天数据'
                        }
                        continue
                
                # 计算涨跌幅（如果有前一天的数据）
                change_pct = None
                if len(df) >= 2:
                    prev_close = df.iloc[-2]['close'] if 'close' in df.columns else None
                    current_close = yesterday_data.get('close') if hasattr(yesterday_data, 'get') else yesterday_data.get('close', None) if isinstance(yesterday_data, dict) else yesterday_data['close']
                    if prev_close and current_close and prev_close > 0:
                        change_pct = ((current_close - prev_close) / prev_close) * 100
                
                # 提取关键数据
                sector_info = {
                    'symbol': etf_symbol,
                    'success': True,
                    'date': yesterday_str,
                    'close': float(yesterday_data.get('close', 0)) if hasattr(yesterday_data, 'get') else float(yesterday_data['close']),
                    'open': float(yesterday_data.get('open', 0)) if hasattr(yesterday_data, 'get') else float(yesterday_data['open']),
                    'high': float(yesterday_data.get('high', 0)) if hasattr(yesterday_data, 'get') else float(yesterday_data['high']),
                    'low': float(yesterday_data.get('low', 0)) if hasattr(yesterday_data, 'get') else float(yesterday_data['low']),
                    'volume': float(yesterday_data.get('volume', 0)) if hasattr(yesterday_data, 'get') else float(yesterday_data['volume']),
                    'change_pct': change_pct
                }
                
                result[sector_name] = sector_info
                self.logger.info(f"✓ {sector_name} ({etf_symbol}): 收盘 {sector_info['close']:.2f}, 涨跌 {change_pct:+.2f}%" if change_pct else f"✓ {sector_name} ({etf_symbol}): 收盘 {sector_info['close']:.2f}")
                
                # 添加延迟，避免速率限制
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"获取板块 {sector_name} ({etf_symbol}) 数据失败: {str(e)}")
                result[sector_name] = {
                    'symbol': etf_symbol,
                    'success': False,
                    'message': str(e)
                }
        
        success_count = sum(1 for v in result.values() if v.get('success', False))
        self.logger.info(f"成功获取 {success_count}/{len(self.sector_etf_map)} 个板块的前一天走势数据")
        
        return result