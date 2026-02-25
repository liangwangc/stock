"""
机器学习数据加载模块
用于从数据库加载训练数据，构建特征和标签
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection
from utils.stock_history_storage import StockHistoryStorage

# 导入配置常量
try:
    from config import THREAD_POOL_CONFIG
except ImportError:
    # 如果导入失败，使用默认值
    THREAD_POOL_CONFIG = {
        "ml_training_default": 16,
        "ml_training_max": 16,
    }

logger = get_logger(__name__)


class MLDataLoader:
    """机器学习数据加载器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.storage = StockHistoryStorage()
        self.logger = logger
    
    def load_training_data(self, 
                          start_date: str,
                          end_date: str,
                          symbols: Optional[List[str]] = None,
                          min_samples_per_stock: int = 40) -> pd.DataFrame:
        """
        加载训练数据
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            symbols: 股票代码列表（None表示所有股票）
            min_samples_per_stock: 每只股票最少样本数
        
        Returns:
            包含特征和标签的DataFrame
        """
        try:
            self.logger.info(f"开始加载训练数据：{start_date} 到 {end_date}")
            
            # 1. 获取有实际结果的预测记录（作为标签）
            predictions_sql = """
                SELECT 
                    sp.symbol,
                    sp.prediction_date,
                    sp.target_date,
                    sp.current_price,
                    sp.predicted_close_price,
                    sp.predicted_change_pct,
                    sp.prediction,
                    sp.up_probability,
                    sp.down_probability,
                    sp.confidence,
                    sp.final_score,
                    sp.actual_price,
                    sp.actual_change_pct,
                    sp.actual_direction,
                    sp.prediction_hit,
                    sp.deviation_pct,
                    sp.absolute_deviation_pct,
                    sp.deviation_price
                FROM stock_predictions sp
                WHERE sp.target_date >= %s 
                  AND sp.target_date <= %s
                  AND sp.actual_price IS NOT NULL
                  AND sp.actual_direction IS NOT NULL
                  AND sp.prediction_hit IS NOT NULL
            """
            
            params = [start_date, end_date]
            if symbols:
                placeholders = ','.join(['%s'] * len(symbols))
                predictions_sql += f" AND sp.symbol IN ({placeholders})"
                params.extend(symbols)
            
            predictions_sql += " ORDER BY sp.symbol, sp.target_date"
            
            predictions = self.db.execute_query(predictions_sql, tuple(params))
            
            if not predictions:
                self.logger.warning(f"没有找到 {start_date} 到 {end_date} 期间的预测记录（需要 actual_price, actual_direction, prediction_hit 都不为空）")
                # 检查是否有预测记录但没有实际结果
                check_sql = """
                    SELECT COUNT(*) as total_count,
                           SUM(CASE WHEN actual_price IS NOT NULL THEN 1 ELSE 0 END) as with_actual_price,
                           SUM(CASE WHEN actual_direction IS NOT NULL THEN 1 ELSE 0 END) as with_actual_direction,
                           SUM(CASE WHEN prediction_hit IS NOT NULL THEN 1 ELSE 0 END) as with_prediction_hit
                    FROM stock_predictions
                    WHERE target_date >= %s AND target_date <= %s
                """
                check_params = [start_date, end_date]
                if symbols:
                    placeholders = ','.join(['%s'] * len(symbols))
                    check_sql += f" AND symbol IN ({placeholders})"
                    check_params.extend(symbols)
                
                check_result = self.db.execute_query(check_sql, tuple(check_params))
                if check_result:
                    stats = check_result[0]
                    self.logger.info(f"数据统计：总预测记录 {stats.get('total_count', 0)} 条")
                    self.logger.info(f"  - 有实际价格: {stats.get('with_actual_price', 0)} 条")
                    self.logger.info(f"  - 有实际方向: {stats.get('with_actual_direction', 0)} 条")
                    self.logger.info(f"  - 有预测命中: {stats.get('with_prediction_hit', 0)} 条")
                    self.logger.info("提示：需要等待预测记录的实际结果更新（通常需要等待股票收盘后更新）")
                return pd.DataFrame()
            
            self.logger.info(f"找到 {len(predictions)} 条有实际结果的预测记录")
            
            # 2. 获取对应的历史数据（作为特征）
            all_data = []
            skipped_no_history = 0
            skipped_insufficient_history = 0
            skipped_no_features = 0
            
            # 统计信息
            sample_count_by_stock = {}
            
            for idx, pred in enumerate(predictions):
                # 每处理1000条记录输出一次进度
                if (idx + 1) % 1000 == 0:
                    self.logger.info(f"处理进度: {idx + 1}/{len(predictions)}，已构建样本: {len(all_data)} 条")
                symbol = str(pred.get('symbol', '')).zfill(6)
                target_date = pred.get('target_date')
                
                if not symbol or not target_date:
                    continue
                
                # 获取该股票在目标日期之前的历史数据（用于构建特征）
                # 需要至少60天的数据来构建特征，查询前120天以确保有足够的数据（考虑非交易日）
                # 实际交易日：120天 ≈ 85-90个交易日，60天 ≈ 42-45个交易日
                target_date_obj = datetime.strptime(target_date, '%Y-%m-%d') if isinstance(target_date, str) else target_date
                feature_start_date = (target_date_obj - timedelta(days=120)).strftime('%Y-%m-%d')  # 查询前120天，确保有足够数据
                feature_end_date = (target_date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
                
                # 获取历史数据
                history_data = self.storage.get_stock_history_data(
                    symbol=symbol,
                    start_date=feature_start_date,
                    end_date=feature_end_date,
                    limit=None,
                    period_type='daily'
                )
                
                if not history_data:
                    skipped_no_history += 1
                    # 调试信息：记录为什么没有历史数据
                    if skipped_no_history <= 5:  # 只记录前5个，避免日志过多
                        self.logger.debug(f"股票 {symbol} 目标日期 {target_date} 没有历史数据（查询范围：{feature_start_date} 到 {feature_end_date}）")
                    continue
                
                # 检查是否有足够的数据
                # 实际交易日：60天 ≈ 42-45个交易日
                # 为了构建特征，至少需要40条记录（对应约60个自然日）
                # 但考虑到非交易日，查询120天应该能返回80-90条记录
                if len(history_data) < min_samples_per_stock:
                    skipped_insufficient_history += 1
                    # 调试信息：记录为什么数据不足（只记录前10个，避免日志过多）
                    if skipped_insufficient_history <= 10:
                        self.logger.warning(f"股票 {symbol} 目标日期 {target_date} 历史数据不足：找到 {len(history_data)} 条，需要至少 {min_samples_per_stock} 条（查询范围：{feature_start_date} 到 {feature_end_date}）")
                        # 检查是否有数据但数量不足
                        if len(history_data) > 0:
                            first_date = min([d.get('trade_date') for d in history_data if d.get('trade_date')])
                            last_date = max([d.get('trade_date') for d in history_data if d.get('trade_date')])
                            self.logger.debug(f"  实际数据日期范围：{first_date} 到 {last_date}")
                    continue
                
                # 统计每个股票的样本数
                if symbol not in sample_count_by_stock:
                    sample_count_by_stock[symbol] = 0
                sample_count_by_stock[symbol] += 1
                
                # 按日期排序（从早到晚）
                history_data_sorted = sorted(history_data, key=lambda x: x.get('trade_date'))
                
                # 构建特征（使用最近60天的数据）
                features = self._extract_features_from_history(history_data_sorted[-60:])
                
                if not features:
                    skipped_no_features += 1
                    continue
                
                # 添加标签
                features['label_direction'] = pred.get('actual_direction', '震荡')
                features['label_change_pct'] = float(pred.get('actual_change_pct', 0)) if pred.get('actual_change_pct') else 0.0
                features['label_up'] = 1 if pred.get('actual_direction') == '上涨' else 0
                features['label_up_probability'] = 1.0 if pred.get('actual_change_pct', 0) > 0 else 0.0
                
                # 添加元数据
                features['symbol'] = symbol
                features['target_date'] = target_date
                features['prediction_date'] = pred.get('prediction_date')
                
                all_data.append(features)
            
            if not all_data:
                self.logger.warning("没有构建出有效的训练样本")
                self.logger.info(f"数据统计：")
                self.logger.info(f"  - 找到预测记录: {len(predictions)} 条")
                self.logger.info(f"  - 缺少历史数据: {skipped_no_history} 条")
                self.logger.info(f"  - 历史数据不足（少于{min_samples_per_stock}条）: {skipped_insufficient_history} 条")
                self.logger.info(f"  - 无法提取特征: {skipped_no_features} 条")
                self.logger.info(f"  - 成功构建样本: {len(all_data)} 条")
                
                # 如果所有记录都因为历史数据不足被跳过，提供更详细的诊断信息
                if skipped_insufficient_history > 0 and skipped_no_history == 0:
                    self.logger.warning("所有记录都有历史数据，但数量不足")
                    self.logger.info("可能的原因：")
                    self.logger.info("  1. 查询日期范围可能有问题（检查 feature_start_date 和 feature_end_date）")
                    self.logger.info("  2. stock_history_data 表中可能缺少某些日期的数据")
                    self.logger.info("  3. 日期格式可能不匹配")
                    # 尝试查询一个样本，看看实际能查到多少数据
                    if len(predictions) > 0:
                        sample_pred = predictions[0]
                        sample_symbol = str(sample_pred.get('symbol', '')).zfill(6)
                        sample_target_date = sample_pred.get('target_date')
                        if sample_target_date:
                            try:
                                sample_target_date_obj = datetime.strptime(sample_target_date, '%Y-%m-%d') if isinstance(sample_target_date, str) else sample_target_date
                                sample_start = (sample_target_date_obj - timedelta(days=120)).strftime('%Y-%m-%d')
                                sample_end = (sample_target_date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
                                sample_data = self.storage.get_stock_history_data(
                                    symbol=sample_symbol,
                                    start_date=sample_start,
                                    end_date=sample_end,
                                    limit=None,
                                    period_type='daily'
                                )
                                self.logger.info(f"示例查询（股票 {sample_symbol}，目标日期 {sample_target_date}）：")
                                self.logger.info(f"  查询范围：{sample_start} 到 {sample_end}")
                                self.logger.info(f"  实际返回：{len(sample_data)} 条记录")
                                if len(sample_data) > 0:
                                    dates = sorted([d.get('trade_date') for d in sample_data if d.get('trade_date')])
                                    self.logger.info(f"  最早日期：{dates[0] if dates else 'N/A'}")
                                    self.logger.info(f"  最晚日期：{dates[-1] if dates else 'N/A'}")
                            except Exception as e:
                                self.logger.debug(f"示例查询失败: {str(e)}")
                
                self.logger.info("解决方案：")
                self.logger.info("  1. 确保 stock_history_data 表中有足够的历史数据（至少60-90天）")
                self.logger.info("  2. 检查日期范围是否合理（建议使用最近90天）")
                self.logger.info("  3. 如果数据确实存在，可能需要检查查询逻辑或数据库索引")
                return pd.DataFrame()
            
            # 输出统计信息
            if len(sample_count_by_stock) > 0:
                self.logger.info(f"样本分布：共 {len(sample_count_by_stock)} 只股票，平均每只股票 {len(all_data) / len(sample_count_by_stock):.1f} 条样本")
            
            # 3. 转换为DataFrame
            df = pd.DataFrame(all_data)
            
            self.logger.info(f"成功加载 {len(df)} 条训练样本，特征数：{len(df.columns)}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"加载训练数据失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def _extract_features_from_history(self, history_data: List[Dict]) -> Dict:
        """
        从历史数据中提取特征（兼容版本）
        
        注意：此函数与 _extract_features_from_history_fast() 有相似逻辑，但职责不同：
        - 此函数：兼容版本，用于单样本特征提取，接受字典列表
        - _extract_features_from_history_fast(): 性能优化版本，用于批量特征提取，接受DataFrame
        
        保持两个函数独立，不合并，以确保代码清晰和功能稳定。
        
        Args:
            history_data: 历史数据列表（按日期排序，从早到晚）
        
        Returns:
            特征字典
        """
        if not history_data or len(history_data) < 20:
            return {}
        
        try:
            # 性能优化：如果数据已经排序，避免重复排序
            # 转换为DataFrame便于计算
            df = pd.DataFrame(history_data)
            
            if len(df) == 0:
                return {}
            
            # 确保按日期排序（性能优化：只在需要时排序）
            if 'trade_date' in df.columns:
                try:
                    # 检查是否已经排序（性能优化：避免不必要的排序）
                    if not df['trade_date'].is_monotonic_increasing:
                        df['trade_date'] = pd.to_datetime(df['trade_date'])
                        df = df.sort_values('trade_date')
                    else:
                        # 如果已经排序，只需要转换日期格式（如果需要）
                        if df['trade_date'].dtype != 'datetime64[ns]':
                            try:
                                df['trade_date'] = pd.to_datetime(df['trade_date'])
                            except Exception:
                                pass
                except Exception:
                    # 如果日期解析失败，假设已经按顺序排列
                    pass
            
            # 获取最新一条数据（用于构建特征）
            latest = df.iloc[-1]
            
            features = {}
            
            # 1. 基础价格特征
            features['close_price'] = float(latest.get('close_price', 0)) if latest.get('close_price') else 0.0
            features['open_price'] = float(latest.get('open_price', 0)) if latest.get('open_price') else 0.0
            features['high_price'] = float(latest.get('high_price', 0)) if latest.get('high_price') else 0.0
            features['low_price'] = float(latest.get('low_price', 0)) if latest.get('low_price') else 0.0
            features['pre_close'] = float(latest.get('pre_close', 0)) if latest.get('pre_close') else 0.0
            features['change_pct'] = float(latest.get('change_pct', 0)) if latest.get('change_pct') else 0.0
            features['change_amount'] = float(latest.get('change_amount', 0)) if latest.get('change_amount') else 0.0
            
            # 2. 成交特征
            features['volume'] = float(latest.get('volume', 0)) if latest.get('volume') else 0.0
            features['amount'] = float(latest.get('amount', 0)) if latest.get('amount') else 0.0
            features['turnover_rate'] = float(latest.get('turnover_rate', 0)) if latest.get('turnover_rate') else 0.0
            features['volume_ratio'] = float(latest.get('volume_ratio', 0)) if latest.get('volume_ratio') else 0.0
            
            # 3. 技术指标特征（性能优化：避免重复的DataFrame转换）
            # 技术指标如果缺失，尝试使用前值（前向填充）
            # 优化：预先计算前向填充值，避免每次调用都遍历历史数据
            def get_technical_indicator(field_name: str, default_value: float = 0.0) -> float:
                """获取技术指标，如果缺失则尝试使用前值（性能优化版本）"""
                value = latest.get(field_name)
                if value is not None and pd.notna(value):
                    return float(value)
                
                # 性能优化：直接使用DataFrame的ffill方法，避免循环遍历
                if field_name in df.columns:
                    # 使用前向填充（兼容新旧pandas版本）
                    try:
                        filled_series = df[field_name].ffill()  # 新版本pandas
                    except AttributeError:
                        filled_series = df[field_name].fillna(method='ffill')  # 旧版本pandas
                    if len(filled_series) > 0:
                        last_filled = filled_series.iloc[-1]
                        if pd.notna(last_filled):
                            return float(last_filled)
                
                # 如果都没有，返回合理的默认值
                return default_value
            
            features['ma5'] = get_technical_indicator('ma5', 0.0)
            features['ma10'] = get_technical_indicator('ma10', 0.0)
            features['ma20'] = get_technical_indicator('ma20', 0.0)
            features['ma60'] = get_technical_indicator('ma60', 0.0)
            features['rsi'] = get_technical_indicator('rsi', 50.0)  # RSI默认50（中性）
            features['macd'] = get_technical_indicator('macd', 0.0)
            features['macd_signal'] = get_technical_indicator('macd_signal', 0.0)
            features['macd_hist'] = get_technical_indicator('macd_hist', 0.0)
            features['x2'] = get_technical_indicator('x2', 50.0)  # X2默认50（中性）
            
            # 4. 资金流向特征（优化：缺失值使用0，表示无数据）
            # 资金流向是实时数据，历史数据可能缺失，使用0表示无数据是合理的
            def get_capital_flow(field_name: str) -> float:
                """获取资金流向数据，缺失则返回0"""
                value = latest.get(field_name)
                if value is not None and pd.notna(value):
                    return float(value)
                return 0.0  # 缺失表示无数据，使用0
            
            features['main_net_inflow'] = get_capital_flow('main_net_inflow')
            features['super_large_inflow'] = get_capital_flow('super_large_inflow')
            features['large_inflow'] = get_capital_flow('large_inflow')
            features['medium_inflow'] = get_capital_flow('medium_inflow')
            features['small_inflow'] = get_capital_flow('small_inflow')
            
            # 5. 估值特征（性能优化：预先计算所有估值指标的中位数，避免重复计算）
            # 预先计算估值指标的中位数（只计算一次，避免在每次调用时重复计算）
            valuation_medians = {}
            valuation_fields = ['pe_ratio', 'pb_ratio', 'total_market_cap', 'float_market_cap']
            for field_name in valuation_fields:
                if field_name in df.columns:
                    try:
                        # 使用DataFrame直接计算中位数（排除0值和NULL）
                        valid_values = df[field_name].dropna()
                        valid_values = valid_values[valid_values > 0]  # 排除0值
                        if len(valid_values) > 0:
                            valuation_medians[field_name] = float(valid_values.median())
                        else:
                            valuation_medians[field_name] = 0.0
                    except Exception:
                        valuation_medians[field_name] = 0.0
                else:
                    valuation_medians[field_name] = 0.0
            
            def get_valuation_indicator(field_name: str) -> float:
                """获取估值指标，如果缺失则尝试使用历史中位数（性能优化版本）"""
                value = latest.get(field_name)
                if value is not None and pd.notna(value) and float(value) > 0:
                    return float(value)
                
                # 使用预先计算的中位数
                return valuation_medians.get(field_name, 0.0)
            
            features['pe_ratio'] = get_valuation_indicator('pe_ratio')
            features['pb_ratio'] = get_valuation_indicator('pb_ratio')
            features['total_market_cap'] = get_valuation_indicator('total_market_cap')
            features['float_market_cap'] = get_valuation_indicator('float_market_cap')
            
            # 6. 融资融券特征（优化：缺失值使用0，表示不支持融资融券）
            # 融资融券数据缺失通常表示该股票不支持融资融券，使用0是合理的
            def get_margin_trading(field_name: str) -> float:
                """获取融资融券数据，缺失则返回0"""
                value = latest.get(field_name)
                if value is not None and pd.notna(value):
                    return float(value)
                return 0.0  # 缺失表示不支持，使用0
            
            features['margin_balance'] = get_margin_trading('margin_balance')
            features['short_balance'] = get_margin_trading('short_balance')
            features['margin_ratio'] = get_margin_trading('margin_ratio')
            
            # 7. 衍生特征
            if features['ma5'] > 0:
                features['price_change_ma5'] = (features['close_price'] - features['ma5']) / features['ma5']
            else:
                features['price_change_ma5'] = 0.0
            
            if features['ma20'] > 0:
                features['price_change_ma20'] = (features['close_price'] - features['ma20']) / features['ma20']
            else:
                features['price_change_ma20'] = 0.0
            
            if features['ma60'] > 0:
                features['price_change_ma60'] = (features['close_price'] - features['ma60']) / features['ma60']
            else:
                features['price_change_ma60'] = 0.0
            
            # MA关系
            features['ma5_above_ma20'] = 1 if features['ma5'] > features['ma20'] else 0
            features['ma20_above_ma60'] = 1 if features['ma20'] > features['ma60'] else 0
            
            # RSI状态
            features['rsi_overbought'] = 1 if features['rsi'] > 70 else 0
            features['rsi_oversold'] = 1 if features['rsi'] < 30 else 0
            
            # MACD状态
            features['macd_bullish'] = 1 if features['macd'] > features['macd_signal'] else 0
            
            # 8. 时间序列特征（使用历史数据计算）
            if len(df) >= 5:
                try:
                    # 修复FutureWarning：先转换类型再fillna
                    close_prices = df['close_price'].astype(float).fillna(0).values
                    change_pcts = df['change_pct'].astype(float).fillna(0).values
                    volumes = df['volume'].astype(float).fillna(0).values
                    
                    # 滞后特征
                    features['close_price_lag_1'] = float(close_prices[-2]) if len(close_prices) >= 2 else 0.0
                    features['close_price_lag_5'] = float(close_prices[-6]) if len(close_prices) >= 6 else 0.0
                    features['change_pct_lag_1'] = float(change_pcts[-2]) if len(change_pcts) >= 2 else 0.0
                    features['change_pct_lag_5'] = float(np.mean(change_pcts[-6:-1])) if len(change_pcts) >= 6 else 0.0
                    
                    # 波动率
                    if len(change_pcts) >= 5:
                        features['volatility_5'] = float(np.std(change_pcts[-5:]))
                    else:
                        features['volatility_5'] = 0.0
                    
                    if len(change_pcts) >= 20:
                        features['volatility_20'] = float(np.std(change_pcts[-20:]))
                    else:
                        features['volatility_20'] = 0.0
                    
                    # 趋势
                    if len(close_prices) >= 6 and close_prices[-6] > 0:
                        features['trend_5'] = float((close_prices[-1] - close_prices[-6]) / close_prices[-6])
                    else:
                        features['trend_5'] = 0.0
                    
                    if len(close_prices) >= 21 and close_prices[-21] > 0:
                        features['trend_20'] = float((close_prices[-1] - close_prices[-21]) / close_prices[-21])
                    else:
                        features['trend_20'] = 0.0
                    
                    # 成交量均值
                    if len(volumes) >= 5:
                        features['volume_ma5'] = float(np.mean(volumes[-5:]))
                    else:
                        features['volume_ma5'] = 0.0
                    
                    if len(volumes) >= 20:
                        features['volume_ma20'] = float(np.mean(volumes[-20:]))
                    else:
                        features['volume_ma20'] = 0.0
                except Exception as e:
                    self.logger.debug(f"计算时间序列特征失败: {str(e)}")
                    # 设置默认值
                    features['close_price_lag_1'] = 0.0
                    features['close_price_lag_5'] = 0.0
                    features['change_pct_lag_1'] = 0.0
                    features['change_pct_lag_5'] = 0.0
                    features['volatility_5'] = 0.0
                    features['volatility_20'] = 0.0
                    features['trend_5'] = 0.0
                    features['trend_20'] = 0.0
                    features['volume_ma5'] = 0.0
                    features['volume_ma20'] = 0.0
            else:
                # 默认值
                features['close_price_lag_1'] = 0.0
                features['close_price_lag_5'] = 0.0
                features['change_pct_lag_1'] = 0.0
                features['change_pct_lag_5'] = 0.0
                features['volatility_5'] = 0.0
                features['volatility_20'] = 0.0
                features['trend_5'] = 0.0
                features['trend_20'] = 0.0
                features['volume_ma5'] = 0.0
                features['volume_ma20'] = 0.0
            
            # 9. 机构级增强因子（无未来函数：均基于当前截面日 T 及之前数据，用于预测 T+1）
            # 9.1 区间收益率（供横截面排名与相对强弱用）
            if len(df) >= 6:
                close_arr = df['close_price'].astype(float).fillna(0).values
                if close_arr[-6] > 0:
                    features['return_5d'] = float((close_arr[-1] - close_arr[-6]) / close_arr[-6])
                else:
                    features['return_5d'] = 0.0
            else:
                features['return_5d'] = 0.0
            if len(df) >= 21:
                close_arr = df['close_price'].astype(float).fillna(0).values
                if close_arr[-21] > 0:
                    features['return_20d'] = float((close_arr[-1] - close_arr[-21]) / close_arr[-21])
                else:
                    features['return_20d'] = 0.0
            else:
                features['return_20d'] = 0.0
            if len(df) >= 61:
                close_arr = df['close_price'].astype(float).fillna(0).values
                if close_arr[-61] > 0:
                    features['return_60d'] = float((close_arr[-1] - close_arr[-61]) / close_arr[-61])
                else:
                    features['return_60d'] = 0.0
            else:
                features['return_60d'] = 0.0
            
            # 9.2 Delta 因子（5 日变化）
            def _safe_val(series, idx, default=0.0):
                if series is None or len(series) == 0:
                    return default
                try:
                    n = len(series)
                    if idx < 0 and n < abs(idx):
                        return default
                    v = series.iloc[idx] if hasattr(series, 'iloc') else series[idx]
                    return float(v) if v is not None and pd.notna(v) else default
                except Exception:
                    return default
            if len(df) >= 6:
                rsi_ser = df['rsi'].ffill() if 'rsi' in df.columns else None
                features['rsi_change_5d'] = features['rsi'] - _safe_val(rsi_ser, -6, 50.0)
                if 'macd_hist' in df.columns:
                    macd_ser = df['macd_hist'].ffill()
                    features['macd_hist_change_5d'] = features['macd_hist'] - _safe_val(macd_ser, -6, 0.0)
                else:
                    features['macd_hist_change_5d'] = 0.0
                if 'volume_ratio' in df.columns:
                    vr_ser = df['volume_ratio'].ffill()
                    features['volume_ratio_change_5d'] = features['volume_ratio'] - _safe_val(vr_ser, -6, 0.0)
                else:
                    features['volume_ratio_change_5d'] = 0.0
                if 'turnover_rate' in df.columns:
                    tr_ser = df['turnover_rate'].ffill()
                    features['turnover_rate_change_5d'] = features['turnover_rate'] - _safe_val(tr_ser, -6, 0.0)
                else:
                    features['turnover_rate_change_5d'] = 0.0
                if 'main_net_inflow' in df.columns:
                    mn_ser = df['main_net_inflow'].ffill()
                    features['main_net_inflow_change_5d'] = features['main_net_inflow'] - _safe_val(mn_ser, -6, 0.0)
                else:
                    features['main_net_inflow_change_5d'] = 0.0
            else:
                features['rsi_change_5d'] = 0.0
                features['macd_hist_change_5d'] = 0.0
                features['volume_ratio_change_5d'] = 0.0
                features['turnover_rate_change_5d'] = 0.0
                features['main_net_inflow_change_5d'] = 0.0
            
            # 9.3 突破因子（0/1）：close/volume 是否 >= 过去 N 日最大值（不含当日，即 shift(1) 语义）
            close_arr = df['close_price'].astype(float).fillna(0).values
            vol_arr = df['volume'].astype(float).fillna(0).values
            if len(close_arr) >= 21:
                past_20_max = float(np.max(close_arr[-21:-1]))  # 前 20 日
                features['is_20d_high'] = 1 if close_arr[-1] >= past_20_max and past_20_max > 0 else 0
            else:
                features['is_20d_high'] = 0
            if len(close_arr) >= 61:
                past_60_max = float(np.max(close_arr[-61:-1]))
                features['is_60d_high'] = 1 if close_arr[-1] >= past_60_max and past_60_max > 0 else 0
            else:
                features['is_60d_high'] = 0
            if len(vol_arr) >= 21:
                past_20_vol_max = float(np.max(vol_arr[-21:-1]))
                features['is_volume_breakout'] = 1 if past_20_vol_max > 0 and vol_arr[-1] >= past_20_vol_max else 0
            else:
                features['is_volume_breakout'] = 0
            
            return features
            
        except Exception as e:
            self.logger.error(f"提取特征失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    def _extract_features_from_history_fast(self, df_history: pd.DataFrame, df_latest: pd.DataFrame, valuation_medians: dict) -> Dict:
        """
        快速提取特征（性能优化版本：使用预处理的DataFrame，避免重复创建和填充）
        
        注意：此函数与 _extract_features_from_history() 有相似逻辑，但职责不同：
        - _extract_features_from_history(): 兼容版本，用于单样本特征提取
        - _extract_features_from_history_fast(): 性能优化版本，用于批量特征提取
        
        保持两个函数独立，不合并，以确保代码清晰和功能稳定。
        
        Args:
            df_history: 历史数据DataFrame（已排序和填充）
            df_latest: 最新一条数据的DataFrame（单行）
            valuation_medians: 预先计算的估值指标中位数
        
        Returns:
            特征字典
        """
        if df_history.empty or df_latest.empty:
            return {}
        
        try:
            # 性能优化：直接访问Series，避免重复调用iloc[0]
            latest = df_latest.iloc[0]
            
            features = {}
            
            # 性能优化：定义安全转换函数，减少重复代码
            def safe_float(val, default=0.0):
                """安全转换为float（性能优化：减少重复的try-except）"""
                try:
                    if val is not None and pd.notna(val):
                        return float(val)
                except (ValueError, TypeError):
                    pass
                return default
            
            # 1. 基础价格特征
            
            # 性能优化：直接使用索引访问，避免get()函数调用
            features['close_price'] = safe_float(latest.get('close_price', 0) if 'close_price' in latest.index else None)
            features['open_price'] = safe_float(latest.get('open_price', 0) if 'open_price' in latest.index else None)
            features['high_price'] = safe_float(latest.get('high_price', 0) if 'high_price' in latest.index else None)
            features['low_price'] = safe_float(latest.get('low_price', 0) if 'low_price' in latest.index else None)
            features['pre_close'] = safe_float(latest.get('pre_close', 0) if 'pre_close' in latest.index else None)
            features['change_pct'] = safe_float(latest.get('change_pct', 0) if 'change_pct' in latest.index else None)
            features['change_amount'] = safe_float(latest.get('change_amount', 0) if 'change_amount' in latest.index else None)
            
            # 2. 成交特征
            features['volume'] = safe_float(latest.get('volume', 0) if 'volume' in latest.index else None)
            features['amount'] = safe_float(latest.get('amount', 0) if 'amount' in latest.index else None)
            features['turnover_rate'] = safe_float(latest.get('turnover_rate', 0) if 'turnover_rate' in latest.index else None)
            features['volume_ratio'] = safe_float(latest.get('volume_ratio', 0) if 'volume_ratio' in latest.index else None)
            
            # 性能优化：批量提取技术指标，减少函数调用开销
            # 3. 技术指标特征（使用已填充的数据）
            tech_fields = ['ma5', 'ma10', 'ma20', 'ma60', 'rsi', 'macd', 'macd_signal', 'macd_hist', 'x2']
            tech_defaults = {'ma5': 0.0, 'ma10': 0.0, 'ma20': 0.0, 'ma60': 0.0, 'rsi': 50.0, 'macd': 0.0, 'macd_signal': 0.0, 'macd_hist': 0.0, 'x2': 50.0}
            hist_len = len(df_history)
            
            for field_name in tech_fields:
                default_value = tech_defaults.get(field_name, 0.0)
                # 性能优化：直接访问，减少函数调用
                if field_name in latest.index:
                    value = latest[field_name]
                    if value is not None and pd.notna(value):
                        features[field_name] = float(value)
                        continue
                # 如果最新值缺失，使用历史数据的最后一个值（已填充）
                if hist_len > 0 and field_name in df_history.columns:
                    last_value = df_history[field_name].iloc[-1]
                    if pd.notna(last_value):
                        features[field_name] = float(last_value)
                        continue
                features[field_name] = default_value
            
            # 性能优化：批量提取，减少函数调用，使用safe_float函数
            # 4. 资金流向特征
            capital_flow_fields = ['main_net_inflow', 'super_large_inflow', 'large_inflow', 'medium_inflow', 'small_inflow']
            for field_name in capital_flow_fields:
                if field_name in latest.index:
                    features[field_name] = safe_float(latest[field_name])
                else:
                    features[field_name] = 0.0
            
            # 5. 估值特征（使用预先计算的中位数）
            valuation_fields = ['pe_ratio', 'pb_ratio', 'total_market_cap', 'float_market_cap']
            for field_name in valuation_fields:
                if field_name in latest.index:
                    value = latest[field_name]
                    if value is not None and pd.notna(value):
                        try:
                            val_float = float(value)
                            if val_float > 0:
                                features[field_name] = val_float
                                continue
                        except (ValueError, TypeError):
                            pass
                features[field_name] = valuation_medians.get(field_name, 0.0)
            
            # 6. 融资融券特征
            margin_fields = ['margin_balance', 'short_balance', 'margin_ratio']
            for field_name in margin_fields:
                if field_name in latest.index:
                    features[field_name] = safe_float(latest[field_name])
                else:
                    features[field_name] = 0.0
            
            # 7. 衍生特征
            if features['ma5'] > 0:
                features['price_change_ma5'] = (features['close_price'] - features['ma5']) / features['ma5']
            else:
                features['price_change_ma5'] = 0.0
            
            if features['ma20'] > 0:
                features['price_change_ma20'] = (features['close_price'] - features['ma20']) / features['ma20']
            else:
                features['price_change_ma20'] = 0.0
            
            if features['ma60'] > 0:
                features['price_change_ma60'] = (features['close_price'] - features['ma60']) / features['ma60']
            else:
                features['price_change_ma60'] = 0.0
            
            features['ma5_above_ma20'] = 1 if features['ma5'] > features['ma20'] else 0
            features['ma20_above_ma60'] = 1 if features['ma20'] > features['ma60'] else 0
            features['rsi_overbought'] = 1 if features['rsi'] > 70 else 0
            features['rsi_oversold'] = 1 if features['rsi'] < 30 else 0
            features['macd_bullish'] = 1 if features['macd'] > features['macd_signal'] else 0
            
            # 性能优化：预先提取数组，避免在条件判断中重复提取
            # 8. 时间序列特征（使用DataFrame向量化计算）
            hist_len = len(df_history)
            if hist_len >= 5:
                try:
                    # 性能优化：一次性提取所有需要的列，避免重复访问
                    # 修复FutureWarning：先转换类型再fillna
                    if 'close_price' in df_history.columns:
                        close_prices = df_history['close_price'].astype(float).fillna(0).values
                    else:
                        close_prices = np.zeros(hist_len)
                    
                    if 'change_pct' in df_history.columns:
                        change_pcts = df_history['change_pct'].astype(float).fillna(0).values
                    else:
                        change_pcts = np.zeros(hist_len)
                    
                    if 'volume' in df_history.columns:
                        volumes = df_history['volume'].astype(float).fillna(0).values
                    else:
                        volumes = np.zeros(hist_len)
                    
                    # 性能优化：使用numpy数组切片，比Python列表切片快
                    features['close_price_lag_1'] = float(close_prices[-2]) if hist_len >= 2 else 0.0
                    features['close_price_lag_5'] = float(close_prices[-6]) if hist_len >= 6 else 0.0
                    features['change_pct_lag_1'] = float(change_pcts[-2]) if hist_len >= 2 else 0.0
                    features['change_pct_lag_5'] = float(np.mean(change_pcts[-6:-1])) if hist_len >= 6 else 0.0
                    
                    features['volatility_5'] = float(np.std(change_pcts[-5:])) if hist_len >= 5 else 0.0
                    features['volatility_20'] = float(np.std(change_pcts[-20:])) if hist_len >= 20 else 0.0
                    
                    features['trend_5'] = float((close_prices[-1] - close_prices[-6]) / close_prices[-6]) if hist_len >= 6 and close_prices[-6] > 0 else 0.0
                    features['trend_20'] = float((close_prices[-1] - close_prices[-21]) / close_prices[-21]) if hist_len >= 21 and close_prices[-21] > 0 else 0.0
                    
                    features['volume_ma5'] = float(np.mean(volumes[-5:])) if hist_len >= 5 else 0.0
                    features['volume_ma20'] = float(np.mean(volumes[-20:])) if hist_len >= 20 else 0.0
                except Exception as e:
                    # 设置默认值
                    features['close_price_lag_1'] = 0.0
                    features['close_price_lag_5'] = 0.0
                    features['change_pct_lag_1'] = 0.0
                    features['change_pct_lag_5'] = 0.0
                    features['volatility_5'] = 0.0
                    features['volatility_20'] = 0.0
                    features['trend_5'] = 0.0
                    features['trend_20'] = 0.0
                    features['volume_ma5'] = 0.0
                    features['volume_ma20'] = 0.0
            else:
                features['close_price_lag_1'] = 0.0
                features['close_price_lag_5'] = 0.0
                features['change_pct_lag_1'] = 0.0
                features['change_pct_lag_5'] = 0.0
                features['volatility_5'] = 0.0
                features['volatility_20'] = 0.0
                features['trend_5'] = 0.0
                features['trend_20'] = 0.0
                features['volume_ma5'] = 0.0
                features['volume_ma20'] = 0.0
            
            return features
            
        except Exception as e:
            self.logger.debug(f"快速提取特征失败: {str(e)}")
            return {}
    
    def load_training_data_from_history(self,
                                       start_date: str,
                                       end_date: str,
                                       symbols: Optional[List[str]] = None,
                                       min_history_days: int = 60,
                                       lookahead_days: int = 1) -> pd.DataFrame:
        """
        直接从stock_history_data表加载训练数据（全量数据）
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            symbols: 股票代码列表（None表示所有股票）
            min_history_days: 最少历史数据天数（用于构建特征）
            lookahead_days: 预测未来多少天（默认1天，即明天）
        
        Returns:
            包含特征和标签的DataFrame
        """
        try:
            # 开始从stock_history_data表加载训练数据（减少日志输出）
            
            # 1. 获取所有股票的历史数据（性能优化：使用索引）
            if symbols:
                # 指定股票列表（性能优化：使用复合索引 idx_symbol_date）
                placeholders = ','.join(['%s'] * len(symbols))
                sql = f"""
                    SELECT symbol, trade_date, close_price, open_price, high_price, low_price,
                           pre_close, change_pct, change_amount, volume, amount, turnover_rate,
                           volume_ratio, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                           main_net_inflow, super_large_inflow, large_inflow, medium_inflow, small_inflow,
                           pe_ratio, pb_ratio, total_market_cap, float_market_cap,
                           margin_balance, short_balance, margin_ratio
                    FROM stock_history_data
                    WHERE period_type = 'daily'
                      AND trade_date >= %s
                      AND trade_date <= %s
                      AND symbol IN ({placeholders})
                    ORDER BY symbol, trade_date
                """
                params = [start_date, end_date] + [str(s).zfill(6) for s in symbols]
                # 性能说明：
                # 1. WHERE period_type = 'daily' 可以使用 idx_period_type 索引
                # 2. AND symbol IN (...) 可以使用 idx_symbol_date 或 uk_symbol_date_period 索引的前缀
                # 3. AND trade_date >= ? AND trade_date <= ? 可以使用 idx_symbol_date 索引
                # 4. ORDER BY symbol, trade_date 可以使用 idx_symbol_date 索引（完全匹配）
                # MySQL会自动选择最优索引（通常是 idx_symbol_date 或 uk_symbol_date_period）
            else:
                # 所有股票（性能优化：使用索引提示，优化查询顺序）
                # 注意：MySQL会自动选择最优索引，但我们可以通过查询顺序优化性能
                sql = """
                    SELECT symbol, trade_date, close_price, open_price, high_price, low_price,
                           pre_close, change_pct, change_amount, volume, amount, turnover_rate,
                           volume_ratio, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
                           main_net_inflow, super_large_inflow, large_inflow, medium_inflow, small_inflow,
                           pe_ratio, pb_ratio, total_market_cap, float_market_cap,
                           margin_balance, short_balance, margin_ratio
                    FROM stock_history_data
                    WHERE period_type = 'daily'
                      AND trade_date >= %s
                      AND trade_date <= %s
                    ORDER BY symbol, trade_date
                """
                params = [start_date, end_date]
                # 性能说明：
                # 1. WHERE period_type = 'daily' 可以使用 idx_period_type 索引
                # 2. AND trade_date >= ? AND trade_date <= ? 可以使用 idx_trade_date 或 idx_date_range 索引
                # 3. ORDER BY symbol, trade_date 可以使用 idx_symbol_date 或 idx_date_range 索引
                # MySQL会自动选择最优索引组合（通常是 idx_trade_date 或 idx_date_range）
            
            all_history = self.db.execute_query(sql, tuple(params))
            
            if not all_history:
                self.logger.warning(f"没有找到 {start_date} 到 {end_date} 期间的历史数据")
                return pd.DataFrame()
            
            self.logger.info(f"找到 {len(all_history)} 条历史记录")
            
            # 2. 按股票分组，构建训练样本
            from collections import defaultdict
            from datetime import datetime as dt
            import time
            
            # 性能优化：使用defaultdict，减少字典查找开销
            stock_data = defaultdict(list)
            
            # 性能优化：减少函数调用，直接访问字典键
            for record in all_history:
                symbol = record.get('symbol')
                if symbol:
                    symbol_str = str(symbol).zfill(6)
                    if record.get('trade_date'):
                        stock_data[symbol_str].append(record)
            
            total_stocks = len(stock_data)
            self.logger.info(f"找到 {total_stocks} 只股票")
            
            # 3. 为每只股票构建训练样本（性能优化：使用多线程并行处理）
            all_samples = []
            processed_stocks = 0
            skipped_stocks = 0
            start_time = time.time()
            
            # 定义处理单只股票的函数（用于并行处理）
            # 性能优化：批量提取特征，避免为每个样本都创建DataFrame
            def process_single_stock(symbol_records_tuple):
                """处理单只股票，构建训练样本（性能优化：批量特征提取）"""
                symbol, records = symbol_records_tuple
                stock_samples = []
                
                try:
                    # 性能优化：检查是否已排序，避免不必要的排序
                    # 如果records已经是按日期排序的，就不需要再排序
                    records_sorted = records
                    records_len = len(records)
                    if records_len > 1:
                        # 性能优化：快速检查：只检查第一个和最后一个记录
                        # 如果第一个日期大于最后一个日期，说明需要排序
                        first_date = records[0].get('trade_date')
                        last_date = records[-1].get('trade_date')
                        if first_date and last_date and first_date > last_date:
                            # 需要排序
                            records_sorted = sorted(records, key=lambda x: x.get('trade_date'))
                            records_len = len(records_sorted)
                    
                    # 需要至少min_history_days + lookahead_days天的数据
                    min_required = min_history_days + lookahead_days
                    if records_len < min_required:
                        return {'symbol': symbol, 'samples': [], 'skipped': True}
                    
                    # 性能优化：为整只股票创建一次DataFrame，然后批量提取特征
                    # 这样可以避免为每个样本都创建DataFrame（性能提升10-100倍）
                    # 使用更高效的数据类型
                    df_all = pd.DataFrame(records_sorted)
                    
                    # 性能优化：减少排序检查，只在必要时排序
                    if 'trade_date' in df_all.columns:
                        try:
                            # 快速检查：如果已经是datetime类型且已排序，跳过
                            if df_all['trade_date'].dtype == 'datetime64[ns]':
                                if df_all['trade_date'].is_monotonic_increasing:
                                    pass  # 已排序，无需操作
                                else:
                                    df_all = df_all.sort_values('trade_date')
                            else:
                                # 转换为datetime并检查排序
                                df_all['trade_date'] = pd.to_datetime(df_all['trade_date'])
                                if not df_all['trade_date'].is_monotonic_increasing:
                                    df_all = df_all.sort_values('trade_date')
                        except Exception:
                            # 如果转换失败，尝试排序（可能已经是字符串格式的日期）
                            try:
                                df_all = df_all.sort_values('trade_date')
                            except Exception:
                                pass
                    
                    # 性能优化：预先填充技术指标（一次性批量填充，避免循环）
                    technical_fields = ['ma5', 'ma10', 'ma20', 'ma60', 'rsi', 'macd', 'macd_signal', 'macd_hist', 'x2']
                    existing_tech_fields = [f for f in technical_fields if f in df_all.columns]
                    if existing_tech_fields:
                        # 批量填充，比循环快
                        df_all[existing_tech_fields] = df_all[existing_tech_fields].ffill()
                    
                    # 性能优化：预先计算估值指标的中位数（一次性计算，使用向量化操作）
                    valuation_medians = {}
                    valuation_fields = ['pe_ratio', 'pb_ratio', 'total_market_cap', 'float_market_cap']
                    for field_name in valuation_fields:
                        if field_name in df_all.columns:
                            try:
                                # 性能优化：使用numpy向量化操作，比pandas快
                                values = df_all[field_name].values
                                valid_values = values[(~pd.isna(values)) & (values > 0)]
                                if len(valid_values) > 0:
                                    valuation_medians[field_name] = float(np.median(valid_values))
                                else:
                                    valuation_medians[field_name] = 0.0
                            except Exception:
                                valuation_medians[field_name] = 0.0
                        else:
                            valuation_medians[field_name] = 0.0
                    
                    # 性能优化：预先提取所有需要的列到numpy数组，避免在循环中访问DataFrame
                    # 这是关键优化：避免每次循环都创建DataFrame切片和调用函数
                    df_len = len(df_all)
                    
                    # 提取所有需要的列到numpy数组（一次性提取，避免循环中重复访问）
                    def get_array(col_name, default=0.0):
                        if col_name in df_all.columns:
                            # 修复FutureWarning：先转换类型再fillna
                            col_data = df_all[col_name].astype(float)
                            return col_data.fillna(default).values
                        return np.full(df_len, default, dtype=float)
                    
                    # 预先提取所有列
                    close_prices = get_array('close_price', 0.0)
                    open_prices = get_array('open_price', 0.0)
                    high_prices = get_array('high_price', 0.0)
                    low_prices = get_array('low_price', 0.0)
                    pre_closes = get_array('pre_close', 0.0)
                    change_pcts = get_array('change_pct', 0.0)
                    change_amounts = get_array('change_amount', 0.0)
                    volumes = get_array('volume', 0.0)
                    amounts = get_array('amount', 0.0)
                    turnover_rates = get_array('turnover_rate', 0.0)
                    volume_ratios = get_array('volume_ratio', 0.0)
                    
                    # 技术指标
                    ma5s = get_array('ma5', 0.0)
                    ma10s = get_array('ma10', 0.0)
                    ma20s = get_array('ma20', 0.0)
                    ma60s = get_array('ma60', 0.0)
                    rsis = get_array('rsi', 50.0)
                    macds = get_array('macd', 0.0)
                    macd_signals = get_array('macd_signal', 0.0)
                    macd_hists = get_array('macd_hist', 0.0)
                    x2s = get_array('x2', 50.0)
                    
                    # 资金流向
                    main_net_inflows = get_array('main_net_inflow', 0.0)
                    super_large_inflows = get_array('super_large_inflow', 0.0)
                    large_inflows = get_array('large_inflow', 0.0)
                    medium_inflows = get_array('medium_inflow', 0.0)
                    small_inflows = get_array('small_inflow', 0.0)
                    
                    # 融资融券
                    margin_balances = get_array('margin_balance', 0.0)
                    short_balances = get_array('short_balance', 0.0)
                    margin_ratios = get_array('margin_ratio', 0.0)
                    
                    # 日期
                    if 'trade_date' in df_all.columns:
                        trade_dates = df_all['trade_date'].values
                    else:
                        trade_dates = None
                    
                    # 性能优化：预先计算数组长度和范围，避免重复计算
                    records_len = len(records_sorted)
                    # 修复：max_i 应该是 records_len - lookahead_days，因为 future_idx = i + lookahead_days
                    # 需要确保 future_idx < records_len，所以 i < records_len - lookahead_days
                    max_i = records_len - lookahead_days - 1  # 减1是因为range是左闭右开区间
                    
                    # 性能优化：安全转换函数（定义在循环外，避免重复定义）
                    def safe_float(val, default=0.0):
                        try:
                            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                                return float(val)
                        except (ValueError, TypeError):
                            pass
                        return default
                    
                    # 遍历每一天，构建训练样本（直接使用numpy数组，避免DataFrame切片和函数调用）
                    for i in range(min_history_days, max_i + 1):
                        # 性能优化：提前检查价格，避免不必要的特征提取
                        if close_prices[i] <= 0:
                            continue
                        
                        current_price = float(close_prices[i])
                        # 修复：未来价格应该是 i + lookahead_days，而不是 i + lookahead_days - 1
                        # 如果 lookahead_days = 1，那么未来价格应该是 close_prices[i + 1]
                        future_idx = i + lookahead_days
                        if future_idx >= df_len or close_prices[future_idx] <= 0:
                            continue
                        future_price = float(close_prices[future_idx])
                        
                        # 性能优化：直接在循环中构建特征，避免DataFrame切片和函数调用
                        features = {}
                        
                        # 1. 基础价格特征（直接使用数组索引）
                        features['close_price'] = current_price
                        features['open_price'] = safe_float(open_prices[i])
                        features['high_price'] = safe_float(high_prices[i])
                        features['low_price'] = safe_float(low_prices[i])
                        features['pre_close'] = safe_float(pre_closes[i])
                        features['change_pct'] = safe_float(change_pcts[i])
                        features['change_amount'] = safe_float(change_amounts[i])
                        
                        # 2. 成交特征
                        features['volume'] = safe_float(volumes[i])
                        features['amount'] = safe_float(amounts[i])
                        features['turnover_rate'] = safe_float(turnover_rates[i])
                        features['volume_ratio'] = safe_float(volume_ratios[i])
                        
                        # 3. 技术指标特征（直接使用数组索引）
                        features['ma5'] = safe_float(ma5s[i], 0.0)
                        features['ma10'] = safe_float(ma10s[i], 0.0)
                        features['ma20'] = safe_float(ma20s[i], 0.0)
                        features['ma60'] = safe_float(ma60s[i], 0.0)
                        features['rsi'] = safe_float(rsis[i], 50.0)
                        features['macd'] = safe_float(macds[i], 0.0)
                        features['macd_signal'] = safe_float(macd_signals[i], 0.0)
                        features['macd_hist'] = safe_float(macd_hists[i], 0.0)
                        features['x2'] = safe_float(x2s[i], 50.0)
                        
                        # 4. 资金流向特征
                        features['main_net_inflow'] = safe_float(main_net_inflows[i])
                        features['super_large_inflow'] = safe_float(super_large_inflows[i])
                        features['large_inflow'] = safe_float(large_inflows[i])
                        features['medium_inflow'] = safe_float(medium_inflows[i])
                        features['small_inflow'] = safe_float(small_inflows[i])
                        
                        # 5. 估值特征（使用预先计算的中位数）
                        # 注意：估值特征需要从DataFrame获取，但我们已经预先计算了中位数
                        for field_name in ['pe_ratio', 'pb_ratio', 'total_market_cap', 'float_market_cap']:
                            if field_name in df_all.columns:
                                val = df_all[field_name].iloc[i]
                                if pd.notna(val) and float(val) > 0:
                                    features[field_name] = float(val)
                                else:
                                    features[field_name] = valuation_medians.get(field_name, 0.0)
                            else:
                                features[field_name] = valuation_medians.get(field_name, 0.0)
                        
                        # 6. 融资融券特征
                        features['margin_balance'] = safe_float(margin_balances[i])
                        features['short_balance'] = safe_float(short_balances[i])
                        features['margin_ratio'] = safe_float(margin_ratios[i])
                        
                        # 7. 衍生特征
                        if features['ma5'] > 0:
                            features['price_change_ma5'] = (features['close_price'] - features['ma5']) / features['ma5']
                        else:
                            features['price_change_ma5'] = 0.0
                        
                        if features['ma20'] > 0:
                            features['price_change_ma20'] = (features['close_price'] - features['ma20']) / features['ma20']
                        else:
                            features['price_change_ma20'] = 0.0
                        
                        if features['ma60'] > 0:
                            features['price_change_ma60'] = (features['close_price'] - features['ma60']) / features['ma60']
                        else:
                            features['price_change_ma60'] = 0.0
                        
                        features['ma5_above_ma20'] = 1 if features['ma5'] > features['ma20'] else 0
                        features['ma20_above_ma60'] = 1 if features['ma20'] > features['ma60'] else 0
                        features['rsi_overbought'] = 1 if features['rsi'] > 70 else 0
                        features['rsi_oversold'] = 1 if features['rsi'] < 30 else 0
                        features['macd_bullish'] = 1 if features['macd'] > features['macd_signal'] else 0
                        
                        # 8. 时间序列特征（使用numpy数组切片，避免DataFrame访问）
                        history_start_idx = i - min_history_days
                        hist_len = min_history_days
                        
                        if hist_len >= 5:
                            try:
                                # 使用numpy数组切片，比DataFrame切片快得多
                                hist_close = close_prices[history_start_idx:i]
                                hist_change_pct = change_pcts[history_start_idx:i]
                                hist_volume = volumes[history_start_idx:i]
                                
                                hist_len_actual = len(hist_close)
                                
                                features['close_price_lag_1'] = float(hist_close[-2]) if hist_len_actual >= 2 else 0.0
                                features['close_price_lag_5'] = float(hist_close[-6]) if hist_len_actual >= 6 else 0.0
                                features['change_pct_lag_1'] = float(hist_change_pct[-2]) if hist_len_actual >= 2 else 0.0
                                features['change_pct_lag_5'] = float(np.mean(hist_change_pct[-6:-1])) if hist_len_actual >= 6 else 0.0
                                
                                features['volatility_5'] = float(np.std(hist_change_pct[-5:])) if hist_len_actual >= 5 else 0.0
                                features['volatility_20'] = float(np.std(hist_change_pct[-20:])) if hist_len_actual >= 20 else 0.0
                                
                                features['trend_5'] = float((hist_close[-1] - hist_close[-6]) / hist_close[-6]) if hist_len_actual >= 6 and hist_close[-6] > 0 else 0.0
                                features['trend_20'] = float((hist_close[-1] - hist_close[-21]) / hist_close[-21]) if hist_len_actual >= 21 and hist_close[-21] > 0 else 0.0
                                
                                features['volume_ma5'] = float(np.mean(hist_volume[-5:])) if hist_len_actual >= 5 else 0.0
                                features['volume_ma20'] = float(np.mean(hist_volume[-20:])) if hist_len_actual >= 20 else 0.0
                            except Exception:
                                # 设置默认值
                                features['close_price_lag_1'] = 0.0
                                features['close_price_lag_5'] = 0.0
                                features['change_pct_lag_1'] = 0.0
                                features['change_pct_lag_5'] = 0.0
                                features['volatility_5'] = 0.0
                                features['volatility_20'] = 0.0
                                features['trend_5'] = 0.0
                                features['trend_20'] = 0.0
                                features['volume_ma5'] = 0.0
                                features['volume_ma20'] = 0.0
                        else:
                            features['close_price_lag_1'] = 0.0
                            features['close_price_lag_5'] = 0.0
                            features['change_pct_lag_1'] = 0.0
                            features['change_pct_lag_5'] = 0.0
                            features['volatility_5'] = 0.0
                            features['volatility_20'] = 0.0
                            features['trend_5'] = 0.0
                            features['trend_20'] = 0.0
                            features['volume_ma5'] = 0.0
                            features['volume_ma20'] = 0.0
                        
                        # 9. 机构级增强因子（无未来函数）
                        if i >= 5 and close_prices[i - 5] > 0:
                            features['return_5d'] = float((close_prices[i] - close_prices[i - 5]) / close_prices[i - 5])
                        else:
                            features['return_5d'] = 0.0
                        if i >= 20 and close_prices[i - 20] > 0:
                            features['return_20d'] = float((close_prices[i] - close_prices[i - 20]) / close_prices[i - 20])
                        else:
                            features['return_20d'] = 0.0
                        if i >= 60 and close_prices[i - 60] > 0:
                            features['return_60d'] = float((close_prices[i] - close_prices[i - 60]) / close_prices[i - 60])
                        else:
                            features['return_60d'] = 0.0
                        
                        features['rsi_change_5d'] = float(rsis[i] - rsis[i - 5]) if i >= 5 else 0.0
                        features['macd_hist_change_5d'] = float(macd_hists[i] - macd_hists[i - 5]) if i >= 5 else 0.0
                        features['volume_ratio_change_5d'] = float(volume_ratios[i] - volume_ratios[i - 5]) if i >= 5 else 0.0
                        features['turnover_rate_change_5d'] = float(turnover_rates[i] - turnover_rates[i - 5]) if i >= 5 else 0.0
                        features['main_net_inflow_change_5d'] = float(main_net_inflows[i] - main_net_inflows[i - 5]) if i >= 5 else 0.0
                        
                        if i >= 20:
                            past_20_max = float(np.max(close_prices[i - 20:i]))
                            features['is_20d_high'] = 1 if past_20_max > 0 and close_prices[i] >= past_20_max else 0
                        else:
                            features['is_20d_high'] = 0
                        if i >= 60:
                            past_60_max = float(np.max(close_prices[i - 60:i]))
                            features['is_60d_high'] = 1 if past_60_max > 0 and close_prices[i] >= past_60_max else 0
                        else:
                            features['is_60d_high'] = 0
                        if i >= 20:
                            past_20_vol_max = float(np.max(volumes[i - 20:i]))
                            features['is_volume_breakout'] = 1 if past_20_vol_max > 0 and volumes[i] >= past_20_vol_max else 0
                        else:
                            features['is_volume_breakout'] = 0
                        
                        # 标签：涨跌幅
                        change_pct = (future_price - current_price) / current_price * 100
                        
                        # 标签：方向（上涨/下跌/震荡）
                        if change_pct > 0.5:  # 涨幅超过0.5%算上涨
                            direction = '上涨'
                            label_up = 1
                        elif change_pct < -0.5:  # 跌幅超过0.5%算下跌
                            direction = '下跌'
                            label_up = 0
                        else:  # 震荡
                            direction = '震荡'
                            label_up = 0  # 震荡算作下跌（二分类）
                        
                        # 添加标签
                        features['label_direction'] = direction
                        features['label_change_pct'] = change_pct
                        features['label_up'] = label_up
                        features['label_up_probability'] = 1.0 if change_pct > 0 else 0.0
                        
                        # 添加元数据
                        features['symbol'] = symbol
                        # 性能优化：直接使用数组访问日期
                        # 注意：future_idx 已经修正为 i + lookahead_days
                        if trade_dates is not None:
                            features['target_date'] = str(trade_dates[i])
                            features['future_date'] = str(trade_dates[future_idx])
                        else:
                            current_record = records_sorted[i]
                            future_record = records_sorted[future_idx]
                            features['target_date'] = str(current_record.get('trade_date'))
                            features['future_date'] = str(future_record.get('trade_date'))
                        
                        stock_samples.append(features)
                    
                    return {'symbol': symbol, 'samples': stock_samples, 'skipped': False}
                except Exception as e:
                    self.logger.error(f"处理股票 {symbol} 时发生异常: {str(e)}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return {'symbol': symbol, 'samples': [], 'skipped': True, 'error': str(e)}
            
            # 性能优化：使用多线程并行处理（CPU密集型任务，但受GIL限制）
            # 注意：虽然特征提取是CPU密集型，但由于大量使用pandas/numpy（C扩展），
            # 线程池仍然有效。进程池需要函数可序列化，实现复杂，暂时使用线程池。
            import os
            import threading
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            # 根据股票数量自动调整线程数（性能优化：增加线程数）
            cpu_count = os.cpu_count() or 4
            # 使用更多线程以提高性能（最多使用CPU核心数，但不超过配置的最大线程数）
            max_workers = min(cpu_count, THREAD_POOL_CONFIG["ml_training_max"])  # 最多使用配置的最大线程数
            if total_stocks < 100:
                max_workers = min(max_workers, 4)  # 少量股票时减少线程数
            elif total_stocks < 500:
                max_workers = min(max_workers, 8)  # 中等数量股票时使用8个线程
            # 大量股票时使用更多线程（最多使用配置的最大线程数）
            
            # 使用多线程并行处理特征提取（减少日志输出）
            
            # 线程安全的计数器
            processed_lock = threading.Lock()
            skipped_lock = threading.Lock()
            samples_lock = threading.Lock()
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_symbol = {
                    executor.submit(process_single_stock, (symbol, records)): symbol
                    for symbol, records in stock_data.items()
                }
                
                # 处理完成的任务
                completed_count = 0
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    completed_count += 1
                    
                    try:
                        result = future.result()
                        if result.get('skipped'):
                            with skipped_lock:
                                skipped_stocks += 1
                        else:
                            with processed_lock:
                                processed_stocks += 1
                            with samples_lock:
                                all_samples.extend(result.get('samples', []))
                    except Exception as e:
                        self.logger.error(f"获取股票 {symbol} 的处理结果失败: {str(e)}")
                        with skipped_lock:
                            skipped_stocks += 1
                    
                    # 每处理500只股票或最后一只股票时显示进度（减少日志输出）
                    if completed_count % 500 == 0 or completed_count == total_stocks:
                        elapsed = time.time() - start_time
                        progress_pct = (completed_count / total_stocks) * 100
                        avg_time_per_stock = elapsed / completed_count if completed_count > 0 else 0
                        remaining_stocks = total_stocks - completed_count
                        estimated_remaining = avg_time_per_stock * remaining_stocks
                        
                        self.logger.info(
                            f"进度: {completed_count}/{total_stocks} ({progress_pct:.1f}%) | "
                            f"已生成: {len(all_samples):,} 条样本 | "
                            f"耗时: {elapsed:.1f}秒 | 预计剩余: {estimated_remaining:.1f}秒"
                        )
            
            if not all_samples:
                self.logger.warning("没有构建出有效的训练样本")
                return pd.DataFrame()
            
            # 性能优化：转换为DataFrame时直接指定数据类型（比后续转换快）
            # 4. 转换为DataFrame（性能优化：使用float32减少内存和提升计算速度）
            if not all_samples:
                self.logger.warning("没有构建出有效的训练样本")
                return pd.DataFrame()
            
            # 性能优化：如果样本数量很大，分批转换（避免一次性创建大DataFrame）
            # 但通常样本数量不会太大，直接转换即可
            df = pd.DataFrame(all_samples)
            
            # 性能优化：批量转换数据类型，比逐列转换快
            # 定义需要保持float64的大字段
            large_fields = {'volume', 'amount', 'main_net_inflow', 'super_large_inflow', 
                          'large_inflow', 'medium_inflow', 'small_inflow', 
                          'margin_balance', 'short_balance', 'total_market_cap', 'float_market_cap'}
            
            # 性能优化：批量转换，只转换数值列且不在large_fields中的列
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            cols_to_convert = [col for col in numeric_cols if col not in large_fields]
            if cols_to_convert:
                try:
                    # 批量转换，比循环快
                    df[cols_to_convert] = df[cols_to_convert].astype('float32')
                except (ValueError, OverflowError):
                    # 如果批量转换失败，逐列转换（降级处理）
                    for col in cols_to_convert:
                        try:
                            df[col] = df[col].astype('float32')
                        except (ValueError, OverflowError):
                            pass
            
            # 成功构建训练样本（减少日志输出）
            
            # 5. 检查数据质量（可选，但建议执行）
            if len(df) > 0:
                quality_report = self.check_training_data_quality(df)
                if quality_report.get('warnings'):
                    self.logger.warning(f"数据质量检查发现 {len(quality_report['warnings'])} 个警告")
                    for warning in quality_report['warnings'][:5]:  # 只显示前5个警告
                        self.logger.warning(f"  - {warning}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"从历史数据加载训练数据失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def check_training_data_quality(self, df: pd.DataFrame, 
                                   min_completeness: float = 0.5,
                                   critical_fields: Optional[List[str]] = None) -> Dict:
        """
        检查训练数据质量
        
        Args:
            df: 训练数据DataFrame
            min_completeness: 最低完整率阈值（低于此值的字段会被标记）
            critical_fields: 关键字段列表（这些字段缺失会发出警告）
        
        Returns:
            数据质量报告字典
        """
        if df.empty:
            return {
                'total_samples': 0,
                'missing_fields': {},
                'low_quality_fields': [],
                'warnings': ['数据为空']
            }
        
        if critical_fields is None:
            critical_fields = ['close_price', 'open_price', 'high_price', 'low_price', 'volume']
        
        quality_report = {
            'total_samples': len(df),
            'missing_fields': {},
            'low_quality_fields': [],
            'critical_field_issues': [],
            'warnings': []
        }
        
        # 排除标签列和元数据列
        exclude_cols = {'symbol', 'target_date', 'future_date', 
                       'label_direction', 'label_change_pct', 'label_up', 'label_up_probability'}
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # 检查每个字段的缺失率
        for col in feature_cols:
            missing_count = df[col].isna().sum()
            missing_rate = missing_count / len(df) if len(df) > 0 else 0
            completeness = 1.0 - missing_rate
            
            quality_report['missing_fields'][col] = {
                'missing_count': int(missing_count),
                'missing_rate': missing_rate,
                'completeness': completeness
            }
            
            # 检查是否低于阈值
            if completeness < min_completeness:
                quality_report['low_quality_fields'].append({
                    'field': col,
                    'completeness': completeness,
                    'missing_rate': missing_rate
                })
                quality_report['warnings'].append(
                    f"字段 {col} 完整率仅 {completeness:.2%}（缺失率 {missing_rate:.2%}），"
                    f"低于阈值 {min_completeness:.2%}"
                )
            
            # 检查关键字段
            if col in critical_fields and completeness < 0.9:
                quality_report['critical_field_issues'].append({
                    'field': col,
                    'completeness': completeness
                })
                quality_report['warnings'].append(
                    f"⚠ 关键字段 {col} 完整率仅 {completeness:.2%}，可能影响训练质量"
                )
        
        # 统计信息
        quality_report['summary'] = {
            'total_fields': len(feature_cols),
            'high_quality_fields': len([f for f in feature_cols 
                                       if quality_report['missing_fields'][f]['completeness'] >= 0.9]),
            'medium_quality_fields': len([f for f in feature_cols 
                                          if 0.5 <= quality_report['missing_fields'][f]['completeness'] < 0.9]),
            'low_quality_fields': len(quality_report['low_quality_fields']),
            'critical_issues': len(quality_report['critical_field_issues'])
        }
        
        return quality_report
    
    def split_data_by_time(self, 
                          df: pd.DataFrame,
                          train_ratio: float = 0.7,
                          val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        按时间划分数据（避免未来信息泄露）
        
        Args:
            df: 数据DataFrame（必须包含target_date列）
            train_ratio: 训练集比例
            val_ratio: 验证集比例
        
        Returns:
            (train_df, val_df, test_df)
        """
        if df.empty or 'target_date' not in df.columns:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # 按日期排序
        df['target_date'] = pd.to_datetime(df['target_date'])
        df = df.sort_values('target_date')
        
        # 计算划分点
        total = len(df)
        train_end = int(total * train_ratio)
        val_end = int(total * (train_ratio + val_ratio))
        
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()
        
        self.logger.info(f"数据划分：训练集 {len(train_df)} 条，验证集 {len(val_df)} 条，测试集 {len(test_df)} 条")
        
        return train_df, val_df, test_df
