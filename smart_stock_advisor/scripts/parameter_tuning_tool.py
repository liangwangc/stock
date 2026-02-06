"""
参数调优工具
用于对X2指标、异常检测、ML动态权重进行组合调参

"组合调参"的含义：
- 不是修改功能代码，而是调整参数数值
- 通过回测验证不同参数组合的效果
- 找到最优的参数配置，提升预测准确性

当前需要调优的参数：
1. X2指标阈值：超买(80)、超卖(20)、偏高(60)、偏低(40)
2. X2指标得分：超买(-0.15)、超卖(0.15)、偏高(-0.05)、偏低(0.05)
3. 异常检测置信度调整：ST股票(-20%)、涨跌停(-10%)
4. ML动态权重范围：默认权重(15%)、最小权重(0%)、最大权重(25%)
5. ML权重计算阈值：准确率>60%、50-60%、<50%的权重计算方式
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection
from utils.model_performance_evaluator import ModelPerformanceEvaluator

logger = get_logger(__name__)


class ParameterTuningTool:
    """参数调优工具"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        self.evaluator = ModelPerformanceEvaluator()
        
        # 当前参数配置（从代码中提取的默认值）
        self.current_params = {
            # X2指标阈值
            'x2_overbought_threshold': 80,      # 超买阈值
            'x2_oversold_threshold': 20,        # 超卖阈值
            'x2_high_threshold': 60,            # 偏高阈值
            'x2_low_threshold': 40,             # 偏低阈值
            
            # X2指标得分
            'x2_overbought_score': -0.15,       # 超买得分
            'x2_oversold_score': 0.15,          # 超卖得分
            'x2_high_score': -0.05,             # 偏高得分
            'x2_low_score': 0.05,               # 偏低得分
            
            # 异常检测置信度调整
            'st_stock_confidence_reduction': 0.20,  # ST股票置信度降低20%
            'limit_up_down_confidence_reduction': 0.10,  # 涨跌停置信度降低10%
            
            # ML动态权重
            'ml_default_weight': 0.15,          # 默认权重15%
            'ml_min_weight': 0.0,              # 最小权重0%
            'ml_max_weight': 0.25,             # 最大权重25%
            
            # ML权重计算阈值
            'ml_high_accuracy_threshold': 0.60,    # 高准确率阈值60%
            'ml_medium_accuracy_threshold': 0.50,  # 中等准确率阈值50%
            
            # ML权重计算系数
            'ml_high_accuracy_weight_base': 0.15,   # 高准确率基础权重
            'ml_high_accuracy_weight_multiplier': 0.25,  # 高准确率权重倍数
            'ml_medium_accuracy_weight_base': 0.10,  # 中等准确率基础权重
            'ml_medium_accuracy_weight_multiplier': 0.50,  # 中等准确率权重倍数
            'ml_low_accuracy_weight_multiplier': 0.20,  # 低准确率权重倍数
        }
    
    def generate_parameter_combinations(self) -> List[Dict]:
        """
        生成参数组合（用于网格搜索）
        
        Returns:
            参数组合列表
        """
        combinations = []
        
        # X2指标阈值组合
        x2_thresholds = [
            {'overbought': 75, 'oversold': 25, 'high': 55, 'low': 45},  # 更保守
            {'overbought': 80, 'oversold': 20, 'high': 60, 'low': 40},  # 当前值
            {'overbought': 85, 'oversold': 15, 'high': 65, 'low': 35},  # 更激进
        ]
        
        # X2指标得分组合
        x2_scores = [
            {'overbought': -0.10, 'oversold': 0.10, 'high': -0.03, 'low': 0.03},  # 更温和
            {'overbought': -0.15, 'oversold': 0.15, 'high': -0.05, 'low': 0.05},  # 当前值
            {'overbought': -0.20, 'oversold': 0.20, 'high': -0.08, 'low': 0.08},  # 更强烈
        ]
        
        # 异常检测置信度调整组合
        anomaly_reductions = [
            {'st': 0.15, 'limit': 0.08},   # 更温和
            {'st': 0.20, 'limit': 0.10},  # 当前值
            {'st': 0.25, 'limit': 0.12},  # 更强烈
        ]
        
        # ML权重范围组合
        ml_weight_ranges = [
            {'default': 0.12, 'min': 0.0, 'max': 0.20},   # 更保守
            {'default': 0.15, 'min': 0.0, 'max': 0.25},   # 当前值
            {'default': 0.18, 'min': 0.0, 'max': 0.30},   # 更激进
        ]
        
        # 生成所有组合（简化：只测试关键组合）
        for x2_thresh in x2_thresholds:
            for x2_score in x2_scores:
                for anomaly_red in anomaly_reductions:
                    for ml_range in ml_weight_ranges:
                        combo = {
                            'x2_overbought_threshold': x2_thresh['overbought'],
                            'x2_oversold_threshold': x2_thresh['oversold'],
                            'x2_high_threshold': x2_thresh['high'],
                            'x2_low_threshold': x2_thresh['low'],
                            'x2_overbought_score': x2_score['overbought'],
                            'x2_oversold_score': x2_score['oversold'],
                            'x2_high_score': x2_score['high'],
                            'x2_low_score': x2_score['low'],
                            'st_stock_confidence_reduction': anomaly_red['st'],
                            'limit_up_down_confidence_reduction': anomaly_red['limit'],
                            'ml_default_weight': ml_range['default'],
                            'ml_min_weight': ml_range['min'],
                            'ml_max_weight': ml_range['max'],
                        }
                        combinations.append(combo)
        
        self.logger.info(f"生成了 {len(combinations)} 个参数组合")
        return combinations
    
    def evaluate_parameters(self, params: Dict, days: int = 30) -> Dict:
        """
        评估参数组合的效果
        
        Args:
            params: 参数配置字典
            days: 回测天数
        
        Returns:
            评估结果字典，包含准确率、收益率等指标
        """
        try:
            # 这里需要实际运行预测和回测
            # 由于涉及修改代码中的硬编码参数，这里提供一个框架
            
            # 1. 评估预测准确率
            evaluation_result = self.evaluator.evaluate_prediction_performance(days=days)
            
            # 2. 计算回测收益
            # TODO: 实现回测逻辑
            
            result = {
                'params': params,
                'direction_accuracy': evaluation_result.get('direction_accuracy', 0),
                'magnitude_mae': evaluation_result.get('magnitude_mae', 0),
                'calibration_score': evaluation_result.get('calibration_score', 0),
                'sample_count': evaluation_result.get('sample_count', 0),
                'evaluation_date': datetime.now().strftime('%Y-%m-%d'),
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"评估参数失败: {str(e)}")
            return {
                'params': params,
                'error': str(e)
            }
    
    def find_optimal_parameters(self, days: int = 30) -> Dict:
        """
        寻找最优参数组合
        
        Args:
            days: 回测天数
        
        Returns:
            最优参数配置和评估结果
        """
        self.logger.info("=" * 60)
        self.logger.info("开始参数调优")
        self.logger.info("=" * 60)
        
        # 生成参数组合
        combinations = self.generate_parameter_combinations()
        
        # 评估每个组合
        results = []
        for i, combo in enumerate(combinations):
            self.logger.info(f"\n评估参数组合 {i+1}/{len(combinations)}...")
            result = self.evaluate_parameters(combo, days=days)
            results.append(result)
        
        # 找到最优组合（按准确率排序）
        valid_results = [r for r in results if 'error' not in r]
        if not valid_results:
            self.logger.error("没有有效的评估结果")
            return {}
        
        # 按准确率排序
        valid_results.sort(key=lambda x: x.get('direction_accuracy', 0), reverse=True)
        
        optimal = valid_results[0]
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("参数调优结果")
        self.logger.info("=" * 60)
        self.logger.info(f"最优参数组合:")
        self.logger.info(json.dumps(optimal['params'], indent=2, ensure_ascii=False))
        self.logger.info(f"\n评估指标:")
        self.logger.info(f"  方向准确率: {optimal.get('direction_accuracy', 0)*100:.2f}%")
        self.logger.info(f"  幅度MAE: {optimal.get('magnitude_mae', 0):.4f}")
        self.logger.info(f"  校准分数: {optimal.get('calibration_score', 0)*100:.2f}%")
        self.logger.info(f"  样本数: {optimal.get('sample_count', 0)}")
        
        return optimal
    
    def save_optimal_parameters(self, optimal_params: Dict, filename: str = None):
        """
        保存最优参数配置到文件
        
        Args:
            optimal_params: 最优参数配置
            filename: 保存文件名（可选）
        """
        if filename is None:
            filename = f"optimal_parameters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(project_root, 'config', filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(optimal_params, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"最优参数已保存到: {filepath}")
    
    def generate_parameter_config_code(self, params: Dict) -> str:
        """
        生成参数配置代码（用于更新config.py或创建配置类）
        
        Args:
            params: 参数配置字典
        
        Returns:
            Python代码字符串
        """
        code = f"""
# 参数调优结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 以下参数通过参数调优工具生成

# X2指标阈值配置
X2_CONFIG = {{
    'overbought_threshold': {params['x2_overbought_threshold']},  # 超买阈值
    'oversold_threshold': {params['x2_oversold_threshold']},      # 超卖阈值
    'high_threshold': {params['x2_high_threshold']},              # 偏高阈值
    'low_threshold': {params['x2_low_threshold']},                # 偏低阈值
    'overbought_score': {params['x2_overbought_score']},           # 超买得分
    'oversold_score': {params['x2_oversold_score']},               # 超卖得分
    'high_score': {params['x2_high_score']},                       # 偏高得分
    'low_score': {params['x2_low_score']},                         # 偏低得分
}}

# 异常检测置信度调整配置
ANOMALY_CONFIG = {{
    'st_stock_confidence_reduction': {params['st_stock_confidence_reduction']},  # ST股票置信度降低
    'limit_up_down_confidence_reduction': {params['limit_up_down_confidence_reduction']},  # 涨跌停置信度降低
}}

# ML动态权重配置
ML_WEIGHT_CONFIG = {{
    'default_weight': {params['ml_default_weight']},      # 默认权重
    'min_weight': {params['ml_min_weight']},              # 最小权重
    'max_weight': {params['ml_max_weight']},              # 最大权重
}}
"""
        return code


def main():
    """主函数"""
    tool = ParameterTuningTool()
    
    # 显示当前参数
    print("\n当前参数配置:")
    print(json.dumps(tool.current_params, indent=2, ensure_ascii=False))
    
    # 询问是否开始调优
    print("\n" + "=" * 60)
    print("参数调优工具")
    print("=" * 60)
    print("\n说明：")
    print("1. 本工具会生成多个参数组合")
    print("2. 对每个组合进行回测评估")
    print("3. 找到准确率最高的参数组合")
    print("\n注意：")
    print("- 调优过程可能需要较长时间（取决于参数组合数量）")
    print("- 建议先用少量组合测试，确认流程正确后再全面调优")
    
    response = input("\n是否开始参数调优？(y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    # 执行调优
    optimal = tool.find_optimal_parameters(days=30)
    
    if optimal:
        # 保存结果
        tool.save_optimal_parameters(optimal)
        
        # 生成配置代码
        config_code = tool.generate_parameter_config_code(optimal['params'])
        print("\n生成的配置代码:")
        print(config_code)
        
        # 保存配置代码
        code_file = os.path.join(project_root, 'config', f"optimal_parameters_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(config_code)
        print(f"\n配置代码已保存到: {code_file}")


if __name__ == '__main__':
    main()
