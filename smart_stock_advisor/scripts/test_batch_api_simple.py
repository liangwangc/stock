"""
简单测试批量API功能
验证代码逻辑是否正确
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import akshare as ak
from data_source.stock_data_source import _call_akshare_without_proxy
from utils.logger import get_logger

logger = get_logger(__name__)


def test_batch_api():
    """测试批量API是否能正常调用"""
    print("=" * 80)
    print("测试批量API调用")
    print("=" * 80)
    
    print("\n1. 测试 ak.stock_zh_a_spot_em() 批量API...")
    print(f"   开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    start_time = datetime.now()
    
    try:
        # 测试批量API调用
        df = _call_akshare_without_proxy(ak.stock_zh_a_spot_em)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"   结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   耗时: {duration:.2f}秒")
        
        if df is None or df.empty:
            print("   [失败] API返回空数据")
            return False
        
        print(f"   [成功] 成功获取数据")
        print(f"   - 股票数量: {len(df)}")
        print(f"   - 列名: {list(df.columns)[:10]}...")  # 显示前10个列名
        
        # 检查必要的列
        code_col = None
        name_col = None
        for col in df.columns:
            col_s = str(col)
            if code_col is None and ('代码' in col_s or col_s.lower() in ['code', 'symbol']):
                code_col = col
            if name_col is None and ('名称' in col_s or col_s.lower() in ['name']):
                name_col = col
        
        if code_col is None:
            print("   [失败] 无法识别股票代码列")
            return False
        
        print(f"   - 代码列: {code_col}")
        if name_col:
            print(f"   - 名称列: {name_col}")
        
        # 显示前5条数据
        print(f"\n2. 数据示例（前5条）:")
        for i, (idx, row) in enumerate(df.head(5).iterrows(), 1):
            symbol = str(row[code_col]).strip()
            name = str(row.get(name_col, 'N/A')).strip() if name_col else 'N/A'
            print(f"   {i}. {symbol} - {name}")
        
        # 检查数据字段
        print(f"\n3. 检查数据字段...")
        price_fields = ['今开', '最新价', '最高', '最低', '昨收']
        volume_fields = ['成交量', '成交额']
        other_fields = ['涨跌幅', '涨跌额', '换手率', '振幅']
        
        available_price_fields = [f for f in price_fields if f in df.columns]
        available_volume_fields = [f for f in volume_fields if f in df.columns]
        available_other_fields = [f for f in other_fields if f in df.columns]
        
        print(f"   - 价格字段: {len(available_price_fields)}/{len(price_fields)}")
        print(f"     可用: {available_price_fields}")
        print(f"   - 成交字段: {len(available_volume_fields)}/{len(volume_fields)}")
        print(f"     可用: {available_volume_fields}")
        print(f"   - 其他字段: {len(available_other_fields)}/{len(other_fields)}")
        print(f"     可用: {available_other_fields}")
        
        # 性能评估
        print(f"\n4. 性能评估:")
        if duration < 5:
            print(f"   ⭐ 性能优秀！耗时 {duration:.2f}秒")
        elif duration < 30:
            print(f"   ✅ 性能良好，耗时 {duration:.2f}秒")
        else:
            print(f"   ⚠️  性能一般，耗时 {duration:.2f}秒")
        
        # 估算5400只股票的耗时
        if len(df) > 0:
            print(f"   - 当前获取 {len(df)} 只股票，耗时 {duration:.2f}秒")
            print(f"   - 预计5400只股票耗时: {duration:.2f}秒（批量API一次性获取）")
            print(f"   - vs 逐只获取: 约 {5400 * 1.5 / 60:.1f}分钟（假设每只1.5秒）")
        
        print("\n" + "=" * 80)
        print("[成功] 测试通过！批量API功能正常")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"   结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   耗时: {duration:.2f}秒")
        print(f"\n   [失败] API调用失败: {str(e)}")
        
        error_msg = str(e)
        is_network_error = (
            'Connection' in error_msg or
            'RemoteDisconnected' in error_msg or
            'timeout' in error_msg.lower() or
            'ECONNRESET' in error_msg
        )
        
        if is_network_error:
            print(f"\n   [警告] 网络连接错误")
            print(f"   建议:")
            print(f"   1. 检查网络连接")
            print(f"   2. 检查防火墙设置")
            print(f"   3. 稍后重试")
            print(f"   4. 如果持续失败，可能是API服务器问题")
        else:
            print(f"\n   [警告] API调用错误")
            print(f"   建议:")
            print(f"   1. 检查akshare版本是否最新")
            print(f"   2. 检查API是否可用")
            print(f"   3. 查看详细错误信息")
        
        print("\n" + "=" * 80)
        print("[失败] 测试失败（网络或API问题）")
        print("=" * 80)
        
        return False


if __name__ == '__main__':
    try:
        success = test_batch_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
