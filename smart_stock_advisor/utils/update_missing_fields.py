"""
批量更新已有数据的缺失字段
用于计算和更新数据库中已有数据但缺失的字段（如技术指标等）
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_storage import StockHistoryStorage
from data_source.stock_data_source import StockDataSource

logger = get_logger(__name__)


class MissingFieldsUpdater:
    """缺失字段更新器"""
    
    def __init__(self):
        self.storage = StockHistoryStorage()
        self.data_source = StockDataSource()
        self.logger = logger
    
    def update_missing_fields_for_symbol(self, symbol: str, start_date: str = None, 
                                        end_date: str = None, fields: List[str] = None) -> Dict:
        """
        更新单只股票的缺失字段
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（格式：YYYY-MM-DD），如果为None则从最早数据开始
            end_date: 结束日期（格式：YYYY-MM-DD），如果为None则到最新数据
            fields: 要更新的字段列表，如果为None则更新所有可计算的字段
        
        Returns:
            更新结果字典
        """
        try:
            self.logger.info(f"开始更新 {symbol} 的缺失字段...")
            
            # 获取已有数据
            existing_data = self.storage.get_stock_history_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=None
            )
            
            if not existing_data:
                self.logger.warning(f"{symbol} 没有数据，跳过")
                return {
                    'symbol': symbol,
                    'updated_count': 0,
                    'skipped_count': 0,
                    'error_count': 0
                }
            
            # 转换为DataFrame以便计算
            df_data = []
            for record in existing_data:
                df_data.append({
                    'trade_date': record.get('trade_date'),
                    'open_price': record.get('open_price'),
                    'close_price': record.get('close_price'),
                    'high_price': record.get('high_price'),
                    'low_price': record.get('low_price'),
                    'volume': record.get('volume'),
                    'pre_close': record.get('pre_close'),
                    'amplitude': record.get('amplitude'),
                    'price_range': record.get('price_range'),
                    'ma5': record.get('ma5'),
                    'ma10': record.get('ma10'),
                    'ma20': record.get('ma20'),
                    'ma60': record.get('ma60'),
                    'rsi': record.get('rsi'),
                    'macd': record.get('macd'),
                    'macd_signal': record.get('macd_signal'),
                    'macd_hist': record.get('macd_hist'),
                    'x2': record.get('x2'),
                    'volume_ratio': record.get('volume_ratio'),
                    'amount': record.get('amount'),
                    'turnover_rate': record.get('turnover_rate'),
                })
            
            df = pd.DataFrame(df_data)
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            df = df.set_index('trade_date')
            
            # 确定要更新的字段
            if fields is None:
                fields = ['amplitude', 'price_range', 'ma5', 'ma10', 'ma20', 'ma60', 
                          'rsi', 'macd', 'macd_signal', 'macd_hist', 'x2', 'volume_ratio',
                          'amount', 'turnover_rate']  # 添加成交额和换手率
            
            updated_count = 0
            skipped_count = 0
            error_count = 0
            
            # 计算缺失字段
            for field in fields:
                try:
                    # 检查字段是否缺失
                    missing_mask = df[field].isna() if field in df.columns else pd.Series([True] * len(df), index=df.index)
                    
                    if not missing_mask.any():
                        self.logger.debug(f"{symbol} {field} 字段已完整，跳过")
                        continue
                    
                    # 根据字段类型计算
                    if field == 'amplitude':
                        # 振幅 = (最高价 - 最低价) / 昨收价 * 100
                        if 'pre_close' in df.columns:
                            df.loc[missing_mask, 'amplitude'] = (
                                (df.loc[missing_mask, 'high_price'] - df.loc[missing_mask, 'low_price']) / 
                                df.loc[missing_mask, 'pre_close'] * 100
                            ).round(2)
                    
                    elif field == 'price_range':
                        # 价格区间 = 最高价 - 最低价
                        df.loc[missing_mask, 'price_range'] = (
                            df.loc[missing_mask, 'high_price'] - df.loc[missing_mask, 'low_price']
                        )
                    
                    elif field in ['ma5', 'ma10', 'ma20', 'ma60']:
                        # 移动平均线
                        period = int(field.replace('ma', ''))
                        if 'close_price' in df.columns:
                            ma_values = df['close_price'].rolling(window=period, min_periods=1).mean()
                            df.loc[missing_mask, field] = ma_values.loc[missing_mask]
                    
                    elif field == 'rsi':
                        # RSI指标
                        if 'close_price' in df.columns and len(df) >= 14:
                            closes = df['close_price']
                            delta = closes.diff()
                            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
                            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
                            rs = gain / loss
                            rsi_values = 100 - (100 / (1 + rs))
                            df.loc[missing_mask, 'rsi'] = rsi_values.loc[missing_mask]
                    
                    elif field in ['macd', 'macd_signal', 'macd_hist']:
                        # MACD指标
                        if 'close_price' in df.columns and len(df) >= 26:
                            closes = df['close_price']
                            ema12 = closes.ewm(span=12, adjust=False).mean()
                            ema26 = closes.ewm(span=26, adjust=False).mean()
                            macd_values = ema12 - ema26
                            signal_values = macd_values.ewm(span=9, adjust=False).mean()
                            hist_values = macd_values - signal_values
                            
                            if field == 'macd':
                                df.loc[missing_mask, 'macd'] = macd_values.loc[missing_mask]
                            elif field == 'macd_signal':
                                df.loc[missing_mask, 'macd_signal'] = signal_values.loc[missing_mask]
                            elif field == 'macd_hist':
                                df.loc[missing_mask, 'macd_hist'] = hist_values.loc[missing_mask]
                    
                    elif field == 'x2':
                        # X2指标
                        if 'close_price' in df.columns and 'high_price' in df.columns and 'low_price' in df.columns and len(df) >= 20:
                            closes = df['close_price']
                            highs = df['high_price']
                            lows = df['low_price']
                            llv_low = lows.rolling(window=20, min_periods=1).min()
                            hhv_high = highs.rolling(window=20, min_periods=1).max()
                            range_width = hhv_high - llv_low
                            
                            for idx in df.index[missing_mask]:
                                if range_width.loc[idx] > 0:
                                    x2_value = (closes.loc[idx] - llv_low.loc[idx]) / range_width.loc[idx] * 100
                                    df.loc[idx, 'x2'] = round(x2_value, 4)
                                else:
                                    df.loc[idx, 'x2'] = 50.0
                    
                    elif field == 'volume_ratio':
                        # 量比
                        if 'volume' in df.columns and len(df) >= 5:
                            volumes = df['volume']
                            avg_volume = volumes.rolling(window=5, min_periods=1).mean()
                            volume_ratio_values = volumes / avg_volume
                            df.loc[missing_mask, 'volume_ratio'] = volume_ratio_values.loc[missing_mask]
                    
                    elif field == 'amount':
                        # 成交额 = 收盘价 * 成交量（手转股：1手=100股）
                        if 'close_price' in df.columns and 'volume' in df.columns:
                            df.loc[missing_mask, 'amount'] = (
                                df.loc[missing_mask, 'close_price'] * 
                                df.loc[missing_mask, 'volume'] * 100
                            )
                    
                    elif field == 'turnover_rate':
                        # 换手率需要流通股本数据，历史数据通常不可用
                        # 这里保持为NULL，如果需要可以从API获取
                        # 换手率 = 成交量 / 流通股本 * 100
                        # 注意：流通股本数据通常不可用，所以换手率保持为NULL
                        pass
                    
                    # 统计更新的数量
                    updated_count += missing_mask.sum()
                    
                except Exception as e:
                    self.logger.error(f"{symbol} 计算 {field} 字段失败: {str(e)}")
                    error_count += 1
            
            # 批量更新数据库
            update_count = 0
            for idx, row in df.iterrows():
                try:
                    # 构建更新数据
                    update_data = {}
                    for field in fields:
                        if field in df.columns and pd.notna(row[field]):
                            update_data[field] = row[field]
                    
                    if update_data:
                        # 更新数据库
                        date_str = idx.strftime('%Y-%m-%d')
                        if self.storage.update_stock_daily_data(symbol, date_str, update_data):
                            update_count += 1
                        else:
                            error_count += 1
                except Exception as e:
                    self.logger.error(f"{symbol} {idx} 更新失败: {str(e)}")
                    error_count += 1
            
            result = {
                'symbol': symbol,
                'updated_count': update_count,
                'skipped_count': skipped_count,
                'error_count': error_count
            }
            
            self.logger.info(f"{symbol} 缺失字段更新完成: 更新 {update_count} 条，错误 {error_count} 条")
            
            return result
            
        except Exception as e:
            self.logger.error(f"更新 {symbol} 缺失字段失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'symbol': symbol,
                'updated_count': 0,
                'skipped_count': 0,
                'error_count': 1
            }
    
    def batch_update_missing_fields(self, symbols: List[str] = None, 
                                   start_date: str = None, end_date: str = None,
                                   fields: List[str] = None) -> Dict:
        """
        批量更新多只股票的缺失字段
        
        Args:
            symbols: 股票代码列表，如果为None则更新所有股票
            start_date: 开始日期
            end_date: 结束日期
            fields: 要更新的字段列表
        
        Returns:
            批量更新结果字典
        """
        try:
            if symbols is None:
                # 获取所有股票代码
                sql = "SELECT DISTINCT symbol FROM stock_history_data"
                results = self.storage.db.execute_query(sql)
                symbols = [r['symbol'] for r in results]
            
            self.logger.info(f"开始批量更新 {len(symbols)} 只股票的缺失字段...")
            
            total_updated = 0
            total_errors = 0
            
            for i, symbol in enumerate(symbols, 1):
                try:
                    result = self.update_missing_fields_for_symbol(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        fields=fields
                    )
                    
                    total_updated += result.get('updated_count', 0)
                    total_errors += result.get('error_count', 0)
                    
                    if i % 10 == 0:
                        self.logger.info(f"进度: {i}/{len(symbols)}, 已更新 {total_updated} 条记录")
                        
                except Exception as e:
                    self.logger.error(f"更新 {symbol} 失败: {str(e)}")
                    total_errors += 1
            
            return {
                'total_symbols': len(symbols),
                'total_updated': total_updated,
                'total_errors': total_errors
            }
            
        except Exception as e:
            self.logger.error(f"批量更新缺失字段失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'total_symbols': 0,
                'total_updated': 0,
                'total_errors': 1
            }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='批量更新已有数据的缺失字段')
    parser.add_argument('--symbol', type=str, help='股票代码（单只股票）')
    parser.add_argument('--symbols', type=str, nargs='+', help='股票代码列表（多只股票）')
    parser.add_argument('--start-date', type=str, help='开始日期（YYYY-MM-DD）')
    parser.add_argument('--end-date', type=str, help='结束日期（YYYY-MM-DD）')
    parser.add_argument('--fields', type=str, nargs='+', 
                       help='要更新的字段列表（如：ma5 ma10 rsi macd）')
    parser.add_argument('--all', action='store_true', help='更新所有股票')
    
    args = parser.parse_args()
    
    updater = MissingFieldsUpdater()
    
    if args.symbol:
        # 更新单只股票
        result = updater.update_missing_fields_for_symbol(
            symbol=args.symbol,
            start_date=args.start_date,
            end_date=args.end_date,
            fields=args.fields
        )
        print(f"更新完成: {result}")
    elif args.symbols:
        # 更新多只股票
        for symbol in args.symbols:
            result = updater.update_missing_fields_for_symbol(
                symbol=symbol,
                start_date=args.start_date,
                end_date=args.end_date,
                fields=args.fields
            )
            print(f"{symbol}: {result}")
    elif args.all:
        # 更新所有股票
        result = updater.batch_update_missing_fields(
            start_date=args.start_date,
            end_date=args.end_date,
            fields=args.fields
        )
        print(f"批量更新完成: {result}")
    else:
        print("请指定 --symbol、--symbols 或 --all 参数")
