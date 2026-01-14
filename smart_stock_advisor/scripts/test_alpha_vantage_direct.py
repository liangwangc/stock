"""
直接测试Alpha Vantage API
"""
import requests
import json
from datetime import datetime, timedelta

api_key = "F2HOLBGJCDQBIE7W"
symbol = "AAPL"

print("=" * 60)
print("直接测试Alpha Vantage API")
print("=" * 60)
print(f"API密钥: {api_key}")
print(f"股票代码: {symbol}")
print()

# 测试API调用
url = "https://www.alphavantage.co/query"
params = {
    'function': 'TIME_SERIES_DAILY',  # 使用免费端点
    'symbol': symbol,
    'apikey': api_key,
    'outputsize': 'compact'  # 先测试compact（最近100条）
}

print("正在调用API...")
print(f"URL: {url}")
print(f"参数: {params}")
print()

try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    print("API响应:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()
    
    # 检查错误
    if 'Error Message' in data:
        print(f"[错误] {data['Error Message']}")
    elif 'Note' in data:
        print(f"[提示] {data['Note']}")
    elif 'Time Series (Daily)' in data:
        time_series = data['Time Series (Daily)']
        print(f"[成功] 获取到 {len(time_series)} 条数据")
        print("\n最近5条数据:")
        count = 0
        for date_str, values in sorted(time_series.items(), reverse=True):
            if count >= 5:
                break
            # TIME_SERIES_DAILY的字段名
            print(f"  {date_str}: 收盘价={values['4. close']}, 成交量={values['5. volume']}")
            count += 1
    else:
        print("[未知] API返回了意外的数据格式")
        print("响应键:", list(data.keys()))
        
except Exception as e:
    print(f"[异常] {str(e)}")
    import traceback
    traceback.print_exc()
