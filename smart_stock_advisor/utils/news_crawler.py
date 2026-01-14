"""
新闻抓取模块
负责定时抓取新闻并保存到数据库
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.news_storage import NewsStorage
from utils.logger import get_logger
from utils.db_connection import DatabaseConnection as DBConnection
from config_db import USE_DATABASE

logger = get_logger(__name__)

# 尝试导入新闻源
try:
    sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))
    from quant_trading_platform.news import UnifiedNewsSource
    NEWS_SOURCE_AVAILABLE = True
except ImportError:
    try:
        from news import UnifiedNewsSource
        NEWS_SOURCE_AVAILABLE = True
    except ImportError:
        NEWS_SOURCE_AVAILABLE = False
        logger.warning("新闻源不可用")

# 尝试导入配置
try:
    from config import NEWS_SOURCES, NEWS_CONFIG, TUSHARE_TOKEN
except ImportError:
    NEWS_SOURCES = []
    NEWS_CONFIG = {'news_count': 20}
    TUSHARE_TOKEN = None


class NewsCrawler:
    """新闻抓取器"""
    
    def __init__(self):
        """
        初始化新闻抓取器
        
        注意：初始化时不会自动启动任何抓取任务。
        抓取任务必须通过 start_crawl_task() 方法手动启动。
        """
        self.logger = logger
        self.news_storage = NewsStorage()
        self.use_database = USE_DATABASE
        
        # 初始化新闻源（但不立即抓取）
        if NEWS_SOURCE_AVAILABLE:
            try:
                self.news_source = UnifiedNewsSource(tushare_token=TUSHARE_TOKEN)
            except Exception as e:
                self.logger.warning(f"初始化新闻源失败: {str(e)}")
                self.news_source = None
        else:
            self.news_source = None
        
        # 任务线程存储（初始为空，不自动启动任何任务）
        self.crawl_threads = {}
        self.stop_flags = {}
    
    def crawl_market_news(self, limit: int = 50, only_today: bool = True) -> Dict[str, int]:
        """
        抓取市场新闻（只抓取当天的新闻）
        
        Args:
            limit: 限制数量
            only_today: 是否只抓取当天的新闻（默认True）
        
        Returns:
            {'success': 成功数量, 'failed': 失败数量, 'duplicate': 重复数量}
        """
        if not self.news_source:
            self.logger.warning("新闻源不可用，无法抓取")
            return {'success': 0, 'failed': 0, 'duplicate': 0}
        
        try:
            self.logger.info(f"开始抓取市场新闻，限制数量: {limit}，只抓取当天: {only_today}")
            news_list = self.news_source.get_market_news(limit, only_today=only_today)
            
            if not news_list:
                self.logger.warning("未获取到市场新闻")
                return {'success': 0, 'failed': 0, 'duplicate': 0}
            
            self.logger.info(f"获取到 {len(news_list)} 条市场新闻，开始保存...")
            result = self.news_storage.save_news_batch(news_list)
            
            self.logger.info(f"市场新闻抓取完成: 成功 {result['success']}, 重复 {result['duplicate']}, 失败 {result['failed']}")
            return result
            
        except Exception as e:
            self.logger.error(f"抓取市场新闻失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'success': 0, 'failed': 1, 'duplicate': 0}
    
    def crawl_stock_news(self, symbol: str, limit: int = 20, only_today: bool = True) -> Dict[str, int]:
        """
        抓取股票新闻（只抓取当天的新闻）
        
        Args:
            symbol: 股票代码
            limit: 限制数量
            only_today: 是否只抓取当天的新闻（默认True）
            
        Returns:
            {'success': 成功数量, 'failed': 失败数量, 'duplicate': 重复数量}
        """
        if not self.news_source:
            self.logger.warning("新闻源不可用，无法抓取")
            return {'success': 0, 'failed': 0, 'duplicate': 0}
        
        try:
            self.logger.info(f"开始抓取股票 {symbol} 的新闻，限制数量: {limit}，只抓取当天: {only_today}")
            news_list = self.news_source.get_stock_news(symbol, limit, only_today=only_today)
            
            if not news_list:
                self.logger.warning(f"未获取到股票 {symbol} 的新闻")
                return {'success': 0, 'failed': 0, 'duplicate': 0}
            
            # 获取股票行业信息（用于标记板块、行业）
            sector = None
            industry = None
            try:
                from data_source.stock_data_source import StockDataSource
                data_source = StockDataSource()
                industry_info = data_source.get_stock_industry_info(symbol)
                sector = industry_info.get('sector')
                industry = industry_info.get('industry')
            except:
                pass
            
            self.logger.info(f"获取到 {len(news_list)} 条股票新闻，开始保存...")
            result = self.news_storage.save_news_batch(news_list, symbol=symbol, 
                                                      sector=sector, industry=industry)
            
            self.logger.info(f"股票 {symbol} 新闻抓取完成: 成功 {result['success']}, 重复 {result['duplicate']}, 失败 {result['failed']}")
            return result
            
        except Exception as e:
            self.logger.error(f"抓取股票 {symbol} 新闻失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'success': 0, 'failed': 1, 'duplicate': 0}
    
    def _parse_news_time(self, news_time) -> Optional[datetime]:
        """
        解析新闻时间，支持多种格式
        
        Args:
            news_time: 时间对象（datetime、str等）
        
        Returns:
            datetime对象，如果解析失败返回None
        """
        if not news_time:
            return None
        
        try:
            if isinstance(news_time, datetime):
                return news_time
            elif isinstance(news_time, str):
                # 尝试多种时间格式
                time_str = news_time.strip()
                
                # 格式1: YYYY-MM-DD HH:MM:SS
                if len(time_str) >= 19:
                    return datetime.strptime(time_str[:19], '%Y-%m-%d %H:%M:%S')
                
                # 格式2: YYYY-MM-DD
                elif len(time_str) >= 10:
                    news_datetime = datetime.strptime(time_str[:10], '%Y-%m-%d')
                    # 如果没有时间部分，设为当天的00:00:00
                    if len(time_str) == 10:
                        return news_datetime.replace(hour=0, minute=0, second=0)
                    return news_datetime
                
                # 格式3: 相对时间（今天、1小时前等）- 返回当前时间
                elif any(keyword in time_str for keyword in ['今天', '刚刚', '分钟前', '小时前']):
                    return datetime.now()
                
                # 其他格式，尝试解析
                else:
                    # 尝试常见格式
                    for fmt in ['%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d']:
                        try:
                            return datetime.strptime(time_str, fmt)
                        except:
                            continue
                    return None
            else:
                return None
        except Exception as e:
            self.logger.debug(f"解析新闻时间失败: {news_time}, 错误: {str(e)}")
            return None
    
    def _calculate_time_range(self, last_fetch_time: Optional[datetime], 
                              interval_minutes: float = 60.0) -> tuple:
        """
        计算抓取时间范围
        
        Args:
            last_fetch_time: 上次获取时间
            interval_minutes: 任务间隔（分钟）
        
        Returns:
            (start_time, end_time) 元组
        """
        now = datetime.now()
        
        if last_fetch_time:
            # 增量获取：从上次获取时间到现在
            start_time = last_fetch_time
            # 如果是凌晨00:00，往前推10分钟，避免遗漏数据
            if start_time.hour == 0 and start_time.minute == 0:
                start_time = start_time - timedelta(minutes=10)
                self.logger.info(f"检测到凌晨00:00时间点，往前推10分钟: {start_time}")
        else:
            # 首次获取：获取当天的新闻
            # 如果是凌晨00:00附近（00:00-00:10），往前推10分钟到前一天
            if now.hour == 0 and now.minute <= 10:
                start_time = (now - timedelta(days=1)).replace(hour=23, minute=50, second=0, microsecond=0)
                self.logger.info(f"检测到凌晨00:00附近，往前推10分钟到前一天: {start_time}")
            else:
                # 从当天00:00开始
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        end_time = now
        return start_time, end_time
    
    def crawl_all_news(self, limit: int = 200, last_fetch_time: Optional[datetime] = None, 
                       interval_minutes: float = 60.0, max_retries: int = 3) -> Dict[str, int]:
        """
        抓取全部新闻（增量获取），并进行关联分析
        
        Args:
            limit: 限制数量（每个新闻源）
            last_fetch_time: 上次获取时间（用于增量获取）
            interval_minutes: 任务间隔（分钟，用于计算时间范围）
            max_retries: 最大重试次数（默认3次）
        
        Returns:
            {
                'success': 成功数量, 
                'failed': 失败数量, 
                'duplicate': 重复数量,
                'source_stats': 各新闻源统计信息,
                'time_range': 时间范围信息
            }
        """
        try:
            if not self.news_source:
                self.logger.warning("新闻源不可用，无法抓取")
                return {'success': 0, 'failed': 0, 'duplicate': 0, 'source_stats': {}, 'time_range': {}}
            
            # 计算时间范围
            start_time, end_time = self._calculate_time_range(last_fetch_time, interval_minutes)
            time_range_str = f"{start_time.strftime('%Y-%m-%d %H:%M:%S')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            self.logger.info(f"开始增量抓取全部新闻，时间范围: {time_range_str}，限制数量: {limit}（每个新闻源），最大重试: {max_retries}次")
            
            # 获取新闻源数量
            source_count = len(self.news_source.sources) if hasattr(self.news_source, 'sources') else 0
            self.logger.info(f"可用新闻源数量: {source_count}")
            
            # 重试机制：如果第一次获取失败，重试
            news_list = []
            for attempt in range(max_retries):
                try:
                    # 获取市场新闻（不限制日期，获取所有新闻以便后续时间过滤）
                    # 注意：limit * 2 是为了获取更多新闻，因为后续会按时间范围过滤
                    news_list = self.news_source.get_market_news(limit=limit * 2, only_today=False)
                    
                    if news_list:
                        self.logger.info(f"第 {attempt + 1} 次尝试成功获取到 {len(news_list)} 条新闻")
                        break
                    else:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2  # 递增等待时间：2秒、4秒、6秒
                            self.logger.warning(f"第 {attempt + 1} 次尝试未获取到新闻，等待 {wait_time} 秒后重试...")
                            time.sleep(wait_time)
                        else:
                            self.logger.warning(f"经过 {max_retries} 次尝试仍未获取到新闻")
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        self.logger.warning(f"第 {attempt + 1} 次尝试获取新闻失败: {str(e)}，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"经过 {max_retries} 次尝试后仍然失败: {str(e)}")
                        import traceback
                        self.logger.error(traceback.format_exc())
            
            if not news_list:
                self.logger.warning(f"未获取到新闻，可能原因：1) 时间范围内没有新闻 2) 新闻源暂时不可用 3) 网络问题")
                return {
                    'success': 0, 
                    'failed': 0, 
                    'duplicate': 0,
                    'source_stats': {},
                    'time_range': {'start': start_time.isoformat(), 'end': end_time.isoformat()}
                }
            
            # 过滤时间范围（只保留时间范围内的新闻）
            filtered_news = []
            time_parse_failed = 0
            time_out_of_range = 0
            
            for news in news_list:
                news_time = news.get('time') or news.get('publish_time') or news.get('pub_time')
                news_datetime = self._parse_news_time(news_time)
                
                if news_datetime:
                    # 检查时间是否在范围内
                    if start_time <= news_datetime <= end_time:
                        filtered_news.append(news)
                    else:
                        time_out_of_range += 1
                else:
                    # 没有时间信息或解析失败，默认保留（可能是实时新闻）
                    if not news_time:
                        # 没有时间信息，保留（可能是实时新闻）
                        filtered_news.append(news)
                    else:
                        # 有时间信息但解析失败，也保留（避免误过滤）
                        filtered_news.append(news)
                        time_parse_failed += 1
            
            self.logger.info(
                f"获取到 {len(news_list)} 条新闻，时间过滤后 {len(filtered_news)} 条 "
                f"（时间范围外: {time_out_of_range} 条，时间解析失败: {time_parse_failed} 条）"
            )
            
            # 统计各新闻源的贡献
            source_stats = {}
            for news in filtered_news:
                source = news.get('source', '未知来源')
                source_stats[source] = source_stats.get(source, 0) + 1
            
            # 使用NewsStockMapper进行关联分析
            try:
                from utils.news_stock_mapper import NewsStockMapper
                stock_mapper = NewsStockMapper()
            except Exception as e:
                self.logger.warning(f"初始化NewsStockMapper失败: {str(e)}")
                stock_mapper = None
            
            # 大盘关键词（用于识别大盘相关新闻）
            market_keywords = ['大盘', '指数', 'A股', '沪深', '上证', '深证', '创业板', '科创板', '市场', 
                             '股市', '股市场', '资本市场', '证券', '券商', '金融']
            
            # 处理每条新闻，进行关联分析
            total_success = 0
            total_failed = 0
            total_duplicate = 0
            mapped_stocks = {}  # 统计关联到的股票数量
            
            for idx, news in enumerate(filtered_news, 1):
                try:
                    # 检查是否是大盘相关新闻
                    title = news.get('title', '')
                    content = news.get('content', '')
                    text = f"{title} {content}".lower()
                    is_market_news = any(keyword in text for keyword in market_keywords)
                    
                    # 使用NewsStockMapper分析新闻，关联到股票、板块、行业
                    symbol = None
                    sector = None
                    industry = None
                    
                    if stock_mapper:
                        try:
                            mappings = stock_mapper.map_news_to_stocks(news)
                            if mappings:
                                # 选择相关性最高的关联
                                primary_mapping = mappings[0]
                                symbol = primary_mapping.get('symbol')
                                sector = primary_mapping.get('sector') or sector
                                industry = primary_mapping.get('industry') or industry
                                
                                # 统计关联到的股票
                                if symbol:
                                    mapped_stocks[symbol] = mapped_stocks.get(symbol, 0) + 1
                                
                                if idx <= 10:  # 只记录前10条的详细日志
                                    self.logger.debug(f"新闻关联分析 [{idx}/{len(filtered_news)}]: {title[:50]}... -> 股票: {symbol}, 板块: {sector}, 行业: {industry}")
                        except Exception as e:
                            self.logger.debug(f"新闻关联分析失败 [{idx}/{len(filtered_news)}]: {str(e)}")
                    
                    # 保存新闻
                    # 如果是大盘新闻且没有关联到具体股票，symbol设为None（表示市场新闻）
                    if is_market_news and not symbol:
                        symbol = None
                    
                    news_id = self.news_storage.save_news_article(news, symbol=symbol, 
                                                                  sector=sector, industry=industry)
                    if news_id:
                        total_success += 1
                    else:
                        # news_id 为 None 表示新闻已存在（重复），save_news_article 内部会处理重复检测
                        total_duplicate += 1
                except Exception as e:
                    self.logger.error(f"处理新闻失败 [{idx}/{len(filtered_news)}]: {str(e)}")
                    total_failed += 1
                    continue
            
            # 构建详细的结果统计
            result = {
                'success': total_success,
                'failed': total_failed,
                'duplicate': total_duplicate,
                'source_stats': source_stats,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'duration_minutes': round((end_time - start_time).total_seconds() / 60, 2)
                },
                'mapped_stocks_count': len(mapped_stocks),
                'total_fetched': len(news_list),
                'total_filtered': len(filtered_news),
                'time_out_of_range': time_out_of_range,
                'time_parse_failed': time_parse_failed
            }
            
            # 详细的日志输出
            self.logger.info(
                f"全部新闻抓取完成: "
                f"成功 {total_success} 条, 重复 {total_duplicate} 条, 失败 {total_failed} 条 | "
                f"获取 {len(news_list)} 条，过滤后 {len(filtered_news)} 条 | "
                f"关联到 {len(mapped_stocks)} 只股票 | "
                f"时间范围: {time_range_str}"
            )
            
            # 输出各新闻源的贡献统计
            if source_stats:
                source_summary = ", ".join([f"{k}: {v}条" for k, v in sorted(source_stats.items(), key=lambda x: x[1], reverse=True)[:5]])
                self.logger.info(f"主要新闻源贡献（前5）: {source_summary}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"抓取全部新闻失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': 0, 
                'failed': 1, 
                'duplicate': 0,
                'source_stats': {},
                'time_range': {},
                'error': str(e)
            }
    
    def start_crawl_task(self, task_id: int, interval_minutes: int, 
                        task_type: str = 'market', symbol: Optional[str] = None):
        """
        启动定时抓取任务
        
        Args:
            task_id: 任务ID
            interval_minutes: 抓取间隔（分钟）
            task_type: 任务类型（market/stock/all）
            symbol: 股票代码（如果是股票任务）
        """
        if task_id in self.crawl_threads:
            self.logger.warning(f"任务 {task_id} 已在运行")
            return
        
        stop_flag = threading.Event()
        self.stop_flags[task_id] = stop_flag
        
        def crawl_loop():
            self.logger.info(f"启动新闻抓取任务 {task_id}: 类型={task_type}, 间隔={interval_minutes}分钟")
            
            # 首次执行立即抓取一次
            first_run = True
            
            while not stop_flag.is_set():
                try:
                    if task_type == 'market':
                        result = self.crawl_market_news(limit=NEWS_CONFIG.get('news_count', 50))
                        self.logger.info(f"任务 {task_id} 市场新闻抓取完成: 成功 {result.get('success', 0)}, 重复 {result.get('duplicate', 0)}, 失败 {result.get('failed', 0)}")
                    elif task_type == 'stock' and symbol:
                        result = self.crawl_stock_news(symbol, limit=NEWS_CONFIG.get('news_count', 20))
                        self.logger.info(f"任务 {task_id} 股票 {symbol} 新闻抓取完成: 成功 {result.get('success', 0)}, 重复 {result.get('duplicate', 0)}, 失败 {result.get('failed', 0)}")
                    elif task_type == 'all':
                        # 抓取全部新闻（增量获取），并进行关联分析
                        # 获取上次执行时间和任务间隔
                        last_fetch_time = None
                        task_interval = interval_minutes
                        try:
                            sql = "SELECT last_run_time, interval_minutes FROM news_crawl_tasks WHERE id = %s"
                            task_info = DBConnection.execute_query(sql, (task_id,))
                            if task_info and task_info[0].get('last_run_time'):
                                last_fetch_time = task_info[0]['last_run_time']
                                if isinstance(last_fetch_time, str):
                                    last_fetch_time = datetime.strptime(last_fetch_time, '%Y-%m-%d %H:%M:%S')
                                task_interval = task_info[0].get('interval_minutes', interval_minutes)
                        except Exception as e:
                            self.logger.debug(f"获取任务信息失败: {str(e)}")
                        
                        result = self.crawl_all_news(limit=NEWS_CONFIG.get('news_count', 200), 
                                                     last_fetch_time=last_fetch_time,
                                                     interval_minutes=task_interval)
                        self.logger.info(f"任务 {task_id} 全部新闻抓取完成: 成功 {result.get('success', 0)}, 重复 {result.get('duplicate', 0)}, 失败 {result.get('failed', 0)}")
                    
                    # 更新任务状态
                    self._update_task_status(task_id, success=True)
                    
                except Exception as e:
                    self.logger.error(f"抓取任务 {task_id} 执行失败: {str(e)}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    self._update_task_status(task_id, success=False, error=str(e))
                
                # 首次执行后，等待指定时间再执行下一次
                if first_run:
                    first_run = False
                else:
                    # 等待指定时间（秒）
                    # stop_flag.wait() 返回 True 如果收到停止信号，False 如果超时
                    wait_seconds = interval_minutes * 60
                    if stop_flag.wait(wait_seconds):
                        # 收到停止信号
                        break
                    # 否则继续下一轮（正常等待结束）
            
            self.logger.info(f"新闻抓取任务 {task_id} 已停止")
            if task_id in self.crawl_threads:
                del self.crawl_threads[task_id]
            if task_id in self.stop_flags:
                del self.stop_flags[task_id]
        
        thread = threading.Thread(target=crawl_loop, daemon=True, name=f"NewsCrawler-{task_id}")
        thread.start()
        self.crawl_threads[task_id] = thread
        
        self.logger.info(f"新闻抓取任务 {task_id} 已启动")
    
    def stop_crawl_task(self, task_id: int):
        """停止抓取任务"""
        if task_id in self.stop_flags:
            self.stop_flags[task_id].set()
            self.logger.info(f"已发送停止信号给任务 {task_id}")
            
            # 更新任务状态
            self._update_task_status(task_id, is_active=False)
        else:
            self.logger.warning(f"任务 {task_id} 不存在或已停止")
    
    def _update_task_status(self, task_id: int, success: bool = True, 
                           error: Optional[str] = None, is_active: Optional[bool] = None):
        """更新任务状态到数据库"""
        if not self.use_database:
            return
        
        try:
            now = datetime.now()
            next_run = now + timedelta(minutes=self._get_task_interval(task_id))
            
            if is_active is not None:
                sql = """
                    UPDATE news_crawl_tasks 
                    SET is_active = %s, updated_at = %s
                    WHERE id = %s
                """
                DBConnection.execute_update(sql, (is_active, now, task_id))
            else:
                sql = """
                    UPDATE news_crawl_tasks 
                    SET last_run_time = %s, next_run_time = %s,
                        run_count = run_count + 1,
                        success_count = success_count + %s,
                        fail_count = fail_count + %s,
                        last_error = %s,
                        updated_at = %s
                    WHERE id = %s
                """
                success_count = 1 if success else 0
                fail_count = 1 if not success else 0
                DBConnection.execute_update(
                    sql, (now, next_run, success_count, fail_count, error, now, task_id)
                )
        except Exception as e:
            self.logger.warning(f"更新任务状态失败: {str(e)}")
    
    def _get_task_interval(self, task_id: int) -> int:
        """获取任务间隔"""
        if not self.use_database:
            return 60
        
        try:
            sql = "SELECT interval_minutes FROM news_crawl_tasks WHERE id = %s"
            result = DBConnection.execute_query(sql, (task_id,))
            if result:
                return result[0].get('interval_minutes', 60)
            return 60
        except:
            return 60
