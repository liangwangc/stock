#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试自适应学习功能
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.adaptive_learning_strategy import AdaptiveLearningStrategy
from utils.online_learning import OnlineLearning
from utils.model_performance_evaluator import ModelPerformanceEvaluator
from utils.adaptive_learning_integration import AdaptiveLearningIntegration
import json


def test_adaptive_strategy():
    """测试自适应学习策略"""
    print("=" * 60)
    print("测试自适应学习策略")
    print("=" * 60)
    
    strategy = AdaptiveLearningStrategy()
    
    # 1. 计算市场波动率
    print("\n1. 计算市场波动率")
    volatility = strategy.calculate_market_volatility(days=30)
    print(f"市场波动率: {volatility:.2%}")
    
    # 2. 确定学习频率
    print("\n2. 确定学习频率")
    frequency_info = strategy.determine_learning_frequency(base_frequency_days=7)
    print(f"建议学习频率: {frequency_info['frequency_days']}天")
    print(f"原因: {frequency_info['reason']}")
    print(f"市场波动率: {frequency_info['volatility']:.2%}")
    
    # 3. 判断是否触发学习
    print("\n3. 判断是否触发学习")
    trigger_info = strategy.should_trigger_learning()
    print(f"是否应该触发: {trigger_info['should_trigger']}")
    print(f"原因: {trigger_info['reason']}")
    if trigger_info.get('accuracy_info'):
        acc_info = trigger_info['accuracy_info']
        print(f"当前准确率: {acc_info.get('current_accuracy', 0):.2%}")
        print(f"趋势: {acc_info.get('trend', '未知')}")
    
    # 4. 确定学习范围
    print("\n4. 确定学习范围")
    range_info = strategy.determine_learning_range()
    print(f"建议学习范围: {range_info['days']}天")
    print(f"原因: {range_info['reason']}")
    print(f"市场状态: {range_info['market_state']}")
    
    # 5. 检查市场状态变化
    print("\n5. 检查市场状态变化")
    state_change = strategy.check_market_state_change(days=7)
    print(f"是否变化: {state_change['has_changed']}")
    print(f"当前状态: {state_change['current_state']}")
    print(f"之前状态: {state_change['previous_state']}")
    
    print("\n" + "=" * 60)


def test_online_learning():
    """测试在线学习"""
    print("=" * 60)
    print("测试在线学习")
    print("=" * 60)
    
    online_learning = OnlineLearning()
    
    # 批量更新权重
    print("\n批量更新权重（使用最近7天数据）")
    result = online_learning.batch_update_weights(days=7)
    
    if result.get('success'):
        print(f"✓ 批量更新成功")
        print(f"样本数: {result.get('sample_count', 0)}")
        print(f"新权重配置:")
        new_weights = result.get('new_weights', {})
        for key, value in new_weights.items():
            print(f"  {key}: {value:.4f}")
    else:
        print(f"✗ 批量更新失败: {result.get('message', '未知错误')}")
    
    print("\n" + "=" * 60)


def test_evaluator():
    """测试评估器"""
    print("=" * 60)
    print("测试评估器（增强功能）")
    print("=" * 60)
    
    evaluator = ModelPerformanceEvaluator()
    
    # 1. 多指标综合评估
    print("\n1. 多指标综合评估")
    comprehensive_result = evaluator.evaluate_comprehensive_performance(days=30)
    if comprehensive_result.get('success'):
        print(f"✓ 综合评估成功")
        print(f"综合得分: {comprehensive_result.get('comprehensive_score', 0):.4f}")
        if comprehensive_result.get('trading_score'):
            print(f"交易得分: {comprehensive_result.get('trading_score', 0):.4f}")
        metrics = comprehensive_result.get('metrics', {})
        print(f"方向准确率: {metrics.get('direction_accuracy', 0):.2%}")
        print(f"幅度得分: {metrics.get('magnitude_score', 0):.4f}")
        print(f"校准得分: {metrics.get('calibration_score', 0):.4f}")
    else:
        print(f"✗ 综合评估失败: {comprehensive_result.get('message', '未知错误')}")
    
    # 2. 分市场状态评估
    print("\n2. 分市场状态评估")
    market_state_result = evaluator.evaluate_by_market_state(days=30)
    if market_state_result.get('success'):
        print(f"✓ 分市场状态评估成功")
        eval_by_state = market_state_result.get('evaluation_by_state', {})
        for state, eval_data in eval_by_state.items():
            print(f"\n{state}:")
            print(f"  样本数: {eval_data.get('sample_count', 0)}")
            print(f"  方向准确率: {eval_data.get('direction_accuracy', 0):.2%}")
            print(f"  幅度误差(MAE): {eval_data.get('magnitude_mae', 0):.4f}")
            print(f"  平均置信度: {eval_data.get('avg_confidence', 0):.4f}")
    else:
        print(f"✗ 分市场状态评估失败: {market_state_result.get('message', '未知错误')}")
    
    # 3. 置信度校准评估
    print("\n3. 置信度校准评估")
    calibration_result = evaluator.evaluate_confidence_calibration(days=30)
    if calibration_result.get('success'):
        print(f"✓ 置信度校准评估成功")
        print(f"期望校准误差(ECE): {calibration_result.get('expected_calibration_error', 0):.4f}")
        print(f"最大校准误差(MCE): {calibration_result.get('max_calibration_error', 0):.4f}")
        print(f"校准质量: {calibration_result.get('calibration_quality', '未知')}")
        print(f"样本数: {calibration_result.get('total_samples', 0)}")
    else:
        print(f"✗ 置信度校准评估失败: {calibration_result.get('message', '未知错误')}")
    
    print("\n" + "=" * 60)


def test_integration():
    """测试集成功能"""
    print("=" * 60)
    print("测试集成功能")
    print("=" * 60)
    
    integration = AdaptiveLearningIntegration()
    
    # 1. 获取学习建议
    print("\n1. 获取学习建议")
    recommendations = integration.get_learning_recommendations()
    if recommendations.get('success'):
        print("✓ 获取学习建议成功")
        recs = recommendations.get('recommendations', {})
        
        print(f"\n学习频率建议:")
        freq_info = recs.get('frequency', {})
        print(f"  频率: {freq_info.get('frequency_days', 0)}天")
        print(f"  原因: {freq_info.get('reason', '')}")
        
        print(f"\n学习范围建议:")
        range_info = recs.get('range', {})
        print(f"  范围: {range_info.get('days', 0)}天")
        print(f"  原因: {range_info.get('reason', '')}")
        
        print(f"\n触发检查:")
        trigger_info = recs.get('trigger_check', {})
        print(f"  是否触发: {trigger_info.get('should_trigger', False)}")
        print(f"  原因: {trigger_info.get('reasons', [])}")
    else:
        print(f"✗ 获取学习建议失败: {recommendations.get('message', '未知错误')}")
    
    # 2. 检查是否触发学习
    print("\n2. 检查是否触发学习")
    trigger_check = integration.check_and_trigger_learning()
    print(f"是否应该触发: {trigger_check.get('should_trigger', False)}")
    print(f"原因: {trigger_check.get('reasons', [])}")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    print("\n开始测试自适应学习功能...\n")
    
    try:
        # 测试自适应学习策略
        test_adaptive_strategy()
        
        # 测试在线学习
        test_online_learning()
        
        # 测试评估器
        test_evaluator()
        
        # 测试集成功能
        test_integration()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
