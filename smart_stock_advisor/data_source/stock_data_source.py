"""
股票数据源
"""
import akshare as ak
import pandas as pd
import random
import threading
import time
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any
from contextlib import contextmanager
from utils.logger import get_logger

logger = get_logger(__name__)


def _call_akshare_without_proxy(func: Callable, *args, **kwargs) -> Any:
    """
    在禁用代理的环境下调用akshare函数（带重试机制）
    
    Args:
        func: 要调用的akshare函数
        *args: 函数的位置参数
        **kwargs: 函数的关键字参数
    
    Returns:
        函数返回值
    
    Raises:
        Exception: 如果重试后仍然失败
    """
    max_retries = 3  # 最大重试次数
    retry_delay = 2  # 初始重试延迟（秒）
    
    for attempt in range(max_retries):
        # 保存原始代理设置
        original_proxy_env = {}
        proxy_env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                          'NO_PROXY', 'no_proxy', 'ALL_PROXY', 'all_proxy']
        
        for var in proxy_env_vars:
            original_proxy_env[var] = os.environ.get(var)
        
        # 保存requests库的代理设置
        original_requests_proxies = {}
        if hasattr(requests, 'proxies'):
            original_requests_proxies = getattr(requests, 'proxies', {})
        
        try:
            # 临时禁用所有代理环境变量
            for var in proxy_env_vars:
                if var in os.environ:
                    del os.environ[var]
            
            # 设置NO_PROXY为*，禁用所有代理
            os.environ['NO_PROXY'] = '*'
            os.environ['no_proxy'] = '*'
            
            # 禁用requests库的全局代理设置
            if hasattr(requests, 'proxies'):
                requests.proxies = {}
            
            # 尝试清除akshare内部session的代理设置
            try:
                if hasattr(ak, 'tool') and hasattr(ak.tool, 'session'):
                    # 保存原始session的代理设置
                    original_session_proxies = {}
                    if hasattr(ak.tool.session, 'proxies'):
                        original_session_proxies = ak.tool.session.proxies
                    
                    # 清除session的代理设置
                    ak.tool.session.proxies = {}
                    
                    # 尝试重新创建session（如果可能）
                    try:
                        import requests as req_module
                        ak.tool.session = req_module.Session()
                        ak.tool.session.proxies = {}
                    except Exception:
                        pass  # 如果重新创建失败，继续使用原session
            except Exception as e:
                logger.debug(f"清除akshare session代理设置失败: {str(e)}")
            
            # 调用函数
            result = func(*args, **kwargs)
            
            # 恢复原始代理设置
            for var, value in original_proxy_env.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            
            # 恢复requests库的代理设置
            if hasattr(requests, 'proxies'):
                requests.proxies = original_requests_proxies
            
            return result
            
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            
            # 检查是否是网络连接错误（需要重试）
            is_network_error = (
                'Connection aborted' in error_str or
                'RemoteDisconnected' in error_str or
                'Connection' in error_type or
                'Timeout' in error_type or
                'timeout' in error_str.lower() or
                'ECONNRESET' in error_str or
                'Broken pipe' in error_str or
                'Connection reset' in error_str.lower()
            )
            
            # 恢复原始代理设置（即使出错也要恢复）
            try:
                for var, value in original_proxy_env.items():
                    if value is not None:
                        os.environ[var] = value
                    elif var in os.environ:
                        del os.environ[var]
                
                if hasattr(requests, 'proxies'):
                    requests.proxies = original_requests_proxies
            except Exception:
                pass
            
            # 如果是网络错误且还有重试机会，则重试
            if is_network_error and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # 指数退避：2秒、4秒、8秒
                logger.warning(f"调用 {func.__name__} 时遇到网络连接问题（第 {attempt + 1}/{max_retries} 次尝试），等待 {wait_time:.1f} 秒后重试: {error_str}")
                time.sleep(wait_time)
                continue
            else:
                # 非网络错误或重试次数用完，记录错误并抛出异常
                if attempt == max_retries - 1:
                    logger.error(f"调用 {func.__name__} 失败（已重试 {max_retries} 次）: {error_str}")
                else:
                    logger.warning(f"调用 {func.__name__} 时遇到错误: {error_str}")
                raise

# 股票列表缓存（全局）
_stock_list_cache = {
    'data': None,
    'timestamp': None,
    'lock': threading.Lock(),
    'cache_duration': 3600  # 缓存1小时
}

# 实时行情数据缓存（全局）
_realtime_spot_cache = {
    'data': None,
    'timestamp': None,
    'lock': threading.Lock(),
    'cache_duration': 300  # 缓存5分钟（实时行情数据变化较快）
}

# 导入数据存储模块（使用绝对路径，避免相对导入失败）
import os
import importlib.util

DATA_STORAGE_AVAILABLE = False
DataStorage = None
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_storage_spec = importlib.util.spec_from_file_location(
        "data_storage",
        os.path.join(project_root, "utils", "data_storage.py")
    )
    data_storage_module = importlib.util.module_from_spec(data_storage_spec)
    data_storage_spec.loader.exec_module(data_storage_module)
    DataStorage = data_storage_module.DataStorage
    DATA_STORAGE_AVAILABLE = True
except Exception as e:
    DATA_STORAGE_AVAILABLE = False
    logger.warning(f"数据存储模块不可用，将不会保存指标数据到CSV: {str(e)}")

