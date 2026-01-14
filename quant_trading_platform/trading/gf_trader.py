"""
广发证券交易接口
需要安装: pip install gf-api-client
需要申请广发证券API权限并获取API密钥
"""
from typing import Dict, Optional
from datetime import datetime
from .base_trader import BaseTrader
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    from gf_api_client import GFAPIClient
    GF_API_AVAILABLE = True
except ImportError:
    GF_API_AVAILABLE = False
    logger.warning("gf-api-client未安装，请运行: pip install gf-api-client")


class GFTrader(BaseTrader):
    """广发证券交易接口"""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        app_id: str,
        base_url: str = "https://openapi.gf.com.cn"
    ):
        """
        初始化广发证券交易接口
        
        Args:
            api_key: API密钥
            api_secret: API密钥
            app_id: 应用ID
            base_url: API基础URL
        """
        if not GF_API_AVAILABLE:
            raise ImportError("请先安装gf-api-client: pip install gf-api-client")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.app_id = app_id
        self.base_url = base_url
        self.logger = logger
        
        # 初始化广发证券API客户端
        try:
            self.client = GFAPIClient(
                api_key=api_key,
                api_secret=api_secret,
                app_id=app_id,
                base_url=base_url
            )
            self.logger.info("广发证券API客户端初始化成功")
        except Exception as e:
            self.logger.error(f"广发证券API客户端初始化失败: {str(e)}")
            raise
    
    def _convert_symbol(self, symbol: str) -> str:
        """
        转换股票代码格式
        广发证券API可能需要特定的代码格式
        """
        # 上海股票: 600xxx -> sh600xxx 或 600xxx.SH
        # 深圳股票: 000xxx/002xxx/300xxx -> sz000xxx 或 000xxx.SZ
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        elif symbol.startswith(('0', '3')):
            return f"{symbol}.SZ"
        else:
            return symbol
    
    def buy(self, symbol: str, amount: float, price: Optional[float] = None) -> Dict:
        """
        买入股票
        
        Args:
            symbol: 股票代码（如：600519）
            amount: 买入金额（元）
            price: 买入价格，如果为None则使用市价
            
        Returns:
            交易结果字典
        """
        try:
            # 转换代码格式
            code = self._convert_symbol(symbol)
            
            # 确定订单类型：限价单或市价单
            order_type = "LIMIT" if price else "MARKET"
            
            # 计算买入数量（A股以100股为单位）
            if price:
                shares = int(amount / price / 100) * 100
                order_price = price
            else:
                # 市价单，先获取当前价格估算
                current_price = self.get_current_price(symbol)
                if current_price:
                    shares = int(amount / current_price / 100) * 100
                    order_price = None
                else:
                    return {'success': False, 'message': '无法获取当前价格'}
            
            if shares <= 0:
                return {'success': False, 'message': '买入金额不足'}
            
            # 调用广发证券API下单
            # 注意：以下代码需要根据实际的gf-api-client接口调整
            order_params = {
                'symbol': code,
                'side': 'BUY',  # 买入
                'type': order_type,
                'quantity': shares,
                'amount': amount if order_type == 'MARKET' else None,
                'price': order_price
            }
            
            # 执行下单（需要根据实际API调整）
            response = self.client.place_order(**order_params)
            
            if response and response.get('success'):
                self.logger.info(f"买入成功: {symbol} {shares}股")
                return {
                    'success': True,
                    'symbol': symbol,
                    'shares': shares,
                    'price': order_price or response.get('price'),
                    'amount': amount,
                    'order_id': response.get('order_id'),
                    'message': '买入成功'
                }
            else:
                error_msg = response.get('message', '买入失败') if response else 'API调用失败'
                self.logger.error(f"买入失败: {error_msg}")
                return {'success': False, 'message': error_msg}
                
        except Exception as e:
            self.logger.error(f"买入股票时出错: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def sell(self, symbol: str, shares: int, price: Optional[float] = None) -> Dict:
        """
        卖出股票
        
        Args:
            symbol: 股票代码
            shares: 卖出股数
            price: 卖出价格，如果为None则使用市价
            
        Returns:
            交易结果字典
        """
        try:
            # 转换代码格式
            code = self._convert_symbol(symbol)
            
            # 确定订单类型
            order_type = "LIMIT" if price else "MARKET"
            
            # 调用广发证券API下单
            order_params = {
                'symbol': code,
                'side': 'SELL',  # 卖出
                'type': order_type,
                'quantity': shares,
                'price': price
            }
            
            # 执行下单
            response = self.client.place_order(**order_params)
            
            if response and response.get('success'):
                self.logger.info(f"卖出成功: {symbol} {shares}股")
                return {
                    'success': True,
                    'symbol': symbol,
                    'shares': shares,
                    'price': price or response.get('price'),
                    'amount': shares * (price or response.get('price', 0)),
                    'order_id': response.get('order_id'),
                    'message': '卖出成功'
                }
            else:
                error_msg = response.get('message', '卖出失败') if response else 'API调用失败'
                self.logger.error(f"卖出失败: {error_msg}")
                return {'success': False, 'message': error_msg}
                
        except Exception as e:
            self.logger.error(f"卖出股票时出错: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def get_position(self, symbol: str) -> Dict:
        """
        获取持仓信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            持仓信息字典
        """
        try:
            code = self._convert_symbol(symbol)
            
            # 调用广发证券API查询持仓
            positions = self.client.get_positions()
            
            # 查找对应股票的持仓
            for pos in positions:
                if pos.get('symbol') == code or pos.get('code') == symbol:
                    return {
                        'symbol': symbol,
                        'shares': int(pos.get('quantity', 0)),
                        'cost': float(pos.get('cost_price', 0)),
                        'market_price': float(pos.get('current_price', 0)),
                        'market_value': float(pos.get('market_value', 0)),
                        'profit': float(pos.get('profit', 0)),
                        'profit_pct': float(pos.get('profit_rate', 0))
                    }
            
            # 没有持仓
            return {
                'symbol': symbol,
                'shares': 0,
                'cost': 0,
                'market_price': self.get_current_price(symbol),
                'market_value': 0,
                'profit': 0,
                'profit_pct': 0
            }
            
        except Exception as e:
            self.logger.error(f"查询持仓时出错: {str(e)}")
            return {
                'symbol': symbol,
                'shares': 0,
                'cost': 0,
                'market_price': 0,
                'market_value': 0,
                'profit': 0,
                'profit_pct': 0
            }
    
    def get_balance(self) -> Dict:
        """
        获取账户余额
        
        Returns:
            账户信息字典
        """
        try:
            # 调用广发证券API查询账户信息
            account_info = self.client.get_account_info()
            
            return {
                'cash': float(account_info.get('available_cash', 0)),
                'total_asset': float(account_info.get('total_asset', 0)),
                'positions_value': float(account_info.get('market_value', 0)),
                'total_value': float(account_info.get('total_asset', 0))
            }
            
        except Exception as e:
            self.logger.error(f"查询账户余额时出错: {str(e)}")
            return {
                'cash': 0,
                'total_asset': 0,
                'positions_value': 0,
                'total_value': 0
            }
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            当前价格
        """
        try:
            code = self._convert_symbol(symbol)
            
            # 调用广发证券API获取行情
            quote = self.client.get_quote(code)
            
            if quote:
                return float(quote.get('last_price', 0))
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取价格时出错: {str(e)}")
            return None

