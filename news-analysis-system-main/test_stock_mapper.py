"""
测试股票匹配模块
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.data_processing.stock_mapper import StockMapper

def test_stock_mapper():
    """测试股票匹配功能"""
    print("=" * 80)
    print("测试股票匹配模块")
    print("=" * 80)
    
    try:
        # 创建股票匹配器
        print("\n1. 初始化股票匹配器...")
        mapper = StockMapper()
        print("   [成功] 股票匹配器初始化完成")
        
        # 测试案例1：包含股票代码的新闻
        print("\n2. 测试案例1：包含股票代码的新闻")
        test_title1 = "贵州茅台发布2024年业绩报告"
        test_content1 = "贵州茅台(600519)今日发布2024年业绩报告，净利润同比增长15%"
        result1 = mapper.map_news_to_stocks(test_title1, test_content1)
        print(f"   标题: {test_title1}")
        print(f"   内容: {test_content1}")
        print(f"   匹配结果:")
        print(f"   - 主要股票: {result1.get('primary_symbol')}")
        print(f"   - 所有股票: {result1.get('symbols')}")
        print(f"   - 板块: {result1.get('sector')}")
        print(f"   - 行业: {result1.get('industry')}")
        print(f"   - 相关性得分: {result1.get('relevance_score')}")
        
        # 测试案例2：包含股票名称的新闻
        print("\n3. 测试案例2：包含股票名称的新闻")
        test_title2 = "中国平安发布季度财报"
        test_content2 = "中国平安保险集团今日发布第三季度财报，业绩表现良好"
        result2 = mapper.map_news_to_stocks(test_title2, test_content2)
        print(f"   标题: {test_title2}")
        print(f"   内容: {test_content2}")
        print(f"   匹配结果:")
        print(f"   - 主要股票: {result2.get('primary_symbol')}")
        print(f"   - 所有股票: {result2.get('symbols')}")
        print(f"   - 板块: {result2.get('sector')}")
        print(f"   - 行业: {result2.get('industry')}")
        
        # 测试案例3：行业相关新闻
        print("\n4. 测试案例3：行业相关新闻（无具体股票）")
        test_title3 = "银行板块整体上涨"
        test_content3 = "今日银行板块整体表现强劲，多家银行股价上涨"
        result3 = mapper.map_news_to_stocks(test_title3, test_content3)
        print(f"   标题: {test_title3}")
        print(f"   内容: {test_content3}")
        print(f"   匹配结果:")
        print(f"   - 主要股票: {result3.get('primary_symbol')}")
        print(f"   - 所有股票: {result3.get('symbols')}")
        print(f"   - 板块: {result3.get('sector')}")
        print(f"   - 行业: {result3.get('industry')}")
        
        # 总结
        print("\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)
        print("[成功] 股票匹配模块测试完成")
        print("\n功能说明:")
        print("1. 股票代码提取：支持6位数字代码（600xxx, 000xxx等）")
        print("2. 股票名称匹配：支持完整名称、去除后缀、简称匹配")
        print("3. 行业匹配：基于行业关键词匹配相关股票")
        print("4. 相关性计算：直接匹配得分1.0，行业匹配得分0.5-0.7")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n[失败] 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_stock_mapper()
    sys.exit(0 if success else 1)
