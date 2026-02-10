"""
日志工具模块

提供统一的日志记录功能，基于Python标准库logging模块封装。
所有模块使用此工具获取logger实例，确保日志格式统一。

主要特性：
- 统一日志格式：时间、模块名、日志级别、消息
- 标准输出：日志输出到标准输出（stdout）
- 日志文件：同时追加写入项目根目录下的 logs/app.log（增量更新）
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
import os
from config import LOG_LEVEL, LOG_FILE

# 项目根目录（utils 的上级）
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_file_handler():
    """创建并返回日志文件 Handler（增量追加模式）"""
    try:
        log_path = os.path.join(_project_root, LOG_FILE)
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
        handler.setLevel(getattr(logging, LOG_LEVEL))
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        return handler
    except Exception as e:
        sys.stderr.write(f"[Logger] 无法创建日志文件 {LOG_FILE}: {e}\n")
        return None

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
        - 使用延迟绑定，避免在重定向stdout时出现问题
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    if not logger.handlers:
        # 使用动态StreamHandler，每次写入时检查stream是否有效
        class DynamicStreamHandler(logging.StreamHandler):
            def __init__(self):
                super().__init__(sys.stdout)
                self._last_stream = sys.stdout
            
            def emit(self, record):
                # 每次写入时检查并更新stream
                try:
                    # 检查当前stream是否有效
                    if self.stream != sys.stdout:
                        self.stream = sys.stdout
                    # 尝试写入
                    super().emit(record)
                    self._last_stream = self.stream
                except (ValueError, OSError, AttributeError) as e:
                    # 如果stream已关闭或无效，尝试恢复
                    error_msg = str(e).lower()
                    if 'closed' in error_msg or 'i/o operation' in error_msg or 'attribute' in error_msg:
                        try:
                            # 尝试使用原始的stdout
                            if hasattr(sys, 'stdout') and sys.stdout is not None:
                                self.stream = sys.stdout
                                super().emit(record)
                                self._last_stream = self.stream
                            else:
                                # 如果stdout不可用，静默失败（避免循环错误）
                                pass
                        except:
                            # 如果所有尝试都失败，静默失败（避免循环错误）
                            pass
                except Exception:
                    # 其他错误也静默处理，避免循环错误
                    pass
            
            def handleError(self, record):
                # 重写handleError，避免写入已关闭的stderr导致循环错误
                try:
                    # 尝试使用当前的stream
                    if self.stream and hasattr(self.stream, 'write'):
                        try:
                            self.stream.write(f'--- Logging error in {self.__class__.__name__} ---\n')
                        except:
                            pass
                except:
                    # 如果所有尝试都失败，静默失败（避免循环错误）
                    pass
        
        handler = DynamicStreamHandler()
        handler.setLevel(getattr(logging, LOG_LEVEL))
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # 添加文件 Handler（增量追加到 logs/app.log）
        file_handler = _get_file_handler()
        if file_handler:
            logger.addHandler(file_handler)
    
    return logger



