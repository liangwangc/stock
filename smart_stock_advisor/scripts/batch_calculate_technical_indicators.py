"""
批量计算技术指标脚本

功能：
- 扫描数据库中缺失技术指标的历史数据
- 批量计算技术指标（MA、RSI、MACD、X2、量比等）
- 更新数据库中的技术指标字段

使用方法：
    # 计算单只股票的技术指标
    python scripts/batch_calculate_technical_indicators.py --symbol 000001
    
    # 批量计算所有股票的技术指标
    python scripts/batch_calculate_technical_indicators.py --all
    
    # 批量计算指定股票列表的技术指标
    python scripts/batch_calculate_technical_indicators.py --symbols 000001,600519,000002
    
    # 计算指定日期范围的数据
    python scripts/batch_calculate_technical_indicators.py --all --start-date 2024-01-01 --end-date 2024-12-31
    
    # 多线程模式（推荐）
    python scripts/batch_calculate_technical_indicators.py --all --threads 5
"""
import os
import sys
import argparse
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_storage import StockHistoryStorage
from data_source.stock_data_source import StockDataSource

logger = get_logger(__name__)


class TechnicalIndicatorsCalculator:
    """技术指标批量计算器"""
    
    def __init__(self, max_workers: int = 1):
        """
        初始化技术指标计算器
        
        Args:
            max_workers: 最大线程数（默认1，单线程模式）
        """
        self.storage = StockHistoryStorage()
        self.data_source = StockDataSource()
        self.logger = logger
        self.max_workers = max_workers
        self.progress_lock = threading.Lock()
        
    def scan_missing_indicators(self, symbols: Optional[List[str]] = None, 
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> Dict[str, List[str]]:
        """
        扫描缺失技术指标的股票和日期
        
        Args:
            symbols: 股票代码列表，如果为None则扫描所有股票
            start_date: 开始日期（格式：YYYY-MM-DD），如果为None则从最早数据开始
            end_date: 结束日期（格式：YYYY-MM-DD），如果为None则到最新数据
        
        Returns:
            字典，key为股票代码，value为缺失技术指标的日期列表
        """
        try:
            self.logger.info("开始扫描缺失技术指标的数据...")
            
            # 如果没有指定股票列表，获取所有股票
            if symbols is None:
                symbols = self._get_all_symbols()
            
            missing_dict = {}
            
            for symbol in symbols:
                try:
                    # 获取该股票的历史数据
                    existing_data = self.storage.get_stock_history_data(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        limit=None
                    )
                    
                    if not existing_data:
                        continue
                    
                    # 找出缺失技术指标的日期
                    missing_dates = []
                    for record in existing_data:
                        trade_date = record.get('trade_date')
                        if isinstance(trade_date, datetime):
                            trade_date = trade_date.strftime('%Y-%m-%d')
                        elif isinstance(trade_date, str):
                            trade_date = trade_date.split()[0]
                        
                        # 检查技术指标字段是否为空
                        # 只要有一个主要指标缺失，就标记为缺失
                        ma5 = record.get('ma5')
                        rsi = record.get('rsi')
                        macd = record.get('macd')
                        
                        if ma5 is None and rsi is None and macd is None:
                            missing_dates.append(trade_date)
                    
                    if missing_dates:
                        missing_dict[symbol] = missing_dates
                        self.logger.debug(f"{symbol}: 缺失 {len(missing_dates)} 天的技术指标")
                
                except Exception as e:
                    self.logger.warning(f"扫描 {symbol} 失败: {str(e)}")
                    continue
            
            total_missing = sum(len(dates) for dates in missing_dict.values())
            self.logger.info(f"扫描完成：{len(missing_dict)} 只股票，共 {total_missing} 天缺失技术指标")
            
            return missing_dict
            
        except Exception as e:
            self.logger.error(f"扫描缺失技术指标失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    def _get_all_symbols(self) -> List[str]:
        """获取所有股票代码列表"""
        try:
            sql = "SELECT DISTINCT symbol FROM stock_history_data ORDER BY symbol"
            results = self.storage.db.execute_query(sql)
            return [row['symbol'] for row in results]
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return []
    
    def calculate_indicators_for_symbol(self, symbol: str, dates: List[str]) -> Dict:
        """
        计算单只股票的技术指标
        
        Args:
            symbol: 股票代码
            dates: 需要计算的日期列表
        
        Returns:
            计算结果字典
        """
        success_count = 0
        fail_count = 0
        
        try:
            self.logger.info(f"{symbol} 开始计算技术指标，共 {len(dates)} 天...")
            
            # 获取该股票的历史数据（需要足够的历史数据来计算指标）
            if not dates:
                return {
                    'symbol': symbol,
                    'total_dates': 0,
                    'success_count': 0,
                    'fail_count': 0,
                    'success_rate': 0
                }
            
            # 计算需要获取的日期范围（需要包含足够的历史数据）
            min_date = min(dates)
            max_date = max(dates)
            
            # 扩展日期范围，确保能获取到足够的历史数据（前60天）
            min_date_obj = datetime.strptime(min_date, '%Y-%m-%d') - timedelta(days=70)
            extended_start = min_date_obj.strftime('%Y-%m-%d')
            extended_end = max_date
            
            # 获取历史K线数据
            kline_data = self.data_source.get_stock_data(
                symbol=symbol,
                start_date=extended_start,
                end_date=extended_end
            )
            
            if kline_data.empty or len(kline_data) < 20:
                self.logger.warning(f"{symbol} 历史数据不足，无法计算技术指标")
                return {
                    'symbol': symbol,
                    'total_dates': len(dates),
                    'success_count': 0,
                    'fail_count': len(dates),
                    'success_rate': 0
                }
            
            # 批量计算技术指标（向量化计算）
            closes = kline_data['close']
            highs = kline_data['high']
            lows = kline_data['low']
            volumes = kline_data['volume'] if 'volume' in kline_data.columns else None
            
            # 计算移动平均线
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
            
            # 计算X2指标（向量化版本）
            x2_series = None
            if len(kline_data) >= 20:
                llv_low = lows.rolling(window=20, min_periods=1).min()
                hhv_high = highs.rolling(window=20, min_periods=1).max()
                range_width = hhv_high - llv_low
                x2_series = np.where(
                    range_width > 0,
                    (closes - llv_low) / range_width * 100,
                    50.0
                )
                x2_series = pd.Series(x2_series, index=kline_data.index)
            
            # 计算量比
            volume_ratio_series = None
            if volumes is not None and len(volumes) >= 5:
                avg_volume = volumes.rolling(window=5, min_periods=1).mean()
                volume_ratio_series = volumes / avg_volume
            
            # 按日期更新技术指标
            dates_sorted = sorted(dates)
            for i, date in enumerate(dates_sorted, 1):
                try:
                    date_obj = pd.to_datetime(date)
                    
                    if date_obj not in kline_data.index:
                        fail_count += 1
                        continue
                    
                    # 准备更新数据
                    update_data = {}
                    
                    # 添加移动平均线
                    if date_obj in ma5_series.index and pd.notna(ma5_series.loc[date_obj]):
                        update_data['ma5'] = float(ma5_series.loc[date_obj])
                    if date_obj in ma10_series.index and pd.notna(ma10_series.loc[date_obj]):
                        update_data['ma10'] = float(ma10_series.loc[date_obj])
                    if date_obj in ma20_series.index and pd.notna(ma20_series.loc[date_obj]):
                        update_data['ma20'] = float(ma20_series.loc[date_obj])
                    if date_obj in ma60_series.index and pd.notna(ma60_series.loc[date_obj]):
                        update_data['ma60'] = float(ma60_series.loc[date_obj])
                    
                    # 添加RSI
                    if rsi_series is not None and date_obj in rsi_series.index and pd.notna(rsi_series.loc[date_obj]):
                        update_data['rsi'] = float(rsi_series.loc[date_obj])
                    
                    # 添加MACD
                    if macd_series is not None and date_obj in macd_series.index and pd.notna(macd_series.loc[date_obj]):
                        update_data['macd'] = float(macd_series.loc[date_obj])
                    if macd_signal_series is not None and date_obj in macd_signal_series.index and pd.notna(macd_signal_series.loc[date_obj]):
                        update_data['macd_signal'] = float(macd_signal_series.loc[date_obj])
                    if macd_hist_series is not None and date_obj in macd_hist_series.index and pd.notna(macd_hist_series.loc[date_obj]):
                        update_data['macd_hist'] = float(macd_hist_series.loc[date_obj])
                    
                    # 添加X2
                    if x2_series is not None and date_obj in x2_series.index and pd.notna(x2_series.loc[date_obj]):
                        update_data['x2'] = float(round(x2_series.loc[date_obj], 4))
                    
                    # 添加量比
                    if volume_ratio_series is not None and date_obj in volume_ratio_series.index and pd.notna(volume_ratio_series.loc[date_obj]):
                        update_data['volume_ratio'] = float(volume_ratio_series.loc[date_obj])
                    
                    # 更新数据库
                    if update_data:
                        if self.storage.update_stock_daily_data(symbol, date, update_data):
                            success_count += 1
                            if i % 100 == 0 or i == len(dates_sorted):
                                self.logger.info(f"{symbol} 进度: {i}/{len(dates_sorted)}, 成功: {success_count}")
                        else:
                            fail_count += 1
                    else:
                        fail_count += 1
                    
                except Exception as e:
                    fail_count += 1
                    self.logger.warning(f"{symbol} {date} 更新失败: {str(e)}")
            
            self.logger.info(f"{symbol} 完成：成功 {success_count}/{len(dates)}, 失败 {fail_count}")
            
            return {
                'symbol': symbol,
                'total_dates': len(dates),
                'success_count': success_count,
                'fail_count': fail_count,
                'success_rate': success_count / len(dates) if dates else 0
            }
            
        except Exception as e:
            self.logger.error(f"{symbol} 计算技术指标失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'symbol': symbol,
                'total_dates': len(dates),
                'success_count': 0,
                'fail_count': len(dates),
                'success_rate': 0
            }
    
    def batch_calculate(self, symbols: Optional[List[str]] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       scan_only: bool = False) -> Dict:
        """
        批量计算技术指标
        
        Args:
            symbols: 股票代码列表，如果为None则处理所有股票
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）
            scan_only: 是否只扫描不计算（默认False）
        
        Returns:
            批量计算结果字典
        """
        start_time = datetime.now()
        
        # 扫描缺失技术指标的数据
        missing_dict = self.scan_missing_indicators(symbols, start_date, end_date)
        
        if not missing_dict:
            self.logger.info("没有缺失技术指标的数据")
            return {
                'total_symbols': 0,
                'total_dates': 0,
                'success_count': 0,
                'fail_count': 0,
                'duration_seconds': 0
            }
        
        if scan_only:
            self.logger.info("仅扫描模式，不进行计算")
            return {
                'total_symbols': len(missing_dict),
                'total_dates': sum(len(dates) for dates in missing_dict.values()),
                'missing_dict': missing_dict
            }
        
        # 批量计算
        total_symbols = len(missing_dict)
        total_dates = sum(len(dates) for dates in missing_dict.values())
        total_success = 0
        total_fail = 0
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"开始批量计算技术指标")
        self.logger.info(f"  股票数量: {total_symbols}")
        self.logger.info(f"  总日期数: {total_dates}")
        self.logger.info(f"  线程数: {self.max_workers}")
        self.logger.info(f"{'='*60}\n")
        
        if self.max_workers > 1:
            # 多线程模式
            results = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_symbol = {
                    executor.submit(self.calculate_indicators_for_symbol, symbol, dates): symbol
                    for symbol, dates in missing_dict.items()
                }
                
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result()
                        results.append(result)
                        total_success += result['success_count']
                        total_fail += result['fail_count']
                    except Exception as e:
                        self.logger.error(f"{symbol} 处理异常: {str(e)}")
                        total_fail += len(missing_dict.get(symbol, []))
        else:
            # 单线程模式
            results = []
            for symbol, dates in missing_dict.items():
                result = self.calculate_indicators_for_symbol(symbol, dates)
                results.append(result)
                total_success += result['success_count']
                total_fail += result['fail_count']
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # 统计结果
        result_summary = {
            'total_symbols': total_symbols,
            'total_dates': total_dates,
            'success_count': total_success,
            'fail_count': total_fail,
            'success_rate': total_success / total_dates if total_dates > 0 else 0,
            'duration_seconds': duration,
            'results': results
        }
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"批量计算完成统计:")
        self.logger.info(f"  股票数量: {total_symbols}")
        self.logger.info(f"  总日期数: {total_dates}")
        self.logger.info(f"  成功: {total_success}")
        self.logger.info(f"  失败: {total_fail}")
        self.logger.info(f"  成功率: {result_summary['success_rate']:.2%}")
        self.logger.info(f"  总耗时: {duration/60:.2f} 分钟")
        self.logger.info(f"{'='*60}")
        
        return result_summary


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量计算技术指标')
    parser.add_argument('--symbol', type=str, help='股票代码（单只股票）')
    parser.add_argument('--symbols', type=str, help='股票代码列表（逗号分隔，如：000001,600519）')
    parser.add_argument('--all', action='store_true', help='处理所有股票')
    parser.add_argument('--start-date', type=str, help='开始日期（格式：YYYY-MM-DD）')
    parser.add_argument('--end-date', type=str, help='结束日期（格式：YYYY-MM-DD）')
    parser.add_argument('--threads', type=int, default=1, help='最大线程数（默认1，单线程模式）')
    parser.add_argument('--scan-only', action='store_true', help='仅扫描缺失数据，不进行计算')
    
    args = parser.parse_args()
    
    # 确定要处理的股票列表
    symbols = None
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
    elif args.all:
        symbols = None  # 处理所有股票
    else:
        parser.print_help()
        return
    
    # 创建计算器
    calculator = TechnicalIndicatorsCalculator(max_workers=args.threads)
    
    # 执行批量计算
    result = calculator.batch_calculate(
        symbols=symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        scan_only=args.scan_only
    )
    
    # 输出结果
    if args.scan_only:
        print(f"\n扫描结果：")
        print(f"  股票数量: {result['total_symbols']}")
        print(f"  总日期数: {result['total_dates']}")
        if result.get('missing_dict'):
            print(f"\n缺失技术指标的股票：")
            for symbol, dates in list(result['missing_dict'].items())[:10]:
                print(f"  {symbol}: {len(dates)} 天")
            if len(result['missing_dict']) > 10:
                print(f"  ... 还有 {len(result['missing_dict']) - 10} 只股票")
    else:
        print(f"\n计算结果：")
        print(f"  股票数量: {result['total_symbols']}")
        print(f"  总日期数: {result['total_dates']}")
        print(f"  成功: {result['success_count']}")
        print(f"  失败: {result['fail_count']}")
        print(f"  成功率: {result['success_rate']:.2%}")
        print(f"  耗时: {result['duration_seconds']/60:.2f} 分钟")


if __name__ == '__main__':
    main()
