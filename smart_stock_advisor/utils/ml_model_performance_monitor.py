"""
ML模型性能监控模块
用于监控ML模型的预测准确率，并根据性能动态调整权重
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


class MLModelPerformanceMonitor:
    """ML模型性能监控器"""
    
    def __init__(self, config_manager=None):
        """
        初始化ML模型性能监控器
        
        Args:
            config_manager: 配置管理器实例（可选，如果提供则使用，否则创建新实例）
        """
        self.db = DatabaseConnection()
        self.logger = logger
        self._model_performance = {}  # {model_id: {'accuracy': 0.65, 'last_update': datetime, 'prediction_count': 100}}
        self._lock = threading.Lock()  # 线程安全锁
        self._config_manager = config_manager  # 保存配置管理器引用（支持热更新）
        self._config_version = None  # 配置版本号（用于检测配置变更）
        self._load_config()  # 从配置加载参数
    
    def _load_config(self):
        """
        从配置加载ML模型权重参数（支持热更新）
        
        注意：PredictionConfigManager 是单例且有缓存机制，重复调用影响不大。
        如果提供了配置管理器实例，则复用；否则创建新实例（单例模式，实际是同一个实例）。
        """
        try:
            # 如果提供了配置管理器，使用它；否则创建新实例（单例模式，实际是同一个实例）
            if self._config_manager is None:
                from utils.prediction_config_manager import PredictionConfigManager
                self._config_manager = PredictionConfigManager()
            
            active_config = self._config_manager.get_config()
            
            # 检查配置版本（如果支持）
            current_config_id = getattr(self._config_manager, '_active_config_id', None)
            if current_config_id != self._config_version:
                self._config_version = current_config_id
                # 配置已更新，重新加载
            
            if active_config and active_config.get('prediction'):
                prediction_config = active_config['prediction']
                # 优先使用配置中的ML权重参数（config.py中的PREDICTION_CONFIG）
                self._default_weight = prediction_config.get('ml_default_weight', 0.35)
                self._min_weight = prediction_config.get('ml_min_weight', 0.10)
                self._max_weight = prediction_config.get('ml_max_weight', 0.50)
                self._high_accuracy_threshold = prediction_config.get('ml_high_accuracy_threshold', 0.60)
                self._medium_accuracy_threshold = prediction_config.get('ml_medium_accuracy_threshold', 0.50)
            else:
                # 使用默认值（与PREDICTION_CONFIG保持一致）
                self._default_weight = 0.35
                self._min_weight = 0.10
                self._max_weight = 0.50
                self._high_accuracy_threshold = 0.60
                self._medium_accuracy_threshold = 0.50
        except Exception as e:
            self.logger.warning(f"加载ML模型配置失败，使用默认值: {str(e)}")
            self._default_weight = 0.35
            self._min_weight = 0.10
            self._max_weight = 0.50
            self._high_accuracy_threshold = 0.60
            self._medium_accuracy_threshold = 0.50
    
    def refresh_config(self):
        """刷新配置（支持热更新）"""
        self._load_config()
        self.logger.debug("ML模型性能监控器配置已刷新")
    
    def update_performance(self, model_id: int, accuracy: float, prediction_count: int = 0):
        """
        更新模型性能
        
        Args:
            model_id: 模型ID
            accuracy: 准确率（0-1之间）
            prediction_count: 预测次数（用于计算加权平均）
        """
        with self._lock:
            if model_id not in self._model_performance:
                self._model_performance[model_id] = {
                    'accuracy': accuracy,
                    'last_update': datetime.now(),
                    'prediction_count': prediction_count
                }
            else:
                # 加权平均更新准确率
                old_data = self._model_performance[model_id]
                old_count = old_data.get('prediction_count', 0)
                old_accuracy = old_data.get('accuracy', 0.5)
                
                total_count = old_count + prediction_count
                if total_count > 0:
                    new_accuracy = (old_accuracy * old_count + accuracy * prediction_count) / total_count
                else:
                    new_accuracy = accuracy
                
                self._model_performance[model_id] = {
                    'accuracy': new_accuracy,
                    'last_update': datetime.now(),
                    'prediction_count': total_count
                }
            
            self.logger.info(f"更新模型 {model_id} 性能: 准确率={accuracy:.2%}, 预测次数={prediction_count}")
    
    def get_optimal_weight(self, model_id: Optional[int] = None, model_type: Optional[str] = None) -> float:
        """
        根据性能计算最优权重
        
        Args:
            model_id: 模型ID（优先使用）
            model_type: 模型类型（如果model_id为None，则根据类型查找激活的模型）
        
        Returns:
            最优权重（0-0.25之间）
        """
        # 检查配置是否更新（轻量级检查，避免频繁重新加载）
        if self._config_manager:
            current_config_id = getattr(self._config_manager, '_active_config_id', None)
            if current_config_id != self._config_version:
                # 配置已更新，重新加载
                self._load_config()
        
        # 如果没有提供model_id，尝试根据model_type查找激活的模型
        if model_id is None and model_type:
            model_id = self._get_active_model_id(model_type)
        
        if model_id is None:
            return self._default_weight
        
        with self._lock:
            if model_id not in self._model_performance:
                # 尝试从数据库加载性能数据
                self._load_performance_from_db(model_id)
            
            if model_id not in self._model_performance:
                # 如果没有性能数据，返回默认权重
                return self._default_weight
            
            accuracy = self._model_performance[model_id].get('accuracy', 0.5)
            last_update = self._model_performance[model_id].get('last_update')
            
            # 如果性能数据过期（超过30天），使用默认权重
            if last_update and (datetime.now() - last_update).days > 30:
                self.logger.warning(f"模型 {model_id} 性能数据已过期，使用默认权重")
                return self._default_weight
            
            # 根据准确率计算权重（使用配置的阈值）
            if accuracy >= self._high_accuracy_threshold:  # 高准确率
                # 准确率越高，权重越高（最高max_weight）
                weight = self._default_weight + (accuracy - self._high_accuracy_threshold) * (self._max_weight - self._default_weight) / (1.0 - self._high_accuracy_threshold)
                weight = min(weight, self._max_weight)
            elif accuracy >= self._medium_accuracy_threshold:  # 中等准确率
                # 准确率在medium-high之间，权重在min-default之间
                range_size = self._high_accuracy_threshold - self._medium_accuracy_threshold
                if range_size > 0:
                    weight = self._min_weight + (accuracy - self._medium_accuracy_threshold) * (self._default_weight - self._min_weight) / range_size
                else:
                    weight = self._default_weight
            else:  # 低准确率
                # 准确率低于medium_threshold，权重很低（最高min_weight）
                weight = max(0.0, accuracy * self._min_weight / self._medium_accuracy_threshold if self._medium_accuracy_threshold > 0 else 0.0)
                weight = min(weight, self._min_weight)
            
            # 限制在最小和最大权重之间
            weight = max(self._min_weight, min(self._max_weight, weight))
            
            self.logger.debug(f"模型 {model_id} 最优权重: {weight:.2%} (准确率: {accuracy:.2%})")
            return weight
    
    def _get_active_model_id(self, model_type: str) -> Optional[int]:
        """根据模型类型获取激活的模型ID"""
        try:
            sql = """
                SELECT id FROM trained_models 
                WHERE model_type = %s AND is_active = 1 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            results = self.db.execute_query(sql, (model_type,))
            if results:
                return results[0][0]
        except Exception as e:
            self.logger.error(f"获取激活模型ID失败: {str(e)}")
        return None
    
    def _load_performance_from_db(self, model_id: int):
        """从数据库加载模型性能数据"""
        try:
            # 从预测结果表中计算准确率
            # 这里需要根据实际的数据结构来实现
            # 暂时跳过，等待后续实现
            pass
        except Exception as e:
            self.logger.error(f"从数据库加载模型性能失败: {str(e)}")
    
    def get_performance(self, model_id: int) -> Optional[Dict]:
        """获取模型性能数据"""
        with self._lock:
            return self._model_performance.get(model_id)
    
    def clear_cache(self):
        """清除性能缓存"""
        with self._lock:
            self._model_performance.clear()
            self.logger.info("已清除模型性能缓存")


# 全局单例
_performance_monitor = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> MLModelPerformanceMonitor:
    """获取性能监控器单例"""
    global _performance_monitor
    if _performance_monitor is None:
        with _monitor_lock:
            if _performance_monitor is None:
                _performance_monitor = MLModelPerformanceMonitor()
    return _performance_monitor
