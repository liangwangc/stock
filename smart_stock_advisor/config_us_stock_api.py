"""
美股数据源API密钥配置
可以将此文件中的密钥设置为环境变量，或直接在此文件中配置
"""
import os

# Alpha Vantage API密钥
# 免费注册：https://www.alphavantage.co/support/#api-key
# 免费版限制：每分钟5次请求，每天500次
ALPHA_VANTAGE_API_KEY = "F2HOLBGJCDQBIE7W"

# Polygon.io API密钥（可选）
# 免费注册：https://polygon.io/
# 免费版限制：每分钟5次请求
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', None)

# Finnhub API密钥（可选）
# 免费注册：https://finnhub.io/
# 免费版限制：每分钟60次请求
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', None)

# 设置环境变量（如果还没有设置）
if not os.getenv('ALPHA_VANTAGE_API_KEY'):
    os.environ['ALPHA_VANTAGE_API_KEY'] = ALPHA_VANTAGE_API_KEY
