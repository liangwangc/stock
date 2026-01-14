"""
akshare数据源实现
"""
import akshare as ak
import pandas as pd
from datetime import datetime
from typing import Optional
from .base_source import BaseDataSource
from utils.logger import get_logger

logger = get_logger(__name__)

class AkshareDataSource(BaseDataSource):
    """使用akshare获取A股数据"""
    
    def __init__(self):
        self.logger = logger
        
    def _convert_code(self, symbol: str) -> str:
        """转换股票代码格式"""
        # 将代码转换为akshare需要的格式
        if symbol.startswith('6'):
            return f"sh{symbol}"  # 上海
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"sz{symbol}"  # 深圳
        else:
            return symbol
    
    def _format_date(self, date_str: str) -> str:
        """格式化日期"""
        try:
            # 支持多种日期格式
            if len(date_str) == 8:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return date_str
        except:
            return date_str
    
    def get_stock_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> pd.DataFrame:
        """
        获取股票数据
        
        Args:
            symbol: 股票代码（如：000001）
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）
            period: 周期（daily, weekly, monthly）
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            self.logger.info(f"正在获取 {symbol} 的数据: {start_date} 至 {end_date}")
            
            # 格式化日期
            start = self._format_date(start_date)
            end = self._format_date(end_date)
            
            # 转换代码格式
            code = self._convert_code(symbol)
            
            # 获取数据
            # 使用股票历史行情数据接口
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                self.logger.warning(f"未获取到 {symbol} 的数据")
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
                '成交量': 'volume',
                '成交额': 'amount'
            }
            
            # 找到匹配的列
            rename_dict = {}
            for old_col, new_col in column_mapping.items():
                for col in df.columns:
                    if old_col in col:
                        rename_dict[col] = new_col
                        break
            
            df = df.rename(columns=rename_dict)
            
            # 确保包含必要的列
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                # 尝试其他可能的列名
                self.logger.warning(f"数据列名不匹配: {df.columns.tolist()}")
                # 使用默认列名（如果akshare返回的格式不同）
                if '日期' in df.columns:
                    df['date'] = df['日期']
                if '开盘' in df.columns:
                    df['open'] = df['开盘']
                if '收盘' in df.columns:
                    df['close'] = df['收盘']
                if '最高' in df.columns:
                    df['high'] = df['最高']
                if '最低' in df.columns:
                    df['low'] = df['最低']
                if '成交量' in df.columns:
                    df['volume'] = df['成交量']
            
            # 选择需要的列
            df = df[required_cols].copy()
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.sort_index()
            
            # 确保数据类型正确
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 删除缺失值
            df = df.dropna()
            
            self.logger.info(f"成功获取 {symbol} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表
        
        Returns:
            DataFrame with columns: code, name
        """
        try:
            self.logger.info("正在获取股票列表...")
            # 获取沪深A股列表
            df = ak.stock_info_a_code_name()
            df.columns = ['code', 'name']
            self.logger.info(f"成功获取 {len(df)} 只股票信息")
            return df
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return pd.DataFrame()

