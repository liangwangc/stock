#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Tushare各个新闻源
"""
import os
import sys
import io

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

# 直接读取token
TUSHARE_TOKEN = "773d7c4add914e2632426899d9ee52296e059334223a467e8cd07870"

def test_tushare_news_sources():
    """测试Tushare各个新闻源"""
    print("=" * 80)
    print("测试Tushare各个新闻源")
    print("=" * 80)
    
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        print(f"\n[OK] Tushare API初始化成功")
        
        # 测试各个新闻源
        news_sources = {
            'yicai': '第一财经',
            'fenghuang': '凤凰财经',
            '10jqka': '同花顺',
            'jinrongjie': '金融界',
            'sina': '新浪财经',
            'yuncaijing': '云财经',
            'eastmoney': '东方财富',
        }
        
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n时间范围: {start_date} 到 {end_date}")
        print("\n" + "-" * 80)
        
        for src, name in news_sources.items():
            print(f"\n测试新闻源: {name} (src={src})")
            try:
                df = pro.news(src=src, start_date=start_date, end_date=end_date)
                
                if df is not None and not df.empty:
                    print(f"  [OK] 获取到 {len(df)} 条新闻")
                    print(f"  数据列: {list(df.columns)}")
                    
                    # 显示前3条
                    for i, (idx, row) in enumerate(df.head(3).iterrows(), 1):
                        title = str(row.get('title', '无标题'))[:60]
                        print(f"    {i}. {title}")
                else:
                    print(f"  [信息] 未获取到新闻（可能该时间段内没有新闻）")
                    
            except AttributeError as e:
                print(f"  [FAIL] news接口不可用: {str(e)}")
                print(f"  可能原因：接口不存在或没有权限")
            except Exception as e:
                print(f"  [FAIL] 获取失败: {str(e)}")
        
        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)
        
    except ImportError:
        print("\n[FAIL] tushare库未安装")
        print("请运行: pip install tushare")
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_tushare_news_sources()
