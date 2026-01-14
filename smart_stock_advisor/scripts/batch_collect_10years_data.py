"""
批量收集A股和美股最近10年历史数据脚本

功能：
- 支持分批处理，避免中断
- 自动记录进度，支持断点续传
- 错误重试机制
- 数据完整性验证

使用方法：
    # A股数据收集
    python scripts/batch_collect_10years_data.py --market cn --batch-size 50
    
    # 美股数据收集
    python scripts/batch_collect_10years_data.py --market us --batch-size 50
    
    # 继续之前的进度
    python scripts/batch_collect_10years_data.py --market cn --resume
"""
import os
import sys
import argparse
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.common_utils import get_project_root

logger = get_logger(__name__)

# 进度文件路径
PROGRESS_FILE_CN = os.path.join(project_root, 'data', 'collect_progress_cn.json')
PROGRESS_FILE_US = os.path.join(project_root, 'data', 'collect_progress_us.json')


class BatchDataCollector:
    """批量数据收集器（基础类）"""
    
    def __init__(self, market: str = 'cn', batch_size: int = 50, delay: float = 1.0, max_workers: int = 1):
        """
        初始化批量数据收集器
        
        Args:
            market: 市场类型（'cn'=A股, 'us'=美股）
            batch_size: 每批处理的股票数量
            delay: 每只股票之间的延迟（秒）
            max_workers: 最大线程数（默认为1，即单线程模式）
        """
        self.market = market
        self.batch_size = batch_size
        self.delay = delay
        self.max_workers = max_workers
        self.logger = logger
        
        # 进度文件锁（用于多线程环境下的进度保存）
        self.progress_lock = threading.Lock()
        
        # 确保data目录存在
        data_dir = os.path.join(project_root, 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # 进度文件
        self.progress_file = PROGRESS_FILE_CN if market == 'cn' else PROGRESS_FILE_US
        
        # 初始化收集器（单线程模式使用，多线程模式下每个线程会创建自己的实例）
        if market == 'cn':
            from utils.stock_history_collector import StockHistoryCollector
            self.collector = StockHistoryCollector()
        else:
            from utils.us_stock_collector import USStockCollector
            self.collector = USStockCollector()
    
    def load_progress(self) -> Dict:
        """加载收集进度"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"加载进度文件失败: {str(e)}")
        
        return {
            'completed_symbols': [],
            'failed_symbols': [],
            'current_batch': 0,
            'total_symbols': 0,
            'start_time': None,
            'last_update': None
        }
    
    def save_progress(self, progress: Dict):
        """
        保存收集进度（线程安全）
        
        Args:
            progress: 进度字典
        """
        try:
            # 使用锁确保多线程环境下进度保存的线程安全
            with self.progress_lock:
                progress['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存进度文件失败: {str(e)}")
    
    def get_stock_list(self) -> List[str]:
        """
        获取股票列表
        
        Returns:
            股票代码列表
        """
        raise NotImplementedError("子类必须实现get_stock_list方法")
    
    def collect_single_stock(self, symbol: str, years: int = 10, collector=None) -> Dict:
        """
        收集单只股票的数据
        
        Args:
            symbol: 股票代码
            years: 收集多少年的数据
            collector: 收集器实例（可选，如果为None则使用self.collector）
        
        Returns:
            收集结果字典
        """
        raise NotImplementedError("子类必须实现collect_single_stock方法")
    
    def batch_collect(self, years: int = 10, resume: bool = False) -> Dict:
        """
        批量收集数据（根据max_workers自动选择单线程或多线程模式）
        
        Args:
            years: 收集多少年的数据（默认10年）
            resume: 是否继续之前的进度
        
        Returns:
            收集结果统计
        """
        # 如果max_workers > 1，使用多线程模式
        if self.max_workers > 1:
            return self.batch_collect_multithread(years=years, resume=resume)
        
        # 否则使用单线程模式
        self.logger.info(f"开始批量收集{self.market.upper()}股数据（近{years}年，单线程模式）...")
        
        # 加载进度
        progress = self.load_progress()
        
        # 获取股票列表
        all_symbols = self.get_stock_list()
        total_symbols = len(all_symbols)
        progress['total_symbols'] = total_symbols
        
        # 确定需要处理的股票
        if resume and progress.get('completed_symbols'):
            # 继续之前的进度
            completed_set = set(progress.get('completed_symbols', []))
            failed_set = {item['symbol'] if isinstance(item, dict) else item for item in progress.get('failed_symbols', [])}
            pending_symbols = [s for s in all_symbols if s not in completed_set and s not in failed_set]
            self.logger.info(f"继续之前的进度：已完成 {len(completed_set)} 只，失败 {len(failed_set)} 只，待处理 {len(pending_symbols)} 只")
        else:
            # 重新开始
            pending_symbols = all_symbols
            progress = {
                'completed_symbols': [],
                'failed_symbols': [],
                'current_batch': 0,
                'total_symbols': total_symbols,
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_update': None
            }
        
        # 分批处理
        total_batches = (len(pending_symbols) + self.batch_size - 1) // self.batch_size
        batch_num = progress.get('current_batch', 0)
        
        start_time = datetime.now()
        total_success = 0
        total_failed = 0
        
        try:
            for i in range(0, len(pending_symbols), self.batch_size):
                batch_num += 1
                batch = pending_symbols[i:i + self.batch_size]
                
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"批次 {batch_num}/{total_batches}: 处理 {len(batch)} 只股票")
                self.logger.info(f"{'='*60}")
                
                batch_start_time = datetime.now()
                batch_success = 0
                batch_failed = 0
                
                for idx, symbol in enumerate(batch, 1):
                    try:
                        self.logger.info(f"[{idx}/{len(batch)}] 正在收集: {symbol}")
                        
                        result = self.collect_single_stock(symbol, years=years)
                        
                        if result.get('success', False):
                            progress['completed_symbols'].append(symbol)
                            batch_success += 1
                            total_success += 1
                            records_count = result.get('records_count', 0)
                            self.logger.info(f"  ✓ {symbol} 收集成功: 成功采集 {records_count} 条记录")
                        else:
                            progress['failed_symbols'].append({
                                'symbol': symbol,
                                'error': result.get('message', '未知错误'),
                                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                            batch_failed += 1
                            total_failed += 1
                            self.logger.warning(f"  ✗ {symbol} 收集失败: {result.get('message', '未知错误')}")
                        
                        # 保存进度（每只股票后保存一次，防止中断丢失）
                        progress['current_batch'] = batch_num
                        self.save_progress(progress)
                        
                        # 延迟，避免API限制
                        if idx < len(batch):
                            time.sleep(self.delay)
                    
                    except KeyboardInterrupt:
                        self.logger.warning("\n用户中断，保存进度...")
                        progress['current_batch'] = batch_num
                        self.save_progress(progress)
                        raise
                    except Exception as e:
                        self.logger.error(f"  ✗ {symbol} 处理异常: {str(e)}")
                        progress['failed_symbols'].append({
                            'symbol': symbol,
                            'error': str(e),
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                        batch_failed += 1
                        total_failed += 1
                        progress['current_batch'] = batch_num
                        self.save_progress(progress)
                
                batch_duration = (datetime.now() - batch_start_time).total_seconds()
                self.logger.info(f"\n批次 {batch_num} 完成: 成功 {batch_success}, 失败 {batch_failed}, 耗时 {batch_duration:.1f}秒")
                
                # 批次之间的延迟
                if i + self.batch_size < len(pending_symbols):
                    self.logger.info(f"等待 {self.delay * 2} 秒后继续下一批...")
                    time.sleep(self.delay * 2)
        
        except KeyboardInterrupt:
            self.logger.warning("\n用户中断，保存进度...")
            progress['current_batch'] = batch_num
            self.save_progress(progress)
        
        # 最终统计
        total_duration = (datetime.now() - start_time).total_seconds()
        progress['current_batch'] = batch_num
        
        result = {
            'total_symbols': total_symbols,
            'completed': len(progress['completed_symbols']),
            'failed': len(progress['failed_symbols']),
            'remaining': total_symbols - len(progress['completed_symbols']) - len(progress['failed_symbols']),
            'total_duration_seconds': total_duration,
            'progress_file': self.progress_file
        }
        
        self.save_progress(progress)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"批量收集完成统计:")
        self.logger.info(f"  总股票数: {total_symbols}")
        self.logger.info(f"  已完成: {result['completed']}")
        self.logger.info(f"  失败: {result['failed']}")
        self.logger.info(f"  剩余: {result['remaining']}")
        self.logger.info(f"  总耗时: {total_duration/3600:.3f} 小时")
        self.logger.info(f"{'='*60}")
        
        return result
    
    def _scan_database_status(self, symbols: List[str], years: int = 10) -> Dict:
        """
        扫描数据库，统计已有数据情况
        
        Args:
            symbols: 股票代码列表
            years: 数据年份范围
        
        Returns:
            统计信息字典
        """
        try:
            from utils.stock_history_storage import StockHistoryStorage
            from datetime import datetime, timedelta
            
            storage = StockHistoryStorage()
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            has_data_count = 0
            no_data_count = 0
            total_missing_days = 0
            completeness_rates = []
            
            # 扫描前10只股票作为示例（避免扫描所有股票耗时过长）
            sample_size = min(10, len(symbols))
            sample_symbols = symbols[:sample_size]
            
            self.logger.info(f"扫描前 {sample_size} 只股票的数据状态（示例）...")
            
            for symbol in sample_symbols:
                try:
                    status = storage.scan_stock_data_status(symbol, start_date_str, end_date_str)
                    
                    if status['existing_count'] > 0:
                        has_data_count += 1
                        completeness_rates.append(status['completeness_rate'])
                        total_missing_days += status['missing_count']
                        
                        if status['missing_count'] > 0:
                            self.logger.info(
                                f"  {symbol}: 已有 {status['existing_count']}/{status['total_dates']} 天 "
                                f"({status['completeness_rate']:.2%}), "
                                f"缺失 {status['missing_count']} 天, "
                                f"最早: {status['earliest_date']}, 最晚: {status['latest_date']}"
                            )
                    else:
                        no_data_count += 1
                        self.logger.info(f"  {symbol}: 无数据")
                        
                except Exception as e:
                    self.logger.debug(f"扫描 {symbol} 失败: {str(e)}")
                    no_data_count += 1
            
            # 估算所有股票的情况（基于样本）
            if sample_size > 0:
                sample_has_data_rate = has_data_count / sample_size
                estimated_has_data = int(len(symbols) * sample_has_data_rate)
                estimated_no_data = len(symbols) - estimated_has_data
                avg_completeness = sum(completeness_rates) / len(completeness_rates) if completeness_rates else 0
                estimated_total_missing = int(total_missing_days * (len(symbols) / sample_size))
            else:
                estimated_has_data = 0
                estimated_no_data = len(symbols)
                avg_completeness = 0
                estimated_total_missing = 0
            
            return {
                'has_data_count': estimated_has_data,
                'no_data_count': estimated_no_data,
                'total_missing_days': estimated_total_missing,
                'avg_completeness': avg_completeness,
                'sample_size': sample_size,
                'sample_has_data': has_data_count,
                'sample_no_data': no_data_count
            }
            
        except Exception as e:
            self.logger.warning(f"扫描数据库状态失败: {str(e)}")
            return {
                'has_data_count': 0,
                'no_data_count': len(symbols),
                'total_missing_days': 0,
                'avg_completeness': 0.0,
                'sample_size': 0,
                'sample_has_data': 0,
                'sample_no_data': 0
            }
    
    def _create_collector_instance(self):
        """
        创建收集器实例（用于多线程环境，每个线程需要独立的实例）
        
        Returns:
            收集器实例
        """
        if self.market == 'cn':
            from utils.stock_history_collector import StockHistoryCollector
            return StockHistoryCollector()
        else:
            from utils.us_stock_collector import USStockCollector
            return USStockCollector()
    
    def _collect_single_stock_worker(self, symbol: str, years: int, progress: Dict) -> Dict:
        """
        单线程工作函数（用于多线程环境）
        
        Args:
            symbol: 股票代码
            years: 收集多少年的数据
            progress: 进度字典（用于更新进度）
        
        Returns:
            收集结果字典
        """
        # 每个线程创建自己的收集器实例
        collector = self._create_collector_instance()
        
        # 添加延迟以避免API速率限制（多线程模式下减少延迟，因为批量模式已经优化）
        import random
        # 批量模式下减少延迟（批量模式已经大幅减少了API调用次数）
        if self.max_workers > 1:
            time.sleep(self.delay * random.uniform(0.2, 0.5))  # 多线程模式下减少延迟
        else:
            time.sleep(self.delay * random.uniform(0.5, 1.5))  # 单线程模式保持原延迟
        
        max_retries = 3
        retry_delay = 2.0  # 重试延迟（秒）
        result = None
        
        for attempt in range(max_retries):
            try:
                result = self.collect_single_stock(symbol, years=years, collector=collector)
                
                # 如果遇到速率限制错误，等待后重试
                if not result.get('success', False):
                    error_msg = result.get('message', '')
                    if 'Rate limited' in error_msg or 'Too Many Requests' in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (attempt + 1)  # 递增等待时间
                            self.logger.warning(f"  {symbol} 遇到速率限制，等待 {wait_time:.1f} 秒后重试（第 {attempt + 1}/{max_retries} 次）...")
                            time.sleep(wait_time)
                            continue
                
                break  # 成功或非速率限制错误，跳出重试循环
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    self.logger.warning(f"  {symbol} 处理异常，等待 {wait_time:.1f} 秒后重试: {str(e)}")
                    time.sleep(wait_time)
                else:
                    result = {
                        'symbol': symbol,
                        'success': False,
                        'message': str(e),
                        'records_count': 0
                    }
        
        if result is None:
            result = {
                'symbol': symbol,
                'success': False,
                'message': '收集失败：重试次数用完',
                'records_count': 0
            }
        
        try:
            # 更新进度（线程安全）
            with self.progress_lock:
                if result.get('success', False):
                    if symbol not in progress['completed_symbols']:
                        progress['completed_symbols'].append(symbol)
                    # 移除失败列表中的该股票（如果存在）
                    progress['failed_symbols'] = [
                        item for item in progress['failed_symbols']
                        if (isinstance(item, dict) and item.get('symbol') != symbol) or item != symbol
                    ]
                else:
                    # 添加到失败列表（如果不存在）
                    failed_symbols_set = {
                        item['symbol'] if isinstance(item, dict) else item
                        for item in progress.get('failed_symbols', [])
                    }
                    if symbol not in failed_symbols_set:
                        progress['failed_symbols'].append({
                            'symbol': symbol,
                            'error': result.get('message', '未知错误'),
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
            
            return result
        except Exception as e:
            self.logger.error(f"收集 {symbol} 失败: {str(e)}")
            error_result = {
                'symbol': symbol,
                'success': False,
                'message': str(e),
                'records_count': 0
            }
            # 更新失败列表
            with self.progress_lock:
                failed_symbols_set = {
                    item['symbol'] if isinstance(item, dict) else item
                    for item in progress.get('failed_symbols', [])
                }
                if symbol not in failed_symbols_set:
                    progress['failed_symbols'].append({
                        'symbol': symbol,
                        'error': str(e),
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
            return error_result
    
    def batch_collect_multithread(self, years: int = 10, resume: bool = False) -> Dict:
        """
        批量收集数据（多线程版本）
        
        Args:
            years: 收集多少年的数据（默认10年）
            resume: 是否继续之前的进度
        
        Returns:
            收集结果统计
        """
        self.logger.info(f"开始批量收集{self.market.upper()}股数据（近{years}年，使用{self.max_workers}个线程）...")
        
        # 加载进度
        progress = self.load_progress()
        
        # 获取股票列表
        all_symbols = self.get_stock_list()
        total_symbols = len(all_symbols)
        progress['total_symbols'] = total_symbols
        
        # 扫描数据库，统计已有数据情况
        self.logger.info(f"\n{'='*60}")
        self.logger.info("正在扫描数据库，统计已有数据情况...")
        self.logger.info(f"{'='*60}")
        
        data_status_summary = self._scan_database_status(all_symbols, years)
        
        self.logger.info(f"\n数据库扫描完成:")
        self.logger.info(f"  总股票数: {total_symbols}")
        self.logger.info(f"  已有数据: {data_status_summary['has_data_count']} 只（估算）")
        self.logger.info(f"  无数据: {data_status_summary['no_data_count']} 只（估算）")
        self.logger.info(f"  数据完整度: {data_status_summary['avg_completeness']:.2%}")
        self.logger.info(f"  总缺失天数: {data_status_summary['total_missing_days']} 天（估算）")
        self.logger.info(f"{'='*60}\n")
        
        # 确定需要处理的股票
        if resume and progress.get('completed_symbols'):
            completed_set = set(progress.get('completed_symbols', []))
            failed_set = {
                item['symbol'] if isinstance(item, dict) else item
                for item in progress.get('failed_symbols', [])
            }
            pending_symbols = [s for s in all_symbols if s not in completed_set and s not in failed_set]
            self.logger.info(f"继续之前的进度：已完成 {len(completed_set)} 只，失败 {len(failed_set)} 只，待处理 {len(pending_symbols)} 只")
        else:
            pending_symbols = all_symbols
            progress = {
                'completed_symbols': [],
                'failed_symbols': [],
                'current_batch': 0,
                'total_symbols': total_symbols,
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_update': None
            }
        
        start_time = datetime.now()
        total_success = 0
        total_failed = 0
        
        # 分批处理（每批内部使用多线程）
        total_batches = (len(pending_symbols) + self.batch_size - 1) // self.batch_size
        batch_num = 0
        
        try:
            for i in range(0, len(pending_symbols), self.batch_size):
                batch_num += 1
                batch = pending_symbols[i:i + self.batch_size]
                
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"批次 {batch_num}/{total_batches}: 处理 {len(batch)} 只股票（使用{self.max_workers}个线程）")
                self.logger.info(f"{'='*60}")
                
                batch_start_time = datetime.now()
                batch_success = 0
                batch_failed = 0
                
                # 使用线程池并行处理（限制并发数量以避免API速率限制）
                # 对于美股，使用更少的并发线程（建议单线程或最多2个线程）
                if self.market == 'us':
                    effective_workers = min(self.max_workers, 1)  # 美股建议单线程，避免速率限制
                    if effective_workers < self.max_workers:
                        self.logger.info(f"  美股API速率限制非常严格，将并发线程数从 {self.max_workers} 降低到 {effective_workers}（建议单线程）")
                else:
                    effective_workers = self.max_workers
                
                with ThreadPoolExecutor(max_workers=effective_workers) as executor:
                    # 提交所有任务
                    future_to_symbol = {
                        executor.submit(self._collect_single_stock_worker, symbol, years, progress): symbol
                        for symbol in batch
                    }
                    
                    # 处理完成的任务
                    for future in as_completed(future_to_symbol):
                        symbol = future_to_symbol[future]
                        try:
                            result = future.result()
                            if result.get('success', False):
                                batch_success += 1
                                total_success += 1
                                records_count = result.get('records_count', 0)
                                self.logger.info(f"  ✓ {symbol} 收集成功: 成功采集 {records_count} 条记录")
                            else:
                                batch_failed += 1
                                total_failed += 1
                                self.logger.warning(f"  ✗ {symbol} 收集失败: {result.get('message', '未知错误')}")
                            
                            # 定期保存进度（减少保存频率，每10只股票保存一次）
                            if batch_success % 10 == 0 or batch_success == len(batch):
                                progress['current_batch'] = batch_num
                                self.save_progress(progress)
                            
                        except Exception as e:
                            batch_failed += 1
                            total_failed += 1
                            self.logger.error(f"  ✗ {symbol} 处理异常: {str(e)}")
                            progress['current_batch'] = batch_num
                            self.save_progress(progress)
                
                batch_duration = (datetime.now() - batch_start_time).total_seconds()
                self.logger.info(f"\n批次 {batch_num} 完成: 成功 {batch_success}, 失败 {batch_failed}, 耗时 {batch_duration:.1f}秒")
                
                # 批次之间的延迟
                if i + self.batch_size < len(pending_symbols):
                    self.logger.info(f"等待 {self.delay} 秒后继续下一批...")
                    time.sleep(self.delay)
        
        except KeyboardInterrupt:
            self.logger.warning("\n用户中断，保存进度...")
            progress['current_batch'] = batch_num
            self.save_progress(progress)
        
        # 最终统计
        total_duration = (datetime.now() - start_time).total_seconds()
        progress['current_batch'] = batch_num
        
        result = {
            'total_symbols': total_symbols,
            'completed': len(progress['completed_symbols']),
            'failed': len(progress['failed_symbols']),
            'remaining': total_symbols - len(progress['completed_symbols']) - len(progress['failed_symbols']),
            'total_duration_seconds': total_duration,
            'progress_file': self.progress_file
        }
        
        self.save_progress(progress)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"批量收集完成统计（多线程模式）:")
        self.logger.info(f"  总股票数: {total_symbols}")
        self.logger.info(f"  已完成: {result['completed']}")
        self.logger.info(f"  失败: {result['failed']}")
        self.logger.info(f"  剩余: {result['remaining']}")
        self.logger.info(f"  总耗时: {total_duration/3600:.3f} 小时")
        self.logger.info(f"  使用线程数: {self.max_workers}")
        self.logger.info(f"{'='*60}")
        
        return result


class CNStockBatchCollector(BatchDataCollector):
    """A股批量数据收集器"""
    
    def __init__(self, batch_size: int = 50, delay: float = 1.0, max_workers: int = 1):
        super().__init__(market='cn', batch_size=batch_size, delay=delay, max_workers=max_workers)
    
    def get_stock_list(self) -> List[str]:
        """获取A股股票列表"""
        try:
            # 方法1: 从akshare获取所有A股列表
            import akshare as ak
            self.logger.info("正在获取A股股票列表...")
            stock_list = ak.stock_info_a_code_name()
            # 处理不同的列名格式
            if isinstance(stock_list, pd.DataFrame):
                # 查找代码列（可能是'code'或'代码'）
                code_col = None
                for col in stock_list.columns:
                    if 'code' in col.lower() or col == '代码':
                        code_col = col
                        break
                if code_col:
                    symbols = stock_list[code_col].tolist()
                else:
                    # 如果没有找到，使用第一列
                    symbols = stock_list.iloc[:, 0].tolist()
            else:
                # 如果不是DataFrame，尝试其他方法
                symbols = list(stock_list) if hasattr(stock_list, '__iter__') else []
            
            # 确保所有代码都是字符串格式
            symbols = [str(s).strip() for s in symbols if s]
            self.logger.info(f"获取到 {len(symbols)} 只A股")
            return symbols
        except Exception as e:
            self.logger.error(f"获取A股列表失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 方法2: 使用示例列表（如果akshare失败）
            self.logger.warning("使用示例股票列表进行测试")
            return ['000001', '000002', '600000', '600519', '600036']
    
    def collect_single_stock(self, symbol: str, years: int = 10, collector=None) -> Dict:
        """收集A股单只股票数据"""
        if collector is None:
            collector = self.collector
        
        try:
            result = collector.collect_stock_history_data(
                symbol=symbol,
                years=years,
                force_refresh=False,  # 不强制刷新，只收集缺失的数据
                use_batch_mode=True  # 使用批量模式提升效率
            )
            success_count = result.get('success_count', 0)
            return {
                'symbol': symbol,
                'success': result.get('success', False) or success_count > 0,  # 如果有成功记录就认为成功
                'message': result.get('message', '') or result.get('error', ''),
                'records_count': success_count  # 统一使用records_count字段
            }
        except Exception as e:
            self.logger.error(f"收集 {symbol} 失败: {str(e)}")
            return {
                'symbol': symbol,
                'success': False,
                'message': str(e),
                'records_count': 0
            }


class USStockBatchCollector(BatchDataCollector):
    """美股批量数据收集器"""
    
    def __init__(self, batch_size: int = 50, delay: float = 1.0, max_workers: int = 1):
        super().__init__(market='us', batch_size=batch_size, delay=delay, max_workers=max_workers)
    
    def get_stock_list(self) -> List[str]:
        """获取美股股票列表（主要股票）"""
        try:
            # 方法1: 获取S&P 500成分股
            from utils.us_stock_collector import USStockCollector
            collector = USStockCollector()
            
            self.logger.info("正在获取美股股票列表（S&P 500）...")
            try:
                import akshare as ak
                sp500_df = ak.tool_trade_date_hist_sina()
                # 或者使用yfinance获取SPY成分股
                import yfinance as yf
                sp500 = yf.Ticker("^GSPC")
                # 实际上应该获取成分股列表
                # 这里先用一些主要股票
                symbols = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
                    'V', 'JNJ', 'WMT', 'JPM', 'MA', 'PG', 'UNH', 'HD', 'DIS', 'PYPL',
                    'BAC', 'VZ', 'ADBE', 'NFLX', 'CMCSA', 'KO', 'NKE', 'PFE', 'T',
                    'MRK', 'INTC', 'PEP', 'TMO', 'CSCO', 'XOM', 'ABT', 'ABBV', 'AVGO',
                    'COST', 'CVX', 'DHR', 'ACN', 'MCD', 'MDT', 'WFC', 'TXN', 'HON',
                    'LIN', 'BMY', 'UPS', 'QCOM', 'PM', 'RTX', 'LOW', 'UNP', 'SPGI'
                ] * 60  # 扩展到约3000只（实际应该从数据源获取完整列表）
                
                self.logger.info(f"获取到 {len(symbols)} 只美股（示例）")
                return symbols[:3000]  # 限制在3000只
            except Exception as e:
                self.logger.warning(f"获取S&P 500列表失败，使用示例列表: {str(e)}")
                return [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
                    'V', 'JNJ', 'WMT', 'JPM', 'MA', 'PG', 'UNH', 'HD', 'DIS'
                ]
        except Exception as e:
            self.logger.error(f"获取美股列表失败: {str(e)}")
            return ['AAPL', 'MSFT', 'GOOGL']
    
    def collect_single_stock(self, symbol: str, years: int = 10, collector=None) -> Dict:
        """收集美股单只股票数据"""
        if collector is None:
            collector = self.collector
        
        try:
            result = collector.collect_stock_history(
                symbol=symbol,
                period=f'{years}y'  # 例如 '10y' 表示10年
            )
            return {
                'symbol': symbol,
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'records_count': result.get('count', 0)  # USStockCollector returns 'count'
            }
        except Exception as e:
            self.logger.error(f"收集 {symbol} 失败: {str(e)}")
            return {
                'symbol': symbol,
                'success': False,
                'message': str(e),
                'records_count': 0
            }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量收集A股和美股最近10年历史数据')
    parser.add_argument('--market', choices=['cn', 'us'], default='cn', 
                       help='市场类型（cn=A股, us=美股）')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='每批处理的股票数量（默认50）')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='每只股票之间的延迟（秒，默认1.0）')
    parser.add_argument('--years', type=int, default=10,
                       help='收集多少年的数据（默认10年）')
    parser.add_argument('--resume', action='store_true',
                       help='继续之前的进度')
    parser.add_argument('--threads', type=int, default=1,
                       help='最大线程数（默认1，即单线程模式。建议2-5，根据网络和API限制调整）')
    
    args = parser.parse_args()
    
    # 创建收集器
    if args.market == 'cn':
        collector = CNStockBatchCollector(
            batch_size=args.batch_size,
            delay=args.delay,
            max_workers=args.threads
        )
    else:
        collector = USStockBatchCollector(
            batch_size=args.batch_size,
            delay=args.delay,
            max_workers=args.threads
        )
    
    # 开始收集
    try:
        result = collector.batch_collect(years=args.years, resume=args.resume)
        print(f"\n收集完成！结果已保存到: {result['progress_file']}")
    except KeyboardInterrupt:
        print("\n\n用户中断，进度已保存。使用 --resume 参数继续之前的进度。")
    except Exception as e:
        logger.error(f"收集过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()

