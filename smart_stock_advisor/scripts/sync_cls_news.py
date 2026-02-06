"""
定时同步财联社新闻数据
从 news-analysis-system-main 的数据库同步新闻和分析结果
"""
import os
import sys
import schedule
import time
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.news_sync_from_cls import NewsSyncFromCls
from utils.logger import get_logger

logger = get_logger(__name__)


def sync_job():
    """执行同步任务"""
    logger.info("=" * 80)
    logger.info(f"开始执行财联社新闻同步任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        sync = NewsSyncFromCls()
        
        # 同步最近1小时的新闻（避免同步过多历史数据）
        since = datetime.now() - timedelta(hours=1)
        result = sync.sync_all(news_limit=500, analysis_limit=500)
        
        logger.info("同步任务完成:")
        logger.info(f"  新闻: 成功={result['news']['synced']}, 跳过={result['news']['skipped']}, 失败={result['news']['failed']}")
        logger.info(f"  分析结果: 成功={result['analysis']['synced']}, 跳过={result['analysis']['skipped']}, 失败={result['analysis']['failed']}")
        logger.info(f"  总计: 成功={result['total_synced']}, 跳过={result['total_skipped']}, 失败={result['total_failed']}")
        
    except Exception as e:
        logger.error(f"同步任务执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 配置同步频率（默认每5分钟执行一次）
    SYNC_INTERVAL_MINUTES = int(os.getenv('CLS_SYNC_INTERVAL', '5'))
    
    logger.info(f"财联社新闻同步服务启动")
    logger.info(f"同步间隔: {SYNC_INTERVAL_MINUTES} 分钟")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 启动时立即执行一次
    sync_job()
    
    # 定时执行
    schedule.every(SYNC_INTERVAL_MINUTES).minutes.do(sync_job)
    
    # 运行调度循环
    while True:
        schedule.run_pending()
        time.sleep(1)
