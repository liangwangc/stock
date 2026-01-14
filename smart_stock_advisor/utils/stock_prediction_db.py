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
            
            # 从prediction_result中获取prediction_type，如果没有则使用参数值
            prediction_type = prediction_result.get('prediction_type', prediction_type)
            
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
                
                columns_check_type = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'prediction_type'")
                has_prediction_type_field = len(columns_check_type) > 0
                
                columns_check_price = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'predicted_close_price'")
                has_predicted_price_field = len(columns_check_price) > 0
            except:
                has_industry_field = False
                has_prediction_type_field = False
                has_predicted_price_field = False
            
            if has_industry_field and has_prediction_type_field and has_predicted_price_field:
                # 如果有所有新字段，使用包含所有新字段的SQL
                sql = """
                    INSERT INTO stock_predictions 
                    (symbol, name, industry, concepts, main_concept, market, prediction_date, target_date, prediction_type,
                     current_price, predicted_close_price, predicted_change_pct, prediction, up_probability, down_probability, confidence, final_score, 
                     prediction_time, png_file, interactive_html, full_report_html, summary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    industry = VALUES(industry),
                    concepts = VALUES(concepts),
                    main_concept = VALUES(main_concept),
                    market = VALUES(market),
                    prediction_date = VALUES(prediction_date),
                    target_date = VALUES(target_date),
                    prediction_type = VALUES(prediction_type),
                    current_price = VALUES(current_price),
                    predicted_close_price = VALUES(predicted_close_price),
                    predicted_change_pct = VALUES(predicted_change_pct),
                    prediction = VALUES(prediction),
                    up_probability = VALUES(up_probability),
                    down_probability = VALUES(down_probability),
                    confidence = VALUES(confidence),
                    final_score = VALUES(final_score),
                    prediction_time = VALUES(prediction_time),
                    png_file = VALUES(png_file),
                    interactive_html = VALUES(interactive_html),
                    full_report_html = VALUES(full_report_html),
                    summary = VALUES(summary)
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
                    prediction_type,  # 添加预测类型
                    current_price if current_price else None,
                    predicted_close_price if predicted_close_price else None,
                    predicted_change_pct if predicted_change_pct is not None else None,
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
            elif has_industry_field and has_prediction_type_field:
                # 如果有新字段，使用包含新字段的SQL
                sql = """
                    INSERT INTO stock_predictions 
                    (symbol, name, industry, concepts, main_concept, market, prediction_date, target_date, prediction_type,
                     current_price, prediction, up_probability, down_probability, confidence, final_score, 
                     prediction_time, png_file, interactive_html, full_report_html, summary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    industry = VALUES(industry),
                    concepts = VALUES(concepts),
                    main_concept = VALUES(main_concept),
                    market = VALUES(market),
                    prediction_date = VALUES(prediction_date),
                    target_date = VALUES(target_date),
                    prediction_type = VALUES(prediction_type),
                    current_price = VALUES(current_price),
                    prediction = VALUES(prediction),
                    up_probability = VALUES(up_probability),
                    down_probability = VALUES(down_probability),
                    confidence = VALUES(confidence),
                    final_score = VALUES(final_score),
                    prediction_time = VALUES(prediction_time),
                    png_file = VALUES(png_file),
                    interactive_html = VALUES(interactive_html),
                    full_report_html = VALUES(full_report_html),
                    summary = VALUES(summary)
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
                    prediction_type,  # 添加预测类型
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
                                 actual_direction: str, prediction_hit: str):
        """
        更新预测记录的实际数据
        
        Args:
            symbol: 股票代码
            target_date: 目标日期
            actual_price: 实际价格
            actual_change_pct: 实际涨跌幅
            actual_direction: 实际方向
            prediction_hit: 预测结果（命中/未命中）
        """
        if not self.use_database:
            return False
        
        try:
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
                       prediction_type: Optional[str] = None) -> List[Dict]:
        """
        获取预测记录列表
        
        Args:
            symbol: 股票代码（可选，None表示获取所有）
            limit: 限制数量（可选）
            order_by: 排序方式（默认按预测时间倒序）
            prediction_type: 预测类型（可选，'after_close'或'before_close'）
            
        Returns:
            预测记录列表
        """
        if not self.use_database:
            return []
        
        try:
            # 检查prediction_type字段是否存在
            try:
                columns_check = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'prediction_type'")
                has_prediction_type_field = len(columns_check) > 0
            except:
                has_prediction_type_field = False
            
            # 构建WHERE条件
            where_conditions = []
            params = []
            
            if symbol:
                where_conditions.append("symbol = %s")
                params.append(str(symbol).zfill(6))
            
            if prediction_type and has_prediction_type_field:
                # 明确过滤 prediction_type，排除 NULL 值
                where_conditions.append("prediction_type = %s AND prediction_type IS NOT NULL")
                params.append(prediction_type)
            
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
                    if limit_int > 0 and limit_int <= 10000:  # 设置上限防止过大查询
                        sql += " LIMIT %s"
                        params.append(limit_int)
                    else:
                        self.logger.warning(f"limit值超出范围: {limit_int}，忽略")
                except (ValueError, TypeError):
                    self.logger.warning(f"无效的limit值: {limit}，忽略")
            
            if params:
                results = self.db.execute_query(sql, tuple(params))
            else:
                results = self.db.execute_query(sql, None)
            
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
            # 检查prediction_type字段是否存在
            try:
                columns_check = self.db.execute_query("SHOW COLUMNS FROM stock_predictions LIKE 'prediction_type'")
                has_prediction_type_field = len(columns_check) > 0
            except:
                has_prediction_type_field = False
            
            # 使用子查询获取每个股票的最新预测时间，然后在应用层再次去重确保唯一性
            if has_prediction_type_field:
                sql = """
                    SELECT p1.* FROM stock_predictions p1
                    INNER JOIN (
                        SELECT symbol, MAX(prediction_time) as max_time
                        FROM stock_predictions
                        WHERE prediction_type = %s
                        GROUP BY symbol
                    ) p2 ON p1.symbol = p2.symbol AND p1.prediction_time = p2.max_time
                    WHERE p1.prediction_type = %s
                    ORDER BY p1.prediction_time DESC
                    LIMIT %s
                """
                results = self.db.execute_query(sql, (prediction_type, prediction_type, limit * 2))  # 多查询一些，以防去重后不够
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
