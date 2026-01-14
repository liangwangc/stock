"""
批量计算成本分布脚本

功能：
- 扫描数据库中缺失成本分布的历史数据
- 批量计算成本分布（基于历史K线数据）
- 更新数据库中的成本分布字段

使用方法：
    # 计算单只股票的成本分布
    python scripts/batch_calculate_cost_distribution.py --symbol 000001
    
    # 批量计算所有股票的成本分布
    python scripts/batch_calculate_cost_distribution.py --all
    
    # 批量计算指定股票列表的成本分布
    python scripts/batch_calculate_cost_distribution.py --symbols 000001,600519,000002
    
    # 计算指定日期范围的数据
    python scripts/batch_calculate_cost_distribution.py --all --start-date 2024-01-01 --end-date 2024-12-31
    
    # 多线程模式（推荐）
    python scripts/batch_calculate_cost_distribution.py --all --threads 5
"""
import os
import sys
import argparse
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_storage import StockHistoryStorage
from data_source.stock_data_source import StockDataSource

logger = get_logger(__name__)


class CostDistributionCalculator:
    """成本分布批量计算器"""
    
    def __init__(self, days: int = 60, bins: int = 20, max_workers: int = 1):
        """
        初始化成本分布计算器
        
        Args:
            days: 计算成本分布使用的历史天数（默认60天）
            bins: 价格分档数量（默认20档）
            max_workers: 最大线程数（默认1，单线程模式）
        """
        self.storage = StockHistoryStorage()
        self.data_source = StockDataSource()
        self.logger = logger
        self.days = days
        self.bins = bins
        self.max_workers = max_workers
        self.progress_lock = threading.Lock()
        
    def scan_missing_cost_distribution(self, symbols: Optional[List[str]] = None, 
                                      start_date: Optional[str] = None,
                                      end_date: Optional[str] = None) -> Dict[str, List[str]]:
        """
        扫描缺失成本分布的股票和日期
        
        Args:
            symbols: 股票代码列表，如果为None则扫描所有股票
            start_date: 开始日期（格式：YYYY-MM-DD），如果为None则从最早数据开始
            end_date: 结束日期（格式：YYYY-MM-DD），如果为None则到最新数据
        
        Returns:
            字典，key为股票代码，value为缺失成本分布的日期列表
        """
        try:
            self.logger.info("开始扫描缺失成本分布的数据...")
            
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
                    
                    # 找出缺失成本分布的日期
                    missing_dates = []
                    for record in existing_data:
                        trade_date = record.get('trade_date')
                        if isinstance(trade_date, datetime):
                            trade_date = trade_date.strftime('%Y-%m-%d')
                        elif isinstance(trade_date, str):
                            trade_date = trade_date.split()[0]
                        
                        # 检查成本分布字段是否为空
                        cost_dist = record.get('cost_distribution')
                        cost_dist_history = record.get('cost_distribution_history')
                        
                        if not cost_dist and not cost_dist_history:
                            missing_dates.append(trade_date)
                    
                    if missing_dates:
                        missing_dict[symbol] = missing_dates
                        self.logger.debug(f"{symbol}: 缺失 {len(missing_dates)} 天的成本分布")
                
                except Exception as e:
                    self.logger.warning(f"扫描 {symbol} 失败: {str(e)}")
                    continue
            
            total_missing = sum(len(dates) for dates in missing_dict.values())
            self.logger.info(f"扫描完成：{len(missing_dict)} 只股票，共 {total_missing} 天缺失成本分布")
            
            return missing_dict
            
        except Exception as e:
            self.logger.error(f"扫描缺失成本分布失败: {str(e)}")
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
    
    def calculate_cost_distribution_for_date(self, symbol: str, date: str) -> Optional[Dict]:
        """
        计算指定日期的成本分布
        
        注意：成本分布是基于历史数据计算的，每个日期的成本分布应该使用该日期之前的历史数据。
        例如，计算2024-01-15的成本分布，应该使用2024-01-15之前60天的数据。
        
        Args:
            symbol: 股票代码
            date: 交易日期（格式：YYYY-MM-DD）
        
        Returns:
            成本分布字典，如果计算失败返回None
        """
        try:
            # 获取历史K线数据（用于计算成本分布）
            # 成本分布应该基于该日期之前的历史数据计算
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            end_date_obj = date_obj - timedelta(days=1)  # 使用该日期前一天作为结束日期
            start_date_obj = end_date_obj - timedelta(days=self.days + 10)  # 多获取10天以确保有足够数据
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
            
            # 获取历史数据
            kline_data = self.data_source.get_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if kline_data.empty or len(kline_data) < 10:
                self.logger.debug(f"{symbol} {date} 数据不足（需要至少10天数据），无法计算成本分布")
                return None
            
            # 使用最近N天的数据计算成本分布
            # 只取最近days天的数据
            if len(kline_data) > self.days:
                kline_data = kline_data.tail(self.days)
            
            # 直接使用核心计算方法（避免重复获取数据）
            if 'close' not in kline_data.columns or 'volume' not in kline_data.columns:
                self.logger.debug(f"{symbol} {date} K线数据缺少必要字段")
                return None
            
            # 计算成本分布
            cost_dist = self.data_source._calculate_cost_distribution_core(
                kline_data['close'].values,
                kline_data['volume'].values,
                bins=self.bins
            )
            
            if not cost_dist or not cost_dist.get('levels'):
                self.logger.debug(f"{symbol} {date} 成本分布计算失败")
                return None
            
            # 添加scope标识
            cost_dist['scope'] = 'history'
            
            return cost_dist
            
        except Exception as e:
            self.logger.debug(f"{symbol} {date} 计算成本分布失败: {str(e)}")
            return None
    
    def update_cost_distribution_for_symbol(self, symbol: str, dates: List[str]) -> Dict:
        """
        更新单只股票的成本分布
        
        Args:
            symbol: 股票代码
            dates: 需要更新的日期列表
        
        Returns:
            更新结果字典
        """
        success_count = 0
        fail_count = 0
        
        try:
            self.logger.info(f"{symbol} 开始计算成本分布，共 {len(dates)} 天...")
            
            # 按日期排序
            dates_sorted = sorted(dates)
            
            # 批量计算成本分布（每个日期都需要计算，因为成本分布是基于历史数据计算的）
            for i, date in enumerate(dates_sorted, 1):
                try:
                    # 计算成本分布
                    cost_dist = self.calculate_cost_distribution_for_date(symbol, date)
                    
                    if cost_dist:
                        # 准备更新数据
                        update_data = {
                            'cost_distribution_history': cost_dist,
                            'cost_distribution': {
                                'history': cost_dist,
                                'intraday': {}  # 历史数据无法获取当日成本分布
                            }
                        }
                        
                        # 更新数据库
                        if self.storage.update_stock_daily_data(symbol, date, update_data):
                            success_count += 1
                            if i % 50 == 0 or i == len(dates_sorted):
                                self.logger.info(f"{symbol} 进度: {i}/{len(dates_sorted)}, 成功: {success_count}")
                        else:
                            fail_count += 1
                    else:
                        fail_count += 1
                    
                    # 避免请求过快
                    if i < len(dates_sorted):
                        time.sleep(0.1)
                
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
            self.logger.error(f"{symbol} 更新成本分布失败: {str(e)}")
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
        批量计算成本分布
        
        Args:
            symbols: 股票代码列表，如果为None则处理所有股票
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）
            scan_only: 是否只扫描不计算（默认False）
        
        Returns:
            批量计算结果字典
        """
        start_time = datetime.now()
        
        # 扫描缺失成本分布的数据
        missing_dict = self.scan_missing_cost_distribution(symbols, start_date, end_date)
        
        if not missing_dict:
            self.logger.info("没有缺失成本分布的数据")
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
        self.logger.info(f"开始批量计算成本分布")
        self.logger.info(f"  股票数量: {total_symbols}")
        self.logger.info(f"  总日期数: {total_dates}")
        self.logger.info(f"  线程数: {self.max_workers}")
        self.logger.info(f"{'='*60}\n")
        
        if self.max_workers > 1:
            # 多线程模式
            results = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_symbol = {
                    executor.submit(self.update_cost_distribution_for_symbol, symbol, dates): symbol
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
                result = self.update_cost_distribution_for_symbol(symbol, dates)
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
        self.logger.info(f"  总耗时: {duration/3600:.3f} 小时")
        self.logger.info(f"{'='*60}")
        
        return result_summary


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量计算成本分布')
    parser.add_argument('--symbol', type=str, help='股票代码（单只股票）')
    parser.add_argument('--symbols', type=str, help='股票代码列表（逗号分隔，如：000001,600519）')
    parser.add_argument('--all', action='store_true', help='处理所有股票')
    parser.add_argument('--start-date', type=str, help='开始日期（格式：YYYY-MM-DD）')
    parser.add_argument('--end-date', type=str, help='结束日期（格式：YYYY-MM-DD）')
    parser.add_argument('--days', type=int, default=60, help='计算成本分布使用的历史天数（默认60）')
    parser.add_argument('--bins', type=int, default=20, help='价格分档数量（默认20）')
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
    calculator = CostDistributionCalculator(
        days=args.days,
        bins=args.bins,
        max_workers=args.threads
    )
    
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
            print(f"\n缺失成本分布的股票：")
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
        print(f"  耗时: {result['duration_seconds']/3600:.3f} 小时")


if __name__ == '__main__':
    main()
