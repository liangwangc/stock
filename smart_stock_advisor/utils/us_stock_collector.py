"""
美股数据收集器
用于批量收集美股历史数据（10年）
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.us_stock_storage import USStockStorage
from data_source.us_stock_data_source import USStockDataSource

logger = get_logger(__name__)


class USStockCollector:
    """美股数据收集器"""
    
    def __init__(self):
        self.data_source = USStockDataSource()
        self.storage = USStockStorage()
        self.logger = logger
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if df.empty or len(df) < 2:
            return df
        
        df = df.copy()
        
        # 移动平均线
        df['ma5'] = df['close'].rolling(window=5, min_periods=1).mean()
        df['ma10'] = df['close'].rolling(window=10, min_periods=1).mean()
        df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['ma50'] = df['close'].rolling(window=50, min_periods=1).mean()
        df['ma200'] = df['close'].rolling(window=200, min_periods=1).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 振幅
        df['amplitude'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # 价格区间
        df['price_range'] = df['high'] - df['low']
        
        # 波动率（20日标准差）
        df['volatility'] = df['close'].rolling(window=20, min_periods=1).std() / df['close'] * 100
        
        # X_2指标（收盘价在20日价格区间中的相对位置）
        period = 20
        llv_low = df['low'].rolling(window=period, min_periods=1).min()
        hhv_high = df['high'].rolling(window=period, min_periods=1).max()
        range_width = hhv_high - llv_low
        df['x2'] = np.where(
            range_width > 0,
            (df['close'] - llv_low) / range_width * 100,
            50  # 如果区间宽度为0（价格没有波动），设置为50（中间位置）
        )
        
        return df
    
    def collect_stock_history(self, symbol: str, start_date: str = None, 
                             end_date: str = None, period: str = "10y",
                             update_existing: bool = False) -> Dict:
        """
        收集单只股票的历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            period: 时间周期（如果start_date和end_date为None时使用）
            update_existing: 是否更新已存在的数据
        
        Returns:
            收集结果字典
        """
        try:
            self.logger.info(f"开始收集 {symbol} 的历史数据...")
            
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
            
            # 获取已存在的日期（用于增量更新）
            existing_dates = []
            if not update_existing:
                existing_dates = set(self.storage.get_existing_dates(symbol, start_date, end_date))
            
            # 获取股票基本信息
            stock_info = self.data_source.get_stock_info(symbol)
            if stock_info:
                # 保存股票基本信息
                self.storage.save_stock_info(stock_info)
                
                # 保存板块和行业映射关系
                if stock_info.get('sector_code'):
                    self.storage.save_sector_stock_map(
                        symbol=symbol,
                        sector_code=stock_info['sector_code'],
                        sector_name=stock_info.get('sector')
                    )
                
                if stock_info.get('industry_code'):
                    self.storage.save_industry_stock_map(
                        symbol=symbol,
                        industry_code=stock_info['industry_code'],
                        industry_name=stock_info.get('industry')
                    )
                elif stock_info.get('industry'):
                    # 如果没有industry_code但有industry名称，尝试创建或查找
                    industry_code = self.storage.create_or_get_industry(
                        industry_name=stock_info['industry'],
                        sector_code=stock_info.get('sector_code')
                    )
                    if industry_code:
                        self.storage.save_industry_stock_map(
                            symbol=symbol,
                            industry_code=industry_code,
                            industry_name=stock_info['industry']
                        )
            
            # 获取历史数据
            df = self.data_source.get_stock_data(symbol, start_date, end_date, period)
            
            if df.empty:
                return {
                    'success': False,
                    'message': f'未获取到 {symbol} 的数据',
                    'count': 0
                }
            
            # 计算技术指标
            df = self.calculate_technical_indicators(df)
            
            # 保存每日数据
            success_count = 0
            fail_count = 0
            
            for idx, row in df.iterrows():
                trade_date = idx.strftime('%Y-%m-%d') if isinstance(idx, pd.Timestamp) else str(idx)
                
                # 如果已存在且不更新，则跳过
                if trade_date in existing_dates:
                    continue
                
                # 准备数据
                data = {
                    'name': stock_info.get('name_en') if stock_info else symbol,
                    'period_type': 'daily',  # 默认为日线数据
                    'exchange': stock_info.get('exchange') if stock_info else None,
                    'open_price': float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
                    'close_price': float(row.get('close', 0)) if pd.notna(row.get('close')) else None,
                    'high_price': float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
                    'low_price': float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
                    'adj_close_price': float(row.get('adj_close', 0)) if pd.notna(row.get('adj_close')) else None,
                    'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
                    'ma5': float(row.get('ma5', 0)) if pd.notna(row.get('ma5')) else None,
                    'ma10': float(row.get('ma10', 0)) if pd.notna(row.get('ma10')) else None,
                    'ma20': float(row.get('ma20', 0)) if pd.notna(row.get('ma20')) else None,
                    'ma50': float(row.get('ma50', 0)) if pd.notna(row.get('ma50')) else None,
                    'ma200': float(row.get('ma200', 0)) if pd.notna(row.get('ma200')) else None,
                    'rsi': float(row.get('rsi', 0)) if pd.notna(row.get('rsi')) else None,
                    'macd': float(row.get('macd', 0)) if pd.notna(row.get('macd')) else None,
                    'macd_signal': float(row.get('macd_signal', 0)) if pd.notna(row.get('macd_signal')) else None,
                    'macd_hist': float(row.get('macd_hist', 0)) if pd.notna(row.get('macd_hist')) else None,
                    'amplitude': float(row.get('amplitude', 0)) if pd.notna(row.get('amplitude')) else None,
                    'price_range': float(row.get('price_range', 0)) if pd.notna(row.get('price_range')) else None,
                    'volatility': float(row.get('volatility', 0)) if pd.notna(row.get('volatility')) else None,
                    'data_source': 'yfinance',
                    'data_quality_score': 1.0,
                    'is_valid': 1
                }
                
                # 计算涨跌幅（如果有前一天的数据）
                if len(df) > 1:
                    prev_idx = df.index.get_indexer([idx], method='pad')[0]
                    if prev_idx >= 0:
                        prev_close = df.iloc[prev_idx].get('close')
                        if pd.notna(prev_close) and pd.notna(data['close_price']):
                            data['pre_close'] = float(prev_close)
                            data['change_amount'] = data['close_price'] - data['pre_close']
                            data['change_pct'] = (data['change_amount'] / data['pre_close']) * 100 if data['pre_close'] > 0 else 0
                
                # 保存数据
                if self.storage.save_stock_history(symbol, trade_date, data):
                    success_count += 1
                else:
                    fail_count += 1
                
                # 避免请求过快
                if success_count % 100 == 0:
                    time.sleep(0.1)
            
            result = {
                'success': True,
                'message': f'收集完成：成功 {success_count}，失败 {fail_count}',
                'count': success_count,
                'fail_count': fail_count
            }
            
            self.logger.info(f"{symbol} 数据收集完成: {result['message']}")
            return result
            
        except Exception as e:
            self.logger.error(f"收集 {symbol} 数据失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'收集失败: {str(e)}',
                'count': 0
            }
    
    def collect_batch_stocks(self, symbols: List[str], start_date: str = None,
                            end_date: str = None, period: str = "10y",
                            delay: float = 0.5) -> Dict:
        """
        批量收集多只股票的历史数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 时间周期
            delay: 每只股票之间的延迟（秒）
        
        Returns:
            批量收集结果
        """
        total_count = len(symbols)
        success_list = []
        fail_list = []
        
        self.logger.info(f"开始批量收集 {total_count} 只股票的历史数据...")
        
        for i, symbol in enumerate(symbols, 1):
            self.logger.info(f"[{i}/{total_count}] 正在收集 {symbol}...")
            
            result = self.collect_stock_history(symbol, start_date, end_date, period)
            
            if result.get('success'):
                success_list.append(symbol)
            else:
                fail_list.append(symbol)
            
            # 延迟，避免请求过快
            if i < total_count:
                time.sleep(delay)
        
        return {
            'total': total_count,
            'success_count': len(success_list),
            'fail_count': len(fail_list),
            'success_list': success_list,
            'fail_list': fail_list
        }
    
    def initialize_gics_sectors(self):
        """初始化GICS板块数据"""
        self.logger.info("开始初始化GICS板块数据...")
        
        sectors = self.data_source.gics_sectors
        success_count = 0
        
        for sector_code, sector_info in sectors.items():
            if self.storage.save_sector_info(
                sector_code=sector_code,
                sector_name_en=sector_info['name_en'],
                sector_name_cn=sector_info['name_cn']
            ):
                success_count += 1
        
        self.logger.info(f"GICS板块初始化完成，成功 {success_count}/{len(sectors)}")
        return success_count == len(sectors)
