"""
风险控制模块
用于控制组合风险，包括总仓位控制、单只股票仓位限制、相关性检查等
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)


class RiskController:
    """风险控制器"""
    
    def __init__(self, config: Dict = None):
        self.logger = logger
        self.config = config or {}
        
        # 默认配置
        self.default_config = {
            'max_total_position_pct': 80.0,  # 总仓位上限
            'max_single_position_pct': 30.0,  # 单只股票最大仓位
            'max_correlation': 0.8,           # 最大相关性
            'enable_risk_control': True,      # 是否启用风险控制
        }
        
        # 合并配置
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
    
    def check_position_limit(self, current_positions: Dict[str, float], 
                            new_symbol: str, new_position_pct: float) -> Tuple[bool, str, Dict]:
        """
        检查仓位限制
        
        Args:
            current_positions: 当前持仓字典 {symbol: position_pct}
            new_symbol: 新股票代码
            new_position_pct: 新仓位百分比
        
        Returns:
            (is_allowed, message, risk_report)
        """
        risk_report = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
            'risk_score': 0.0,  # 风险得分 0-1，越高风险越大
        }
        
        if not self.config.get('enable_risk_control', True):
            return True, "风险控制已禁用", risk_report
        
        # 1. 检查单只股票仓位限制
        if new_position_pct > self.config['max_single_position_pct']:
            risk_report['checks_failed'] += 1
            risk_report['errors'].append(
                f"单只股票仓位超限: {new_position_pct:.1f}% > {self.config['max_single_position_pct']:.1f}%"
            )
            return False, f"单只股票仓位超限", risk_report
        
        risk_report['checks_passed'] += 1
        
        # 2. 检查总仓位限制
        total_position = sum(current_positions.values()) + new_position_pct
        if total_position > self.config['max_total_position_pct']:
            risk_report['checks_failed'] += 1
            risk_report['errors'].append(
                f"总仓位超限: {total_position:.1f}% > {self.config['max_total_position_pct']:.1f}%"
            )
            return False, f"总仓位超限", risk_report
        
        risk_report['checks_passed'] += 1
        
        # 3. 警告：总仓位接近上限
        if total_position > self.config['max_total_position_pct'] * 0.9:
            risk_report['warnings'].append(
                f"总仓位接近上限: {total_position:.1f}% / {self.config['max_total_position_pct']:.1f}%"
            )
        
        # 计算风险得分
        total_checks = risk_report['checks_passed'] + risk_report['checks_failed']
        if total_checks > 0:
            risk_report['risk_score'] = risk_report['checks_failed'] / total_checks
        
        return True, "仓位检查通过", risk_report
    
    def check_correlation(self, current_symbols: List[str], new_symbol: str,
                         correlation_data: pd.DataFrame = None) -> Tuple[bool, str, Dict]:
        """
        检查股票相关性
        
        Args:
            current_symbols: 当前持有的股票代码列表
            new_symbol: 新股票代码
            correlation_data: 相关性数据DataFrame（可选，如果提供则使用，否则跳过检查）
        
        Returns:
            (is_allowed, message, risk_report)
        """
        risk_report = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
            'max_correlation': 0.0,
            'correlated_stocks': [],
        }
        
        if not self.config.get('enable_risk_control', True):
            return True, "风险控制已禁用", risk_report
        
        if not current_symbols or correlation_data is None:
            # 没有持仓或没有相关性数据，跳过检查
            risk_report['checks_passed'] += 1
            return True, "相关性检查跳过（无持仓或无数据）", risk_report
        
        # 检查新股票与现有持仓的相关性
        max_corr = 0.0
        correlated_stocks = []
        
        for symbol in current_symbols:
            if symbol in correlation_data.columns and new_symbol in correlation_data.columns:
                try:
                    corr = correlation_data[symbol].corr(correlation_data[new_symbol])
                    if not pd.isna(corr):
                        if abs(corr) > max_corr:
                            max_corr = abs(corr)
                        if abs(corr) > self.config['max_correlation']:
                            correlated_stocks.append({
                                'symbol': symbol,
                                'correlation': corr
                            })
                except Exception as e:
                    self.logger.debug(f"计算相关性失败 {symbol}-{new_symbol}: {str(e)}")
        
        risk_report['max_correlation'] = max_corr
        risk_report['correlated_stocks'] = correlated_stocks
        
        if max_corr > self.config['max_correlation']:
            risk_report['checks_failed'] += 1
            risk_report['warnings'].append(
                f"检测到高相关性: {max_corr:.2f} > {self.config['max_correlation']}"
            )
            risk_report['warnings'].append(
                f"相关股票: {', '.join([s['symbol'] for s in correlated_stocks])}"
            )
        else:
            risk_report['checks_passed'] += 1
        
        is_allowed = len(correlated_stocks) == 0 or max_corr <= self.config['max_correlation']
        message = "相关性检查通过" if is_allowed else f"检测到高相关性: {max_corr:.2f}"
        
        return is_allowed, message, risk_report
    
    def calculate_portfolio_risk(self, positions: Dict[str, float],
                                price_data: Dict[str, pd.DataFrame] = None) -> Dict:
        """
        计算组合风险指标
        
        Args:
            positions: 持仓字典 {symbol: position_pct}
            price_data: 价格数据字典 {symbol: DataFrame}（可选）
        
        Returns:
            风险指标字典
        """
        risk_metrics = {
            'total_position_pct': sum(positions.values()),
            'position_count': len(positions),
            'max_single_position_pct': max(positions.values()) if positions else 0.0,
            'position_concentration': 0.0,  # 仓位集中度（HHI指数）
            'risk_score': 0.0,
            'warnings': [],
        }
        
        if not positions:
            return risk_metrics
        
        # 计算仓位集中度（HHI指数）
        position_values = list(positions.values())
        if position_values:
            hhi = sum(p ** 2 for p in position_values)  # HHI指数
            risk_metrics['position_concentration'] = hhi
        
        # 检查风险
        if risk_metrics['total_position_pct'] > self.config['max_total_position_pct']:
            risk_metrics['warnings'].append(
                f"总仓位超限: {risk_metrics['total_position_pct']:.1f}%"
            )
        
        if risk_metrics['max_single_position_pct'] > self.config['max_single_position_pct']:
            risk_metrics['warnings'].append(
                f"单只股票仓位超限: {risk_metrics['max_single_position_pct']:.1f}%"
            )
        
        if risk_metrics['position_concentration'] > 0.3:  # HHI > 0.3 表示集中度高
            risk_metrics['warnings'].append(
                f"仓位集中度较高: {risk_metrics['position_concentration']:.2f}"
            )
        
        # 计算综合风险得分
        risk_score = 0.0
        if risk_metrics['total_position_pct'] > self.config['max_total_position_pct']:
            risk_score += 0.4
        if risk_metrics['max_single_position_pct'] > self.config['max_single_position_pct']:
            risk_score += 0.3
        if risk_metrics['position_concentration'] > 0.3:
            risk_score += 0.3
        
        risk_metrics['risk_score'] = min(risk_score, 1.0)
        
        return risk_metrics
    
    def get_risk_advice(self, risk_metrics: Dict) -> str:
        """
        根据风险指标生成风险建议
        
        Args:
            risk_metrics: 风险指标字典
        
        Returns:
            风险建议文本
        """
        advice_parts = []
        
        if risk_metrics.get('risk_score', 0) > 0.7:
            advice_parts.append("⚠️ 风险较高，建议降低仓位")
        elif risk_metrics.get('risk_score', 0) > 0.4:
            advice_parts.append("⚠️ 风险中等，注意控制仓位")
        else:
            advice_parts.append("✓ 风险可控")
        
        if risk_metrics.get('total_position_pct', 0) > self.config['max_total_position_pct'] * 0.9:
            advice_parts.append("建议降低总仓位")
        
        if risk_metrics.get('position_concentration', 0) > 0.3:
            advice_parts.append("建议分散持仓，降低集中度")
        
        return " | ".join(advice_parts) if advice_parts else "无特殊建议"
