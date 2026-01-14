"""
API访问频率限制模块
实现API访问频率限制，防止恶意请求和过载
"""
import time
from typing import Dict, Tuple
from collections import defaultdict, deque
import threading
from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """API访问频率限制器"""
    
    def __init__(self, default_limit: int = 60, default_window: int = 60):
        """
        初始化限流器
        
        Args:
            default_limit: 默认限制次数（每分钟）
            default_window: 默认时间窗口（秒）
        """
        self.default_limit = default_limit
        self.default_window = default_window
        self._records: Dict[str, deque] = defaultdict(lambda: deque())
        self._limits: Dict[str, Tuple[int, int]] = {}  # {key: (limit, window)}
        self._lock = threading.Lock()
    
    def set_limit(self, key: str, limit: int, window: int = None):
        """
        设置特定key的访问限制
        
        Args:
            key: 限制key（如用户ID、IP地址）
            limit: 限制次数
            window: 时间窗口（秒），默认使用default_window
        """
        if window is None:
            window = self.default_window
        
        with self._lock:
            self._limits[key] = (limit, window)
    
    def check_rate_limit(self, key: str, limit: int = None, window: int = None) -> Tuple[bool, Dict]:
        """
        检查是否超过访问频率限制
        
        Args:
            key: 限制key（如用户ID、IP地址）
            limit: 限制次数（可选，使用配置的限制）
            window: 时间窗口（秒，可选，使用配置的窗口）
        
        Returns:
            (是否允许访问, 详细信息字典)
        """
        with self._lock:
            # 获取限制配置
            if limit is None or window is None:
                if key in self._limits:
                    limit, window = self._limits[key]
                else:
                    limit = limit or self.default_limit
                    window = window or self.default_window
            
            current_time = time.time()
            records = self._records[key]
            
            # 清理过期记录
            while records and current_time - records[0] > window:
                records.popleft()
            
            # 检查是否超过限制
            if len(records) >= limit:
                # 计算需要等待的时间
                oldest_time = records[0] if records else current_time
                wait_time = window - (current_time - oldest_time)
                
                return False, {
                    'allowed': False,
                    'limit': limit,
                    'window': window,
                    'current': len(records),
                    'reset_after': max(0, wait_time)
                }
            
            # 记录本次访问
            records.append(current_time)
            
            return True, {
                'allowed': True,
                'limit': limit,
                'window': window,
                'current': len(records),
                'remaining': limit - len(records),
                'reset_after': window
            }
    
    def reset(self, key: str = None):
        """
        重置访问记录
        
        Args:
            key: 要重置的key，如果为None则重置所有
        """
        with self._lock:
            if key is None:
                self._records.clear()
            elif key in self._records:
                del self._records[key]
    
    def get_stats(self, key: str = None) -> Dict:
        """
        获取访问统计信息
        
        Args:
            key: 要查询的key，如果为None则返回全局统计
        
        Returns:
            统计信息字典
        """
        current_time = time.time()
        
        with self._lock:
            if key is None:
                # 返回全局统计
                total_keys = len(self._records)
                total_requests = sum(len(records) for records in self._records.values())
                return {
                    'total_keys': total_keys,
                    'total_requests': total_requests
                }
            else:
                # 返回特定key的统计
                if key not in self._records:
                    return {'key': key, 'requests': 0}
                
                records = self._records[key]
                # 清理过期记录
                while records and current_time - records[0] > self.default_window:
                    records.popleft()
                
                limit, window = self._limits.get(key, (self.default_limit, self.default_window))
                
                return {
                    'key': key,
                    'requests': len(records),
                    'limit': limit,
                    'window': window,
                    'remaining': max(0, limit - len(records))
                }


# 全局限流器实例
_rate_limiter = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器实例（单例模式）"""
    global _rate_limiter
    
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter(default_limit=60, default_window=60)
    
    return _rate_limiter
