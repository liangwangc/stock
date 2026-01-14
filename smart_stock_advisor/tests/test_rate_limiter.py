"""
API访问频率限制器测试
"""
import pytest
import time
from utils.rate_limiter import RateLimiter, get_rate_limiter


class TestRateLimiter:
    """RateLimiter测试类"""
    
    def test_init(self):
        """测试初始化"""
        limiter = RateLimiter(default_limit=60, default_window=60)
        assert limiter.default_limit == 60
        assert limiter.default_window == 60
    
    def test_set_limit(self):
        """测试设置限制"""
        limiter = RateLimiter()
        limiter.set_limit("test_key", 10, 30)
        assert limiter._limits["test_key"] == (10, 30)
    
    def test_check_rate_limit_allowed(self):
        """测试检查限流（允许访问）"""
        limiter = RateLimiter(default_limit=10, default_window=60)
        key = "test_user_1"
        
        # 前10次应该允许
        for i in range(10):
            allowed, info = limiter.check_rate_limit(key, limit=10, window=60)
            assert allowed is True
            assert info['allowed'] is True
            assert info['current'] == i + 1
            assert info['remaining'] == 10 - (i + 1)
    
    def test_check_rate_limit_exceeded(self):
        """测试检查限流（超过限制）"""
        limiter = RateLimiter(default_limit=5, default_window=60)
        key = "test_user_2"
        
        # 前5次允许
        for i in range(5):
            allowed, info = limiter.check_rate_limit(key, limit=5, window=60)
            assert allowed is True
        
        # 第6次应该被限制
        allowed, info = limiter.check_rate_limit(key, limit=5, window=60)
        assert allowed is False
        assert info['allowed'] is False
        assert info['current'] == 5
        assert 'reset_after' in info
    
    def test_reset(self):
        """测试重置记录"""
        limiter = RateLimiter(default_limit=5, default_window=60)
        key = "test_user_3"
        
        # 使用5次
        for i in range(5):
            limiter.check_rate_limit(key, limit=5, window=60)
        
        # 重置
        limiter.reset(key)
        
        # 重置后应该可以再次使用
        allowed, info = limiter.check_rate_limit(key, limit=5, window=60)
        assert allowed is True
        assert info['current'] == 1
    
    def test_get_stats(self):
        """测试获取统计信息"""
        limiter = RateLimiter()
        key = "test_user_4"
        
        # 使用几次
        for i in range(3):
            limiter.check_rate_limit(key, limit=10, window=60)
        
        # 获取统计信息
        stats = limiter.get_stats(key)
        assert stats['key'] == key
        assert stats['requests'] == 3
        assert stats['limit'] == 10
        assert stats['window'] == 60
        assert stats['remaining'] == 7
    
    def test_get_global_stats(self):
        """测试获取全局统计信息"""
        limiter = RateLimiter()
        
        # 使用多个key
        for i in range(3):
            limiter.check_rate_limit(f"user_{i}", limit=10, window=60)
        
        # 获取全局统计
        stats = limiter.get_stats()
        assert stats['total_keys'] == 3
        assert stats['total_requests'] == 3
    
    def test_singleton(self):
        """测试单例模式"""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2