class StockDataSource:
    """股票数据源"""
    
    def __init__(self):
        self.logger = logger
        # 初始化数据存储管理器
        if DATA_STORAGE_AVAILABLE:
            self.data_storage = DataStorage(base_dir="data")
        else:
            self.data_storage = None
    
    def get_stock_data(self, symbol: str, days: int = 60, start_date: str = None, end_date: str = None, force_api: bool = False, use_db_only: bool = False, pre_queried_data: pd.DataFrame = None) -> pd.DataFrame:
        """
        获取股票历史数据（优先从数据库获取，如果数据库没有则从API获取）
        
        Args:
            symbol: 股票代码
            days: 获取最近多少天的数据（当start_date和end_date为None时使用）
            start_date: 开始日期（格式：YYYY-MM-DD 或 YYYYMMDD），如果提供，则忽略days参数
            end_date: 结束日期（格式：YYYY-MM-DD 或 YYYYMMDD），如果为None，则使用今天
            force_api: 是否强制从API获取（True=跳过数据库查询，直接从API获取；False=优先从数据库获取）
            use_db_only: 是否只使用数据库（True=只从数据库获取，如果数据库没有数据则返回空DataFrame；False=数据库没有时fallback到API）
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            # 计算日期范围
            if start_date is not None:
                # 转换日期格式为YYYY-MM-DD
                if '-' in start_date:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                else:
                    start_date_obj = datetime.strptime(start_date, '%Y%m%d')
                start_date_str = start_date_obj.strftime('%Y-%m-%d')
            else:
                end_date_obj = datetime.now()
                start_date_obj = end_date_obj - timedelta(days=days)
                start_date_str = start_date_obj.strftime('%Y-%m-%d')
            
            if end_date is not None:
                # 转换日期格式为YYYY-MM-DD
                if '-' in end_date:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                else:
                    end_date_obj = datetime.strptime(end_date, '%Y%m%d')
                end_date_str = end_date_obj.strftime('%Y-%m-%d')
            else:
                end_date_str = datetime.now().strftime('%Y-%m-%d')
            
            # 如果force_api=True，跳过数据库查询，直接从API获取
            if not force_api:
                # 优先从数据库获取
                try:
                    from utils.stock_history_storage import StockHistoryStorage
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        storage = StockHistoryStorage()
                        db_data = storage.get_stock_history_data(
                            symbol=symbol,
                            start_date=start_date_str,
                            end_date=end_date_str,
                            limit=None
                        )
                        
                        if db_data and len(db_data) > 0:
                            # 转换为DataFrame
                            records = []
                            for row in db_data:
                                records.append({
                                    'date': row.get('trade_date'),
                                    'open': float(row.get('open_price', 0)) if row.get('open_price') else None,
                                    'high': float(row.get('high_price', 0)) if row.get('high_price') else None,
                                    'low': float(row.get('low_price', 0)) if row.get('low_price') else None,
                                    'close': float(row.get('close_price', 0)) if row.get('close_price') else None,
                                    'volume': float(row.get('volume', 0)) if row.get('volume') else None,
                                })
                            
                            df = pd.DataFrame(records)
                            if not df.empty:
                                # 转换日期格式
                                df['date'] = pd.to_datetime(df['date'])
                                df = df.set_index('date')
                                df = df.sort_index()
                                
                                # 确保数据类型正确
                                for col in ['open', 'high', 'low', 'close', 'volume']:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                                
                                df = df.dropna()
                                
                                # 使用debug级别，避免日志过多（批量获取时会调用很多次）
                                self.logger.debug(f"从数据库获取 {symbol} 数据，共 {len(df)} 条记录（{start_date_str} 至 {end_date_str}）")
                                return df
                            else:
                                if use_db_only:
                                    self.logger.warning(f"数据库中没有 {symbol} 的数据，且use_db_only=True，返回空DataFrame")
                                    return pd.DataFrame()
                                self.logger.debug(f"数据库中没有 {symbol} 的数据，将从API获取")
                        else:
                            if use_db_only:
                                self.logger.warning(f"数据库中没有 {symbol} 的数据，且use_db_only=True，返回空DataFrame")
                                return pd.DataFrame()
                            self.logger.debug(f"数据库中没有 {symbol} 的数据，将从API获取")
                except Exception as e:
                    if use_db_only:
                        self.logger.warning(f"从数据库获取数据失败，且use_db_only=True，返回空DataFrame: {str(e)}")
                        return pd.DataFrame()
                    self.logger.debug(f"从数据库获取数据失败，将从API获取: {str(e)}")
            
            # 如果use_db_only=True，不调用API，直接返回空DataFrame
            if use_db_only:
                self.logger.warning(f"数据库中没有 {symbol} 的数据，且use_db_only=True，返回空DataFrame")
                return pd.DataFrame()
            
            # 如果数据库没有数据或force_api=True，从API获取
            start_date_str_api = start_date_obj.strftime('%Y%m%d')
            end_date_str_api = end_date_obj.strftime('%Y%m%d')
            
            if force_api:
                self.logger.info(f"[API调用] 强制从API获取 {symbol} 的数据: {start_date_str_api} 至 {end_date_str_api}")
            else:
                # 使用info级别，确保能看到API调用（批量获取时每50个股票打印一次进度）
                self.logger.info(f"[API调用] 正在从API获取 {symbol} 的数据: {start_date_str_api} 至 {end_date_str_api}")
            
            # 使用代理禁用函数调用akshare API
            df = _call_akshare_without_proxy(
                ak.stock_zh_a_hist,
                symbol=symbol,
                period="daily",
                start_date=start_date_str_api,
                end_date=end_date_str_api,
                adjust="qfq"
            )
            
            if df.empty:
                self.logger.warning(f"[API调用] {symbol} API返回空数据，请求范围: {start_date_str_api} 至 {end_date_str_api}")
                return pd.DataFrame()
            
            self.logger.info(f"[API调用] {symbol} API返回数据成功，共 {len(df)} 条记录")
            
            # 检查索引是否是日期类型（akshare有时会直接返回日期索引）
            if isinstance(df.index, pd.DatetimeIndex):
                self.logger.debug(f"{symbol} 检测到日期索引，将索引转换为date列")
                df = df.reset_index()
                # 索引列通常是第一列，将其重命名为date
                if len(df.columns) > 0:
                    first_col = df.columns[0]
                    df = df.rename(columns={first_col: 'date'})
            
            # 标准化列名（去除前后空格）
            df.columns = [col.strip() for col in df.columns]
            
            # 重命名列（使用简单直接的方法）
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '换手率': 'turnover_rate'
            }
            
            # 直接重命名匹配的列
            rename_dict = {}
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    rename_dict[old_col] = new_col
            
            if rename_dict:
                # 先保存'日期'列的数据用于fallback（如果重命名失败）
                date_col_data = None
                if '日期' in df.columns:
                    date_col_data = df['日期'].copy()
                
                df = df.rename(columns=rename_dict)
                self.logger.debug(f"{symbol} 重命名列: {rename_dict}")
                
                # 如果重命名失败，尝试直接创建date列
                if 'date' not in df.columns:
                    if date_col_data is not None:
                        df['date'] = date_col_data
                        self.logger.debug(f"{symbol} 通过fallback方法从保存的数据创建date列")
                    elif '日期' in df.columns:
                        df['date'] = df['日期']
                        self.logger.debug(f"{symbol} 通过fallback方法从'日期'列创建date列")
            else:
                self.logger.warning(f"{symbol} 没有找到任何可重命名的列，当前列名: {list(df.columns)}")
            
            # 如果date列缺失，尝试多种方法查找日期列
            if 'date' not in df.columns:
                self.logger.warning(f"{symbol} date列缺失，当前列名: {list(df.columns)}")
                # 方法1: 直接查找'日期'列（可能在标准化后仍然存在）
                if '日期' in df.columns:
                    df['date'] = df['日期']
                    self.logger.debug(f"{symbol} 从'日期'列复制到date列")
                # 方法2: 尝试查找第一列是否可能是日期列
                elif len(df.columns) > 0:
                    first_col = df.columns[0]
                    try:
                        if len(df) > 0:
                            sample_value = df[first_col].iloc[0]
                            if sample_value is not None:
                                pd.to_datetime(sample_value)
                                df = df.rename(columns={first_col: 'date'})
                                self.logger.debug(f"{symbol} 使用第一列作为日期列: {first_col}")
                    except Exception as e:
                        self.logger.debug(f"{symbol} 第一列不是日期格式: {str(e)}")
            
            # 确保包含必要的列（如果重命名失败，直接复制）
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            optional_cols = ['amount', 'turnover_rate']
            
            # 再次检查并复制缺失的列
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df[new_col] = df[old_col].copy()
                    self.logger.debug(f"{symbol} 从'{old_col}'列复制到'{new_col}'列")
            
            # 最终检查所有必需列是否存在
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                self.logger.error(f"获取 {symbol} 数据失败: 缺少必需的列 {missing_cols}，当前列名: {list(df.columns)}")
                # 最后一次尝试：如果date列缺失，尝试从第一列创建
                if 'date' in missing_cols and len(df.columns) > 0:
                    try:
                        first_col = df.columns[0]
                        df['date'] = df[first_col].copy()
                        self.logger.warning(f"{symbol} 最后一次尝试：从第一列'{first_col}'创建date列")
                        # 重新检查
                        missing_cols = [col for col in required_cols if col not in df.columns]
                        if missing_cols:
                            return pd.DataFrame()
                    except Exception as e:
                        self.logger.error(f"{symbol} 最后一次修复尝试失败: {str(e)}")
                        return pd.DataFrame()
                else:
                    return pd.DataFrame()
            
            # 再次确认date列存在（防止意外丢失）
            if 'date' not in df.columns:
                self.logger.error(f"获取 {symbol} 数据失败: date列在最终检查时丢失，当前列名: {list(df.columns)}")
                return pd.DataFrame()
            
            # 保留必要列和可选列（如果存在）
            cols_to_keep = required_cols.copy()
            for col in optional_cols:
                if col in df.columns:
                    cols_to_keep.append(col)
            
            # 确保date列在cols_to_keep中
            if 'date' not in cols_to_keep:
                cols_to_keep.insert(0, 'date')
            
            df = df[cols_to_keep].copy()
            
            # 再次确认date列存在（防止copy后丢失）
            if 'date' not in df.columns:
                self.logger.error(f"获取 {symbol} 数据失败: date列在copy后丢失，cols_to_keep: {cols_to_keep}，当前列名: {list(df.columns)}")
                return pd.DataFrame()
            
            # 如果API没有返回成交额，尝试计算（近似值：收盘价 * 成交量）
            if 'amount' not in df.columns or df['amount'].isna().all():
                if 'close' in df.columns and 'volume' in df.columns:
                    # 成交额 = 收盘价 * 成交量（手转股：1手=100股）
                    df['amount'] = df['close'] * df['volume'] * 100
                    self.logger.debug(f"{symbol} 成交额通过计算获得（收盘价*成交量*100）")
            
            # 转换日期格式（再次确认date列存在）
            if 'date' not in df.columns:
                self.logger.error(f"获取 {symbol} 数据失败: date列在日期转换前丢失")
                return pd.DataFrame()
            
            try:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                df = df.sort_index()
            except Exception as e:
                self.logger.error(f"获取 {symbol} 数据失败: 日期转换失败: {str(e)}，date列内容: {df['date'].head(3).tolist() if 'date' in df.columns else 'date列不存在'}")
                return pd.DataFrame()
            
            # 确保数据类型正确
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            if 'amount' in df.columns:
                numeric_cols.append('amount')
            if 'turnover_rate' in df.columns:
                numeric_cols.append('turnover_rate')
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 只对必要列进行dropna，保留可选列
            # 注意：date列已经是索引了，所以需要从subset中排除
            cols_for_dropna = [col for col in required_cols if col in df.columns]
            if cols_for_dropna:
                df = df.dropna(subset=cols_for_dropna)
            else:
                self.logger.warning(f"{symbol} 没有列可用于dropna，所有必需列都已经是索引或不存在")
            
            self.logger.info(f"从API获取 {symbol} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            data = self.get_stock_data(symbol, days=1)
            if not data.empty:
                return float(data['close'].iloc[-1])
            return 0.0
        except Exception as e:
            self.logger.error(f"获取当前价格失败: {str(e)}")
            return 0.0
    
    def get_stock_industry_info(self, symbol: str, use_db_only: bool = False) -> Dict:
        """
        获取股票行业和概念板块信息
        
        Args:
            symbol: 股票代码
            use_db_only: 是否只使用数据库数据（设置页面预测时应设为True，不调用API）
        
        Returns:
            {
                'industry': '行业名称',
                'concepts': ['概念1', '概念2', ...],
                'industry_keywords': ['行业关键词1', ...]
            }
        """
        try:
            industry_info = {
                'industry': '',
                'concepts': [],
                'industry_keywords': []
            }
            
            # 设置页面预测：如果use_db_only=True，只从数据库获取数据
            if use_db_only:
                try:
                    from utils.db_connection import DatabaseConnection
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        db = DatabaseConnection()
                        # 从stock_industry_info表获取行业信息
                        sql = """
                            SELECT industry, concepts
                            FROM stock_industry_info
                            WHERE symbol = %s
                            LIMIT 1
                        """
                        result = db.execute_query(sql, (symbol,))
                        
                        if result and len(result) > 0:
                            record = result[0]
                            industry = record.get('industry', '')
                            concepts_str = record.get('concepts', '')
                            
                            if industry:
                                industry_info['industry'] = industry
                                industry_info['industry_keywords'].append(industry)
                            
                            if concepts_str:
                                # 解析concepts（可能是JSON字符串或逗号分隔的字符串）
                                try:
                                    import json
                                    concepts = json.loads(concepts_str) if isinstance(concepts_str, str) else concepts_str
                                    if isinstance(concepts, list):
                                        industry_info['concepts'] = concepts
                                        industry_info['industry_keywords'].extend(concepts)
                                    elif isinstance(concepts, str):
                                        concepts_list = [c.strip() for c in concepts.split(',') if c.strip()]
                                        industry_info['concepts'] = concepts_list
                                        industry_info['industry_keywords'].extend(concepts_list)
                                except:
                                    # 如果解析失败，尝试作为逗号分隔的字符串处理
                                    concepts_list = [c.strip() for c in str(concepts_str).split(',') if c.strip()]
                                    industry_info['concepts'] = concepts_list
                                    industry_info['industry_keywords'].extend(concepts_list)
                except Exception as e:
                    self.logger.debug(f"从数据库获取股票行业信息失败: {str(e)}")
                
                # 设置页面预测：如果数据库没有数据，返回空数据（不做API调用）
                return industry_info
            
            # 如果use_db_only=False，从API获取（实时预测模式）
            # 获取股票基本信息（使用无代理方式调用，避免代理连接错误）
            stock_info = _call_akshare_without_proxy(ak.stock_individual_info_em, symbol=symbol)
            if stock_info is not None and not stock_info.empty:
                for _, row in stock_info.iterrows():
                    key = str(row.iloc[0]).strip()
                    value = str(row.iloc[1]).strip()
                    
                    # 行业信息
                    if '行业' in key or 'industry' in key.lower():
                        industry_info['industry'] = value
                        industry_info['industry_keywords'].append(value)
                    
                    # 概念板块
                    if '概念' in key or 'concept' in key.lower():
                        if value and value != 'nan':
                            concepts = [c.strip() for c in value.split(',') if c.strip()]
                            industry_info['concepts'].extend(concepts)
                            industry_info['industry_keywords'].extend(concepts)
            
            # 尝试从其他接口获取概念板块（使用无代理方式调用）
            # 注意：只在use_db_only=False时调用（实时预测模式）
            try:
                concept_data = _call_akshare_without_proxy(ak.stock_board_concept_name_em)
                if not concept_data.empty:
                    # 查找包含该股票的概念板块
                    for _, row in concept_data.iterrows():
                        concept_name = str(row.iloc[0]) if len(row) > 0 else ''
                        if concept_name and concept_name not in industry_info['concepts']:
                            # 这里可以进一步查询该概念下的股票列表
                            # 简化处理：将概念名称加入关键词
                            industry_info['industry_keywords'].append(concept_name)
            except:
                pass
            
            # 去重
            industry_info['concepts'] = list(set(industry_info['concepts']))
            industry_info['industry_keywords'] = list(set(industry_info['industry_keywords']))
            
            return industry_info
        except Exception as e:
            self.logger.error(f"获取股票行业信息失败: {str(e)}")
            return {'industry': '', 'concepts': [], 'industry_keywords': []}
    
    def get_stock_info(self, symbol: str, skip_pe_pb: bool = False) -> dict:
        """
        获取股票基本信息（包括市盈率、市净率等）
        
        Args:
            symbol: 股票代码
            skip_pe_pb: 是否跳过PE/PB获取（历史数据收集时可以跳过，提升性能）
        
        Returns:
            股票信息字典
        """
        global _realtime_spot_cache  # 在函数开始处声明global
        
        try:
            # 获取股票基本信息（使用无代理方式调用）
            stock_info = _call_akshare_without_proxy(ak.stock_individual_info_em, symbol=symbol)
            info_dict = {}
            if stock_info is not None and not stock_info.empty:
                for _, row in stock_info.iterrows():
                    key = str(row.iloc[0]).strip()
                    value = row.iloc[1]
                    info_dict[key] = value
            
            # 尝试获取市盈率、市净率（如果skip_pe_pb=True则跳过，提升性能）
            if skip_pe_pb:
                self.logger.debug(f"{symbol} 跳过PE/PB获取（skip_pe_pb=True）")
            else:
                try:
                    # 获取实时行情数据，可能包含PE、PB（使用缓存）
                    realtime_data = None
                    
                    # 检查缓存
                    with _realtime_spot_cache['lock']:
                        if _realtime_spot_cache['data'] is not None:
                            cache_age = time.time() - _realtime_spot_cache['timestamp'] if _realtime_spot_cache['timestamp'] else float('inf')
                            if cache_age < _realtime_spot_cache['cache_duration']:
                                realtime_data = _realtime_spot_cache['data'].copy()
                                self.logger.debug(f"使用缓存的实时行情数据（缓存年龄: {cache_age:.1f}秒）")
                    
                    # 如果缓存未命中，获取新数据并更新缓存
                    if realtime_data is None:
                        realtime_data = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
                        if not realtime_data.empty:
                            with _realtime_spot_cache['lock']:
                                _realtime_spot_cache['data'] = realtime_data.copy()
                                _realtime_spot_cache['timestamp'] = time.time()
                                self.logger.debug(f"实时行情数据已缓存（{len(realtime_data)}只股票）")
                    
                    if not realtime_data.empty:
                        # 查找代码列
                        code_col = None
                        for col in realtime_data.columns:
                            if '代码' in col or 'code' in col.lower():
                                code_col = col
                                break
                        
                        if code_col:
                            stock_data = realtime_data[realtime_data[code_col] == symbol]
                            if not stock_data.empty:
                                # 查找PE、PB列
                                for col in realtime_data.columns:
                                    col_lower = col.lower()
                                    if ('市盈率' in col or 'pe' in col_lower) and 'pe_ratio' not in info_dict:
                                        pe_value = stock_data[col].iloc[0]
                                        if pd.notna(pe_value) and str(pe_value) != 'nan':
                                            try:
                                                pe_float = float(str(pe_value).replace('倍', '').replace(',', '').strip())
                                                info_dict['pe_ratio'] = pe_float
                                            except:
                                                pass
                                    if ('市净率' in col or 'pb' in col_lower) and 'pb_ratio' not in info_dict:
                                        pb_value = stock_data[col].iloc[0]
                                        if pd.notna(pb_value) and str(pb_value) != 'nan':
                                            try:
                                                pb_float = float(str(pb_value).replace('倍', '').replace(',', '').strip())
                                                info_dict['pb_ratio'] = pb_float
                                            except:
                                                pass
                except Exception as e:
                    self.logger.debug(f"获取PE/PB失败: {str(e)}")
            
            # 如果从基本信息中获取到PE、PB，直接使用
            for key, value in info_dict.items():
                if '市盈率' in key or 'PE' in key.upper():
                    try:
                        pe = float(str(value).replace('倍', '').replace(',', ''))
                        info_dict['pe_ratio'] = pe
                    except:
                        pass
                if '市净率' in key or 'PB' in key.upper():
                    try:
                        pb = float(str(value).replace('倍', '').replace(',', ''))
                        info_dict['pb_ratio'] = pb
                    except:
                        pass
            
            # 提取股票名称（尝试多个可能的键名）
            stock_name = None
            for key in ['股票简称', '股票名称', '名称', 'name', '股票全称']:
                if key in info_dict:
                    stock_name = str(info_dict[key]).strip()
                    if stock_name and stock_name != 'nan' and stock_name != '':
                        info_dict['name'] = stock_name
                        break
            
            # 如果还是没有找到名称，尝试从实时行情获取（使用缓存）
            if not stock_name or stock_name == '':
                try:
                    # 使用缓存的实时行情数据（已在函数开始处声明global）
                    realtime_data = None
                    
                    # 检查缓存
                    with _realtime_spot_cache['lock']:
                        if _realtime_spot_cache['data'] is not None:
                            cache_age = time.time() - _realtime_spot_cache['timestamp'] if _realtime_spot_cache['timestamp'] else float('inf')
                            if cache_age < _realtime_spot_cache['cache_duration']:
                                realtime_data = _realtime_spot_cache['data'].copy()
                    
                    # 如果缓存未命中，获取新数据并更新缓存
                    if realtime_data is None:
                        realtime_data = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
                        if not realtime_data.empty:
                            with _realtime_spot_cache['lock']:
                                _realtime_spot_cache['data'] = realtime_data.copy()
                                _realtime_spot_cache['timestamp'] = time.time()
                    
                    if not realtime_data.empty:
                        code_col = None
                        name_col = None
                        for col in realtime_data.columns:
                            if '代码' in col or 'code' in col.lower():
                                code_col = col
                            if '名称' in col or 'name' in col.lower():
                                name_col = col
                        
                        if code_col and name_col:
                            stock_data = realtime_data[realtime_data[code_col] == symbol]
                            if not stock_data.empty:
                                name_value = stock_data[name_col].iloc[0]
                                if pd.notna(name_value):
                                    stock_name = str(name_value).strip()
                                    if stock_name and stock_name != 'nan':
                                        info_dict['name'] = stock_name
                except Exception as e:
                    self.logger.debug(f"从实时行情获取股票名称失败: {str(e)}")
            
            return info_dict
        except Exception as e:
            self.logger.warning(f"获取股票信息失败: {str(e)}")
            return {}

    def get_all_stock_list(self, limit: int = None, sort_by_turnover: bool = True, random_sort: bool = False, use_cache: bool = True) -> List[Dict]:
        """
        获取A股股票列表（代码+名称）（支持缓存）

        Args:
            limit: 限制返回数量，None表示返回全部
            sort_by_turnover: 是否按成交额排序（从高到低），默认True
            random_sort: 是否随机排序，如果为True，则忽略sort_by_turnover
            use_cache: 是否使用缓存（默认True）

        Returns:
            [{'symbol': '000001', 'name': '平安银行'}, ...]
        """
        global _stock_list_cache
        
        # 检查缓存
        if use_cache:
            with _stock_list_cache['lock']:
                if _stock_list_cache['data'] is not None:
                    cache_age = time.time() - _stock_list_cache['timestamp'] if _stock_list_cache['timestamp'] else float('inf')
                    if cache_age < _stock_list_cache['cache_duration']:
                        self.logger.debug(f"使用缓存的股票列表（缓存年龄: {cache_age:.1f}秒）")
                        cached_data = _stock_list_cache['data'].copy()
                        # 应用limit和排序
                        if random_sort:
                            random.shuffle(cached_data)
                        elif sort_by_turnover:
                            # 注意：缓存的数据可能没有按成交额排序，需要重新排序
                            # 但为了性能，这里直接返回缓存数据
                            pass
                        if limit and limit > 0:
                            cached_data = cached_data[:limit]
                        return cached_data
        
        try:
            df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
            if df is None or df.empty:
                return []

            # 识别"代码/名称/成交额"列（不同版本AkShare列名可能略有差异）
            code_col = None
            name_col = None
            turnover_col = None
            
            for col in df.columns:
                col_s = str(col)
                if code_col is None and ('代码' in col_s or col_s.lower() in ['code', 'symbol']):
                    code_col = col
                if name_col is None and ('名称' in col_s or col_s.lower() in ['name']):
                    name_col = col
                if turnover_col is None and ('成交额' in col_s or 'turnover' in col_s.lower()):
                    turnover_col = col

            if code_col is None:
                for candidate in ['代码', '股票代码']:
                    if candidate in df.columns:
                        code_col = candidate
                        break
            if name_col is None:
                for candidate in ['名称', '股票名称']:
                    if candidate in df.columns:
                        name_col = candidate
                        break
            if turnover_col is None:
                for candidate in ['成交额', '成交量']:
                    if candidate in df.columns:
                        turnover_col = candidate
                        break

            if code_col is None:
                self.logger.warning("无法从 ak.stock_zh_a_spot_em() 结果中识别股票代码列")
                return []

            # 根据排序方式处理
            if random_sort:
                # 随机排序：先构建所有记录，然后打乱
                self.logger.info("使用随机排序")
                records: List[Dict] = []
                for _, row in df.iterrows():
                    code = str(row.get(code_col, '')).strip()
                    if not code:
                        continue
                    if code.isdigit():
                        code = code.zfill(6)  # 保留前导零

                    name = ''
                    if name_col is not None:
                        name = str(row.get(name_col, '')).strip()

                    records.append({'symbol': code, 'name': name})
                
                # 打乱顺序
                random.shuffle(records)
            elif sort_by_turnover and turnover_col:
                # 按成交额排序：先排序DataFrame，再构建记录
                self.logger.info(f"按 {turnover_col} 排序（从高到低）")
                # 确保成交额列为数值类型
                df[turnover_col] = pd.to_numeric(df[turnover_col], errors='coerce')
                # 按成交额降序排序
                df = df.sort_values(by=turnover_col, ascending=False, na_position='last')
                
                # 构建记录（已排序）
                records: List[Dict] = []
                for _, row in df.iterrows():
                    code = str(row.get(code_col, '')).strip()
                    if not code:
                        continue
                    if code.isdigit():
                        code = code.zfill(6)  # 保留前导零

                    name = ''
                    if name_col is not None:
                        name = str(row.get(name_col, '')).strip()

                    records.append({'symbol': code, 'name': name})
            else:
                # 原始顺序（不排序）
                records: List[Dict] = []
                for _, row in df.iterrows():
                    code = str(row.get(code_col, '')).strip()
                    if not code:
                        continue
                    if code.isdigit():
                        code = code.zfill(6)  # 保留前导零

                    name = ''
                    if name_col is not None:
                        name = str(row.get(name_col, '')).strip()

                    records.append({'symbol': code, 'name': name})
            
            # 如果设置了limit，截取指定数量
            if limit and limit > 0:
                records = records[:limit]
                sort_desc = '随机' if random_sort else ('按成交额' if sort_by_turnover else '原始')
                self.logger.info(f"成功获取 {len(records)} 只股票（{sort_desc}排序，取前{limit}只）")
            else:
                sort_desc = '随机' if random_sort else ('按成交额' if sort_by_turnover else '原始')
                self.logger.info(f"成功获取 {len(records)} 只股票（{sort_desc}排序）")
            
            # 更新缓存（只缓存未限制数量的完整列表）
            if use_cache and (limit is None or limit == 0):
                with _stock_list_cache['lock']:
                    _stock_list_cache['data'] = records.copy()
                    _stock_list_cache['timestamp'] = time.time()
                    self.logger.debug(f"股票列表已缓存（{len(records)}只股票）")
            
            return records
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return []
    
    def get_market_index_data(self, index_code: str = "sh000001", days: int = 60, use_db_only: bool = False) -> pd.DataFrame:
        """
        获取市场指数历史数据
        
        Args:
            index_code: 指数代码
                - "sh000001": 上证指数
                - "sz399001": 深证成指
                - "sz399006": 创业板指
            days: 获取最近多少天的数据
            use_db_only: 是否只使用数据库数据（设置页面预测时应设为True，不调用API）
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            # 设置页面预测：如果use_db_only=True，只从数据库获取数据
            if use_db_only:
                try:
                    from utils.db_connection import DatabaseConnection
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        db = DatabaseConnection()
                        # 从stock_history_data表获取指数数据（指数代码作为symbol）
                        start_date_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                        end_date_str = datetime.now().strftime('%Y-%m-%d')
                        
                        sql = """
                            SELECT trade_date as date, open_price as open, high_price as high, 
                                   low_price as low, close_price as close, volume
                            FROM stock_history_data
                            WHERE symbol = %s
                            AND period_type = 'daily'
                            AND trade_date >= %s
                            AND trade_date <= %s
                            ORDER BY trade_date ASC
                        """
                        records = db.execute_query(sql, (index_code, start_date_str, end_date_str))
                        
                        if records and len(records) > 0:
                            df = pd.DataFrame(records)
                            if not df.empty:
                                df['date'] = pd.to_datetime(df['date'])
                                df = df.set_index('date')
                                df = df.sort_index()
                                
                                # 确保数据类型正确
                                for col in ['open', 'high', 'low', 'close', 'volume']:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                                
                        df = df.dropna()
                        self.logger.debug(f"从数据库获取指数 {index_code} 数据，共 {len(df)} 条记录")
                        return df
                except Exception as e:
                    self.logger.debug(f"从数据库获取指数 {index_code} 数据失败: {str(e)}")
                
                # 如果数据库没有数据或查询失败，且use_db_only=True，返回空DataFrame（设置页面预测：不做API调用）
                self.logger.debug(f"数据库中没有指数 {index_code} 的数据，且use_db_only=True，返回空DataFrame")
                return pd.DataFrame()
            
            # 如果use_db_only=False，从API获取
            self.logger.info(f"正在获取指数 {index_code} 的数据: {start_date} 至 {end_date}")
            
            # 使用akshare获取指数数据
            # akshare获取指数数据的接口
            try:
                # 方法1: 使用index_zh_a_hist（需要指数代码，如"000001"）
                index_symbol = index_code.replace('sh', '').replace('sz', '')
                df = ak.index_zh_a_hist(symbol=index_symbol, period="日k", 
                                        start_date=start_date, 
                                        end_date=end_date)
                
                # 检查返回的数据格式，可能需要调整列名
                if not df.empty:
                    # 如果返回的列名不包含'date'，尝试查找日期列
                    if 'date' not in df.columns:
                        # 查找可能的日期列
                        date_cols = [col for col in df.columns if '日期' in col or 'date' in col.lower() or '时间' in col]
                        if date_cols:
                            df = df.rename(columns={date_cols[0]: 'date'})
                        else:
                            # 如果没有找到日期列，尝试使用索引
                            if df.index.name in ['日期', 'date', '时间']:
                                df = df.reset_index()
                                df = df.rename(columns={df.columns[0]: 'date'})
                            else:
                                # 如果都没有，尝试使用第一列作为日期
                                df = df.reset_index()
                                if len(df.columns) > 0:
                                    df = df.rename(columns={df.columns[0]: 'date'})
                
            except Exception as e1:
                try:
                    # 方法2: 使用stock_zh_index_daily获取指数日线数据
                    df = ak.stock_zh_index_daily(symbol=index_code)
                    # 过滤日期范围
                    if not df.empty:
                        # 查找日期列
                        date_cols = [col for col in df.columns if '日期' in col or 'date' in col.lower()]
                        if date_cols:
                            df = df.rename(columns={date_cols[0]: 'date'})
                        elif df.index.name in ['日期', 'date']:
                            df = df.reset_index()
                            df = df.rename(columns={df.columns[0]: 'date'})
                        else:
                            df = df.reset_index()
                            if len(df.columns) > 0:
                                df = df.rename(columns={df.columns[0]: 'date'})
                        
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            df = df[(df['date'] >= pd.to_datetime(start_date)) & 
                                   (df['date'] <= pd.to_datetime(end_date))]
                except Exception as e2:
                    self.logger.warning(f"获取指数{index_code}数据失败: {str(e1)}, {str(e2)}")
                    return pd.DataFrame()
            
            if df.empty:
                self.logger.warning(f"未获取到指数 {index_code} 的数据")
                return pd.DataFrame()
            
            # 标准化列名
            df.columns = [col.strip() for col in df.columns]
            
            # 重命名列
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume'
            }
            
            rename_dict = {}
            for old_col, new_col in column_mapping.items():
                for col in df.columns:
                    if old_col in col:
                        rename_dict[col] = new_col
                        break
            
            df = df.rename(columns=rename_dict)
            
            # 确保包含必要的列
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df[new_col] = df[old_col]
            
            df = df[required_cols].copy()
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.sort_index()
            
            # 确保数据类型正确
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            
            self.logger.info(f"成功获取指数 {index_code} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取指数 {index_code} 数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_all_market_indices(self, days: int = 60, use_db_only: bool = False) -> Dict[str, pd.DataFrame]:
        """
        获取所有主要市场指数数据
        
        Args:
            days: 获取最近多少天的数据
            use_db_only: 是否只使用数据库数据（设置页面预测时应设为True，不调用API）
        
        Returns:
            字典，包含各指数的数据
        """
        indices = {
            'sh000001': '上证指数',
            'sz399001': '深证成指',
            'sz399006': '创业板指'
        }
        
        result = {}
        for code, name in indices.items():
            try:
                data = self.get_market_index_data(code, days, use_db_only=use_db_only)
                if not data.empty:
                    result[name] = data
            except Exception as e:
                self.logger.warning(f"获取{name}数据失败: {str(e)}")
        
        return result
    
    def get_us_sector_data(self, sector_name: str = None, days: int = 5, use_db_only: bool = False) -> pd.DataFrame:
        """
        获取美股板块数据
        
        Args:
            sector_name: 板块名称（如：科技、金融、能源等），如果为None则获取主要指数
            days: 获取最近多少天的数据
            use_db_only: 是否只使用数据库数据（设置页面预测时应设为True，不调用API）
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            # 设置页面预测：如果use_db_only=True，只从数据库获取数据
            if use_db_only:
                try:
                    from utils.db_connection import DatabaseConnection
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        db = DatabaseConnection()
                        # 从us_sector_index_history表获取数据
                        # 美股板块ETF映射
                        sector_etf_map = {
                            '半导体': 'SOXX', '芯片': 'SMH', '云计算': 'CLOU', '互联网': 'QQQ',
                            '新能源': 'ICLN', '新能源车': 'DRIV', '光伏': 'TAN',
                            '科技': 'XLK', '金融': 'XLF', '医疗': 'XLV', '能源': 'XLE',
                            '消费': 'XLY', '工业': 'XLI', '材料': 'XLB', '公用事业': 'XLU',
                            '房地产': 'XLRE', '通信': 'XLC', '消费必需品': 'XLP',
                        }
                        
                        symbol = sector_etf_map.get(sector_name, 'SPY') if sector_name else 'SPY'
                        end_date_str = datetime.now().strftime('%Y-%m-%d')
                        start_date_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                        
                        sql = """
                            SELECT trade_date as date, open_price as open, high_price as high, 
                                   low_price as low, close_price as close, volume
                            FROM us_sector_index_history
                            WHERE symbol = %s
                            AND trade_date >= %s
                            AND trade_date <= %s
                            ORDER BY trade_date ASC
                        """
                        records = db.execute_query(sql, (symbol, start_date_str, end_date_str))
                        
                        if records and len(records) > 0:
                            df = pd.DataFrame(records)
                            if not df.empty:
                                df['date'] = pd.to_datetime(df['date'])
                                df = df.set_index('date')
                                df = df.sort_index()
                                
                                for col in ['open', 'high', 'low', 'close', 'volume']:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                                
                                df = df.dropna()
                                self.logger.debug(f"从数据库获取美股板块 {symbol} 数据，共 {len(df)} 条记录")
                                return df
                except Exception as e:
                    self.logger.debug(f"从数据库获取美股板块数据失败: {str(e)}")
                
                # 如果数据库没有数据，返回空DataFrame（设置页面预测：不做API调用）
                self.logger.debug(f"数据库中没有美股板块 {sector_name or 'SPY'} 的数据，且use_db_only=True，返回空DataFrame")
                return pd.DataFrame()
            
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            # 美股板块ETF映射（用于获取板块数据）
            # 先细分主题板块，再使用大类板块作为兜底
            sector_etf_map = {
                # 精细化科技相关
                '半导体': 'SOXX',      # iShares Semiconductor ETF
                '芯片': 'SMH',         # VanEck Semiconductor ETF
                '云计算': 'CLOU',      # Global X Cloud Computing ETF
                '互联网': 'QQQ',       # Invesco QQQ Trust（纳指100，高度科技/互联网）
                # 新能源相关
                '新能源': 'ICLN',      # iShares Global Clean Energy ETF
                '新能源车': 'DRIV',    # Global X Autonomous & Electric Vehicles ETF
                '光伏': 'TAN',         # Invesco Solar ETF
                # 大类行业板块
                '科技': 'XLK',         # Technology Select Sector SPDR Fund
                '金融': 'XLF',         # Financial Select Sector SPDR Fund
                '医疗': 'XLV',         # Health Care Select Sector SPDR Fund
                '能源': 'XLE',         # Energy Select Sector SPDR Fund
                '消费': 'XLY',         # Consumer Discretionary Select Sector SPDR Fund
                '工业': 'XLI',         # Industrial Select Sector SPDR Fund
                '材料': 'XLB',         # Materials Select Sector SPDR Fund
                '公用事业': 'XLU',     # Utilities Select Sector SPDR Fund
                '房地产': 'XLRE',      # Real Estate Select Sector SPDR Fund
                '通信': 'XLC',         # Communication Services Select Sector SPDR Fund
                '消费必需品': 'XLP',   # Consumer Staples Select Sector SPDR Fund
            }
            
            # 如果指定了板块名称，使用对应的ETF
            if sector_name and sector_name in sector_etf_map:
                symbol = sector_etf_map[sector_name]
            else:
                # 默认获取标普500指数
                symbol = 'SPY'  # SPDR S&P 500 ETF
            
            self.logger.info(f"正在获取美股板块数据: {symbol} ({sector_name or '标普500'})")
            
            # 使用akshare获取美股ETF数据
            try:
                # 方法1: 尝试使用stock_us_hist获取历史数据
                try:
                    df = ak.stock_us_hist(symbol=symbol, period="daily", 
                                         start_date=start_date.replace('-', ''), 
                                         end_date=end_date.replace('-', ''), 
                                         adjust="qfq")
                except:
                    # 方法2: 尝试使用stock_us_daily获取日线数据
                    try:
                        df = ak.stock_us_daily(symbol=symbol)
                        # 过滤日期范围
                        if not df.empty and 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            df = df[(df['date'] >= pd.to_datetime(start_date)) & 
                                   (df['date'] <= pd.to_datetime(end_date))]
                    except:
                        # 方法3: 如果akshare不支持，返回空DataFrame
                        self.logger.warning(f"akshare不支持获取美股板块 {symbol} 的数据")
                        return pd.DataFrame()
                
                if df.empty:
                    self.logger.warning(f"未获取到美股板块 {symbol} 的数据")
                    return pd.DataFrame()
                
                # 标准化列名
                df.columns = [col.strip() for col in df.columns]
                
                # 重命名列（akshare美股数据列名可能不同）
                column_mapping = {
                    '日期': 'date',
                    'Date': 'date',
                    'date': 'date',
                    '开盘': 'open',
                    'Open': 'open',
                    'open': 'open',
                    '收盘': 'close',
                    'Close': 'close',
                    'close': 'close',
                    '最高': 'high',
                    'High': 'high',
                    'high': 'high',
                    '最低': 'low',
                    'Low': 'low',
                    'low': 'low',
                    '成交量': 'volume',
                    'Volume': 'volume',
                    'volume': 'volume'
                }
                
                rename_dict = {}
                for old_col, new_col in column_mapping.items():
                    for col in df.columns:
                        if old_col.lower() == col.lower():
                            rename_dict[col] = new_col
                            break
                
                df = df.rename(columns=rename_dict)
                
                # 确保包含必要的列
                required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
                for col in required_cols:
                    if col not in df.columns:
                        # 尝试使用第一列作为date
                        if col == 'date' and len(df.columns) > 0:
                            df = df.rename(columns={df.columns[0]: 'date'})
                        else:
                            self.logger.warning(f"缺少列: {col}")
                            return pd.DataFrame()
                
                df = df[required_cols].copy()
                
                # 转换日期格式
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                df = df.sort_index()
                
                # 确保数据类型正确
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df = df.dropna()
                
                self.logger.info(f"成功获取美股板块 {symbol} 数据，共 {len(df)} 条记录")
                return df
                
            except Exception as e:
                self.logger.warning(f"获取美股板块数据失败: {str(e)}")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"获取美股板块数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_us_sector_mapping(self) -> Dict[str, List[str]]:
        """
        获取美股板块与A股板块的映射关系
        
        Returns:
            字典，键为美股板块名称（包括细分主题），值为对应的A股行业/概念关键词列表
        """
        return {
            # 精细化科技链
            '半导体': ['半导体', '芯片', '集成电路', '功率半导体', '封测', '设计', '代工'],
            '芯片': ['芯片', 'GPU', 'CPU', '存储芯片', '射频芯片'],
            '云计算': ['云计算', '云服务', '数据中心', '服务器', 'IDC'],
            '互联网': ['互联网', '平台经济', '电商', '社交', '在线广告'],
            # 新能源链
            '新能源': ['新能源', '风电', '光伏', '清洁能源', '储能'],
            '新能源车': ['新能源汽车', '电动车', '锂电池', '动力电池', '充电桩'],
            '光伏': ['光伏', '太阳能', '组件', '逆变器', '光伏玻璃'],
            # 大类行业
            '科技': ['计算机', '电子', '通信', '软件', '人工智能', '云', '信息技术'],
            '金融': ['银行', '证券', '保险', '金融', '信托', '券商'],
            '医疗': ['医药', '医疗', '生物', '医疗器械', '生物医药', '疫苗'],
            '能源': ['石油', '天然气', '煤炭', '能源', '电力', '油服'],
            '消费': ['消费', '零售', '商贸', '电商', '消费电子', '家电', '白酒', '啤酒'],
            '工业': ['机械', '工业', '制造', '装备', '自动化', '工控', '高端制造'],
            '材料': ['化工', '钢铁', '有色金属', '材料', '建材', '稀土'],
            '公用事业': ['公用事业', '水务', '燃气', '环保', '垃圾发电'],
            '房地产': ['房地产', '地产', '建筑', '基建', '物业'],
            '通信': ['通信', '5G', '通信设备', '电信', '光通信'],
            '消费必需品': ['食品', '饮料', '农业', '食品饮料', '乳制品', '猪肉']
        }
    
    def get_north_bound_capital(self, days: int = 5, use_db_only: bool = False) -> Dict:
        """
        获取北向资金数据（沪股通+深股通）
        
        Args:
            days: 获取最近多少天的数据
            use_db_only: 是否只使用数据库数据（设置页面预测时应设为True，不调用API）
            
        Returns:
            {
                'today_net_inflow': 今日净流入（亿元）,
                'avg_net_inflow_5d': 5日平均净流入（亿元）,
                'avg_net_inflow_10d': 10日平均净流入（亿元）,
                'trend': 'inflow'/'outflow'/'neutral'
            }
        """
        try:
            # 设置页面预测：如果use_db_only=True，只从数据库获取数据
            if use_db_only:
                try:
                    from utils.db_connection import DatabaseConnection
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        db = DatabaseConnection()
                        # 从north_bound_capital表获取最新数据
                        sql = """
                            SELECT today_net_inflow, avg_net_inflow_5d, avg_net_inflow_10d, trend
                            FROM north_bound_capital
                            WHERE date = CURDATE()
                            ORDER BY timestamp DESC
                            LIMIT 1
                        """
                        result = db.execute_query(sql)
                        
                        if result and len(result) > 0:
                            record = result[0]
                            return {
                                'today_net_inflow': float(record.get('today_net_inflow', 0.0)) if record.get('today_net_inflow') is not None else 0.0,
                                'avg_net_inflow_5d': float(record.get('avg_net_inflow_5d', 0.0)) if record.get('avg_net_inflow_5d') is not None else 0.0,
                                'avg_net_inflow_10d': float(record.get('avg_net_inflow_10d', 0.0)) if record.get('avg_net_inflow_10d') is not None else 0.0,
                                'trend': record.get('trend', 'neutral')
                            }
                except Exception as e:
                    self.logger.debug(f"从数据库获取北向资金数据失败: {str(e)}")
                
                # 如果数据库没有数据，返回中性数据（设置页面预测：不做API调用）
                self.logger.debug("数据库中没有北向资金数据，且use_db_only=True，返回中性值")
                return {
                    'today_net_inflow': 0.0,
                    'avg_net_inflow_5d': 0.0,
                    'avg_net_inflow_10d': 0.0,
                    'trend': 'neutral'
                }
            
            # 尝试多种方法获取北向资金数据
            today_net = 0.0
            
            # 方法1: 使用 stock_connect_north_flow_em（使用无代理方式调用）
            try:
                # 检查方法是否存在
                if hasattr(ak, 'stock_connect_north_flow_em'):
                    north_data = _call_akshare_without_proxy(ak.stock_connect_north_flow_em, indicator="北向资金")
                else:
                    raise AttributeError("stock_connect_north_flow_em方法不存在")
                
                if north_data is not None and not north_data.empty:
                    latest = north_data.iloc[-1]
                    # 查找净流入列
                    for col in north_data.columns:
                        col_str = str(col)
                        if '净流入' in col_str or '净买入' in col_str or '当日成交净买入额' in col_str:
                            try:
                                val_str = str(latest[col])
                                # 处理不同的数值格式
                                val_str = val_str.replace('亿', '').replace('万', '').replace(',', '').strip()
                                val = float(val_str)
                                if '万' in str(latest[col]) or val < 100:  # 如果是万元单位，转换为亿元
                                    val = val / 10000
                                today_net = val
                                break
                            except Exception as e:
                                self.logger.debug(f"解析北向资金列 {col} 失败: {str(e)}")
                                
                    if today_net != 0:
                        # 计算5日和10日平均
                        avg_5d = 0.0
                        avg_10d = 0.0
                        if len(north_data) >= 5:
                            for col in north_data.columns:
                                if '净流入' in str(col) or '净买入' in str(col):
                                    try:
                                        recent_5 = north_data[col].tail(5)
                                        avg_5d = recent_5.mean()
                                        if '万' in str(col) or avg_5d < 100:
                                            avg_5d = avg_5d / 10000
                                        if len(north_data) >= 10:
                                            recent_10 = north_data[col].tail(10)
                                            avg_10d = recent_10.mean()
                                            if '万' in str(col) or avg_10d < 100:
                                                avg_10d = avg_10d / 10000
                                        break
                                    except:
                                        pass
                        
                        result = {
                            'today_net_inflow': today_net,
                            'avg_net_inflow_5d': avg_5d if avg_5d != 0 else today_net,
                            'avg_net_inflow_10d': avg_10d if avg_10d != 0 else today_net,
                            'trend': 'inflow' if today_net > 0 else 'outflow'
                        }
                        
                        # 保存到CSV
                        if self.data_storage:
                            self.data_storage.save_north_bound_capital(result)
                        
                        return result
            except Exception as e:
                self.logger.debug(f"方法1获取北向资金失败: {str(e)}")
            
            # 方法2: 尝试 stock_connect_north_sina（使用无代理方式调用）
            try:
                if hasattr(ak, 'stock_connect_north_sina'):
                    north_data = _call_akshare_without_proxy(ak.stock_connect_north_sina)
                else:
                    raise AttributeError("stock_connect_north_sina方法不存在")
                
                if north_data is not None and not north_data.empty:
                    latest = north_data.iloc[-1]
                    for col in north_data.columns:
                        col_str = str(col)
                        if '净流入' in col_str or '净买入' in col_str:
                            try:
                                val_str = str(latest[col])
                                val_str = val_str.replace('亿', '').replace('万', '').replace(',', '').strip()
                                val = float(val_str)
                                if '万' in str(latest[col]) or val < 100:
                                    val = val / 10000
                                today_net = val
                                break
                            except:
                                pass
                    
                    if today_net != 0:
                        result = {
                            'today_net_inflow': today_net,
                            'avg_net_inflow_5d': today_net,
                            'avg_net_inflow_10d': today_net,
                            'trend': 'inflow' if today_net > 0 else 'outflow'
                        }
                        
                        # 保存到CSV
                        if self.data_storage:
                            self.data_storage.save_north_bound_capital(result)
                        
                        return result
            except Exception as e:
                self.logger.debug(f"方法2获取北向资金失败: {str(e)}")
            
            # 方法3: 尝试使用Tushare接口（根据测试结果，Tushare成功）
            try:
                import tushare as ts
                from config import TUSHARE_TOKEN
                if TUSHARE_TOKEN:
                    ts.set_token(TUSHARE_TOKEN)
                    pro = ts.pro_api()
                    
                    # 使用moneyflow_hsgt接口获取沪深港通资金流向
                    today = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
                    north_data_df = pro.moneyflow_hsgt(start_date=start_date, end_date=today)
                    
                    if not north_data_df.empty:
                        # 解析最新数据
                        latest = north_data_df.iloc[-1]
                        # 查找净流入列（可能是ggt_ss, ggt_s2h等）
                        today_net = 0.0
                        for col in ['ggt_ss', 'ggt_s2h', 'hgt', 'sgt']:
                            if col in north_data_df.columns:
                                try:
                                    val = float(latest[col])
                                    # 转换为亿元（Tushare返回的单位可能是万元）
                                    if abs(val) > 10000:
                                        val = val / 10000
                                    today_net += val
                                except:
                                    pass
                        
                        if today_net != 0:
                            # 计算平均值
                            avg_5d = 0.0
                            avg_10d = 0.0
                            if len(north_data_df) >= 5:
                                for col in ['ggt_ss', 'ggt_s2h', 'hgt', 'sgt']:
                                    if col in north_data_df.columns:
                                        try:
                                            recent_5 = north_data_df[col].tail(5)
                                            avg_val = recent_5.mean()
                                            if abs(avg_val) > 10000:
                                                avg_val = avg_val / 10000
                                            avg_5d += avg_val
                                            if len(north_data_df) >= 10:
                                                recent_10 = north_data_df[col].tail(10)
                                                avg_val_10 = recent_10.mean()
                                                if abs(avg_val_10) > 10000:
                                                    avg_val_10 = avg_val_10 / 10000
                                                avg_10d += avg_val_10
                                        except:
                                            pass
                            
                            result = {
                                'today_net_inflow': today_net,
                                'avg_net_inflow_5d': avg_5d if avg_5d != 0 else today_net,
                                'avg_net_inflow_10d': avg_10d if avg_10d != 0 else today_net,
                                'trend': 'inflow' if today_net > 0 else 'outflow'
                            }
                            
                            # 保存到CSV
                            if self.data_storage:
                                self.data_storage.save_north_bound_capital(result)
                            
                            self.logger.info("使用Tushare成功获取北向资金数据")
                            return result
            except ImportError:
                self.logger.debug("Tushare未安装，跳过Tushare接口")
            except Exception as e:
                self.logger.debug(f"Tushare获取北向资金失败: {str(e)}")
            
            # 如果都失败，返回中性数据
            self.logger.warning("未能获取到北向资金数据，返回中性值")
            return {
                'today_net_inflow': 0.0,
                'avg_net_inflow_5d': 0.0,
                'avg_net_inflow_10d': 0.0,
                'trend': 'neutral'
            }
        except Exception as e:
            self.logger.warning(f"获取北向资金数据失败: {str(e)}")
            return {
                'today_net_inflow': 0.0,
                'avg_net_inflow_5d': 0.0,
                'avg_net_inflow_10d': 0.0,
                'trend': 'neutral'
            }
    
    def get_margin_trading_data(self, symbol: str, days: int = 5, use_db_only: bool = False) -> Dict:
        """
        获取融资融券数据
        
        Args:
            symbol: 股票代码
            days: 获取最近多少天的数据
            use_db_only: 是否只使用数据库数据（设置页面预测时应设为True，不调用API）
            
        Returns:
            {
                'margin_balance': 融资余额（万元）,
                'margin_change': 融资余额变化（万元）,
                'margin_change_pct': 融资余额变化百分比,
                'short_balance': 融券余额（万元）,
                'trend': 'increasing'/'decreasing'/'stable'
            }
        """
        try:
            # 设置页面预测：如果use_db_only=True，只从数据库获取数据
            if use_db_only:
                try:
                    from utils.db_connection import DatabaseConnection
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        db = DatabaseConnection()
                        # 从margin_trading表获取最新数据
                        sql = """
                            SELECT margin_balance, margin_change, margin_change_pct, short_balance, trend
                            FROM margin_trading
                            WHERE symbol = %s
                            AND date = CURDATE()
                            ORDER BY timestamp DESC
                            LIMIT 1
                        """
                        result = db.execute_query(sql, (symbol,))
                        
                        if result and len(result) > 0:
                            record = result[0]
                            return {
                                'margin_balance': float(record.get('margin_balance', 0.0)) if record.get('margin_balance') is not None else 0.0,
                                'margin_change': float(record.get('margin_change', 0.0)) if record.get('margin_change') is not None else 0.0,
                                'margin_change_pct': float(record.get('margin_change_pct', 0.0)) if record.get('margin_change_pct') is not None else 0.0,
                                'short_balance': float(record.get('short_balance', 0.0)) if record.get('short_balance') is not None else 0.0,
                                'trend': record.get('trend', 'stable')
                            }
                except Exception as e:
                    self.logger.debug(f"从数据库获取融资融券数据失败: {str(e)}")
                
                # 如果数据库没有数据，返回中性数据（设置页面预测：不做API调用）
                self.logger.debug(f"数据库中没有股票 {symbol} 的融资融券数据，且use_db_only=True，返回中性值")
                return {
                    'margin_balance': 0.0,
                    'margin_change': 0.0,
                    'margin_change_pct': 0.0,
                    'short_balance': 0.0,
                    'trend': 'stable'
                }
            
            margin_balance = 0.0
            short_balance = 0.0
            margin_change = 0.0
            margin_change_pct = 0.0
            
            # 判断是上交所还是深交所
            if symbol.startswith('6'):
                # 上交所股票（使用无代理方式调用）
                try:
                    if hasattr(ak, 'stock_margin_underlying_info_sse'):
                        # 注意：stock_margin_underlying_info_sse可能不接受symbol参数
                        # 先尝试带symbol参数，如果失败则尝试不带参数
                        try:
                            margin_data = _call_akshare_without_proxy(ak.stock_margin_underlying_info_sse, symbol=symbol)
                        except TypeError:
                            # 如果symbol参数不被支持，尝试不带参数（返回所有股票数据，然后筛选）
                            margin_data_all = _call_akshare_without_proxy(ak.stock_margin_underlying_info_sse)
                            if margin_data_all is not None and not margin_data_all.empty:
                                # 查找代码列并筛选
                                code_col = None
                                for col in margin_data_all.columns:
                                    if '代码' in str(col) or 'code' in str(col).lower() or 'symbol' in str(col).lower():
                                        code_col = col
                                        break
                                if code_col:
                                    margin_data = margin_data_all[margin_data_all[code_col].astype(str).str.contains(symbol)]
                                else:
                                    margin_data = margin_data_all
                            else:
                                margin_data = None
                    else:
                        raise AttributeError("stock_margin_underlying_info_sse方法不存在")
                    
                    if margin_data is not None and not margin_data.empty:
                        latest = margin_data.iloc[-1]
                        # 查找融资余额和融券余额列
                        for col in margin_data.columns:
                            col_str = str(col)
                            if '融资余额' in col_str:
                                try:
                                    val_str = str(latest[col]).replace(',', '').replace('万', '').replace('亿', '').strip()
                                    margin_balance = float(val_str)
                                    if '亿' in str(latest[col]):
                                        margin_balance = margin_balance * 10000
                                except:
                                    pass
                            elif '融券余额' in col_str:
                                try:
                                    val_str = str(latest[col]).replace(',', '').replace('万', '').replace('亿', '').strip()
                                    short_balance = float(val_str)
                                    if '亿' in str(latest[col]):
                                        short_balance = short_balance * 10000
                                except:
                                    pass
                        
                        # 计算变化
                        if len(margin_data) > 1:
                            for col in margin_data.columns:
                                if '融资余额' in str(col):
                                    try:
                                        prev_val_str = str(margin_data.iloc[-2][col]).replace(',', '').replace('万', '').replace('亿', '').strip()
                                        prev_margin = float(prev_val_str)
                                        if '亿' in str(margin_data.iloc[-2][col]):
                                            prev_margin = prev_margin * 10000
                                        margin_change = margin_balance - prev_margin
                                        if prev_margin > 0:
                                            margin_change_pct = (margin_change / prev_margin) * 100
                                        break
                                    except:
                                        pass
                except Exception as e:
                    self.logger.debug(f"获取上交所融资融券数据失败: {str(e)}")
                else:
                    # 深交所股票（使用无代理方式调用）
                    try:
                        if hasattr(ak, 'stock_margin_underlying_info_szse'):
                            # 注意：stock_margin_underlying_info_szse可能不接受symbol参数
                            # 尝试不同的调用方式
                            try:
                                # 方法1：尝试不带参数（返回所有股票数据，然后筛选）
                                margin_data_all = _call_akshare_without_proxy(ak.stock_margin_underlying_info_szse)
                                if margin_data_all is not None and not margin_data_all.empty:
                                    # 查找代码列并筛选
                                    code_col = None
                                    for col in margin_data_all.columns:
                                        if '代码' in str(col) or 'code' in str(col).lower() or 'symbol' in str(col).lower():
                                            code_col = col
                                            break
                                    if code_col:
                                        margin_data = margin_data_all[margin_data_all[code_col].astype(str).str.contains(symbol)]
                                    else:
                                        margin_data = margin_data_all
                            except TypeError:
                                # 方法2：如果必须带参数，尝试使用date参数
                                try:
                                    from datetime import datetime
                                    today = datetime.now().strftime('%Y%m%d')
                                    margin_data_all = _call_akshare_without_proxy(ak.stock_margin_underlying_info_szse, date=today)
                                    if margin_data_all is not None and not margin_data_all.empty:
                                        # 查找代码列并筛选
                                        code_col = None
                                        for col in margin_data_all.columns:
                                            if '代码' in str(col) or 'code' in str(col).lower() or 'symbol' in str(col).lower():
                                                code_col = col
                                                break
                                        if code_col:
                                            margin_data = margin_data_all[margin_data_all[code_col].astype(str).str.contains(symbol)]
                                        else:
                                            margin_data = margin_data_all
                                except Exception:
                                    # 方法3：如果都失败，尝试不带任何参数
                                    margin_data = None
                        else:
                            raise AttributeError("stock_margin_underlying_info_szse方法不存在")
                        
                        if margin_data is not None and not margin_data.empty:
                            latest = margin_data.iloc[-1]
                            
                            # 解析融资余额和融券余额
                            margin_balance = 0.0
                            short_balance = 0.0
                            
                            for col in margin_data.columns:
                                col_str = str(col)
                                if '融资余额' in col_str or '融资' in col_str:
                                    try:
                                        val = str(latest[col]).replace(',', '').replace('万', '').strip()
                                        margin_balance = float(val)
                                    except:
                                        pass
                                elif '融券余额' in col_str or '融券' in col_str:
                                    try:
                                        val = str(latest[col]).replace(',', '').replace('万', '').strip()
                                        short_balance = float(val)
                                    except:
                                        pass
                            
                            # 计算变化趋势（如果有历史数据）
                            if len(margin_data) > 1:
                                prev_margin = 0.0
                                for col in margin_data.columns:
                                    if '融资余额' in str(col):
                                        try:
                                            val = str(margin_data.iloc[-2][col]).replace(',', '').replace('万', '').strip()
                                            prev_margin = float(val)
                                            break
                                        except:
                                            pass
                                
                                margin_change = margin_balance - prev_margin
                                margin_change_pct = (margin_change / prev_margin * 100) if prev_margin > 0 else 0.0
                                
                                if margin_change_pct > 2:
                                    trend = 'increasing'
                                elif margin_change_pct < -2:
                                    trend = 'decreasing'
                                else:
                                    trend = 'stable'
                                
                                return {
                                    'margin_balance': margin_balance,
                                    'margin_change': margin_change,
                                    'margin_change_pct': margin_change_pct,
                                    'short_balance': short_balance,
                                    'trend': trend
                                }
                            else:
                                return {
                                    'margin_balance': margin_balance,
                                    'margin_change': 0.0,
                                    'margin_change_pct': 0.0,
                                    'short_balance': short_balance,
                                    'trend': 'stable'
                                }
                    except Exception as e:
                        self.logger.debug(f"获取深交所融资融券数据失败: {str(e)}")
            
            # 如果获取成功，返回数据
            if margin_balance > 0 or short_balance > 0:
                trend = 'increasing' if margin_change_pct > 2 else 'decreasing' if margin_change_pct < -2 else 'stable'
                result = {
                    'margin_balance': margin_balance,
                    'margin_change': margin_change,
                    'margin_change_pct': margin_change_pct,
                    'short_balance': short_balance,
                    'trend': trend
                }
                
                # 保存到CSV
                if self.data_storage:
                    self.data_storage.save_margin_trading_data(symbol, result)
                
                return result
            
            # 方法3: 尝试使用Tushare接口（根据测试结果，Tushare成功）
            try:
                import tushare as ts
                from config import TUSHARE_TOKEN
                if TUSHARE_TOKEN:
                    ts.set_token(TUSHARE_TOKEN)
                    pro = ts.pro_api()
                    
                    # 使用margin接口获取融资融券数据
                    tushare_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                    today = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
                    margin_data_df = pro.margin(ts_code=tushare_code, start_date=start_date, end_date=today)
                    
                    if not margin_data_df.empty:
                        latest = margin_data_df.iloc[-1]
                        margin_balance = float(latest.get('rzye', 0)) / 10000 if latest.get('rzye') else 0.0  # 转换为万元
                        short_balance = float(latest.get('rqye', 0)) / 10000 if latest.get('rqye') else 0.0  # 转换为万元
                        
                        # 计算变化
                        margin_change = 0.0
                        margin_change_pct = 0.0
                        if len(margin_data_df) > 1:
                            prev = margin_data_df.iloc[-2]
                            prev_margin = float(prev.get('rzye', 0)) / 10000 if prev.get('rzye') else 0.0
                            margin_change = margin_balance - prev_margin
                            if prev_margin > 0:
                                margin_change_pct = (margin_change / prev_margin) * 100
                        
                        trend = 'increasing' if margin_change_pct > 2 else 'decreasing' if margin_change_pct < -2 else 'stable'
                        
                        result = {
                            'margin_balance': margin_balance,
                            'margin_change': margin_change,
                            'margin_change_pct': margin_change_pct,
                            'short_balance': short_balance,
                            'trend': trend
                        }
                        
                        # 保存到CSV
                        if self.data_storage:
                            self.data_storage.save_margin_trading_data(symbol, result)
                        
                        self.logger.info(f"使用Tushare成功获取股票 {symbol} 的融资融券数据")
                        return result
            except ImportError:
                self.logger.debug("Tushare未安装，跳过Tushare接口")
            except Exception as e:
                self.logger.debug(f"Tushare获取融资融券数据失败: {str(e)}")
            
            # 如果获取失败，返回中性数据
            self.logger.warning(f"未能获取到股票 {symbol} 的融资融券数据，返回中性值")
            return {
                'margin_balance': 0.0,
                'margin_change': 0.0,
                'margin_change_pct': 0.0,
                'short_balance': 0.0,
                'trend': 'stable'
            }
        except Exception as e:
            self.logger.warning(f"获取融资融券数据失败: {str(e)}")
            return {
                'margin_balance': 0.0,
                'margin_change': 0.0,
                'margin_change_pct': 0.0,
                'short_balance': 0.0,
                'trend': 'stable'
            }
    
    def get_main_force_capital(self, symbol: str, days: int = 5, use_db_only: bool = False) -> Dict:
        """
        获取主力资金流向数据（大单、中单、小单）
        
        Args:
            symbol: 股票代码
            days: 获取最近多少天的数据
            use_db_only: 是否只使用数据库数据（设置页面预测时应设为True，不调用API）
            
        Returns:
            {
                'main_net_inflow': 主力资金净流入（万元）,
                'main_net_inflow_pct': 主力资金净流入百分比,
                'trend': 'inflow'/'outflow'/'neutral'
            }
        """
        try:
            # 设置页面预测：如果use_db_only=True，只从数据库获取数据
            if use_db_only:
                try:
                    from utils.db_connection import DatabaseConnection
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        db = DatabaseConnection()
                        # 从main_force_capital表获取最新数据
                        sql = """
                            SELECT main_net_inflow, main_net_inflow_pct, trend
                            FROM main_force_capital
                            WHERE symbol = %s
                            AND date = CURDATE()
                            ORDER BY timestamp DESC
                            LIMIT 1
                        """
                        result = db.execute_query(sql, (symbol,))
                        
                        if result and len(result) > 0:
                            record = result[0]
                            return {
                                'main_net_inflow': float(record.get('main_net_inflow', 0.0)) if record.get('main_net_inflow') is not None else 0.0,
                                'main_net_inflow_pct': float(record.get('main_net_inflow_pct', 0.0)) if record.get('main_net_inflow_pct') is not None else 0.0,
                                'trend': record.get('trend', 'neutral')
                            }
                except Exception as e:
                    self.logger.debug(f"从数据库获取主力资金数据失败: {str(e)}")
                
                # 如果数据库没有数据，返回中性数据（设置页面预测：不做API调用）
                self.logger.debug(f"数据库中没有股票 {symbol} 的主力资金数据，且use_db_only=True，返回中性值")
                return {
                    'main_net_inflow': 0.0,
                    'main_net_inflow_pct': 0.0,
                    'trend': 'neutral'
                }
            
            main_net = 0.0
            main_net_pct = 0.0
            
            # 方法1: 使用 stock_individual_fund_flow（使用无代理方式调用）
            try:
                capital_flow = _call_akshare_without_proxy(ak.stock_individual_fund_flow, stock=symbol, market="sh" if symbol.startswith('6') else "sz")
                if not capital_flow.empty:
                    # 解析主力资金数据
                    latest = capital_flow.iloc[-1] if len(capital_flow) > 0 else None
                    if latest is not None:
                        for col in capital_flow.columns:
                            col_str = str(col).strip()
                            try:
                                value = latest[col]
                                if pd.notna(value):
                                    # 匹配主力净流入金额
                                    if '主力' in col_str and '净流入' in col_str and '净额' in col_str and '占比' not in col_str:
                                        try:
                                            val = float(value)
                                            main_net = val
                                        except (ValueError, TypeError):
                                            val_str = str(value).replace(',', '').replace('万', '').replace('亿', '').strip()
                                            try:
                                                val = float(val_str)
                                                if '亿' in str(value):
                                                    val = val * 10000  # 转换为万元
                                                main_net = val
                                            except:
                                                pass
                                    # 匹配主力净流入占比（如果API直接提供了百分比，直接使用）
                                    elif '主力' in col_str and ('占比' in col_str or '净流入占比' in col_str):
                                        try:
                                            val = float(value)
                                            main_net_pct = val  # API返回的已经是百分比
                                        except (ValueError, TypeError):
                                            val_str = str(value).replace('%', '').replace(',', '').strip()
                                            try:
                                                main_net_pct = float(val_str)
                                            except:
                                                pass
                            except Exception:
                                continue
            except Exception as e:
                self.logger.debug(f"方法1获取主力资金失败: {str(e)}")
            
            # 方法2: 使用 stock_individual_fund_flow_rank（使用无代理方式调用）
            if main_net == 0:
                try:
                    capital_flow = _call_akshare_without_proxy(ak.stock_individual_fund_flow_rank, indicator="今日")
                    if not capital_flow.empty:
                        # 查找该股票的资金流向
                        code_col = None
                        for col in capital_flow.columns:
                            if '代码' in str(col) or 'code' in str(col).lower():
                                code_col = col
                                break
                        if code_col:
                            row = capital_flow[capital_flow[code_col].astype(str).str.contains(symbol)]
                            if not row.empty:
                                row = row.iloc[0]
                                for col in capital_flow.columns:
                                    col_str = str(col).strip()
                                    try:
                                        value = row[col]
                                        if pd.notna(value):
                                            # 匹配主力净流入金额
                                            if '主力' in col_str and '净流入' in col_str and '净额' in col_str and '占比' not in col_str:
                                                try:
                                                    val = float(value)
                                                    main_net = val
                                                except (ValueError, TypeError):
                                                    val_str = str(value).replace(',', '').replace('万', '').replace('亿', '').strip()
                                                    try:
                                                        val = float(val_str)
                                                        if '亿' in str(value):
                                                            val = val * 10000
                                                        main_net = val
                                                    except:
                                                        pass
                                            # 匹配主力净流入占比
                                            elif '主力' in col_str and ('占比' in col_str or '净流入占比' in col_str):
                                                try:
                                                    val = float(value)
                                                    main_net_pct = val
                                                except (ValueError, TypeError):
                                                    val_str = str(value).replace('%', '').replace(',', '').strip()
                                                    try:
                                                        main_net_pct = float(val_str)
                                                    except:
                                                        pass
                                    except Exception:
                                        continue
                except Exception as e:
                    self.logger.debug(f"方法2获取主力资金失败: {str(e)}")
            
            # 如果API没有提供百分比，则计算百分比
            if main_net != 0 and main_net_pct == 0:
                try:
                    # 获取股票成交额来计算百分比
                    stock_data = self.get_stock_data(symbol, days=1)
                    if not stock_data.empty:
                        current_price = stock_data['close'].iloc[-1]
                        volume = stock_data['volume'].iloc[-1]
                        turnover = current_price * volume  # 成交额（元）
                        
                        if turnover > 0:
                            # main_net单位是万元，turnover单位是元
                            main_net_pct = (main_net * 10000 / turnover) * 100  # 转换为百分比
                        else:
                            main_net_pct = 0.0
                except Exception as e:
                    self.logger.debug(f"计算主力资金百分比失败: {str(e)}")
                    main_net_pct = 0.0
            
            # 返回结果
            if main_net != 0 or main_net_pct != 0:
                result = {
                    'main_net_inflow': main_net,
                    'main_net_inflow_pct': main_net_pct,
                    'trend': 'inflow' if main_net > 0 else ('outflow' if main_net < 0 else 'neutral')
                }
                
                # 保存到CSV
                if self.data_storage:
                    self.data_storage.save_main_force_capital(symbol, result)
                
                return result
            
            # 如果获取失败，返回中性数据
            self.logger.warning(f"未能获取到股票 {symbol} 的主力资金数据，返回中性值")
            return {
                'main_net_inflow': 0.0,
                'main_net_inflow_pct': 0.0,
                'trend': 'neutral'
            }
        except Exception as e:
            self.logger.warning(f"获取主力资金数据失败: {str(e)}")
            return {
                'main_net_inflow': 0.0,
                'main_net_inflow_pct': 0.0,
                'trend': 'neutral'
            }
    
    def get_sector_performance(self, days: int = 5) -> Dict:
        """
        获取板块表现数据（行业板块和概念板块）
        
        Args:
            days: 获取最近多少天的数据
            
        Returns:
            {
                'industry_sectors': {行业名: {涨跌幅, 资金净流入, 热度}},
                'concept_sectors': {概念名: {涨跌幅, 资金净流入, 热度}},
                'hot_sectors': ['板块1', '板块2', ...]  # 热门板块列表
            }
        """
        try:
            # 抑制 pandas SettingWithCopyWarning 警告（来自 akshare 库内部）
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='.*SettingWithCopyWarning.*')
                warnings.filterwarnings('ignore', message='.*A value is trying to be set on a copy.*')
                warnings.filterwarnings('ignore', category=FutureWarning)
                
                # 获取行业板块数据（使用无代理方式调用，避免代理连接错误）
                try:
                    industry_board = _call_akshare_without_proxy(ak.stock_board_industry_name_em)
                    concept_board = _call_akshare_without_proxy(ak.stock_board_concept_name_em)
                except Exception as e:
                    self.logger.debug(f"获取板块列表失败: {str(e)}")
                    industry_board = pd.DataFrame()
                    concept_board = pd.DataFrame()
                
                industry_dict = {}
                concept_dict = {}
                
                # 处理行业板块 - 获取真实的涨跌幅数据
                if not industry_board.empty:
                    sector_list = []
                    for _, row in industry_board.head(50).iterrows():  # 取前50个行业
                        sector_name = str(row.get('板块名称', row.get('name', ''))).strip()
                        if sector_name:
                            sector_list.append(sector_name)
                    
                    # 获取板块实时行情数据（使用无代理方式调用）
                    try:
                        sector_info = _call_akshare_without_proxy(ak.stock_board_industry_name_em)
                        if not sector_info.empty:
                            for sector_name in sector_list[:30]:  # 只处理前30个，避免请求过多
                                try:
                                    # 获取板块指数数据（使用无代理方式调用）
                                    board_info = _call_akshare_without_proxy(ak.stock_board_industry_info_em, symbol=sector_name)
                                    if not board_info.empty:
                                        # 查找涨跌幅列
                                        change_pct = 0.0
                                        for col in board_info.columns:
                                            if '涨跌幅' in str(col) or '涨跌' in str(col) or 'change' in str(col).lower():
                                                try:
                                                    change_pct = float(board_info[col].iloc[-1])
                                                    break
                                                except:
                                                    pass
                                        
                                        industry_dict[sector_name] = {
                                            'change_pct': change_pct,
                                            'capital_flow': 0.0,  # 暂时无法获取
                                            'heat': 0.5 + abs(change_pct) / 10.0  # 涨跌幅越大，热度越高
                                        }
                                    else:
                                        industry_dict[sector_name] = {
                                            'change_pct': 0.0,
                                            'capital_flow': 0.0,
                                            'heat': 0.5
                                        }
                                except Exception as e:
                                    self.logger.debug(f"获取板块 {sector_name} 数据失败: {str(e)}")
                                    industry_dict[sector_name] = {
                                        'change_pct': 0.0,
                                        'capital_flow': 0.0,
                                        'heat': 0.5
                                    }
                    except Exception as e:
                        self.logger.debug(f"获取行业板块详细数据失败: {str(e)}")
                        # 使用占位数据
                        for sector_name in sector_list[:30]:
                            industry_dict[sector_name] = {
                                'change_pct': 0.0,
                                'capital_flow': 0.0,
                                'heat': 0.5
                            }
                
                # 处理概念板块 - 简化处理，使用占位数据
                if not concept_board.empty:
                    for _, row in concept_board.head(30).iterrows():  # 取前30个概念
                        sector_name = str(row.get('板块名称', row.get('name', ''))).strip()
                        if sector_name:
                            concept_dict[sector_name] = {
                                'change_pct': 0.0,
                                'capital_flow': 0.0,
                                'heat': 0.5
                            }
                
                # 识别热门板块（根据涨跌幅排序）
                hot_sectors = []
                try:
                    # 合并所有板块数据
                    all_sectors = []
                    for sector_name, sector_info in industry_dict.items():
                        all_sectors.append((sector_name, sector_info.get('change_pct', 0.0)))
                    for sector_name, sector_info in concept_dict.items():
                        all_sectors.append((sector_name, sector_info.get('change_pct', 0.0)))
                    
                    # 按涨跌幅排序，取前10名作为热门板块
                    all_sectors.sort(key=lambda x: abs(x[1]), reverse=True)
                    hot_sectors = [name for name, pct in all_sectors[:10] if abs(pct) > 1.0]  # 涨跌幅超过1%的板块
                except Exception as e:
                    self.logger.debug(f"识别热门板块失败: {str(e)}")
                    hot_sectors = []
                
                result = {
                    'industry_sectors': industry_dict,
                    'concept_sectors': concept_dict,
                    'hot_sectors': hot_sectors
                }
                
                # 保存到CSV
                if self.data_storage:
                    self.data_storage.save_sector_rotation_data(result)
                
                return result
        except Exception as e:
            self.logger.debug(f"获取板块数据失败: {str(e)}")
            return {
                'industry_sectors': {},
                'concept_sectors': {},
                'hot_sectors': []
            }

    def get_realtime_quote(self, symbol: str) -> Dict:
        """
        获取股票实时行情数据（优先从数据库获取今天的数据，如果数据库没有则从API获取）
        
        Args:
            symbol: 股票代码
            
        Returns:
            实时行情数据字典，包含：
            - current_price: 当前价格
            - open_price: 开盘价
            - high_price: 最高价
            - low_price: 最低价
            - pre_close: 昨收价
            - volume: 成交量
            - amount: 成交额
            - change_pct: 涨跌幅
            - change_amount: 涨跌额
            - bid_price: 买一价
            - ask_price: 卖一价
            - bid_volume: 买一量
            - ask_volume: 卖一量
            - turnover_rate: 换手率
            - amplitude: 振幅
            - timestamp: 数据时间戳
        """
        try:
            # 优先从数据库获取今天的数据
            today = datetime.now().strftime('%Y-%m-%d')
            try:
                from utils.stock_history_storage import StockHistoryStorage
                from config_db import USE_DATABASE
                
                if USE_DATABASE:
                    storage = StockHistoryStorage()
                    # 检查数据库中是否有今天的数据
                    today_data = storage.get_stock_history_data(
                        symbol=symbol,
                        start_date=today,
                        end_date=today,
                        limit=1,
                        period_type='daily'
                    )
                    
                    if today_data and len(today_data) > 0:
                        record = today_data[0]
                        # 从数据库数据构建实时行情数据
                        result = {
                            'symbol': symbol,
                            'current_price': float(record.get('close_price', 0)) if record.get('close_price') else None,
                            'open_price': float(record.get('open_price', 0)) if record.get('open_price') else None,
                            'high_price': float(record.get('high_price', 0)) if record.get('high_price') else None,
                            'low_price': float(record.get('low_price', 0)) if record.get('low_price') else None,
                            'pre_close': float(record.get('pre_close', 0)) if record.get('pre_close') else None,
                            'volume': float(record.get('volume', 0)) if record.get('volume') else None,
                            'amount': float(record.get('amount', 0)) if record.get('amount') else None,
                            'timestamp': record.get('trade_date', today) + ' ' + (record.get('update_time', '') or '15:00:00')
                        }
                        
                        # 计算涨跌幅和涨跌额
                        if result.get('current_price') and result.get('pre_close') and result['pre_close'] > 0:
                            result['change_amount'] = result['current_price'] - result['pre_close']
                            result['change_pct'] = (result['change_amount'] / result['pre_close']) * 100
                        
                        # 如果有成交额和成交量，计算换手率
                        if result.get('amount') and result.get('volume') and result['volume'] > 0:
                            # 换手率 = 成交额 / (成交量 * 当前价) * 100
                            if result.get('current_price') and result['current_price'] > 0:
                                result['turnover_rate'] = (result['amount'] / (result['volume'] * result['current_price'])) * 100
                        
                        # 如果有最高价和最低价，计算振幅
                        if result.get('high_price') and result.get('low_price') and result.get('pre_close') and result['pre_close'] > 0:
                            result['amplitude'] = ((result['high_price'] - result['low_price']) / result['pre_close']) * 100
                        
                        self.logger.info(f"从数据库获取 {symbol} 今天的数据（{today}）")
                        return result
                    else:
                        self.logger.debug(f"数据库中没有 {symbol} 今天的数据（{today}），将从API获取")
            except Exception as e:
                self.logger.debug(f"从数据库获取今天数据失败，将从API获取: {str(e)}")
            
            # 如果数据库没有今天的数据，从API获取实时行情
            # 使用东方财富实时行情接口
            df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
            
            if df is None or df.empty:
                self.logger.warning(f"无法获取实时行情数据")
                return {}
            
            # 查找代码列
            code_col = None
            for col in df.columns:
                if '代码' in col or 'code' in col.lower():
                    code_col = col
                    break
            
            if code_col is None:
                self.logger.warning("无法识别股票代码列")
                return {}
            
            # 筛选目标股票
            stock_data = df[df[code_col] == symbol]
            
            if stock_data.empty:
                self.logger.warning(f"未找到股票 {symbol} 的实时数据")
                return {}
            
            row = stock_data.iloc[0]
            
            # 构建结果字典
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 映射列名到标准字段
            column_mappings = {
                'current_price': ['最新价', '现价', 'price'],
                'open_price': ['今开', '开盘价', 'open'],
                'high_price': ['最高', '最高价', 'high'],
                'low_price': ['最低', '最低价', 'low'],
                'pre_close': ['昨收', '昨日收盘', 'pre_close'],
                'volume': ['成交量', 'volume'],
                'amount': ['成交额', 'amount'],
                'change_pct': ['涨跌幅', 'change_pct', 'pct_change'],
                'change_amount': ['涨跌额', 'change'],
                'turnover_rate': ['换手率', 'turnover'],
                'amplitude': ['振幅', 'amplitude'],
                'bid_price': ['买入价', '买一价', 'bid'],
                'ask_price': ['卖出价', '卖一价', 'ask'],
                'pe_ratio': ['市盈率-动态', '市盈率', 'pe'],
                'pb_ratio': ['市净率', 'pb'],
                'total_value': ['总市值', 'market_cap'],
                'float_value': ['流通市值', 'float_cap'],
                'name': ['名称', '股票名称', 'name']
            }
            
            for field, possible_cols in column_mappings.items():
                for col in possible_cols:
                    if col in df.columns:
                        try:
                            value = row[col]
                            if pd.notna(value):
                                if field in ['current_price', 'open_price', 'high_price', 'low_price', 
                                           'pre_close', 'change_amount', 'bid_price', 'ask_price']:
                                    result[field] = float(value)
                                elif field in ['volume', 'amount', 'total_value', 'float_value']:
                                    result[field] = float(value)
                                elif field in ['change_pct', 'turnover_rate', 'amplitude', 'pe_ratio', 'pb_ratio']:
                                    result[field] = float(value)
                                else:
                                    result[field] = str(value)
                        except:
                            pass
                        break
            
            # 计算额外指标
            if 'current_price' in result and 'pre_close' in result:
                if result['pre_close'] > 0:
                    # 计算涨跌幅（如果没有直接获取到）
                    if 'change_pct' not in result:
                        result['change_pct'] = round((result['current_price'] - result['pre_close']) / result['pre_close'] * 100, 2)
                    # 计算涨跌额
                    if 'change_amount' not in result:
                        result['change_amount'] = round(result['current_price'] - result['pre_close'], 2)
            
            # 计算涨停价和跌停价
            if 'pre_close' in result:
                pre_close = result['pre_close']
                # ST股票涨跌停5%，普通股票10%，科创板/创业板20%
                if symbol.startswith('688') or symbol.startswith('300'):
                    limit_pct = 0.20
                elif 'name' in result and ('ST' in result.get('name', '') or '*ST' in result.get('name', '')):
                    limit_pct = 0.05
                else:
                    limit_pct = 0.10
                
                result['limit_up'] = round(pre_close * (1 + limit_pct), 2)
                result['limit_down'] = round(pre_close * (1 - limit_pct), 2)
                result['limit_pct'] = limit_pct * 100
            
            self.logger.info(f"获取 {symbol} 实时行情成功: 当前价 {result.get('current_price', 'N/A')}, 涨跌幅 {result.get('change_pct', 'N/A')}%")
            return result
            
        except Exception as e:
            self.logger.warning(f"获取实时行情失败: {str(e)}")
            return {}

    def get_intraday_data(self, symbol: str) -> pd.DataFrame:
        """
        获取股票盘中分时数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame with columns: time, price, volume, avg_price
        """
        try:
            # 尝试多种接口获取分时数据
            df = None
            
            # 方法1: 使用 stock_zh_a_minute_em (东方财富分时数据)
            try:
                df = ak.stock_zh_a_minute_em(symbol=symbol, period='1', adjust='')
                if df is not None and not df.empty:
                    self.logger.debug(f"使用 stock_zh_a_minute_em 获取分时数据成功")
            except Exception as e1:
                self.logger.debug(f"stock_zh_a_minute_em 失败: {str(e1)}")
                # 方法2: 使用 stock_zh_a_minute (备用接口)
                try:
                    df = ak.stock_zh_a_minute(symbol=symbol, period='1', adjust='')
                    if df is not None and not df.empty:
                        self.logger.debug(f"使用 stock_zh_a_minute 获取分时数据成功")
                except Exception as e2:
                    self.logger.debug(f"stock_zh_a_minute 失败: {str(e2)}")
            
            if df is None or df.empty:
                self.logger.warning(f"无法获取 {symbol} 的分时数据")
                return pd.DataFrame()
            
            # 标准化列名
            df.columns = [col.lower() for col in df.columns]
            
            # 重命名列
            rename_map = {}
            for col in df.columns:
                if 'time' in col or '时间' in col:
                    rename_map[col] = 'time'
                elif 'close' in col or '收盘' in col or '价格' in col or 'price' in col:
                    rename_map[col] = 'price'
                elif 'volume' in col or '成交量' in col or 'vol' in col:
                    rename_map[col] = 'volume'
                elif 'avg' in col or '均价' in col:
                    rename_map[col] = 'avg_price'
            
            if rename_map:
                df = df.rename(columns=rename_map)
            
            # 确保有 price 和 volume 列
            if 'price' not in df.columns and len(df.columns) >= 2:
                df['price'] = df.iloc[:, 1]
            if 'volume' not in df.columns and len(df.columns) >= 3:
                df['volume'] = df.iloc[:, 2]
            
            self.logger.info(f"获取 {symbol} 分时数据成功，共 {len(df)} 条记录，列: {list(df.columns)}")
            return df
            
        except Exception as e:
            self.logger.warning(f"获取分时数据失败: {str(e)}")
            return pd.DataFrame()

    def get_realtime_capital_flow(self, symbol: str) -> Dict:
        """
        获取股票实时资金流向
        
        Args:
            symbol: 股票代码
            
        Returns:
            实时资金流向数据
        """
        try:
            # 优先从实时行情接口获取主力资金数据（速度快、覆盖好）
            # 注意：如果实时行情接口没有资金流向数据，会继续使用个股资金流向接口
            try:
                df_spot = ak.stock_zh_a_spot_em()
                if df_spot is not None and not df_spot.empty:
                    code_col = None
                    for col in df_spot.columns:
                        if '代码' in str(col) or str(col).lower() in ['code', 'symbol']:
                            code_col = col
                            break
                    if code_col:
                        row = df_spot[df_spot[code_col] == symbol]
                        if not row.empty:
                            row = row.iloc[0]
                            result = {
                                'symbol': symbol,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            found_data = False
                            # 主力净流入
                            main_cols = [c for c in df_spot.columns if '主力净流入' in str(c) and '占比' not in str(c)]
                            if main_cols:
                                try:
                                    main_val = row[main_cols[0]]
                                    result['main_net_inflow'] = float(str(main_val).replace(',', ''))
                                    found_data = True
                                except Exception:
                                    pass
                            # 主力净流入占比
                            pct_cols = [c for c in df_spot.columns if '主力净流入占比' in str(c) or '主力净流入占比' in str(c)]
                            if pct_cols:
                                try:
                                    pct_val = row[pct_cols[0]]
                                    result['main_net_inflow_pct'] = float(str(pct_val).replace('%', '').replace(',', ''))
                                except Exception:
                                    pass
                            
                            # 只有在找到资金流向数据时才返回，否则继续使用个股资金流向接口
                            if found_data:
                                # 计算总净流入（这里等同于主力净流入）
                                total_inflow = result.get('main_net_inflow', 0.0)
                                result['total_net_inflow'] = total_inflow
                                # 趋势判断
                                if total_inflow > 0:
                                    result['flow_trend'] = '资金净流入'
                                elif total_inflow < 0:
                                    result['flow_trend'] = '资金净流出'
                                else:
                                    result['flow_trend'] = '资金平衡'
                                return result
            except Exception as e:
                self.logger.debug(f"从实时行情获取资金流向失败: {str(e)}")

            # 回退：使用个股资金流向接口
            try:
                df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if symbol.startswith('6') else "sz")
            except Exception as e:
                self.logger.debug(f"调用 stock_individual_fund_flow 失败: {str(e)}")
                df = None

            if df is None or df.empty:
                # 尝试使用排名接口
                try:
                    df_rank = ak.stock_individual_fund_flow_rank(indicator="今日")
                    if df_rank is not None and not df_rank.empty:
                        # 查找该股票
                        code_col = None
                        for col in df_rank.columns:
                            if '代码' in str(col) or 'code' in str(col).lower():
                                code_col = col
                                break
                        if code_col:
                            row = df_rank[df_rank[code_col].astype(str).str.contains(symbol)]
                            if not row.empty:
                                df = row
                except Exception as e:
                    self.logger.debug(f"调用 stock_individual_fund_flow_rank 失败: {str(e)}")
                    pass
            
            if df is None or df.empty:
                return {}
            
            latest = df.iloc[-1] if len(df) > 0 else None
            if latest is None:
                return {}
            
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 改进列名匹配逻辑，支持多种列名格式
            for col in df.columns:
                try:
                    value = latest[col]
                    if pd.notna(value):
                        col_str = str(col).strip()
                        # 尝试转换为数值
                        try:
                            val = float(value)
                        except (ValueError, TypeError):
                            # 如果无法转换，尝试清理字符串（去掉逗号、万、亿等）
                            val_str = str(value).replace(',', '').replace('万', '').replace('亿', '').strip()
                            try:
                                val = float(val_str)
                                if '亿' in str(value):
                                    val = val * 10000  # 转换为万元
                            except:
                                continue
                        
                        # 匹配主力净流入（支持多种列名格式）
                        if ('主力' in col_str or 'main' in col_str.lower()) and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                            if 'main_net_inflow' not in result:
                                result['main_net_inflow'] = val
                        # 匹配超大单净流入
                        elif ('超大单' in col_str or 'super' in col_str.lower()) and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                            if 'super_large_net_inflow' not in result:
                                result['super_large_net_inflow'] = val
                        # 匹配大单净流入
                        elif ('大单' in col_str and '超大' not in col_str) and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                            if 'large_net_inflow' not in result:
                                result['large_net_inflow'] = val
                        # 匹配中单净流入
                        elif '中单' in col_str and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                            if 'medium_net_inflow' not in result:
                                result['medium_net_inflow'] = val
                        # 匹配小单净流入
                        elif '小单' in col_str and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                            if 'small_net_inflow' not in result:
                                result['small_net_inflow'] = val
                except Exception as e:
                    self.logger.debug(f"处理列 {col} 时出错: {str(e)}")
                    continue
            
            # 计算总净流入（包含所有类型的资金）
            total_inflow = sum([
                result.get('main_net_inflow', 0.0),
                result.get('super_large_net_inflow', 0.0),
                result.get('large_net_inflow', 0.0),
                result.get('medium_net_inflow', 0.0),
                result.get('small_net_inflow', 0.0)
            ])
            result['total_net_inflow'] = total_inflow
            
            # 趋势判断
            if total_inflow > 0:
                result['flow_trend'] = '资金净流入'
            elif total_inflow < 0:
                result['flow_trend'] = '资金净流出'
            else:
                result['flow_trend'] = '资金平衡'
            
            return result
            
        except Exception as e:
            self.logger.debug(f"获取实时资金流向失败: {str(e)}")
            return {}

    def _calculate_cost_distribution_core(self, prices, volumes, bins: int = 20) -> Dict:
        """通用成本分布计算核心逻辑"""
        try:
            if prices is None or volumes is None:
                return {'levels': [], 'top_levels': [], 'comment': '数据不足，无法计算成本分布'}
            import numpy as np
            prices = list(prices)
            volumes = list(volumes)
            if len(prices) == 0:
                return {'levels': [], 'top_levels': [], 'comment': '数据不足，无法计算成本分布'}
            
            price_min = float(min(prices))
            price_max = float(max(prices))
            if price_min <= 0 or price_max <= 0 or price_max == price_min:
                return {'levels': [], 'top_levels': [], 'comment': '价格区间异常，无法计算成本分布'}
            
            bin_edges = np.linspace(price_min, price_max, bins + 1)
            bin_volumes = np.zeros(bins)
            
            for p, v in zip(prices, volumes):
                idx = np.searchsorted(bin_edges, p, side='right') - 1
                idx = max(0, min(bins - 1, idx))
                try:
                    bin_volumes[idx] += float(v)
                except Exception:
                    continue
            
            total_volume = bin_volumes.sum()
            if total_volume <= 0:
                return {'levels': [], 'top_levels': [], 'comment': '成交量为0，无法计算成本分布'}
            
            levels = []
            for i in range(bins):
                vol = float(bin_volumes[i])
                if vol <= 0:
                    continue
                price_level = (bin_edges[i] + bin_edges[i + 1]) / 2
                pct = vol / total_volume * 100
                levels.append({
                    'price': round(float(price_level), 2),
                    'volume': vol,
                    'volume_pct': round(float(pct), 2)
                })
            
            levels.sort(key=lambda x: x['volume_pct'], reverse=True)
            top_levels = levels[:5]
            comment = "主要成本区间：" + "，".join(
                [f"{lvl['price']}元({lvl['volume_pct']}%)" for lvl in top_levels]
            ) if top_levels else "未能识别明显的成本集中区域"
            
            return {'levels': levels, 'top_levels': top_levels, 'comment': comment}
        except Exception as e:
            self.logger.warning(f"成本分布核心计算失败: {str(e)}")
            return {'levels': [], 'top_levels': [], 'comment': '计算失败'}

    def get_cost_distribution(self, symbol: str, days: int = 60, bins: int = 20) -> Dict:
        """
        计算股票的历史成本分布（最近N天日线，价位-成交量-占比）
        """
        try:
            df = self.get_stock_data(symbol, days=days)
            if df is None or df.empty:
                return {'levels': [], 'top_levels': [], 'comment': '数据不足，无法计算成本分布', 'scope': 'history'}
            
            result = self._calculate_cost_distribution_core(df['close'].values, df['volume'].values, bins=bins)
            result['scope'] = 'history'
            
            # 保存到CSV（如果启用数据存储）
            if self.data_storage and result.get('levels'):
                try:
                    self.data_storage.save_cost_distribution(
                        symbol,
                        result,
                        timestamp=datetime.now()
                    )
                except Exception as e:
                    self.logger.warning(f"保存历史成本分布数据失败: {str(e)}")
            
            return result
        except Exception as e:
            self.logger.warning(f"计算历史成本分布失败: {str(e)}")
            return {'levels': [], 'top_levels': [], 'comment': '计算失败', 'scope': 'history'}

    def get_intraday_cost_distribution(self, symbol: str, bins: int = 20) -> Dict:
        """
        计算当日分时成本分布（使用当日分时价格与成交量）
        """
        try:
            intraday_df = self.get_intraday_data(symbol)
            if intraday_df is None or intraday_df.empty:
                self.logger.debug(f"当日分时数据为空，symbol={symbol}")
                return {'levels': [], 'top_levels': [], 'comment': '当日分时数据不足，无法计算成本分布', 'scope': 'intraday'}
            
            # 尝试多种列名匹配
            price_col = None
            volume_col = None
            
            # 优先查找标准列名
            if 'price' in intraday_df.columns:
                price_col = 'price'
            elif 'close' in intraday_df.columns:
                price_col = 'close'
            else:
                # 尝试通过位置获取（第二列通常是价格）
                if len(intraday_df.columns) >= 2:
                    price_col = intraday_df.columns[1]
            
            if 'volume' in intraday_df.columns:
                volume_col = 'volume'
            else:
                # 尝试通过位置获取（第三列通常是成交量）
                if len(intraday_df.columns) >= 3:
                    volume_col = intraday_df.columns[2]
            
            if price_col is None or volume_col is None:
                self.logger.warning(f"无法识别分时数据列名，可用列: {list(intraday_df.columns)}")
                return {'levels': [], 'top_levels': [], 'comment': '分时数据列名识别失败', 'scope': 'intraday'}
            
            prices = intraday_df[price_col].values
            volumes = intraday_df[volume_col].values
            
            result = self._calculate_cost_distribution_core(prices, volumes, bins=bins)
            result['scope'] = 'intraday'
            
            if self.data_storage and result.get('levels'):
                try:
                    self.data_storage.save_cost_distribution(
                        symbol,
                        result,
                        timestamp=datetime.now()
                    )
                except Exception as e:
                    self.logger.warning(f"保存当日成本分布数据失败: {str(e)}")
            
            return result
        except Exception as e:
            self.logger.warning(f"计算当日成本分布失败: {str(e)}")
            return {'levels': [], 'top_levels': [], 'comment': '计算失败', 'scope': 'intraday'}

    def is_trading_time(self) -> Dict:
        """
        判断当前是否为交易时间
        
        Returns:
            {
                'is_trading': 是否交易时间,
                'session': 交易时段（pre_open/morning/noon_break/afternoon/closed）,
                'next_session': 下一个交易时段,
                'time_to_next': 距离下一时段的分钟数
            }
        """
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        result = {
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'weekday': weekday,
            'is_trading_day': weekday < 5  # 周一到周五
        }
        
        if weekday >= 5:
            result['is_trading'] = False
            result['session'] = 'weekend'
            result['next_session'] = 'pre_open'
            result['message'] = '周末休市'
            return result
        
        from datetime import time
        
        # 定义交易时段
        pre_open_start = time(9, 15)    # 集合竞价开始
        pre_open_end = time(9, 25)      # 集合竞价结束
        morning_start = time(9, 30)     # 上午开盘
        morning_end = time(11, 30)      # 上午收盘
        afternoon_start = time(13, 0)   # 下午开盘
        afternoon_end = time(15, 0)     # 下午收盘
        
        if current_time < pre_open_start:
            result['is_trading'] = False
            result['session'] = 'pre_market'
            result['next_session'] = 'pre_open'
            result['message'] = '盘前，等待集合竞价'
        elif pre_open_start <= current_time < pre_open_end:
            result['is_trading'] = True
            result['session'] = 'pre_open'
            result['next_session'] = 'morning'
            result['message'] = '集合竞价时段'
        elif pre_open_end <= current_time < morning_start:
            result['is_trading'] = False
            result['session'] = 'pre_open_break'
            result['next_session'] = 'morning'
            result['message'] = '竞价结束，等待开盘'
        elif morning_start <= current_time < morning_end:
            result['is_trading'] = True
            result['session'] = 'morning'
            result['next_session'] = 'noon_break'
            result['message'] = '上午交易时段'
        elif morning_end <= current_time < afternoon_start:
            result['is_trading'] = False
            result['session'] = 'noon_break'
            result['next_session'] = 'afternoon'
            result['message'] = '午间休市'
        elif afternoon_start <= current_time < afternoon_end:
            result['is_trading'] = True
            result['session'] = 'afternoon'
            result['next_session'] = 'closed'
            result['message'] = '下午交易时段'
        else:
            result['is_trading'] = False
            result['session'] = 'closed'
            result['next_session'] = 'pre_open'
            result['message'] = '已收盘'
        
        return result

    def get_bid_ask_data(self, symbol: str) -> Dict:
        """
        获取股票五档买卖盘数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            五档买卖盘数据
        """
        try:
            # 获取实时行情（包含买卖盘）
            df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
            
            if df is None or df.empty:
                return {}
            
            # 查找代码列
            code_col = None
            for col in df.columns:
                if '代码' in col:
                    code_col = col
                    break
            
            if code_col is None:
                return {}
            
            stock_data = df[df[code_col] == symbol]
            
            if stock_data.empty:
                return {}
            
            row = stock_data.iloc[0]
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'bids': [],  # 买盘
                'asks': []   # 卖盘
            }
            
            # 尝试解析买卖盘数据
            for i in range(1, 6):
                bid_price_cols = [f'买{i}价', f'买{i}', f'bid{i}_price']
                bid_vol_cols = [f'买{i}量', f'bid{i}_volume']
                ask_price_cols = [f'卖{i}价', f'卖{i}', f'ask{i}_price']
                ask_vol_cols = [f'卖{i}量', f'ask{i}_volume']
                
                bid_price = None
                bid_vol = None
                ask_price = None
                ask_vol = None
                
                for col in bid_price_cols:
                    if col in df.columns:
                        try:
                            bid_price = float(row[col])
                        except:
                            pass
                        break
                
                for col in bid_vol_cols:
                    if col in df.columns:
                        try:
                            bid_vol = float(row[col])
                        except:
                            pass
                        break
                
                for col in ask_price_cols:
                    if col in df.columns:
                        try:
                            ask_price = float(row[col])
                        except:
                            pass
                        break
                
                for col in ask_vol_cols:
                    if col in df.columns:
                        try:
                            ask_vol = float(row[col])
                        except:
                            pass
                        break
                
                if bid_price is not None:
                    result['bids'].append({'price': bid_price, 'volume': bid_vol or 0})
                if ask_price is not None:
                    result['asks'].append({'price': ask_price, 'volume': ask_vol or 0})
            
            return result
            
        except Exception as e:
            self.logger.debug(f"获取买卖盘数据失败: {str(e)}")
            return {}
    
    def get_auction_data(self, symbol: str) -> Dict:
        """
        获取集合竞价数据（9:15-9:25）
        
        Args:
            symbol: 股票代码
            
        Returns:
            集合竞价数据字典，包含：
            - auction_price: 集合竞价价格
            - auction_volume: 集合竞价成交量
            - match_volume: 匹配成交量
            - unmatch_volume: 未匹配量
            - buy_volume: 买入申报量
            - sell_volume: 卖出申报量
            - current_price: 当前价格（昨收）
            - change_pct: 涨跌幅
        """
        try:
            # 获取实时行情（包含集合竞价信息）
            realtime_quote = self.get_realtime_quote(symbol)
            if not realtime_quote:
                return {}
            
            # 尝试从akshare获取集合竞价数据
            try:
                # 使用akshare获取集合竞价数据
                df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
                if df is None or df.empty:
                    return {}
                
                # 查找代码列
                code_col = None
                for col in df.columns:
                    if '代码' in col or 'code' in col.lower():
                        code_col = col
                        break
                
                if code_col is None:
                    return {}
                
                stock_data = df[df[code_col] == symbol]
                if stock_data.empty:
                    return {}
                
                row = stock_data.iloc[0]
                
                # 尝试获取集合竞价相关字段
                auction_price = None
                auction_volume = None
                match_volume = None
                
                # 查找可能的字段名
                price_cols = ['集合竞价', '竞价', 'auction', 'pre_open']
                volume_cols = ['竞价量', '集合竞价量', 'auction_volume']
                
                for col in df.columns:
                    col_lower = col.lower()
                    if any(keyword in col for keyword in ['集合竞价', '竞价']) and '价' in col:
                        try:
                            auction_price = float(row[col])
                        except:
                            pass
                    if any(keyword in col for keyword in ['集合竞价', '竞价']) and '量' in col:
                        try:
                            auction_volume = float(row[col])
                        except:
                            pass
                
                # 如果获取不到集合竞价数据，使用当前价格作为参考
                current_price = realtime_quote.get('current_price', realtime_quote.get('pre_close', 0))
                
                result = {
                    'symbol': symbol,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'auction_price': auction_price if auction_price else current_price,
                    'auction_volume': auction_volume if auction_volume else 0,
                    'match_volume': match_volume if match_volume else 0,
                    'current_price': current_price,
                    'pre_close': realtime_quote.get('pre_close', current_price),
                    'change_pct': realtime_quote.get('change_pct', 0)
                }
                
                # 计算涨跌幅（如果集合竞价价格存在）
                if auction_price and current_price > 0:
                    result['change_pct'] = ((auction_price - current_price) / current_price) * 100
                
                return result
                
            except Exception as e:
                self.logger.debug(f"从akshare获取集合竞价数据失败: {str(e)}")
                # 降级方案：使用实时行情数据
                current_price = realtime_quote.get('current_price', realtime_quote.get('pre_close', 0))
                return {
                    'symbol': symbol,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'auction_price': current_price,
                    'auction_volume': 0,
                    'match_volume': 0,
                    'current_price': current_price,
                    'pre_close': realtime_quote.get('pre_close', current_price),
                    'change_pct': realtime_quote.get('change_pct', 0),
                    'note': '集合竞价数据不可用，使用当前价格'
                }
            
        except Exception as e:
            self.logger.debug(f"获取集合竞价数据失败: {str(e)}")
            return {}
    
    def check_suspension(self, symbol: str) -> Dict:
        """
        检测股票是否停牌
        
        Args:
            symbol: 股票代码
        
        Returns:
            停牌信息字典，包含：
            - is_suspended: 是否停牌
            - reason: 停牌原因
            - resume_date: 预计复牌时间
            - strategy: 策略建议
        """
        try:
            # 获取股票信息
            stock_info = self.get_stock_info(symbol)
            if not stock_info:
                return {'is_suspended': False}
            
            # 尝试从实时行情判断是否停牌
            # 如果无法获取实时行情或价格为0，可能是停牌
            realtime_quote = self.get_realtime_quote(symbol)
            
            # 检查股票名称中是否包含停牌相关关键词
            name = stock_info.get('name', '')
            
            # 尝试从akshare获取停牌信息
            try:
                # 使用akshare获取股票基本信息
                df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
                if df is not None and not df.empty:
                    code_col = None
                    for col in df.columns:
                        if '代码' in col or 'code' in col.lower():
                            code_col = col
                            break
                    
                    if code_col:
                        stock_data = df[df[code_col] == symbol]
                        if not stock_data.empty:
                            row = stock_data.iloc[0]
                            
                            # 检查是否有成交量（停牌股票通常成交量为0）
                            volume_cols = ['成交量', 'volume', '成交额', 'amount']
                            volume = 0
                            for col in volume_cols:
                                if col in df.columns:
                                    try:
                                        volume = float(row[col])
                                        break
                                    except:
                                        pass
                            
                            # 如果成交量为0且当前是交易时间，可能是停牌
                            if volume == 0:
                                trading_time = self.is_trading_time()
                                if trading_time.get('is_trading', False):
                                    return {
                                        'is_suspended': True,
                                        'reason': '疑似停牌（成交量为0）',
                                        'resume_date': None,
                                        'strategy': 'avoid',
                                        'message': '股票疑似停牌，成交量为0，建议避免交易'
                                    }
            except Exception as e:
                self.logger.debug(f"从akshare检查停牌信息失败: {str(e)}")
            
            # 如果实时行情不可用，且是交易时间，可能是停牌
            if not realtime_quote or not realtime_quote.get('current_price'):
                trading_time = self.is_trading_time()
                if trading_time.get('is_trading', False):
                    return {
                        'is_suspended': True,
                        'reason': '无法获取实时行情，疑似停牌',
                        'resume_date': None,
                        'strategy': 'avoid',
                        'message': '无法获取实时行情，可能是停牌，建议避免交易'
                    }
            
            return {'is_suspended': False}
            
        except Exception as e:
            self.logger.debug(f"检查停牌状态失败: {str(e)}")
            return {'is_suspended': False, 'error': str(e)}
    
    def check_st_stock(self, symbol: str) -> Dict:
        """
        检查是否为ST股票
        
        Args:
            symbol: 股票代码
        
        Returns:
            ST股票信息字典
        """
        try:
            stock_info = self.get_stock_info(symbol)
            if not stock_info:
                return {'is_st': False}
            
            name = stock_info.get('name', '')
            is_st = 'ST' in name or '*ST' in name or 'st' in name.lower()
            
            if is_st:
                return {
                    'is_st': True,
                    'risk_level': 'high',
                    'limit_pct': 0.05,  # ST股票涨跌停±5%
                    'strategy': {
                        'max_position_pct': 10.0,  # 最大仓位降低到10%
                        'min_confidence': 0.7,  # 最低置信度提高到70%
                        'stop_loss_pct': -3.0,  # 止损更严格，-3%
                    },
                    'warning': 'ST股票风险较高，建议谨慎操作'
                }
            
            return {'is_st': False}
            
        except Exception as e:
            self.logger.debug(f"检查ST股票状态失败: {str(e)}")
            return {'is_st': False, 'error': str(e)}
    
    def get_dragon_tiger_list(self, symbol: str, days: int = 5) -> Dict:
        """
        获取龙虎榜数据
        
        Args:
            symbol: 股票代码
            days: 获取最近多少天的数据
        
        Returns:
            龙虎榜数据字典
        """
        try:
            # 尝试从akshare获取龙虎榜数据
            try:
                # 获取最近几天的龙虎榜数据
                df = ak.stock_lhb_detail_em(symbol=symbol)
                if df is None or df.empty:
                    return {}
                
                # 解析龙虎榜数据
                institution_buy = 0
                institution_sell = 0
                hot_money_buy = 0
                hot_money_sell = 0
                
                # 遍历数据，分类统计
                for _, row in df.iterrows():
                    # 尝试识别机构席位和游资席位
                    # 机构席位通常包含：机构专用、基金、保险等
                    # 游资席位通常包含：营业部等
                    seat_name = str(row.get('席位名称', '') or row.get('营业部', '') or '')
                    
                    buy_amount = float(row.get('买入金额', 0) or 0)
                    sell_amount = float(row.get('卖出金额', 0) or 0)
                    
                    # 判断是机构还是游资（简化判断）
                    if any(keyword in seat_name for keyword in ['机构', '基金', '保险', '券商', 'QFII']):
                        institution_buy += buy_amount
                        institution_sell += sell_amount
                    else:
                        hot_money_buy += buy_amount
                        hot_money_sell += sell_amount
                
                return {
                    'symbol': symbol,
                    'institution_buy': institution_buy,
                    'institution_sell': institution_sell,
                    'institution_net': institution_buy - institution_sell,
                    'hot_money_buy': hot_money_buy,
                    'hot_money_sell': hot_money_sell,
                    'hot_money_net': hot_money_buy - hot_money_sell,
                    'total_buy': institution_buy + hot_money_buy,
                    'total_sell': institution_sell + hot_money_sell,
                    'total_net': (institution_buy + hot_money_buy) - (institution_sell + hot_money_sell),
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
                
            except Exception as e:
                self.logger.debug(f"从akshare获取龙虎榜数据失败: {str(e)}")
                return {}
            
        except Exception as e:
            self.logger.debug(f"获取龙虎榜数据失败: {str(e)}")
            return {}
    
    def get_market_statistics(self, use_db_only: bool = False) -> Dict:
        """
        获取市场统计数据（用于计算恐慌/贪婪指数）
        
        Args:
            use_db_only: 是否只使用数据库数据（设置页面预测时应设为True，不调用API）
        
        Returns:
            市场统计数据字典，包含：
            - total_stocks: 总股票数
            - rising_stocks: 上涨股票数
            - falling_stocks: 下跌股票数
            - flat_stocks: 平盘股票数
            - limit_up_count: 涨停股票数
            - limit_down_count: 跌停股票数
            - total_volume: 总成交量
            - avg_volume: 平均成交量（用于计算成交量比例）
        """
        try:
            # 设置页面预测：如果use_db_only=True，只从数据库获取数据
            if use_db_only:
                try:
                    from utils.db_connection import DatabaseConnection
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        db = DatabaseConnection()
                        # 从stock_history_data表获取当天的统计数据
                        today = datetime.now().strftime('%Y-%m-%d')
                        sql = """
                            SELECT 
                                COUNT(*) as total_stocks,
                                SUM(CASE WHEN change_pct > 0 THEN 1 ELSE 0 END) as rising_stocks,
                                SUM(CASE WHEN change_pct < 0 THEN 1 ELSE 0 END) as falling_stocks,
                                SUM(CASE WHEN change_pct = 0 THEN 1 ELSE 0 END) as flat_stocks,
                                SUM(CASE WHEN is_limit_up = 1 THEN 1 ELSE 0 END) as limit_up_count,
                                SUM(CASE WHEN is_limit_down = 1 THEN 1 ELSE 0 END) as limit_down_count,
                                SUM(volume) as total_volume,
                                AVG(volume) as avg_volume
                            FROM stock_history_data
                            WHERE trade_date = %s
                            AND period_type = 'daily'
                        """
                        result = db.execute_query(sql, (today,))
                        
                        if result and len(result) > 0:
                            record = result[0]
                            total_stocks = int(record.get('total_stocks', 0) or 0)
                            rising_stocks = int(record.get('rising_stocks', 0) or 0)
                            falling_stocks = int(record.get('falling_stocks', 0) or 0)
                            flat_stocks = int(record.get('flat_stocks', 0) or 0)
                            limit_up_count = int(record.get('limit_up_count', 0) or 0)
                            limit_down_count = int(record.get('limit_down_count', 0) or 0)
                            total_volume = float(record.get('total_volume', 0) or 0)
                            avg_volume = float(record.get('avg_volume', 0) or 0)
                            
                            if total_stocks > 0:
                                rising_stocks_pct = rising_stocks / total_stocks
                                falling_stocks_pct = falling_stocks / total_stocks
                            else:
                                rising_stocks_pct = 0.5
                                falling_stocks_pct = 0.5
                            
                            return {
                                'total_stocks': total_stocks,
                                'rising_stocks': rising_stocks,
                                'falling_stocks': falling_stocks,
                                'flat_stocks': flat_stocks,
                                'rising_stocks_pct': rising_stocks_pct,
                                'falling_stocks_pct': falling_stocks_pct,
                                'limit_up_count': limit_up_count,
                                'limit_down_count': limit_down_count,
                                'total_volume': total_volume,
                                'avg_volume': avg_volume,
                                'date': today
                            }
                except Exception as e:
                    self.logger.debug(f"从数据库获取市场统计数据失败: {str(e)}")
                
                # 如果数据库没有数据，返回中性数据（设置页面预测：不做API调用）
                self.logger.debug("数据库中没有市场统计数据，且use_db_only=True，返回中性值")
                return {
                    'total_stocks': 0,
                    'rising_stocks': 0,
                    'falling_stocks': 0,
                    'flat_stocks': 0,
                    'rising_stocks_pct': 0.5,
                    'falling_stocks_pct': 0.5,
                    'limit_up_count': 0,
                    'limit_down_count': 0,
                    'total_volume': 0,
                    'avg_volume': 0,
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
            
            # 如果use_db_only=False，从API获取
            # 使用akshare获取A股实时行情数据
            try:
                df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
                if df is None or df.empty:
                    return {}
                
                # 计算统计数据
                total_stocks = len(df)
                
                # 上涨、下跌、平盘股票数
                rising_stocks = 0
                falling_stocks = 0
                flat_stocks = 0
                limit_up_count = 0
                limit_down_count = 0
                
                # 总成交量
                total_volume = 0
                
                # 遍历数据统计
                for _, row in df.iterrows():
                    # 获取涨跌幅（可能是百分比形式，如"2.5"表示2.5%）
                    change_pct = 0.0
                    try:
                        change_pct_str = str(row.get('涨跌幅', 0) or row.get('涨跌幅度', 0) or 0)
                        # 移除百分号
                        change_pct_str = change_pct_str.replace('%', '').strip()
                        change_pct = float(change_pct_str) if change_pct_str else 0.0
                    except:
                        change_pct = 0.0
                    
                    # 判断涨跌
                    if change_pct > 0:
                        rising_stocks += 1
                        # 判断是否涨停（涨跌幅接近10%或20%，考虑ST股票5%）
                        if change_pct >= 9.5:  # 接近10%涨停
                            limit_up_count += 1
                    elif change_pct < 0:
                        falling_stocks += 1
                        # 判断是否跌停
                        if change_pct <= -9.5:  # 接近-10%跌停
                            limit_down_count += 1
                    else:
                        flat_stocks += 1
                    
                    # 累计成交量
                    try:
                        volume = float(row.get('成交量', 0) or row.get('volume', 0) or 0)
                        total_volume += volume
                    except:
                        pass
                
                # 计算比例
                rising_stocks_pct = rising_stocks / total_stocks if total_stocks > 0 else 0.5
                falling_stocks_pct = falling_stocks / total_stocks if total_stocks > 0 else 0.5
                
                # 计算平均成交量（用于计算成交量比例，需要与历史平均对比）
                # 这里简化处理，使用当前总成交量作为参考
                avg_volume = total_volume / total_stocks if total_stocks > 0 else 0
                
                return {
                    'total_stocks': total_stocks,
                    'rising_stocks': rising_stocks,
                    'falling_stocks': falling_stocks,
                    'flat_stocks': flat_stocks,
                    'rising_stocks_pct': rising_stocks_pct,
                    'falling_stocks_pct': falling_stocks_pct,
                    'limit_up_count': limit_up_count,
                    'limit_down_count': limit_down_count,
                    'total_volume': total_volume,
                    'avg_volume': avg_volume,
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
                
            except Exception as e:
                self.logger.debug(f"从akshare获取市场统计数据失败: {str(e)}")
                return {}
            
        except Exception as e:
            self.logger.debug(f"获取市场统计数据失败: {str(e)}")
            return {}
    
    def get_restricted_shares(self, symbol: str) -> Dict:
        """
        获取限售股解禁数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            限售股解禁数据字典，包含：
            - next_lift_date: 最近解禁日期
            - lift_volume: 解禁数量（股）
            - total_shares: 总股本（股）
            - lift_ratio: 解禁比例
            - lift_details: 解禁详情列表
        """
        try:
            # 尝试从akshare获取限售股解禁数据
            try:
                # akshare可能没有直接的限售股解禁接口，这里使用股票基本信息作为参考
                # 实际应用中，可以从其他数据源获取，如Wind、同花顺等
                
                # 方法1: 尝试使用akshare的股票基本信息（可能包含限售股信息）
                try:
                    # 获取股票基本信息
                    stock_info = self.get_stock_info(symbol)
                    total_shares = stock_info.get('total_shares', 0)  # 总股本
                    float_shares = stock_info.get('float_shares', 0)  # 流通股本
                    
                    # 计算限售股数量（总股本 - 流通股本）
                    restricted_shares = total_shares - float_shares if total_shares > 0 and float_shares > 0 else 0
                    
                    if restricted_shares > 0 and total_shares > 0:
                        restricted_ratio = restricted_shares / total_shares
                        
                        # 由于无法获取具体解禁日期，这里返回限售股信息
                        # 实际应用中，需要从专业数据源获取解禁日期
                        return {
                            'has_restricted': True,
                            'restricted_shares': restricted_shares,
                            'total_shares': total_shares,
                            'float_shares': float_shares,
                            'restricted_ratio': restricted_ratio,
                            'next_lift_date': None,  # 需要从其他数据源获取
                            'lift_volume': 0,  # 需要从其他数据源获取
                            'lift_ratio': 0,  # 需要从其他数据源获取
                            'note': '限售股数据来自股票基本信息，具体解禁日期需要从专业数据源获取'
                        }
                    else:
                        return {
                            'has_restricted': False,
                            'note': '未发现限售股或数据不足'
                        }
                        
                except Exception as e:
                    self.logger.debug(f"从股票基本信息获取限售股数据失败: {str(e)}")
                
                # 方法2: 尝试使用akshare的其他接口（如果有）
                # 注意：akshare可能没有专门的限售股解禁接口
                # 这里返回空数据，表示无法获取
                return {
                    'has_restricted': False,
                    'note': 'akshare暂不支持限售股解禁数据，需要从其他数据源获取'
                }
                
            except Exception as e:
                self.logger.debug(f"从akshare获取限售股解禁数据失败: {str(e)}")
                return {
                    'has_restricted': False,
                    'note': f'获取限售股解禁数据失败: {str(e)}'
                }
            
        except Exception as e:
            self.logger.debug(f"获取限售股解禁数据失败: {str(e)}")
            return {
                'has_restricted': False,
                'note': f'获取限售股解禁数据失败: {str(e)}'
            }
    
    def get_actual_stock_change(self, symbol: str, target_date: str, current_price: float = None) -> Dict:
        """
        获取股票在目标日期的实际价格和涨跌幅
        
        Args:
            symbol: 股票代码
            target_date: 目标日期（格式：YYYY-MM-DD）
            current_price: 预测时的价格（用于计算涨跌幅），如果为None则从数据库查询预测记录获取
        
        Returns:
            {
                'success': True/False,
                'close': 实际收盘价,
                'change_pct': 实际涨跌幅（%）,
                'direction': 实际方向（上涨/下跌/平盘）,
                'message': 错误信息（如果失败）
            }
        """
        try:
            symbol = str(symbol).zfill(6)
            
            # 优先从数据库获取历史数据
            try:
                from utils.stock_history_storage import StockHistoryStorage
                storage = StockHistoryStorage()
                
                # 查询目标日期的历史数据
                history_data = storage.get_stock_history_data(
                    symbol=symbol,
                    start_date=target_date,
                    end_date=target_date,
                    limit=1,
                    period_type='daily'
                )
                
                if history_data and len(history_data) > 0:
                    record = history_data[0]
                    actual_close = float(record.get('close_price', 0)) if record.get('close_price') else None
                    
                    if actual_close is None or actual_close <= 0:
                        return {
                            'success': False,
                            'message': f'目标日期 {target_date} 的收盘价数据不存在或无效'
                        }
                    
                    # 如果没有提供current_price，尝试从stock_predictions表获取
                    if current_price is None:
                        try:
                            from utils.db_connection import DatabaseConnection
                            sql = """
                                SELECT current_price 
                                FROM stock_predictions 
                                WHERE symbol = %s AND target_date = %s 
                                ORDER BY prediction_time DESC 
                                LIMIT 1
                            """
                            results = DatabaseConnection.execute_query(sql, (symbol, target_date))
                            if results and len(results) > 0:
                                current_price = float(results[0].get('current_price', 0)) if results[0].get('current_price') else None
                        except Exception as e:
                            self.logger.debug(f"从stock_predictions获取current_price失败: {str(e)}")
                    
                    # 如果仍然没有current_price，使用数据库中的change_pct（如果有）
                    if current_price is None or current_price <= 0:
                        # 尝试使用数据库中的change_pct字段
                        change_pct_from_db = float(record.get('change_pct', 0)) if record.get('change_pct') is not None else None
                        if change_pct_from_db is not None:
                            # 使用数据库中的涨跌幅，但需要判断方向
                            actual_change_pct = change_pct_from_db
                            if actual_change_pct > 0:
                                actual_direction = '上涨'
                            elif actual_change_pct < 0:
                                actual_direction = '下跌'
                            else:
                                actual_direction = '平盘'
                            
                            return {
                                'success': True,
                                'close': actual_close,
                                'change_pct': actual_change_pct,
                                'direction': actual_direction
                            }
                        else:
                            return {
                                'success': False,
                                'message': f'无法获取预测时的价格，无法计算涨跌幅'
                            }
                    
                    # 计算实际涨跌幅
                    actual_change_pct = ((actual_close - current_price) / current_price * 100) if current_price > 0 else 0.0
                    
                    # 判断实际方向
                    if actual_change_pct > 0.01:  # 大于0.01%算上涨
                        actual_direction = '上涨'
                    elif actual_change_pct < -0.01:  # 小于-0.01%算下跌
                        actual_direction = '下跌'
                    else:
                        actual_direction = '平盘'
                    
                    return {
                        'success': True,
                        'close': actual_close,
                        'change_pct': actual_change_pct,
                        'direction': actual_direction
                    }
                else:
                    return {
                        'success': False,
                        'message': f'目标日期 {target_date} 的历史数据不存在'
                    }
                    
            except Exception as e:
                self.logger.warning(f"从数据库获取实际股票数据失败: {str(e)}")
                # 如果数据库获取失败，尝试从API获取
                try:
                    # 使用get_stock_data方法获取数据
                    df = self.get_stock_data(symbol, start_date=target_date, end_date=target_date)
                    
                    if df is not None and not df.empty:
                        # 查找目标日期的数据
                        target_date_obj = pd.to_datetime(target_date)
                        if target_date_obj in df.index:
                            row = df.loc[target_date_obj]
                            actual_close = float(row.get('close', 0)) if pd.notna(row.get('close')) else None
                            
                            if actual_close is None or actual_close <= 0:
                                return {
                                    'success': False,
                                    'message': f'目标日期 {target_date} 的收盘价数据无效'
                                }
                            
                            # 如果没有提供current_price，尝试从stock_predictions表获取
                            if current_price is None:
                                try:
                                    from utils.db_connection import DatabaseConnection
                                    sql = """
                                        SELECT current_price 
                                        FROM stock_predictions 
                                        WHERE symbol = %s AND target_date = %s 
                                        ORDER BY prediction_time DESC 
                                        LIMIT 1
                                    """
                                    results = DatabaseConnection.execute_query(sql, (symbol, target_date))
                                    if results and len(results) > 0:
                                        current_price = float(results[0].get('current_price', 0)) if results[0].get('current_price') else None
                                except Exception:
                                    pass
                            
                            if current_price is None or current_price <= 0:
                                return {
                                    'success': False,
                                    'message': f'无法获取预测时的价格，无法计算涨跌幅'
                                }
                            
                            # 计算实际涨跌幅
                            actual_change_pct = ((actual_close - current_price) / current_price * 100) if current_price > 0 else 0.0
                            
                            # 判断实际方向
                            if actual_change_pct > 0.01:
                                actual_direction = '上涨'
                            elif actual_change_pct < -0.01:
                                actual_direction = '下跌'
                            else:
                                actual_direction = '平盘'
                            
                            return {
                                'success': True,
                                'close': actual_close,
                                'change_pct': actual_change_pct,
                                'direction': actual_direction
                            }
                        else:
                            return {
                                'success': False,
                                'message': f'目标日期 {target_date} 的数据不存在'
                            }
                    else:
                        return {
                            'success': False,
                            'message': f'无法获取目标日期 {target_date} 的股票数据'
                        }
                except Exception as api_error:
                    self.logger.warning(f"从API获取实际股票数据失败: {str(api_error)}")
                    return {
                        'success': False,
                        'message': f'获取实际股票数据失败: {str(api_error)}'
                    }
        
        except Exception as e:
            self.logger.error(f"获取实际股票变化数据失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'获取实际股票变化数据失败: {str(e)}'
            }


