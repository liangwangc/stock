"""
测试美股数据源可用性
检查各个接口是否能正常获取数据
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data_source.us_stock_data_source import USStockDataSource
from utils.logger import get_logger

logger = get_logger(__name__)

def test_data_source():
    """测试数据源"""
    print("=" * 60)
    print("美股数据源测试")
    print("=" * 60)
    
    # 测试股票代码
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    # 创建数据源实例
    ds = USStockDataSource()
    
    import sys
    import io
    # 设置输出编码为UTF-8
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print(f"\n可用数据源:")
    print(f"  - akshare: {'[可用]' if ds.akshare_available else '[不可用]'}")
    print(f"  - yfinance: {'[可用]' if ds.yfinance_available else '[不可用]'}")
    
    if not ds.akshare_available and not ds.yfinance_available:
        print("\n[错误] 没有可用的数据源！")
        print("请安装: pip install akshare yfinance")
        return
    
    # 测试每个股票
    success_count = 0
    fail_count = 0
    
    for symbol in test_symbols:
        print(f"\n{'=' * 60}")
        print(f"测试股票: {symbol}")
        print(f"{'=' * 60}")
        
        try:
            # 获取最近1年的数据
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)
            
            print(f"获取日期范围: {start_date} 到 {end_date}")
            print("正在获取数据...")
            
            df = ds.get_stock_data(
                symbol=symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if df is not None and not df.empty:
                print(f"[成功] 获取数据")
                print(f"  记录数: {len(df)}")
                print(f"  日期范围: {df.index.min()} 到 {df.index.max()}")
                print(f"  列: {', '.join(df.columns)}")
                print(f"  最新收盘价: {df['close'].iloc[-1]:.2f}")
                success_count += 1
            else:
                print(f"[失败] 返回空数据")
                fail_count += 1
                
        except Exception as e:
            print(f"[失败] {str(e)}")
            fail_count += 1
    
    # 总结
    print(f"\n{'=' * 60}")
    print("测试总结")
    print(f"{'=' * 60}")
    print(f"成功: {success_count}/{len(test_symbols)}")
    print(f"失败: {fail_count}/{len(test_symbols)}")
    
    if success_count > 0:
        print("\n[通过] 至少有一个数据源可用")
    else:
        print("\n[失败] 所有数据源均失败")
        print("\n建议:")
        print("1. 检查网络连接")
        print("2. 检查API是否有限制")
        print("3. 考虑使用其他数据源（如Alpha Vantage、Polygon.io、Finnhub）")
        print("4. 查看增强版数据源: data_source/us_stock_data_source_enhanced.py")

if __name__ == '__main__':
    test_data_source()
