"""
风险管理模块

本模块提供全面的风险管理功能，包括动态止损/止盈、组合风险控制、
仓位管理优化和风险限额管理。帮助交易系统在追求收益的同时有效控制风险。

主要功能：
- 动态止损/止盈：根据股票波动率动态调整止损和止盈比例
- 组合风险控制：计算组合相关性、HHI指数，评估组合风险
- 仓位管理优化：基于风险评分优化仓位分配
- 风险限额管理：检查和管理各种风险限额（单股、组合、总仓位等）

风险控制策略：
- 波动率调整：高波动率股票使用更宽的止损/止盈范围
- 相关性检查：避免持有高度相关的股票组合
- HHI指数：评估持仓集中度，避免过度集中
- 风险评分：综合考虑多个风险因素，给出风险评分

使用示例：
    ```python
    from utils.risk_manager import RiskManager
    
    risk_manager = RiskManager()
    
    # 计算动态止损/止盈
    stop_loss_info = risk_manager.calculate_dynamic_stop_loss_take_profit(
        symbol='000001',
        current_price=10.5
    )
    
    # 检查组合风险
    portfolio_risk = risk_manager.check_portfolio_risk(holdings)
    
    # 优化仓位分配
    optimized_positions = risk_manager.optimize_position_sizing(
        signals, risk_scores
    )
    ```

作者：Smart Stock Advisor Team
创建日期：2024
最后更新：2024
"""
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection, USE_DATABASE
from utils.logger import get_logger

logger = get_logger(__name__)


