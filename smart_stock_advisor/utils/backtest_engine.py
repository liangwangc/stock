"""
回测引擎模块
用于使用历史数据模拟交易，评估不同参数组合的表现
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from utils.prediction_config_manager import PredictionConfigManager

# 导入配置常量
try:
    from config import CONFIDENCE_THRESHOLDS, PROBABILITY_THRESHOLDS
except ImportError:
    # 如果导入失败，使用默认值
    CONFIDENCE_THRESHOLDS = {
        "medium": 0.55,
    }
    PROBABILITY_THRESHOLDS = {
        "buy_signal": 0.6,
    }

logger = get_logger(__name__)


class BacktestEngine:
    """回测引擎"""
    
    # 最大持仓天数（超过后强制平仓，避免持仓"卡住"）
    MAX_HOLDING_DAYS = 10
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        self.config_manager = PredictionConfigManager()
    
    def _get_trading_params_from_config(self) -> Dict:
        """
        从数据库配置中读取交易参数（优化器保存的最佳参数）。
        如果读取失败则使用合理默认值。
        """
        defaults = {
            'buy_threshold': 0.6,
            'sell_threshold': 0.4,
            'min_confidence': 0.55,
            'stop_loss_pct': -5.0,
            'take_profit_pct': 8.0,
            'max_position_pct': 0.3,
            'max_holding_days': self.MAX_HOLDING_DAYS,
        }
        try:
            config = self.config_manager.get_config()
            if config:
                prediction = config.get('prediction', {}) if isinstance(config.get('prediction', {}), dict) else {}
                # 统一优先读取顶层 trading 分类，其次兼容历史结构
                trading = config.get('trading', {}) if isinstance(config.get('trading', {}), dict) else {}
                legacy_trading = prediction.get('trading', {}) if isinstance(prediction.get('trading', {}), dict) else {}

                # 兼容旧键名，避免“设置了参数但回测读不到”
                alias_map = {
                    'buy_threshold': ['buy_threshold', 'buy_signal_threshold'],
                    'sell_threshold': ['sell_threshold', 'sell_signal_threshold'],
                    'min_confidence': ['min_confidence', 'trading_min_confidence', 'confidence_threshold'],
                    'stop_loss_pct': ['stop_loss_pct'],
                    'take_profit_pct': ['take_profit_pct'],
                    'max_position_pct': ['max_position_pct', 'max_single_position_pct'],
                    'max_holding_days': ['max_holding_days'],
                }

                sources = [trading, legacy_trading, prediction]
                for target_key, candidate_keys in alias_map.items():
                    for source in sources:
                        for candidate_key in candidate_keys:
                            if candidate_key in source and source[candidate_key] is not None:
                                defaults[target_key] = float(source[candidate_key])
                                break
                        else:
                            continue
                        break

                # 统一仓位单位：配置可能是比例(0.3)或百分比(30)
                if defaults['max_position_pct'] > 1:
                    defaults['max_position_pct'] = defaults['max_position_pct'] / 100.0

                # 防御性裁剪，避免脏配置影响回测稳定性
                defaults['max_position_pct'] = max(0.01, min(1.0, defaults['max_position_pct']))
                if defaults['stop_loss_pct'] > 0:
                    defaults['stop_loss_pct'] = -abs(defaults['stop_loss_pct'])
        except Exception as e:
            self.logger.warning(f"读取配置交易参数失败，使用默认值: {e}")
        return defaults
    
    def _get_predictions(self, start_date: str, end_date: str) -> List[Dict]:
        """查询已验证的预测记录"""
        sql = """
            SELECT 
                symbol, name, prediction_date, target_date,
                prediction, up_probability, down_probability, confidence,
                current_price, actual_price, actual_change_pct,
                prediction_hit
            FROM stock_predictions
            WHERE target_date >= %s 
              AND target_date <= %s
              AND actual_price IS NOT NULL
              AND prediction_hit IS NOT NULL
            ORDER BY target_date ASC
        """
        return self.db.execute_query(sql, (start_date, end_date)) or []
    
    def _check_positions_for_sell(self, positions: dict, latest_prices: dict,
                                  current_date, capital: float, trades: list,
                                  stop_loss_pct: float, take_profit_pct: float,
                                  stamp_tax_rate: float, commission_rate: float,
                                  slippage_rate: float,
                                  max_holding_days: int = None,
                                  exclude_symbols: set = None) -> float:
        """
        在日期切换时，遍历所有持仓检查止盈/止损/超时强制平仓。
        这样即使某只股票当天没有新的预测记录，仍然能执行风控。
        
        Args:
            positions: 当前持仓字典（会被原地修改）
            latest_prices: 最新市价字典
            current_date: 当前处理的日期
            capital: 当前可用现金
            trades: 交易记录列表（会被原地追加）
            stop_loss_pct: 止损阈值（百分比，如 -5.0）
            take_profit_pct: 止盈阈值（百分比，如 8.0）
            stamp_tax_rate: 印花税费率
            commission_rate: 佣金费率
            slippage_rate: 滑点费率
            max_holding_days: 最大持仓天数，None 使用类默认值
            exclude_symbols: 本轮已经被信号处理过的股票，跳过避免重复
            
        Returns:
            更新后的 capital
        """
        if max_holding_days is None:
            max_holding_days = self.MAX_HOLDING_DAYS
        if exclude_symbols is None:
            exclude_symbols = set()
        
        symbols_to_sell = []
        
        for symbol, pos in positions.items():
            if symbol in exclude_symbols:
                continue
            
            cost_price = pos['cost_price']
            market_price = latest_prices.get(symbol, cost_price)
            profit_pct = (market_price - cost_price) / cost_price * 100 if cost_price > 0 else 0
            
            should_sell = False
            sell_reason = ''
            
            # 止盈
            if profit_pct >= take_profit_pct:
                should_sell = True
                sell_reason = '止盈'
            # 止损
            elif profit_pct <= stop_loss_pct:
                should_sell = True
                sell_reason = '止损'
            # 超时强制平仓
            elif max_holding_days > 0:
                buy_date = pos.get('buy_date')
                if buy_date and current_date:
                    try:
                        if isinstance(buy_date, str):
                            buy_dt = datetime.strptime(buy_date, '%Y-%m-%d').date()
                        else:
                            buy_dt = buy_date if hasattr(buy_date, 'year') else buy_date
                        if isinstance(current_date, str):
                            cur_dt = datetime.strptime(current_date, '%Y-%m-%d').date()
                        else:
                            cur_dt = current_date if hasattr(current_date, 'year') else current_date
                        holding_days = (cur_dt - buy_dt).days
                        if holding_days >= max_holding_days:
                            should_sell = True
                            sell_reason = f'持仓超{max_holding_days}天'
                    except Exception:
                        pass
            
            if should_sell:
                symbols_to_sell.append((symbol, market_price, sell_reason, profit_pct))
        
        # 执行卖出（不能在遍历 positions 时删除）
        for symbol, sell_price, sell_reason, profit_pct in symbols_to_sell:
            pos = positions[symbol]
            proceeds = self._sell_stock(
                symbol, pos['shares'], sell_price,
                stamp_tax_rate, commission_rate, slippage_rate
            )
            capital += proceeds
            actual_profit = proceeds - pos['total_cost']
            
            trades.append({
                'date': current_date,
                'symbol': symbol,
                'action': 'SELL',
                'price': sell_price,
                'shares': pos['shares'],
                'cost_price': round(pos['cost_price'], 4),
                'profit': round(actual_profit, 2),
                'profit_pct': round(profit_pct, 2),
                'reason': sell_reason,
                'capital_after': round(capital, 2)
            })
            del positions[symbol]
        
        return capital
    
    def _force_close_all(self, positions: dict, latest_prices: dict,
                         close_date, capital: float, trades: list,
                         stamp_tax_rate: float, commission_rate: float,
                         slippage_rate: float) -> float:
        """
        回测结束时强制平仓所有剩余持仓，计入交易记录和手续费。
        
        Returns:
            更新后的 capital
        """
        symbols_to_close = list(positions.keys())
        for symbol in symbols_to_close:
            pos = positions[symbol]
            sell_price = latest_prices.get(symbol, pos['cost_price'])
            profit_pct = (sell_price - pos['cost_price']) / pos['cost_price'] * 100 if pos['cost_price'] > 0 else 0
            
            proceeds = self._sell_stock(
                symbol, pos['shares'], sell_price,
                stamp_tax_rate, commission_rate, slippage_rate
            )
            capital += proceeds
            actual_profit = proceeds - pos['total_cost']
            
            trades.append({
                'date': close_date,
                'symbol': symbol,
                'action': 'SELL',
                'price': sell_price,
                'shares': pos['shares'],
                'cost_price': round(pos['cost_price'], 4),
                'profit': round(actual_profit, 2),
                'profit_pct': round(profit_pct, 2),
                'reason': '回测结束平仓',
                'capital_after': round(capital, 2)
            })
            del positions[symbol]
        
        return capital
    
    def backtest_predictions(self, start_date: str, end_date: str, 
                            initial_capital: float = 100000.0,
                            commission_rate: float = 0.0003,
                            stamp_tax_rate: float = 0.001,
                            slippage_rate: float = 0.001) -> Dict:
        """
        回测预测模型
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            initial_capital: 初始资金
            commission_rate: 佣金费率
            stamp_tax_rate: 印花税费率
            slippage_rate: 滑点费率
            
        Returns:
            回测结果字典
        """
        try:
            # 从数据库配置读取交易参数（与优化器使用同一套参数）
            tp = self._get_trading_params_from_config()
            buy_threshold = tp['buy_threshold']
            sell_threshold = tp['sell_threshold']
            min_confidence = tp['min_confidence']
            stop_loss_pct = tp['stop_loss_pct']
            take_profit_pct = tp['take_profit_pct']
            max_position_pct = tp['max_position_pct']
            max_holding_days = int(tp['max_holding_days'])
            
            self.logger.info(
                f"回测使用交易参数: 买入阈值={buy_threshold}, 卖出阈值={sell_threshold}, "
                f"置信度={min_confidence}, 止损={stop_loss_pct}%, 止盈={take_profit_pct}%, "
                f"仓位={max_position_pct}, 持仓天数={max_holding_days}"
            )
            
            predictions = self._get_predictions(start_date, end_date)
            
            if not predictions:
                return {
                    'success': False,
                    'message': f'没有找到 {start_date} 到 {end_date} 期间的预测记录'
                }
            
            # 模拟交易
            capital = initial_capital
            positions = {}  # {symbol: {'shares': int, 'cost_price': float, 'total_cost': float, 'buy_date': str}}
            trades = []  # 交易记录
            daily_values = []  # 每日资产价值
            latest_prices = {}  # 跟踪每只股票最新市场价格
            
            current_date = None
            processed_symbols_today = set()  # 当天已被信号处理过的股票
            
            # 统计有效交易日数 vs 自然日跨度
            unique_dates = set()
            
            # 预先按日期分组每只股票的价格，确保风控检查时使用当天最新价格
            date_prices_map = {}
            for p in predictions:
                td = p.get('target_date')
                sym = p.get('symbol', '')
                ap = float(p.get('actual_price', 0))
                cp = float(p.get('current_price', 0))
                price = ap if ap > 0 else cp
                if td and sym and price > 0:
                    if td not in date_prices_map:
                        date_prices_map[td] = {}
                    date_prices_map[td][sym] = price
            
            for pred in predictions:
                symbol = pred.get('symbol', '')
                target_date = pred.get('target_date')
                prediction = pred.get('prediction', '震荡')
                up_prob = float(pred.get('up_probability', 0))
                confidence = float(pred.get('confidence', 0))
                current_price = float(pred.get('current_price', 0))
                actual_price = float(pred.get('actual_price', 0))
                
                if not symbol or not target_date or current_price <= 0:
                    continue
                
                unique_dates.add(str(target_date))
                
                # 更新最新市场价格（用于持仓估值）
                if actual_price > 0:
                    latest_prices[symbol] = actual_price
                elif current_price > 0:
                    latest_prices[symbol] = current_price
                
                # 日期切换：先对所有持仓做风控检查（止盈/止损/超时），再处理当天信号
                if target_date != current_date:
                    if current_date:
                        # 记录前一天的资产价值
                        total_value = self._calculate_portfolio_value(
                            capital, positions, latest_prices
                        )
                        daily_values.append({
                            'date': current_date,
                            'capital': round(capital, 2),
                            'positions_value': round(total_value - capital, 2),
                            'total_value': round(total_value, 2)
                        })
                    
                    current_date = target_date
                    processed_symbols_today = set()
                    
                    # 先用当天所有预测的价格更新latest_prices，再做风控
                    if current_date in date_prices_map:
                        latest_prices.update(date_prices_map[current_date])
                    
                    # 在新的一天开始时，检查所有持仓的止盈/止损/超时
                    capital = self._check_positions_for_sell(
                        positions, latest_prices, current_date, capital, trades,
                        stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                        stamp_tax_rate=stamp_tax_rate, commission_rate=commission_rate,
                        slippage_rate=slippage_rate, max_holding_days=max_holding_days,
                        exclude_symbols=processed_symbols_today
                    )
                
                # 确定交易价格：统一使用actual_price（目标日实际收盘价）
                trade_price = actual_price if actual_price > 0 else current_price
                
                # --- 交易决策逻辑 ---
                
                # 先检查是否持有该股票，如果持有，优先检查信号卖出
                if symbol in positions:
                    pos = positions[symbol]
                    cost_price = pos['cost_price']
                    sell_price = trade_price
                    profit_pct = (sell_price - cost_price) / cost_price * 100 if cost_price > 0 else 0
                    
                    should_sell = False
                    sell_reason = ''
                    
                    if prediction == '下跌' and up_prob <= sell_threshold:
                        should_sell = True
                        sell_reason = '预测下跌'
                    elif profit_pct >= take_profit_pct:
                        should_sell = True
                        sell_reason = '止盈'
                    elif profit_pct <= stop_loss_pct:
                        should_sell = True
                        sell_reason = '止损'
                    
                    if should_sell:
                        proceeds = self._sell_stock(
                            symbol, pos['shares'],
                            sell_price, stamp_tax_rate, commission_rate, slippage_rate
                        )
                        capital += proceeds
                        actual_profit = proceeds - pos['total_cost']
                        
                        trades.append({
                            'date': target_date,
                            'symbol': symbol,
                            'action': 'SELL',
                            'price': sell_price,
                            'shares': pos['shares'],
                            'cost_price': round(cost_price, 4),
                            'profit': round(actual_profit, 2),
                            'profit_pct': round(profit_pct, 2),
                            'reason': sell_reason,
                            'capital_after': round(capital, 2)
                        })
                        del positions[symbol]
                    
                    processed_symbols_today.add(symbol)
                
                # 买入条件：预测上涨且置信度足够，且当前未持有
                elif prediction == '上涨' and up_prob >= buy_threshold and confidence >= min_confidence:
                    if symbol not in positions:
                        shares, total_cost = self._buy_stock_with_max_position(
                            symbol, capital, trade_price, max_position_pct,
                            commission_rate, slippage_rate
                        )
                        if shares > 0:
                            per_share_cost = total_cost / shares
                            positions[symbol] = {
                                'shares': shares,
                                'cost_price': per_share_cost,
                                'total_cost': total_cost,
                                'buy_date': target_date
                            }
                            capital -= total_cost
                            trades.append({
                                'date': target_date,
                                'symbol': symbol,
                                'action': 'BUY',
                                'price': round(trade_price, 4),
                                'per_share_cost': round(per_share_cost, 4),
                                'shares': shares,
                                'capital_after': round(capital, 2)
                            })
                    
                    processed_symbols_today.add(symbol)
            
            # 记录最后一天的资产价值
            if current_date:
                total_value = self._calculate_portfolio_value(
                    capital, positions, latest_prices
                )
                daily_values.append({
                    'date': current_date,
                    'capital': round(capital, 2),
                    'positions_value': round(total_value - capital, 2),
                    'total_value': round(total_value, 2)
                })
            
            # 回测结束：强制平仓所有剩余持仓（标准回测实践）
            final_date = current_date or end_date
            capital = self._force_close_all(
                positions, latest_prices, final_date, capital, trades,
                stamp_tax_rate, commission_rate, slippage_rate
            )
            
            final_value = capital  # 全部平仓后，final_value 就是 capital
            
            # 计算回测指标
            metrics = self._calculate_metrics(
                initial_capital, final_value, daily_values, trades
            )
            
            # 计算覆盖密度信息
            total_natural_days = 0
            try:
                d1 = datetime.strptime(start_date, '%Y-%m-%d').date()
                d2 = datetime.strptime(end_date, '%Y-%m-%d').date()
                total_natural_days = (d2 - d1).days + 1
            except Exception:
                total_natural_days = len(unique_dates)
            
            return {
                'success': True,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'final_value': round(final_value, 2),
                'total_return': round((final_value - initial_capital) / initial_capital * 100, 2),
                'trades_count': len(trades),
                'win_trades': sum(1 for t in trades if t.get('action') == 'SELL' and t.get('profit', 0) > 0),
                'loss_trades': sum(1 for t in trades if t.get('action') == 'SELL' and t.get('profit', 0) <= 0),
                'parameters': tp,  # 返回实际使用的交易参数
                'metrics': metrics,
                'trades': trades[-50:] if len(trades) > 50 else trades,
                'daily_values': daily_values[-60:] if len(daily_values) > 60 else daily_values,
                'data_coverage': {
                    'trading_days_with_data': len(unique_dates),
                    'total_natural_days': total_natural_days,
                    'coverage_ratio': round(len(unique_dates) / max(total_natural_days, 1) * 100, 1)
                }
            }
            
        except Exception as e:
            self.logger.error(f"回测失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'回测失败: {str(e)}'
            }
    
    def backtest_with_parameters(self, start_date: str, end_date: str,
                                 parameters: Dict,
                                 initial_capital: float = 100000.0) -> Dict:
        """
        使用指定参数回测
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            parameters: 参数字典，可以包含：
                - buy_threshold: 买入阈值（上涨概率，默认0.6）
                - sell_threshold: 卖出阈值（下跌概率，默认0.4）
                - min_confidence: 最小置信度（默认0.55）
                - stop_loss_pct: 止损百分比（默认-5.0）
                - take_profit_pct: 止盈百分比（默认8.0）
                - max_position_pct: 单只股票最大仓位（默认0.3）
                - max_holding_days: 最大持仓天数（默认10）
            initial_capital: 初始资金
            
        Returns:
            回测结果字典
        """
        # 提取参数（使用默认值）
        buy_threshold = parameters.get('buy_threshold', 0.6)
        sell_threshold = parameters.get('sell_threshold', 0.4)
        min_confidence = parameters.get('min_confidence', 0.55)
        stop_loss_pct = parameters.get('stop_loss_pct', -5.0)
        take_profit_pct = parameters.get('take_profit_pct', 8.0)
        max_position_pct = parameters.get('max_position_pct', 0.3)
        max_holding_days = parameters.get('max_holding_days', self.MAX_HOLDING_DAYS)
        
        # 费率
        commission_rate = 0.0003
        stamp_tax_rate = 0.001
        slippage_rate = 0.001
        
        try:
            predictions = self._get_predictions(start_date, end_date)
            
            if not predictions:
                return {
                    'success': False,
                    'message': f'没有找到 {start_date} 到 {end_date} 期间的预测记录'
                }
            
            # 模拟交易（使用参数化的策略）
            capital = initial_capital
            positions = {}
            trades = []
            daily_values = []
            latest_prices = {}
            
            current_date = None
            processed_symbols_today = set()
            unique_dates = set()
            
            # 预先按日期分组价格，确保风控检查使用当天价格
            date_prices_map = {}
            for p in predictions:
                td = p.get('target_date')
                sym = p.get('symbol', '')
                ap = float(p.get('actual_price', 0))
                cp = float(p.get('current_price', 0))
                price = ap if ap > 0 else cp
                if td and sym and price > 0:
                    if td not in date_prices_map:
                        date_prices_map[td] = {}
                    date_prices_map[td][sym] = price
            
            for pred in predictions:
                symbol = pred.get('symbol', '')
                target_date = pred.get('target_date')
                prediction = pred.get('prediction', '震荡')
                up_prob = float(pred.get('up_probability', 0))
                confidence = float(pred.get('confidence', 0))
                current_price = float(pred.get('current_price', 0))
                actual_price = float(pred.get('actual_price', 0))
                
                if not symbol or not target_date or current_price <= 0:
                    continue
                
                unique_dates.add(str(target_date))
                
                # 更新最新市场价格
                if actual_price > 0:
                    latest_prices[symbol] = actual_price
                elif current_price > 0:
                    latest_prices[symbol] = current_price
                
                # 日期切换
                if target_date != current_date:
                    if current_date:
                        total_value = self._calculate_portfolio_value(
                            capital, positions, latest_prices
                        )
                        daily_values.append({
                            'date': current_date,
                            'capital': round(capital, 2),
                            'positions_value': round(total_value - capital, 2),
                            'total_value': round(total_value, 2)
                        })
                    
                    current_date = target_date
                    processed_symbols_today = set()
                    
                    # 先用当天所有预测的价格更新latest_prices，再做风控
                    if current_date in date_prices_map:
                        latest_prices.update(date_prices_map[current_date])
                    
                    # 在新的一天开始时，检查所有持仓的止盈/止损/超时
                    capital = self._check_positions_for_sell(
                        positions, latest_prices, current_date, capital, trades,
                        stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                        stamp_tax_rate=stamp_tax_rate, commission_rate=commission_rate,
                        slippage_rate=slippage_rate, max_holding_days=max_holding_days,
                        exclude_symbols=processed_symbols_today
                    )
                
                # 交易价格：统一使用 actual_price
                trade_price = actual_price if actual_price > 0 else current_price
                
                # --- 交易决策 ---
                
                # 先检查持仓卖出（信号驱动）
                if symbol in positions:
                    pos = positions[symbol]
                    cost_price = pos['cost_price']
                    sell_price = trade_price
                    profit_pct = (sell_price - cost_price) / cost_price * 100 if cost_price > 0 else 0
                    
                    should_sell = False
                    sell_reason = ''
                    
                    if prediction == '下跌' and up_prob <= sell_threshold:
                        should_sell = True
                        sell_reason = '预测下跌'
                    elif profit_pct >= take_profit_pct:
                        should_sell = True
                        sell_reason = '止盈'
                    elif profit_pct <= stop_loss_pct:
                        should_sell = True
                        sell_reason = '止损'
                    
                    if should_sell:
                        proceeds = self._sell_stock(
                            symbol, pos['shares'],
                            sell_price, stamp_tax_rate, commission_rate, slippage_rate
                        )
                        capital += proceeds
                        actual_profit = proceeds - pos['total_cost']
                        
                        trades.append({
                            'date': target_date,
                            'symbol': symbol,
                            'action': 'SELL',
                            'price': sell_price,
                            'shares': pos['shares'],
                            'cost_price': round(cost_price, 4),
                            'profit': round(actual_profit, 2),
                            'profit_pct': round(profit_pct, 2),
                            'reason': sell_reason,
                            'capital_after': round(capital, 2)
                        })
                        del positions[symbol]
                    
                    processed_symbols_today.add(symbol)
                
                # 买入条件
                elif prediction == '上涨' and up_prob >= buy_threshold and confidence >= min_confidence:
                    if symbol not in positions:
                        shares, total_cost = self._buy_stock_with_max_position(
                            symbol, capital, trade_price, max_position_pct
                        )
                        if shares > 0:
                            per_share_cost = total_cost / shares
                            positions[symbol] = {
                                'shares': shares,
                                'cost_price': per_share_cost,
                                'total_cost': total_cost,
                                'buy_date': target_date
                            }
                            capital -= total_cost
                            trades.append({
                                'date': target_date,
                                'symbol': symbol,
                                'action': 'BUY',
                                'price': round(trade_price, 4),
                                'per_share_cost': round(per_share_cost, 4),
                                'shares': shares,
                                'capital_after': round(capital, 2)
                            })
                    
                    processed_symbols_today.add(symbol)
            
            # 记录最后一天的资产价值
            if current_date:
                total_value = self._calculate_portfolio_value(
                    capital, positions, latest_prices
                )
                daily_values.append({
                    'date': current_date,
                    'capital': round(capital, 2),
                    'positions_value': round(total_value - capital, 2),
                    'total_value': round(total_value, 2)
                })
            
            # 回测结束：强制平仓所有剩余持仓
            final_date = current_date or end_date
            capital = self._force_close_all(
                positions, latest_prices, final_date, capital, trades,
                stamp_tax_rate, commission_rate, slippage_rate
            )
            
            final_value = capital
            
            # 计算回测指标
            metrics = self._calculate_metrics(
                initial_capital, final_value, daily_values, trades
            )
            
            # 覆盖密度
            total_natural_days = 0
            try:
                d1 = datetime.strptime(start_date, '%Y-%m-%d').date()
                d2 = datetime.strptime(end_date, '%Y-%m-%d').date()
                total_natural_days = (d2 - d1).days + 1
            except Exception:
                total_natural_days = len(unique_dates)
            
            return {
                'success': True,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'final_value': round(final_value, 2),
                'total_return': round((final_value - initial_capital) / initial_capital * 100, 2),
                'trades_count': len(trades),
                'win_trades': sum(1 for t in trades if t.get('action') == 'SELL' and t.get('profit', 0) > 0),
                'loss_trades': sum(1 for t in trades if t.get('action') == 'SELL' and t.get('profit', 0) <= 0),
                'parameters': parameters,
                'metrics': metrics,
                'trades': trades[-50:] if len(trades) > 50 else trades,
                'daily_values': daily_values[-60:] if len(daily_values) > 60 else daily_values,
                'data_coverage': {
                    'trading_days_with_data': len(unique_dates),
                    'total_natural_days': total_natural_days,
                    'coverage_ratio': round(len(unique_dates) / max(total_natural_days, 1) * 100, 1)
                }
            }
            
        except Exception as e:
            self.logger.error(f"参数回测失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'参数回测失败: {str(e)}'
            }
    
    def _buy_stock_with_max_position(self, symbol: str, available_capital: float, price: float,
                                     max_position_pct: float = 0.3,
                                     commission_rate: float = 0.0003,
                                     slippage_rate: float = 0.001) -> Tuple[int, float]:
        """买入股票（使用参数化的最大仓位）"""
        # 考虑滑点
        buy_price = price * (1 + slippage_rate)
        
        # 单只股票最多使用max_position_pct的资金
        max_investment = available_capital * max_position_pct
        
        # 计算可买入股数（100股为1手）
        shares = int((max_investment / buy_price) / 100) * 100
        
        if shares < 100:
            return 0, 0.0
        
        # 计算总成本（含佣金）
        cost = shares * buy_price * (1 + commission_rate)
        
        return shares, cost
    
    def _buy_stock(self, symbol: str, available_capital: float, price: float,
                   commission_rate: float, slippage_rate: float) -> Tuple[int, float]:
        """买入股票"""
        # 考虑滑点
        buy_price = price * (1 + slippage_rate)
        
        # 单只股票最多使用30%的资金
        max_investment = available_capital * 0.3
        
        # 计算可买入股数（100股为1手）
        shares = int((max_investment / buy_price) / 100) * 100
        
        if shares < 100:
            return 0, 0.0
        
        # 计算总成本（含佣金）
        cost = shares * buy_price * (1 + commission_rate)
        
        return shares, cost
    
    def _sell_stock(self, symbol: str, shares: int, price: float,
                    stamp_tax_rate: float, commission_rate: float,
                    slippage_rate: float) -> float:
        """卖出股票"""
        # 考虑滑点
        sell_price = price * (1 - slippage_rate)
        
        # 计算总收入（扣除印花税和佣金）
        proceeds = shares * sell_price * (1 - stamp_tax_rate - commission_rate)
        
        return proceeds
    
    def _calculate_portfolio_value(self, cash: float, positions: Dict,
                                  latest_prices: dict = None) -> float:
        """
        计算投资组合总价值
        
        Args:
            cash: 可用现金
            positions: 持仓字典
            latest_prices: 最新市场价格字典 {symbol: price}，用于实时估值
                          如果传入的不是dict（如传了date字符串），则退化为使用成本价
        """
        total_value = cash
        
        # 兼容旧的调用方式：如果传入的不是字典，退化为使用成本价
        if not isinstance(latest_prices, dict):
            latest_prices = {}
        
        for symbol, pos in positions.items():
            # 优先使用最新市场价格，没有则使用成本价
            market_price = latest_prices.get(symbol, pos['cost_price'])
            total_value += pos['shares'] * market_price
        return total_value
    
    def _calculate_metrics(self, initial_capital: float, final_value: float,
                          daily_values: List[Dict], trades: List[Dict]) -> Dict:
        """计算回测指标"""
        # 总收益率
        total_return = (final_value - initial_capital) / initial_capital
        
        # 计算年化收益率（假设回测期为N天）
        if daily_values:
            days = len(daily_values)
            if days > 0:
                annual_return = (1 + total_return) ** (365 / days) - 1
            else:
                annual_return = 0.0
        else:
            annual_return = 0.0
        
        # 计算最大回撤
        max_drawdown = 0.0
        if daily_values:
            peak = initial_capital
            for dv in daily_values:
                value = dv.get('total_value', initial_capital)
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        # 计算胜率
        sell_trades = [t for t in trades if t.get('action') == 'SELL']
        if sell_trades:
            win_count = sum(1 for t in sell_trades if t.get('profit', 0) > 0)
            win_rate = win_count / len(sell_trades)
        else:
            win_rate = 0.0
        
        # 计算盈亏比
        if sell_trades:
            profits = [t.get('profit', 0) for t in sell_trades if t.get('profit', 0) > 0]
            losses = [abs(t.get('profit', 0)) for t in sell_trades if t.get('profit', 0) < 0]
            
            avg_profit = sum(profits) / len(profits) if profits else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        else:
            profit_loss_ratio = 0.0
        
        # 计算夏普比率：从 daily_values 构造日收益率序列，Sharpe = (μ/σ) × √252
        sharpe_ratio = 0.0
        if daily_values and len(daily_values) >= 2:
            values = [initial_capital] + [dv.get('total_value', initial_capital) for dv in daily_values]
            daily_returns = []
            for i in range(1, len(values)):
                if values[i - 1] > 0:
                    r = (values[i] - values[i - 1]) / values[i - 1]
                    daily_returns.append(r)
            if daily_returns:
                mean_r = sum(daily_returns) / len(daily_returns)
                var_r = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
                std_r = var_r ** 0.5
                if std_r > 1e-10:
                    sharpe_ratio = (mean_r - 0) / std_r * (252 ** 0.5)  # 年化，无风险利率取0
        
        return {
            'total_return': round(total_return * 100, 2),
            'annual_return': round(annual_return * 100, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'win_rate': round(win_rate * 100, 2),
            'profit_loss_ratio': round(profit_loss_ratio, 2),
            'sharpe_ratio': round(sharpe_ratio, 2)
        }


if __name__ == '__main__':
    # 测试代码
    engine = BacktestEngine()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    print("=" * 60)
    print("测试回测引擎")
    print("=" * 60)
    result = engine.backtest_predictions(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
