"""
新闻系统定时任务调度器
统一管理新闻获取和LLM分析任务
"""
import sys
import os
import schedule
import time
import logging
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.data_processing.get_cls_news import fetch_and_store_news
from src.analysis.main import job as llm_analysis_job

# 配置日志
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f'scheduler_{datetime.now().strftime("%Y%m%d")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def news_fetch_job():
    """新闻获取任务"""
    try:
        logger.info("=" * 60)
        logger.info("开始执行新闻获取任务")
        logger.info("=" * 60)
        fetch_and_store_news()
        logger.info("新闻获取任务完成")
    except Exception as e:
        logger.error(f"新闻获取任务失败: {str(e)}", exc_info=True)


def llm_analysis_job_wrapper():
    """LLM分析任务包装器"""
    try:
        logger.info("=" * 60)
        logger.info("开始执行LLM分析任务")
        logger.info("=" * 60)
        llm_analysis_job()
        logger.info("LLM分析任务完成")
    except Exception as e:
        logger.error(f"LLM分析任务失败: {str(e)}", exc_info=True)


def setup_schedules():
    """设置定时任务"""
    # 配置：可以根据需要修改这些时间间隔
    
    # 新闻获取：每10分钟执行一次
    schedule.every(10).minutes.do(news_fetch_job)
    logger.info("已设置新闻获取任务：每10分钟执行一次")
    
    # LLM分析：每2小时执行一次（可以根据需要调整）
    schedule.every(2).hours.do(llm_analysis_job_wrapper)
    logger.info("已设置LLM分析任务：每2小时执行一次")
    
    # 可选：每天特定时间执行
    # schedule.every().day.at("09:00").do(news_fetch_job)
    # schedule.every().day.at("01:00").do(llm_analysis_job_wrapper)


def run_scheduler():
    """运行调度器"""
    logger.info("=" * 80)
    logger.info("新闻系统定时任务调度器启动")
    logger.info("=" * 80)
    logger.info(f"日志文件: {log_file}")
    
    # 设置定时任务
    setup_schedules()
    
    # 启动时是否立即执行一次（可选）
    # logger.info("启动时立即执行一次新闻获取...")
    # news_fetch_job()
    
    logger.info("调度器运行中，按 Ctrl+C 停止...")
    logger.info("=" * 80)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭调度器...")
        schedule.clear()
        logger.info("调度器已停止")


if __name__ == '__main__':
    run_scheduler()
