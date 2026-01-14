"""
预测参数配置管理器
用于管理预测模型的参数配置，支持动态加载和热更新
"""
import json
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


class PredictionConfigManager:
    """预测参数配置管理器（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PredictionConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.db = DatabaseConnection()
        self.logger = logger
        self._config_cache = {}  # 配置缓存 {config_id: {category: {key: value}}}
        self._active_config_id = None  # 当前激活的配置ID
        self._cache_lock = threading.Lock()
        self._initialized = True
        
        # 确保表存在
        self._ensure_tables_exist()
        
        # 加载激活的配置
        self._load_active_config()
    
    def _ensure_tables_exist(self):
        """确保数据表存在"""
        try:
            # 检查表是否存在
            try:
                self.db.execute_query("SELECT 1 FROM prediction_config LIMIT 1")
                self.logger.info("预测参数配置表已存在")
                return
            except Exception:
                # 表不存在，需要创建
                pass
            
            # 创建表
            sql_file = os.path.join(project_root, "database", "prediction_config_table.sql")
            if not os.path.exists(sql_file):
                self.logger.warning(f"SQL文件不存在: {sql_file}，将尝试直接创建表")
                self._create_tables_directly()
                return
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                create_sql = f.read()
            
            # 分割SQL语句（更精确的方式）
            statements = []
            current_statement = []
            for line in create_sql.split('\n'):
                line = line.strip()
                # 跳过注释行和空行
                if not line or line.startswith('--'):
                    continue
                current_statement.append(line)
                # 如果行以分号结尾，表示一个完整的语句
                if line.endswith(';'):
                    statement = ' '.join(current_statement).rstrip(';').strip()
                    if statement:
                        statements.append(statement)
                    current_statement = []
            
            # 执行所有SQL语句
            for statement in statements:
                if not statement:
                    continue
                try:
                    self.db.execute_update(statement)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "already exists" not in error_msg and "duplicate" not in error_msg and "table" not in error_msg:
                        self.logger.warning(f"创建表时出错: {str(e)}")
            
            self.logger.info("预测参数配置表创建完成")
        except Exception as e:
            self.logger.warning(f"检查数据表时出错: {str(e)}，尝试直接创建表")
            try:
                self._create_tables_directly()
            except Exception as e2:
                self.logger.error(f"直接创建表也失败: {str(e2)}")
    
    def _create_tables_directly(self):
        """直接创建表（不依赖SQL文件）"""
        try:
            # 创建配置主表
            sql1 = """
                CREATE TABLE IF NOT EXISTS `prediction_config` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `config_name` VARCHAR(100) NOT NULL COMMENT '配置名称',
                    `description` TEXT COMMENT '配置描述',
                    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认配置',
                    `is_active` TINYINT(1) DEFAULT 0 COMMENT '是否激活',
                    `created_by` INT COMMENT '创建人ID',
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY `uk_config_name` (`config_name`),
                    INDEX `idx_is_active` (`is_active`),
                    INDEX `idx_is_default` (`is_default`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测配置主表'
            """
            self.db.execute_update(sql1)
            
            # 创建配置值表
            sql2 = """
                CREATE TABLE IF NOT EXISTS `prediction_config_values` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `config_id` INT NOT NULL COMMENT '配置ID',
                    `category` VARCHAR(50) NOT NULL COMMENT '配置分类',
                    `param_key` VARCHAR(100) NOT NULL COMMENT '参数键',
                    `param_value` TEXT NOT NULL COMMENT '参数值',
                    `param_type` VARCHAR(20) NOT NULL COMMENT '参数类型',
                    `description` VARCHAR(255) COMMENT '参数描述',
                    `min_value` DECIMAL(10,4) COMMENT '最小值',
                    `max_value` DECIMAL(10,4) COMMENT '最大值',
                    `unit` VARCHAR(20) COMMENT '单位',
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (`config_id`) REFERENCES `prediction_config`(`id`) ON DELETE CASCADE,
                    UNIQUE KEY `uk_config_param` (`config_id`, `category`, `param_key`),
                    INDEX `idx_config_id` (`config_id`),
                    INDEX `idx_category` (`category`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置值表'
            """
            self.db.execute_update(sql2)
            
            # 创建配置历史表
            sql3 = """
                CREATE TABLE IF NOT EXISTS `prediction_config_history` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                    `config_id` INT NOT NULL COMMENT '配置ID',
                    `action` VARCHAR(20) NOT NULL COMMENT '操作类型',
                    `old_values` JSON COMMENT '修改前的值',
                    `new_values` JSON COMMENT '修改后的值',
                    `changed_by` INT COMMENT '修改人ID',
                    `change_description` VARCHAR(500) COMMENT '变更说明',
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (`config_id`) REFERENCES `prediction_config`(`id`) ON DELETE CASCADE,
                    INDEX `idx_config_id` (`config_id`),
                    INDEX `idx_created_at` (`created_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置历史表'
            """
            self.db.execute_update(sql3)
            
            self.logger.info("预测参数配置表已直接创建")
        except Exception as e:
            self.logger.error(f"直接创建表失败: {str(e)}")
            raise
    
    def _load_active_config(self):
        """加载当前激活的配置"""
        try:
            # 先检查表是否存在
            try:
                sql = "SELECT id FROM prediction_config WHERE is_active = 1 LIMIT 1"
                results = self.db.execute_query(sql)
                if results:
                    self._active_config_id = results[0]['id']
                    self.get_config(self._active_config_id)  # 加载到缓存
                    self.logger.info(f"已加载激活的配置，ID: {self._active_config_id}")
                else:
                    self.logger.info("未找到激活的配置，将使用config.py中的默认值")
            except Exception as e:
                # 表不存在或查询失败，使用默认配置
                self.logger.info(f"无法查询激活配置（表可能不存在）: {str(e)}，将使用config.py中的默认值")
        except Exception as e:
            self.logger.warning(f"加载激活配置失败: {str(e)}，将使用config.py中的默认值")
    
    def get_config(self, config_id: int = None) -> Dict:
        """
        获取配置（如果config_id为None，返回当前激活的配置）
        
        Args:
            config_id: 配置ID，如果为None则返回激活的配置
        
        Returns:
            配置字典，格式：{
                'prediction': {...},
                'indicator': {...},
                'news': {...},
                'trading': {...}
            }
        """
        try:
            # 如果未指定config_id，使用激活的配置
            if config_id is None:
                if self._active_config_id is None:
                    # 如果没有激活的配置，返回None（使用config.py默认值）
                    return None
                config_id = self._active_config_id
            
            # 检查缓存
            with self._cache_lock:
                if config_id in self._config_cache:
                    return self._config_cache[config_id]
            
            # 从数据库加载
            sql = """
                SELECT category, param_key, param_value, param_type
                FROM prediction_config_values
                WHERE config_id = %s
                ORDER BY category, param_key
            """
            results = self.db.execute_query(sql, (config_id,))
            
            if not results:
                return None
            
            # 组织配置数据
            config_dict = {
                'prediction': {},
                'indicator': {},
                'news': {},
                'trading': {}
            }
            
            for row in results:
                category = row['category']
                key = row['param_key']
                value_str = row['param_value']
                param_type = row['param_type']
                
                # 解析值
                if param_type == 'number':
                    try:
                        value = float(value_str)
                        # 如果是整数，返回整数
                        if value.is_integer():
                            value = int(value)
                    except ValueError:
                        value = 0.0
                elif param_type == 'boolean':
                    value = value_str.lower() in ('true', '1', 'yes', 'on')
                else:
                    value = value_str
                
                if category in config_dict:
                    config_dict[category][key] = value
            
            # 缓存配置
            with self._cache_lock:
                self._config_cache[config_id] = config_dict
            
            return config_dict
            
        except Exception as e:
            self.logger.error(f"获取配置失败: {str(e)}")
            return None
    
    def get_config_info(self, config_id: int = None) -> Optional[Dict]:
        """获取配置信息（不包括值）"""
        try:
            if config_id is None:
                config_id = self._active_config_id
                if config_id is None:
                    return None
            
            sql = "SELECT * FROM prediction_config WHERE id = %s"
            results = self.db.execute_query(sql, (config_id,))
            if results:
                return results[0]
            return None
        except Exception as e:
            self.logger.error(f"获取配置信息失败: {str(e)}")
            return None
    
    def get_all_configs(self) -> List[Dict]:
        """获取所有配置列表"""
        try:
            sql = """
                SELECT id, config_name, description, is_default, is_active, 
                       created_by, created_at, updated_at
                FROM prediction_config
                ORDER BY is_active DESC, is_default DESC, created_at DESC
            """
            return self.db.execute_query(sql)
        except Exception as e:
            self.logger.error(f"获取配置列表失败: {str(e)}")
            return []
    
    def create_config(self, config_name: str, description: str, values: Dict, 
                     user_id: int = None, is_default: bool = False) -> Optional[int]:
        """
        创建新配置
        
        Args:
            config_name: 配置名称
            description: 配置描述
            values: 配置值字典，格式：{
                'prediction': {...},
                'indicator': {...},
                'news': {...},
                'trading': {...}
            }
            user_id: 创建人ID
            is_default: 是否设为默认配置
        
        Returns:
            新创建的配置ID，失败返回None
        """
        try:
            # 验证配置
            is_valid, error_msg = self.validate_config(values)
            if not is_valid:
                self.logger.error(f"配置验证失败: {error_msg}")
                return None
            
            # 如果设为默认，先取消其他默认配置
            if is_default:
                sql = "UPDATE prediction_config SET is_default = 0"
                self.db.execute_update(sql)
            
            # 创建配置主记录
            sql = """
                INSERT INTO prediction_config 
                (config_name, description, is_default, is_active, created_by)
                VALUES (%s, %s, %s, 0, %s)
            """
            self.db.execute_update(sql, (config_name, description, 1 if is_default else 0, user_id))
            
            # 获取新创建的配置ID
            sql2 = "SELECT LAST_INSERT_ID() as id"
            results = self.db.execute_query(sql2)
            if not results:
                return None
            
            config_id = results[0]['id']
            
            # 保存配置值
            self._save_config_values(config_id, values, user_id)
            
            # 记录历史
            self._record_history(config_id, 'create', None, values, user_id, f"创建配置: {config_name}")
            
            # 清除缓存
            with self._cache_lock:
                if config_id in self._config_cache:
                    del self._config_cache[config_id]
            
            self.logger.info(f"创建配置成功: {config_name} (ID: {config_id})")
            return config_id
            
        except Exception as e:
            self.logger.error(f"创建配置失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def update_config(self, config_id: int, config_name: str = None, 
                     description: str = None, values: Dict = None,
                     user_id: int = None) -> bool:
        """更新配置"""
        try:
            # 获取旧值
            old_values = self.get_config(config_id)
            if old_values is None:
                self.logger.error(f"配置 {config_id} 不存在")
                return False
            
            # 更新主记录
            updates = []
            params = []
            if config_name:
                updates.append("config_name = %s")
                params.append(config_name)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            
            if updates:
                params.append(config_id)
                sql = f"UPDATE prediction_config SET {', '.join(updates)} WHERE id = %s"
                self.db.execute_update(sql, tuple(params))
            
            # 更新配置值
            if values:
                # 验证新值
                is_valid, error_msg = self.validate_config(values)
                if not is_valid:
                    self.logger.error(f"配置验证失败: {error_msg}")
                    return False
                
                self._save_config_values(config_id, values, user_id)
            
            # 记录历史
            new_values = values if values else old_values
            self._record_history(config_id, 'update', old_values, new_values, user_id, 
                               f"更新配置: {config_id}")
            
            # 清除缓存
            with self._cache_lock:
                if config_id in self._config_cache:
                    del self._config_cache[config_id]
            
            self.logger.info(f"更新配置成功: {config_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"更新配置失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def delete_config(self, config_id: int, user_id: int = None) -> bool:
        """删除配置"""
        try:
            # 获取配置信息
            config_info = self.get_config_info(config_id)
            if not config_info:
                return False
            
            # 不能删除激活的配置
            if config_info.get('is_active') == 1:
                self.logger.error(f"不能删除激活的配置: {config_id}")
                return False
            
            # 记录历史
            old_values = self.get_config(config_id)
            self._record_history(config_id, 'delete', old_values, None, user_id, 
                               f"删除配置: {config_info.get('config_name')}")
            
            # 删除配置（CASCADE会自动删除配置值）
            sql = "DELETE FROM prediction_config WHERE id = %s"
            self.db.execute_update(sql, (config_id,))
            
            # 清除缓存
            with self._cache_lock:
                if config_id in self._config_cache:
                    del self._config_cache[config_id]
            
            self.logger.info(f"删除配置成功: {config_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"删除配置失败: {str(e)}")
            return False
    
    def activate_config(self, config_id: int, user_id: int = None) -> bool:
        """激活配置"""
        try:
            # 检查配置是否存在
            config_info = self.get_config_info(config_id)
            if not config_info:
                self.logger.error(f"配置 {config_id} 不存在")
                return False
            
            # 取消其他激活的配置
            sql = "UPDATE prediction_config SET is_active = 0 WHERE is_active = 1"
            self.db.execute_update(sql)
            
            # 激活指定配置
            sql = "UPDATE prediction_config SET is_active = 1 WHERE id = %s"
            self.db.execute_update(sql, (config_id,))
            
            # 更新激活配置ID
            self._active_config_id = config_id
            
            # 清除缓存（强制重新加载）
            with self._cache_lock:
                self._config_cache.clear()
            
            # 记录历史
            self._record_history(config_id, 'activate', None, None, user_id, 
                               f"激活配置: {config_info.get('config_name')}")
            
            self.logger.info(f"激活配置成功: {config_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"激活配置失败: {str(e)}")
            return False
    
    def validate_config(self, values: Dict) -> Tuple[bool, str]:
        """
        验证配置值
        
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 检查必需的分类
            required_categories = ['prediction', 'indicator']
            for category in required_categories:
                if category not in values:
                    return False, f"缺少必需的分类: {category}"
            
            # 验证预测权重总和
            if 'prediction' in values:
                prediction = values['prediction']
                weight_keys = [
                    'news_weight', 'capital_flow_weight', 'market_weight',
                    'technical_weight', 'sector_rotation_weight',
                    'history_weight', 'us_sector_weight', 'valuation_weight'
                ]
                
                total_weight = 0
                for key in weight_keys:
                    if key in prediction:
                        weight = float(prediction[key])
                        if weight < 0 or weight > 1:
                            return False, f"权重 {key} 超出范围 [0, 1]: {weight}"
                        total_weight += weight
                
                # 允许±0.01的误差
                if abs(total_weight - 1.0) > 0.01:
                    return False, f"权重总和为 {total_weight:.2f}，应为 1.0（允许误差±0.01）"
            
            # 验证技术指标参数范围
            if 'indicator' in values:
                indicator = values['indicator']
                # MA参数
                if 'ma_short' in indicator and (indicator['ma_short'] < 1 or indicator['ma_short'] > 100):
                    return False, "MA短期参数应在 [1, 100] 范围内"
                if 'ma_long' in indicator and (indicator['ma_long'] < 1 or indicator['ma_long'] > 200):
                    return False, "MA长期参数应在 [1, 200] 范围内"
                # RSI参数
                if 'rsi_period' in indicator and (indicator['rsi_period'] < 2 or indicator['rsi_period'] > 100):
                    return False, "RSI周期应在 [2, 100] 范围内"
                # MACD参数
                if 'macd_fast' in indicator and (indicator['macd_fast'] < 1 or indicator['macd_fast'] > 50):
                    return False, "MACD快线应在 [1, 50] 范围内"
                if 'macd_slow' in indicator and (indicator['macd_slow'] < 1 or indicator['macd_slow'] > 100):
                    return False, "MACD慢线应在 [1, 100] 范围内"
            
            return True, "配置验证通过"
            
        except Exception as e:
            return False, f"验证配置时出错: {str(e)}"
    
    def _save_config_values(self, config_id: int, values: Dict, user_id: int = None):
        """保存配置值到数据库"""
        try:
            # 参数定义（包含类型、范围、描述等信息）
            param_definitions = self._get_param_definitions()
            
            # 先删除旧值
            sql = "DELETE FROM prediction_config_values WHERE config_id = %s"
            self.db.execute_update(sql, (config_id,))
            
            # 插入新值
            for category, category_values in values.items():
                if category not in param_definitions:
                    continue
                
                for param_key, param_value in category_values.items():
                    if param_key not in param_definitions[category]:
                        continue
                    
                    param_def = param_definitions[category][param_key]
                    param_type = param_def.get('type', 'number')
                    min_value = param_def.get('min')
                    max_value = param_def.get('max')
                    description = param_def.get('description', '')
                    unit = param_def.get('unit', '')
                    
                    # 转换为字符串
                    if param_type == 'boolean':
                        value_str = 'true' if param_value else 'false'
                    else:
                        value_str = str(param_value)
                    
                    sql = """
                        INSERT INTO prediction_config_values
                        (config_id, category, param_key, param_value, param_type, 
                         description, min_value, max_value, unit)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    self.db.execute_update(sql, (
                        config_id, category, param_key, value_str, param_type,
                        description, min_value, max_value, unit
                    ))
            
        except Exception as e:
            self.logger.error(f"保存配置值失败: {str(e)}")
            raise
    
    def _get_param_definitions(self) -> Dict:
        """获取参数定义（类型、范围、描述等）"""
        return {
            'prediction': {
                'news_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '', 
                               'description': '新闻情感权重（包含政策新闻）'},
                'capital_flow_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                       'description': '资金流向权重（北向资金、融资融券、主力资金）'},
                'market_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                 'description': '市场情绪权重（包含大盘指数影响）'},
                'technical_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                    'description': '技术指标权重'},
                'sector_rotation_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                          'description': '板块轮动权重'},
                'history_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                  'description': '历史模式权重'},
                'us_sector_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                    'description': '美股板块权重'},
                'valuation_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                    'description': '估值指标权重'},
                'min_confidence': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                  'description': '最小置信度'},
                'lookback_days': {'type': 'number', 'min': 30, 'max': 365, 'unit': '天',
                                 'description': '回看天数'},
            },
            'indicator': {
                'ma_short': {'type': 'number', 'min': 1, 'max': 100, 'unit': '日',
                            'description': '短期均线周期'},
                'ma_long': {'type': 'number', 'min': 1, 'max': 200, 'unit': '日',
                           'description': '长期均线周期'},
                'rsi_period': {'type': 'number', 'min': 2, 'max': 100, 'unit': '日',
                              'description': 'RSI周期（默认）'},
                'rsi_short': {'type': 'number', 'min': 2, 'max': 100, 'unit': '日',
                             'description': 'RSI短周期'},
                'rsi_mid': {'type': 'number', 'min': 2, 'max': 100, 'unit': '日',
                           'description': 'RSI中周期'},
                'macd_fast': {'type': 'number', 'min': 1, 'max': 50, 'unit': '日',
                             'description': 'MACD快线周期'},
                'macd_slow': {'type': 'number', 'min': 1, 'max': 100, 'unit': '日',
                             'description': 'MACD慢线周期'},
                'macd_signal': {'type': 'number', 'min': 1, 'max': 50, 'unit': '日',
                               'description': 'MACD信号线周期'},
                'kdj_period': {'type': 'number', 'min': 1, 'max': 50, 'unit': '日',
                              'description': 'KDJ周期'},
                'kdj_k_period': {'type': 'number', 'min': 1, 'max': 20, 'unit': '日',
                                'description': 'KDJ K值平滑周期'},
                'kdj_d_period': {'type': 'number', 'min': 1, 'max': 20, 'unit': '日',
                                'description': 'KDJ D值平滑周期'},
                'cci_period': {'type': 'number', 'min': 2, 'max': 100, 'unit': '日',
                              'description': 'CCI周期'},
            },
            'news': {
                'news_count': {'type': 'number', 'min': 5, 'max': 100, 'unit': '条',
                              'description': '分析的新闻数量'},
                'sentiment_threshold': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                       'description': '情感阈值'},
                'confidence_threshold': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                        'description': '置信度阈值'},
                'include_industry_news': {'type': 'boolean', 'min': None, 'max': None, 'unit': '',
                                         'description': '是否包含行业相关新闻'},
                'industry_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                   'description': '行业相关新闻的权重（相对于直接相关新闻）'},
            },
            'trading': {
                'buy_signal_threshold': {'type': 'number', 'min': 0.5, 'max': 0.9, 'unit': '',
                                        'description': '买入信号阈值（上涨概率超过此值考虑买入）'},
                'strong_buy_threshold': {'type': 'number', 'min': 0.7, 'max': 0.95, 'unit': '',
                                        'description': '强烈买入信号阈值'},
                'sell_signal_threshold': {'type': 'number', 'min': 0.5, 'max': 0.8, 'unit': '',
                                         'description': '卖出信号阈值（下跌概率超过此值考虑卖出）'},
                'strong_sell_threshold': {'type': 'number', 'min': 0.6, 'max': 0.9, 'unit': '',
                                         'description': '强烈卖出信号阈值'},
                'min_confidence': {'type': 'number', 'min': 0.3, 'max': 0.9, 'unit': '',
                                  'description': '最低置信度要求'},
                'high_confidence': {'type': 'number', 'min': 0.5, 'max': 0.95, 'unit': '',
                                   'description': '高置信度'},
                'capital_flow_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                       'description': '实时资金流向权重'},
                'bid_ask_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                  'description': '买卖盘分析权重'},
                'intraday_weight': {'type': 'number', 'min': 0, 'max': 1, 'unit': '',
                                   'description': '盘中涨跌调整权重'},
                'stop_loss_pct': {'type': 'number', 'min': -20, 'max': 0, 'unit': '%',
                                 'description': '止损比例'},
                'take_profit_pct': {'type': 'number', 'min': 0, 'max': 50, 'unit': '%',
                                   'description': '止盈比例'},
                'trailing_stop_pct': {'type': 'number', 'min': 0, 'max': 20, 'unit': '%',
                                     'description': '移动止损比例'},
                'max_position_pct': {'type': 'number', 'min': 1, 'max': 100, 'unit': '%',
                                    'description': '单只股票最大仓位'},
                'position_step': {'type': 'number', 'min': 1, 'max': 50, 'unit': '%',
                                 'description': '建仓步进'},
                'chase_high_threshold': {'type': 'number', 'min': 0, 'max': 20, 'unit': '%',
                                        'description': '追高警告阈值（今日涨幅%）'},
                'catch_low_threshold': {'type': 'number', 'min': -20, 'max': 0, 'unit': '%',
                                       'description': '抄底机会阈值（今日跌幅%）'},
                'monitor_interval': {'type': 'number', 'min': 10, 'max': 300, 'unit': '秒',
                                    'description': '默认监控间隔'},
                'alert_on_signal_change': {'type': 'boolean', 'min': None, 'max': None, 'unit': '',
                                          'description': '信号变化时是否提醒'},
            }
        }
    
    def _record_history(self, config_id: int, action: str, old_values: Dict = None,
                       new_values: Dict = None, user_id: int = None, description: str = None):
        """记录配置变更历史"""
        try:
            old_json = json.dumps(old_values, ensure_ascii=False) if old_values else None
            new_json = json.dumps(new_values, ensure_ascii=False) if new_values else None
            
            sql = """
                INSERT INTO prediction_config_history
                (config_id, action, old_values, new_values, changed_by, change_description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.db.execute_update(sql, (config_id, action, old_json, new_json, user_id, description))
        except Exception as e:
            self.logger.warning(f"记录配置历史失败: {str(e)}")
    
    def get_config_history(self, config_id: int, limit: int = 50) -> List[Dict]:
        """获取配置变更历史"""
        try:
            sql = """
                SELECT * FROM prediction_config_history
                WHERE config_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            results = self.db.execute_query(sql, (config_id, limit))
            
            # 解析JSON字段
            for result in results:
                if result.get('old_values'):
                    try:
                        result['old_values'] = json.loads(result['old_values']) if isinstance(result['old_values'], str) else result['old_values']
                    except:
                        result['old_values'] = None
                if result.get('new_values'):
                    try:
                        result['new_values'] = json.loads(result['new_values']) if isinstance(result['new_values'], str) else result['new_values']
                    except:
                        result['new_values'] = None
            
            return results
        except Exception as e:
            self.logger.error(f"获取配置历史失败: {str(e)}")
            return []
    
    def get_active_config_id(self) -> Optional[int]:
        """获取当前激活的配置ID"""
        return self._active_config_id
    
    def refresh_cache(self):
        """刷新配置缓存"""
        with self._cache_lock:
            self._config_cache.clear()
        self._load_active_config()
