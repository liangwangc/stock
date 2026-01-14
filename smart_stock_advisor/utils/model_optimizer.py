"""
模型参数优化模块
使用优化算法优化权重参数，基于历史回测结果调整参数
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import itertools

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from utils.backtest_engine import BacktestEngine
from utils.prediction_config_manager import PredictionConfigManager

logger = get_logger(__name__)


class ModelOptimizer:
    """模型参数优化器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        self.backtest_engine = BacktestEngine()
        self.config_manager = PredictionConfigManager()
    
    def optimize_weights_grid_search(self, start_date: str, end_date: str,
                                    optimization_config: Optional[Dict] = None) -> Dict:
        """
        使用网格搜索优化权重参数
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
            optimization_config: 优化配置
            
        Returns:
            优化结果字典
        """
        try:
            # 获取当前参数
            current_config = self.config_manager.get_config()
            if not current_config:
                return {
                    'success': False,
                    'message': '无法获取当前配置'
                }
            
            current_prediction_config = current_config.get('prediction', {})
            
            # 定义参数搜索空间
            if optimization_config:
                search_space = optimization_config.get('search_space', {})
            else:
                # 默认搜索空间（围绕当前值±10%）
                search_space = self._generate_default_search_space(current_prediction_config)
            
            self.logger.info(f"开始网格搜索优化，搜索空间大小: {self._calculate_search_space_size(search_space)}")
            
            # 执行网格搜索
            best_params = None
            best_performance = None
            best_score = float('-inf')
            
            all_results = []
            iteration = 0
            
            # 生成所有参数组合
            param_combinations = self._generate_parameter_combinations(search_space)
            total_combinations = len(param_combinations)
            
            self.logger.info(f"总共需要测试 {total_combinations} 个参数组合")
            
            for params in param_combinations:
                iteration += 1
                
                # 每10个组合输出一次进度
                if iteration % 10 == 0 or iteration == 1:
                    progress_pct = (iteration / total_combinations) * 100
                    self.logger.info(f"优化进度: {iteration}/{total_combinations} ({progress_pct:.1f}%)")
                
                # 使用该参数组合回测
                backtest_result = self.backtest_engine.backtest_with_parameters(
                    start_date, end_date, params
                )
                
                if not backtest_result.get('success'):
                    continue
                
                # 计算评分（综合考虑收益率、夏普比率、最大回撤等）
                score = self._calculate_optimization_score(backtest_result)
                
                all_results.append({
                    'parameters': params,
                    'backtest_result': backtest_result,
                    'score': score
                })
                
                # 更新最佳参数
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_performance = backtest_result
                    improvement = ((best_score - current_score) / abs(current_score) * 100) if current_score != 0 else 0
                    self.logger.info(f"找到更好的参数组合，评分: {score:.4f} (改进: {improvement:.2f}%)")
            
            if not best_params:
                return {
                    'success': False,
                    'message': '没有找到有效的参数组合'
                }
            
            # 获取当前参数的性能（用于对比）
            current_backtest = self.backtest_engine.backtest_with_parameters(
                start_date, end_date, current_prediction_config
            )
            current_score = self._calculate_optimization_score(current_backtest) if current_backtest.get('success') else 0
            
            # 计算改进百分比
            improvement_pct = ((best_score - current_score) / abs(current_score) * 100) if current_score != 0 else 0
            
            # 判断是否自动应用（改进超过阈值）
            auto_apply_threshold = optimization_config.get('auto_apply_threshold', 5.0) if optimization_config else 5.0  # 默认5%
            should_auto_apply = improvement_pct >= auto_apply_threshold
            
            # 保存优化历史
            optimization_record = {
                'optimization_date': datetime.now(),
                'optimization_method': 'grid_search',
                'old_parameters': current_prediction_config,
                'new_parameters': best_params,
                'old_performance': current_backtest.get('metrics', {}) if current_backtest.get('success') else {},
                'new_performance': best_performance.get('metrics', {}) if best_performance else {},
                'improvement_pct': round(improvement_pct, 2),
                'is_applied': 1 if should_auto_apply else 0,  # 如果改进超过阈值，自动应用
                'backtest_result': best_performance,
                'optimization_config': optimization_config or {}
            }
            
            optimization_record_id = self._save_optimization_history(optimization_record)
            
            # 如果改进超过阈值，自动应用优化参数
            if should_auto_apply:
                try:
                    from utils.model_parameter_updater import ModelParameterUpdater
                    updater = ModelParameterUpdater()
                    apply_result = updater.apply_optimized_parameters(
                        optimization_id=optimization_record_id,
                        user_id=None,
                        force=False
                    )
                    if apply_result.get('success'):
                        self.logger.info(f"优化参数已自动应用（改进 {improvement_pct:.2f}% >= {auto_apply_threshold}%）")
                    else:
                        self.logger.warning(f"优化参数自动应用失败: {apply_result.get('message', '未知错误')}")
                except Exception as e:
                    self.logger.warning(f"自动应用优化参数时出错: {str(e)}")
            
            return {
                'success': True,
                'optimization_id': optimization_record_id,
                'best_parameters': best_params,
                'best_performance': best_performance,
                'best_score': round(best_score, 4),
                'current_score': round(current_score, 4),
                'improvement_pct': round(improvement_pct, 2),
                'is_auto_applied': should_auto_apply,  # 是否已自动应用
                'total_combinations_tested': total_combinations,
                'all_results': sorted(all_results, key=lambda x: x['score'], reverse=True)[:10]  # 返回前10个最佳结果
            }
            
        except Exception as e:
            self.logger.error(f"参数优化失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'优化失败: {str(e)}'
            }
    
    def _generate_default_search_space(self, current_config: Dict) -> Dict:
        """
        生成默认搜索空间（优化版）
        
        优化策略：
        1. 核心权重（news, capital_flow, market, technical）使用较小步长（3%）
        2. 辅助权重（sector_rotation, history, us_sector, valuation）使用较大步长（5%）
        3. 减少搜索空间大小，提高优化效率
        """
        search_space = {}
        
        # 核心权重参数（使用较小步长，更精细搜索）
        core_weight_params = [
            'news_weight', 'capital_flow_weight', 'market_weight', 'technical_weight'
        ]
        
        # 辅助权重参数（使用较大步长，快速搜索）
        auxiliary_weight_params = [
            'sector_rotation_weight', 'history_weight',
            'us_sector_weight', 'valuation_weight'
        ]
        
        # 生成核心权重搜索空间（当前值±15%，步长3%）
        for param in core_weight_params:
            current_value = current_config.get(param, 0.1)
            min_val = max(0.01, current_value * 0.85)
            max_val = min(0.5, current_value * 1.15)
            step = 0.03
            
            values = []
            val = min_val
            while val <= max_val:
                values.append(round(val, 3))
                val += step
            
            # 确保包含当前值
            if current_value not in values:
                values.append(round(current_value, 3))
                values.sort()
            
            search_space[param] = values
        
        # 生成辅助权重搜索空间（当前值±20%，步长5%）
        for param in auxiliary_weight_params:
            current_value = current_config.get(param, 0.05)
            min_val = max(0.01, current_value * 0.8)
            max_val = min(0.3, current_value * 1.2)
            step = 0.05
            
            values = []
            val = min_val
            while val <= max_val:
                values.append(round(val, 3))
                val += step
            
            # 确保包含当前值
            if current_value not in values:
                values.append(round(current_value, 3))
                values.sort()
            
            search_space[param] = values
        
        return search_space
    
    def _generate_parameter_combinations(self, search_space: Dict) -> List[Dict]:
        """生成所有参数组合"""
        # 获取所有参数的键和值列表
        keys = list(search_space.keys())
        values_lists = [search_space[key] for key in keys]
        
        # 生成所有组合
        combinations = []
        for combo in itertools.product(*values_lists):
            params = dict(zip(keys, combo))
            
            # 归一化权重（确保权重总和为1）
            total_weight = sum(params.get(k, 0) for k in keys if 'weight' in k)
            if total_weight > 0:
                for k in keys:
                    if 'weight' in k:
                        params[k] = round(params[k] / total_weight, 4)
            
            combinations.append(params)
        
        return combinations
    
    def _calculate_search_space_size(self, search_space: Dict) -> int:
        """计算搜索空间大小"""
        size = 1
        for values in search_space.values():
            size *= len(values)
        return size
    
    def _calculate_optimization_score(self, backtest_result: Dict) -> float:
        """
        计算优化评分
        
        综合考虑：
        - 总收益率（权重：40%）
        - 夏普比率（权重：30%）
        - 最大回撤（权重：20%，越小越好）
        - 胜率（权重：10%）
        """
        if not backtest_result.get('success'):
            return float('-inf')
        
        metrics = backtest_result.get('metrics', {})
        
        total_return = metrics.get('total_return', 0) / 100.0  # 转换为小数
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        max_drawdown = abs(metrics.get('max_drawdown', 0)) / 100.0  # 转换为小数，取绝对值
        win_rate = metrics.get('win_rate', 0) / 100.0  # 转换为小数
        
        # 计算综合评分
        score = (
            total_return * 0.4 +
            sharpe_ratio * 0.3 +
            (1 - max_drawdown) * 0.2 +  # 回撤越小越好，所以用1减去
            win_rate * 0.1
        )
        
        return score
    
    def _save_optimization_history(self, record: Dict) -> int:
        """保存优化历史到数据库，返回记录ID"""
        try:
            # 使用连接直接执行以获取lastrowid
            from utils.db_connection import DatabaseConnection as DBConnection
            try:
                from config_db import DB_CONFIG
            except ImportError:
                DB_CONFIG = {'autocommit': True}
            
            conn = DBConnection.get_connection()
            if not conn:
                self.logger.error("无法获取数据库连接")
                return 0
            
            sql = """
                INSERT INTO parameter_optimization_history
                (optimization_date, optimization_method, old_parameters, new_parameters,
                 old_performance, new_performance, improvement_pct, is_applied,
                 backtest_result, optimization_config)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                record.get('optimization_date'),
                record.get('optimization_method'),
                json.dumps(record.get('old_parameters', {}), ensure_ascii=False),
                json.dumps(record.get('new_parameters', {}), ensure_ascii=False),
                json.dumps(record.get('old_performance', {}), ensure_ascii=False),
                json.dumps(record.get('new_performance', {}), ensure_ascii=False),
                record.get('improvement_pct'),
                record.get('is_applied', 0),
                json.dumps(record.get('backtest_result', {}), ensure_ascii=False),
                json.dumps(record.get('optimization_config', {}), ensure_ascii=False)
            )
            
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if not DB_CONFIG.get('autocommit', True):
                conn.commit()
            optimization_id = cursor.lastrowid
            cursor.close()
            
            self.logger.info(f"优化历史已保存，ID: {optimization_id}")
            return optimization_id if optimization_id else 0
            
        except Exception as e:
            self.logger.error(f"保存优化历史失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0


if __name__ == '__main__':
    # 测试代码
    optimizer = ModelOptimizer()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    print("=" * 60)
    print("测试参数优化（网格搜索）")
    print("=" * 60)
    
    # 使用较小的搜索空间进行测试
    test_config = {
        'search_space': {
            'news_weight': [0.20, 0.25, 0.30],
            'capital_flow_weight': [0.15, 0.18, 0.20],
            'technical_weight': [0.18, 0.20, 0.22]
        }
    }
    
    result = optimizer.optimize_weights_grid_search(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        test_config
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
