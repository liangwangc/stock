# -*- coding: utf-8 -*-
"""
回测结果可视化模块
用于可视化回测结果，包括收益曲线、最大回撤、交易记录等
"""
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)


class BacktestVisualizer:
    """回测结果可视化器"""
    
    def __init__(self):
        # 创建reports目录用于存放回测结果文件
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.reports_dir = os.path.join(project_root, 'reports')
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
        self.logger = logger
    
    def visualize_backtest_result(self, backtest_result: Dict, 
                                   filename: Optional[str] = None) -> str:
        """
        生成回测结果的HTML可视化报告
        
        Args:
            backtest_result: 回测结果字典
            filename: 输出文件名（可选，默认自动生成）
            
        Returns:
            HTML文件路径
        """
        if not backtest_result.get('success', False):
            self.logger.warning("回测结果无效，无法可视化")
            return ""
        
        try:
            # 生成文件名
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"backtest_result_{timestamp}.html"
            
            filepath = os.path.join(self.reports_dir, filename)
            
            # 创建HTML报告
            html_content = self._create_html_report(backtest_result)
            
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"回测结果可视化报告已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"生成回测结果可视化报告失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return ""
    
    def _create_html_report(self, backtest_result: Dict) -> str:
        """创建HTML报告内容"""
        # 提取数据
        start_date = backtest_result.get('start_date', '')
        end_date = backtest_result.get('end_date', '')
        initial_capital = backtest_result.get('initial_capital', 100000.0)
        final_value = backtest_result.get('final_value', 0)
        total_return = backtest_result.get('total_return', 0)
        metrics = backtest_result.get('metrics', {})
        trades = backtest_result.get('trades', [])
        daily_values = backtest_result.get('daily_values', [])
        parameters = backtest_result.get('parameters', {})
        
        # 本次回测使用的交易参数（R7：报告内展示，与设置页一致）
        params_html = self._create_params_section(parameters)
        
        # 生成图表HTML
        profit_curve_html = self._create_profit_curve_chart(daily_values, initial_capital)
        drawdown_html = self._create_drawdown_chart(daily_values, initial_capital)
        trades_table_html = self._create_trades_table(trades)
        metrics_html = self._create_metrics_chart(metrics)
        
        # 生成HTML报告
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>回测结果报告</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-left: 4px solid #4CAF50;
            padding-left: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-item {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-item h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .summary-item .value {{
            font-size: 24px;
            font-weight: bold;
        }}
        .chart-container {{
            margin: 20px 0;
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .positive {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .negative {{
            color: #2ecc71;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 回测结果报告</h1>
        
        <div class="summary">
            <div class="summary-item">
                <h3>回测期间</h3>
                <div class="value">{start_date} 至 {end_date}</div>
            </div>
            <div class="summary-item">
                <h3>初始资金</h3>
                <div class="value">¥{initial_capital:,.0f}</div>
            </div>
            <div class="summary-item">
                <h3>最终资产</h3>
                <div class="value">¥{final_value:,.2f}</div>
            </div>
            <div class="summary-item">
                <h3>总收益率</h3>
                <div class="value" style="color: {'#e74c3c' if total_return >= 0 else '#2ecc71'}">{total_return:+.2f}%</div>
            </div>
            <div class="summary-item">
                <h3>年化收益率</h3>
                <div class="value" style="color: {'#e74c3c' if metrics.get('annual_return', 0) >= 0 else '#2ecc71'}">{metrics.get('annual_return', 0):+.2f}%</div>
            </div>
            <div class="summary-item">
                <h3>最大回撤</h3>
                <div class="value" style="color: #2ecc71">{metrics.get('max_drawdown', 0):.2f}%</div>
            </div>
            <div class="summary-item">
                <h3>胜率</h3>
                <div class="value">{metrics.get('win_rate', 0):.2f}%</div>
            </div>
            <div class="summary-item">
                <h3>交易次数</h3>
                <div class="value">{backtest_result.get('trades_count', 0)}</div>
            </div>
        </div>
        
        <h2>📋 本次回测使用的交易参数</h2>
        <div class="chart-container">
            {params_html}
        </div>
        
        <h2>📈 收益曲线</h2>
        <div class="chart-container">
            {profit_curve_html}
        </div>
        
        <h2>📉 最大回撤</h2>
        <div class="chart-container">
            {drawdown_html}
        </div>
        
        <h2>📊 绩效指标</h2>
        <div class="chart-container">
            {metrics_html}
        </div>
        
        <h2>📋 交易记录</h2>
        {trades_table_html}
        
        <div style="margin-top: 40px; text-align: center; color: #999; font-size: 12px;">
            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _create_params_section(self, parameters: Dict) -> str:
        """生成本次回测使用的交易参数 HTML（R7：与设置页一致，便于核对）"""
        if not parameters:
            return "<p>无参数记录</p>"
        p = parameters
        max_pos = p.get('max_position_pct')
        if max_pos is not None:
            max_pos_str = f"{max_pos * 100:.0f}%" if max_pos <= 1 else f"{max_pos}%"
        else:
            max_pos_str = "-"
        rows = [
            ("买入阈值", p.get('buy_threshold'), ""),
            ("卖出阈值", p.get('sell_threshold'), ""),
            ("最小置信度", p.get('min_confidence'), ""),
            ("止损", p.get('stop_loss_pct'), "%"),
            ("止盈", p.get('take_profit_pct'), "%"),
            ("单只仓位", max_pos_str, ""),
            ("最大持仓天数", p.get('max_holding_days'), ""),
        ]
        html = '<table style="width: auto; min-width: 280px;"><tbody>'
        for label, val, suffix in rows:
            if val is None or val == "":
                disp = "-"
            elif suffix == "%" and isinstance(val, (int, float)):
                disp = f"{val}{suffix}"
            else:
                disp = str(val) + str(suffix)
            html += f'<tr><td style="color:#666; padding:6px 12px 6px 0;">{label}</td><td style="font-weight:bold;">{disp}</td></tr>'
        html += '</tbody></table>'
        return html
    
    def _create_profit_curve_chart(self, daily_values: List[Dict], initial_capital: float) -> str:
        """创建收益曲线图"""
        if not daily_values:
            return "<p>暂无数据</p>"
        
        try:
            # 准备数据
            df = pd.DataFrame(daily_values)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 计算收益率
            df['return_pct'] = (df['total_value'] - initial_capital) / initial_capital * 100
            
            # 标记买入和卖出点（从交易记录中获取）
            # 这里简化处理，实际可以从trades数据中提取
            
            # 创建图表
            fig = go.Figure()
            
            # 收益曲线
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['return_pct'],
                mode='lines',
                name='累计收益率',
                line=dict(color='#3498db', width=2),
                fill='tozeroy',
                fillcolor='rgba(52, 152, 219, 0.1)'
            ))
            
            # 添加零线
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            fig.update_layout(
                title='累计收益率曲线',
                xaxis_title='日期',
                yaxis_title='收益率 (%)',
                hovermode='x unified',
                template='plotly_white',
                height=400
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='profit_curve')
            
        except Exception as e:
            self.logger.error(f"创建收益曲线图失败: {str(e)}")
            return f"<p>图表生成失败: {str(e)}</p>"
    
    def _create_drawdown_chart(self, daily_values: List[Dict], initial_capital: float) -> str:
        """创建最大回撤图"""
        if not daily_values:
            return "<p>暂无数据</p>"
        
        try:
            # 准备数据
            df = pd.DataFrame(daily_values)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 计算累计最高值
            df['cummax'] = df['total_value'].cummax()
            
            # 计算回撤
            df['drawdown'] = (df['total_value'] - df['cummax']) / df['cummax'] * 100
            
            # 创建图表
            fig = go.Figure()
            
            # 回撤面积图
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['drawdown'],
                mode='lines',
                name='回撤',
                line=dict(color='#e74c3c', width=2),
                fill='tozeroy',
                fillcolor='rgba(231, 76, 60, 0.3)'
            ))
            
            fig.update_layout(
                title='最大回撤曲线',
                xaxis_title='日期',
                yaxis_title='回撤 (%)',
                hovermode='x unified',
                template='plotly_white',
                height=300
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='drawdown_chart')
            
        except Exception as e:
            self.logger.error(f"创建最大回撤图失败: {str(e)}")
            return f"<p>图表生成失败: {str(e)}</p>"
    
    def _create_trades_table(self, trades: List[Dict]) -> str:
        """创建交易记录表格"""
        if not trades:
            return "<p>暂无交易记录</p>"
        
        try:
            html = """
            <table>
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>股票代码</th>
                        <th>操作</th>
                        <th>价格</th>
                        <th>数量</th>
                        <th>收益</th>
                        <th>收益率</th>
                        <th>说明</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for trade in trades:
                date = trade.get('date', '')
                symbol = trade.get('symbol', '')
                action = trade.get('action', '')
                action_cn = '买入' if action == 'BUY' else '卖出' if action == 'SELL' else action
                price = trade.get('price', 0)
                shares = trade.get('shares', 0)
                profit = trade.get('profit', 0)
                profit_pct = trade.get('profit_pct', 0)
                reason = trade.get('reason', '')
                
                profit_class = 'positive' if profit >= 0 else 'negative'
                profit_pct_class = 'positive' if profit_pct >= 0 else 'negative'
                
                html += f"""
                    <tr>
                        <td>{date}</td>
                        <td>{symbol}</td>
                        <td>{action_cn}</td>
                        <td>¥{price:.2f}</td>
                        <td>{shares}</td>
                        <td class="{profit_class}">¥{profit:.2f}</td>
                        <td class="{profit_pct_class}">{profit_pct:+.2f}%</td>
                        <td>{reason}</td>
                    </tr>
                """
            
            html += """
                </tbody>
            </table>
            """
            
            return html
            
        except Exception as e:
            self.logger.error(f"创建交易记录表格失败: {str(e)}")
            return f"<p>表格生成失败: {str(e)}</p>"
    
    def _create_metrics_chart(self, metrics: Dict) -> str:
        """创建绩效指标图表"""
        try:
            # 提取关键指标
            metrics_data = {
                '年化收益率': metrics.get('annual_return', 0),
                '最大回撤': metrics.get('max_drawdown', 0),
                '胜率': metrics.get('win_rate', 0),
                '盈亏比': metrics.get('profit_loss_ratio', 0),
                '夏普比率': metrics.get('sharpe_ratio', 0)
            }
            
            # 创建柱状图
            fig = go.Figure()
            
            colors = ['#3498db' if v >= 0 else '#e74c3c' for v in metrics_data.values()]
            colors[1] = '#e74c3c'  # 最大回撤始终为红色
            
            fig.add_trace(go.Bar(
                x=list(metrics_data.keys()),
                y=list(metrics_data.values()),
                marker_color=colors,
                text=[f'{v:.2f}' for v in metrics_data.values()],
                textposition='auto'
            ))
            
            fig.update_layout(
                title='绩效指标对比',
                xaxis_title='指标',
                yaxis_title='数值',
                template='plotly_white',
                height=300
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='metrics_chart')
            
        except Exception as e:
            self.logger.error(f"创建绩效指标图表失败: {str(e)}")
            return f"<p>图表生成失败: {str(e)}</p>"
    
    def create_profit_curve_html(self, backtest_result: Dict) -> str:
        """
        仅生成收益曲线图的HTML（用于嵌入其他页面）
        
        Args:
            backtest_result: 回测结果字典
            
        Returns:
            HTML字符串
        """
        daily_values = backtest_result.get('daily_values', [])
        initial_capital = backtest_result.get('initial_capital', 100000.0)
        return self._create_profit_curve_chart(daily_values, initial_capital)
    
    def create_drawdown_html(self, backtest_result: Dict) -> str:
        """
        仅生成最大回撤图的HTML（用于嵌入其他页面）
        
        Args:
            backtest_result: 回测结果字典
            
        Returns:
            HTML字符串
        """
        daily_values = backtest_result.get('daily_values', [])
        initial_capital = backtest_result.get('initial_capital', 100000.0)
        return self._create_drawdown_chart(daily_values, initial_capital)
