"""
pytest配置文件
提供测试用的fixtures和配置
"""
import sys
import os
import pytest

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture(scope="session")
def project_root_path():
    """返回项目根目录路径"""
    return project_root


@pytest.fixture(scope="function")
def mock_db_config(monkeypatch):
    """模拟数据库配置（测试时不连接真实数据库）"""
    monkeypatch.setenv("USE_DATABASE", "False")
    monkeypatch.setattr("config_db.USE_DATABASE", False)
    monkeypatch.setattr("config_db.DB_CONFIG", {
        'host': 'localhost',
        'port': 3307,
        'user': 'test_user',
        'password': 'test_password',
        'database': 'test_db',
        'charset': 'utf8mb4',
        'autocommit': True,
        'connect_timeout': 10,
    })


@pytest.fixture(scope="function")
def mock_logger(monkeypatch):
    """模拟日志记录器"""
    import logging
    mock_logger = logging.getLogger("test")
    mock_logger.setLevel(logging.DEBUG)
    return mock_logger
