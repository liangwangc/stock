"""
股票预测记录数据库访问模块
"""
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config_db import USE_DATABASE
except ImportError:
    USE_DATABASE = False

logger = get_logger(__name__)


class StockPredictionDB:
    """股票预测记录数据库访问类"""
    
    def __init__(self):
        """初始化"""
        self.db = DatabaseConnection()
        self.use_database = USE_DATABASE
        self.logger = logger
    
    @staticmethod
    def _map_prediction_type_to_stock_type(prediction_type: str) -> str:
        """
        将prediction_type值映射到stock_type值
        
        Args:
            prediction_type: 'after_close' 或 'before_close'
        
        Returns:
            stock_type值: '收盘-明日' 或 '未收盘-明日'
        """
        mapping = {
            'after_close': '收盘-明日',
            'before_close': '未收盘-明日'
        }
        return mapping.get(prediction_type, prediction_type)
    
    @staticmethod
    def _map_stock_type_to_prediction_type(stock_type: str) -> str:
        """
        将stock_type值映射回prediction_type值
        
        Args:
            stock_type: '收盘-明日' 或 '未收盘-明日'
        
        Returns:
            prediction_type值: 'after_close' 或 'before_close'
        """
        mapping = {
            '收盘-明日': 'after_close',
            '未收盘-明日': 'before_close'
        }
        return mapping.get(stock_type, stock_type)
    
    def save_prediction(self, symbol: str, prediction_result: Dict, 
                       png_file: str = None, interactive_html: str = None, 
                       full_report_html: str = None, prediction_type: str = 'after_close'):
        """
        保存股票预测记录
        
        Args:
            symbol: 股票代码
            prediction_result: 预测结果字典
            png_file: PNG文件路径
            interactive_html: 交互式HTML路径
            full_report_html: 完整报告HTML路径
            prediction_type: 预测类型（'after_close'=收盘-明日，'before_close'=未收盘-明天）
        """
        if not self.use_database:
            return None
        
        try:
            # 提取数据
            name = prediction_result.get('name', '')
            prediction_date = prediction_result.get('prediction_date', '')
            target_date = prediction_result.get('target_date', '')
            current_price = prediction_result.get('current_price', 0)
            prediction = prediction_result.get('prediction', '震荡')
            up_probability = prediction_result.get('up_probability', 0)
            down_probability = prediction_result.get('down_probability', 0)
            confidence = prediction_result.get('confidence', 0)
            final_score = prediction_result.get('final_score', 0)
            predicted_close_price = prediction_result.get('predicted_close_price', None)  # 明日大概收盘价格
            predicted_change_pct = prediction_result.get('predicted_change_pct', None)  # 明日大概涨幅百分比
            prediction_time = prediction_result.get('prediction_time', datetime.now())
            summary = prediction_result.get('summary', '')
            
            # 提取实际结果
            actual_price = prediction_result.get('actual_price', None)
            actual_change_pct = prediction_result.get('actual_change_pct', None)
            
            # 计算偏差值（如果预测值和实际值都存在）
            deviation_pct = None
            absolute_deviation_pct = None
            deviation_price = None
            
            if predicted_change_pct is not None and actual_change_pct is not None:
                try:
                    deviation_pct = float(predicted_change_pct) - float(actual_change_pct)
                    absolute_deviation_pct = abs(deviation_pct)
                except (ValueError, TypeError):
                    pass
            
            if predicted_close_price is not None and actual_price is not None:
                try:
                    deviation_price = float(predicted_close_price) - float(actual_price)
                except (ValueError, TypeError):
                    pass
            
            # 提取学习分析相关字段（新增）
            market_state = prediction_result.get('market_state', {})
            market_state_str = market_state.get('state', 'sideways') if isinstance(market_state, dict) else (market_state if isinstance(market_state, str) else 'sideways')
            data_quality_score = prediction_result.get('data_quality_score', None)
            factor_consistency_score = prediction_result.get('factor_consistency_score', None)
            factor_weights = prediction_result.get('factor_weights', {})
            config_id = prediction_result.get('config_id', None)
            
            # 将factor_weights转换为JSON字符串
            import json
            factor_weights_json = json.dumps(factor_weights, ensure_ascii=False) if factor_weights else None
            
            # 从prediction_result中获取prediction_type，如果没有则使用参数值
            prediction_type = prediction_result.get('prediction_type', prediction_type)
            
            # 映射prediction_type值到stock_type值（如果使用stock_type字段）
            stock_type_value = self._map_prediction_type_to_stock_type(prediction_type) if prediction_type else None
            
            # 提取行业和板块信息（如果存在于prediction_result中）
            industry = prediction_result.get('industry', '')
            concepts = prediction_result.get('concepts', [])
            main_concept = prediction_result.get('main_concept', '')
            market = prediction_result.get('market', 'A股')
            
            # 如果concepts是列表，转换为JSON字符串
            import json
            if isinstance(concepts, list):
                concepts_json = json.dumps(concepts, ensure_ascii=False) if concepts else None
            else:
                concepts_json = concepts if concepts else None
            
            # 如果没有提供main_concept，从concepts中取第一个
            if not main_concept and concepts:
                if isinstance(concepts, list) and len(concepts) > 0:
                    main_concept = concepts[0]
                elif isinstance(concepts, str):
                    try:
                        concepts_list = json.loads(concepts)
                        if isinstance(concepts_list, list) and len(concepts_list) > 0:
                            main_concept = concepts_list[0]
                    except:
                        pass
            
            # 转换时间格式
            if isinstance(prediction_time, str):
                try:
                    prediction_time = datetime.strptime(prediction_time, '%Y-%m-%d %H:%M:%S')
                except:
                    prediction_time = datetime.now()
            
            prediction_time_str = prediction_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(prediction_time, datetime) else str(prediction_time)
            
            # 转换文件路径为相对路径（存储时只存文件名）
            png_basename = os.path.basename(png_file) if png_file else None
            interactive_basename = os.path.basename(interactive_html) if interactive_html else None
            full_report_basename = os.path.basename(full_report_html) if full_report_html else None
            
            # 构建SQL，尝试包含新字段（如果字段存在）
            try:
                # 先检查字段是否存在
                columns_check = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'industry'")
                has_industry_field = len(columns_check) > 0
                
                # 检查stock_type字段（优先）或prediction_type字段
                columns_check_stock_type = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'stock_type'")
                has_stock_type_field = len(columns_check_stock_type) > 0
                
                if not has_stock_type_field:
                    columns_check_type = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'prediction_type'")
                    has_prediction_type_field = len(columns_check_type) > 0
                else:
                    has_prediction_type_field = False
                
                columns_check_price = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'predicted_close_price'")
                has_predicted_price_field = len(columns_check_price) > 0
                
                # 检查学习分析相关字段
                columns_check_factor_weights = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'factor_weights'")
                has_factor_weights_field = len(columns_check_factor_weights) > 0
                
                columns_check_market_state = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'market_state'")
                has_market_state_field = len(columns_check_market_state) > 0
                
                columns_check_data_quality = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'data_quality_score'")
                has_data_quality_field = len(columns_check_data_quality) > 0
                
                columns_check_factor_consistency = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'factor_consistency_score'")
                has_factor_consistency_field = len(columns_check_factor_consistency) > 0
                
                columns_check_config_id = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'config_id'")
                has_config_id_field = len(columns_check_config_id) > 0
                
                # 检查偏差值字段
                columns_check_deviation = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'deviation_pct'")
                has_deviation_field = len(columns_check_deviation) > 0

                # 检查 ML 爆发增强相关字段（可选）
                columns_check_breakout = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'ml_breakout_score'")
                has_breakout_field = len(columns_check_breakout) > 0
                columns_check_boosted = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'ml_boosted_return'")
                has_boosted_field = len(columns_check_boosted) > 0
            except:
                has_industry_field = False
                has_stock_type_field = False
                has_prediction_type_field = False
                has_predicted_price_field = False
                has_factor_weights_field = False
                has_market_state_field = False
                has_data_quality_field = False
                has_factor_consistency_field = False
                has_config_id_field = False
                has_deviation_field = False
                has_breakout_field = False
                has_boosted_field = False
            
            # 根据字段存在情况选择使用stock_type还是prediction_type
            type_field_name = 'stock_type' if has_stock_type_field else ('prediction_type' if has_prediction_type_field else None)
            type_field_value = stock_type_value if has_stock_type_field else (prediction_type if has_prediction_type_field else None)
            
            # 构建字段列表和参数列表（动态添加学习分析字段）
            base_fields = []
            base_params = []
            base_updates = []
            
            # 基础字段
            base_fields.extend(['symbol', 'name'])
            base_params.extend([str(symbol).zfill(6), name])
            base_updates.extend(['name = VALUES(name)'])
            
            if has_industry_field:
                base_fields.append('industry')
                base_params.append(industry if industry else None)
                base_updates.append('industry = VALUES(industry)')
            
            if has_industry_field:
                base_fields.extend(['concepts', 'main_concept', 'market'])
                base_params.extend([concepts_json, main_concept if main_concept else None, market if market else 'A股'])
                base_updates.extend(['concepts = VALUES(concepts)', 'main_concept = VALUES(main_concept)', 'market = VALUES(market)'])
            
            base_fields.extend(['prediction_date', 'target_date'])
            base_params.extend([prediction_date if prediction_date else None, target_date if target_date else None])
            base_updates.extend(['prediction_date = VALUES(prediction_date)', 'target_date = VALUES(target_date)'])
            
            if type_field_name:
                base_fields.append(type_field_name)
                base_params.append(type_field_value)
                base_updates.append(f'{type_field_name} = VALUES({type_field_name})')
            
            base_fields.append('current_price')
            base_params.append(current_price if current_price else None)
            base_updates.append('current_price = VALUES(current_price)')
            
            if has_predicted_price_field:
                base_fields.extend(['predicted_close_price', 'predicted_change_pct'])
                base_params.extend([
                    predicted_close_price if predicted_close_price else None,
                    predicted_change_pct if predicted_change_pct is not None else None
                ])
                base_updates.extend([
                    'predicted_close_price = VALUES(predicted_close_price)',
                    'predicted_change_pct = VALUES(predicted_change_pct)'
                ])
            
            base_fields.extend(['prediction', 'up_probability', 'down_probability', 'confidence', 'final_score'])
            base_params.extend([
                prediction,
                up_probability if up_probability else None,
                down_probability if down_probability else None,
                confidence if confidence else None,
                final_score if final_score else None
            ])
            base_updates.extend([
                'prediction = VALUES(prediction)',
                'up_probability = VALUES(up_probability)',
                'down_probability = VALUES(down_probability)',
                'confidence = VALUES(confidence)',
                'final_score = VALUES(final_score)'
            ])
            
            # 添加学习分析字段（如果存在）
            if has_factor_weights_field:
                base_fields.append('factor_weights')
                base_params.append(factor_weights_json)
                base_updates.append('factor_weights = VALUES(factor_weights)')
            
            if has_market_state_field:
                base_fields.append('market_state')
                base_params.append(market_state_str)
                base_updates.append('market_state = VALUES(market_state)')
            
            if has_data_quality_field:
                base_fields.append('data_quality_score')
                base_params.append(data_quality_score)
                base_updates.append('data_quality_score = VALUES(data_quality_score)')
            
            if has_factor_consistency_field:
                base_fields.append('factor_consistency_score')
                base_params.append(factor_consistency_score)
                base_updates.append('factor_consistency_score = VALUES(factor_consistency_score)')
            
            if has_config_id_field:
                base_fields.append('config_id')
                base_params.append(config_id)
                base_updates.append('config_id = VALUES(config_id)')
            
            # 添加偏差值字段（如果存在）
            if has_deviation_field:
                base_fields.extend(['deviation_pct', 'absolute_deviation_pct', 'deviation_price'])
                base_params.extend([deviation_pct, absolute_deviation_pct, deviation_price])
                base_updates.extend([
                    'deviation_pct = VALUES(deviation_pct)',
                    'absolute_deviation_pct = VALUES(absolute_deviation_pct)',
                    'deviation_price = VALUES(deviation_price)'
                ])

            # 添加 ML 爆发增强相关字段（如果存在）
            if has_breakout_field:
                base_fields.append('ml_breakout_score')
                base_params.append(prediction_result.get('ml_breakout_score'))
                base_updates.append('ml_breakout_score = VALUES(ml_breakout_score)')

            if has_boosted_field:
                base_fields.append('ml_boosted_return')
                base_params.append(prediction_result.get('ml_boosted_return'))
                base_updates.append('ml_boosted_return = VALUES(ml_boosted_return)')
            
            base_fields.extend(['prediction_time', 'png_file', 'interactive_html', 'full_report_html', 'summary'])
            base_params.extend([
                prediction_time_str,
                png_basename,
                interactive_basename,
                full_report_basename,
                summary
            ])
            base_updates.extend([
                'prediction_time = VALUES(prediction_time)',
                'png_file = VALUES(png_file)',
                'interactive_html = VALUES(interactive_html)',
                'full_report_html = VALUES(full_report_html)',
                'summary = VALUES(summary)'
            ])
            
            # 构建SQL语句
            fields_str = ', '.join(base_fields)
            placeholders = ', '.join(['%s'] * len(base_fields))
            updates_str = ',\n                    '.join(base_updates)
            
            if has_industry_field and type_field_name and has_predicted_price_field:
                # 如果有所有新字段，使用包含所有新字段的SQL
                sql = f"""
                    INSERT INTO stock_predictions 
                    ({fields_str})
                    VALUES ({placeholders})
                    ON DUPLICATE KEY UPDATE
                    {updates_str}
                """
                params = tuple(base_params)
            elif has_industry_field and type_field_name:
                # 使用动态构建的SQL（已包含所有可用字段）
                sql = f"""
                    INSERT INTO stock_predictions 
                    ({fields_str})
                    VALUES ({placeholders})
                    ON DUPLICATE KEY UPDATE
                    {updates_str}
                """
                params = tuple(base_params)
            elif has_industry_field:
                # 如果有industry字段但没有prediction_type字段
                sql = """
                    INSERT INTO stock_predictions 
                    (symbol, name, industry, concepts, main_concept, market, prediction_date, target_date, 
                     current_price, prediction, up_probability, down_probability, confidence, final_score, 
                     prediction_time, png_file, interactive_html, full_report_html, summary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    str(symbol).zfill(6),
                    name,
                    industry if industry else None,
                    concepts_json,
                    main_concept if main_concept else None,
                    market if market else 'A股',
                    prediction_date if prediction_date else None,
                    target_date if target_date else None,
                    current_price if current_price else None,
                    prediction,
                    up_probability if up_probability else None,
                    down_probability if down_probability else None,
                    confidence if confidence else None,
                    final_score if final_score else None,
                    prediction_time_str,
                    png_basename,
                    interactive_basename,
                    full_report_basename,
                    summary
                )
            else:
                # 如果没有新字段，使用原来的SQL（向后兼容）
                sql = """
                    INSERT INTO stock_predictions 
                    (symbol, name, prediction_date, target_date, current_price, prediction,
                     up_probability, down_probability, confidence, final_score, prediction_time,
                     png_file, interactive_html, full_report_html, summary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    str(symbol).zfill(6),
                    name,
                    prediction_date if prediction_date else None,
                    target_date if target_date else None,
                    current_price if current_price else None,
                    prediction,
                    up_probability if up_probability else None,
                    down_probability if down_probability else None,
                    confidence if confidence else None,
                    final_score if final_score else None,
                    prediction_time_str,
                    png_basename,
                    interactive_basename,
                    full_report_basename,
                    summary
                )
            
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存预测记录到数据库: {symbol} - {prediction_date}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存预测记录到数据库失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def update_prediction_actual(self, symbol: str, target_date: str, 
                                 actual_price: float, actual_change_pct: float,
                                 actual_direction: str, prediction_hit: str,
                                 deviation_pct: float = None, absolute_deviation_pct: float = None,
                                 deviation_price: float = None):
        """
        更新预测记录的实际数据（包括偏差字段）
        
        Args:
            symbol: 股票代码
            target_date: 目标日期
            actual_price: 实际价格
            actual_change_pct: 实际涨跌幅
            actual_direction: 实际方向
            prediction_hit: 预测结果（命中/未命中）
            deviation_pct: 偏差值（预测涨跌幅 - 实际涨跌幅，可选）
            absolute_deviation_pct: 绝对偏差值（|预测涨跌幅 - 实际涨跌幅|，可选）
            deviation_price: 价格偏差（预测收盘价 - 实际价格，可选）
        """
        if not self.use_database:
            return False
        
        try:
            # 检查偏差字段是否存在
            try:
                columns_check = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'deviation_pct'")
                has_deviation_fields = len(columns_check) > 0
            except:
                has_deviation_fields = False
            
            if has_deviation_fields:
                # 如果偏差字段存在，更新所有字段
                sql = """
                    UPDATE stock_predictions 
                    SET actual_price = %s, actual_change_pct = %s, 
                        actual_direction = %s, prediction_hit = %s,
                        deviation_pct = %s, absolute_deviation_pct = %s, deviation_price = %s
                    WHERE symbol = %s AND target_date = %s
                """
                params = (
                    actual_price,
                    actual_change_pct,
                    actual_direction,
                    prediction_hit,
                    deviation_pct,
                    absolute_deviation_pct,
                    deviation_price,
                    str(symbol).zfill(6),
                    target_date
                )
            else:
                # 如果偏差字段不存在，只更新基本字段（向后兼容）
                sql = """
                    UPDATE stock_predictions 
                    SET actual_price = %s, actual_change_pct = %s, 
                        actual_direction = %s, prediction_hit = %s
                    WHERE symbol = %s AND target_date = %s
                """
                params = (
                    actual_price,
                    actual_change_pct,
                    actual_direction,
                    prediction_hit,
                    str(symbol).zfill(6),
                    target_date
                )
            
            self.db.execute_update(sql, params)
            self.logger.debug(f"更新预测记录实际数据: {symbol} - {target_date}")
            return True
            
        except Exception as e:
            self.logger.error(f"更新预测记录实际数据失败: {str(e)}")
            return False
    
    def get_predictions(self, symbol: Optional[str] = None, 
                       limit: Optional[int] = None,
                       order_by: str = 'prediction_time DESC',
                       prediction_type: Optional[str] = None,
                       target_date: Optional[str] = None) -> List[Dict]:
        """
        获取预测记录列表
        
        Args:
            symbol: 股票代码（可选，None表示获取所有）
            limit: 限制数量（可选）
            order_by: 排序方式（默认按预测时间倒序）
            prediction_type: 预测类型（可选，'after_close'或'before_close'）
            target_date: 目标日期过滤（可选，格式：'YYYY-MM-DD'）
            
        Returns:
            预测记录列表
        """
        if not self.use_database:
            return []
        
        try:
            # 检查stock_type字段（优先）或prediction_type字段是否存在
            has_stock_type_field = False
            has_prediction_type_field = False
            try:
                columns_check_stock_type = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'stock_type'")
                has_stock_type_field = len(columns_check_stock_type) > 0
                
                if not has_stock_type_field:
                    columns_check = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'prediction_type'")
                    has_prediction_type_field = len(columns_check) > 0
            except:
                has_stock_type_field = False
                has_prediction_type_field = False
            
            # 构建WHERE条件
            where_conditions = []
            params = []
            
            if symbol:
                where_conditions.append("symbol = %s")
                params.append(str(symbol).zfill(6))
            
            if prediction_type:
                # 优先使用stock_type字段，如果不存在则使用prediction_type字段
                if has_stock_type_field:
                    # 映射prediction_type值到stock_type值
                    stock_type_value = self._map_prediction_type_to_stock_type(prediction_type)
                    where_conditions.append("stock_type = %s AND stock_type IS NOT NULL")
                    params.append(stock_type_value)
                elif has_prediction_type_field:
                    # 明确过滤 prediction_type，排除 NULL 值
                    where_conditions.append("prediction_type = %s AND prediction_type IS NOT NULL")
                    params.append(prediction_type)
            
            # 添加 target_date 过滤条件（如果提供）
            if target_date:
                where_conditions.append("DATE(target_date) = %s")
                params.append(target_date)
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # 验证order_by（防止SQL注入）
            allowed_order_fields = {'prediction_time', 'prediction_date', 'target_date', 
                                 'confidence', 'final_score', 'current_price', 'symbol', 'name'}
            allowed_directions = {'ASC', 'DESC'}
            
            # 解析order_by
            order_parts = order_by.strip().upper().split()
            if len(order_parts) == 2:
                field, direction = order_parts
                if field.lower() in allowed_order_fields and direction in allowed_directions:
                    safe_order_by = f"{field.lower()} {direction}"
                else:
                    safe_order_by = "prediction_time DESC"  # 默认
            else:
                safe_order_by = "prediction_time DESC"  # 默认
            
            sql = f"""
                SELECT * FROM stock_predictions 
                {where_clause}
                ORDER BY {safe_order_by}
            """
            
            # 验证limit（防止SQL注入）
            if limit:
                try:
                    limit_int = int(limit)
                    if limit_int > 0 and limit_int <= 50000:  # 增加上限到50000，支持更多数据查询
                        sql += " LIMIT %s"
                        params.append(limit_int)
                    else:
                        self.logger.warning(f"limit值超出范围: {limit_int}，忽略")
                except (ValueError, TypeError):
                    self.logger.warning(f"无效的limit值: {limit}，忽略")
            
            # 记录SQL查询（调试用）
            self.logger.debug(f"【SQL查询】执行查询: {sql}")
            self.logger.debug(f"【SQL查询】参数: {params}")
            
            if params:
                results = self.db.execute_query(sql, tuple(params))
            else:
                results = self.db.execute_query(sql, None)
            
            self.logger.debug(f"【SQL查询】查询结果数量: {len(results) if results else 0}")
            
            # 转换结果为字典列表
            records = []
            for row in results:
                record = dict(row)
                # 转换文件路径为完整路径
                if record.get('png_file'):
                    record['png_file'] = os.path.join(project_root, 'reports', record['png_file'])
                if record.get('interactive_html'):
                    record['interactive_html'] = os.path.join(project_root, 'reports', record['interactive_html'])
                if record.get('full_report_html'):
                    record['full_report_html'] = os.path.join(project_root, 'reports', record['full_report_html'])
                records.append(record)
            
            return records
            
        except Exception as e:
            self.logger.error(f"获取预测记录失败: {str(e)}")
            return []
    
    def get_latest_prediction(self, symbol: str) -> Optional[Dict]:
        """
        获取指定股票的最新预测记录
        
        Args:
            symbol: 股票代码
            
        Returns:
            最新预测记录字典，如果不存在则返回None
        """
        if not self.use_database:
            return None
        
        try:
            sql = """
                SELECT 
                    symbol, name, prediction_date, target_date,
                    prediction, up_probability, down_probability, confidence,
                    final_score, summary, factors
                FROM stock_predictions
                WHERE symbol = %s
                ORDER BY prediction_time DESC
                LIMIT 1
            """
            results = self.db.execute_query(sql, (symbol,))
            
            if results and len(results) > 0:
                result = results[0]
                # 解析factors JSON（如果存在）
                factors_str = result.get('factors')
                if factors_str:
                    try:
                        import json
                        if isinstance(factors_str, str):
                            result['factors'] = json.loads(factors_str)
                        else:
                            result['factors'] = factors_str
                    except:
                        result['factors'] = {}
                return result
            return None
            
        except Exception as e:
            self.logger.error(f"获取最新预测记录失败: {str(e)}")
            return None
    
    def get_latest_predictions(self, limit: int = 10, prediction_type: str = 'after_close') -> List[Dict]:
        """
        获取最新的预测记录（每个股票只保留最新的一条）
        
        Args:
            limit: 返回数量限制
            prediction_type: 预测类型（'after_close'=收盘-明日，'before_close'=未收盘-明天）
            
        Returns:
            最新预测记录列表（每个股票只保留最新的一条，去重）
        """
        if not self.use_database:
            return []
        
        try:
            # 检查stock_type字段（优先）或prediction_type字段是否存在
            has_stock_type_field = False
            has_prediction_type_field = False
            try:
                columns_check_stock_type = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'stock_type'")
                has_stock_type_field = len(columns_check_stock_type) > 0
                
                if not has_stock_type_field:
                    columns_check = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'prediction_type'")
                    has_prediction_type_field = len(columns_check) > 0
            except:
                has_stock_type_field = False
                has_prediction_type_field = False
            
            # 使用子查询获取每个股票的最新预测时间，然后在应用层再次去重确保唯一性
            if has_stock_type_field or has_prediction_type_field:
                type_field_name = 'stock_type' if has_stock_type_field else 'prediction_type'
                # 如果使用stock_type字段，需要映射值
                if has_stock_type_field:
                    type_field_value = self._map_prediction_type_to_stock_type(prediction_type)
                else:
                    type_field_value = prediction_type
                
                sql = f"""
                    SELECT p1.* FROM stock_predictions p1
                    INNER JOIN (
                        SELECT symbol, MAX(prediction_time) as max_time
                        FROM stock_predictions
                        WHERE {type_field_name} = %s
                        GROUP BY symbol
                    ) p2 ON p1.symbol = p2.symbol AND p1.prediction_time = p2.max_time
                    WHERE p1.{type_field_name} = %s
                    ORDER BY p1.prediction_time DESC
                    LIMIT %s
                """
                results = self.db.execute_query(sql, (type_field_value, type_field_value, limit * 2))  # 多查询一些，以防去重后不够
            else:
                # 如果字段不存在，使用原来的逻辑（向后兼容）
                sql = """
                    SELECT p1.* FROM stock_predictions p1
                    INNER JOIN (
                        SELECT symbol, MAX(prediction_time) as max_time
                        FROM stock_predictions
                        GROUP BY symbol
                    ) p2 ON p1.symbol = p2.symbol AND p1.prediction_time = p2.max_time
                    ORDER BY p1.prediction_time DESC
                    LIMIT %s
                """
                results = self.db.execute_query(sql, (limit * 2,))  # 多查询一些，以防去重后不够
            
            # 在应用层再次去重，确保每个股票只有最新的一条
            # 使用字典存储，key为symbol，value为最新的记录
            latest_by_symbol = {}
            for row in results:
                record = dict(row)
                symbol = str(record.get('symbol', '')).strip().zfill(6)
                if not symbol:
                    continue
                
                # 转换文件路径
                if record.get('png_file'):
                    record['png_file'] = os.path.join(project_root, 'reports', record['png_file'])
                if record.get('interactive_html'):
                    record['interactive_html'] = os.path.join(project_root, 'reports', record['interactive_html'])
                if record.get('full_report_html'):
                    record['full_report_html'] = os.path.join(project_root, 'reports', record['full_report_html'])
                
                # 如果该股票还没有记录，或者当前记录的时间更新，则更新
                if symbol not in latest_by_symbol:
                    latest_by_symbol[symbol] = record
                else:
                    # 比较 prediction_time，保留最新的
                    current_time = record.get('prediction_time')
                    existing_time = latest_by_symbol[symbol].get('prediction_time')
                    if current_time and existing_time:
                        # 转换为datetime比较
                        try:
                            if isinstance(current_time, str):
                                current_dt = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
                            else:
                                current_dt = current_time
                            
                            if isinstance(existing_time, str):
                                existing_dt = datetime.strptime(existing_time, '%Y-%m-%d %H:%M:%S')
                            else:
                                existing_dt = existing_time
                            
                            if current_dt > existing_dt:
                                latest_by_symbol[symbol] = record
                        except:
                            # 如果时间解析失败，使用字符串比较
                            if str(current_time) > str(existing_time):
                                latest_by_symbol[symbol] = record
                    elif current_time and not existing_time:
                        latest_by_symbol[symbol] = record
            
            # 转换为列表，按 prediction_time 倒序排序
            records = list(latest_by_symbol.values())
            records.sort(key=lambda x: x.get('prediction_time', ''), reverse=True)
            
            # 限制返回数量
            return records[:limit]
            
        except Exception as e:
            self.logger.error(f"获取最新预测记录失败: {str(e)}")
            return []
