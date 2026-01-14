"""
测试A股优化功能
测试所有已实现的优化功能是否能正常获取数据并工作
"""
import sys
import os
from datetime import datetime

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from data_source.stock_data_source import StockDataSource
from predictor.realtime_trading_advisor import RealtimeTradingAdvisor
from predictor.stock_predictor import StockPredictor

def test_limit_up_down_strategy():
    """测试涨跌停板交易策略"""
    print("\n" + "="*60)
    print("测试1: 涨跌停板交易策略")
    print("="*60)
    
    try:
        advisor = RealtimeTradingAdvisor()
        data_source = StockDataSource()
        
        # 测试股票：贵州茅台（600519）
        symbol = "600519"
        
        # 获取实时行情
        quote = data_source.get_realtime_quote(symbol)
        if not quote or not quote.get('current_price'):
            print(f"  ❌ 无法获取 {symbol} 的实时行情")
            return False
        
        current_price = quote.get('current_price', 0)
        limit_up = quote.get('limit_up', 0)
        limit_down = quote.get('limit_down', 0)
        
        print(f"  股票代码: {symbol}")
        print(f"  当前价格: {current_price:.2f}元")
        print(f"  涨停价: {limit_up:.2f}元")
        print(f"  跌停价: {limit_down:.2f}元")
        
        # 获取买卖盘数据
        bid_ask = data_source.get_bid_ask_data(symbol)
        
        # 测试涨停板策略
        if limit_up > 0:
            limit_up_strategy = advisor.calculate_limit_up_strategy(
                symbol, current_price, limit_up, bid_ask
            )
            if limit_up_strategy.get('available'):
                print(f"  ✅ 涨停板策略计算成功")
                print(f"     距离涨停: {limit_up_strategy.get('distance_to_limit', 0):.2f}%")
                print(f"     是否涨停: {limit_up_strategy.get('is_limit_up', False)}")
                print(f"     是否接近涨停: {limit_up_strategy.get('is_near_limit', False)}")
                print(f"     建议: {limit_up_strategy.get('suggestion', '')}")
            else:
                print(f"  ⚠️ 涨停板策略不可用: {limit_up_strategy.get('reason', '')}")
        
        # 测试跌停板策略
        if limit_down > 0:
            limit_down_strategy = advisor.calculate_limit_down_strategy(
                symbol, current_price, limit_down
            )
            if limit_down_strategy.get('available'):
                print(f"  ✅ 跌停板策略计算成功")
                print(f"     距离跌停: {limit_down_strategy.get('distance_to_limit', 0):.2f}%")
                print(f"     是否跌停: {limit_down_strategy.get('is_limit_down', False)}")
                print(f"     是否接近跌停: {limit_down_strategy.get('is_near_limit', False)}")
                print(f"     建议: {limit_down_strategy.get('suggestion', '')}")
            else:
                print(f"  ⚠️ 跌停板策略不可用: {limit_down_strategy.get('reason', '')}")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_t1_optimization():
    """测试T+1制度优化"""
    print("\n" + "="*60)
    print("测试2: T+1制度优化")
    print("="*60)
    
    try:
        advisor = RealtimeTradingAdvisor()
        predictor = StockPredictor()
        
        symbol = "600519"
        
        # 执行预测
        prediction_result = predictor.predict(symbol)
        if not prediction_result.get('success'):
            print(f"  ❌ 无法获取 {symbol} 的预测结果")
            return False
        
        # 测试持仓周期优化
        holding_optimization = advisor.optimize_holding_period(symbol, prediction_result)
        if holding_optimization.get('available'):
            print(f"  ✅ T+1持仓周期优化计算成功")
            print(f"     是否建议买入: {holding_optimization.get('should_buy', False)}")
            print(f"     资金占用成本: {holding_optimization.get('capital_cost', 0):.2f}元")
            print(f"     机会成本: {holding_optimization.get('opportunity_cost', 0):.2f}元")
            print(f"     净收益: {holding_optimization.get('net_benefit', 0):.2f}元")
            print(f"     建议: {holding_optimization.get('suggestion', '')}")
        else:
            print(f"  ⚠️ T+1优化不可用: {holding_optimization.get('reason', '')}")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_auction_strategy():
    """测试集合竞价策略"""
    print("\n" + "="*60)
    print("测试3: 集合竞价策略增强")
    print("="*60)
    
    try:
        advisor = RealtimeTradingAdvisor()
        data_source = StockDataSource()
        predictor = StockPredictor()
        
        symbol = "600519"
        
        # 获取集合竞价数据
        auction_data = data_source.get_auction_data(symbol)
        print(f"  集合竞价数据: {auction_data}")
        
        # 执行预测
        prediction_result = predictor.predict(symbol)
        if not prediction_result.get('success'):
            print(f"  ❌ 无法获取 {symbol} 的预测结果")
            return False
        
        # 测试集合竞价策略
        auction_strategy = advisor.calculate_auction_strategy(
            symbol, prediction_result, auction_data
        )
        if auction_strategy.get('available'):
            print(f"  ✅ 集合竞价策略计算成功")
            print(f"     是否参与竞价: {auction_strategy.get('should_participate', False)}")
            print(f"     建议竞价价格: {auction_strategy.get('auction_price', 0):.2f}元")
            print(f"     建议: {auction_strategy.get('suggestion', '')}")
        else:
            print(f"  ⚠️ 集合竞价策略不可用: {auction_strategy.get('reason', '')}")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_suspension_detection():
    """测试停牌检测和处理"""
    print("\n" + "="*60)
    print("测试4: 停牌检测和处理")
    print("="*60)
    
    try:
        data_source = StockDataSource()
        
        # 测试正常股票
        symbol = "600519"
        suspension_info = data_source.check_suspension(symbol)
        print(f"  股票代码: {symbol}")
        print(f"  是否停牌: {suspension_info.get('is_suspended', False)}")
        if suspension_info.get('is_suspended'):
            print(f"     停牌原因: {suspension_info.get('reason', '未知')}")
            print(f"     策略建议: {suspension_info.get('strategy', '')}")
        else:
            print(f"  ✅ 股票正常交易")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_st_stock_detection():
    """测试ST股票特殊处理"""
    print("\n" + "="*60)
    print("测试5: ST股票特殊处理")
    print("="*60)
    
    try:
        data_source = StockDataSource()
        
        # 测试正常股票
        symbol = "600519"
        st_info = data_source.check_st_stock(symbol)
        print(f"  股票代码: {symbol}")
        print(f"  是否ST股票: {st_info.get('is_st', False)}")
        if st_info.get('is_st'):
            print(f"     风险等级: {st_info.get('risk_level', '')}")
            print(f"     涨跌停限制: ±{st_info.get('limit_pct', 0)*100:.0f}%")
            print(f"     警告: {st_info.get('warning', '')}")
        else:
            print(f"  ✅ 非ST股票，正常交易")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_dragon_tiger_list():
    """测试龙虎榜数据分析"""
    print("\n" + "="*60)
    print("测试6: 龙虎榜数据分析")
    print("="*60)
    
    try:
        advisor = RealtimeTradingAdvisor()
        
        # 测试股票：选择一个可能有龙虎榜数据的股票
        symbol = "600519"
        
        # 测试龙虎榜分析
        dragon_tiger_analysis = advisor.analyze_dragon_tiger_list(symbol)
        if dragon_tiger_analysis.get('available'):
            print(f"  ✅ 龙虎榜分析成功")
            print(f"     机构净流入: {dragon_tiger_analysis.get('institution_net', 0)/10000:.2f}万元")
            print(f"     游资净流入: {dragon_tiger_analysis.get('hot_money_net', 0)/10000:.2f}万元")
            print(f"     总净流入: {dragon_tiger_analysis.get('total_net', 0)/10000:.2f}万元")
            print(f"     分析得分: {dragon_tiger_analysis.get('score', 0):.2f}")
            print(f"     影响: {dragon_tiger_analysis.get('impact', 'neutral')}")
            print(f"     建议: {dragon_tiger_analysis.get('suggestion', '')}")
        else:
            print(f"  ⚠️ 龙虎榜数据不可用: {dragon_tiger_analysis.get('reason', '无数据')}")
            print(f"     说明: 可能该股票近期未上龙虎榜")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_market_sentiment_index():
    """测试市场情绪指标（恐慌指数、贪婪指数）"""
    print("\n" + "="*60)
    print("测试7: 市场情绪指标（恐慌指数、贪婪指数）")
    print("="*60)
    
    try:
        predictor = StockPredictor()
        
        # 测试市场情绪指标
        sentiment_index = predictor.calculate_market_sentiment_index()
        if sentiment_index.get('available'):
            print(f"  ✅ 市场情绪指标计算成功")
            print(f"     恐慌指数: {sentiment_index.get('fear_index', 50):.1f}")
            print(f"     贪婪指数: {sentiment_index.get('greed_index', 50):.1f}")
            print(f"     综合情绪: {sentiment_index.get('sentiment', 'neutral')}")
            print(f"     建议: {sentiment_index.get('suggestion', '')}")
            
            market_stats = sentiment_index.get('market_stats', {})
            if market_stats:
                print(f"     市场统计:")
                print(f"       总股票数: {market_stats.get('total_stocks', 0)}")
                print(f"       上涨股票比例: {market_stats.get('rising_stocks_pct', 0):.2f}%")
                print(f"       下跌股票比例: {market_stats.get('falling_stocks_pct', 0):.2f}%")
                print(f"       涨停股票数: {market_stats.get('limit_up_count', 0)}")
                print(f"       跌停股票数: {market_stats.get('limit_down_count', 0)}")
            
            if sentiment_index.get('emotional_trading'):
                print(f"     ⚠️ 情绪化交易警告: {sentiment_index.get('emotional_reason', '')}")
        else:
            print(f"  ⚠️ 市场情绪指标不可用: {sentiment_index.get('suggestion', '无法获取数据')}")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_restricted_shares():
    """测试限售股解禁追踪"""
    print("\n" + "="*60)
    print("测试8: 限售股解禁追踪")
    print("="*60)
    
    try:
        advisor = RealtimeTradingAdvisor()
        
        # 测试股票
        symbol = "600519"
        
        # 测试限售股解禁追踪
        restricted_info = advisor.track_restricted_shares(symbol)
        if restricted_info.get('has_restricted'):
            print(f"  ✅ 限售股解禁追踪成功")
            print(f"     最近解禁日期: {restricted_info.get('next_lift_date', '未知')}")
            if restricted_info.get('days_to_lift') is not None:
                print(f"     距离解禁: {restricted_info.get('days_to_lift', 0)}天")
            print(f"     解禁数量: {restricted_info.get('lift_volume', 0)/100000000:.2f}亿股")
            print(f"     解禁比例: {restricted_info.get('lift_ratio', 0)*100:.2f}%")
            print(f"     限售股比例: {restricted_info.get('restricted_ratio', 0)*100:.2f}%")
            print(f"     影响评估: {restricted_info.get('impact', 'minimal')}")
            if restricted_info.get('warning'):
                print(f"     警告: {restricted_info.get('warning', '')}")
            if restricted_info.get('suggestion'):
                print(f"     建议: {restricted_info.get('suggestion', '')}")
        else:
            print(f"  ⚠️ 无限售股或数据不足: {restricted_info.get('reason', restricted_info.get('note', '未知'))}")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_realtime_decision_integration():
    """测试实时交易决策整合"""
    print("\n" + "="*60)
    print("测试9: 实时交易决策整合（综合测试）")
    print("="*60)
    
    try:
        advisor = RealtimeTradingAdvisor()
        
        symbol = "600519"
        
        print(f"  股票代码: {symbol}")
        print(f"  正在获取实时交易决策...")
        
        # 获取实时交易决策（包含所有优化功能）
        result = advisor.get_realtime_decision(symbol=symbol, holding=False)
        
        if not result.get('success'):
            print(f"  ❌ 获取实时交易决策失败: {result.get('message', '未知错误')}")
            return False
        
        print(f"  ✅ 实时交易决策获取成功")
        
        # 检查各个优化功能是否包含在结果中
        decision = result.get('decision', {})
        print(f"\n  交易决策:")
        print(f"     操作建议: {decision.get('action_cn', '未知')}")
        print(f"     信号强度: {decision.get('strength_cn', '未知')}")
        
        # 检查涨跌停板策略
        limit_strategy = decision.get('limit_strategy', {})
        if limit_strategy.get('limit_up') or limit_strategy.get('limit_down'):
            print(f"  ✅ 涨跌停板策略已整合")
        
        # 检查T+1优化
        if decision.get('holding_period_optimization'):
            print(f"  ✅ T+1制度优化已整合")
        
        # 检查集合竞价策略
        if result.get('auction_strategy'):
            print(f"  ✅ 集合竞价策略已整合")
        
        # 检查停牌和ST股票
        if result.get('suspension_info'):
            print(f"  ✅ 停牌检测已整合")
        if result.get('st_info'):
            print(f"  ✅ ST股票检测已整合")
        
        # 检查龙虎榜分析
        if result.get('dragon_tiger_analysis'):
            print(f"  ✅ 龙虎榜分析已整合")
        
        # 检查限售股解禁
        if result.get('restricted_shares_info'):
            print(f"  ✅ 限售股解禁追踪已整合")
        
        # 显示决策理由
        reasons = decision.get('reasons', [])
        if reasons:
            print(f"\n  决策理由:")
            for i, reason in enumerate(reasons[:5], 1):
                print(f"     {i}. {reason}")
        
        # 显示风险警告
        warnings = decision.get('risk_warnings', [])
        if warnings:
            print(f"\n  风险警告:")
            for i, warning in enumerate(warnings[:5], 1):
                print(f"     {i}. {warning}")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("A股优化功能测试")
    print("="*80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 执行各项测试
    test_results.append(("涨跌停板交易策略", test_limit_up_down_strategy()))
    test_results.append(("T+1制度优化", test_t1_optimization()))
    test_results.append(("集合竞价策略增强", test_auction_strategy()))
    test_results.append(("停牌检测和处理", test_suspension_detection()))
    test_results.append(("ST股票特殊处理", test_st_stock_detection()))
    test_results.append(("龙虎榜数据分析", test_dragon_tiger_list()))
    test_results.append(("市场情绪指标", test_market_sentiment_index()))
    test_results.append(("限售股解禁追踪", test_restricted_shares()))
    test_results.append(("实时交易决策整合", test_realtime_decision_integration()))
    
    # 输出测试总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    print("="*80)
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️ 有 {total - passed} 项测试失败，请检查上述错误信息")

if __name__ == '__main__':
    main()
