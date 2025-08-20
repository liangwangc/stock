"""
主程序测试

测试主程序中的函数和功能。
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from project_name.main import hello_world, get_app_info, main


class TestHelloWorld:
    """测试hello_world函数"""
    
    def test_hello_world_with_name(self):
        """测试带名字的问候"""
        result = hello_world("Alice")
        assert result == "Hello, Alice!"
    
    def test_hello_world_without_name(self):
        """测试不带名字的问候（使用默认值）"""
        with patch.dict(os.environ, {}, clear=True):
            result = hello_world()
            assert result == "Hello, World!"
    
    def test_hello_world_with_env_user(self):
        """测试使用环境变量USER的问候"""
        with patch.dict(os.environ, {"USER": "Bob"}, clear=True):
            result = hello_world()
            assert result == "Hello, Bob!"


class TestGetAppInfo:
    """测试get_app_info函数"""
    
    def test_get_app_info_default_values(self):
        """测试默认值"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_app_info()
            assert result["name"] == "Python项目"
            assert result["version"] == "0.1.0"
            assert result["environment"] == "development"
            assert result["debug"] is False
    
    def test_get_app_info_with_env_vars(self):
        """测试环境变量设置"""
        env_vars = {
            "APP_NAME": "测试应用",
            "APP_VERSION": "1.0.0",
            "ENVIRONMENT": "production",
            "DEBUG": "true"
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = get_app_info()
            assert result["name"] == "测试应用"
            assert result["version"] == "1.0.0"
            assert result["environment"] == "production"
            assert result["debug"] is True
    
    def test_get_app_info_debug_false(self):
        """测试DEBUG为false的情况"""
        with patch.dict(os.environ, {"DEBUG": "false"}, clear=True):
            result = get_app_info()
            assert result["debug"] is False


class TestMain:
    """测试main函数"""
    
    @patch('builtins.print')
    def test_main_execution(self, mock_print):
        """测试main函数执行"""
        with patch.dict(os.environ, {}, clear=True):
            main()
            
            # 验证打印调用
            assert mock_print.call_count > 0
            
            # 验证关键输出
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert "Python项目启动" in print_calls
            assert "程序执行完成" in print_calls


if __name__ == "__main__":
    pytest.main([__file__]) 