class RiskManager:
    """
    风险管理器
    
    提供全面的风险管理功能，帮助交易系统识别、评估和控制各种风险。
    
    主要功能模块：
    1. 动态止损/止盈：根据股票历史波动率动态调整止损和止盈比例
    2. 组合风险控制：评估持仓组合的整体风险（相关性、集中度等）
    3. 仓位管理优化：基于风险评分优化仓位分配，避免过度集中
    4. 风险限额管理：检查和管理各种风险限额，确保不超出风险承受能力
    
    风险指标：
    - 波动率：股票价格的历史波动程度
    - 相关性：股票之间的价格关联程度
    - HHI指数：持仓集中度指数（0-1，越高越集中）
    - 风险评分：综合多个风险因素的综合评分
    
    应用场景：
    - 交易前风险评估
    - 持仓组合风险监控
    - 仓位分配优化
    - 风险限额检查
    """
    
    def __init__(self):
        """
        初始化风险管理器
        
        初始化数据库连接和日志记录器。
        """
        self.db = DatabaseConnection() if USE_DATABASE else None
        self.logger = logger
    
    def calculate_dynamic_stop_loss_take_profit(
        self,
        symbol: str,
        current_price: float,
        stock_data: Optional[pd.DataFrame] = None,
        base_stop_loss_pct: float = -5.0,
        base_take_profit_pct: float = 8.0,
        volatility_period: int = 20
    ) -> Dict:
        """
        计算动态止损/止盈（根据波动率调整）
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            stock_data: 股票历史数据（可选，如果没有则从数据库获取）
            base_stop_loss_pct: 基础止损比例（%）
            base_take_profit_pct: 基础止盈比例（%）
            volatility_period: 波动率计算周期（天数）
        
        Returns:
            动态止损/止盈配置字典，包含：
                - stop_loss_pct: 调整后的止损比例
                - take_profit_pct: 调整后的止盈比例
                - stop_loss_price: 止损价格
                - take_profit_price: 止盈价格
                - volatility: 波动率
                - adjustment_factor: 调整因子
                - explanation: 说明
        """
        try:
            # 获取历史数据（如果没有提供）
            if stock_data is None or stock_data.empty:
                stock_data = self._get_stock_data(symbol, days=volatility_period + 10)
            
            if stock_data is None or stock_data.empty or len(stock_data) < volatility_period:
                # 数据不足，使用基础值
                stop_loss_pct = base_stop_loss_pct
                take_profit_pct = base_take_profit_pct
                adjustment_factor = 1.0
                volatility = None
                explanation = "历史数据不足，使用基础止损/止盈比例"
            else:
                # 计算波动率（使用收益率的标准差）
                if 'change_pct' in stock_data.columns:
                    returns = stock_data['change_pct'].tail(volatility_period).values
                else:
                    # 如果没有change_pct，计算收益率
                    prices = stock_data['close'].tail(volatility_period + 1).values
                    returns = np.diff(prices) / prices[:-1] * 100
                
                volatility = np.std(returns)  # 波动率（日标准差）
                
                # 根据波动率调整止损/止盈比例
                # 波动率越高，止损/止盈幅度越大
                # 基准波动率假设为2%（A股平均日波动率）
                base_volatility = 2.0
                
                if volatility > 0:
                    # 调整因子：波动率 / 基准波动率，范围0.5-2.0
                    adjustment_factor = max(0.5, min(2.0, volatility / base_volatility))
                else:
                    adjustment_factor = 1.0
                
                # 应用调整因子
                stop_loss_pct = base_stop_loss_pct * adjustment_factor
                take_profit_pct = base_take_profit_pct * adjustment_factor
                
                # 限制止损/止盈范围（避免过大或过小）
                stop_loss_pct = max(-15.0, min(-2.0, stop_loss_pct))  # 止损：-15% 到 -2%
                take_profit_pct = max(3.0, min(20.0, take_profit_pct))  # 止盈：3% 到 20%
                
                explanation = (
                    f"波动率：{volatility:.2f}%（基准：{base_volatility:.2f}%），"
                    f"调整因子：{adjustment_factor:.2f}，"
                    f"止损/止盈已根据波动率调整"
                )
            
            # 计算具体价格
            stop_loss_price = current_price * (1 + stop_loss_pct / 100)
            take_profit_price = current_price * (1 + take_profit_pct / 100)
            
            return {
                'stop_loss_pct': round(stop_loss_pct, 2),
                'take_profit_pct': round(take_profit_pct, 2),
                'stop_loss_price': round(stop_loss_price, 2),
                'take_profit_price': round(take_profit_price, 2),
                'volatility': round(volatility, 2) if volatility is not None else None,
                'adjustment_factor': round(adjustment_factor, 2),
                'explanation': explanation,
                'base_stop_loss_pct': base_stop_loss_pct,
                'base_take_profit_pct': base_take_profit_pct
            }
            
        except Exception as e:
            self.logger.error(f"计算动态止损/止盈失败: {str(e)}")
            # 发生错误时使用基础值
            return {
                'stop_loss_pct': base_stop_loss_pct,
                'take_profit_pct': base_take_profit_pct,
                'stop_loss_price': current_price * (1 + base_stop_loss_pct / 100),
                'take_profit_price': current_price * (1 + base_take_profit_pct / 100),
                'volatility': None,
                'adjustment_factor': 1.0,
                'explanation': f"计算失败，使用基础值: {str(e)}",
                'base_stop_loss_pct': base_stop_loss_pct,
                'base_take_profit_pct': base_take_profit_pct
            }
    
    def _get_stock_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        从数据库获取股票历史数据
        
        Args:
            symbol: 股票代码
            days: 获取天数
        
        Returns:
            股票数据DataFrame，包含日期、收盘价、涨跌幅等
        """
        if not self.db:
            return None
        
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days + 10)
            
            # 查询股票数据（假设有stock_data表，如果没有则返回None）
            sql = """
                SELECT date, close, change_pct
                FROM stock_data
                WHERE symbol = %s
                  AND date >= %s
                  AND date <= %s
                ORDER BY date ASC
            """
            
            results = self.db.execute_query(sql, (symbol, start_date, end_date))
            
            if not results:
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(results)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            if 'close' in df.columns:
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
            if 'change_pct' in df.columns:
                df['change_pct'] = pd.to_numeric(df['change_pct'], errors='coerce')
            
            return df
            
        except Exception as e:
            self.logger.debug(f"获取股票数据失败: {str(e)}")
            return None


    def calculate_portfolio_risk(
        self,
        positions: List[Dict],
        days: int = 60
    ) -> Dict:
        """
        计算组合风险控制（相关性检查、HHI指数）
        
        Args:
            positions: 持仓列表，每个元素包含：
                - symbol: 股票代码
                - weight: 仓位权重（0-1）
                - name: 股票名称（可选）
            days: 用于计算相关性的历史数据天数
        
        Returns:
            组合风险分析结果，包含：
                - correlation_matrix: 相关性矩阵
                - avg_correlation: 平均相关性
                - max_correlation: 最大相关性
                - hhi_index: HHI指数（集中度指数）
                - diversification_score: 分散化得分（0-1）
                - risk_warnings: 风险警告列表
                - recommendations: 优化建议
        """
        try:
            if not positions or len(positions) < 2:
                return {
                    'success': False,
                    'message': '持仓数量不足，无法计算组合风险',
                    'recommendations': ['增加持仓数量以降低集中度风险']
                }
            
            symbols = [p['symbol'] for p in positions]
            weights = [p['weight'] for p in positions]
            
            # 计算HHI指数（赫芬达尔-赫希曼指数，用于衡量集中度）
            # HHI = Σ(weight_i)^2，范围0-1，越接近1表示集中度越高
            hhi_index = sum(w ** 2 for w in weights)
            
            # 计算相关性矩阵
            correlation_matrix = self._calculate_correlation_matrix(symbols, days)
            
            if correlation_matrix is None:
                return {
                    'success': False,
                    'message': '无法计算相关性矩阵（数据不足）',
                    'hhi_index': round(hhi_index, 4),
                    'recommendations': ['数据不足，无法进行相关性分析']
                }
            
            # 提取相关性（排除对角线）
            correlations = []
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    corr = correlation_matrix[i][j]
                    if not np.isnan(corr):
                        correlations.append(corr)
            
            avg_correlation = np.mean(correlations) if correlations else 0.0
            max_correlation = max(correlations) if correlations else 0.0
            
            # 计算分散化得分（0-1，越高越好）
            # 考虑HHI（集中度越低越好）和相关性（相关性越低越好）
            hhi_score = 1.0 - hhi_index  # HHI越高，得分越低
            correlation_score = 1.0 - abs(avg_correlation)  # 相关性越高，得分越低
            diversification_score = (hhi_score * 0.6 + correlation_score * 0.4)  # 加权平均
            diversification_score = max(0.0, min(1.0, diversification_score))
            
            # 生成风险警告
            risk_warnings = []
            recommendations = []
            
            # HHI警告
            if hhi_index > 0.5:
                risk_warnings.append(f"组合集中度较高（HHI={hhi_index:.3f}），存在集中度风险")
                recommendations.append(f"建议降低单只股票仓位，将最大仓位控制在{max(weights)*100:.1f}%以下")
            elif hhi_index > 0.3:
                risk_warnings.append(f"组合集中度中等（HHI={hhi_index:.3f}），建议增加分散度")
                recommendations.append("建议增加持仓数量或降低最大仓位")
            
            # 相关性警告
            if max_correlation > 0.8:
                risk_warnings.append(f"存在高度相关持仓（最大相关性={max_correlation:.3f}），分散化效果差")
                # 找出高度相关的股票对
                high_corr_pairs = []
                for i in range(len(symbols)):
                    for j in range(i + 1, len(symbols)):
                        if correlation_matrix[i][j] > 0.8:
                            high_corr_pairs.append((symbols[i], symbols[j], correlation_matrix[i][j]))
                
                if high_corr_pairs:
                    for sym1, sym2, corr in high_corr_pairs:
                        recommendations.append(f"建议减少 {sym1} 和 {sym2} 的持仓（相关性={corr:.3f}）")
            
            elif avg_correlation > 0.6:
                risk_warnings.append(f"平均相关性较高（{avg_correlation:.3f}），分散化效果一般")
                recommendations.append("建议增加不同行业或板块的持仓以降低相关性")
            
            # 分散化得分建议
            if diversification_score < 0.4:
                recommendations.append("组合分散化得分较低，建议大幅增加持仓数量或降低集中度")
            elif diversification_score < 0.6:
                recommendations.append("组合分散化得分中等，建议适当增加持仓数量")
            
            return {
                'success': True,
                'correlation_matrix': correlation_matrix.tolist() if isinstance(correlation_matrix, np.ndarray) else correlation_matrix,
                'symbols': symbols,
                'avg_correlation': round(avg_correlation, 4),
                'max_correlation': round(max_correlation, 4),
                'hhi_index': round(hhi_index, 4),
                'diversification_score': round(diversification_score, 4),
                'risk_warnings': risk_warnings,
                'recommendations': recommendations,
                'interpretation': self._interpret_diversification_score(diversification_score)
            }
            
        except Exception as e:
            self.logger.error(f"计算组合风险失败: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def _calculate_correlation_matrix(self, symbols: List[str], days: int = 60) -> Optional[np.ndarray]:
        """
        计算股票之间的相关性矩阵
        
        Args:
            symbols: 股票代码列表
            days: 历史数据天数
        
        Returns:
            相关性矩阵（numpy array），如果失败返回None
        """
        try:
            returns_data = []
            valid_symbols = []
            
            for symbol in symbols:
                # 获取股票收益率数据
                stock_data = self._get_stock_data(symbol, days=days + 10)
                if stock_data is None or stock_data.empty or len(stock_data) < days:
                    continue
                
                # 计算收益率
                if 'change_pct' in stock_data.columns:
                    returns = stock_data['change_pct'].tail(days).values
                else:
                    prices = stock_data['close'].tail(days + 1).values
                    returns = np.diff(prices) / prices[:-1] * 100
                
                returns_data.append(returns)
                valid_symbols.append(symbol)
            
            if len(returns_data) < 2:
                return None
            
            # 对齐数据（确保所有序列长度相同）
            min_len = min(len(r) for r in returns_data)
            returns_data = [r[-min_len:] for r in returns_data]
            
            # 计算相关性矩阵
            returns_df = pd.DataFrame(returns_data, index=valid_symbols).T
            correlation_matrix = returns_df.corr().values
            
            return correlation_matrix
            
        except Exception as e:
            self.logger.debug(f"计算相关性矩阵失败: {str(e)}")
            return None
    
    def _interpret_diversification_score(self, score: float) -> str:
        """解释分散化得分"""
        if score >= 0.8:
            return "分散化良好"
        elif score >= 0.6:
            return "分散化中等"
        elif score >= 0.4:
            return "分散化较差"
        else:
            return "分散化很差"
    
    def optimize_position_size(
        self,
        symbol: str,
        signal_strength: float,
        confidence: float,
        volatility: Optional[float] = None,
        current_positions: Optional[List[Dict]] = None,
        max_total_position: float = 0.8,
        max_single_position: float = 0.3,
        base_position: float = 0.1
    ) -> Dict:
        """
        基于风险评分优化仓位大小
        
        Args:
            symbol: 股票代码
            signal_strength: 信号强度（0-1）
            confidence: 置信度（0-1）
            volatility: 波动率（可选）
            current_positions: 当前持仓列表（用于计算组合风险）
            max_total_position: 总仓位上限（默认80%）
            max_single_position: 单只股票最大仓位（默认30%）
            base_position: 基础仓位（默认10%）
        
        Returns:
            仓位优化结果，包含：
                - recommended_position: 建议仓位（0-1）
                - risk_score: 风险评分（0-1，越高风险越大）
                - position_reason: 仓位建议理由
                - risk_factors: 风险因子分析
                - warnings: 风险警告
        """
        try:
            risk_factors = {}
            risk_score = 0.0
            warnings = []
            
            # 1. 信号强度因子（信号越强，风险越低，可增加仓位）
            signal_risk = 1.0 - signal_strength
            risk_factors['signal_risk'] = {
                'value': signal_risk,
                'description': f"信号强度风险: {signal_strength:.1%}（强度越高，风险越低）"
            }
            risk_score += signal_risk * 0.3  # 权重30%
            
            # 2. 置信度因子（置信度越高，风险越低，可增加仓位）
            confidence_risk = 1.0 - confidence
            risk_factors['confidence_risk'] = {
                'value': confidence_risk,
                'description': f"置信度风险: {confidence:.1%}（置信度越高，风险越低）"
            }
            risk_score += confidence_risk * 0.25  # 权重25%
            
            # 3. 波动率因子（波动率越高，风险越大，应降低仓位）
            if volatility is not None:
                # 基准波动率假设为2%
                base_volatility = 2.0
                if volatility > 0:
                    volatility_risk = min(1.0, volatility / (base_volatility * 2))  # 波动率超过4%时为1.0
                else:
                    volatility_risk = 0.5
                
                risk_factors['volatility_risk'] = {
                    'value': volatility_risk,
                    'description': f"波动率风险: {volatility:.2f}%（基准：{base_volatility:.2f}%）"
                }
                risk_score += volatility_risk * 0.25  # 权重25%
                
                if volatility > 5.0:
                    warnings.append(f"波动率较高（{volatility:.2f}%），建议降低仓位")
            else:
                volatility_risk = 0.5  # 未知波动率，假设中等风险
                risk_factors['volatility_risk'] = {
                    'value': volatility_risk,
                    'description': "波动率风险: 未知（使用默认值）"
                }
                risk_score += volatility_risk * 0.25
            
            # 4. 组合集中度因子（如果已有持仓）
            concentration_risk = 0.0
            if current_positions:
                try:
                    portfolio_result = self.calculate_portfolio_risk(current_positions)
                    if portfolio_result.get('success', False):
                        hhi = portfolio_result.get('hhi_index', 0)
                        concentration_risk = hhi  # HHI直接作为集中度风险
                        risk_factors['concentration_risk'] = {
                            'value': concentration_risk,
                            'description': f"组合集中度风险: HHI={hhi:.3f}"
                        }
                        
                        if hhi > 0.5:
                            warnings.append(f"组合集中度较高（HHI={hhi:.3f}），建议降低新仓位")
                        elif hhi > 0.3:
                            warnings.append(f"组合集中度中等（HHI={hhi:.3f}），建议适度控制仓位")
                except Exception:
                    pass
            
            if 'concentration_risk' not in risk_factors:
                risk_factors['concentration_risk'] = {
                    'value': 0.0,
                    'description': "组合集中度风险: 无持仓或数据不足"
                }
            risk_score += concentration_risk * 0.2  # 权重20%
            
            # 确保风险评分在0-1范围内
            risk_score = max(0.0, min(1.0, risk_score))
            
            # 根据风险评分计算建议仓位
            # 风险评分越高，建议仓位越小
            # 风险评分 = 0 时，建议仓位 = max_single_position（最大仓位）
            # 风险评分 = 1 时，建议仓位 = base_position * 0.3（最小仓位，基础仓位的30%）
            position_range = max_single_position - (base_position * 0.3)
            recommended_position = max_single_position - (risk_score * position_range)
            recommended_position = max(base_position * 0.3, min(max_single_position, recommended_position))
            
            # 检查总仓位限制
            if current_positions:
                current_total_position = sum(p.get('weight', 0) for p in current_positions)
                remaining_capacity = max_total_position - current_total_position
                
                if recommended_position > remaining_capacity:
                    warnings.append(f"建议仓位（{recommended_position:.1%}）超过剩余容量（{remaining_capacity:.1%}），调整为剩余容量")
                    recommended_position = max(0, remaining_capacity)
            
            # 生成仓位建议理由
            position_reason_parts = []
            position_reason_parts.append(f"基于风险评分（{risk_score:.2f}）计算建议仓位：")
            
            if signal_strength >= 0.7:
                position_reason_parts.append(f"✓ 信号强度高（{signal_strength:.1%}），支持较高仓位")
            elif signal_strength < 0.5:
                position_reason_parts.append(f"⚠ 信号强度低（{signal_strength:.1%}），建议降低仓位")
            
            if confidence >= 0.7:
                position_reason_parts.append(f"✓ 置信度高（{confidence:.1%}），支持较高仓位")
            elif confidence < 0.55:
                position_reason_parts.append(f"⚠ 置信度低（{confidence:.1%}），建议降低仓位")
            
            if volatility is not None:
                if volatility < 2.0:
                    position_reason_parts.append(f"✓ 波动率低（{volatility:.2f}%），风险可控")
                elif volatility > 4.0:
                    position_reason_parts.append(f"⚠ 波动率高（{volatility:.2f}%），建议降低仓位")
            
            position_reason = "\n".join(position_reason_parts)
            
            return {
                'recommended_position': round(recommended_position, 4),
                'recommended_position_pct': round(recommended_position * 100, 2),
                'risk_score': round(risk_score, 4),
                'position_reason': position_reason,
                'risk_factors': risk_factors,
                'warnings': warnings,
                'constraints': {
                    'max_total_position': max_total_position,
                    'max_single_position': max_single_position,
                    'base_position': base_position
                }
            }
            
        except Exception as e:
            self.logger.error(f"优化仓位大小失败: {str(e)}")
            return {
                'recommended_position': base_position,
                'recommended_position_pct': base_position * 100,
                'risk_score': 0.5,
                'position_reason': f"计算失败，使用基础仓位: {str(e)}",
                'risk_factors': {},
                'warnings': [f"仓位优化计算失败: {str(e)}"],
                'constraints': {
                    'max_total_position': max_total_position,
                    'max_single_position': max_single_position,
                    'base_position': base_position
                }
            }
    
    def check_risk_limits(
        self,
        positions: List[Dict],
        new_position: Optional[Dict] = None,
        risk_limits: Optional[Dict] = None
    ) -> Dict:
        """
        检查风险限额管理
        
        Args:
            positions: 当前持仓列表，每个元素包含：
                - symbol: 股票代码
                - weight: 仓位权重（0-1）
                - cost_price: 成本价（可选）
                - current_price: 当前价（可选）
            new_position: 新持仓建议（可选），包含：
                - symbol: 股票代码
                - weight: 建议仓位权重
            risk_limits: 风险限额配置（可选），包含：
                - max_total_position: 总仓位上限（默认80%）
                - max_single_position: 单只股票最大仓位（默认30%）
                - max_sector_position: 单板块最大仓位（默认40%）
                - max_industry_position: 单行业最大仓位（默认50%）
                - max_correlation: 最大相关性（默认0.8）
                - max_drawdown: 最大回撤限制（默认-20%）
                - max_loss_per_stock: 单只股票最大亏损限制（默认-10%）
        
        Returns:
            风险限额检查结果，包含：
                - passed: 是否通过检查
                - violations: 违规列表
                - warnings: 警告列表
                - recommendations: 建议列表
        """
        try:
            if risk_limits is None:
                risk_limits = {
                    'max_total_position': 0.8,
                    'max_single_position': 0.3,
                    'max_sector_position': 0.4,
                    'max_industry_position': 0.5,
                    'max_correlation': 0.8,
                    'max_drawdown': -0.20,
                    'max_loss_per_stock': -0.10
                }
            
            violations = []
            warnings = []
            recommendations = []
            
            # 计算当前持仓总仓位
            current_total_position = sum(p.get('weight', 0) for p in positions)
            
            # 1. 检查总仓位限制
            max_total = risk_limits.get('max_total_position', 0.8)
            if new_position:
                projected_total = current_total_position + new_position.get('weight', 0)
                if projected_total > max_total:
                    violations.append({
                        'type': 'total_position_exceeded',
                        'message': f"总仓位将超过限制（{projected_total:.1%} > {max_total:.1%}）",
                        'current': current_total_position,
                        'projected': projected_total,
                        'limit': max_total
                    })
                    recommendations.append(f"建议降低总仓位至{max_total:.1%}以下，或减少新仓位")
                elif projected_total > max_total * 0.9:
                    warnings.append({
                        'type': 'total_position_warning',
                        'message': f"总仓位接近限制（{projected_total:.1%} / {max_total:.1%}）",
                        'current': current_total_position,
                        'projected': projected_total,
                        'limit': max_total
                    })
            elif current_total_position > max_total:
                violations.append({
                    'type': 'total_position_exceeded',
                    'message': f"当前总仓位已超过限制（{current_total_position:.1%} > {max_total:.1%}）",
                    'current': current_total_position,
                    'limit': max_total
                })
                recommendations.append(f"建议立即降低总仓位至{max_total:.1%}以下")
            
            # 2. 检查单只股票仓位限制
            max_single = risk_limits.get('max_single_position', 0.3)
            for pos in positions:
                weight = pos.get('weight', 0)
                if weight > max_single:
                    violations.append({
                        'type': 'single_position_exceeded',
                        'symbol': pos.get('symbol', ''),
                        'message': f"{pos.get('symbol', '')} 仓位超过限制（{weight:.1%} > {max_single:.1%}）",
                        'current': weight,
                        'limit': max_single
                    })
                    recommendations.append(f"建议降低 {pos.get('symbol', '')} 的仓位至{max_single:.1%}以下")
            
            if new_position:
                new_weight = new_position.get('weight', 0)
                if new_weight > max_single:
                    violations.append({
                        'type': 'new_position_exceeded',
                        'symbol': new_position.get('symbol', ''),
                        'message': f"新持仓 {new_position.get('symbol', '')} 仓位超过限制（{new_weight:.1%} > {max_single:.1%}）",
                        'proposed': new_weight,
                        'limit': max_single
                    })
                    recommendations.append(f"建议降低新持仓仓位至{max_single:.1%}以下")
            
            # 3. 检查单只股票亏损限制
            max_loss_per_stock = risk_limits.get('max_loss_per_stock', -0.10)
            for pos in positions:
                cost_price = pos.get('cost_price')
                current_price = pos.get('current_price')
                
                if cost_price and current_price and cost_price > 0:
                    loss_pct = (current_price - cost_price) / cost_price
                    if loss_pct < max_loss_per_stock:
                        violations.append({
                            'type': 'loss_limit_exceeded',
                            'symbol': pos.get('symbol', ''),
                            'message': f"{pos.get('symbol', '')} 亏损超过限制（{loss_pct:.1%} < {max_loss_per_stock:.1%}）",
                            'loss_pct': loss_pct,
                            'limit': max_loss_per_stock
                        })
                        recommendations.append(f"建议立即止损 {pos.get('symbol', '')}（亏损{loss_pct:.1%}）")
            
            # 4. 检查组合最大回撤（需要历史数据，这里简化处理）
            # 实际应用中需要计算投资组合的历史最大回撤
            
            # 5. 检查相关性限制（如果持仓数量>=2）
            if len(positions) >= 2:
                max_correlation = risk_limits.get('max_correlation', 0.8)
                try:
                    portfolio_result = self.calculate_portfolio_risk(positions)
                    if portfolio_result.get('success', False):
                        max_corr = portfolio_result.get('max_correlation', 0)
                        if max_corr > max_correlation:
                            violations.append({
                                'type': 'correlation_exceeded',
                                'message': f"组合最大相关性超过限制（{max_corr:.3f} > {max_correlation:.3f}）",
                                'max_correlation': max_corr,
                                'limit': max_correlation
                            })
                            recommendations.append("建议降低高度相关股票的仓位")
                except Exception:
                    pass
            
            # 6. 检查板块/行业集中度（需要板块/行业信息，这里简化处理）
            # 实际应用中需要从数据库获取股票的板块和行业信息
            
            passed = len(violations) == 0
            
            return {
                'passed': passed,
                'violations': violations,
                'warnings': warnings,
                'recommendations': recommendations,
                'current_total_position': current_total_position,
                'risk_limits': risk_limits,
                'summary': self._generate_risk_summary(passed, violations, warnings)
            }
            
        except Exception as e:
            self.logger.error(f"检查风险限额失败: {str(e)}")
            return {
                'passed': False,
                'violations': [{'type': 'check_failed', 'message': str(e)}],
                'warnings': [],
                'recommendations': [],
                'current_total_position': 0,
                'risk_limits': risk_limits or {},
                'summary': f"风险限额检查失败: {str(e)}"
            }
    
    def _generate_risk_summary(self, passed: bool, violations: List[Dict], warnings: List[Dict]) -> str:
        """生成风险摘要"""
        if passed and not warnings:
            return "风险限额检查通过，无违规和警告"
        elif passed:
            return f"风险限额检查通过，但有 {len(warnings)} 个警告"
        else:
            return f"风险限额检查未通过，发现 {len(violations)} 个违规"


# 全局实例
_risk_manager_instance = None

def get_risk_manager() -> RiskManager:
    """获取风险管理器单例"""
    global _risk_manager_instance
    if _risk_manager_instance is None:
        _risk_manager_instance = RiskManager()
    return _risk_manager_instance
