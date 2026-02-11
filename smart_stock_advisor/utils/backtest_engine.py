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
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
    
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
            # 查询预测记录
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
            
            predictions = self.db.execute_query(sql, (start_date, end_date))
            
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
            daily_capital = capital
            
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
                
                # 更新最新市场价格（用于持仓估值）
                if actual_price > 0:
                    latest_prices[symbol] = actual_price
                elif current_price > 0:
                    latest_prices[symbol] = current_price
                
                # 更新日期
                if target_date != current_date:
                    if current_date:
                        # 计算当日资产价值（使用最新市场价格）
                        total_value = self._calculate_portfolio_value(
                            capital, positions, latest_prices
                        )
                        daily_values.append({
                            'date': current_date,
                            'capital': capital,
                            'positions_value': total_value - capital,
                            'total_value': total_value
                        })
                    current_date = target_date
                
                # 交易决策逻辑
                # 买入条件：预测上涨且置信度足够
                if prediction == '上涨' and up_prob >= PROBABILITY_THRESHOLDS["buy_signal"] and confidence >= CONFIDENCE_THRESHOLDS["medium"]:
                    if symbol not in positions:
                        # 买入
                        shares, total_cost = self._buy_stock(
                            symbol, capital, current_price,
                            commission_rate, slippage_rate
                        )
                        if shares > 0:
                            # 每股成本价 = 总成本 / 股数
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
                                'price': per_share_cost,
                                'shares': shares,
                                'capital_after': capital
                            })
                
                # 卖出条件：预测下跌或持仓盈利达到目标
                elif symbol in positions:
                    pos = positions[symbol]
                    cost_price = pos['cost_price']  # 每股成本价
                    # 使用actual_price（目标日实际价格）计算利润
                    sell_price = actual_price if actual_price > 0 else current_price
                    profit_pct = (sell_price - cost_price) / cost_price * 100 if cost_price > 0 else 0
                    
                    # 预测下跌或达到止盈/止损
                    should_sell = False
                    sell_reason = ''
                    
                    if prediction == '下跌' and up_prob <= 0.4:
                        should_sell = True
                        sell_reason = '预测下跌'
                    elif profit_pct >= 8.0:  # 止盈
                        should_sell = True
                        sell_reason = '止盈'
                    elif profit_pct <= -5.0:  # 止损
                        should_sell = True
                        sell_reason = '止损'
                    
                    if should_sell:
                        # 卖出
                        proceeds = self._sell_stock(
                            symbol, pos['shares'],
                            sell_price, stamp_tax_rate, commission_rate, slippage_rate
                        )
                        capital += proceeds
                        
                        # 利润 = 卖出所得 - 买入总成本
                        actual_profit = proceeds - pos['total_cost']
                        
                        trades.append({
                            'date': target_date,
                            'symbol': symbol,
                            'action': 'SELL',
                            'price': sell_price,
                            'shares': pos['shares'],
                            'cost_price': cost_price,
                            'profit': round(actual_profit, 2),
                            'profit_pct': round(profit_pct, 2),
                            'reason': sell_reason,
                            'capital_after': capital
                        })
                        
                        del positions[symbol]
            
            # 计算最终资产价值（使用最新市场价格估值未平仓头寸）
            final_date = predictions[-1].get('target_date') if predictions else end_date
            final_value = self._calculate_portfolio_value(
                capital, positions, latest_prices
            )
            
            # 计算回测指标
            metrics = self._calculate_metrics(
                initial_capital, final_value, daily_values, trades
            )
            
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
                'metrics': metrics,
                'trades': trades[-20:] if len(trades) > 20 else trades,  # 只返回最后20笔交易
                'daily_values': daily_values[-30:] if len(daily_values) > 30 else daily_values  # 只返回最后30天
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
        
        try:
            # 查询预测记录（与backtest_predictions相同）
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
            
            predictions = self.db.execute_query(sql, (start_date, end_date))
            
            if not predictions:
                return {
                    'success': False,
                    'message': f'没有找到 {start_date} 到 {end_date} 期间的预测记录'
                }
            
            # 模拟交易（使用参数化的策略）
            capital = initial_capital
            positions = {}  # {symbol: {'shares': int, 'cost_price': float, 'total_cost': float, 'buy_date': str}}
            trades = []  # 交易记录
            daily_values = []  # 每日资产价值
            latest_prices = {}  # 跟踪每只股票最新市场价格
            
            current_date = None
            
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
                
                # 更新最新市场价格（用于持仓估值）
                if actual_price > 0:
                    latest_prices[symbol] = actual_price
                elif current_price > 0:
                    latest_prices[symbol] = current_price
                
                # 更新日期
                if target_date != current_date:
                    if current_date:
                        # 使用实际市价计算当日资产价值
                        total_value = self._calculate_portfolio_value(
                            capital, positions, latest_prices
                        )
                        daily_values.append({
                            'date': current_date,
                            'capital': capital,
                            'positions_value': total_value - capital,
                            'total_value': total_value
                        })
                    current_date = target_date
                
                # 确定交易价格：使用actual_price（目标日实际价格）
                trade_price = actual_price if actual_price > 0 else current_price
                
                # 交易决策逻辑（使用参数化的阈值）
                # 买入条件：预测上涨且上涨概率 >= buy_threshold 且置信度 >= min_confidence
                if prediction == '上涨' and up_prob >= buy_threshold and confidence >= min_confidence:
                    if symbol not in positions:
                        # 买入（使用参数化的最大仓位）
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
                                'price': trade_price,
                                'per_share_cost': round(per_share_cost, 4),
                                'shares': shares,
                                'capital_after': round(capital, 2)
                            })
                
                # 卖出条件：预测下跌或达到止盈/止损
                elif symbol in positions:
                    pos = positions[symbol]
                    cost_price = pos['cost_price']  # 每股成本价
                    sell_price = actual_price if actual_price > 0 else current_price
                    profit_pct = (sell_price - cost_price) / cost_price * 100 if cost_price > 0 else 0
                    
                    # 预测下跌或达到止盈/止损（使用参数化的阈值）
                    should_sell = False
                    sell_reason = ''
                    
                    if prediction == '下跌' and up_prob <= sell_threshold:
                        should_sell = True
                        sell_reason = '预测下跌'
                    elif profit_pct >= take_profit_pct:  # 止盈
                        should_sell = True
                        sell_reason = '止盈'
                    elif profit_pct <= stop_loss_pct:  # 止损
                        should_sell = True
                        sell_reason = '止损'
                    
                    if should_sell:
                        # 卖出
                        sell_shares = pos['shares']
                        proceeds = self._sell_stock(
                            symbol, sell_shares,
                            sell_price, 0.001, 0.0003, 0.001  # 印花税、佣金、滑点
                        )
                        capital += proceeds
                        
                        # 正确计算利润：卖出所得 - 买入总成本
                        actual_profit = proceeds - pos['total_cost']
                        
                        trades.append({
                            'date': target_date,
                            'symbol': symbol,
                            'action': 'SELL',
                            'price': sell_price,
                            'shares': sell_shares,
                            'cost_price': round(cost_price, 4),
                            'profit': round(actual_profit, 2),
                            'profit_pct': round(profit_pct, 2),
                            'reason': sell_reason,
                            'capital_after': round(capital, 2)
                        })
                        
                        del positions[symbol]
            
            # 计算最终资产价值（使用最新市场价格）
            final_value = self._calculate_portfolio_value(
                capital, positions, latest_prices
            )
            
            # 计算回测指标
            metrics = self._calculate_metrics(
                initial_capital, final_value, daily_values, trades
            )
            
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
                'parameters': parameters,  # 记录使用的参数
                'metrics': metrics,
                'trades': trades[-20:] if len(trades) > 20 else trades,
                'daily_values': daily_values[-30:] if len(daily_values) > 30 else daily_values
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
