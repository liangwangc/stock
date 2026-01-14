"""
交易成本管理模块
实现精确交易成本计算、交易频率限制、交易成本统计和分析、交易记录管理
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection, USE_DATABASE
from utils.logger import get_logger

logger = get_logger(__name__)


class TradingCostManager:
    """交易成本管理器"""
    
    def __init__(self):
        self.db = DatabaseConnection() if USE_DATABASE else None
        self.logger = logger
        
        # 默认券商费率配置（可扩展支持多个券商）
        self.default_broker_config = {
            'commission_rate': 0.0003,      # 佣金费率（万分之3）
            'stamp_tax_rate': 0.001,        # 印花税（千分之1，仅卖出收取）
            'transfer_fee_rate': 0.00002,   # 过户费（万分之0.2）
            'min_commission': 5.0,          # 最低佣金（元）
            'name': '默认券商'
        }
    
    def calculate_trading_cost(
        self,
        symbol: str,
        price: float,
        quantity: int,
        direction: str,  # 'buy' 或 'sell'
        broker_config: Optional[Dict] = None,
        slippage_rate: float = 0.001
    ) -> Dict:
        """
        精确计算交易成本（考虑不同券商费率）
        
        Args:
            symbol: 股票代码
            price: 交易价格（元）
            quantity: 交易数量（股）
            direction: 交易方向（'buy' 或 'sell'）
            broker_config: 券商费率配置（可选，使用默认配置）
            slippage_rate: 滑点率（默认0.1%）
        
        Returns:
            交易成本详情，包含：
                - total_amount: 总金额（元）
                - commission: 佣金（元）
                - stamp_tax: 印花税（元，仅卖出）
                - transfer_fee: 过户费（元）
                - slippage_cost: 滑点成本（元）
                - total_cost: 总成本（元）
                - cost_rate: 成本率（%）
                - details: 详细说明
        """
        try:
            if broker_config is None:
                broker_config = self.default_broker_config
            
            # 计算总金额
            total_amount = price * quantity
            
            # 计算滑点成本
            slippage_cost = total_amount * slippage_rate
            
            # 计算佣金（买入和卖出都收取）
            commission_rate = broker_config.get('commission_rate', 0.0003)
            commission = total_amount * commission_rate
            min_commission = broker_config.get('min_commission', 5.0)
            commission = max(commission, min_commission)
            
            # 计算印花税（仅卖出收取）
            stamp_tax = 0.0
            if direction.lower() == 'sell':
                stamp_tax_rate = broker_config.get('stamp_tax_rate', 0.001)
                stamp_tax = total_amount * stamp_tax_rate
            
            # 计算过户费（买入和卖出都收取）
            transfer_fee_rate = broker_config.get('transfer_fee_rate', 0.00002)
            transfer_fee = total_amount * transfer_fee_rate
            
            # 计算总成本
            total_cost = commission + stamp_tax + transfer_fee + slippage_cost
            cost_rate = (total_cost / total_amount) * 100 if total_amount > 0 else 0.0
            
            # 生成详细说明
            details = []
            details.append(f"交易金额: {total_amount:.2f}元")
            details.append(f"佣金: {commission:.2f}元（费率{commission_rate:.4%}，最低{min_commission:.2f}元）")
            if direction.lower() == 'sell':
                details.append(f"印花税: {stamp_tax:.2f}元（费率{broker_config.get('stamp_tax_rate', 0.001):.4%}，仅卖出）")
            else:
                details.append(f"印花税: 0元（仅卖出收取）")
            details.append(f"过户费: {transfer_fee:.2f}元（费率{transfer_fee_rate:.4%}）")
            details.append(f"滑点成本: {slippage_cost:.2f}元（费率{slippage_rate:.4%}）")
            details.append(f"总成本: {total_cost:.2f}元（成本率{cost_rate:.4f}%）")
            
            return {
                'symbol': symbol,
                'direction': direction,
                'price': price,
                'quantity': quantity,
                'total_amount': round(total_amount, 2),
                'commission': round(commission, 2),
                'stamp_tax': round(stamp_tax, 2),
                'transfer_fee': round(transfer_fee, 2),
                'slippage_cost': round(slippage_cost, 2),
                'total_cost': round(total_cost, 2),
                'cost_rate': round(cost_rate, 4),
                'broker_config': broker_config.get('name', '默认券商'),
                'details': details
            }
            
        except Exception as e:
            self.logger.error(f"计算交易成本失败: {str(e)}")
            return {
                'symbol': symbol,
                'direction': direction,
                'error': str(e),
                'total_cost': 0.0,
                'cost_rate': 0.0
            }
    
    def record_trading_transaction(
        self,
        symbol: str,
        direction: str,
        price: float,
        quantity: int,
        trading_date: Optional[datetime] = None,
        broker_config: Optional[Dict] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """
        记录交易记录（用于真实交易后手动录入）
        
        Args:
            symbol: 股票代码
            direction: 交易方向（'buy' 或 'sell'）
            price: 交易价格（元）
            quantity: 交易数量（股）
            trading_date: 交易日期（可选，默认当前时间）
            broker_config: 券商费率配置（可选）
            notes: 备注（可选）
        
        Returns:
            交易记录结果，包含：
                - success: 是否成功
                - transaction_id: 交易记录ID
                - cost_details: 成本详情
        """
        try:
            if not self.db:
                return {
                    'success': False,
                    'message': '数据库不可用，无法保存交易记录'
                }
            
            if trading_date is None:
                trading_date = datetime.now()
            
            # 计算交易成本
            cost_details = self.calculate_trading_cost(
                symbol=symbol,
                price=price,
                quantity=quantity,
                direction=direction,
                broker_config=broker_config
            )
            
            if 'error' in cost_details:
                return {
                    'success': False,
                    'message': f"计算交易成本失败: {cost_details['error']}"
                }
            
            # 保存到数据库
            date_str = trading_date.strftime('%Y-%m-%d')
            timestamp_str = trading_date.strftime('%Y-%m-%d %H:%M:%S')
            
            sql = """
                INSERT INTO trading_transactions 
                (symbol, direction, price, quantity, total_amount, trading_date, trading_time,
                 commission, stamp_tax, transfer_fee, slippage_cost, total_cost, cost_rate,
                 broker_name, notes, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            params = (
                symbol,
                direction.upper(),
                price,
                quantity,
                cost_details['total_amount'],
                date_str,
                timestamp_str,
                cost_details['commission'],
                cost_details['stamp_tax'],
                cost_details['transfer_fee'],
                cost_details['slippage_cost'],
                cost_details['total_cost'],
                cost_details['cost_rate'],
                cost_details['broker_config'],
                notes
            )
            
            # 执行插入并获取插入ID
            conn = self.db.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                transaction_id = cursor.lastrowid
                conn.commit()
                cursor.close()
            else:
                transaction_id = None
            
            if transaction_id:
                self.logger.info(f"交易记录已保存: {symbol} {direction} {quantity}股 @ {price}元, ID={transaction_id}")
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'cost_details': cost_details,
                    'message': '交易记录保存成功'
                }
            else:
                return {
                    'success': False,
                    'message': '保存交易记录失败'
                }
                
        except Exception as e:
            self.logger.error(f"记录交易失败: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def check_trading_frequency(
        self,
        symbol: str,
        direction: str,
        days: int = 7,
        max_trades: int = 3
    ) -> Dict:
        """
        检查交易频率限制（避免过度交易）
        
        Args:
            symbol: 股票代码
            direction: 交易方向（'buy' 或 'sell'）
            days: 检查天数（默认7天）
            max_trades: 最大交易次数（默认3次）
        
        Returns:
            交易频率检查结果，包含：
                - allowed: 是否允许交易
                - recent_trades: 近期交易次数
                - limit: 交易次数限制
                - warning: 警告信息（如果有）
        """
        try:
            if not self.db:
                return {
                    'allowed': True,
                    'message': '数据库不可用，无法检查交易频率',
                    'recent_trades': 0,
                    'limit': max_trades
                }
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 查询近期交易次数
            sql = """
                SELECT COUNT(*) as trade_count
                FROM trading_transactions
                WHERE symbol = %s
                  AND direction = %s
                  AND trading_date >= %s
                  AND trading_date <= %s
            """
            
            results = self.db.execute_query(sql, (symbol, direction.upper(), start_date, end_date))
            
            if results and len(results) > 0:
                recent_trades = results[0].get('trade_count', 0)
            else:
                recent_trades = 0
            
            allowed = recent_trades < max_trades
            warning = None
            
            if not allowed:
                warning = f"交易频率过高：{days}天内已交易{recent_trades}次（限制{max_trades}次），建议减少交易频率"
            
            elif recent_trades >= max_trades * 0.8:
                warning = f"交易频率接近限制：{days}天内已交易{recent_trades}次（限制{max_trades}次），请注意控制交易频率"
            
            return {
                'allowed': allowed,
                'recent_trades': recent_trades,
                'limit': max_trades,
                'check_period_days': days,
                'warning': warning,
                'message': f"{days}天内{direction.upper()}交易{recent_trades}次（限制{max_trades}次）"
            }
            
        except Exception as e:
            self.logger.error(f"检查交易频率失败: {str(e)}")
            return {
                'allowed': True,
                'message': f"检查失败，允许交易: {str(e)}",
                'recent_trades': 0,
                'limit': max_trades
            }
    
    def get_trading_cost_statistics(
        self,
        days: int = 30,
        symbol: Optional[str] = None
    ) -> Dict:
        """
        获取交易成本统计和分析
        
        Args:
            days: 统计天数（默认30天）
            symbol: 股票代码（可选，指定某只股票）
        
        Returns:
            交易成本统计结果，包含：
                - total_trades: 总交易次数
                - total_cost: 总成本
                - avg_cost_rate: 平均成本率
                - cost_by_direction: 按方向统计成本
                - cost_by_symbol: 按股票统计成本
                - cost_trend: 成本趋势
        """
        try:
            if not self.db:
                return {
                    'success': False,
                    'message': '数据库不可用，无法统计交易成本'
                }
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 基础查询
            base_sql = """
                SELECT 
                    symbol,
                    direction,
                    total_amount,
                    commission,
                    stamp_tax,
                    transfer_fee,
                    slippage_cost,
                    total_cost,
                    cost_rate,
                    trading_date
                FROM trading_transactions
                WHERE trading_date >= %s
                  AND trading_date <= %s
            """
            
            params = [start_date, end_date]
            
            if symbol:
                base_sql += " AND symbol = %s"
                params.append(symbol)
            
            base_sql += " ORDER BY trading_date DESC"
            
            results = self.db.execute_query(base_sql, params)
            
            if not results:
                return {
                    'success': True,
                    'total_trades': 0,
                    'message': f'没有找到 {days} 天内的交易记录',
                    'period_days': days,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                }
            
            # 统计总交易次数和总成本
            total_trades = len(results)
            total_cost = sum(float(r.get('total_cost', 0) or 0) for r in results)
            total_amount = sum(float(r.get('total_amount', 0) or 0) for r in results)
            avg_cost_rate = (total_cost / total_amount * 100) if total_amount > 0 else 0.0
            
            # 按方向统计
            cost_by_direction = {'BUY': {'count': 0, 'cost': 0.0, 'amount': 0.0},
                                'SELL': {'count': 0, 'cost': 0.0, 'amount': 0.0}}
            for r in results:
                direction = r.get('direction', 'UNKNOWN')
                if direction in cost_by_direction:
                    cost_by_direction[direction]['count'] += 1
                    cost_by_direction[direction]['cost'] += float(r.get('total_cost', 0) or 0)
                    cost_by_direction[direction]['amount'] += float(r.get('total_amount', 0) or 0)
            
            # 计算各方向的成本率
            for direction, stats in cost_by_direction.items():
                if stats['amount'] > 0:
                    stats['cost_rate'] = (stats['cost'] / stats['amount']) * 100
                else:
                    stats['cost_rate'] = 0.0
            
            # 按股票统计
            cost_by_symbol = {}
            for r in results:
                sym = r.get('symbol', '')
                if sym not in cost_by_symbol:
                    cost_by_symbol[sym] = {
                        'count': 0,
                        'buy_count': 0,
                        'sell_count': 0,
                        'cost': 0.0,
                        'amount': 0.0
                    }
                
                cost_by_symbol[sym]['count'] += 1
                if r.get('direction') == 'BUY':
                    cost_by_symbol[sym]['buy_count'] += 1
                elif r.get('direction') == 'SELL':
                    cost_by_symbol[sym]['sell_count'] += 1
                
                cost_by_symbol[sym]['cost'] += float(r.get('total_cost', 0) or 0)
                cost_by_symbol[sym]['amount'] += float(r.get('total_amount', 0) or 0)
            
            # 计算各股票的成本率
            for sym, stats in cost_by_symbol.items():
                if stats['amount'] > 0:
                    stats['cost_rate'] = (stats['cost'] / stats['amount']) * 100
                else:
                    stats['cost_rate'] = 0.0
            
            # 成本趋势（按日期统计）
            cost_trend = {}
            for r in results:
                date_str = r.get('trading_date').strftime('%Y-%m-%d') if hasattr(r.get('trading_date'), 'strftime') else str(r.get('trading_date'))
                if date_str not in cost_trend:
                    cost_trend[date_str] = {'count': 0, 'cost': 0.0}
                cost_trend[date_str]['count'] += 1
                cost_trend[date_str]['cost'] += float(r.get('total_cost', 0) or 0)
            
            # 成本组成分析
            total_commission = sum(float(r.get('commission', 0) or 0) for r in results)
            total_stamp_tax = sum(float(r.get('stamp_tax', 0) or 0) for r in results)
            total_transfer_fee = sum(float(r.get('transfer_fee', 0) or 0) for r in results)
            total_slippage = sum(float(r.get('slippage_cost', 0) or 0) for r in results)
            
            cost_breakdown = {
                'commission': {
                    'total': round(total_commission, 2),
                    'percentage': round((total_commission / total_cost * 100) if total_cost > 0 else 0, 2)
                },
                'stamp_tax': {
                    'total': round(total_stamp_tax, 2),
                    'percentage': round((total_stamp_tax / total_cost * 100) if total_cost > 0 else 0, 2)
                },
                'transfer_fee': {
                    'total': round(total_transfer_fee, 2),
                    'percentage': round((total_transfer_fee / total_cost * 100) if total_cost > 0 else 0, 2)
                },
                'slippage': {
                    'total': round(total_slippage, 2),
                    'percentage': round((total_slippage / total_cost * 100) if total_cost > 0 else 0, 2)
                }
            }
            
            return {
                'success': True,
                'period_days': days,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'symbol': symbol,
                'total_trades': total_trades,
                'total_cost': round(total_cost, 2),
                'total_amount': round(total_amount, 2),
                'avg_cost_rate': round(avg_cost_rate, 4),
                'cost_by_direction': {k: {
                    'count': v['count'],
                    'cost': round(v['cost'], 2),
                    'amount': round(v['amount'], 2),
                    'cost_rate': round(v.get('cost_rate', 0), 4)
                } for k, v in cost_by_direction.items()},
                'cost_by_symbol': {k: {
                    'count': v['count'],
                    'buy_count': v['buy_count'],
                    'sell_count': v['sell_count'],
                    'cost': round(v['cost'], 2),
                    'amount': round(v['amount'], 2),
                    'cost_rate': round(v.get('cost_rate', 0), 4)
                } for k, v in cost_by_symbol.items()},
                'cost_trend': cost_trend,
                'cost_breakdown': cost_breakdown
            }
            
        except Exception as e:
            self.logger.error(f"统计交易成本失败: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_transaction_history(
        self,
        symbol: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> Dict:
        """
        获取交易记录历史
        
        Args:
            symbol: 股票代码（可选）
            days: 查询天数（默认30天）
            limit: 返回记录数限制（默认100条）
        
        Returns:
            交易记录列表
        """
        try:
            if not self.db:
                return {
                    'success': False,
                    'message': '数据库不可用，无法查询交易记录'
                }
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            base_sql = """
                SELECT 
                    id, symbol, direction, price, quantity, total_amount,
                    trading_date, trading_time, commission, stamp_tax,
                    transfer_fee, slippage_cost, total_cost, cost_rate,
                    broker_name, notes, decision_id, created_at
                FROM trading_transactions
                WHERE trading_date >= %s
                  AND trading_date <= %s
            """
            
            params = [start_date, end_date]
            
            if symbol:
                base_sql += " AND symbol = %s"
                params.append(symbol)
            
            base_sql += " ORDER BY trading_time DESC LIMIT %s"
            params.append(limit)
            
            results = self.db.execute_query(base_sql, params)
            
            return {
                'success': True,
                'count': len(results) if results else 0,
                'transactions': results if results else []
            }
            
        except Exception as e:
            self.logger.error(f"查询交易记录失败: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'count': 0,
                'transactions': []
            }


# 全局实例
_cost_manager_instance = None

def get_trading_cost_manager() -> TradingCostManager:
    """获取交易成本管理器单例"""
    global _cost_manager_instance
    if _cost_manager_instance is None:
        _cost_manager_instance = TradingCostManager()
    return _cost_manager_instance
