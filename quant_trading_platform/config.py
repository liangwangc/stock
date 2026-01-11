"""
配置文件
"""

# 数据存储路径
DATA_DIR = "data"

# 默认交易参数
DEFAULT_CASH = 1000000  # 初始资金：100万
DEFAULT_COMMISSION = 0.0003  # 手续费率：0.03%（万三）
DEFAULT_SLIPPAGE = 0.001  # 滑点：0.1%

# 回测参数
START_DATE = "20240101"  # 回测开始日期
END_DATE = "20251231"  # 回测结束日期

# 默认股票池（示例）
DEFAULT_STOCKS = [
    "601727",  # 上海电气
]

# 数据源配置
DATA_SOURCE = "akshare"  # 数据源：akshare

# 日志配置
LOG_LEVEL = "INFO"

# 广发证券API配置（需要申请API权限）
GF_API_CONFIG = {
    "api_key": "",  # 请填写您的API密钥
    "api_secret": "",  # 请填写您的API密钥
    "app_id": "",  # 请填写您的应用ID
    "base_url": "https://openapi.gf.com.cn",  # API基础URL
    "enabled": False  # 是否启用广发证券API（需要先配置API密钥）
}

