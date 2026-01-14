"""
测试Alpha Vantage API密钥是否能正常获取美股数据
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data_source.us_stock_data_source_enhanced import EnhancedUSStockDataSource
from utils.logger import get_logger

logger = get_logger(__name__)

def test_alpha_vantage():
    """测试Alpha Vantage数据源"""
    print("=" * 60)
    print("Alpha Vantage API 测试")
    print("=" * 60)
    
    # API密钥
    api_key = "F2HOLBGJCDQBIE7W"
    
    # 创建增强版数据源实例
    print(f"\n正在初始化数据源...")
    ds = EnhancedUSStockDataSource(alpha_vantage_api_key=api_key)
    
    print(f"\n可用数据源:")
    print(f"  - akshare: {'[可用]' if 'akshare' in ds.data_sources else '[不可用]'}")
    print(f"  - yfinance: {'[可用]' if 'yfinance' in ds.data_sources else '[不可用]'}")
    print(f"  - alpha_vantage: {'[可用]' if 'alpha_vantage' in ds.data_sources else '[不可用]'}")
    print(f"  - polygon: {'[可用]' if 'polygon' in ds.data_sources else '[不可用]'}")
    print(f"  - finnhub: {'[可用]' if 'finnhub' in ds.data_sources else '[不可用]'}")
    
    if 'alpha_vantage' not in ds.data_sources:
        print("\n[错误] Alpha Vantage数据源未启用！")
        print("请检查API密钥是否正确配置。")
        return
    
    # 测试股票代码
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    print(f"\n{'=' * 60}")
    print("开始测试数据获取...")
    print(f"{'=' * 60}")
    
    success_count = 0
    fail_count = 0
    
    for symbol in test_symbols:
        print(f"\n测试股票: {symbol}")
        print("-" * 60)
        
        try:
            # 获取最近1年的数据
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)
            
            print(f"获取日期范围: {start_date} 到 {end_date}")
            print("正在获取数据（Alpha Vantage免费版限制：每分钟5次请求，请耐心等待）...")
            
            df = ds.get_stock_data(
                symbol=symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if df is not None and not df.empty:
                print(f"[成功] 获取数据成功")
                print(f"  记录数: {len(df)}")
                print(f"  日期范围: {df.index.min()} 到 {df.index.max()}")
                print(f"  列: {', '.join(df.columns)}")
                if 'close' in df.columns:
                    print(f"  最新收盘价: {df['close'].iloc[-1]:.2f}")
                    print(f"  最早收盘价: {df['close'].iloc[0]:.2f}")
                success_count += 1
            else:
                print(f"[失败] 返回空数据")
                fail_count += 1
                
        except Exception as e:
            print(f"[失败] 获取数据失败: {str(e)}")
            fail_count += 1
    
    # 总结
    print(f"\n{'=' * 60}")
    print("测试总结")
    print(f"{'=' * 60}")
    print(f"成功: {success_count}/{len(test_symbols)}")
    print(f"失败: {fail_count}/{len(test_symbols)}")
    
    if success_count > 0:
        print("\n[通过] Alpha Vantage API密钥可用！")
        print("\n建议:")
        print("1. 可以将API密钥设置为环境变量:")
        print("   Windows PowerShell: $env:ALPHA_VANTAGE_API_KEY = 'F2HOLBGJCDQBIE7W'")
        print("2. 或者在代码中直接使用EnhancedUSStockDataSource时传入密钥")
        print("3. 注意：Alpha Vantage免费版限制每分钟5次请求，每天500次")
    else:
        print("\n[失败] 所有测试均失败")
        print("\n可能原因:")
        print("1. API密钥无效或已过期")
        print("2. 网络连接问题")
        print("3. API服务暂时不可用")
        print("4. 已达到API请求限制")

if __name__ == '__main__':
    test_alpha_vantage()
