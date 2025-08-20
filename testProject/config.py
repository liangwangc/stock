#!/usr/bin/env python3
"""
数据库配置文件

包含所有数据库相关的配置信息
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class DatabaseConfig:
    """数据库配置类"""
    
    # 数据库类型 - 设置为MySQL
    DATABASE_TYPE = "mysql"
    
    # SQLite配置
    SQLITE_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
    
    # MySQL配置 - 直接配置你的MySQL信息
    MYSQL_CONFIG = {
        "host": "192.168.0.215",
        "port": 3306,
        "database": "nanan_data",
        "user": "root",
        "password": "Cdslyk@912",
        "charset": "utf8mb4"
    }
    
    # PostgreSQL配置
    POSTGRES_CONFIG = {
        "host": os.getenv("DATABASE_HOST", "localhost"),
        "port": int(os.getenv("DATABASE_PORT", "5432")),
        "database": os.getenv("DATABASE_NAME", "myapp"),
        "user": os.getenv("DATABASE_USER", "postgres"),
        "password": os.getenv("DATABASE_PASSWORD", ""),
    }
    
    # Redis配置
    REDIS_CONFIG = {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db": int(os.getenv("REDIS_DB", "0")),
        "password": os.getenv("REDIS_PASSWORD", None),
        "decode_responses": True
    }
    
    @classmethod
    def get_database_url(cls) -> str:
        """获取数据库连接URL"""
        if cls.DATABASE_TYPE == "mysql":
            config = cls.MYSQL_CONFIG
            return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        elif cls.DATABASE_TYPE == "postgresql":
            config = cls.POSTGRES_CONFIG
            return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        else:
            return cls.SQLITE_DATABASE_URL
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """获取数据库配置字典"""
        if cls.DATABASE_TYPE == "mysql":
            return cls.MYSQL_CONFIG
        elif cls.DATABASE_TYPE == "postgresql":
            return cls.POSTGRES_CONFIG
        else:
            return {"database_url": cls.SQLITE_DATABASE_URL}


class Config:
    """应用配置类"""
    
    # 应用配置
    APP_NAME = os.getenv("APP_NAME", "Python项目")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # 数据库配置
    DATABASE_CONFIG = DatabaseConfig()
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_LEVEL", "app.log")
    
    # 安全配置
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    @classmethod
    def is_development(cls) -> bool:
        """是否为开发环境"""
        return cls.ENVIRONMENT.lower() == "development"
    
    @classmethod
    def is_production(cls) -> bool:
        """是否为生产环境"""
        return cls.ENVIRONMENT.lower() == "production"


# 创建配置实例
config = Config() 