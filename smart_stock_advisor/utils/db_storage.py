"""
数据库存储模块
用于将各种指标数据保存到MySQL数据库
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


class DatabaseStorage:
    """数据库存储管理器"""
    
    def __init__(self):
        """初始化数据库存储管理器"""
        self.db = DatabaseConnection()
        self.logger = logger
    
    def save_north_bound_capital(self, data: Dict, timestamp: datetime = None):
        """保存北向资金数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # 使用 INSERT ... ON DUPLICATE KEY UPDATE
            sql = """
                INSERT INTO north_bound_capital 
                (timestamp, date, today_net_inflow, avg_net_inflow_5d, avg_net_inflow_10d, trend)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                timestamp = VALUES(timestamp),
                today_net_inflow = VALUES(today_net_inflow),
                avg_net_inflow_5d = VALUES(avg_net_inflow_5d),
                avg_net_inflow_10d = VALUES(avg_net_inflow_10d),
                trend = VALUES(trend)
            """
            params = (
                timestamp_str,
                date_str,
                data.get('today_net_inflow', 0.0),
                data.get('avg_net_inflow_5d', 0.0),
                data.get('avg_net_inflow_10d', 0.0),
                data.get('trend', 'neutral')
            )
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存北向资金数据: {date_str}")
        except Exception as e:
            self.logger.error(f"保存北向资金数据失败: {str(e)}")
    
    def save_margin_trading_data(self, symbol: str, data: Dict, timestamp: datetime = None):
        """保存融资融券数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            symbol_str = str(symbol).zfill(6)
            
            sql = """
                INSERT INTO margin_trading 
                (timestamp, date, symbol, margin_balance, margin_change, margin_change_pct, short_balance, trend)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                timestamp = VALUES(timestamp),
                margin_balance = VALUES(margin_balance),
                margin_change = VALUES(margin_change),
                margin_change_pct = VALUES(margin_change_pct),
                short_balance = VALUES(short_balance),
                trend = VALUES(trend)
            """
            params = (
                timestamp_str,
                date_str,
                symbol_str,
                data.get('margin_balance', 0.0),
                data.get('margin_change', 0.0),
                data.get('margin_change_pct', 0.0),
                data.get('short_balance', 0.0),
                data.get('trend', 'stable')
            )
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存融资融券数据: {symbol} - {date_str}")
        except Exception as e:
            self.logger.error(f"保存融资融券数据失败: {str(e)}")
    
    def save_main_force_capital(self, symbol: str, data: Dict, timestamp: datetime = None):
        """保存主力资金数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            symbol_str = str(symbol).zfill(6)
            
            sql = """
                INSERT INTO main_force_capital 
                (timestamp, date, symbol, main_net_inflow, main_net_inflow_pct, trend)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                timestamp = VALUES(timestamp),
                main_net_inflow = VALUES(main_net_inflow),
                main_net_inflow_pct = VALUES(main_net_inflow_pct),
                trend = VALUES(trend)
            """
            params = (
                timestamp_str,
                date_str,
                symbol_str,
                data.get('main_net_inflow', 0.0),
                data.get('main_net_inflow_pct', 0.0),
                data.get('trend', 'neutral')
            )
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存主力资金数据: {symbol} - {date_str}")
        except Exception as e:
            self.logger.error(f"保存主力资金数据失败: {str(e)}")
    
    def save_sector_rotation_data(self, data: Dict, timestamp: datetime = None):
        """保存板块轮动数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # 删除当天的旧数据
            delete_sql = "DELETE FROM sector_rotation WHERE date = %s"
            self.db.execute_update(delete_sql, (date_str,))
            
            new_records = []
            
            # 处理行业板块数据
            industry_sectors = data.get('industry_sectors', {})
            for sector_name, sector_info in industry_sectors.items():
                new_records.append((
                    timestamp_str,
                    date_str,
                    sector_name,
                    'industry',
                    sector_info.get('change_pct', 0.0),
                    sector_info.get('capital_flow', 0.0),
                    sector_info.get('heat', 0.0),
                    1 if sector_name in data.get('hot_sectors', []) else 0
                ))
            
            # 处理概念板块数据
            concept_sectors = data.get('concept_sectors', {})
            for sector_name, sector_info in concept_sectors.items():
                new_records.append((
                    timestamp_str,
                    date_str,
                    sector_name,
                    'concept',
                    sector_info.get('change_pct', 0.0),
                    sector_info.get('capital_flow', 0.0),
                    sector_info.get('heat', 0.0),
                    1 if sector_name in data.get('hot_sectors', []) else 0
                ))
            
            if new_records:
                sql = """
                    INSERT INTO sector_rotation 
                    (timestamp, date, sector_name, sector_type, change_pct, capital_flow, heat, is_hot)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                self.db.execute_many(sql, new_records)
                self.logger.debug(f"保存板块轮动数据: {date_str} - {len(new_records)}条记录")
        except Exception as e:
            self.logger.error(f"保存板块轮动数据失败: {str(e)}")
    
    def save_technical_indicators(self, symbol: str, data: Dict, timestamp: datetime = None):
        """保存技术指标数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            symbol_str = str(symbol).zfill(6)
            
            sql = """
                INSERT INTO technical_indicators 
                (timestamp, date, symbol, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist,
                 kdj_k, kdj_d, kdj_j, boll_upper, boll_middle, boll_lower, volume_ratio, turnover_rate)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                timestamp = VALUES(timestamp),
                ma5 = VALUES(ma5), ma10 = VALUES(ma10), ma20 = VALUES(ma20), ma60 = VALUES(ma60),
                rsi = VALUES(rsi),
                macd = VALUES(macd), macd_signal = VALUES(macd_signal), macd_hist = VALUES(macd_hist),
                kdj_k = VALUES(kdj_k), kdj_d = VALUES(kdj_d), kdj_j = VALUES(kdj_j),
                boll_upper = VALUES(boll_upper), boll_middle = VALUES(boll_middle), boll_lower = VALUES(boll_lower),
                volume_ratio = VALUES(volume_ratio), turnover_rate = VALUES(turnover_rate)
            """
            params = (
                timestamp_str, date_str, symbol_str,
                data.get('ma5'), data.get('ma10'), data.get('ma20'), data.get('ma60'),
                data.get('rsi'),
                data.get('macd'), data.get('macd_signal'), data.get('macd_hist'),
                data.get('kdj_k'), data.get('kdj_d'), data.get('kdj_j'),
                data.get('boll_upper'), data.get('boll_middle'), data.get('boll_lower'),
                data.get('volume_ratio'), data.get('turnover_rate')
            )
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存技术指标数据: {symbol} - {date_str}")
        except Exception as e:
            self.logger.error(f"保存技术指标数据失败: {str(e)}")
    
    def save_news_sentiment(self, symbol: Optional[str], data: Dict, timestamp: datetime = None):
        """保存新闻情感数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            symbol_str = str(symbol).zfill(6) if symbol else None
            
            sql = """
                INSERT INTO news_sentiment 
                (timestamp, date, symbol, news_count, direct_news_count, industry_news_count,
                 positive_count, negative_count, sentiment, sentiment_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                timestamp = VALUES(timestamp),
                news_count = VALUES(news_count),
                direct_news_count = VALUES(direct_news_count),
                industry_news_count = VALUES(industry_news_count),
                positive_count = VALUES(positive_count),
                negative_count = VALUES(negative_count),
                sentiment = VALUES(sentiment),
                sentiment_score = VALUES(sentiment_score)
            """
            params = (
                timestamp_str, date_str, symbol_str,
                data.get('news_count', 0),
                data.get('direct_news_count', 0),
                data.get('industry_news_count', 0),
                data.get('positive_count', 0),
                data.get('negative_count', 0),
                data.get('sentiment', 'neutral'),
                data.get('sentiment_score', 0.0)
            )
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存新闻情感数据: {symbol or 'market'} - {date_str}")
        except Exception as e:
            self.logger.error(f"保存新闻情感数据失败: {str(e)}")
    
    def save_market_sentiment(self, data: Dict, timestamp: datetime = None):
        """保存市场情绪数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            index_predictions = data.get('index_predictions', {})
            index_predictions_json = json.dumps(index_predictions, ensure_ascii=False) if index_predictions else None
            
            sql = """
                INSERT INTO market_sentiment 
                (timestamp, date, overall_prediction, overall_up_probability, overall_down_probability,
                 index_predictions, trend)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                timestamp = VALUES(timestamp),
                overall_prediction = VALUES(overall_prediction),
                overall_up_probability = VALUES(overall_up_probability),
                overall_down_probability = VALUES(overall_down_probability),
                index_predictions = VALUES(index_predictions),
                trend = VALUES(trend)
            """
            params = (
                timestamp_str, date_str,
                data.get('overall_prediction', '震荡'),
                data.get('overall_up_probability', 0.5),
                data.get('overall_down_probability', 0.5),
                index_predictions_json,
                data.get('trend', 'neutral')
            )
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存市场情绪数据: {date_str}")
        except Exception as e:
            self.logger.error(f"保存市场情绪数据失败: {str(e)}")
    
    def save_prediction_factors(self, symbol: str, factors: Dict, prediction_result: Dict, timestamp: datetime = None):
        """保存预测因子数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # 类型检查：确保factors是字典类型，避免列表类型导致的错误
            if not isinstance(factors, dict):
                self.logger.error(f"保存预测因子数据失败: factors参数类型错误，期望dict，实际为{type(factors).__name__}")
                return
            
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            symbol_str = str(symbol).zfill(6)
            
            # 提取各因子数据（确保是字典类型，避免列表类型导致的错误）
            technical = factors.get('technical', {}) if isinstance(factors.get('technical'), dict) else {}
            news = factors.get('news', {}) if isinstance(factors.get('news'), dict) else {}
            capital_flow = factors.get('capital_flow', {}) if isinstance(factors.get('capital_flow'), dict) else {}
            market = factors.get('market', {}) if isinstance(factors.get('market'), dict) else {}
            history = factors.get('history', {}) if isinstance(factors.get('history'), dict) else {}
            # 【已优化移除】以下三个因子已从预测模型中移除
            # sector_rotation = factors.get('sector_rotation', {}) if isinstance(factors.get('sector_rotation'), dict) else {}
            # valuation = factors.get('valuation', {}) if isinstance(factors.get('valuation'), dict) else {}
            # us_sector = factors.get('us_sector', {}) if isinstance(factors.get('us_sector'), dict) else {}
            
            sql = """
                INSERT INTO prediction_factors 
                (timestamp, date, symbol, technical_score, technical_weight, technical_trend,
                 news_score, news_weight, news_sentiment,
                 capital_flow_score, capital_flow_weight, capital_flow_trend,
                 market_score, market_weight, market_trend,
                 sector_rotation_score, sector_rotation_weight, sector_rotation_trend,
                 history_score, history_weight, history_pattern,
                 valuation_score, valuation_weight, pe_ratio, pb_ratio,
                 us_sector_score, us_sector_weight, us_sector_name,
                 final_score, up_probability, down_probability, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                timestamp_str, date_str, symbol_str,
                technical.get('score'), technical.get('weight'), technical.get('trend'),
                news.get('score'), news.get('weight'), news.get('sentiment'),
                capital_flow.get('score'), capital_flow.get('weight'), capital_flow.get('trend'),
                market.get('score'), market.get('weight'), market.get('trend'),
                None, None, None,  # 【已优化移除】sector_rotation_score, sector_rotation_weight, sector_rotation_trend
                history.get('score'), history.get('weight'), history.get('pattern'),
                None, None, None, None,  # 【已优化移除】valuation_score, valuation_weight, pe_ratio, pb_ratio
                None, None, None,  # 【已优化移除】us_sector_score, us_sector_weight, us_sector_name
                prediction_result.get('final_score'),
                prediction_result.get('up_probability'),
                prediction_result.get('down_probability'),
                prediction_result.get('confidence')
            )
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存预测因子数据: {symbol} - {date_str}")
        except Exception as e:
            self.logger.error(f"保存预测因子数据失败: {str(e)}")
    
    def save_cost_distribution(self, symbol: str, cost_data: Dict, scope: str = 'history', timestamp: datetime = None):
        """保存成本分布数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            symbol_str = str(symbol).zfill(6)
            
            levels_json = json.dumps(cost_data.get('levels', []), ensure_ascii=False) if cost_data.get('levels') else None
            top_levels_json = json.dumps(cost_data.get('top_levels', []), ensure_ascii=False) if cost_data.get('top_levels') else None
            
            sql = """
                INSERT INTO cost_distribution 
                (timestamp, date, symbol, scope, levels, top_levels)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                timestamp = VALUES(timestamp),
                levels = VALUES(levels),
                top_levels = VALUES(top_levels)
            """
            params = (timestamp_str, date_str, symbol_str, scope, levels_json, top_levels_json)
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存成本分布数据: {symbol} - {date_str} - {scope}")
        except Exception as e:
            self.logger.error(f"保存成本分布数据失败: {str(e)}")
    
    def save_realtime_trading_decision(self, data: Dict, timestamp: datetime = None):
        """保存实时交易决策数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            date_str = timestamp.strftime('%Y-%m-%d')
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            symbol = data.get('symbol', '')
            decision = data.get('decision', {})
            quote = data.get('realtime_quote', {})
            prediction = data.get('prediction', {})
            capital_flow = data.get('capital_flow', {})
            trading_time = data.get('trading_time', {})
            
            reasons = decision.get('reasons', []) or []
            risk_warnings = decision.get('risk_warnings', []) or []
            
            sql = """
                INSERT INTO realtime_trading_decisions 
                (timestamp, date, symbol, mode, holding, cost_price, current_price, change_pct,
                 up_probability, down_probability, confidence, prediction_direction, target_date,
                 signal_strength, action, action_cn, strength, strength_cn, trading_session,
                 trading_message, main_net_inflow, total_net_inflow, flow_trend, reasons,
                 risk_warnings, position_advice)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                timestamp_str, date_str, str(symbol).zfill(6),
                data.get('mode', ''),
                int(bool(data.get('cost_price'))) if data.get('cost_price') else 0,
                data.get('cost_price'),
                quote.get('current_price'),
                quote.get('change_pct'),
                prediction.get('up_probability'),
                prediction.get('down_probability'),
                prediction.get('confidence'),
                prediction.get('direction', ''),
                prediction.get('target_date', ''),
                data.get('signal_strength'),
                decision.get('action', ''),
                decision.get('action_cn', ''),
                decision.get('strength', ''),
                decision.get('strength_cn', ''),
                trading_time.get('session', ''),
                trading_time.get('message', ''),
                capital_flow.get('main_net_inflow'),
                capital_flow.get('total_net_inflow'),
                capital_flow.get('flow_trend', ''),
                ' | '.join(str(r) for r in reasons),
                ' | '.join(str(r) for r in risk_warnings),
                decision.get('position_advice', '')
            )
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存实时交易决策数据: {symbol} - {date_str}")
        except Exception as e:
            self.logger.error(f"保存实时交易决策数据失败: {str(e)}")
