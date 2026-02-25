"""
模型参数优化模块
使用优化算法优化权重参数，基于历史回测结果调整参数
"""
import sys
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
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

# 全局进度存储（用于实时进度反馈）
_optimization_progress = {}
_optimization_progress_lock = None


def _convert_to_serializable(obj: Any) -> Any:
    """
    将对象转换为可JSON序列化的格式
    处理 date、datetime 等特殊类型
    
    Args:
        obj: 要转换的对象
        
    Returns:
        可序列化的对象
    """
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return [_convert_to_serializable(item) for item in obj]
    else:
        return obj


def _safe_json_dumps(obj: Any, ensure_ascii: bool = False) -> str:
    """
    安全地将对象转换为JSON字符串
    自动处理 date、datetime 等特殊类型
    
    Args:
        obj: 要转换的对象
        ensure_ascii: 是否确保ASCII编码
        
    Returns:
        JSON字符串
    """
    serializable_obj = _convert_to_serializable(obj)
    return json.dumps(serializable_obj, ensure_ascii=ensure_ascii)

try:
    import threading
    _optimization_progress_lock = threading.Lock()
except ImportError:
    pass


class ModelOptimizer:
    """模型参数优化器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        self.backtest_engine = BacktestEngine()
        self.config_manager = PredictionConfigManager()
    
    def optimize_weights_grid_search(self, start_date: str, end_date: str,
                                    optimization_config: Optional[Dict] = None,
                                    progress_id: Optional[str] = None) -> Dict:
        """
        使用网格搜索优化权重参数（支持时间序列交叉验证）
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
            optimization_config: 优化配置
                - use_cross_validation: 是否使用交叉验证（默认False）
                - train_ratio: 训练集比例（默认0.8，即80%训练，20%验证）
                - search_space: 自定义搜索空间
            
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
            
            # 检查是否使用交叉验证
            use_cross_validation = optimization_config.get('use_cross_validation', False) if optimization_config else False
            train_ratio = optimization_config.get('train_ratio', 0.8) if optimization_config else 0.8
            
            # 如果使用交叉验证，分割数据
            if use_cross_validation:
                # 计算日期范围
                from datetime import datetime as dt
                start_dt = dt.strptime(start_date, '%Y-%m-%d')
                end_dt = dt.strptime(end_date, '%Y-%m-%d')
                total_days = (end_dt - start_dt).days
                train_days = int(total_days * train_ratio)
                
                train_end_dt = start_dt + timedelta(days=train_days)
                train_end_date = train_end_dt.strftime('%Y-%m-%d')
                
                self.logger.info(f"使用时间序列交叉验证：训练集 {start_date} 到 {train_end_date}，验证集 {train_end_date} 到 {end_date}")
            else:
                train_end_date = end_date
            
            # 定义参数搜索空间
            if optimization_config and optimization_config.get('search_space'):
                search_space = optimization_config.get('search_space')
            else:
                # 默认搜索空间（围绕当前值±10%）
                search_space = self._generate_default_search_space(current_prediction_config)
            
            self.logger.info(f"开始网格搜索优化，搜索空间大小: {self._calculate_search_space_size(search_space)}")
            
            # 执行网格搜索
            best_params = None
            best_performance = None
            best_score = float('-inf')
            best_validation_score = float('-inf') if use_cross_validation else None
            
            all_results = []
            iteration = 0
            
            # 生成所有参数组合
            param_combinations = self._generate_parameter_combinations(search_space)
            total_combinations = len(param_combinations)
            
            self.logger.info(f"总共需要测试 {total_combinations} 个参数组合")
            
            # 初始化进度
            if progress_id:
                self._update_progress(progress_id, {
                    'status': 'running',
                    'current': 0,
                    'total': total_combinations,
                    'percentage': 0.0,
                    'message': f'开始优化，共 {total_combinations} 个参数组合',
                    'best_score': None,
                    'current_score': None
                })
            
            for params in param_combinations:
                iteration += 1
                
                # 更新进度（每5个组合更新一次，或第一个和最后一个）
                if progress_id and (iteration % 5 == 0 or iteration == 1 or iteration == total_combinations):
                    progress_pct = (iteration / total_combinations) * 100
                    self.logger.info(f"优化进度: {iteration}/{total_combinations} ({progress_pct:.1f}%)")
                    
                    self._update_progress(progress_id, {
                        'status': 'running',
                        'current': iteration,
                        'total': total_combinations,
                        'percentage': progress_pct,
                        'message': f'正在测试参数组合 {iteration}/{total_combinations} ({progress_pct:.1f}%)',
                        'best_score': best_score if best_score != float('-inf') else None,
                        'current_score': None
                    })
                
                # 在训练集上回测
                backtest_result = self.backtest_engine.backtest_with_parameters(
                    start_date, train_end_date, params
                )
                
                if not backtest_result.get('success'):
                    continue
                
                # 计算训练集评分
                train_score = self._calculate_optimization_score(backtest_result)
                
                # 如果使用交叉验证，在验证集上验证
                validation_score = None
                if use_cross_validation:
                    validation_backtest = self.backtest_engine.backtest_with_parameters(
                        train_end_date, end_date, params
                    )
                    if validation_backtest.get('success'):
                        validation_score = self._calculate_optimization_score(validation_backtest)
                        # 使用验证集评分作为主要评分（避免过拟合）
                        score = validation_score
                    else:
                        score = train_score * 0.5  # 验证失败，降低评分
                else:
                    score = train_score
                
                all_results.append({
                    'parameters': params,
                    'backtest_result': backtest_result,
                    'train_score': train_score,
                    'validation_score': validation_score,
                    'score': score
                })
                
                # 更新最佳参数（使用验证集评分或训练集评分）
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_performance = backtest_result
                    if use_cross_validation and validation_score is not None:
                        best_validation_score = validation_score
                    self.logger.info(f"找到更好的参数组合，评分: {score:.4f} (训练集: {train_score:.4f}, 验证集: {validation_score if validation_score else 'N/A'})")
                    
                    # 更新进度（找到更好的参数时）
                    if progress_id:
                        progress_pct = (iteration / total_combinations) * 100
                        self._update_progress(progress_id, {
                            'status': 'running',
                            'current': iteration,
                            'total': total_combinations,
                            'percentage': progress_pct,
                            'message': f'找到更好的参数组合！评分: {score:.4f} ({iteration}/{total_combinations})',
                            'best_score': best_score,
                            'current_score': None
                        })
            
            if not best_params:
                return {
                    'success': False,
                    'message': '没有找到有效的参数组合'
                }
            
            # 更新进度：计算当前参数性能
            if progress_id:
                self._update_progress(progress_id, {
                    'status': 'running',
                    'current': total_combinations,
                    'total': total_combinations,
                    'percentage': 95.0,
                    'message': '正在计算当前参数性能...',
                    'best_score': best_score if best_score != float('-inf') else None,
                    'current_score': None
                })
            
            # 获取当前参数的性能（用于对比，在完整数据集上）
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
            
            # 提取参数信息（用于前端展示）
            # 当前默认交易参数
            current_trading_params = {
                'buy_threshold': current_prediction_config.get('buy_threshold', 0.6),
                'sell_threshold': current_prediction_config.get('sell_threshold', 0.4),
                'min_confidence': current_prediction_config.get('min_confidence', 0.55),
                'stop_loss_pct': current_prediction_config.get('stop_loss_pct', -5.0),
                'take_profit_pct': current_prediction_config.get('take_profit_pct', 8.0),
                'max_position_pct': current_prediction_config.get('max_position_pct', 0.3),
            }
            
            # 也提取权重信息（如果best_params中有的话）
            best_weights = {}
            current_weights = {}
            for key in best_params:
                if key.endswith('_weight'):
                    best_weights[key] = best_params[key]
            for key in current_prediction_config:
                if key.endswith('_weight'):
                    current_weights[key] = current_prediction_config[key]
            
            result = {
                'success': True,
                'optimization_id': optimization_record_id,
                'best_parameters': best_params,
                'best_performance': best_performance,
                'best_score': round(best_score, 4),
                'current_score': round(current_score, 4),
                'improvement_pct': round(improvement_pct, 2),
                'is_auto_applied': should_auto_apply,
                'total_combinations_tested': total_combinations,
                'all_results': sorted(all_results, key=lambda x: x['score'], reverse=True)[:10],
                'optimization_method': 'grid_search',
                'best_weights': best_weights,
                'current_weights': current_weights,
                'current_trading_params': current_trading_params,  # 当前交易参数（用于前端对比展示）
            }
            
            # 如果使用了交叉验证，添加验证集信息
            if use_cross_validation:
                result['use_cross_validation'] = True
                result['train_ratio'] = train_ratio
                result['best_validation_score'] = round(best_validation_score, 4) if best_validation_score is not None else None
            
            # 更新进度：优化完成（包含完整结果）
            if progress_id:
                self._update_progress(progress_id, {
                    'status': 'completed',
                    'current': total_combinations,
                    'total': total_combinations,
                    'percentage': 100.0,
                    'message': f'优化完成！改进: {improvement_pct:.2f}%',
                    'best_score': best_score,
                    'current_score': current_score,
                    'improvement_pct': improvement_pct,
                    'result': result  # 存储完整结果，供前端获取
                })
                try:
                    import threading
                    def cleanup_progress():
                        import time
                        time.sleep(30)  # 30秒后清理，给前端足够时间获取结果
                        self._clear_progress(progress_id)
                    threading.Thread(target=cleanup_progress, daemon=True).start()
                except Exception as e:
                    self.logger.debug(f"清理进度失败: {str(e)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"参数优化失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            # 更新进度：失败
            if progress_id:
                self._update_progress(progress_id, {
                    'status': 'failed',
                    'current': iteration if 'iteration' in locals() else 0,
                    'total': total_combinations if 'total_combinations' in locals() else 0,
                    'percentage': 0.0,
                    'message': f'优化失败: {str(e)}',
                    'error': str(e)
                })
            
            return {
                'success': False,
                'message': f'参数优化失败: {str(e)}'
            }
    
    def _update_progress(self, progress_id: str, progress_data: Dict):
        """更新优化进度"""
        global _optimization_progress, _optimization_progress_lock
        
        if _optimization_progress_lock:
            with _optimization_progress_lock:
                _optimization_progress[progress_id] = {
                    **progress_data,
                    'update_time': datetime.now().isoformat()
                }
        else:
            _optimization_progress[progress_id] = {
                **progress_data,
                'update_time': datetime.now().isoformat()
            }
    
    def _clear_progress(self, progress_id: str):
        """清理优化进度"""
        global _optimization_progress, _optimization_progress_lock
        
        if _optimization_progress_lock:
            with _optimization_progress_lock:
                if progress_id in _optimization_progress:
                    del _optimization_progress[progress_id]
        else:
            if progress_id in _optimization_progress:
                del _optimization_progress[progress_id]
    
    @staticmethod
    def get_progress(progress_id: str) -> Optional[Dict]:
        """获取优化进度"""
        global _optimization_progress
        
        return _optimization_progress.get(progress_id)
    
    def optimize_weights_bayesian(self, start_date: str, end_date: str,
                                  optimization_config: Optional[Dict] = None) -> Dict:
        """
        使用贝叶斯优化优化权重参数（如果scikit-optimize可用）
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
            optimization_config: 优化配置
                - n_calls: 评估次数（默认100）
                - use_cross_validation: 是否使用交叉验证
            
        Returns:
            优化结果字典
        """
        try:
            # 尝试导入scikit-optimize
            try:
                from skopt import gp_minimize
                from skopt.space import Real
                from skopt.utils import use_named_args
                BAYESIAN_AVAILABLE = True
            except ImportError:
                BAYESIAN_AVAILABLE = False
                self.logger.warning("scikit-optimize未安装，无法使用贝叶斯优化，回退到网格搜索")
                return self.optimize_weights_grid_search(start_date, end_date, optimization_config)
            
            # 获取当前参数
            current_config = self.config_manager.get_config()
            if not current_config:
                return {
                    'success': False,
                    'message': '无法获取当前配置'
                }
            
            current_prediction_config = current_config.get('prediction', {})
            
            # 确保当前配置包含交易参数的合理默认值（避免基线回测使用全默认值）
            trading_defaults = {
                'buy_threshold': 0.6,
                'sell_threshold': 0.4,
                'min_confidence': 0.55,
                'stop_loss_pct': -5.0,
                'take_profit_pct': 8.0,
                'max_position_pct': 0.3,
            }
            trading_section = current_prediction_config.get('trading', current_prediction_config)
            for key, default_val in trading_defaults.items():
                if key not in current_prediction_config:
                    current_prediction_config[key] = trading_section.get(key, default_val)
            
            # 检查是否使用交叉验证
            use_cross_validation = optimization_config.get('use_cross_validation', False) if optimization_config else False
            train_ratio = optimization_config.get('train_ratio', 0.8) if optimization_config else 0.8
            n_calls = optimization_config.get('n_calls', 100) if optimization_config else 100
            
            # 如果使用交叉验证，分割数据
            if use_cross_validation:
                from datetime import datetime as dt
                start_dt = dt.strptime(start_date, '%Y-%m-%d')
                end_dt = dt.strptime(end_date, '%Y-%m-%d')
                total_days = (end_dt - start_dt).days
                train_days = int(total_days * train_ratio)
                
                train_end_dt = start_dt + timedelta(days=train_days)
                train_end_date = train_end_dt.strftime('%Y-%m-%d')
                
                self.logger.info(f"使用时间序列交叉验证：训练集 {start_date} 到 {train_end_date}，验证集 {train_end_date} 到 {end_date}")
            else:
                train_end_date = end_date
            
            # 定义搜索空间（使用Real类型，连续值）
            # 搜索交易参数（回测引擎实际使用的参数）
            dimensions = []
            param_names = []
            
            trading_params = {
                'buy_threshold': (0.50, 0.75),       # 买入上涨概率阈值
                'sell_threshold': (0.25, 0.50),       # 卖出上涨概率上限
                'min_confidence': (0.40, 0.70),       # 最小置信度
                'stop_loss_pct': (-12.0, -2.0),       # 止损百分比
                'take_profit_pct': (4.0, 20.0),       # 止盈百分比
                'max_position_pct': (0.10, 0.40),     # 单股最大仓位
            }
            
            for param_name, (min_val, max_val) in trading_params.items():
                dimensions.append(Real(min_val, max_val, name=param_name))
                param_names.append(param_name)
            
            # 定义目标函数（负评分，因为gp_minimize是最小化）
            @use_named_args(dimensions=dimensions)
            def objective(**params):
                # 交易参数直接使用，不需要归一化
                # 在训练集上回测
                backtest_result = self.backtest_engine.backtest_with_parameters(
                    start_date, train_end_date, params
                )
                
                if not backtest_result.get('success'):
                    return 1000.0  # 返回很大的值（表示很差）
                
                # 计算评分
                train_score = self._calculate_optimization_score(backtest_result)
                
                # 如果使用交叉验证，在验证集上验证
                if use_cross_validation:
                    validation_backtest = self.backtest_engine.backtest_with_parameters(
                        train_end_date, end_date, params
                    )
                    if validation_backtest.get('success'):
                        validation_score = self._calculate_optimization_score(validation_backtest)
                        # 使用验证集评分（避免过拟合）
                        score = validation_score
                    else:
                        score = train_score * 0.5
                else:
                    score = train_score
                
                # 返回负评分（因为gp_minimize是最小化）
                return -score
            
            self.logger.info(f"开始贝叶斯优化，评估次数: {n_calls}")
            
            # 执行贝叶斯优化
            result = gp_minimize(
                func=objective,
                dimensions=dimensions,
                n_calls=n_calls,
                random_state=42,
                n_initial_points=10  # 初始随机采样点数
            )
            
            # 提取最佳参数（交易参数直接使用，无需归一化）
            best_params = dict(zip(param_names, result.x))
            # 对 stop_loss_pct 确保为负值
            if best_params.get('stop_loss_pct', 0) > 0:
                best_params['stop_loss_pct'] = -best_params['stop_loss_pct']
            
            best_score = -result.fun  # 取负号（因为返回的是负评分）
            
            # 在完整数据集上回测最佳参数
            best_backtest = self.backtest_engine.backtest_with_parameters(
                start_date, end_date, best_params
            )
            
            if not best_backtest.get('success'):
                return {
                    'success': False,
                    'message': '最佳参数回测失败'
                }
            
            # 获取当前参数的性能
            current_backtest = self.backtest_engine.backtest_with_parameters(
                start_date, end_date, current_prediction_config
            )
            current_score = self._calculate_optimization_score(current_backtest) if current_backtest.get('success') else 0
            
            # 计算改进百分比
            improvement_pct = ((best_score - current_score) / abs(current_score) * 100) if current_score != 0 else 0
            
            # 判断是否自动应用
            auto_apply_threshold = optimization_config.get('auto_apply_threshold', 5.0) if optimization_config else 5.0
            should_auto_apply = improvement_pct >= auto_apply_threshold
            
            # 保存优化历史
            optimization_record = {
                'optimization_date': datetime.now(),
                'optimization_method': 'bayesian',
                'old_parameters': current_prediction_config,
                'new_parameters': best_params,
                'old_performance': current_backtest.get('metrics', {}) if current_backtest.get('success') else {},
                'new_performance': best_backtest.get('metrics', {}) if best_backtest else {},
                'improvement_pct': round(improvement_pct, 2),
                'is_applied': 1 if should_auto_apply else 0,
                'backtest_result': best_backtest,
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
                'best_performance': best_backtest,
                'best_score': round(best_score, 4),
                'current_score': round(current_score, 4),
                'improvement_pct': round(improvement_pct, 2),
                'is_auto_applied': should_auto_apply,
                'total_evaluations': n_calls,
                'optimization_method': 'bayesian',
                'use_cross_validation': use_cross_validation
            }
            
        except Exception as e:
            self.logger.error(f"贝叶斯优化失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 如果贝叶斯优化失败，回退到网格搜索
            self.logger.info("回退到网格搜索优化")
            return self.optimize_weights_grid_search(start_date, end_date, optimization_config)
    
    def _generate_default_search_space(self, current_config: Dict) -> Dict:
        """
        生成默认搜索空间（修复版）
        
        关键修复：搜索交易参数（buy_threshold, sell_threshold等），
        因为回测引擎实际使用的是这些参数，而不是权重参数。
        权重参数的优化由WeightOptimizer基于因子准确率单独处理。
        
        搜索的参数包括：
        1. buy_threshold: 买入上涨概率阈值
        2. sell_threshold: 卖出下跌概率阈值
        3. min_confidence: 最小置信度
        4. stop_loss_pct: 止损百分比
        5. take_profit_pct: 止盈百分比
        6. max_position_pct: 单只股票最大仓位
        """
        search_space = {}
        
        # 买入阈值（上涨概率 >= 此值才买入）
        search_space['buy_threshold'] = [0.50, 0.55, 0.60, 0.65, 0.70]
        
        # 卖出阈值（上涨概率 <= 此值且预测下跌才卖出）
        search_space['sell_threshold'] = [0.30, 0.35, 0.40, 0.45]
        
        # 最小置信度（置信度 >= 此值才执行交易）
        search_space['min_confidence'] = [0.45, 0.50, 0.55, 0.60, 0.65]
        
        # 止损百分比（负值，亏损超过此值强制卖出）
        search_space['stop_loss_pct'] = [-3.0, -5.0, -7.0, -10.0]
        
        # 止盈百分比（盈利超过此值强制卖出）
        search_space['take_profit_pct'] = [5.0, 8.0, 10.0, 15.0]
        
        # 单只股票最大仓位比例
        search_space['max_position_pct'] = [0.15, 0.20, 0.25, 0.30]
        
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
            
            # 如果参数中包含权重参数，进行归一化
            weight_keys = [k for k in keys if 'weight' in k and k != 'max_position_pct']
            if weight_keys:
                total_weight = sum(params.get(k, 0) for k in weight_keys)
                if total_weight > 0:
                    for k in weight_keys:
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
        计算优化评分（修复版：统一量纲到0-1区间）
        
        综合考虑（各指标先归一化到0-1区间，再加权）：
        - 总收益率（权重：35%）— 归一化到0-1
        - 胜率（权重：25%）— 已经是0-1
        - 最大回撤（权重：25%，越小越好）— 归一化到0-1
        - 夏普比率（权重：15%）— 归一化到0-1
        """
        if not backtest_result.get('success'):
            return float('-inf')
        
        metrics = backtest_result.get('metrics', {})
        
        # 总收益率：值域约-50%到+50%，映射到0-1
        total_return_pct = metrics.get('total_return', 0)  # 已经是百分比值
        return_score = max(0, min(1, (total_return_pct + 50) / 100.0))  # -50%→0, 0%→0.5, 50%→1
        
        # 胜率：值域0-100%，映射到0-1
        win_rate_pct = metrics.get('win_rate', 0)  # 已经是百分比值
        win_rate_score = max(0, min(1, win_rate_pct / 100.0))
        
        # 最大回撤：值域0-50%，越小越好，映射到0-1
        max_drawdown_pct = abs(metrics.get('max_drawdown', 0))  # 已经是百分比值
        drawdown_score = max(0, min(1, 1 - max_drawdown_pct / 50.0))  # 0%→1, 25%→0.5, 50%→0
        
        # 夏普比率：值域约-3到+3，映射到0-1
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        sharpe_score = max(0, min(1, (sharpe_ratio + 3) / 6.0))  # -3→0, 0→0.5, 3→1
        
        # 计算综合评分（各分项已归一化到0-1，加权求和）
        score = (
            return_score * 0.35 +
            win_rate_score * 0.25 +
            drawdown_score * 0.25 +
            sharpe_score * 0.15
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
                _safe_json_dumps(record.get('old_parameters', {}), ensure_ascii=False),
                _safe_json_dumps(record.get('new_parameters', {}), ensure_ascii=False),
                _safe_json_dumps(record.get('old_performance', {}), ensure_ascii=False),
                _safe_json_dumps(record.get('new_performance', {}), ensure_ascii=False),
                record.get('improvement_pct'),
                record.get('is_applied', 0),
                _safe_json_dumps(record.get('backtest_result', {}), ensure_ascii=False),
                _safe_json_dumps(record.get('optimization_config', {}), ensure_ascii=False)
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
    
    # 使用默认交易参数搜索空间进行测试
    test_config = {
        # 不传 search_space，使用默认交易参数搜索空间
    }
    
    result = optimizer.optimize_weights_grid_search(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        test_config
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
