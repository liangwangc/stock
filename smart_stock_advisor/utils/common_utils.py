"""
公共工具函数模块

提供项目中常用的工具函数，避免代码重复，提高代码复用性。

主要功能：
- 股票代码规范化
- 路径处理
- 日期时间格式化
- 数据转换
- 字符串处理

使用示例：
    ```python
    from utils.common_utils import normalize_symbol, get_project_root
    
    symbol = normalize_symbol('1')  # 返回 '000001'
    root = get_project_root()  # 返回项目根目录
    ```
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Union


def get_project_root() -> str:
    """
    获取项目根目录路径
    
    获取smart_stock_advisor项目的根目录（utils目录的上级目录）。
    
    Returns:
        str: 项目根目录的绝对路径
    
    示例:
        ```python
        root = get_project_root()
        # 返回: '/path/to/smart_stock_advisor'
        ```
    """
    # 获取当前文件的目录（utils目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 返回上级目录（项目根目录）
    return os.path.dirname(current_dir)


def normalize_symbol(symbol: Union[str, int]) -> str:
    """
    规范化股票代码
    
    将股票代码转换为6位字符串格式（不足6位前面补0）。
    用于统一股票代码格式，确保数据库存储和查询的一致性。
    
    Args:
        symbol: 股票代码（可以是字符串或整数，如 '1', 1, '000001'）
    
    Returns:
        str: 规范化的6位股票代码字符串
    
    示例:
        ```python
        normalize_symbol('1')      # 返回 '000001'
        normalize_symbol(1)        # 返回 '000001'
        normalize_symbol('000001') # 返回 '000001'
        ```
    """
    return str(symbol).zfill(6)


def is_valid_symbol(symbol: Union[str, int]) -> bool:
    """
    验证股票代码格式是否有效
    
    检查股票代码是否为6位数字格式。
    
    Args:
        symbol: 股票代码
    
    Returns:
        bool: 如果格式有效返回True，否则返回False
    
    示例:
        ```python
        is_valid_symbol('000001')  # 返回 True
        is_valid_symbol('123')     # 返回 False
        is_valid_symbol('ABC')     # 返回 False
        ```
    """
    symbol_str = str(symbol).strip()
    # 检查是否为6位数字
    return symbol_str.isdigit() and len(symbol_str) == 6


def format_datetime(dt: Optional[datetime] = None, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化日期时间为字符串
    
    将datetime对象格式化为指定格式的字符串。如果不提供datetime对象，使用当前时间。
    
    Args:
        dt: datetime对象，如果为None则使用当前时间
        format_str: 格式字符串，默认 '%Y-%m-%d %H:%M:%S'
    
    Returns:
        str: 格式化后的日期时间字符串
    
    示例:
        ```python
        format_datetime()  # 返回当前时间，如 '2024-01-01 12:00:00'
        format_datetime(datetime(2024, 1, 1))  # 返回 '2024-01-01 00:00:00'
        format_datetime(format_str='%Y-%m-%d')  # 返回 '2024-01-01'
        ```
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)


def format_date(date_obj: Optional[Union[datetime, str]] = None, format_str: str = '%Y-%m-%d') -> str:
    """
    格式化日期为字符串
    
    将日期对象（datetime或date）或日期字符串格式化为指定格式。
    如果不提供日期对象，使用当前日期。
    
    Args:
        date_obj: 日期对象（datetime/date）或日期字符串，如果为None则使用当前日期
        format_str: 格式字符串，默认 '%Y-%m-%d'
    
    Returns:
        str: 格式化后的日期字符串
    
    示例:
        ```python
        format_date()  # 返回当前日期，如 '2024-01-01'
        format_date(datetime(2024, 1, 1))  # 返回 '2024-01-01'
        format_date('20240101', format_str='%Y%m%d')  # 返回 '20240101'
        ```
    """
    if date_obj is None:
        return datetime.now().strftime(format_str)
    
    if isinstance(date_obj, str):
        # 尝试解析字符串
        try:
            # 尝试多种格式
            for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
                try:
                    date_obj = datetime.strptime(date_obj, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                return date_obj  # 如果无法解析，返回原字符串
        except:
            return date_obj
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    return date_obj.strftime(format_str)


def parse_date(date_str: str, format_str: Optional[str] = None) -> Optional[datetime]:
    """
    解析日期字符串为datetime对象
    
    尝试多种格式解析日期字符串。
    
    Args:
        date_str: 日期字符串
        format_str: 指定的格式字符串，如果为None则尝试多种格式
    
    Returns:
        datetime对象，如果解析失败返回None
    
    示例:
        ```python
        parse_date('2024-01-01')  # 返回 datetime(2024, 1, 1)
        parse_date('20240101')    # 返回 datetime(2024, 1, 1)
        ```
    """
    if format_str:
        try:
            return datetime.strptime(date_str, format_str)
        except ValueError:
            return None
    
    # 尝试多种格式
    formats = ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def safe_int(value: Union[str, int, float, None], default: int = 0) -> int:
    """
    安全地将值转换为整数
    
    如果转换失败，返回默认值。
    
    Args:
        value: 要转换的值
        default: 转换失败时的默认值
    
    Returns:
        int: 转换后的整数值
    
    示例:
        ```python
        safe_int('123')    # 返回 123
        safe_int('abc')    # 返回 0
        safe_int('abc', -1) # 返回 -1
        safe_int(None)     # 返回 0
        ```
    """
    try:
        return int(float(value)) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_float(value: Union[str, int, float, None], default: float = 0.0) -> float:
    """
    安全地将值转换为浮点数
    
    如果转换失败，返回默认值。
    
    Args:
        value: 要转换的值
        default: 转换失败时的默认值
    
    Returns:
        float: 转换后的浮点数值
    
    示例:
        ```python
        safe_float('123.45')  # 返回 123.45
        safe_float('abc')     # 返回 0.0
        safe_float('abc', -1.0) # 返回 -1.0
        ```
    """
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def truncate_string(text: str, max_length: int, suffix: str = '...') -> str:
    """
    截断字符串到指定长度
    
    如果字符串超过最大长度，截断并添加后缀。
    
    Args:
        text: 要截断的字符串
        max_length: 最大长度
        suffix: 截断后添加的后缀，默认 '...'
    
    Returns:
        str: 截断后的字符串
    
    示例:
        ```python
        truncate_string('Hello World', 5)  # 返回 'He...'
        truncate_string('Hello', 10)       # 返回 'Hello'
        ```
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def ensure_dir(dir_path: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        dir_path: 目录路径
    
    Returns:
        bool: 如果目录存在或创建成功返回True，否则返回False
    
    示例:
        ```python
        ensure_dir('/path/to/dir')  # 如果目录不存在则创建
        ```
    """
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception:
        return False
