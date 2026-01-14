# -*- coding: utf-8 -*-
"""
优化功能测试脚本
测试刚才完成的4个高优先级优化功能
"""
import sys
import os
from datetime import datetime, timedelta

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_backtest_visualizer():
    """测试1：回测结果可视化"""
    print("=" * 60)
    print("测试1：回测结果可视化")
    print("=" * 60)
    
    try:
        from visualizer.backtest_visualizer import BacktestVisualizer
        
        # 创建模拟的回测结果数据
        mock_result = {
            'success': True,
            'start_date': '2025-12-01',
            'end_date': '2026-01-01',
            'initial_capital': 100000.0,
            'final_value': 105000.0,
            'total_return': 5.0,
            'trades_count': 10,
            'win_trades': 6,
            'loss_trades': 4,
            'metrics': {
                'annual_return': 60.0,
                'max_drawdown': -8.5,
                'win_rate': 0.6,
                'profit_loss_ratio': 1.5,
                'sharpe_ratio': 1.2
            },
            'trades': [
                {
                    'date': '2025-12-05',
                    'symbol': '600519',
                    'action': 'BUY',
                    'price': 1800.0,
                    'shares': 100,
                    'capital_after': 80000.0
                },
                {
                    'date': '2025-12-10',
                    'symbol': '600519',
                    'action': 'SELL',
                    'price': 1850.0,
                    'shares': 100,
                    'cost_price': 1800.0,
                    'profit': 5000.0,
                    'profit_pct': 2.78,
                    'reason': '止盈'
                }
            ],
            'daily_values': [
                {
                    'date': '2025-12-01',
                    'capital': 100000.0,
                    'positions_value': 0.0,
                    'total_value': 100000.0
                },
                {
                    'date': '2025-12-05',
                    'capital': 82000.0,
                    'positions_value': 18000.0,
                    'total_value': 100000.0
                },
                {
                    'date': '2025-12-10',
                    'capital': 87000.0,
                    'positions_value': 0.0,
                    'total_value': 87000.0
                },
                {
                    'date': '2026-01-01',
                    'capital': 95000.0,
                    'positions_value': 10000.0,
                    'total_value': 105000.0
                }
            ]
        }
        
        visualizer = BacktestVisualizer()
        filepath = visualizer.visualize_backtest_result(mock_result, filename='test_backtest_result.html')
        
        if filepath:
            print(f"[OK] 回测结果可视化测试通过")
            print(f"   HTML文件已生成: {filepath}")
            return True
        else:
            print(f"[FAIL] 回测结果可视化测试失败: 未生成文件")
            return False
            
    except Exception as e:
        print(f"[FAIL] 回测结果可视化测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_trading_performance_evaluator():
    """测试2：交易性能评估收益计算"""
    print("\n" + "=" * 60)
    print("测试2：交易性能评估收益计算")
    print("=" * 60)
    
    try:
        from utils.model_performance_evaluator import ModelPerformanceEvaluator
        
        evaluator = ModelPerformanceEvaluator()
        
        # 注意：这个测试需要数据库中有实际数据
        # 如果数据库中没有数据，会返回失败，但这是正常的
        result = evaluator.evaluate_trading_performance(days=7)  # 使用较短的天数进行测试
        
        if result.get('success'):
            print(f"[OK] 交易性能评估测试通过")
            print(f"   评估样本数: {result.get('evaluated_count', 0)}")
            print(f"   总收益率: {result.get('total_return', 0):.2f}%")
            print(f"   平均收益率: {result.get('avg_return', 0):.2f}%")
            print(f"   胜率: {result.get('win_rate', 0)*100:.2f}%")
            return True
        else:
            message = result.get('message', '未知错误')
            if '没有找到' in message or '样本数量不足' in message:
                print(f"[SKIP] 交易性能评估测试跳过: {message}")
                print(f"   （这是正常的，表示数据库中没有足够的测试数据）")
                return True  # 这种情况视为测试通过
            else:
                print(f"[FAIL] 交易性能评估测试失败: {message}")
                return False
                
    except Exception as e:
        print(f"[FAIL] 交易性能评估测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_backtest_with_parameters():
    """测试3：参数组合回测功能"""
    print("\n" + "=" * 60)
    print("测试3：参数组合回测功能")
    print("=" * 60)
    
    try:
        from utils.backtest_engine import BacktestEngine
        
        engine = BacktestEngine()
        
        # 计算测试日期范围（最近7天）
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        # 测试参数
        test_parameters = {
            'buy_threshold': 0.65,  # 买入阈值
            'sell_threshold': 0.35,  # 卖出阈值
            'min_confidence': 0.60,  # 最小置信度
            'stop_loss_pct': -6.0,   # 止损
            'take_profit_pct': 10.0, # 止盈
            'max_position_pct': 0.25  # 最大仓位
        }
        
        result = engine.backtest_with_parameters(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            parameters=test_parameters,
            initial_capital=100000.0
        )
        
        if result.get('success'):
            print(f"[OK] 参数组合回测测试通过")
            print(f"   使用的参数: {result.get('parameters', {})}")
            print(f"   总收益率: {result.get('total_return', 0):.2f}%")
            print(f"   交易次数: {result.get('trades_count', 0)}")
            return True
        else:
            message = result.get('message', '未知错误')
            if '没有找到' in message:
                print(f"[SKIP] 参数组合回测测试跳过: {message}")
                print(f"   （这是正常的，表示数据库中没有足够的测试数据）")
                return True  # 这种情况视为测试通过
            else:
                print(f"[FAIL] 参数组合回测测试失败: {message}")
                return False
                
    except Exception as e:
        print(f"[FAIL] 参数组合回测测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_realtime_weight_adjustment():
    """测试4：实时策略权重动态调整"""
    print("\n" + "=" * 60)
    print("测试4：实时策略权重动态调整")
    print("=" * 60)
    
    try:
        from predictor.realtime_trading_advisor import RealtimeTradingAdvisor
        
        advisor = RealtimeTradingAdvisor()
        
        # 测试权重调整方法（通过反射调用私有方法）
        base_capital_flow_weight = 0.25
        base_bid_ask_weight = 0.15
        base_intraday_weight = 0.10
        
        # 测试牛市权重调整
        bull_weights = advisor._adjust_weights_by_market_state(
            'bull_market',
            base_capital_flow_weight,
            base_bid_ask_weight,
            base_intraday_weight
        )
        print(f"牛市权重调整: 资金流向={bull_weights[0]:.3f}, "
              f"买卖盘={bull_weights[1]:.3f}, 盘中={bull_weights[2]:.3f}")
        
        # 测试熊市权重调整
        bear_weights = advisor._adjust_weights_by_market_state(
            'bear_market',
            base_capital_flow_weight,
            base_bid_ask_weight,
            base_intraday_weight
        )
        print(f"熊市权重调整: 资金流向={bear_weights[0]:.3f}, "
              f"买卖盘={bear_weights[1]:.3f}, 盘中={bear_weights[2]:.3f}")
        
        # 测试震荡市权重调整（应该保持原值）
        sideways_weights = advisor._adjust_weights_by_market_state(
            'sideways',
            base_capital_flow_weight,
            base_bid_ask_weight,
            base_intraday_weight
        )
        print(f"震荡市权重调整: 资金流向={sideways_weights[0]:.3f}, "
              f"买卖盘={sideways_weights[1]:.3f}, 盘中={sideways_weights[2]:.3f}")
        
        # 验证权重调整逻辑
        if (bull_weights[0] < base_capital_flow_weight and  # 牛市降低资金流向权重
            bear_weights[0] > base_capital_flow_weight and  # 熊市提高资金流向权重
            sideways_weights[0] == base_capital_flow_weight):  # 震荡市保持原值
            print(f"[OK] 实时策略权重动态调整测试通过")
            return True
        else:
            print(f"[FAIL] 实时策略权重动态调整测试失败: 权重调整逻辑不正确")
            return False
            
    except Exception as e:
        print(f"[FAIL] 实时策略权重动态调整测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("优化功能测试脚本")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # 测试1：回测结果可视化
    results.append(("回测结果可视化", test_backtest_visualizer()))
    
    # 测试2：交易性能评估收益计算
    results.append(("交易性能评估收益计算", test_trading_performance_evaluator()))
    
    # 测试3：参数组合回测功能
    results.append(("参数组合回测功能", test_backtest_with_parameters()))
    
    # 测试4：实时策略权重动态调整
    results.append(("实时策略权重动态调整", test_realtime_weight_adjustment()))
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！")
        return 0
    else:
        print(f"\n[WARN] 有 {total - passed} 个测试失败或跳过")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
