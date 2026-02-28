"""
机器学习模型管理模块
用于加载、保存、管理训练好的模型
"""
import json
import pickle
import os
from datetime import datetime
from typing import Dict, List, Optional
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


class MLModelManager:
    """机器学习模型管理器"""
    
    def __init__(self):
        self.logger = logger
        self.models_dir = os.path.join(project_root, 'models')
        self._model_cache = {}  # 模型缓存
    
    def save_model_info(self,
                       model_name: str,
                       model_type: str,
                       model_version: str,
                       model_file_path: str,
                       feature_list: List[str],
                       feature_importance: Dict[str, float],
                       training_config: Dict,
                       training_metrics: Dict,
                       train_start_date: str,
                       train_end_date: str,
                       val_start_date: Optional[str] = None,
                       val_end_date: Optional[str] = None,
                       test_start_date: Optional[str] = None,
                       test_end_date: Optional[str] = None,
                       sample_count: int = 0,
                       is_active: bool = False,
                       description: Optional[str] = None,
                       base_model_id: Optional[int] = None) -> int:
        """
        保存模型信息到数据库
        
        Returns:
            模型ID
        """
        try:
            # 检查是否有base_model_id字段（如果表结构已更新）
            try:
                check_sql = "SHOW COLUMNS FROM trained_models LIKE 'base_model_id'"
                has_base_model_id = len(DatabaseConnection.execute_query(check_sql)) > 0
            except:
                has_base_model_id = False
            
            if has_base_model_id and base_model_id:
                sql = """
                    INSERT INTO trained_models 
                    (model_name, model_type, model_version, model_file_path,
                     feature_list, feature_importance, training_config, training_metrics,
                     train_start_date, train_end_date, val_start_date, val_end_date,
                     test_start_date, test_end_date, sample_count, feature_count,
                     is_active, description, base_model_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    model_name, model_type, model_version, model_file_path,
                    json.dumps(feature_list), json.dumps(feature_importance),
                    json.dumps(training_config), json.dumps(training_metrics),
                    train_start_date, train_end_date, val_start_date, val_end_date,
                    test_start_date, test_end_date, sample_count, len(feature_list),
                    is_active, description, base_model_id
                )
            else:
                sql = """
                    INSERT INTO trained_models 
                    (model_name, model_type, model_version, model_file_path,
                     feature_list, feature_importance, training_config, training_metrics,
                     train_start_date, train_end_date, val_start_date, val_end_date,
                     test_start_date, test_end_date, sample_count, feature_count,
                     is_active, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    model_name, model_type, model_version, model_file_path,
                    json.dumps(feature_list), json.dumps(feature_importance),
                    json.dumps(training_config), json.dumps(training_metrics),
                    train_start_date, train_end_date, val_start_date, val_end_date,
                    test_start_date, test_end_date, sample_count, len(feature_list),
                    is_active, description
                )
            
            # 使用execute_update方法执行插入（使用类方法调用）
            affected_rows = DatabaseConnection.execute_update(sql, params)
            if affected_rows <= 0:
                self.logger.error(
                    f"模型信息 INSERT 未影响任何行 (affected_rows={affected_rows})，请检查："
                    " 1) config_db 中 USE_DATABASE 是否为 True；2) 数据库连接是否正常；3) trained_models 表是否存在"
                )
                return 0
            
            # 获取刚插入的记录ID（必须在同一连接上立即查询）
            sql2 = "SELECT LAST_INSERT_ID() as id"
            results = DatabaseConnection.execute_query(sql2)
            if results:
                model_id = results[0].get('id')
                if model_id:
                    self.logger.info(f"模型信息保存成功: {model_name} v{model_version} (ID: {model_id})")
                    return int(model_id)
                self.logger.warning(f"LAST_INSERT_ID() 返回空: {model_name} v{model_version}")
            else:
                self.logger.warning(f"模型信息 INSERT 已执行但无法获取ID (LAST_INSERT_ID 查询无结果): {model_name} v{model_version}")
            return 0
            
        except Exception as e:
            self.logger.error(f"保存模型信息失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0
    
    def load_model(self, model_type: str, version: Optional[str] = None, use_cache: bool = True) -> Optional[object]:
        """
        加载模型
        
        Args:
            model_type: 模型类型（xgb_classifier/lgb_classifier等）
            version: 模型版本（None表示加载激活的模型）
            use_cache: 是否使用缓存
        
        Returns:
            模型对象
        """
        try:
            # 检查缓存
            cache_key = f"{model_type}_{version or 'active'}"
            if use_cache and cache_key in self._model_cache:
                self.logger.debug(f"从缓存加载模型: {cache_key}")
                return self._model_cache[cache_key]
            
            # 查询数据库
            if version:
                sql = """
                    SELECT model_file_path, feature_list
                    FROM trained_models
                    WHERE model_type = %s AND model_version = %s
                    LIMIT 1
                """
                params = (model_type, version)
            else:
                sql = """
                    SELECT model_file_path, feature_list
                    FROM trained_models
                    WHERE model_type = %s AND is_active = 1
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                params = (model_type,)
            
            results = DatabaseConnection.execute_query(sql, params)
            
            if not results:
                self.logger.warning(f"未找到模型: {model_type} v{version or 'active'}")
                return None
            
            result = results[0]
            model_file_path = result.get('model_file_path')
            
            # 构建完整路径
            if not os.path.isabs(model_file_path):
                full_path = os.path.join(project_root, model_file_path)
            else:
                full_path = model_file_path
            
            if not os.path.exists(full_path):
                self.logger.error(f"模型文件不存在: {full_path}")
                return None
            
            # 加载模型
            with open(full_path, 'rb') as f:
                model = pickle.load(f)
            
            # 缓存模型
            if use_cache:
                self._model_cache[cache_key] = model
            
            self.logger.info(f"模型加载成功: {model_type} v{version or 'active'}")
            
            return model
            
        except Exception as e:
            self.logger.error(f"加载模型失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def get_model_info(self, model_type: str, version: Optional[str] = None) -> Optional[Dict]:
        """
        获取模型信息
        
        Args:
            model_type: 模型类型
            version: 模型版本（None表示获取激活的模型）
        
        Returns:
            模型信息字典
        """
        try:
            if version:
                sql = """
                    SELECT * FROM trained_models
                    WHERE model_type = %s AND model_version = %s
                    LIMIT 1
                """
                params = (model_type, version)
            else:
                sql = """
                    SELECT * FROM trained_models
                    WHERE model_type = %s AND is_active = 1
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                params = (model_type,)
            
            results = DatabaseConnection.execute_query(sql, params)
            
            if not results:
                return None
            
            result = results[0]
            
            # 解析JSON字段
            if result.get('feature_list'):
                result['feature_list'] = json.loads(result['feature_list'])
            if result.get('feature_importance'):
                result['feature_importance'] = json.loads(result['feature_importance'])
            if result.get('training_config'):
                result['training_config'] = json.loads(result['training_config'])
            if result.get('training_metrics'):
                result['training_metrics'] = json.loads(result['training_metrics'])
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取模型信息失败: {str(e)}")
            return None
    
    def list_models(self, model_type: Optional[str] = None) -> List[Dict]:
        """
        列出所有模型
        
        Args:
            model_type: 模型类型（None表示所有类型）
        
        Returns:
            模型列表
        """
        try:
            if model_type:
                sql = """
                    SELECT * FROM trained_models
                    WHERE model_type = %s
                    ORDER BY created_at DESC
                """
                params = (model_type,)
            else:
                sql = """
                    SELECT * FROM trained_models
                    ORDER BY created_at DESC
                """
                params = ()
            
            results = DatabaseConnection.execute_query(sql, params)
            
            # 解析JSON字段
            model_list = []
            for result in results:
                model_dict = dict(result)
                if model_dict.get('feature_list'):
                    try:
                        model_dict['feature_list'] = json.loads(model_dict['feature_list'])
                    except:
                        pass
                if model_dict.get('feature_importance'):
                    try:
                        model_dict['feature_importance'] = json.loads(model_dict['feature_importance'])
                    except:
                        pass
                if model_dict.get('training_config'):
                    try:
                        model_dict['training_config'] = json.loads(model_dict['training_config'])
                    except:
                        pass
                if model_dict.get('training_metrics'):
                    try:
                        model_dict['training_metrics'] = json.loads(model_dict['training_metrics'])
                    except:
                        pass
                model_list.append(model_dict)
            
            return model_list
            
        except Exception as e:
            self.logger.error(f"列出模型失败: {str(e)}")
            return []
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict]:
        """
        根据ID获取模型信息
        
        Args:
            model_id: 模型ID
        
        Returns:
            模型信息字典
        """
        try:
            sql = """
                SELECT * FROM trained_models
                WHERE id = %s
                LIMIT 1
            """
            results = DatabaseConnection.execute_query(sql, (model_id,))
            
            if not results:
                return None
            
            result = results[0]
            model_dict = dict(result)
            
            # 解析JSON字段
            if model_dict.get('feature_list'):
                try:
                    model_dict['feature_list'] = json.loads(model_dict['feature_list'])
                except:
                    pass
            if model_dict.get('feature_importance'):
                try:
                    model_dict['feature_importance'] = json.loads(model_dict['feature_importance'])
                except:
                    pass
            if model_dict.get('training_config'):
                try:
                    model_dict['training_config'] = json.loads(model_dict['training_config'])
                except:
                    pass
            if model_dict.get('training_metrics'):
                try:
                    model_dict['training_metrics'] = json.loads(model_dict['training_metrics'])
                except:
                    pass
            
            return model_dict
            
        except Exception as e:
            self.logger.error(f"获取模型信息失败: {str(e)}")
            return None
    
    def activate_model(self, model_id: int) -> bool:
        """
        激活模型（同一类型只能有一个激活的模型）
        
        Args:
            model_id: 模型ID
        
        Returns:
            是否成功
        """
        try:
            # 先获取模型类型
            sql = "SELECT model_type FROM trained_models WHERE id = %s"
            results = DatabaseConnection.execute_query(sql, (model_id,))
            
            if not results:
                self.logger.warning(f"模型不存在: ID={model_id}")
                return False
            
            model_type = results[0].get('model_type')
            
            # 先取消同类型其他模型的激活状态
            update_sql = "UPDATE trained_models SET is_active = 0 WHERE model_type = %s"
            DatabaseConnection.execute_update(update_sql, (model_type,))
            
            # 激活指定模型
            activate_sql = "UPDATE trained_models SET is_active = 1 WHERE id = %s"
            affected_rows = DatabaseConnection.execute_update(activate_sql, (model_id,))
            
            if affected_rows > 0:
                self.logger.info(f"模型激活成功: ID={model_id}")
                # 清除缓存
                self._model_cache.clear()
                return True
            else:
                self.logger.warning(f"模型激活失败: ID={model_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"激活模型失败: {str(e)}")
            return False
    
    def clear_cache(self):
        """清除模型缓存"""
        self._model_cache.clear()
        self.logger.info("模型缓存已清除")
