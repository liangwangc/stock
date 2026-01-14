"""
模型参数更新模块
将优化后的参数更新到数据库，支持A/B测试和参数版本管理
"""
import sys
import os
from datetime import datetime
from typing import Dict, Optional, List
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from utils.prediction_config_manager import PredictionConfigManager

logger = get_logger(__name__)


class ModelParameterUpdater:
    """模型参数更新器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        self.config_manager = PredictionConfigManager()
    
    def apply_optimized_parameters(self, optimization_id: int, 
                                  user_id: Optional[int] = None,
                                  force: bool = False) -> Dict:
        """
        应用优化后的参数
        
        Args:
            optimization_id: 优化历史记录ID
            user_id: 操作人ID
            force: 是否强制应用（跳过确认）
            
        Returns:
            更新结果字典
        """
        try:
            # 查询优化记录
            sql = """
                SELECT 
                    id, optimization_date, optimization_method,
                    old_parameters, new_parameters,
                    old_performance, new_performance,
                    improvement_pct, is_applied
                FROM parameter_optimization_history
                WHERE id = %s
            """
            
            results = self.db.execute_query(sql, (optimization_id,))
            
            if not results:
                return {
                    'success': False,
                    'message': f'未找到优化记录 ID: {optimization_id}'
                }
            
            record = results[0]
            
            # 检查是否已应用
            if record.get('is_applied') == 1 and not force:
                return {
                    'success': False,
                    'message': '该优化记录已应用，如需重新应用请使用force=True'
                }
            
            # 检查改进百分比
            improvement_pct = float(record.get('improvement_pct', 0))
            if improvement_pct < 0 and not force:
                return {
                    'success': False,
                    'message': f'优化结果未改进（改进百分比: {improvement_pct:.2f}%），如需强制应用请使用force=True'
                }
            
            # 解析新参数
            new_parameters_json = record.get('new_parameters', '{}')
            if isinstance(new_parameters_json, str):
                new_parameters = json.loads(new_parameters_json)
            else:
                new_parameters = new_parameters_json
            
            # 获取当前激活的配置
            active_config = self.config_manager.get_config()
            if not active_config:
                return {
                    'success': False,
                    'message': '无法获取当前激活的配置'
                }
            
            active_config_id = self.config_manager.get_active_config_id()
            
            # 创建新配置或更新现有配置
            config_name = f"优化配置_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            description = f"通过{record.get('optimization_method')}优化，改进{improvement_pct:.2f}%"
            
            # 创建新配置
            new_config_id = self.config_manager.create_config(
                config_name=config_name,
                description=description,
                values={
                    'prediction': new_parameters,
                    'indicator': active_config.get('indicator', {}),
                    'news': active_config.get('news', {}),
                    'trading': active_config.get('trading', {})
                },
                user_id=user_id,
                is_default=False
            )
            
            if not new_config_id:
                return {
                    'success': False,
                    'message': '创建新配置失败'
                }
            
            # 激活新配置
            success = self.config_manager.activate_config(new_config_id, user_id=user_id)
            
            if not success:
                return {
                    'success': False,
                    'message': '激活新配置失败'
                }
            
            # 更新优化记录
            update_sql = """
                UPDATE parameter_optimization_history
                SET is_applied = 1,
                    applied_at = %s,
                    applied_by = %s
                WHERE id = %s
            """
            
            self.db.execute_update(update_sql, (datetime.now(), user_id, optimization_id))
            
            self.logger.info(f"成功应用优化参数，配置ID: {new_config_id}, 优化记录ID: {optimization_id}")
            
            return {
                'success': True,
                'message': '参数已成功应用',
                'new_config_id': new_config_id,
                'new_config_name': config_name,
                'improvement_pct': improvement_pct
            }
            
        except Exception as e:
            self.logger.error(f"应用优化参数失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'应用失败: {str(e)}'
            }
    
    def rollback_parameters(self, optimization_id: int,
                            user_id: Optional[int] = None) -> Dict:
        """
        回滚参数到优化前的状态
        
        Args:
            optimization_id: 优化历史记录ID
            user_id: 操作人ID
            
        Returns:
            回滚结果字典
        """
        try:
            # 查询优化记录
            sql = """
                SELECT old_parameters, new_parameters
                FROM parameter_optimization_history
                WHERE id = %s
            """
            
            results = self.db.execute_query(sql, (optimization_id,))
            
            if not results:
                return {
                    'success': False,
                    'message': f'未找到优化记录 ID: {optimization_id}'
                }
            
            record = results[0]
            
            # 解析旧参数
            old_parameters_json = record.get('old_parameters', '{}')
            if isinstance(old_parameters_json, str):
                old_parameters = json.loads(old_parameters_json)
            else:
                old_parameters = old_parameters_json
            
            # 获取当前激活的配置
            active_config = self.config_manager.get_config()
            if not active_config:
                return {
                    'success': False,
                    'message': '无法获取当前激活的配置'
                }
            
            # 创建回滚配置
            config_name = f"回滚配置_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            description = f"回滚到优化记录ID {optimization_id} 之前的状态"
            
            new_config_id = self.config_manager.create_config(
                config_name=config_name,
                description=description,
                values={
                    'prediction': old_parameters,
                    'indicator': active_config.get('indicator', {}),
                    'news': active_config.get('news', {}),
                    'trading': active_config.get('trading', {})
                },
                user_id=user_id,
                is_default=False
            )
            
            if not new_config_id:
                return {
                    'success': False,
                    'message': '创建回滚配置失败'
                }
            
            # 激活回滚配置
            success = self.config_manager.activate_config(new_config_id, user_id=user_id)
            
            if not success:
                return {
                    'success': False,
                    'message': '激活回滚配置失败'
                }
            
            self.logger.info(f"成功回滚参数，配置ID: {new_config_id}")
            
            return {
                'success': True,
                'message': '参数已成功回滚',
                'new_config_id': new_config_id,
                'new_config_name': config_name
            }
            
        except Exception as e:
            self.logger.error(f"回滚参数失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'回滚失败: {str(e)}'
            }
    
    def get_optimization_history(self, limit: int = 20) -> List[Dict]:
        """
        获取优化历史记录
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            优化历史记录列表
        """
        try:
            sql = """
                SELECT 
                    id, optimization_date, optimization_method,
                    improvement_pct, is_applied, applied_at,
                    old_performance, new_performance
                FROM parameter_optimization_history
                ORDER BY optimization_date DESC
                LIMIT %s
            """
            
            results = self.db.execute_query(sql, (limit,))
            
            records = []
            for r in results:
                record = {
                    'id': r.get('id'),
                    'optimization_date': r.get('optimization_date').strftime('%Y-%m-%d %H:%M:%S') if r.get('optimization_date') else None,
                    'optimization_method': r.get('optimization_method'),
                    'improvement_pct': float(r.get('improvement_pct', 0)) if r.get('improvement_pct') is not None else 0,
                    'is_applied': r.get('is_applied') == 1,
                    'applied_at': r.get('applied_at').strftime('%Y-%m-%d %H:%M:%S') if r.get('applied_at') else None
                }
                
                # 解析性能指标
                try:
                    old_perf = r.get('old_performance')
                    if isinstance(old_perf, str):
                        record['old_performance'] = json.loads(old_perf)
                    else:
                        record['old_performance'] = old_perf
                    
                    new_perf = r.get('new_performance')
                    if isinstance(new_perf, str):
                        record['new_performance'] = json.loads(new_perf)
                    else:
                        record['new_performance'] = new_perf
                except:
                    pass
                
                records.append(record)
            
            return records
            
        except Exception as e:
            self.logger.error(f"获取优化历史失败: {str(e)}")
            return []


if __name__ == '__main__':
    # 测试代码
    updater = ModelParameterUpdater()
    
    print("=" * 60)
    print("测试获取优化历史")
    print("=" * 60)
    history = updater.get_optimization_history(limit=10)
    print(json.dumps(history, indent=2, ensure_ascii=False))
