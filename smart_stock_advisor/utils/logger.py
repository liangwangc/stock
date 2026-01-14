"""
日志工具模块

提供统一的日志记录功能，基于Python标准库logging模块封装。
所有模块使用此工具获取logger实例，确保日志格式统一。

主要特性：
- 统一日志格式：时间、模块名、日志级别、消息
- 标准输出：日志输出到标准输出（stdout）
- 日志级别：从配置文件读取（LOG_LEVEL）
- 单例模式：每个模块名只创建一个logger实例

使用示例：
    ```python
    from utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    ```

作者：Smart Stock Advisor Team
创建日期：2024
最后更新：2024
"""
import logging
import sys
from config import LOG_LEVEL

def get_logger(name: str) -> logging.Logger:
    """
    获取logger实例
    
    根据模块名获取或创建logger实例。如果logger已存在（已添加handler），
    直接返回；否则创建新的logger并配置handler。
    
    Args:
        name: 模块名称，通常使用 __name__（如 'utils.backup_manager'）
    
    Returns:
        logging.Logger: 配置好的logger实例
    
    Note:
        - logger级别从配置文件的LOG_LEVEL读取
        - 日志格式：时间 - 模块名 - 级别 - 消息
        - 输出到标准输出（stdout），可由上层重定向到文件
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, LOG_LEVEL))
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger



