"""
实时交易决策顾问
在开盘时间实时获取数据，预测明天走势，辅助当天买卖决策
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta, time
import sys
import os
import threading

# 添加父目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import importlib.util

# 导入依赖模块
spec = importlib.util.spec_from_file_location(
    "stock_data_source",
    os.path.join(project_root, "data_source", "stock_data_source.py")
)
stock_data_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock_data_module)
StockDataSource = stock_data_module.StockDataSource

spec = importlib.util.spec_from_file_location(
    "logger",
    os.path.join(project_root, "utils", "logger.py")
)
logger_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logger_module)
get_logger = logger_module.get_logger

spec = importlib.util.spec_from_file_location(
    "stock_predictor",
    os.path.join(project_root, "predictor", "stock_predictor.py")
)
predictor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(predictor_module)
StockPredictor = predictor_module.StockPredictor

# 尝试导入数据存储模块（用于保存实时决策快照）
DATA_STORAGE_AVAILABLE = False
DataStorage = None
try:
    ds_spec = importlib.util.spec_from_file_location(
        "data_storage",
        os.path.join(project_root, "utils", "data_storage.py")
    )
    data_storage_module = importlib.util.module_from_spec(ds_spec)
    ds_spec.loader.exec_module(data_storage_module)
    DataStorage = data_storage_module.DataStorage
    DATA_STORAGE_AVAILABLE = True
except Exception:
    DATA_STORAGE_AVAILABLE = False

logger = get_logger(__name__)


class RealtimeTradingAdvisor:
    """实时交易决策顾问"""
    
    def __init__(self):
        self.data_source = StockDataSource()
        self.predictor = StockPredictor()
        self.logger = logger
        # 数据存储（如果可用，用于记录每一次实时决策）
        if DATA_STORAGE_AVAILABLE:
            try:
                self.data_storage = DataStorage(base_dir=os.path.join(project_root, "data"))
            except Exception:
                self.data_storage = None
        else:
            self.data_storage = None
        
        # 预测结果缓存（优化：避免重复计算）
        # 格式: {symbol: {'prediction': {...}, 'timestamp': datetime, 'cache_duration': 600}}
        self._prediction_cache = {}
        self._cache_lock = threading.Lock()  # 线程安全锁
        self._default_cache_duration = 600  # 默认缓存10分钟（600秒）
        
        # 交易决策配置（从 config.py 读取，如果不可用则使用默认值）
        try:
            config_spec = importlib.util.spec_from_file_location(
                "config",
                os.path.join(project_root, "config.py")
            )
            config_module = importlib.util.module_from_spec(config_spec)
            config_spec.loader.exec_module(config_module)
            TRADING_CONFIG = getattr(config_module, 'TRADING_CONFIG', {})
        except Exception:
            TRADING_CONFIG = {}
        
        # 使用配置文件中的配置，如果不存在则使用默认值
        self.config = {
            # 买入信号阈值
            'buy_signal_threshold': TRADING_CONFIG.get('buy_signal_threshold', 0.65),
            'strong_buy_threshold': TRADING_CONFIG.get('strong_buy_threshold', 0.75),
            
            # 卖出信号阈值
            'sell_signal_threshold': TRADING_CONFIG.get('sell_signal_threshold', 0.60),
            'strong_sell_threshold': TRADING_CONFIG.get('strong_sell_threshold', 0.70),
            
            # 置信度要求
            'min_confidence': TRADING_CONFIG.get('min_confidence', 0.55),
            'high_confidence': TRADING_CONFIG.get('high_confidence', 0.70),
            
            # 资金流向权重（实时决策中的权重）
            'capital_flow_weight': TRADING_CONFIG.get('capital_flow_weight', 0.25),
            
            # 盘口分析权重
            'bid_ask_weight': TRADING_CONFIG.get('bid_ask_weight', 0.15),
            
            # 盘中涨跌调整权重
            'intraday_weight': TRADING_CONFIG.get('intraday_weight', 0.10),
            
            # 止损止盈设置
            'stop_loss_pct': TRADING_CONFIG.get('stop_loss_pct', -5.0),
            'take_profit_pct': TRADING_CONFIG.get('take_profit_pct', 8.0),
            'trailing_stop_pct': TRADING_CONFIG.get('trailing_stop_pct', 3.0),
            
            # 仓位控制
            'max_position_pct': TRADING_CONFIG.get('max_position_pct', 30.0),
            'position_step': TRADING_CONFIG.get('position_step', 10.0),
            
            # 交易成本设置
            'commission_rate': TRADING_CONFIG.get('commission_rate', 0.0003),
            'stamp_tax_rate': TRADING_CONFIG.get('stamp_tax_rate', 0.001),
            'slippage_rate': TRADING_CONFIG.get('slippage_rate', 0.001),
            'min_profit_threshold': TRADING_CONFIG.get('min_profit_threshold', 0.01),
            'enable_cost_consideration': TRADING_CONFIG.get('enable_cost_consideration', True),
        }
        
        # 尝试使用优化后的阈值（如果信号分析器可用）
        try:
            from utils.signal_analyzer import get_signal_analyzer
            signal_analyzer = get_signal_analyzer()
            threshold_config = {
                'buy_signal_threshold': self.config['buy_signal_threshold'],
                'strong_buy_threshold': self.config['strong_buy_threshold'],
                'sell_signal_threshold': self.config['sell_signal_threshold'],
                'strong_sell_threshold': self.config['strong_sell_threshold']
            }
            optimized_result = signal_analyzer.get_optimized_thresholds(threshold_config, days=30, min_samples=20)
            
            if optimized_result.get('success', False):
                optimized_thresholds = optimized_result.get('optimized_thresholds', {})
                # 使用优化后的阈值更新配置
                self.config.update(optimized_thresholds)
                adjustments = optimized_result.get('adjustments', {})
                if adjustments:
                    self.logger.info(f"已应用优化后的信号阈值（基于历史表现动态调整）")
                    for key, adj in adjustments.items():
                        self.logger.debug(f"  {key}: {adj['old']:.3f} -> {adj['new']:.3f} ({adj['reason']})")
        except Exception as e:
            self.logger.debug(f"信号阈值优化失败，使用基础配置: {str(e)}")
    
    def get_realtime_decision(self, symbol: str, holding: bool = False, 
                              cost_price: float = None, mode: str = "single") -> Dict:
        """
        获取实时交易决策
        
        Args:
            symbol: 股票代码
            holding: 是否持有该股票
            cost_price: 持仓成本价（如果持有）
            
        Returns:
            交易决策结果
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"开始实时交易决策分析: {symbol}")
        self.logger.info(f"{'='*60}")
        
        # 1. 检查交易时间
        trading_time = self.data_source.is_trading_time()
        self.logger.info(f"当前时段: {trading_time['message']}")
        
        result = {
            'symbol': symbol,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mode': mode,
            'cost_price': cost_price,
            'trading_time': trading_time,
            'success': False
        }
        
        # 2. 获取实时行情（带数据质量检查）
        self.logger.info("\n步骤1: 获取实时行情数据...")
        realtime_quote = self.data_source.get_realtime_quote(symbol)
        
        if not realtime_quote:
            result['message'] = '无法获取实时行情数据'
            return result
        
        # 数据质量验证
        try:
            from utils.data_validator import DataValidator
            validator = DataValidator()
            is_valid, msg, quality_report = validator.validate_realtime_quote(realtime_quote)
            if not is_valid:
                self.logger.warning(f"实时行情数据验证失败: {msg}")
                result['data_quality'] = {
                    'is_valid': False,
                    'message': msg,
                    'quality_score': quality_report.get('quality_score', 0.0),
                    'warnings': quality_report.get('warnings', [])
                }
            else:
                result['data_quality'] = {
                    'is_valid': True,
                    'message': msg,
                    'quality_score': quality_report.get('quality_score', 1.0),
                    'warnings': quality_report.get('warnings', [])
                }
        except Exception as e:
            self.logger.debug(f"数据验证失败（不影响主流程）: {str(e)}")
            result['data_quality'] = {'is_valid': True, 'message': '验证跳过', 'quality_score': 1.0}
        
        result['realtime_quote'] = realtime_quote
        current_price = realtime_quote.get('current_price', 0)
        change_pct = realtime_quote.get('change_pct', 0)
        
        self.logger.info(f"当前价格: {current_price}元")
        self.logger.info(f"今日涨跌幅: {change_pct:.2f}%")
        
        # 3. 执行预测分析（预测明天走势）- 使用缓存优化
        self.logger.info("\n步骤2: 执行预测分析（预测明天走势）...")
        prediction_result = self._get_cached_prediction(symbol, force_refresh=False)
        
        if not prediction_result or not prediction_result.get('success', False):
            result['message'] = '预测分析失败'
            return result
        
        result['prediction'] = {
            'direction': prediction_result['prediction'],
            'up_probability': prediction_result['up_probability'],
            'down_probability': prediction_result['down_probability'],
            'confidence': prediction_result['confidence'],
            'target_date': prediction_result.get('target_date', '明天')
        }
        
        self.logger.info(f"预测方向: {prediction_result['prediction']}")
        self.logger.info(f"上涨概率: {prediction_result['up_probability']:.1%}")
        self.logger.info(f"下跌概率: {prediction_result['down_probability']:.1%}")
        self.logger.info(f"置信度: {prediction_result['confidence']:.1%}")
        
        # 4. 获取实时资金流向
        self.logger.info("\n步骤3: 分析实时资金流向...")
        capital_flow = self.data_source.get_realtime_capital_flow(symbol)
        result['capital_flow'] = capital_flow
        
        if capital_flow:
            self.logger.info(f"资金流向趋势: {capital_flow.get('flow_trend', '未知')}")
            main_inflow = capital_flow.get('main_net_inflow', 0)
            self.logger.info(f"主力净流入: {main_inflow/10000:.2f}万元" if main_inflow else "主力净流入: 数据不可用")
        
        # 5. 分析买卖盘
        self.logger.info("\n步骤4: 分析买卖盘...")
        bid_ask = self.data_source.get_bid_ask_data(symbol)
        result['bid_ask'] = bid_ask
        
        bid_ask_score = self._analyze_bid_ask(bid_ask)
        self.logger.info(f"买卖盘强度得分: {bid_ask_score:.2f}")
        
        # 6. 综合计算交易信号
        self.logger.info("\n步骤5: 综合计算交易信号...")
        
        # 基础预测得分
        base_score = prediction_result['up_probability'] - 0.5  # 范围 -0.5 到 0.5
        
        # 实时资金流向调整（带数据完整性检查）
        capital_adjustment = 0
        capital_flow_quality = 1.0  # 数据质量评分（0-1）
        if capital_flow:
            total_inflow = capital_flow.get('total_net_inflow', 0)
            # 检查数据完整性
            if total_inflow is None:
                capital_flow_quality = 0.0  # 数据缺失
                self.logger.debug("资金流向数据缺失，降低资金流向权重")
            elif abs(total_inflow) < 1000:  # 数据过小，可能不准确
                capital_flow_quality = 0.5
                self.logger.debug("资金流向数据过小，可能不准确")
            
            if total_inflow and total_inflow is not None:
                if total_inflow > 0:
                    capital_adjustment = min(total_inflow / 100000000, 0.1)  # 最多+0.1
                elif total_inflow < 0:
                    capital_adjustment = max(total_inflow / 100000000, -0.1)  # 最多-0.1
        else:
            capital_flow_quality = 0.0  # 数据完全缺失
            self.logger.debug("资金流向数据不可用")
        
        # 买卖盘调整（带数据完整性检查）
        bid_ask_adjustment = 0
        bid_ask_quality = 1.0  # 数据质量评分（0-1）
        if bid_ask is not None and bid_ask_score is not None:
            bid_ask_adjustment = bid_ask_score * 0.05  # 范围 -0.05 到 0.05
            # 检查买卖盘数据完整性
            if not bid_ask or len(bid_ask.get('bids', [])) == 0 or len(bid_ask.get('asks', [])) == 0:
                bid_ask_quality = 0.3  # 数据不完整
                self.logger.debug("买卖盘数据不完整，降低买卖盘权重")
        else:
            bid_ask_quality = 0.0  # 数据完全缺失
            self.logger.debug("买卖盘数据不可用")
        
        # 今日涨跌幅调整（追涨杀跌风险控制）
        intraday_adjustment = 0
        if change_pct > 5:
            intraday_adjustment = -0.05  # 已涨太多，降低买入意愿
        elif change_pct < -5:
            intraday_adjustment = 0.05   # 已跌太多，可能有反弹机会
        
        # 获取基础权重配置
        base_capital_flow_weight = self.config.get('capital_flow_weight', 0.25)
        base_bid_ask_weight = self.config.get('bid_ask_weight', 0.15)
        base_intraday_weight = self.config.get('intraday_weight', 0.10)
        
        # 根据市场状态动态调整权重
        market_state_info = prediction_result.get('market_state', {})
        market_state = market_state_info.get('state', 'sideways')  # 默认震荡市
        
        capital_flow_weight, bid_ask_weight, intraday_weight = self._adjust_weights_by_market_state(
            market_state,
            base_capital_flow_weight,
            base_bid_ask_weight,
            base_intraday_weight
        )
        
        # 根据数据质量调整权重（数据质量低时降低权重，提高预测权重）
        if capital_flow_quality < 1.0:
            # 数据质量低时，降低资金流向权重，提高预测权重
            weight_reduction = (1.0 - capital_flow_quality) * 0.5  # 最多降低50%
            capital_flow_weight = capital_flow_weight * (1.0 - weight_reduction)
            self.logger.debug(f"资金流向数据质量{capital_flow_quality:.2f}，权重调整为{capital_flow_weight:.3f}")
        
        if bid_ask_quality < 1.0:
            # 数据质量低时，降低买卖盘权重，提高预测权重
            weight_reduction = (1.0 - bid_ask_quality) * 0.5  # 最多降低50%
            bid_ask_weight = bid_ask_weight * (1.0 - weight_reduction)
            self.logger.debug(f"买卖盘数据质量{bid_ask_quality:.2f}，权重调整为{bid_ask_weight:.3f}")
        
        # 预测权重 = 1 - 其他权重之和（确保权重总和为1）
        prediction_weight = 1.0 - capital_flow_weight - bid_ask_weight - intraday_weight
        
        final_signal_score = (
            base_score * prediction_weight +           # 预测权重（动态计算）
            capital_adjustment * capital_flow_weight + # 资金流向权重
            bid_ask_adjustment * bid_ask_weight +      # 买卖盘权重
            intraday_adjustment * intraday_weight      # 盘中调整权重
        )
        
        # 转换为信号强度（0-1）
        signal_strength = 0.5 + final_signal_score
        signal_strength = max(0, min(1, signal_strength))
        
        self.logger.info(f"综合信号强度: {signal_strength:.2f}")
        
        # 生成信号强度评分说明（如果信号分析器可用）
        signal_explanation = None
        try:
            from utils.signal_analyzer import get_signal_analyzer
            signal_analyzer = get_signal_analyzer()
            signal_explanation = signal_analyzer.generate_signal_explanation(
                signal_strength=signal_strength,
                final_score=final_signal_score,
                factor_scores={
                    'prediction': base_score,
                    'capital_flow': capital_adjustment,
                    'bid_ask': bid_ask_adjustment,
                    'intraday': intraday_adjustment
                },
                weights={
                    'prediction_weight': prediction_weight,
                    'capital_flow_weight': capital_flow_weight,
                    'bid_ask_weight': bid_ask_weight,
                    'intraday_weight': intraday_weight
                }
            )
            result['signal_explanation'] = signal_explanation
            self.logger.debug(f"信号评分说明已生成")
        except Exception as e:
            self.logger.debug(f"生成信号评分说明失败（不影响主流程）: {str(e)}")
        
        # 7. 涨跌停板策略分析（如果接近或已涨跌停）
        limit_up_price = realtime_quote.get('limit_up', 0)
        limit_down_price = realtime_quote.get('limit_down', 0)
        current_price = realtime_quote.get('current_price', 0)
        
        # 获取新闻得分（用于判断是否有重大利好/利空）
        news_score = None
        try:
            news_result = self.predictor.calculate_news_score(symbol)
            if news_result:
                news_score = {
                    'sentiment': news_result.get('sentiment', 'neutral'),
                    'sentiment_score': news_result.get('sentiment_score', 0)
                }
        except Exception as e:
            self.logger.debug(f"获取新闻得分失败: {str(e)}")
        
        # 涨停板策略
        limit_up_strategy = None
        if limit_up_price > 0 and current_price > 0:
            limit_up_strategy = self.calculate_limit_up_strategy(
                symbol, current_price, limit_up_price, bid_ask, news_score
            )
            result['limit_up_strategy'] = limit_up_strategy
            if limit_up_strategy.get('available'):
                self.logger.info(f"涨停板策略: {limit_up_strategy.get('reason', '')}")
        
        # 跌停板策略
        limit_down_strategy = None
        if limit_down_price > 0 and current_price > 0:
            limit_down_strategy = self.calculate_limit_down_strategy(
                symbol, current_price, limit_down_price, news_score
            )
            result['limit_down_strategy'] = limit_down_strategy
            if limit_down_strategy.get('available'):
                self.logger.info(f"跌停板策略: {limit_down_strategy.get('reason', '')}")
        
        # 7.1 T+1制度优化：持仓周期优化（如果未持仓，评估是否应该买入）
        holding_period_optimization = None
        if not holding:
            holding_period_optimization = self.optimize_holding_period(symbol, prediction_result)
            result['holding_period_optimization'] = holding_period_optimization
            if holding_period_optimization.get('should_buy'):
                self.logger.info(f"持仓周期优化: {holding_period_optimization.get('reason', '')}")
            else:
                self.logger.info(f"持仓周期优化: {holding_period_optimization.get('reason', '')}")
        
        # 7.2 集合竞价策略（如果在集合竞价时段）
        auction_strategy = None
        trading_time_info = trading_time
        if trading_time_info and trading_time_info.get('session') == 'pre_open':
            auction_data = self.data_source.get_auction_data(symbol)
            auction_strategy = self.calculate_auction_strategy(symbol, prediction_result, auction_data)
            result['auction_strategy'] = auction_strategy
            if auction_strategy.get('available'):
                if auction_strategy.get('should_participate'):
                    self.logger.info(f"集合竞价策略: {auction_strategy.get('reason', '')}")
                else:
                    self.logger.info(f"集合竞价策略: {auction_strategy.get('reason', '')}")
        
        # 8. 生成交易决策
        self.logger.info("\n步骤8: 生成交易决策...")
        
        decision = self._make_trading_decision(
            symbol=symbol,
            signal_strength=signal_strength,
            prediction_result=prediction_result,
            realtime_quote=realtime_quote,
            capital_flow=capital_flow,
            holding=holding,
            cost_price=cost_price,
            trading_time=trading_time,
            limit_up_strategy=limit_up_strategy,
            limit_down_strategy=limit_down_strategy,
            holding_period_optimization=holding_period_optimization,
            auction_strategy=auction_strategy
        )
        
        # 7.3 龙虎榜数据分析（如果可用）
        dragon_tiger_analysis = None
        try:
            dragon_tiger_analysis = self.analyze_dragon_tiger_list(symbol)
            result['dragon_tiger_analysis'] = dragon_tiger_analysis
            if dragon_tiger_analysis.get('available'):
                self.logger.info(f"龙虎榜分析: {dragon_tiger_analysis.get('suggestion', '')}")
        except Exception as e:
            self.logger.debug(f"龙虎榜分析失败（不影响主流程）: {str(e)}")
            dragon_tiger_analysis = None
        
        # 8. 生成交易决策
        self.logger.info("\n步骤8: 生成交易决策...")
        
        decision = self._make_trading_decision(
            symbol=symbol,
            signal_strength=signal_strength,
            prediction_result=prediction_result,
            realtime_quote=realtime_quote,
            capital_flow=capital_flow,
            holding=holding,
            cost_price=cost_price,
            trading_time=trading_time,
            limit_up_strategy=limit_up_strategy,
            limit_down_strategy=limit_down_strategy,
            holding_period_optimization=holding_period_optimization,
            auction_strategy=auction_strategy,
            dragon_tiger_analysis=dragon_tiger_analysis
        )
        
        # 7.4 限售股解禁追踪
        restricted_shares_info = None
        try:
            restricted_shares_info = self.track_restricted_shares(symbol)
            result['restricted_shares_info'] = restricted_shares_info
            if restricted_shares_info.get('has_restricted'):
                self.logger.info(f"限售股解禁: {restricted_shares_info.get('warning', '')}")
        except Exception as e:
            self.logger.debug(f"限售股解禁追踪失败（不影响主流程）: {str(e)}")
            restricted_shares_info = None
        
        # 8. 生成交易决策
        self.logger.info("\n步骤8: 生成交易决策...")
        
        decision = self._make_trading_decision(
            symbol=symbol,
            signal_strength=signal_strength,
            prediction_result=prediction_result,
            realtime_quote=realtime_quote,
            capital_flow=capital_flow,
            holding=holding,
            cost_price=cost_price,
            trading_time=trading_time,
            limit_up_strategy=limit_up_strategy,
            limit_down_strategy=limit_down_strategy,
            holding_period_optimization=holding_period_optimization,
            auction_strategy=auction_strategy,
            dragon_tiger_analysis=dragon_tiger_analysis,
            restricted_shares_info=restricted_shares_info
        )
        
        # 8.1 停牌检测和ST股票检查
        suspension_info = self.data_source.check_suspension(symbol)
        st_info = self.data_source.check_st_stock(symbol)
        result['suspension_info'] = suspension_info
        result['st_info'] = st_info
        
        # 整合龙虎榜分析到决策中（已在_make_trading_decision中处理，这里保留用于兼容）
        if dragon_tiger_analysis and dragon_tiger_analysis.get('available'):
            decision['dragon_tiger'] = dragon_tiger_analysis
        
        # 如果停牌，调整决策
        if suspension_info.get('is_suspended', False):
            decision['action'] = 'AVOID'
            decision['action_cn'] = '停牌，无法交易'
            decision['strength'] = 'STRONG'
            decision['strength_cn'] = '强烈'
            decision['reasons'].append(f"停牌原因: {suspension_info.get('reason', '未知')}")
            decision['risk_warnings'].append(suspension_info.get('message', '股票停牌，无法交易'))
        
        # 如果是ST股票，调整策略
        if st_info.get('is_st', False):
            decision['st_warning'] = st_info.get('warning', '')
            decision['risk_warnings'].append(st_info.get('warning', ''))
            # 调整仓位建议
            if decision.get('position_advice'):
                # 降低仓位建议
                decision['position_advice'] = f"ST股票风险高，建议仓位: {st_info.get('strategy', {}).get('max_position_pct', 10)}%"
            # 调整止损止盈
            if st_info.get('strategy'):
                st_strategy = st_info.get('strategy', {})
                decision['st_strategy'] = st_strategy
                # 如果决策中有止损止盈建议，根据ST策略调整
                if 'price_suggestions' in decision:
                    if 'stop_loss' in decision['price_suggestions']:
                        # 调整止损价（更严格）
                        decision['price_suggestions']['stop_loss'] = round(
                            current_price * (1 + st_strategy.get('stop_loss_pct', -3.0) / 100), 2
                        )
        
        result['decision'] = decision
        result['signal_strength'] = signal_strength
        result['success'] = True
        
        # 9. 输出决策结果
        self._print_decision_summary(result)
        
        # 9. 保存实时决策快照到CSV，供后续模型学习使用
        try:
            if self.data_storage:
                self.data_storage.save_realtime_trading_decision(result, timestamp=datetime.now())
        except Exception as e:
            self.logger.debug(f"保存实时交易决策数据失败（不影响主流程）: {str(e)}")
        
        return result
    
    def _get_cached_prediction(self, symbol: str, force_refresh: bool = False, 
                                cache_duration: int = None) -> Optional[Dict]:
        """
        获取缓存的预测结果，如果缓存不存在或已过期，则执行新的预测
        
        Args:
            symbol: 股票代码
            force_refresh: 是否强制刷新（忽略缓存）
            cache_duration: 缓存时长（秒），默认使用 self._default_cache_duration
        
        Returns:
            预测结果字典，如果失败返回None
        """
        if cache_duration is None:
            cache_duration = self._default_cache_duration
        
        with self._cache_lock:
            # 检查缓存是否存在且未过期
            if not force_refresh and symbol in self._prediction_cache:
                cached_data = self._prediction_cache[symbol]
                cache_time = cached_data.get('timestamp')
                cache_dur = cached_data.get('cache_duration', cache_duration)
                
                if cache_time:
                    age_seconds = (datetime.now() - cache_time).total_seconds()
                    if age_seconds < cache_dur:
                        # 缓存有效，返回缓存结果
                        self.logger.debug(f"使用缓存的预测结果（缓存年龄: {age_seconds:.1f}秒）")
                        return cached_data.get('prediction')
                    else:
                        # 缓存过期，删除
                        self.logger.debug(f"缓存已过期（年龄: {age_seconds:.1f}秒），重新预测")
                        del self._prediction_cache[symbol]
            
            # 执行新的预测
            try:
                self.logger.info(f"执行新的预测分析: {symbol}")
                prediction_result = self.predictor.predict(symbol)
                
                if prediction_result and prediction_result.get('success', False):
                    # 保存到缓存
                    self._prediction_cache[symbol] = {
                        'prediction': prediction_result,
                        'timestamp': datetime.now(),
                        'cache_duration': cache_duration
                    }
                    self.logger.info(f"预测结果已缓存（缓存时长: {cache_duration}秒）")
                    return prediction_result
                else:
                    self.logger.warning(f"预测失败: {symbol}")
                    return None
            except Exception as e:
                self.logger.error(f"执行预测时发生异常: {str(e)}")
                return None
    
    def clear_prediction_cache(self, symbol: str = None):
        """
        清除预测缓存
        
        Args:
            symbol: 股票代码，如果为None则清除所有缓存
        """
        with self._cache_lock:
            if symbol:
                if symbol in self._prediction_cache:
                    del self._prediction_cache[symbol]
                    self.logger.info(f"已清除 {symbol} 的预测缓存")
            else:
                self._prediction_cache.clear()
                self.logger.info("已清除所有预测缓存")
    
    def _adjust_weights_by_market_state(self, market_state: str,
                                        base_capital_flow_weight: float,
                                        base_bid_ask_weight: float,
                                        base_intraday_weight: float) -> tuple:
        """
        根据市场状态动态调整权重
        
        Args:
            market_state: 市场状态（'bull_market'/'bear_market'/'sideways'）
            base_capital_flow_weight: 基础资金流向权重
            base_bid_ask_weight: 基础买卖盘权重
            base_intraday_weight: 基础盘中调整权重
            
        Returns:
            (调整后的资金流向权重, 调整后的买卖盘权重, 调整后的盘中调整权重)
        """
        if market_state == 'bull_market':
            # 牛市：提高预测权重，降低盘中调整权重
            # 预测权重提高 -> 其他权重相对降低
            capital_flow_weight = base_capital_flow_weight * 0.9  # 降低10%
            bid_ask_weight = base_bid_ask_weight * 0.9  # 降低10%
            intraday_weight = base_intraday_weight * 0.8  # 降低20%
            
            self.logger.debug(f"牛市权重调整: 资金流向={capital_flow_weight:.2f}, "
                            f"买卖盘={bid_ask_weight:.2f}, 盘中={intraday_weight:.2f}")
        
        elif market_state == 'bear_market':
            # 熊市：提高资金流向权重，降低预测权重
            # 资金流向权重提高 -> 其他权重相对降低
            capital_flow_weight = base_capital_flow_weight * 1.2  # 提高20%
            bid_ask_weight = base_bid_ask_weight * 1.1  # 提高10%
            intraday_weight = base_intraday_weight * 1.1  # 提高10%
            
            # 确保权重不超过合理范围
            capital_flow_weight = min(capital_flow_weight, 0.4)
            bid_ask_weight = min(bid_ask_weight, 0.25)
            intraday_weight = min(intraday_weight, 0.15)
            
            self.logger.debug(f"熊市权重调整: 资金流向={capital_flow_weight:.2f}, "
                            f"买卖盘={bid_ask_weight:.2f}, 盘中={intraday_weight:.2f}")
        
        else:
            # 震荡市：使用默认权重
            capital_flow_weight = base_capital_flow_weight
            bid_ask_weight = base_bid_ask_weight
            intraday_weight = base_intraday_weight
        
        return capital_flow_weight, bid_ask_weight, intraday_weight
    
    def _analyze_bid_ask(self, bid_ask: Dict) -> float:
        """
        分析买卖盘，返回强度得分
        
        Returns:
            得分范围 -1 到 1，正数表示买盘强，负数表示卖盘强
        """
        if not bid_ask:
            return 0
        
        bids = bid_ask.get('bids', [])
        asks = bid_ask.get('asks', [])
        
        if not bids or not asks:
            return 0
        
        # 计算买盘总量
        bid_volume = sum(b.get('volume', 0) for b in bids)
        # 计算卖盘总量
        ask_volume = sum(a.get('volume', 0) for a in asks)
        
        if bid_volume + ask_volume == 0:
            return 0
        
        # 买卖比
        ratio = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        
        return ratio
    
    def calculate_limit_up_strategy(self, symbol: str, current_price: float, 
                                   limit_up_price: float, bid_ask: Dict = None,
                                   news_score: Dict = None) -> Dict:
        """
        涨停板交易策略
        - 如果接近涨停（距离涨停<1%），判断是否追涨
        - 如果已涨停，判断是否排队买入
        - 考虑封板强度（封单量/流通市值）
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            limit_up_price: 涨停价
            bid_ask: 买卖盘数据（可选）
            news_score: 新闻得分（可选，用于判断是否有重大利好消息）
        
        Returns:
            涨停板策略字典
        """
        try:
            if limit_up_price <= 0 or current_price <= 0:
                return {
                    'available': False,
                    'reason': '价格数据无效'
                }
            
            distance_to_limit = (limit_up_price - current_price) / limit_up_price * 100
            
            strategy = {
                'available': True,
                'distance_to_limit': round(distance_to_limit, 2),  # 距离涨停的百分比
                'is_limit_up': current_price >= limit_up_price * 0.999,  # 是否已涨停
                'is_near_limit': distance_to_limit < 1.0,  # 是否接近涨停（<1%）
                'can_chase': False,  # 是否追涨
                'can_queue': False,  # 是否排队
                'risk_level': 'high',  # 风险等级：low/medium/high
                'seal_strength': 0.0,  # 封板强度（0-1）
                'reason': '',
                'suggestion': ''
            }
            
            # 获取封板强度
            limit_up_volume = 0
            if bid_ask:
                # 从买卖盘数据中获取涨停封单量（通常是买一档的量）
                bids = bid_ask.get('bids', [])
                if bids and len(bids) > 0:
                    # 买一档的价格如果是涨停价，则其量就是封单量
                    bid1 = bids[0]
                    bid1_price = bid1.get('price', 0)
                    if abs(bid1_price - limit_up_price) < 0.01:  # 价格接近涨停价
                        limit_up_volume = bid1.get('volume', 0)
            
            # 获取流通市值（用于计算封板强度）
            try:
                stock_info = self.data_source.get_stock_info(symbol)
                float_market_cap = stock_info.get('float_value', 0)  # 流通市值
                if float_market_cap <= 0:
                    # 如果获取不到流通市值，尝试用总市值
                    float_market_cap = stock_info.get('total_value', 0)
                
                if float_market_cap > 0:
                    # 封板强度 = 封单量 / 流通市值
                    strategy['seal_strength'] = limit_up_volume / float_market_cap
                else:
                    # 如果获取不到市值，使用封单量本身作为参考
                    strategy['seal_strength'] = 0.0 if limit_up_volume < 1000000 else 0.05  # 封单量>100万手，认为有一定强度
            except Exception as e:
                self.logger.debug(f"获取股票信息失败: {str(e)}")
                strategy['seal_strength'] = 0.0
            
            # 判断是否有重大利好消息
            has_good_news = False
            if news_score:
                sentiment = news_score.get('sentiment', 'neutral')
                sentiment_score = news_score.get('sentiment_score', 0)
                if sentiment == 'positive' and sentiment_score > 0.5:
                    has_good_news = True
            
            # 策略判断
            if strategy['is_limit_up']:
                # 已涨停
                if strategy['seal_strength'] > 0.1:  # 封板强度>10%
                    strategy['can_queue'] = True
                    strategy['risk_level'] = 'medium'
                    strategy['reason'] = '封板强度高，可考虑排队买入'
                    strategy['suggestion'] = '涨停封单量大，封板强度高，可考虑排队买入，但需注意开板风险'
                elif strategy['seal_strength'] > 0.05:  # 封板强度5%-10%
                    strategy['can_queue'] = True
                    strategy['risk_level'] = 'medium'
                    strategy['reason'] = '封板强度中等，可谨慎排队'
                    strategy['suggestion'] = '封板强度中等，可谨慎排队，但需密切关注开板情况'
                else:
                    strategy['risk_level'] = 'high'
                    strategy['reason'] = '封板强度低，可能开板，不建议排队'
                    strategy['suggestion'] = '封板强度低，可能随时开板，不建议排队买入'
            
            elif strategy['is_near_limit']:
                # 接近涨停（<1%）
                if strategy['seal_strength'] > 0.05 and has_good_news:
                    strategy['can_chase'] = True
                    strategy['risk_level'] = 'medium'
                    strategy['reason'] = '接近涨停且封板强度高，有利好消息，可考虑追涨'
                    strategy['suggestion'] = '接近涨停，封板强度高且有利好消息，可考虑追涨，但需控制仓位'
                elif strategy['seal_strength'] > 0.05:
                    strategy['can_chase'] = True
                    strategy['risk_level'] = 'medium'
                    strategy['reason'] = '接近涨停且封板强度高，可考虑追涨'
                    strategy['suggestion'] = '接近涨停，封板强度高，可考虑追涨，但需注意风险'
                else:
                    strategy['risk_level'] = 'high'
                    strategy['reason'] = '接近涨停但封板强度低，追涨风险高'
                    strategy['suggestion'] = '接近涨停但封板强度低，追涨风险高，不建议追涨'
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"计算涨停板策略失败: {str(e)}")
            return {
                'available': False,
                'reason': f'计算失败: {str(e)}'
            }
    
    def calculate_limit_down_strategy(self, symbol: str, current_price: float,
                                     limit_down_price: float, news_score: Dict = None) -> Dict:
        """
        跌停板抄底策略
        - 如果接近跌停，判断是否抄底
        - 考虑跌停原因（是否有利空消息）
        - 考虑市场整体情况
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            limit_down_price: 跌停价
            news_score: 新闻得分（可选，用于判断是否有重大利空消息）
        
        Returns:
            跌停板策略字典
        """
        try:
            if limit_down_price <= 0 or current_price <= 0:
                return {
                    'available': False,
                    'reason': '价格数据无效'
                }
            
            distance_to_limit = (current_price - limit_down_price) / limit_down_price * 100
            
            strategy = {
                'available': True,
                'distance_to_limit': round(distance_to_limit, 2),  # 距离跌停的百分比
                'is_limit_down': current_price <= limit_down_price * 1.001,  # 是否已跌停
                'is_near_limit': distance_to_limit < 1.0,  # 是否接近跌停（<1%）
                'can_buy': False,  # 是否抄底
                'risk_level': 'high',  # 风险等级
                'has_negative_news': False,  # 是否有重大利空
                'reason': '',
                'suggestion': ''
            }
            
            # 检查是否有重大利空
            if news_score:
                sentiment = news_score.get('sentiment', 'neutral')
                sentiment_score = news_score.get('sentiment_score', 0)
                if sentiment == 'negative' and sentiment_score < -0.5:
                    strategy['has_negative_news'] = True
            
            # 策略判断
            if strategy['is_limit_down']:
                # 已跌停
                if strategy['has_negative_news']:
                    strategy['risk_level'] = 'high'
                    strategy['reason'] = '已跌停且存在重大利空，不建议抄底'
                    strategy['suggestion'] = '已跌停且存在重大利空消息，不建议抄底，风险极高'
                else:
                    strategy['can_buy'] = True
                    strategy['risk_level'] = 'medium'
                    strategy['reason'] = '已跌停但无重大利空，可能是情绪性下跌，可考虑抄底'
                    strategy['suggestion'] = '已跌停但无重大利空，可能是情绪性下跌，可考虑小仓位抄底，但需谨慎'
            
            elif strategy['is_near_limit']:
                # 接近跌停（<1%）
                if strategy['has_negative_news']:
                    strategy['risk_level'] = 'high'
                    strategy['reason'] = '接近跌停且存在重大利空，不建议抄底'
                    strategy['suggestion'] = '接近跌停且存在重大利空，不建议抄底，可能继续下跌'
                else:
                    strategy['can_buy'] = True
                    strategy['risk_level'] = 'medium'
                    strategy['reason'] = '接近跌停但无重大利空，可能是情绪性下跌，可考虑抄底'
                    strategy['suggestion'] = '接近跌停但无重大利空，可能是情绪性下跌，可考虑小仓位抄底'
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"计算跌停板策略失败: {str(e)}")
            return {
                'available': False,
                'reason': f'计算失败: {str(e)}'
            }
    
    def analyze_dragon_tiger_list(self, symbol: str) -> Dict:
        """
        分析龙虎榜数据
        - 机构席位买入/卖出
        - 游资席位买入/卖出
        - 对短期走势的影响
        
        Args:
            symbol: 股票代码
        
        Returns:
            龙虎榜分析结果字典
        """
        try:
            # 获取龙虎榜数据
            dragon_tiger_data = self.data_source.get_dragon_tiger_list(symbol, days=5)
            
            if not dragon_tiger_data:
                return {
                    'available': False,
                    'reason': '无龙虎榜数据'
                }
            
            # 机构席位
            institution_buy = dragon_tiger_data.get('institution_buy', 0)
            institution_sell = dragon_tiger_data.get('institution_sell', 0)
            institution_net = dragon_tiger_data.get('institution_net', 0)
            
            # 游资席位
            hot_money_buy = dragon_tiger_data.get('hot_money_buy', 0)
            hot_money_sell = dragon_tiger_data.get('hot_money_sell', 0)
            hot_money_net = dragon_tiger_data.get('hot_money_net', 0)
            
            # 总净流入
            total_net = dragon_tiger_data.get('total_net', 0)
            
            # 分析得分（-1到1，正数表示看涨，负数表示看跌）
            score = 0.0
            
            # 机构净买入/卖出影响（权重0.4）
            if institution_net > 0:
                # 机构净买入，看涨信号
                institution_score = min(institution_net / 100000000, 0.4)  # 每1亿净买入，增加0.1分，最多0.4分
                score += institution_score
            elif institution_net < 0:
                # 机构净卖出，看跌信号
                institution_score = max(institution_net / 100000000, -0.4)  # 每1亿净卖出，减少0.1分，最多-0.4分
                score += institution_score
            
            # 游资净买入/卖出影响（权重0.3）
            if hot_money_net > 0:
                # 游资净买入，短期看涨但波动可能加大
                hot_money_score = min(hot_money_net / 50000000, 0.3)  # 每5000万净买入，增加0.1分，最多0.3分
                score += hot_money_score * 0.8  # 游资影响权重稍低（0.8）
            elif hot_money_net < 0:
                # 游资净卖出，短期看跌
                hot_money_score = max(hot_money_net / 50000000, -0.3)  # 每5000万净卖出，减少0.1分，最多-0.3分
                score += hot_money_score * 0.8
            
            # 总净流入影响（权重0.3）
            if total_net > 0:
                total_score = min(total_net / 200000000, 0.3)  # 每2亿净流入，增加0.1分，最多0.3分
                score += total_score
            elif total_net < 0:
                total_score = max(total_net / 200000000, -0.3)  # 每2亿净流出，减少0.1分，最多-0.3分
                score += total_score
            
            # 限制得分范围
            score = max(-1.0, min(1.0, score))
            
            # 判断影响方向
            if score > 0.3:
                impact = 'positive'
                suggestion = f"机构净买入{institution_net/10000:.0f}万元，游资净买入{hot_money_net/10000:.0f}万元，短期看涨"
            elif score < -0.3:
                impact = 'negative'
                suggestion = f"机构净卖出{abs(institution_net)/10000:.0f}万元，游资净卖出{abs(hot_money_net)/10000:.0f}万元，短期看跌"
            else:
                impact = 'neutral'
                suggestion = f"机构净流入{institution_net/10000:.0f}万元，游资净流入{hot_money_net/10000:.0f}万元，影响中性"
            
            return {
                'available': True,
                'institution_buy': institution_buy,
                'institution_sell': institution_sell,
                'institution_net': institution_net,
                'hot_money_buy': hot_money_buy,
                'hot_money_sell': hot_money_sell,
                'hot_money_net': hot_money_net,
                'total_net': total_net,
                'score': score,
                'impact': impact,
                'suggestion': suggestion,
                'date': dragon_tiger_data.get('date', '')
            }
            
        except Exception as e:
            self.logger.error(f"分析龙虎榜数据失败: {str(e)}")
            return {
                'available': False,
                'reason': f'分析失败: {str(e)}'
            }
    
    def optimize_holding_period(self, symbol: str, prediction_result: Dict) -> Dict:
        """
        优化持仓周期（考虑T+1）
        - 如果预测明天上涨，今天买入，明天才能卖出
        - 考虑资金占用成本
        - 考虑机会成本
        
        Args:
            symbol: 股票代码
            prediction_result: 预测结果
        
        Returns:
            持仓周期优化结果字典
        """
        try:
            # 资金占用成本（假设年化利率5%）
            daily_cost_rate = 0.05 / 365  # 日利率
            
            # 预测收益
            predicted_change_pct = prediction_result.get('predicted_change_pct', 0) or 0
            predicted_return = predicted_change_pct / 100 if predicted_change_pct else 0
            
            # 当前价格（用于计算成本）
            current_price = prediction_result.get('current_price', 0) or 0
            
            # 计算资金占用成本（假设买入1股）
            capital_cost = current_price * daily_cost_rate if current_price > 0 else 0
            
            # 计算机会成本（假设平均市场收益为年化8%）
            market_daily_return = 0.08 / 365
            opportunity_cost = current_price * market_daily_return if current_price > 0 else 0
            
            # 计算预期收益（假设买入1股）
            expected_return = current_price * predicted_return if current_price > 0 else 0
            
            # 净收益 = 预期收益 - 资金占用成本 - 机会成本
            net_benefit = expected_return - capital_cost - opportunity_cost
            net_return = net_benefit / current_price if current_price > 0 else 0
            
            # 如果净收益<0.5%，不建议买入（考虑交易成本）
            min_return = 0.005  # 0.5%
            
            strategy = {
                'available': True,
                'should_buy': net_return > min_return,
                'capital_cost': round(capital_cost, 4),
                'opportunity_cost': round(opportunity_cost, 4),
                'net_benefit': round(net_benefit, 4),
                'net_return': round(net_return * 100, 2),  # 转换为百分比
                'holding_days': 1,  # T+1，至少持有1天
                'predicted_return': round(predicted_return * 100, 2),
                'reason': '',
                'suggestion': ''
            }
            
            if net_return > min_return:
                strategy['reason'] = f'净收益{net_return*100:.2f}%，建议买入'
                strategy['suggestion'] = f'T+1制度下，预测收益{predicted_return*100:.2f}%，净收益{net_return*100:.2f}%，建议买入并持有至少1天'
            else:
                strategy['reason'] = f'净收益{net_return*100:.2f}%，低于最低要求{min_return*100:.2f}%'
                strategy['suggestion'] = f'T+1制度下，预测收益{predicted_return*100:.2f}%，净收益{net_return*100:.2f}%，考虑交易成本，不建议买入'
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"优化持仓周期失败: {str(e)}")
            return {
                'available': False,
                'reason': f'计算失败: {str(e)}'
            }
    
    def calculate_auction_strategy(self, symbol: str, prediction_result: Dict, auction_data: Dict = None) -> Dict:
        """
        集合竞价策略（9:15-9:25）
        - 根据预测结果决定是否参与集合竞价
        - 确定集合竞价价格
        - 考虑集合竞价成交量
        
        Args:
            symbol: 股票代码
            prediction_result: 预测结果
            auction_data: 集合竞价数据（可选）
        
        Returns:
            集合竞价策略结果字典
        """
        try:
            if not auction_data:
                auction_data = self.data_source.get_auction_data(symbol)
            
            if not auction_data:
                return {
                    'available': False,
                    'reason': '无法获取集合竞价数据'
                }
            
            auction_price = auction_data.get('auction_price', 0) or auction_data.get('current_price', 0)
            auction_volume = auction_data.get('auction_volume', 0) or 0
            current_price = auction_data.get('current_price', 0) or prediction_result.get('current_price', 0) or 0
            
            # 预测方向
            prediction_direction = prediction_result.get('prediction', '震荡')
            up_prob = prediction_result.get('up_probability', 0.5) or 0.5
            confidence = prediction_result.get('confidence', 0.5) or 0.5
            
            strategy = {
                'available': True,
                'should_participate': False,
                'auction_price': round(auction_price, 2) if auction_price else 0,
                'current_price': round(current_price, 2) if current_price else 0,
                'auction_volume': auction_volume,
                'reason': '',
                'suggestion': ''
            }
            
            if not auction_price or auction_price <= 0:
                strategy['reason'] = '集合竞价价格无效'
                strategy['suggestion'] = '无法获取有效的集合竞价价格，建议观察后再决定'
                return strategy
            
            if not current_price or current_price <= 0:
                strategy['reason'] = '当前价格无效'
                strategy['suggestion'] = '无法获取有效的当前价格，建议观察后再决定'
                return strategy
            
            # 判断是否参与集合竞价
            price_diff_pct = (auction_price - current_price) / current_price * 100 if current_price > 0 else 0
            
            if prediction_direction == '上涨' and up_prob > 0.65 and confidence > 0.6:
                # 看涨，且集合竞价价格合理
                if price_diff_pct <= 2.0:  # 不超过当前价2%
                    strategy['should_participate'] = True
                    strategy['reason'] = '预测上涨，集合竞价价格合理，建议参与'
                    strategy['suggestion'] = f'预测上涨（上涨概率{up_prob*100:.1f}%，置信度{confidence*100:.1f}%），集合竞价价格{auction_price:.2f}元（相对当前价{price_diff_pct:+.2f}%），建议参与集合竞价'
                else:
                    strategy['reason'] = '预测上涨，但集合竞价价格过高'
                    strategy['suggestion'] = f'预测上涨，但集合竞价价格{auction_price:.2f}元相对当前价{price_diff_pct:+.2f}%过高，建议观察开盘后再决定'
            elif prediction_direction == '下跌' and up_prob < 0.35:
                # 看跌，不参与集合竞价
                strategy['reason'] = '预测下跌，不建议参与集合竞价'
                strategy['suggestion'] = f'预测下跌（上涨概率{up_prob*100:.1f}%），不建议参与集合竞价，建议观察开盘后再决定'
            else:
                strategy['reason'] = '预测不明确，建议观察后再决定'
                strategy['suggestion'] = f'预测方向{prediction_direction}（上涨概率{up_prob*100:.1f}%，置信度{confidence*100:.1f}%），预测不明确，建议观察开盘后再决定'
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"计算集合竞价策略失败: {str(e)}")
            return {
                'available': False,
                'reason': f'计算失败: {str(e)}'
            }
    
    def track_restricted_shares(self, symbol: str) -> Dict:
        """
        追踪限售股解禁
        - 解禁日期
        - 解禁数量
        - 解禁影响评估
        
        Args:
            symbol: 股票代码
        
        Returns:
            限售股解禁追踪结果字典
        """
        try:
            restricted_data = self.data_source.get_restricted_shares(symbol)
            
            if not restricted_data:
                return {
                    'has_restricted': False,
                    'reason': '无法获取限售股数据'
                }
            
            if not restricted_data.get('has_restricted'):
                return {
                    'has_restricted': False,
                    'reason': restricted_data.get('note', '未发现限售股或数据不足')
                }
            
            # 最近解禁日期
            next_lift_date = restricted_data.get('next_lift_date')
            lift_volume = restricted_data.get('lift_volume', 0) or 0
            total_shares = restricted_data.get('total_shares', 0) or 0
            restricted_shares = restricted_data.get('restricted_shares', 0) or 0
            restricted_ratio = restricted_data.get('restricted_ratio', 0) or 0
            
            # 计算解禁比例
            lift_ratio = lift_volume / total_shares if total_shares > 0 else 0
            
            # 计算距离解禁的天数（如果解禁日期可用）
            days_to_lift = None
            if next_lift_date:
                try:
                    from datetime import datetime
                    if isinstance(next_lift_date, str):
                        lift_date = datetime.strptime(next_lift_date, '%Y-%m-%d').date()
                    else:
                        lift_date = next_lift_date
                    today = datetime.now().date()
                    days_to_lift = (lift_date - today).days
                except Exception:
                    days_to_lift = None
            
            # 评估影响
            impact = 'minimal'
            impact_score = 0.0
            if lift_ratio > 0.1:
                impact = 'high'
                impact_score = 0.8
            elif lift_ratio > 0.05:
                impact = 'medium'
                impact_score = 0.5
            elif lift_ratio > 0.02:
                impact = 'low'
                impact_score = 0.3
            else:
                impact = 'minimal'
                impact_score = 0.1
            
            # 生成警告和建议
            warning = ''
            suggestion = ''
            if impact == 'high':
                warning = f'解禁比例{lift_ratio*100:.2f}%，影响{impact}，建议关注'
                suggestion = f'限售股解禁比例较高（{lift_ratio*100:.2f}%），可能对股价造成较大压力，建议谨慎操作'
            elif impact == 'medium':
                warning = f'解禁比例{lift_ratio*100:.2f}%，影响{impact}'
                suggestion = f'限售股解禁比例中等（{lift_ratio*100:.2f}%），可能对股价造成一定影响，建议关注'
            elif impact == 'low' and lift_ratio > 0:
                suggestion = f'限售股解禁比例较低（{lift_ratio*100:.2f}%），影响较小'
            
            result = {
                'has_restricted': True,
                'next_lift_date': next_lift_date.strftime('%Y-%m-%d') if next_lift_date and hasattr(next_lift_date, 'strftime') else (next_lift_date if next_lift_date else '未知'),
                'days_to_lift': days_to_lift,
                'lift_volume': lift_volume,
                'lift_ratio': lift_ratio,
                'restricted_shares': restricted_shares,
                'total_shares': total_shares,
                'restricted_ratio': restricted_ratio,
                'impact': impact,
                'impact_score': impact_score,
                'warning': warning,
                'suggestion': suggestion,
                'note': restricted_data.get('note', '')
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"追踪限售股解禁失败: {str(e)}")
            return {
                'has_restricted': False,
                'reason': f'追踪失败: {str(e)}'
            }
    
    def _make_trading_decision(self, symbol: str, signal_strength: float,
                               prediction_result: Dict, realtime_quote: Dict,
                               capital_flow: Dict, holding: bool,
                               cost_price: float, trading_time: Dict,
                               limit_up_strategy: Dict = None,
                               limit_down_strategy: Dict = None,
                               holding_period_optimization: Dict = None,
                               auction_strategy: Dict = None,
                               dragon_tiger_analysis: Dict = None,
                               restricted_shares_info: Dict = None) -> Dict:
        """
        生成交易决策
        """
        current_price = realtime_quote.get('current_price', 0)
        change_pct = realtime_quote.get('change_pct', 0)
        up_prob = prediction_result['up_probability']
        down_prob = prediction_result['down_probability']
        confidence = prediction_result['confidence']
        prediction_dir = prediction_result['prediction']
        
        decision = {
            'action': 'HOLD',  # BUY, SELL, HOLD
            'action_cn': '持有观望',
            'strength': 'NEUTRAL',  # STRONG, MODERATE, WEAK, NEUTRAL
            'strength_cn': '中性',
            'reasons': [],
            'price_suggestions': {},
            'risk_warnings': [],
            'position_advice': '',
            'limit_strategy': {}  # 涨跌停板策略
        }
        
        # 整合涨跌停板策略到决策中
        if limit_up_strategy and limit_up_strategy.get('available'):
            decision['limit_strategy']['limit_up'] = limit_up_strategy
            # 如果涨停且可以排队，添加建议
            if limit_up_strategy.get('is_limit_up') and limit_up_strategy.get('can_queue'):
                decision['reasons'].append(f"涨停板策略: {limit_up_strategy.get('reason', '')}")
                decision['risk_warnings'].append(limit_up_strategy.get('suggestion', ''))
            # 如果接近涨停且可以追涨，添加建议
            elif limit_up_strategy.get('is_near_limit') and limit_up_strategy.get('can_chase'):
                decision['reasons'].append(f"涨停板策略: {limit_up_strategy.get('reason', '')}")
                decision['risk_warnings'].append(limit_up_strategy.get('suggestion', ''))
            # 如果接近涨停但风险高，添加警告
            elif limit_up_strategy.get('is_near_limit') or limit_up_strategy.get('is_limit_up'):
                decision['risk_warnings'].append(f"涨停板风险: {limit_up_strategy.get('suggestion', '')}")
        
        if limit_down_strategy and limit_down_strategy.get('available'):
            decision['limit_strategy']['limit_down'] = limit_down_strategy
            # 如果跌停且可以抄底，添加建议
            if (limit_down_strategy.get('is_limit_down') or limit_down_strategy.get('is_near_limit')) and \
               limit_down_strategy.get('can_buy'):
                decision['reasons'].append(f"跌停板策略: {limit_down_strategy.get('reason', '')}")
                decision['risk_warnings'].append(limit_down_strategy.get('suggestion', ''))
            # 如果跌停但风险高，添加警告
            elif limit_down_strategy.get('is_limit_down') or limit_down_strategy.get('is_near_limit'):
                decision['risk_warnings'].append(f"跌停板风险: {limit_down_strategy.get('suggestion', '')}")
        
        # 整合龙虎榜分析到决策中
        if dragon_tiger_analysis and dragon_tiger_analysis.get('available'):
            decision['dragon_tiger'] = dragon_tiger_analysis
            impact = dragon_tiger_analysis.get('impact', 'neutral')
            if impact == 'positive':
                decision['reasons'].append(f"龙虎榜: {dragon_tiger_analysis.get('suggestion', '')}")
                # 龙虎榜正面影响，可以适当提高买入信号强度
                if decision.get('action') in ['BUY', 'ADD']:
                    decision['strength'] = 'STRONG' if decision.get('strength') == 'MODERATE' else decision.get('strength')
                    decision['strength_cn'] = '强烈' if decision.get('strength') == 'STRONG' else decision.get('strength_cn')
            elif impact == 'negative':
                decision['risk_warnings'].append(f"龙虎榜: {dragon_tiger_analysis.get('suggestion', '')}")
                # 龙虎榜负面影响，降低买入信号强度或建议观望
                if decision.get('action') in ['BUY', 'ADD']:
                    decision['action'] = 'WAIT'
                    decision['action_cn'] = '观望（龙虎榜显示资金流出）'
                    decision['strength'] = 'WEAK'
                    decision['strength_cn'] = '弱'
        
        # 整合限售股解禁信息到决策中
        if restricted_shares_info and restricted_shares_info.get('has_restricted'):
            decision['restricted_shares'] = restricted_shares_info
            impact = restricted_shares_info.get('impact', 'minimal')
            impact_score = restricted_shares_info.get('impact_score', 0.0)
            warning = restricted_shares_info.get('warning', '')
            suggestion = restricted_shares_info.get('suggestion', '')
            
            # 根据影响程度调整决策
            if impact == 'high':
                # 高影响：降低买入信号强度或建议观望
                if decision.get('action') in ['BUY', 'ADD']:
                    # 如果解禁日期很近（7天内），建议观望
                    days_to_lift = restricted_shares_info.get('days_to_lift')
                    if days_to_lift is not None and days_to_lift <= 7:
                        decision['action'] = 'WAIT'
                        decision['action_cn'] = '观望（近期解禁风险高）'
                        decision['strength'] = 'WEAK'
                        decision['strength_cn'] = '弱'
                    else:
                        # 解禁日期较远，降低信号强度
                        if decision.get('strength') == 'STRONG':
                            decision['strength'] = 'MODERATE'
                            decision['strength_cn'] = '适中'
                        decision['reasons'].append(f"限售股解禁风险：{warning}")
                
                decision['risk_warnings'].append(warning if warning else f"解禁比例{restricted_shares_info.get('lift_ratio', 0)*100:.2f}%，影响{impact}，建议关注")
            elif impact == 'medium':
                # 中等影响：添加风险警告
                decision['risk_warnings'].append(warning if warning else f"解禁比例{restricted_shares_info.get('lift_ratio', 0)*100:.2f}%，影响{impact}")
                if suggestion:
                    decision['reasons'].append(suggestion)
            elif impact == 'low' and warning:
                # 低影响：仅添加提醒
                decision['reasons'].append(warning)
        
        # 检查是否为交易时间
        if not trading_time.get('is_trading', False):
            session = trading_time.get('session', '')
            if session == 'pre_open':
                decision['action'] = 'PREPARE'
                decision['action_cn'] = '准备竞价'
            elif session in ['closed', 'weekend']:
                decision['action'] = 'WAIT'
                decision['action_cn'] = '等待开盘'
            decision['reasons'].append(f"当前时段: {trading_time.get('message', '')}")
        
        # 获取市场状态（如果可用）并调整策略
        market_state_info = prediction_result.get('market_state', {})
        market_state = market_state_info.get('state', 'sideways')
        decision['market_state'] = market_state  # 记录市场状态到决策中
        
        # 根据市场状态和波动率动态调整止损止盈阈值
        base_stop_loss_pct = self.config['stop_loss_pct']
        base_take_profit_pct = self.config['take_profit_pct']
        
        # 先根据市场状态调整
        if market_state == 'bull_market':
            # 牛市：提高止盈目标，放宽止损（趋势向上，可能继续上涨）
            market_adjusted_stop_loss_pct = base_stop_loss_pct * 1.2  # 放宽20%（负数变大）
            market_adjusted_take_profit_pct = base_take_profit_pct * 1.2  # 提高20%
        elif market_state == 'bear_market':
            # 熊市：降低止盈目标，收紧止损（趋势向下，风险较大）
            market_adjusted_stop_loss_pct = base_stop_loss_pct * 0.8  # 收紧20%（负数变小）
            market_adjusted_take_profit_pct = base_take_profit_pct * 0.8  # 降低20%
        else:
            market_adjusted_stop_loss_pct = base_stop_loss_pct
            market_adjusted_take_profit_pct = base_take_profit_pct
        
        # 再根据波动率进一步调整（如果风险管理器可用）
        adjusted_stop_loss_pct = market_adjusted_stop_loss_pct
        adjusted_take_profit_pct = market_adjusted_take_profit_pct
        
        try:
            from utils.risk_manager import get_risk_manager
            risk_manager = get_risk_manager()
            
            # 获取股票数据用于计算波动率
            stock_data = None
            try:
                stock_data = self.data_source.get_stock_data(symbol, days=30)
            except Exception:
                pass
            
            # 计算动态止损/止盈
            dynamic_result = risk_manager.calculate_dynamic_stop_loss_take_profit(
                symbol=symbol,
                current_price=current_price,
                stock_data=stock_data,
                base_stop_loss_pct=market_adjusted_stop_loss_pct,
                base_take_profit_pct=market_adjusted_take_profit_pct,
                volatility_period=20
            )
            
            adjusted_stop_loss_pct = dynamic_result.get('stop_loss_pct', market_adjusted_stop_loss_pct)
            adjusted_take_profit_pct = dynamic_result.get('take_profit_pct', market_adjusted_take_profit_pct)
            
            # 保存动态调整结果到决策中
            decision['dynamic_risk_adjustment'] = {
                'stop_loss_pct': adjusted_stop_loss_pct,
                'take_profit_pct': adjusted_take_profit_pct,
                'volatility': dynamic_result.get('volatility'),
                'adjustment_factor': dynamic_result.get('adjustment_factor'),
                'explanation': dynamic_result.get('explanation')
            }
            
            self.logger.debug(f"动态止损/止盈调整: 波动率={dynamic_result.get('volatility')}, "
                            f"止损={adjusted_stop_loss_pct:.1f}%, 止盈={adjusted_take_profit_pct:.1f}%")
            
        except Exception as e:
            self.logger.debug(f"动态止损/止盈计算失败，使用市场状态调整后的值: {str(e)}")
        
        # T+1制度优化：计算持仓成本和资金占用成本
        position_cost_info = None
        if holding and cost_price and cost_price > 0:
            # 计算持仓成本（考虑T+1制度）
            position_cost_info = self._calculate_position_cost(
                symbol, cost_price, current_price
            )
            decision['position_cost'] = position_cost_info
            
            profit_pct = (current_price - cost_price) / cost_price * 100
            decision['current_profit_pct'] = profit_pct
            
            # 考虑T+1制度，至少持有1天
            decision['min_holding_days'] = 1  # T+1制度，至少持有1天
            decision['holding_advice'] = 'T+1制度：当天买入的股票，当天不能卖出，至少持有1天'
            
            # 止损检查（使用调整后的止损阈值）
            if profit_pct <= adjusted_stop_loss_pct:
                decision['action'] = 'SELL'
                decision['action_cn'] = '止损卖出'
                decision['strength'] = 'STRONG'
                decision['strength_cn'] = '强烈'
                decision['reasons'].append(f"触发止损线（{market_state}市场调整后: {adjusted_stop_loss_pct:.1f}%），当前亏损{profit_pct:.2f}%")
                decision['risk_warnings'].append('建议立即止损，避免更大损失')
            
            # 止盈检查（使用调整后的止盈阈值）
            elif profit_pct >= adjusted_take_profit_pct:
                if prediction_dir == '下跌' or down_prob > 0.6:
                    decision['action'] = 'SELL'
                    decision['action_cn'] = '止盈卖出'
                    decision['strength'] = 'STRONG'
                    decision['strength_cn'] = '强烈'
                    decision['reasons'].append(f"达到止盈目标（{market_state}市场调整后: {adjusted_take_profit_pct:.1f}%），当前盈利{profit_pct:.2f}%")
                    decision['reasons'].append(f"预测明天{prediction_dir}，建议落袋为安")
                else:
                    decision['action'] = 'HOLD'
                    decision['action_cn'] = '继续持有'
                    decision['strength'] = 'MODERATE'
                    decision['strength_cn'] = '适中'
                    decision['reasons'].append(f"当前盈利{profit_pct:.2f}%，但预测明天看涨")
                    decision['reasons'].append('可设置移动止损继续持有')
                    decision['price_suggestions']['trailing_stop'] = round(
                        current_price * (1 - self.config['trailing_stop_pct'] / 100), 2
                    )
            
            # 持有中的卖出决策
            elif down_prob > self.config['strong_sell_threshold'] and confidence > self.config['min_confidence']:
                decision['action'] = 'SELL'
                decision['action_cn'] = '建议卖出'
                decision['strength'] = 'STRONG'
                decision['strength_cn'] = '强烈'
                decision['reasons'].append(f"预测明天下跌概率{down_prob:.1%}，置信度{confidence:.1%}")
                if profit_pct > 0:
                    decision['reasons'].append(f"当前盈利{profit_pct:.2f}%，建议先行获利了结")
                else:
                    decision['reasons'].append(f"当前亏损{abs(profit_pct):.2f}%，建议减仓止损")
            
            elif down_prob > self.config['sell_signal_threshold'] and confidence > self.config['min_confidence']:
                decision['action'] = 'REDUCE'
                decision['action_cn'] = '建议减仓'
                decision['strength'] = 'MODERATE'
                decision['strength_cn'] = '适中'
                decision['reasons'].append(f"预测明天下跌概率{down_prob:.1%}")
                decision['position_advice'] = '建议减仓50%'
            
            # 持有中的加仓决策
            elif up_prob > self.config['strong_buy_threshold'] and confidence > self.config['high_confidence']:
                if profit_pct > 0:  # 盈利中才考虑加仓
                    decision['action'] = 'ADD'
                    decision['action_cn'] = '可以加仓'
                    decision['strength'] = 'MODERATE'
                    decision['strength_cn'] = '适中'
                    decision['reasons'].append(f"预测明天上涨概率{up_prob:.1%}，置信度高")
                    decision['reasons'].append(f"当前盈利{profit_pct:.2f}%，趋势良好")
                    decision['position_advice'] = '可适当加仓，但注意控制总仓位'
        
        # 如果未持有股票
        else:
            # T+1制度优化：考虑持仓周期和资金成本
            if holding_period_optimization:
                decision['holding_period_optimization'] = holding_period_optimization
                # 如果持仓周期优化建议不买入，则不建议买入
                if not holding_period_optimization.get('should_buy', True):
                    decision['action'] = 'WAIT'
                    decision['action_cn'] = '观望（T+1制度：预期净收益不足）'
                    decision['strength'] = 'WEAK'
                    decision['strength_cn'] = '弱'
                    decision['reasons'].append(holding_period_optimization.get('reason', ''))
                    decision['reasons'].append(f"T+1制度：至少持有1天，资金占用成本需考虑")
                    decision['risk_warnings'].append(holding_period_optimization.get('suggestion', ''))
                    return decision
                else:
                    # 如果建议买入，添加T+1制度说明
                    decision['reasons'].append(holding_period_optimization.get('reason', ''))
                    decision['reasons'].append(f"T+1制度：至少持有1天，净收益{holding_period_optimization.get('net_return', 0):.2f}%")
            
            # 计算预期收益（基于预测概率）
            expected_return = (up_prob - down_prob) * 0.05  # 假设平均涨幅5%
            
            # 计算交易成本
            if self.config.get('enable_cost_consideration', True):
                # 买入成本：手续费 + 滑点
                buy_cost_rate = self.config['commission_rate'] + self.config['slippage_rate']
                # 卖出成本：手续费 + 印花税 + 滑点（假设未来卖出）
                sell_cost_rate = self.config['commission_rate'] + self.config['stamp_tax_rate'] + self.config['slippage_rate']
                # 总成本率（买入+卖出）
                total_cost_rate = buy_cost_rate + sell_cost_rate
                
                # 净预期收益 = 预期收益 - 交易成本
                net_expected_return = expected_return - total_cost_rate
                
                # 检查是否达到最小盈利阈值
                min_threshold = self.config.get('min_profit_threshold', 0.01)
                cost_info = {
                    'total_cost_rate': total_cost_rate,
                    'expected_return': expected_return,
                    'net_expected_return': net_expected_return,
                    'cost_breakdown': {
                        'commission': self.config['commission_rate'],
                        'stamp_tax': self.config['stamp_tax_rate'],
                        'slippage': self.config['slippage_rate']
                    }
                }
                decision['cost_analysis'] = cost_info
                
                # 如果净预期收益不足，不建议买入
                if net_expected_return < min_threshold:
                    decision['action'] = 'WAIT'
                    decision['action_cn'] = '观望（预期收益不足覆盖交易成本）'
                    decision['strength'] = 'WEAK'
                    decision['strength_cn'] = '弱'
                    decision['reasons'].append(f"预期净收益{net_expected_return:.2%} < 最小阈值{min_threshold:.2%}")
                    decision['reasons'].append(f"交易成本率: {total_cost_rate:.2%}（手续费{buy_cost_rate:.2%}+卖出{sell_cost_rate:.2%}）")
                    return decision
            
            # 强烈买入信号
            if up_prob > self.config['strong_buy_threshold'] and confidence > self.config['high_confidence']:
                decision['action'] = 'BUY'
                decision['action_cn'] = '建议买入'
                decision['strength'] = 'STRONG'
                decision['strength_cn'] = '强烈'
                decision['reasons'].append(f"预测明天上涨概率{up_prob:.1%}，置信度{confidence:.1%}")
                
                # 添加交易成本信息
                if self.config.get('enable_cost_consideration', True) and 'cost_analysis' in decision:
                    cost = decision['cost_analysis']
                    decision['reasons'].append(f"预期净收益: {cost['net_expected_return']:.2%}（扣除交易成本{cost['total_cost_rate']:.2%}）")
                
                # 检查资金流向
                if capital_flow and capital_flow.get('flow_trend') == '资金净流入':
                    decision['reasons'].append('实时资金净流入，买盘活跃')
                
                # 检查今日涨跌
                if change_pct > 3:
                    decision['risk_warnings'].append(f'今日已涨{change_pct:.2f}%，注意追高风险')
                    decision['strength'] = 'MODERATE'
                    decision['strength_cn'] = '适中'
                elif change_pct < -3:
                    decision['reasons'].append(f'今日回调{abs(change_pct):.2f}%，可能是买入机会')
                
                decision['position_advice'] = f'建议仓位: {self.config["position_step"]}%-{self.config["max_position_pct"]}%'
            
            # 普通买入信号
            elif up_prob > self.config['buy_signal_threshold'] and confidence > self.config['min_confidence']:
                decision['action'] = 'BUY'
                decision['action_cn'] = '可以买入'
                decision['strength'] = 'MODERATE'
                decision['strength_cn'] = '适中'
                decision['reasons'].append(f"预测明天上涨概率{up_prob:.1%}")
                
                # 添加交易成本信息
                if self.config.get('enable_cost_consideration', True) and 'cost_analysis' in decision:
                    cost = decision['cost_analysis']
                    decision['reasons'].append(f"预期净收益: {cost['net_expected_return']:.2%}")
                
                decision['position_advice'] = f'建议轻仓试探: {self.config["position_step"]}%'
            
            # 观望信号
            elif prediction_dir == '震荡':
                decision['action'] = 'WAIT'
                decision['action_cn'] = '建议观望'
                decision['strength'] = 'NEUTRAL'
                decision['strength_cn'] = '中性'
                decision['reasons'].append('预测明天震荡，建议观望')
                decision['reasons'].append('等待更明确的方向信号')
            
            # 不建议买入
            elif down_prob > self.config['sell_signal_threshold']:
                decision['action'] = 'AVOID'
                decision['action_cn'] = '不建议买入'
                decision['strength'] = 'MODERATE'
                decision['strength_cn'] = '适中'
                decision['reasons'].append(f"预测明天下跌概率{down_prob:.1%}")
                decision['reasons'].append('建议等待回调后再考虑')
        
        # 添加价格建议
        if decision['action'] in ['BUY', 'ADD']:
            # 买入价格建议
            if change_pct > 0:
                # 今日上涨，建议等回调
                decision['price_suggestions']['ideal_buy'] = round(current_price * 0.98, 2)
                decision['price_suggestions']['max_buy'] = round(current_price * 1.01, 2)
            else:
                # 今日下跌，可以当前价附近买入
                decision['price_suggestions']['ideal_buy'] = round(current_price * 0.99, 2)
                decision['price_suggestions']['max_buy'] = round(current_price * 1.02, 2)
            
            # 止损价
            decision['price_suggestions']['stop_loss'] = round(
                decision['price_suggestions']['ideal_buy'] * (1 + self.config['stop_loss_pct'] / 100), 2
            )
            # 目标价
            decision['price_suggestions']['target'] = round(
                decision['price_suggestions']['ideal_buy'] * (1 + self.config['take_profit_pct'] / 100), 2
            )
        
        elif decision['action'] in ['SELL', 'REDUCE']:
            # 卖出价格建议
            if change_pct > 0:
                # 今日上涨，可以稍等更高价
                decision['price_suggestions']['ideal_sell'] = round(current_price * 1.01, 2)
                decision['price_suggestions']['min_sell'] = round(current_price * 0.99, 2)
            else:
                # 今日下跌，建议尽快卖出
                decision['price_suggestions']['ideal_sell'] = current_price
                decision['price_suggestions']['min_sell'] = round(current_price * 0.98, 2)
        
        return decision
    
    def _print_decision_summary(self, result: Dict):
        """打印决策摘要"""
        decision = result.get('decision', {})
        quote = result.get('realtime_quote', {})
        prediction = result.get('prediction', {})
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("【实时交易决策结果】")
        self.logger.info("=" * 60)
        
        # 基本信息
        self.logger.info(f"\n股票代码: {result['symbol']}")
        self.logger.info(f"当前价格: {quote.get('current_price', 'N/A')}元")
        self.logger.info(f"今日涨跌: {quote.get('change_pct', 'N/A')}%")
        
        # 预测信息
        self.logger.info(f"\n【明日预测】")
        self.logger.info(f"预测方向: {prediction.get('direction', 'N/A')}")
        self.logger.info(f"上涨概率: {prediction.get('up_probability', 0):.1%}")
        self.logger.info(f"置信度: {prediction.get('confidence', 0):.1%}")
        
        # 交易决策
        action_cn = decision.get('action_cn', '未知')
        strength_cn = decision.get('strength_cn', '未知')
        
        self.logger.info(f"\n【交易决策】")
        self.logger.info(f"操作建议: {action_cn} ({strength_cn})")
        
        # 决策理由
        reasons = decision.get('reasons', [])
        if reasons:
            self.logger.info(f"\n决策理由:")
            for i, reason in enumerate(reasons, 1):
                self.logger.info(f"  {i}. {reason}")
        
        # 价格建议
        price_suggestions = decision.get('price_suggestions', {})
        if price_suggestions:
            self.logger.info(f"\n价格建议:")
            if 'ideal_buy' in price_suggestions:
                self.logger.info(f"  理想买入价: {price_suggestions['ideal_buy']}元")
                self.logger.info(f"  最高买入价: {price_suggestions.get('max_buy', 'N/A')}元")
                self.logger.info(f"  止损价: {price_suggestions.get('stop_loss', 'N/A')}元")
                self.logger.info(f"  目标价: {price_suggestions.get('target', 'N/A')}元")
            if 'ideal_sell' in price_suggestions:
                self.logger.info(f"  理想卖出价: {price_suggestions['ideal_sell']}元")
                self.logger.info(f"  最低卖出价: {price_suggestions.get('min_sell', 'N/A')}元")
            if 'trailing_stop' in price_suggestions:
                self.logger.info(f"  移动止损价: {price_suggestions['trailing_stop']}元")
        
        # 仓位建议
        position_advice = decision.get('position_advice', '')
        if position_advice:
            self.logger.info(f"\n仓位建议: {position_advice}")
        
        # 风险警告
        warnings = decision.get('risk_warnings', [])
        if warnings:
            self.logger.info(f"\n⚠️ 风险警告:")
            for warning in warnings:
                self.logger.info(f"  - {warning}")
        
        # 信号强度评分说明
        signal_explanation = result.get('signal_explanation')
        if signal_explanation:
            self.logger.info(f"\n【信号强度评分说明】")
            self.logger.info(f"信号强度: {signal_explanation['signal_strength']:.1%} ({signal_explanation['interpretation']})")
            self.logger.info(f"\n{signal_explanation['explanation']}")
            if signal_explanation.get('suggestions'):
                self.logger.info(f"\n建议:")
                for suggestion in signal_explanation['suggestions']:
                    self.logger.info(f"  - {suggestion}")
        
        self.logger.info("\n" + "=" * 60)
    
    def monitor_realtime(self, symbol: str, interval_seconds: int = 60,
                         holding: bool = False, cost_price: float = None):
        """
        实时监控股票，定期更新交易建议
        
        Args:
            symbol: 股票代码
            interval_seconds: 更新间隔（秒）
            holding: 是否持有
            cost_price: 持仓成本
        """
        import time as time_module
        
        self.logger.info(f"\n开始实时监控 {symbol}，更新间隔 {interval_seconds} 秒")
        self.logger.info("按 Ctrl+C 停止监控\n")
        
        # 初始化可视化器（用于生成HTML报告）
        try:
            vis_spec = importlib.util.spec_from_file_location(
                "prediction_visualizer",
                os.path.join(project_root, "visualizer", "prediction_visualizer.py")
            )
            vis_module = importlib.util.module_from_spec(vis_spec)
            vis_spec.loader.exec_module(vis_module)
            PredictionVisualizer = vis_module.PredictionVisualizer
            visualizer = PredictionVisualizer()
            self.logger.info("HTML报告可视化器已初始化")
        except Exception as e:
            self.logger.warning(f"初始化HTML可视化器失败: {str(e)}，监控模式将只输出控制台日志")
            visualizer = None
        
        # 监控模式专用HTML文件名（固定文件名，每次覆盖）
        monitor_html_file = None
        if visualizer:
            monitor_html_file = os.path.join(visualizer.reports_dir, f'monitor_{symbol}.html')
            self.logger.info(f"HTML监控页面将保存到: {monitor_html_file}")
            self.logger.info("请在浏览器中打开此文件，页面将自动刷新\n")
            
            # 生成初始监控页面（包含设置信息）
            try:
                initial_page = visualizer.create_realtime_monitor_page(
                    symbol=symbol,
                    interval=interval_seconds,
                    holding=holding,
                    cost_price=cost_price
                )
                if initial_page:
                    self.logger.info(f"  初始监控页面已生成: {initial_page}")
            except Exception as e:
                self.logger.warning(f"  生成初始监控页面失败: {str(e)}")
        
        last_action = None
        update_count = 0
        
        try:
            while True:
                # 检查是否为交易时间
                trading_time = self.data_source.is_trading_time()
                
                if not trading_time.get('is_trading', False):
                    session = trading_time.get('session', '')
                    if session in ['closed', 'weekend']:
                        self.logger.info(f"当前非交易时间: {trading_time.get('message', '')}")
                        self.logger.info("监控结束")
                        break
                    elif session == 'noon_break':
                        self.logger.info("午间休市，等待下午开盘...")
                        time_module.sleep(60)
                        continue
                
                update_count += 1
                self.logger.info(f"\n[更新 #{update_count}] 获取最新实时数据...")
                
                # 获取实时决策
                result = self.get_realtime_decision(
                    symbol=symbol,
                    holding=holding,
                    cost_price=cost_price,
                    mode="monitor"
                )
                
                # 检查是否有重要信号变化
                if result.get('success', False):
                    current_action = result.get('decision', {}).get('action', '')
                    
                    if current_action != last_action:
                        if current_action in ['BUY', 'SELL', 'ADD', 'REDUCE']:
                            self.logger.warning(f"\n🔔 信号变化: {last_action} -> {current_action}")
                            self.logger.warning("请注意查看最新交易建议！\n")
                        last_action = current_action
                    
                    # 生成HTML报告（如果可视化器可用）
                    if visualizer and monitor_html_file:
                        try:
                            # 执行预测分析以获取完整数据
                            prediction_result = self.predictor.predict(symbol)
                            if prediction_result.get('success', False):
                                # 获取股票数据
                                stock_data = self.data_source.get_stock_data(symbol, days=60)
                                
                                # 准备实时数据
                                realtime_data = {
                                    'quote': result.get('realtime_quote', {}),
                                    'capital_flow': result.get('capital_flow', {}),
                                    'trading_time': result.get('trading_time', {}),
                                    'decision': result.get('decision', {}),
                                    'prediction': result.get('prediction', {}),
                                    'signal_strength': result.get('signal_strength', 0)
                                }
                                
                                # 生成HTML报告（使用固定文件名，每次覆盖）
                                html_file = visualizer._create_interactive_html_report(
                                    prediction_result, 
                                    stock_data, 
                                    realtime_data,
                                    monitor_html_file=monitor_html_file,
                                    refresh_interval=interval_seconds
                                )
                                
                                if html_file:
                                    self.logger.info(f"  ✅ HTML监控页面已更新: {html_file}")
                                    self.logger.info(f"     请在浏览器中打开: {html_file}")
                        except Exception as e:
                            self.logger.warning(f"  生成HTML报告失败: {str(e)}")
                            import traceback
                            self.logger.debug(traceback.format_exc())
                            # 不影响监控继续运行
                
                # 等待下一次更新
                self.logger.info(f"\n等待 {interval_seconds} 秒后更新...")
                time_module.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            self.logger.info("\n\n用户停止监控")
            if monitor_html_file:
                self.logger.info(f"最后更新的HTML页面: {monitor_html_file}")
    
    def batch_scan(self, symbols: List[str], top_n: int = 10) -> List[Dict]:
        """
        批量扫描股票，找出最佳买入机会
        
        Args:
            symbols: 股票代码列表
            top_n: 返回前N个最佳机会
            
        Returns:
            排序后的机会列表
        """
        self.logger.info(f"\n开始批量扫描 {len(symbols)} 只股票...")
        
        opportunities = []
        
        for i, symbol in enumerate(symbols, 1):
            try:
                self.logger.info(f"\n[{i}/{len(symbols)}] 扫描: {symbol}")
                
                result = self.get_realtime_decision(symbol, holding=False, mode="scan")
                
                if result.get('success', False):
                    decision = result.get('decision', {})
                    prediction = result.get('prediction', {})
                    quote = result.get('realtime_quote', {})
                    
                    # 只关注买入信号
                    if decision.get('action') in ['BUY', 'ADD']:
                        opportunities.append({
                            'symbol': symbol,
                            'name': quote.get('name', ''),
                            'current_price': quote.get('current_price', 0),
                            'change_pct': quote.get('change_pct', 0),
                            'up_probability': prediction.get('up_probability', 0),
                            'confidence': prediction.get('confidence', 0),
                            'signal_strength': result.get('signal_strength', 0),
                            'action': decision.get('action_cn', ''),
                            'strength': decision.get('strength_cn', ''),
                            'reasons': decision.get('reasons', [])
                        })
                        
            except Exception as e:
                self.logger.warning(f"扫描 {symbol} 失败: {str(e)}")
                continue
        
        # 按信号强度排序
        opportunities.sort(key=lambda x: (x['signal_strength'], x['up_probability']), reverse=True)
        
        # 返回前N个
        top_opportunities = opportunities[:top_n]
        
        # 打印结果
        self.logger.info(f"\n\n{'='*80}")
        self.logger.info(f"批量扫描结果 - 前 {len(top_opportunities)} 个买入机会")
        self.logger.info(f"{'='*80}")
        
        for i, opp in enumerate(top_opportunities, 1):
            self.logger.info(f"\n{i}. {opp['symbol']} {opp['name']}")
            self.logger.info(f"   当前价: {opp['current_price']}元, 涨跌: {opp['change_pct']:.2f}%")
            self.logger.info(f"   上涨概率: {opp['up_probability']:.1%}, 置信度: {opp['confidence']:.1%}")
            self.logger.info(f"   操作建议: {opp['action']} ({opp['strength']})")
        
        return top_opportunities


# 便捷函数
def get_trading_advice(symbol: str, holding: bool = False, cost_price: float = None) -> Dict:
    """
    获取股票交易建议的便捷函数
    
    Args:
        symbol: 股票代码
        holding: 是否持有该股票
        cost_price: 持仓成本价
        
    Returns:
        交易决策结果
    """
    advisor = RealtimeTradingAdvisor()
    return advisor.get_realtime_decision(symbol, holding, cost_price, mode="single")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='实时交易决策顾问')
    parser.add_argument('--symbol', '-s', type=str, help='股票代码')
    parser.add_argument('--holding', action='store_true', help='是否持有该股票')
    parser.add_argument('--cost', type=float, help='持仓成本价')
    parser.add_argument('--monitor', '-m', action='store_true', help='开启实时监控模式')
    parser.add_argument('--interval', '-i', type=int, default=60, help='监控更新间隔（秒）')
    parser.add_argument('--scan', action='store_true', help='批量扫描模式')
    parser.add_argument('--limit', type=int, default=20, help='扫描股票数量限制')
    
    args = parser.parse_args()
    
    advisor = RealtimeTradingAdvisor()
    
    if args.scan:
        # 批量扫描模式
        data_source = StockDataSource()
        stock_list = data_source.get_all_stock_list(limit=args.limit, sort_by_turnover=True)
        symbols = [s['symbol'] for s in stock_list]
        advisor.batch_scan(symbols, top_n=10)
    
    elif args.symbol:
        if args.monitor:
            # 实时监控模式
            advisor.monitor_realtime(
                symbol=args.symbol,
                interval_seconds=args.interval,
                holding=args.holding,
                cost_price=args.cost
            )
        else:
            # 单次决策
            advisor.get_realtime_decision(
                symbol=args.symbol,
                holding=args.holding,
                cost_price=args.cost
            )
    else:
        print("请指定股票代码 (--symbol) 或使用批量扫描模式 (--scan)")
        print("\n示例:")
        print("  py realtime_trading_advisor.py --symbol 600519")
        print("  py realtime_trading_advisor.py --symbol 600519 --holding --cost 1800")
        print("  py realtime_trading_advisor.py --symbol 600519 --monitor --interval 30")
        print("  py realtime_trading_advisor.py --scan --limit 50")

