# -*- coding: utf-8 -*-
"""
预测结果可视化
"""
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from typing import Dict
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import textwrap
import importlib.util
import os

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

class PredictionVisualizer:
    """预测结果可视化器"""
    
    def __init__(self):
        self.fig = None
        self.axes = None
        # 创建reports目录用于存放预测结果文件
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.reports_dir = os.path.join(project_root, 'reports')
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
    
    def visualize(self, prediction_result: Dict, stock_data: pd.DataFrame = None, 
                  realtime_data: Dict = None):
        """
        可视化预测结果
        
        Args:
            prediction_result: 预测结果字典
            stock_data: 股票历史数据（可选）
            realtime_data: 实时交易决策数据（可选），包含实时行情、资金流向、交易决策等
        """
        if not prediction_result.get('success', False):
            print("预测失败，无法可视化")
            return
        
        # 创建图表 - 使用4行4列布局（增加一行用于实时数据展示）
        fig = plt.figure(figsize=(20, 18))
        # 第一行：饼图(左)、雷达图(中左)、涨跌对比图(中右)、实时交易决策(右)
        # 第二行：市场行情预测(左)、个股预测分析(右)，并排显示，固定大小
        # 第三行：实时数据面板（全宽）
        # 第四行：30天趋势图(全宽)
        gs = fig.add_gridspec(4, 4, hspace=0.25, wspace=0.3, 
                              height_ratios=[1, 1.2, 0.8, 1.2],
                              width_ratios=[1, 1, 1, 1])
        
        symbol = prediction_result['symbol']
        up_prob = prediction_result['up_probability']
        down_prob = prediction_result['down_probability']
        confidence = prediction_result['confidence']
        target_date = prediction_result.get('target_date')
        
        # 尝试获取实时数据（如果未提供）
        if realtime_data is None:
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                data_source_spec = importlib.util.spec_from_file_location(
                    "stock_data_source",
                    os.path.join(project_root, "data_source", "stock_data_source.py")
                )
                data_source_module = importlib.util.module_from_spec(data_source_spec)
                data_source_spec.loader.exec_module(data_source_module)
                StockDataSource = data_source_module.StockDataSource
                
                data_source = StockDataSource()
                realtime_quote = data_source.get_realtime_quote(symbol)
                capital_flow = data_source.get_realtime_capital_flow(symbol)
                trading_time = data_source.is_trading_time()
                
                realtime_data = {
                    'quote': realtime_quote,
                    'capital_flow': capital_flow,
                    'trading_time': trading_time
                }
            except Exception as e:
                realtime_data = {}
        
        # 计算两种成本分布（历史 + 当日），用于个股分析和报告展示，同时触发CSV存储
        cost_distribution = {}
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_source_spec = importlib.util.spec_from_file_location(
                "stock_data_source_for_cost",
                os.path.join(project_root, "data_source", "stock_data_source.py")
            )
            data_source_module = importlib.util.module_from_spec(data_source_spec)
            data_source_spec.loader.exec_module(data_source_module)
            StockDataSourceForCost = data_source_module.StockDataSource
            ds_for_cost = StockDataSourceForCost()
            history_cost = ds_for_cost.get_cost_distribution(symbol)
            intraday_cost = ds_for_cost.get_intraday_cost_distribution(symbol)
            cost_distribution = {
                'history': history_cost,
                'intraday': intraday_cost
            }
        except Exception:
            cost_distribution = {}
        
        # 将成本分布挂到预测结果中，便于HTML报告等复用
        if isinstance(prediction_result, dict):
            prediction_result['cost_distribution'] = cost_distribution
        
        # 1. 涨跌概率饼图（第一行左）
        ax1 = fig.add_subplot(gs[0, 0])
        colors = ['#2ecc71', '#e74c3c', '#95a5a6']
        sizes = [up_prob, down_prob, 1 - up_prob - down_prob]
        labels = [f'上涨 {up_prob*100:.1f}%', f'下跌 {down_prob*100:.1f}%', '其他']
        explode = (0.1, 0.1, 0)
        
        ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
        if target_date:
            ax1.set_title(f'{symbol} {target_date} 涨跌概率', fontsize=12, fontweight='bold')
        else:
            ax1.set_title(f'{symbol} 涨跌概率', fontsize=12, fontweight='bold')
        
        # 2. 各因素得分雷达图（第一行中左）
        ax3 = fig.add_subplot(gs[0, 1], projection='polar')
        
        factors = prediction_result['factors']
        # 【已优化】移除已优化的因子：us_sector
        categories_radar = ['技术指标', '新闻情感', '市场情绪', '历史模式']
        scores = [
            factors['technical']['score'],
            factors['news']['score'],
            factors['market']['score'],
            factors['history']['score']
        ]
        
        # 转换为0-1范围用于雷达图
        scores_normalized = [(s + 1) / 2 for s in scores]
        scores_normalized += scores_normalized[:1]  # 闭合图形
        
        angles = np.linspace(0, 2 * np.pi, len(categories_radar), endpoint=False).tolist()
        angles += angles[:1]
        
        ax3.plot(angles, scores_normalized, 'o-', linewidth=2, label='得分')
        ax3.fill(angles, scores_normalized, alpha=0.25)
        ax3.set_xticks(angles[:-1])
        ax3.set_xticklabels(categories_radar, fontsize=10)
        ax3.set_ylim(0, 1)
        ax3.set_title('各因素得分雷达图', fontsize=12, fontweight='bold', pad=15)
        ax3.grid(True)
        
        # 添加得分标签
        for angle, score, label in zip(angles[:-1], scores_normalized[:-1], categories_radar):
            ax3.text(angle, score + 0.1, f'{score:.2f}', ha='center', va='center', fontsize=8)
        
        # 3. 概率柱状图（第一行中右）
        ax2 = fig.add_subplot(gs[0, 2])
        categories = ['上涨概率', '下跌概率']
        probabilities = [up_prob * 100, down_prob * 100]
        colors_bar = ['#2ecc71', '#e74c3c']
        
        bars = ax2.bar(categories, probabilities, color=colors_bar, alpha=0.7, edgecolor='black', width=0.6)
        ax2.set_ylabel('概率 (%)', fontsize=10)
        ax2.set_ylim(0, 100)
        ax2.set_title('涨跌概率对比', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        # 在柱状图上添加数值标签
        for bar, prob in zip(bars, probabilities):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{prob:.1f}%',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # 4. 实时交易决策（第一行右侧，固定大小，红色方框位置）
        trading_ax = fig.add_subplot(gs[0, 3])
        trading_ax.axis('off')  # 不显示坐标轴
        
        # 显示实时交易决策信息
        realtime_decision = realtime_data.get('decision', {}) if realtime_data else {}
        realtime_quote = realtime_data.get('quote', {}) if realtime_data else {}
        
        if realtime_decision:
            # 显示实时交易决策标题
            y_pos = 0.95
            trading_ax.text(0.5, y_pos, "【实时交易决策】", 
                           fontsize=12, fontweight='bold', ha='center',
                           color='red', transform=trading_ax.transAxes)
            y_pos -= 0.1
            
            # 显示操作建议
            action_cn = realtime_decision.get('action_cn', '未知')
            strength_cn = realtime_decision.get('strength_cn', '未知')
            
            # 根据操作类型设置颜色
            action_color = 'green' if realtime_decision.get('action') in ['BUY', 'ADD'] else \
                          'red' if realtime_decision.get('action') in ['SELL', 'REDUCE'] else 'orange'
            
            trading_ax.text(0.5, y_pos, f"操作: {action_cn}", 
                           fontsize=11, fontweight='bold', ha='center',
                           color=action_color, transform=trading_ax.transAxes)
            y_pos -= 0.08
            trading_ax.text(0.5, y_pos, f"强度: {strength_cn}", 
                           fontsize=10, ha='center',
                           color='darkblue', transform=trading_ax.transAxes)
            y_pos -= 0.12
            
            # 显示价格建议
            price_suggestions = realtime_decision.get('price_suggestions', {})
            if price_suggestions:
                if 'ideal_buy' in price_suggestions:
                    trading_ax.text(0.05, y_pos, f"理想买入: {price_suggestions['ideal_buy']:.2f}元", 
                                   fontsize=9, ha='left', color='green',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.08
                    trading_ax.text(0.05, y_pos, f"止损价: {price_suggestions.get('stop_loss', 'N/A')}", 
                                   fontsize=9, ha='left', color='red',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.08
                    trading_ax.text(0.05, y_pos, f"目标价: {price_suggestions.get('target', 'N/A')}", 
                                   fontsize=9, ha='left', color='blue',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.1
                if 'ideal_sell' in price_suggestions:
                    trading_ax.text(0.05, y_pos, f"理想卖出: {price_suggestions['ideal_sell']:.2f}元", 
                                   fontsize=9, ha='left', color='red',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.1
            
            # 显示决策理由（最多显示2条）
            reasons = realtime_decision.get('reasons', [])[:2]
            if reasons:
                trading_ax.text(0.05, y_pos, "理由:", 
                               fontsize=9, ha='left', fontweight='bold',
                               transform=trading_ax.transAxes)
                y_pos -= 0.08
                for reason in reasons:
                    wrapped_reason = textwrap.fill(reason, width=18)
                    reason_lines = wrapped_reason.split('\n')
                    for line in reason_lines[:2]:  # 最多显示2行
                        trading_ax.text(0.05, y_pos, f"• {line}", 
                                       fontsize=8, ha='left', style='italic',
                                       color='darkgreen', transform=trading_ax.transAxes)
                        y_pos -= 0.06
                    if len(reason_lines) > 2:
                        break
            
            # 添加红色边框使实时交易决策区域更明显
            trading_ax.add_patch(plt.Rectangle((0.02, 0.05), 0.96, 0.9, 
                                              fill=False, edgecolor='red', 
                                              linewidth=2.5, linestyle='-',
                                              transform=trading_ax.transAxes))
        else:
            # 如果没有实时决策数据，显示传统交易建议
            trading_suggestions = prediction_result.get('trading_suggestions', {})
            if trading_suggestions:
                # 显示交易建议标题
                y_pos = 0.95
                trading_ax.text(0.05, y_pos, "交易建议", 
                               fontsize=12, fontweight='bold', ha='left',
                               transform=trading_ax.transAxes)
                y_pos -= 0.1
                
                buy_price = trading_suggestions.get('buy_price')
                if buy_price:
                    trading_ax.text(0.05, y_pos, f"买入: {buy_price:.2f}元", 
                                   fontsize=10, ha='left',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.12
                
                sell_price = trading_suggestions.get('sell_price')
                if sell_price:
                    trading_ax.text(0.05, y_pos, f"卖出: {sell_price:.2f}元", 
                                   fontsize=10, ha='left',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.12
                
                auction_entry = trading_suggestions.get('auction_entry', False)
                auction_price = trading_suggestions.get('auction_price')
                auction_reason = trading_suggestions.get('auction_reason', '')
                if auction_entry and auction_price:
                    trading_ax.text(0.05, y_pos, "竞价进入", 
                                   fontsize=10, ha='left', fontweight='bold',
                                   color='green', transform=trading_ax.transAxes)
                    y_pos -= 0.08
                    trading_ax.text(0.05, y_pos, f"价格: {auction_price:.2f}元", 
                                   fontsize=9, ha='left',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.08
                    if auction_reason:
                        # 换行显示原因
                        wrapped_reason = textwrap.fill(auction_reason, width=15)
                        reason_lines = wrapped_reason.split('\n')
                        for line in reason_lines:
                            trading_ax.text(0.05, y_pos, f"理由: {line}", 
                                           fontsize=8, ha='left', style='italic',
                                           color='darkgreen', transform=trading_ax.transAxes)
                            y_pos -= 0.06
                    y_pos -= 0.06
                else:
                    trading_ax.text(0.05, y_pos, "竞价建议", 
                                   fontsize=10, ha='left', fontweight='bold',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.08
                    if auction_reason:
                        wrapped_reason = textwrap.fill(auction_reason, width=15)
                        reason_lines = wrapped_reason.split('\n')
                        for line in reason_lines:
                            trading_ax.text(0.05, y_pos, line, 
                                           fontsize=8, ha='left', style='italic',
                                           color='gray', transform=trading_ax.transAxes)
                            y_pos -= 0.06
                    y_pos -= 0.06
                
                stop_loss = trading_suggestions.get('stop_loss')
                take_profit = trading_suggestions.get('take_profit')
                if stop_loss:
                    trading_ax.text(0.05, y_pos, f"止损: {stop_loss:.2f}元", 
                                   fontsize=9, ha='left',
                                   transform=trading_ax.transAxes)
                    y_pos -= 0.1
                if take_profit:
                    trading_ax.text(0.05, y_pos, f"止盈: {take_profit:.2f}元", 
                                   fontsize=9, ha='left',
                                   transform=trading_ax.transAxes)
                
                # 添加红色边框使交易建议区域更明显
                trading_ax.add_patch(plt.Rectangle((0.02, 0.05), 0.96, 0.9, 
                                                  fill=False, edgecolor='red', 
                                                  linewidth=2, linestyle='-',
                                                  transform=trading_ax.transAxes))
        
        # 5. 市场行情预测（第二行左半部分，固定大小）
        market_ax = fig.add_subplot(gs[1, :2])
        market_ax.axis('off')  # 不显示坐标轴
        market_ax.set_xlim(0, 1)
        market_ax.set_ylim(0, 1)
        
        # 显示市场整体行情预测
        market_overall = prediction_result.get('market_overall', {})
        date_desc = prediction_result.get('date_desc', '明天')
        
        # 计算可用区域（留出边距）
        margin_left = 0.03
        margin_right = 0.03
        margin_top = 0.02
        margin_bottom = 0.02
        content_width = 1 - margin_left - margin_right
        content_height = 1 - margin_top - margin_bottom
        
        y_pos = 1 - margin_top
        
        # 标题
        title_height = 0.08
        market_ax.text(margin_left + 0.02, y_pos - 0.01, '【市场整体行情预测】', 
                      fontsize=12, fontweight='bold', ha='left',
                      color='darkblue',
                      transform=market_ax.transAxes,
                      bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.5))
        y_pos -= title_height + 0.05
        
        # 添加市场整体行情预测
        if market_overall.get('success', False):
            market_pred = market_overall.get('overall_prediction', '震荡')
            market_up_prob = market_overall.get('overall_up_probability', 0.5) * 100
            market_down_prob = market_overall.get('overall_down_probability', 0.5) * 100
            
            # 市场整体预测结果（使用textwrap确保换行）
            market_text = f"沪深股市整体预计{market_pred}，上涨概率{market_up_prob:.1f}%，下跌概率{market_down_prob:.1f}%"
            # 根据可用宽度换行（大约每行25个字符）
            wrapped_market_text = textwrap.fill(market_text, width=25)
            lines = wrapped_market_text.split('\n')
            for line in lines:
                if y_pos < margin_bottom + 0.05:
                    break
                market_ax.text(margin_left + 0.02, y_pos, line, 
                              fontsize=10, ha='left', va='top', color='darkblue',
                              transform=market_ax.transAxes)
                y_pos -= 0.08
            y_pos -= 0.02  # 段落间距
            
            # 各指数预测详情
            index_predictions = market_overall.get('index_predictions', {})
            if index_predictions:
                line_height = 0.08
                min_y = margin_bottom + 0.05
                for index_name, pred in index_predictions.items():
                    if y_pos < min_y:
                        break  # 超出边界则停止显示
                    index_text = f"{index_name}: {pred['prediction']}，上涨{pred['up_probability']*100:.1f}%，"
                    index_text += f"当前{pred['current_value']:.2f}，今日{pred['change_pct']:+.2f}%"
                    # 换行处理
                    wrapped_index_text = textwrap.fill(index_text, width=28)
                    index_lines = wrapped_index_text.split('\n')
                    for line in index_lines:
                        if y_pos < min_y:
                            break
                        market_ax.text(margin_left + 0.02, y_pos, line, 
                                      fontsize=9, ha='left', va='top',
                                      transform=market_ax.transAxes)
                        y_pos -= line_height
                    y_pos -= 0.02  # 项目间距
        
        # 添加边框
        market_ax.add_patch(plt.Rectangle((margin_left, margin_bottom), 
                                          content_width, content_height, 
                                          fill=False, edgecolor='darkblue', 
                                          linewidth=2, linestyle='-',
                                          transform=market_ax.transAxes))
        
        # 6. 个股行情预测（第二行右半部分，固定大小）
        stock_ax = fig.add_subplot(gs[1, 2:])
        stock_ax.axis('off')  # 不显示坐标轴
        stock_ax.set_xlim(0, 1)
        stock_ax.set_ylim(0, 1)
        
        # 显示个股预测总结
        summary = prediction_result.get('summary')
        
        # 计算可用区域（留出边距）
        margin_left = 0.03
        margin_right = 0.03
        margin_top = 0.02
        margin_bottom = 0.02
        content_width = 1 - margin_left - margin_right
        content_height = 1 - margin_top - margin_bottom
        
        y_pos = 1 - margin_top
        
        # 标题
        title_height = 0.08
        stock_ax.text(margin_left + 0.02, y_pos - 0.01, '【个股预测分析】', 
                     fontsize=12, fontweight='bold', ha='left',
                     color='darkgreen',
                     transform=stock_ax.transAxes,
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.5))
        y_pos -= title_height + 0.05
        
        # 获取各项指标（每个指标一行显示）
        factors = prediction_result.get('factors', {})
        min_y = margin_bottom + 0.05
        line_height = 0.08
        font_size = 9
        text_width = 28
        
        # 1. 技术指标
        if 'technical' in factors:
            tech = factors['technical']
            tech_score = tech.get('score', 0)
            tech_trend = tech.get('trend', '中性')
            trend_text = {'up': '偏多', 'down': '偏空', 'neutral': '中性'}.get(tech_trend, '中性')
            tech_text = f"技术指标: 得分{tech_score:.2f}（{trend_text}，趋势：{tech_trend}）"
            if y_pos >= min_y:
                stock_ax.text(margin_left + 0.02, y_pos, tech_text,
                              fontsize=font_size, ha='left', va='top', color='darkgreen',
                              transform=stock_ax.transAxes)
                y_pos -= line_height
            y_pos -= 0.02
        
        # 2. 新闻情感
        if 'news' in factors:
            news = factors['news']
            news_score = news.get('score', 0)
            news_sent = news.get('sentiment', '中性')
            news_count = news.get('news_count', 0)
            news_text = f"新闻情感: {news_sent}（得分{news_score:.2f}，新闻条数{news_count}）"
            
            # 如果有利空/利好统计，追加到同一行
            positive_count = news.get('positive_count', 0)
            negative_count = news.get('negative_count', 0)
            if positive_count > 0 or negative_count > 0:
                news_text += f"，利好消息{positive_count}条，利空消息{negative_count}条"
            
            # 如果有权重调整
            weight_multiplier = news.get('weight_multiplier', 1.0)
            if weight_multiplier != 1.0:
                if weight_multiplier > 1.0:
                    news_text += f"，权重提升{((weight_multiplier - 1) * 100):.0f}%"
                else:
                    news_text += f"，权重降低{((1 - weight_multiplier) * 100):.0f}%"
            
            if y_pos >= min_y:
                stock_ax.text(margin_left + 0.02, y_pos, news_text,
                              fontsize=font_size, ha='left', va='top', color='darkgreen',
                              transform=stock_ax.transAxes)
                y_pos -= line_height
            y_pos -= 0.02
        
        # 3. 市场情绪
        if 'market' in factors:
            market = factors['market']
            market_score = market.get('score', 0)
            market_trend = market.get('trend', '中性')
            market_text = f"市场情绪: 得分{market_score:.2f}（趋势：{market_trend}）"
            if y_pos >= min_y:
                stock_ax.text(margin_left + 0.02, y_pos, market_text,
                              fontsize=font_size, ha='left', va='top', color='darkgreen',
                              transform=stock_ax.transAxes)
                y_pos -= line_height
            y_pos -= 0.02
        
        # 4. 历史模式
        if 'history' in factors:
            history = factors['history']
            history_score = history.get('score', 0)
            history_pattern = history.get('pattern', '无')
            history_text = f"历史模式: 得分{history_score:.2f}（{history_pattern}）"
            if y_pos >= min_y:
                stock_ax.text(margin_left + 0.02, y_pos, history_text,
                              fontsize=font_size, ha='left', va='top', color='darkgreen',
                              transform=stock_ax.transAxes)
                y_pos -= line_height
            y_pos -= 0.02
        
        # 【已优化移除】5. 美股板块 - 已从预测模型中移除
        # if 'us_sector' in factors:
        #     us_sector = factors['us_sector']
        #     sector_name = us_sector.get('sector', '')
        #     if sector_name and sector_name != 'unknown':
        #         us_score = us_sector.get('score', 0)
        #         us_trend = us_sector.get('trend', '中性')
        #         change_pct = us_sector.get('change_pct', 0)
        #         us_text = f"美股板块: {sector_name}（得分{us_score:.2f}，趋势：{us_trend}，涨跌幅{change_pct:+.2f}%）"
        #         if y_pos >= min_y:
        #             stock_ax.text(margin_left + 0.02, y_pos, us_text,
        #                           fontsize=font_size, ha='left', va='top', color='darkgreen',
        #                           transform=stock_ax.transAxes)
        #             y_pos -= line_height
        #         y_pos -= 0.02
        
        # 【已优化移除】6. 估值指标 - 已从预测模型中移除
        # if 'valuation' in factors:
        #     valuation = factors['valuation']
        #     val_score = valuation.get('score', 0)
        #     val_status = valuation.get('valuation', '未知')
        #     pe_ratio = valuation.get('pe_ratio')
        #     pb_ratio = valuation.get('pb_ratio')
        #     
        #     val_text = f"估值指标: 得分{val_score:.2f}（估值：{val_status}"
        #     if pe_ratio:
        #         val_text += f"，PE：{pe_ratio}"
        #     if pb_ratio:
        #         val_text += f"，PB：{pb_ratio}"
        #     val_text += "）"
        #     if y_pos >= min_y:
        #         stock_ax.text(margin_left + 0.02, y_pos, val_text,
        #                       fontsize=font_size, ha='left', va='top', color='darkgreen',
        #                       transform=stock_ax.transAxes)
        #         y_pos -= line_height
        #     y_pos -= 0.02
        
        # 7. 综合预测结果
        prediction = prediction_result.get('prediction', '震荡')
        up_prob = prediction_result.get('up_probability', 0) * 100
        down_prob = prediction_result.get('down_probability', 0) * 100
        confidence_val = prediction_result.get('confidence', 0) * 100
        
        y_pos -= 0.02  # 分隔线间距
        final_text = f"综合预测: {prediction}，上涨概率{up_prob:.1f}%，下跌概率{down_prob:.1f}%，置信度{confidence_val:.1f}%"
        if y_pos >= min_y:
            stock_ax.text(margin_left + 0.02, y_pos, final_text,
                          fontsize=font_size, ha='left', va='top', color='darkgreen',
                          fontweight='bold',
                          transform=stock_ax.transAxes)
            y_pos -= line_height
        
        # 添加边框
        stock_ax.add_patch(plt.Rectangle((margin_left, margin_bottom), 
                                         content_width, content_height, 
                                         fill=False, edgecolor='darkgreen', 
                                         linewidth=2, linestyle='-',
                                         transform=stock_ax.transAxes))
        
        # 7. 实时数据面板（第三行全宽，分成左右两半）
        # 左边：实时行情数据，右边：成本分布
        realtime_left_ax = fig.add_subplot(gs[2, :2])  # 左半部分
        realtime_left_ax.axis('off')
        realtime_left_ax.set_xlim(0, 1)
        realtime_left_ax.set_ylim(0, 1)
        
        cost_right_ax = fig.add_subplot(gs[2, 2:])  # 右半部分
        cost_right_ax.axis('off')
        cost_right_ax.set_xlim(0, 1)
        cost_right_ax.set_ylim(0, 1)
        
        # 左边：显示实时行情数据
        if realtime_quote:
            y_pos = 0.95
            realtime_left_ax.text(0.02, y_pos, "【实时行情数据】", 
                           fontsize=13, fontweight='bold', ha='left',
                           color='darkblue', transform=realtime_left_ax.transAxes)
            y_pos -= 0.15
            
            # 当前价格和涨跌幅
            current_price = realtime_quote.get('current_price', 0)
            change_pct = realtime_quote.get('change_pct', 0)
            change_amount = realtime_quote.get('change_amount', 0)
            
            # 根据涨跌设置颜色
            price_color = 'red' if change_pct < 0 else 'green' if change_pct > 0 else 'black'
            
            # 当前价格和涨跌幅（短文本，不需要换行）
            price_text = f"当前价格: {current_price:.2f}元"
            realtime_left_ax.text(0.05, y_pos, price_text, 
                               fontsize=11, fontweight='bold', ha='left',
                               color=price_color, transform=realtime_left_ax.transAxes)
            y_pos -= 0.12
            
            change_text = f"今日涨跌: {change_pct:+.2f}% ({change_amount:+.2f}元)"
            realtime_left_ax.text(0.05, y_pos, change_text, 
                               fontsize=10, ha='left',
                               color=price_color, transform=realtime_left_ax.transAxes)
            y_pos -= 0.12
            
            # 开盘价、最高价、最低价（一行显示，用 | 分隔）
            open_price = realtime_quote.get('open_price')
            high_price = realtime_quote.get('high_price')
            low_price = realtime_quote.get('low_price')
            pre_close = realtime_quote.get('pre_close')
            
            price_info_parts = []
            if open_price:
                price_info_parts.append(f"开盘: {open_price:.2f}元")
            if high_price:
                price_info_parts.append(f"最高: {high_price:.2f}元")
            if low_price:
                price_info_parts.append(f"最低: {low_price:.2f}元")
            if pre_close:
                price_info_parts.append(f"昨收: {pre_close:.2f}元")
            
            if price_info_parts:
                price_info_text = " | ".join(price_info_parts)
                # 使用更大的宽度（50个字符），充分利用框的宽度
                wrapped_price_info = textwrap.fill(price_info_text, width=50)
                for line in wrapped_price_info.split('\n'):
                    realtime_left_ax.text(0.05, y_pos, line, 
                                       fontsize=9, ha='left', transform=realtime_left_ax.transAxes)
                    y_pos -= 0.10
            
            # 换手率和振幅（一行显示）
            turnover_rate = realtime_quote.get('turnover_rate')
            amplitude = realtime_quote.get('amplitude')
            turnover_parts = []
            if turnover_rate:
                turnover_parts.append(f"换手率: {turnover_rate:.2f}%")
            if amplitude:
                turnover_parts.append(f"振幅: {amplitude:.2f}%")
            
            if turnover_parts:
                turnover_text = " | ".join(turnover_parts)
                wrapped_turnover = textwrap.fill(turnover_text, width=50)
                for line in wrapped_turnover.split('\n'):
                    realtime_left_ax.text(0.05, y_pos, line, 
                                       fontsize=9, ha='left', transform=realtime_left_ax.transAxes)
                    y_pos -= 0.10
            
            # 实时资金流向
            capital_flow = realtime_data.get('capital_flow', {}) if realtime_data else {}
            if capital_flow:
                y_pos = max(0.5, y_pos)  # 确保不超出边界
                realtime_left_ax.text(0.05, y_pos, "【资金流向】", 
                                   fontsize=11, fontweight='bold', ha='left',
                                   color='darkblue', transform=realtime_left_ax.transAxes)
                y_pos -= 0.12
                
                flow_trend = capital_flow.get('flow_trend', '未知')
                flow_color = 'green' if '流入' in flow_trend else 'red' if '流出' in flow_trend else 'gray'
                trend_text = f"趋势: {flow_trend}"
                realtime_left_ax.text(0.05, y_pos, trend_text, 
                                   fontsize=10, ha='left', color=flow_color,
                                   fontweight='bold', transform=realtime_left_ax.transAxes)
                y_pos -= 0.10
                
                main_inflow = capital_flow.get('main_net_inflow', 0)
                if main_inflow:
                    inflow_color = 'green' if main_inflow > 0 else 'red'
                    inflow_text = f"主力净流入: {main_inflow/10000:.2f}万元"
                    realtime_left_ax.text(0.05, y_pos, inflow_text, 
                                       fontsize=9, ha='left', color=inflow_color,
                                       transform=realtime_left_ax.transAxes)
                    y_pos -= 0.10
                
                total_inflow = capital_flow.get('total_net_inflow', 0)
                if total_inflow:
                    total_color = 'green' if total_inflow > 0 else 'red'
                    total_text = f"总净流入: {total_inflow/10000:.2f}万元"
                    realtime_left_ax.text(0.05, y_pos, total_text, 
                                       fontsize=9, ha='left', color=total_color,
                                       transform=realtime_left_ax.transAxes)
                    y_pos -= 0.10
            
            # 交易时段信息
            trading_time = realtime_data.get('trading_time', {}) if realtime_data else {}
            if trading_time:
                y_pos = max(0.2, y_pos - 0.1)
                session = trading_time.get('session', '')
                message = trading_time.get('message', '')
                is_trading = trading_time.get('is_trading', False)
                
                session_color = 'green' if is_trading else 'orange'
                session_text = f"时段: {message}"
                wrapped_session = textwrap.fill(session_text, width=50)
                for line in wrapped_session.split('\n'):
                    realtime_left_ax.text(0.05, y_pos, line, 
                                       fontsize=9, ha='left', color=session_color,
                                       transform=realtime_left_ax.transAxes)
                    y_pos -= 0.10
            
            # 添加左边实时数据边框
            realtime_left_ax.add_patch(plt.Rectangle((0.01, 0.05), 0.98, 0.9, 
                                               fill=False, edgecolor='blue', 
                                               linewidth=2, linestyle='--',
                                               transform=realtime_left_ax.transAxes))
        else:
            # 如果没有实时数据，显示提示
            realtime_left_ax.text(0.5, 0.5, "实时数据暂不可用\n（可能不在交易时间）", 
                           fontsize=12, ha='center', va='center',
                           color='gray', style='italic',
                           transform=realtime_left_ax.transAxes)
        
        # 右边：成本分布独立区域（历史 + 当日），单独圈起来显示
        cost_distribution = prediction_result.get('cost_distribution', {}) if isinstance(prediction_result, dict) else {}
        if isinstance(cost_distribution, dict):
            history_cost = cost_distribution.get('history') or {}
            intraday_cost = cost_distribution.get('intraday') or {}
            history_top = history_cost.get('top_levels') or []
            intraday_top = intraday_cost.get('top_levels') or []
            
            # 计算可用区域
            margin_left = 0.02
            margin_right = 0.02
            margin_top = 0.05
            margin_bottom = 0.05
            box_x = margin_left
            box_y = margin_bottom
            box_w = 1 - margin_left - margin_right
            box_h = 1 - margin_top - margin_bottom
            
            # 外框
            cost_right_ax.add_patch(plt.Rectangle((box_x, box_y), box_w, box_h,
                                                   fill=False, edgecolor='darkgreen',
                                                   linewidth=2, linestyle='-',
                                                   transform=cost_right_ax.transAxes))
            
            cy = box_y + box_h - 0.06
            cost_right_ax.text(box_x + 0.02, cy, "【成本分布（历史 & 当日）】",
                                 fontsize=11, fontweight='bold', ha='left',
                                 color='darkgreen', transform=cost_right_ax.transAxes)
            cy -= 0.12
            
            # 历史成本分布（支持换行，充分利用框的宽度）
            if history_top:
                h_texts = []
                for lvl in history_top:
                    try:
                        price = float(lvl.get('price', 0.0))
                        pct = float(lvl.get('volume_pct', 0.0))
                        h_texts.append(f"{price:.2f}元({pct:.1f}%)")
                    except Exception:
                        continue
                if h_texts:
                    history_line = "历史: " + "，".join(h_texts)
                    # 使用更大的宽度（55个字符），充分利用框的宽度
                    wrapped_history = textwrap.fill(history_line, width=55)
                    for line in wrapped_history.split('\n'):
                        if cy < box_y + 0.05:
                            break
                        cost_right_ax.text(box_x + 0.03, cy, line,
                                             fontsize=9, ha='left', va='top',
                                             color='darkgreen', transform=cost_right_ax.transAxes)
                        cy -= 0.10
            
            # 当日成本分布（支持换行，充分利用框的宽度）
            if intraday_top:
                i_texts = []
                for lvl in intraday_top:
                    try:
                        price = float(lvl.get('price', 0.0))
                        pct = float(lvl.get('volume_pct', 0.0))
                        i_texts.append(f"{price:.2f}元({pct:.1f}%)")
                    except Exception:
                        continue
                if i_texts:
                    intraday_line = "当日: " + "，".join(i_texts)
                    # 使用更大的宽度（55个字符），充分利用框的宽度
                    wrapped_intraday = textwrap.fill(intraday_line, width=55)
                    for line in wrapped_intraday.split('\n'):
                        if cy < box_y + 0.05:
                            break
                        cost_right_ax.text(box_x + 0.03, cy, line,
                                             fontsize=9, ha='left', va='top',
                                             color='darkgreen', transform=cost_right_ax.transAxes)
                        cy -= 0.10
            else:
                # 如果没有当日数据，显示提示
                if cy >= box_y + 0.05:
                    cost_right_ax.text(box_x + 0.03, cy, "当日: 暂无当日分时数据",
                                         fontsize=9, ha='left', va='top',
                                         color='gray', style='italic',
                                         transform=cost_right_ax.transAxes)
        else:
            # 如果没有成本分布数据，显示提示
            cost_right_ax.text(0.5, 0.5, "成本分布数据暂不可用", 
                           fontsize=12, ha='center', va='center',
                           color='gray', style='italic',
                           transform=cost_right_ax.transAxes)
        
        # 9. 30天趋势图（第四行全宽，动态交互式）
        if stock_data is not None and not stock_data.empty:
            ax4 = fig.add_subplot(gs[3, :])
            
            recent_data = stock_data.tail(30)  # 显示最近30天
            
            # 使用更动态的样式
            ax4.plot(recent_data.index, recent_data['close'], linewidth=2.5, 
                    label='收盘价', color='#3498db', marker='o', markersize=4)
            if 'low' in recent_data.columns and 'high' in recent_data.columns:
                ax4.fill_between(recent_data.index, recent_data['low'], recent_data['high'],
                                alpha=0.2, color='#3498db', label='价格区间')
            
            # 添加移动平均线使图表更动态
            ma5 = recent_data['close'].rolling(window=5).mean()
            ma10 = recent_data['close'].rolling(window=10).mean()
            ax4.plot(recent_data.index, ma5, linewidth=1.5, label='MA5', color='orange', linestyle='--')
            ax4.plot(recent_data.index, ma10, linewidth=1.5, label='MA10', color='red', linestyle='--')
            
            # 添加当前价格线
            current_price = prediction_result['current_price']
            ax4.axhline(y=current_price, color='r', linestyle='--', linewidth=2, 
                       label=f'当前价格: {current_price:.2f}元', alpha=0.7)
            
            ax4.set_xlabel('日期', fontsize=12)
            ax4.set_ylabel('价格 (元)', fontsize=12)
            date_desc = prediction_result.get('date_desc', '明天')
            ax4.set_title(f'{symbol} 最近30天价格走势图（动态）', fontsize=14, fontweight='bold')
            ax4.legend(loc='best', fontsize=10, ncol=5)
            ax4.grid(True, alpha=0.3, linestyle='--')
            
            # 旋转x轴标签
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # 8. 添加预测信息文本（放在图表下方）
        date_desc = prediction_result.get('date_desc', '明天')
        info_text = f"预测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        if target_date:
            info_text += f"预测日期({date_desc}): {target_date} | "
        info_text += f"置信度: {confidence*100:.1f}% | 预测方向: {prediction_result['prediction']}"
        
        fig.text(0.5, 0.02, 
                info_text,
                ha='center', fontsize=10, style='italic')
        
        plt.suptitle(f'{symbol} 股票预测分析报告', fontsize=16, fontweight='bold', y=0.99)
        
        # 保存图片到reports目录
        png_filename = os.path.join(self.reports_dir, f'prediction_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.savefig(png_filename, dpi=150, bbox_inches='tight')
        print(f"\n预测图表已保存: {png_filename}")
        
        # 在显示图表之前立即保存预测记录（先保存PNG路径，HTML路径稍后更新）
        # 动态导入logger
        import os as os_module
        project_root = os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__)))
        logger_spec = importlib.util.spec_from_file_location(
            "logger",
            os_module.path.join(project_root, "utils", "logger.py")
        )
        logger_module = importlib.util.module_from_spec(logger_spec)
        logger_spec.loader.exec_module(logger_module)
        get_logger = logger_module.get_logger
        logger = get_logger(__name__)
        
        logger.info("正在保存预测记录...")
        self.save_stock_record(symbol, prediction_result, png_filename, None)
        logger.info("预测记录已保存（PNG路径已记录，HTML路径将在生成后更新）")
        
        plt.show()
        
        # 8. 创建可交互的30天趋势图（可用鼠标查看每天数据，动态交互式）
        interactive_html = None
        if stock_data is not None and not stock_data.empty:
            recent_data = stock_data.tail(30).copy()
            recent_data = recent_data.reset_index()
            
            # 如果有完整的K线数据，使用蜡烛图
            has_ohlc = all(col in recent_data.columns for col in ['open', 'high', 'low', 'close'])
            
            x_values = recent_data['date'] if 'date' in recent_data.columns else recent_data.iloc[:, 0]

            if has_ohlc:
                # 蜡烛图（包含开高低收，悬停时显示每天详细价格）
                fig_interactive = go.Figure(data=[
                    go.Candlestick(
                        x=x_values,
                        open=recent_data['open'],
                        high=recent_data['high'],
                        low=recent_data['low'],
                        close=recent_data['close'],
                        name='价格',
                        hovertemplate=(
                            '日期: %{x|%Y-%m-%d}<br>' +
                            '开盘: %{open:.2f}<br>' +
                            '最高: %{high:.2f}<br>' +
                            '最低: %{low:.2f}<br>' +
                            '收盘: %{close:.2f}<extra></extra>'
                        )
                    )
                ])
            else:
                # 回退为折线图（只有收盘价）
                fig_interactive = go.Figure(data=[
                    go.Scatter(
                        x=x_values,
                        y=recent_data['close'],
                        mode='lines+markers',
                        name='收盘价',
                        hovertemplate=(
                            '日期: %{x|%Y-%m-%d}<br>' +
                            '收盘: %{y:.2f}<extra></extra>'
                        )
                    )
                ])
            
            fig_interactive.update_layout(
                title=f'{symbol} 最近30天价格走势（可交互）',
                xaxis_title='日期',
                yaxis_title='价格 (元)',
                xaxis_rangeslider_visible=False,
                hovermode='x'
            )
            
            interactive_html = os.path.join(self.reports_dir, f'prediction_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}_interactive.html')
            fig_interactive.write_html(interactive_html, auto_open=False)
            print(f"可交互的30天趋势图已保存为: {interactive_html}")
            print("用浏览器打开后，可以用鼠标悬停在任意一天上查看当天的价格等详细信息。")
        
        # 9. 创建完整的交互式HTML报告（包含可滚动的个股预测分析和实时数据）
        full_report_html = self._create_interactive_html_report(prediction_result, stock_data, realtime_data)
        
        # 更新预测记录，添加HTML报告路径
        if full_report_html:
            # logger在之前已经定义，可以直接使用
            logger.info("正在更新预测记录（添加HTML报告路径）...")
            self.save_stock_record(symbol, prediction_result, png_filename, full_report_html, interactive_html)
            logger.info("预测记录已更新（HTML路径已添加）")
        
        # 返回生成的文件路径
        return {
            'png_file': png_filename,
            'interactive_html': interactive_html,
            'full_report_html': full_report_html
        }
    
    def visualize_no_display(self, prediction_result: Dict, stock_data: pd.DataFrame = None):
        """
        可视化预测结果（不显示图表窗口，用于批量模式）
        
        Args:
            prediction_result: 预测结果字典
            stock_data: 股票历史数据（可选）
            
        Returns:
            包含文件路径的字典 {'png_file': ..., 'full_report_html': ...}
        """
        if not prediction_result.get('success', False):
            return None
        
        # 调用正常的visualize方法，但需要修改它不显示窗口
        # 我们复制visualize的逻辑，但去掉plt.show()
        
        # 创建图表 - 使用3行4列布局
        fig = plt.figure(figsize=(18, 14))
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3, 
                              height_ratios=[1, 1.2, 1.2],
                              width_ratios=[1, 1, 1, 1])
        
        symbol = prediction_result['symbol']
        up_prob = prediction_result['up_probability']
        down_prob = prediction_result['down_probability']
        confidence = prediction_result['confidence']
        target_date = prediction_result.get('target_date')
        
        # 复用visualize方法中的图表生成代码
        # （这里简化处理，直接调用visualize但捕获plt.show）
        # 更好的方法是提取图表生成逻辑到单独的方法
        
        # 暂时方案：使用matplotlib的非交互后端
        import matplotlib
        original_backend = matplotlib.get_backend()
        matplotlib.use('Agg')  # 使用非交互后端
        
        try:
            # 调用visualize方法生成图表（但不显示）
            # 我们需要修改visualize方法接受一个参数控制是否显示
            # 或者直接在这里重新实现
            result = self.visualize(prediction_result, stock_data)
            
            # 如果visualize方法调用了plt.show()，我们需要关闭figure
            plt.close('all')
            
            return result
        finally:
            # 恢复原始后端
            matplotlib.use(original_backend)
    
    def visualize_no_display_v2(self, prediction_result: Dict, stock_data: pd.DataFrame = None,
                                realtime_data: Dict = None):
        """
        可视化预测结果（已废弃：不再生成PNG/HTML文件，只保存数据到数据库）
        
        Args:
            prediction_result: 预测结果字典
            stock_data: 股票历史数据（可选，已废弃）
            realtime_data: 实时交易决策数据（可选，已废弃）
        
        Returns:
            dict: 返回空字典，不再生成文件
        """
        # 不再生成PNG/HTML文件，所有数据都保存到数据库
        # 返回空字典以保持接口兼容性
        try:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.debug(f"visualize_no_display_v2 已废弃，不再生成PNG/HTML文件，数据已保存到数据库")
        except:
            pass
        
        return {}
    
    def _create_interactive_html_report(self, prediction_result: Dict, stock_data: pd.DataFrame = None,
                                       realtime_data: Dict = None, monitor_html_file: str = None,
                                       refresh_interval: int = 60):
        """
        创建完整的交互式HTML报告，包含可滚动的个股预测分析和实时数据
        
        Args:
            prediction_result: 预测结果字典（优先使用，如果数据不完整则从数据库补充）
            stock_data: 股票历史数据（可选）
            realtime_data: 实时交易决策数据（可选）
            monitor_html_file: 监控模式专用文件名（固定文件名，每次覆盖）
            refresh_interval: 自动刷新间隔（秒），用于监控模式
        """
        symbol = prediction_result['symbol']
        
        # 数据一致性改进：如果传入的prediction_result不完整，尝试从数据库补充
        try:
            from utils.stock_prediction_db import StockPredictionDB
            from config_db import USE_DATABASE
            
            if USE_DATABASE:
                db = StockPredictionDB()
                # 尝试从数据库获取最新的预测数据（如果传入的数据不完整）
                if not prediction_result.get('factors') or not prediction_result.get('up_probability'):
                    latest_prediction = db.get_latest_prediction(symbol)
                    if latest_prediction:
                        # 补充缺失的数据
                        if not prediction_result.get('factors'):
                            prediction_result['factors'] = latest_prediction.get('factors', {})
                        if not prediction_result.get('up_probability'):
                            prediction_result['up_probability'] = latest_prediction.get('up_probability', 0.5)
                        if not prediction_result.get('down_probability'):
                            prediction_result['down_probability'] = latest_prediction.get('down_probability', 0.5)
                        if not prediction_result.get('confidence'):
                            prediction_result['confidence'] = latest_prediction.get('confidence', 0.5)
        except Exception as e:
            # 如果数据库读取失败，使用传入的数据（不中断流程）
            try:
                from utils.logger import get_logger
                logger = get_logger(__name__)
                logger.debug(f"从数据库补充数据失败，使用传入的数据: {str(e)}")
            except:
                pass
        summary = prediction_result.get('summary', '')
        market_overall = prediction_result.get('market_overall', {})
        trading_suggestions = prediction_result.get('trading_suggestions', {})
        date_desc = prediction_result.get('date_desc', '明天')
        target_date = prediction_result.get('target_date', '')
        cost_distribution = prediction_result.get('cost_distribution', {}) if isinstance(prediction_result, dict) else {}
        
        # 提取实时数据
        realtime_quote = realtime_data.get('quote', {}) if realtime_data else {}
        realtime_decision = realtime_data.get('decision', {}) if realtime_data else {}
        capital_flow = realtime_data.get('capital_flow', {}) if realtime_data else {}
        trading_time = realtime_data.get('trading_time', {}) if realtime_data else {}
        
        # 构建HTML内容（根据是否为监控模式添加自动刷新）
        refresh_meta = f'<meta http-equiv="refresh" content="{refresh_interval}">' if monitor_html_file else ''
        monitor_title = ' - 实时监控' if monitor_html_file else ''
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {refresh_meta}
    <title>{symbol} 股票预测分析报告{monitor_title}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .section {{
            margin: 20px 0;
            padding: 15px;
            border-radius: 5px;
        }}
        .market-section {{
            background-color: #e8f4f8;
            border-left: 4px solid #3498db;
        }}
        .stock-section {{
            background-color: #e8f8e8;
            border-left: 4px solid #2ecc71;
            max-height: 500px;
            overflow-y: auto;
            padding: 15px;
        }}
        .stock-section::-webkit-scrollbar {{
            width: 8px;
        }}
        .stock-section::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 4px;
        }}
        .stock-section::-webkit-scrollbar-thumb {{
            background: #888;
            border-radius: 4px;
        }}
        .stock-section::-webkit-scrollbar-thumb:hover {{
            background: #555;
        }}
        .trading-section {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
        }}
        h2 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        .summary-text {{
            line-height: 1.8;
            font-size: 14px;
            color: #333;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .trading-item {{
            margin: 10px 0;
            padding: 8px;
            background-color: white;
            border-radius: 3px;
        }}
        .label {{
            font-weight: bold;
            color: #555;
        }}
        .value {{
            color: #2c3e50;
            font-size: 16px;
        }}
        .index-item {{
            margin: 8px 0;
            padding: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{symbol} 股票预测分析报告</h1>
        <p style="text-align: center; color: #7f8c8d;">
            预测日期({date_desc}): {target_date} | 
            预测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
        
        <div class="section market-section">
            <h2>【市场整体行情预测】</h2>
"""
        
        # 添加市场整体行情预测
        if market_overall.get('success', False):
            market_pred = market_overall.get('overall_prediction', '震荡')
            market_up_prob = market_overall.get('overall_up_probability', 0.5) * 100
            market_down_prob = market_overall.get('overall_down_probability', 0.5) * 100
            
            html_content += f"""
            <p><strong>沪深股市整体预计{market_pred}</strong></p>
            <p>上涨概率: {market_up_prob:.1f}%，下跌概率: {market_down_prob:.1f}%</p>
"""
            
            index_predictions = market_overall.get('index_predictions', {})
            if index_predictions:
                html_content += "<h3>各指数预测详情：</h3>"
                for index_name, pred in index_predictions.items():
                    html_content += f"""
            <div class="index-item">
                <strong>{index_name}:</strong> {pred['prediction']} 
                (上涨{pred['up_probability']*100:.1f}%，当前{pred['current_value']:.2f}，今日{pred['change_pct']:+.2f}%)
            </div>
"""
        
        html_content += """
        </div>
        
        <div class="section stock-section">
            <h2>【个股预测分析】（可滚动查看完整内容）</h2>
            <div class="summary-text">
"""
        
        # 添加个股预测分析（按每个指标一行排列）
        factors = prediction_result.get('factors', {})
        
        # 1. 技术指标
        if 'technical' in factors:
            tech = factors['technical']
            html_content += f"""
            <div class="index-item">
                <strong>技术指标:</strong> 得分 {tech.get('score', 0):.2f} | 
                权重 {tech.get('weight', 0)*100:.1f}% | 
                趋势: {tech.get('trend', '中性')}
            </div>
"""
            # 显示技术指标信号
            signals = tech.get('signals', {})
            if signals:
                signal_text = ' | '.join([f"{k}: {v}" for k, v in signals.items()])
                html_content += f"""
            <div class="index-item" style="margin-left: 20px; font-size: 12px; color: #666;">
                信号: {signal_text}
            </div>
"""
        
        # 2. 新闻情感
        if 'news' in factors:
            news = factors['news']
            html_content += f"""
            <div class="index-item">
                <strong>新闻情感:</strong> 得分 {news.get('score', 0):.2f} | 
                权重 {news.get('weight', 0)*100:.1f}% | 
                情感: {news.get('sentiment', '中性')} | 
                新闻条数: {news.get('news_count', 0)}
            </div>
"""
            # 显示直接相关和行业相关新闻数量
            direct_news_count = news.get('direct_news_count', 0)
            industry_news_count = news.get('industry_news_count', 0)
            if direct_news_count > 0 or industry_news_count > 0:
                html_content += f"""
            <div class="index-item" style="margin-left: 20px; font-size: 12px; color: #666;">
                直接相关: {direct_news_count} 条 | 行业相关: {industry_news_count} 条
            </div>
"""
            # 显示利空/利好信息
            positive_count = news.get('positive_count', 0)
            negative_count = news.get('negative_count', 0)
            if positive_count > 0 or negative_count > 0:
                html_content += f"""
            <div class="index-item" style="margin-left: 20px; font-size: 12px; color: #666;">
                利好消息: {positive_count} 条 | 利空消息: {negative_count} 条
            </div>
"""
            weight_multiplier = news.get('weight_multiplier', 1.0)
            if weight_multiplier != 1.0:
                if weight_multiplier > 1.0:
                    html_content += f"""
            <div class="index-item" style="margin-left: 20px; font-size: 12px; color: #27ae60;">
                权重调整: 提升 {((weight_multiplier - 1) * 100):.0f}%
            </div>
"""
                else:
                    html_content += f"""
            <div class="index-item" style="margin-left: 20px; font-size: 12px; color: #e74c3c;">
                权重调整: 降低 {((1 - weight_multiplier) * 100):.0f}%
            </div>
"""
        
        # 3. 市场情绪
        if 'market' in factors:
            market = factors['market']
            html_content += f"""
            <div class="index-item">
                <strong>市场情绪:</strong> 得分 {market.get('score', 0):.2f} | 
                权重 {market.get('weight', 0)*100:.1f}% | 
                趋势: {market.get('trend', '中性')}
            </div>
"""
        
        # 4. 历史模式
        if 'history' in factors:
            history = factors['history']
            html_content += f"""
            <div class="index-item">
                <strong>历史模式:</strong> 得分 {history.get('score', 0):.2f} | 
                权重 {history.get('weight', 0)*100:.1f}% | 
                模式: {history.get('pattern', '无')}
            </div>
"""
        
        # 【已优化移除】5. 美股板块 - 已从预测模型中移除
        # if 'us_sector' in factors:
        #     us_sector = factors['us_sector']
        #     sector_name = us_sector.get('sector', '')
        #     if sector_name:
        #         html_content += f"""
        #     <div class="index-item">
        #         <strong>美股板块:</strong> 得分 {us_sector.get('score', 0):.2f} | 
        #         权重 {us_sector.get('weight', 0)*100:.1f}% | 
        #         板块: {sector_name} | 
        #         趋势: {us_sector.get('trend', '中性')}
        #     </div>
        # """
        #         change_pct = us_sector.get('change_pct', 0)
        #         if change_pct:
        #             html_content += f"""
        #     <div class="index-item" style="margin-left: 20px; font-size: 12px; color: #666;">
        #         涨跌幅: {change_pct:+.2f}%
        #     </div>
        # """
        
        # 【已优化移除】6. 估值指标 - 已从预测模型中移除
        # if 'valuation' in factors:
        #     valuation = factors['valuation']
        #     html_content += f"""
        #     <div class="index-item">
        #         <strong>估值指标:</strong> 得分 {valuation.get('score', 0):.2f} | 
        #         权重 {valuation.get('weight', 0)*100:.1f}% | 
        #         估值: {valuation.get('valuation', '未知')}
        #     </div>
        # """
        #     pe_ratio = valuation.get('pe_ratio')
        #     pb_ratio = valuation.get('pb_ratio')
        #     if pe_ratio or pb_ratio:
        #         val_info = []
        #         if pe_ratio:
        #             val_info.append(f"PE: {pe_ratio}")
        #         if pb_ratio:
        #             val_info.append(f"PB: {pb_ratio}")
        #         html_content += f"""
        #     <div class="index-item" style="margin-left: 20px; font-size: 12px; color: #666;">
        #         {', '.join(val_info)}
        #     </div>
        # """
        
        # 7. 成本分布（历史 + 当日），并在鼠标悬停时显示计算公式
        if isinstance(cost_distribution, dict):
            history_cost = cost_distribution.get('history') or {}
            intraday_cost = cost_distribution.get('intraday') or {}
            history_top = history_cost.get('top_levels') or []
            intraday_top = intraday_cost.get('top_levels') or []

            if history_top or intraday_top:
                html_content += """
            <div class="index-item" style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #2ecc71;">
                <strong>成本分布（历史 & 当日）:</strong>
            </div>
"""
            # 历史成本分布（最近N天日线）
            if history_top:
                h_texts = []
                for lvl in history_top:
                    try:
                        price = float(lvl.get('price', 0.0))
                        pct = float(lvl.get('volume_pct', 0.0))
                        h_texts.append(f"{price:.2f}元({pct:.1f}%)")
                    except Exception:
                        continue
                if h_texts:
                    history_formula = (
                        "计算公式：使用最近N天日线收盘价与对应成交量，将价格划分为若干档位，"
                        "每档成交量 = 落在该价位区间内的成交量之和，"
                        "成交量占比 = 该档成交量 / 全部档成交量 × 100%。"
                    )
                    html_content += f"""
            <div class="index-item" style="margin-left: 20px; font-size: 13px; color: #2c3e50;"
                 title="{history_formula}">
                历史成本分布: 主要成本区 {'，'.join(h_texts)}
            </div>
"""
            # 当日成本分布（分时）
            if intraday_top:
                i_texts = []
                for lvl in intraday_top:
                    try:
                        price = float(lvl.get('price', 0.0))
                        pct = float(lvl.get('volume_pct', 0.0))
                        i_texts.append(f"{price:.2f}元({pct:.1f}%)")
                    except Exception:
                        continue
                if i_texts:
                    intraday_formula = (
                        "计算公式：使用当日分时价格与对应成交量，将价格划分为若干档位，"
                        "每档成交量 = 落在该价位区间内的成交量之和，"
                        "成交量占比 = 该档成交量 / 全部档成交量 × 100%。"
                    )
                    html_content += f"""
            <div class="index-item" style="margin-left: 20px; font-size: 13px; color: #2c3e50;"
                 title="{intraday_formula}">
                当日成本分布: 主要成本区 {'，'.join(i_texts)}
            </div>
"""
        
        # 8. 综合预测结果
        html_content += f"""
            <div class="index-item" style="margin-top: 15px; padding-top: 10px; border-top: 2px solid #2ecc71;">
                <strong>综合预测:</strong> 
                预测方向: {prediction_result.get('prediction', '震荡')} | 
                上涨概率: {prediction_result.get('up_probability', 0)*100:.1f}% | 
                下跌概率: {prediction_result.get('down_probability', 0)*100:.1f}% | 
                置信度: {prediction_result.get('confidence', 0)*100:.1f}%
            </div>
"""
        
        # 9. 详细摘要（如果有）
        if summary:
            html_content += f"""
            <div class="index-item" style="margin-top: 15px; padding-top: 10px; border-top: 1px dashed #ccc;">
                <strong>详细分析摘要:</strong>
            </div>
            <div class="summary-text" style="margin-left: 20px; margin-top: 5px;">
                {summary.replace('。', '。\n')}
            </div>
"""
        
        html_content += """
            </div>
        </div>
        
        <div class="section trading-section">
            <h2>【交易建议】</h2>
"""
        
        # 添加交易建议
        if trading_suggestions:
            buy_price = trading_suggestions.get('buy_price')
            if buy_price:
                html_content += f"""
            <div class="trading-item">
                <span class="label">买入建议价:</span>
                <span class="value"> {buy_price:.2f}元</span>
            </div>
"""
            
            sell_price = trading_suggestions.get('sell_price')
            if sell_price:
                html_content += f"""
            <div class="trading-item">
                <span class="label">卖出建议价:</span>
                <span class="value"> {sell_price:.2f}元</span>
            </div>
"""
            
            auction_entry = trading_suggestions.get('auction_entry', False)
            auction_price = trading_suggestions.get('auction_price')
            auction_reason = trading_suggestions.get('auction_reason', '')
            if auction_entry and auction_price:
                html_content += f"""
            <div class="trading-item">
                <span class="label">竞价进入:</span>
                <span class="value"> 建议，价格: {auction_price:.2f}元</span>
            </div>
"""
                if auction_reason:
                    html_content += f"""
            <div class="trading-item" style="font-size: 12px; color: #555; font-style: italic;">
                <span class="label">理由:</span>
                <span>{auction_reason}</span>
            </div>
"""
            else:
                html_content += f"""
            <div class="trading-item">
                <span class="label">竞价建议:</span>
                <span class="value">{auction_reason if auction_reason else '不建议'}</span>
            </div>
"""
            
            stop_loss = trading_suggestions.get('stop_loss')
            take_profit = trading_suggestions.get('take_profit')
            if stop_loss:
                html_content += f"""
            <div class="trading-item">
                <span class="label">止损价:</span>
                <span class="value"> {stop_loss:.2f}元</span>
            </div>
"""
            if take_profit:
                html_content += f"""
            <div class="trading-item">
                <span class="label">止盈价:</span>
                <span class="value"> {take_profit:.2f}元</span>
            </div>
"""
        
        # 添加实时数据展示（如果有）
        if realtime_quote or realtime_decision:
            html_content += """
        </div>
        
        <div class="section" style="background-color: #e3f2fd; border-left: 4px solid #2196f3;">
            <h2>【实时行情与交易决策】</h2>
"""
            
            # 实时行情数据
            if realtime_quote:
                current_price = realtime_quote.get('current_price', 0)
                change_pct = realtime_quote.get('change_pct', 0)
                change_amount = realtime_quote.get('change_amount', 0)
                open_price = realtime_quote.get('open_price')
                high_price = realtime_quote.get('high_price')
                low_price = realtime_quote.get('low_price')
                pre_close = realtime_quote.get('pre_close')
                turnover_rate = realtime_quote.get('turnover_rate')
                amplitude = realtime_quote.get('amplitude')
                
                price_color = 'red' if change_pct < 0 else 'green' if change_pct > 0 else 'black'
                
                html_content += f"""
            <h3 style="color: #1976d2;">实时行情</h3>
            <div class="trading-item">
                <span class="label">当前价格:</span>
                <span class="value" style="color: {price_color}; font-size: 18px; font-weight: bold;">
                    {current_price:.2f}元
                </span>
                <span style="color: {price_color}; margin-left: 10px;">
                    {change_pct:+.2f}% ({change_amount:+.2f}元)
                </span>
            </div>
"""
                if open_price or high_price or low_price or pre_close:
                    html_content += """
            <div class="trading-item" style="display: flex; gap: 20px;">
"""
                    if open_price:
                        html_content += f'<span>开盘: {open_price:.2f}元</span>'
                    if high_price:
                        html_content += f'<span style="color: red;">最高: {high_price:.2f}元</span>'
                    if low_price:
                        html_content += f'<span style="color: green;">最低: {low_price:.2f}元</span>'
                    if pre_close:
                        html_content += f'<span>昨收: {pre_close:.2f}元</span>'
                    html_content += """
            </div>
"""
                if turnover_rate or amplitude:
                    html_content += """
            <div class="trading-item" style="display: flex; gap: 20px;">
"""
                    if turnover_rate:
                        html_content += f'<span>换手率: {turnover_rate:.2f}%</span>'
                    if amplitude:
                        html_content += f'<span>振幅: {amplitude:.2f}%</span>'
                    html_content += """
            </div>
"""
            
            # 实时资金流向
            if capital_flow:
                flow_trend = capital_flow.get('flow_trend', '未知')
                main_inflow = capital_flow.get('main_net_inflow', 0)
                total_inflow = capital_flow.get('total_net_inflow', 0)
                
                flow_color = 'green' if '流入' in flow_trend else 'red' if '流出' in flow_trend else 'gray'
                
                html_content += f"""
            <h3 style="color: #1976d2; margin-top: 15px;">资金流向</h3>
            <div class="trading-item">
                <span class="label">资金流向趋势:</span>
                <span class="value" style="color: {flow_color}; font-weight: bold;">{flow_trend}</span>
            </div>
"""
                if main_inflow:
                    inflow_color = 'green' if main_inflow > 0 else 'red'
                    html_content += f"""
            <div class="trading-item">
                <span class="label">主力净流入:</span>
                <span style="color: {inflow_color};">
                    {main_inflow/10000:.2f}万元
                </span>
            </div>
"""
                if total_inflow:
                    total_color = 'green' if total_inflow > 0 else 'red'
                    html_content += f"""
            <div class="trading-item">
                <span class="label">总净流入:</span>
                <span style="color: {total_color};">
                    {total_inflow/10000:.2f}万元
                </span>
            </div>
"""
            
            # 实时交易决策
            if realtime_decision:
                action_cn = realtime_decision.get('action_cn', '未知')
                strength_cn = realtime_decision.get('strength_cn', '未知')
                reasons = realtime_decision.get('reasons', [])
                price_suggestions = realtime_decision.get('price_suggestions', {})
                
                action_color = 'green' if realtime_decision.get('action') in ['BUY', 'ADD'] else \
                              'red' if realtime_decision.get('action') in ['SELL', 'REDUCE'] else 'orange'
                
                html_content += f"""
            <h3 style="color: #1976d2; margin-top: 15px;">实时交易决策</h3>
            <div class="trading-item">
                <span class="label">操作建议:</span>
                <span class="value" style="color: {action_color}; font-size: 16px; font-weight: bold;">
                    {action_cn}
                </span>
                <span style="margin-left: 10px; color: #555;">({strength_cn})</span>
            </div>
"""
                if reasons:
                    html_content += """
            <div class="trading-item">
                <span class="label">决策理由:</span>
                <ul style="margin: 5px 0; padding-left: 20px;">
"""
                    for reason in reasons[:3]:  # 最多显示3条
                        html_content += f'<li style="margin: 5px 0;">{reason}</li>'
                    html_content += """
                </ul>
            </div>
"""
                if price_suggestions:
                    html_content += """
            <div class="trading-item">
                <span class="label">价格建议:</span>
                <div style="margin-left: 20px; margin-top: 5px;">
"""
                    if 'ideal_buy' in price_suggestions:
                        html_content += f"""
                    <div>理想买入价: <span style="color: green; font-weight: bold;">{price_suggestions['ideal_buy']:.2f}元</span></div>
                    <div>止损价: <span style="color: red;">{price_suggestions.get('stop_loss', 'N/A')}</span></div>
                    <div>目标价: <span style="color: blue;">{price_suggestions.get('target', 'N/A')}</span></div>
"""
                    if 'ideal_sell' in price_suggestions:
                        html_content += f"""
                    <div>理想卖出价: <span style="color: red; font-weight: bold;">{price_suggestions['ideal_sell']:.2f}元</span></div>
"""
                    html_content += """
                </div>
            </div>
"""
            
            # 交易时段
            if trading_time:
                message = trading_time.get('message', '')
                is_trading = trading_time.get('is_trading', False)
                session_color = 'green' if is_trading else 'orange'
                html_content += f"""
            <div class="trading-item" style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ccc;">
                <span class="label">交易时段:</span>
                <span style="color: {session_color}; font-weight: bold;">{message}</span>
            </div>
"""
        
        html_content += """
        </div>
    </div>
</body>
</html>
"""
        
        # 保存HTML文件到reports目录
        if monitor_html_file:
            # 监控模式：使用固定文件名（每次覆盖）
            html_filename = monitor_html_file
            # 在HTML中添加监控模式标识
            html_content = html_content.replace(
                f'<h1>{symbol} 股票预测分析报告</h1>',
                f'<h1>{symbol} 股票预测分析报告 - <span style="color: #e74c3c;">实时监控模式</span></h1>'
            )
        else:
            # 普通模式：使用时间戳文件名
            html_filename = os.path.join(self.reports_dir, f'prediction_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}_full_report.html')
        
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if monitor_html_file:
            logger.info(f"监控页面已更新: {html_filename} (每 {refresh_interval} 秒自动刷新)")
        else:
            print(f"\n完整的交互式HTML报告已保存为: {html_filename}")
            print("用浏览器打开后，个股预测分析部分可以滚动查看完整内容。")
        
        return html_filename
    
    def visualize_simple(self, prediction_result: Dict):
        """
        简化版可视化（仅显示关键信息）
        """
        if not prediction_result.get('success', False):
            print("预测失败")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        symbol = prediction_result['symbol']
        up_prob = prediction_result['up_probability']
        down_prob = prediction_result['down_probability']
        
        # 概率饼图
        ax1 = axes[0]
        colors = ['#2ecc71', '#e74c3c']
        sizes = [up_prob, down_prob]
        labels = [f'上涨 {up_prob*100:.1f}%', f'下跌 {down_prob*100:.1f}%']
        
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                shadow=True, startangle=90)
        ax1.set_title(f'{symbol} 明日涨跌概率', fontsize=14, fontweight='bold')
        
        # 概率柱状图
        ax2 = axes[1]
        categories = ['上涨', '下跌']
        probabilities = [up_prob * 100, down_prob * 100]
        colors_bar = ['#2ecc71', '#e74c3c']
        
        bars = ax2.bar(categories, probabilities, color=colors_bar, alpha=0.7)
        ax2.set_ylabel('概率 (%)', fontsize=12)
        ax2.set_ylim(0, 100)
        ax2.set_title('涨跌概率对比', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        for bar, prob in zip(bars, probabilities):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{prob:.1f}%',
                    ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        filename = os.path.join(self.reports_dir, f'prediction_{symbol}_simple.png')
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n预测图表已保存: {filename}")
        
        plt.show()
    
    def save_stock_record(self, symbol: str, prediction_result: Dict, png_file: str = None, full_report_html: str = None, interactive_html: str = None):
        """
        保存股票预测记录（仅保存到数据库，不生成文件）
        
        Args:
            symbol: 股票代码
            prediction_result: 预测结果字典
            png_file: PNG图片文件路径（已废弃，不再使用）
            full_report_html: 完整HTML报告文件路径（已废弃，不再使用）
            interactive_html: 交互式HTML路径（已废弃，不再使用）
        """
        import os
        import importlib.util
        
        # 只使用数据库保存
        try:
            import sys
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # 为避免与其他路径中的 utils 包冲突，这里使用 importlib 直接按文件路径加载
            sys.path.insert(0, project_root)
            db_spec = importlib.util.spec_from_file_location(
                "stock_prediction_db",
                os.path.join(project_root, "utils", "stock_prediction_db.py")
            )
            db_module = importlib.util.module_from_spec(db_spec)
            db_spec.loader.exec_module(db_module)
            StockPredictionDB = db_module.StockPredictionDB
            from config_db import USE_DATABASE
            
            if USE_DATABASE:
                db = StockPredictionDB()
                # png_file, interactive_html, full_report_html 都传None，不再保存文件路径
                # 从prediction_result中获取prediction_type，默认为'after_close'
                prediction_type = prediction_result.get('prediction_type', 'after_close')
                success = db.save_prediction(symbol, prediction_result, None, None, None, prediction_type=prediction_type)
                if success:
                    # 性能优化：不再每次保存后立即更新历史数据
                    # 改为在批量预测完成后统一更新一次（由调用方负责）
                    # 这样可以避免重复更新，大幅提升性能
                    
                    # 使用logger记录成功信息
                    try:
                        from utils.logger import get_logger
                        logger = get_logger(__name__)
                        logger.info(f"预测记录已保存到数据库: {symbol}")
                        logger.debug(f"  股票代码: {symbol} | 预测日期: {prediction_result.get('prediction_date', '')} | 目标日期: {prediction_result.get('target_date', '')}")
                    except:
                        print(f"预测记录已保存到数据库: {symbol}")
                        print(f"  股票代码: {symbol} | 预测日期: {prediction_result.get('prediction_date', '')} | 目标日期: {prediction_result.get('target_date', '')}")
                    return
                else:
                    # 数据库保存失败
                    try:
                        from utils.logger import get_logger
                        logger = get_logger(__name__)
                        logger.error(f"数据库保存失败: {symbol}")
                    except:
                        print(f"数据库保存失败: {symbol}")
                    return
            else:
                # 数据库未启用
                try:
                    from utils.logger import get_logger
                    logger = get_logger(__name__)
                    logger.warning(f"数据库未启用，无法保存预测记录: {symbol}")
                except:
                    print(f"数据库未启用，无法保存预测记录: {symbol}")
                return
        except Exception as e:
            # 数据库保存异常
            try:
                from utils.logger import get_logger
                logger = get_logger(__name__)
                logger.error(f"数据库保存异常: {symbol}, 错误: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            except:
                print(f"数据库保存异常: {symbol}, 错误: {str(e)}")
                import traceback
                traceback.print_exc()
            return
        
        # 不再支持CSV模式，所有数据必须保存到数据库
        # 如果数据库保存失败，记录错误并返回
    
    def create_stock_list_page(self):
        """
        创建股票预测列表页面（已废弃：不再生成HTML，数据从数据库读取）
        
        Returns:
            dict: 返回空结果，不再生成HTML页面
        """
        # 不再生成HTML页面，所有数据都从数据库读取（页面由前端通过API动态获取）
        try:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.debug(f"create_stock_list_page 已废弃，不再生成HTML页面，数据从数据库读取")
        except:
            pass
        
        return {
            'html_file': None,
            'total_records': 0,
            'total_stocks': 0,
            'latest_symbols': [],
            'success': True  # 返回成功，但不生成文件
        }
        
        # 动态导入logger
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logger_spec = importlib.util.spec_from_file_location(
            "logger",
            os.path.join(project_root, "utils", "logger.py")
        )
        logger_module = importlib.util.module_from_spec(logger_spec)
        logger_spec.loader.exec_module(logger_module)
        get_logger = logger_module.get_logger
        logger = get_logger(__name__)
        
        # 获取项目根目录，确保CSV文件路径正确
        csv_file = os.path.join(project_root, 'stock_predictions.csv')
        html_file = os.path.join(project_root, 'stock_list.html')
        
        logger.debug(f"正在读取CSV文件: {csv_file}")
        logger.debug(f"CSV文件是否存在: {os.path.exists(csv_file)}")
        
        result_info = {
            'html_file': html_file,
            'total_records': 0,
            'total_stocks': 0,
            'latest_symbols': [],
            'success': False
        }
        
        if not os.path.exists(csv_file):
            # CSV文件不存在，生成空列表页面
            logger.debug("CSV文件不存在，生成空列表页面")
            html_content = self._generate_empty_stock_list_html()
        else:
                try:
                    logger.debug(f"正在读取CSV文件内容...")
                    df = pd.read_csv(csv_file, dtype={'symbol': str}, encoding='utf-8-sig')
                    logger.debug(f"CSV文件读取成功，共 {len(df)} 行数据")
                    
                    # 转换为字典列表，处理NaN值
                    for idx, row in df.iterrows():
                        record = {}
                        for col in df.columns:
                            value = row[col]
                            # 处理NaN值和类型转换
                            if pd.isna(value):
                                if col in ['current_price', 'up_probability', 'down_probability', 'confidence']:
                                    value = 0
                                else:
                                    value = ''
                            # 确保数值类型正确
                            elif col in ['current_price', 'up_probability', 'down_probability', 'confidence']:
                                try:
                                    value = float(value)
                                except (ValueError, TypeError):
                                    value = 0
                            record[col] = value
                        records.append(record)
                except Exception as e:
                    import traceback
                    logger.warning(f"读取CSV文件失败: {e}")
                    logger.debug(f"错误详情: {traceback.format_exc()}")
                    html_content = self._generate_empty_stock_list_html()
                    return result_info
        
        # 处理记录数据
        result_info['total_records'] = len(records)
        
        if not records:
            logger.debug("记录为空，生成空列表页面")
            html_content = self._generate_empty_stock_list_html()
        else:
            logger.debug(f"正在生成包含 {len(records)} 条记录的列表页面...")
            html_content = self._generate_stock_list_html(records)
            
            # 为每个股票生成历史预测页面
            unique_symbols = set()
            for record in records:
                symbol = str(record.get('symbol', '')).strip()
                if symbol:
                    unique_symbols.add(symbol)
            
            result_info['total_stocks'] = len(unique_symbols)
            
            # 获取最新的几只股票（按预测时间排序）
            try:
                if records:
                    # 按prediction_time排序，获取最新的股票
                    sorted_records = sorted(records, key=lambda x: x.get('prediction_time', ''), reverse=True)
                    latest_symbols = []
                    seen_symbols = set()
                    for record in sorted_records:
                        symbol = str(record.get('symbol', '')).strip()
                        if symbol and symbol not in seen_symbols:
                            latest_symbols.append(symbol)
                            seen_symbols.add(symbol)
                            if len(latest_symbols) >= 5:
                                break
                    result_info['latest_symbols'] = latest_symbols
            except Exception as e:
                logger.debug(f"获取最新股票列表失败: {e}")
            
            logger.debug(f"正在为 {len(unique_symbols)} 只股票生成历史预测页面...")
            history_success_count = 0
            for symbol in unique_symbols:
                try:
                    self.create_stock_history_page(symbol)
                    history_success_count += 1
                except Exception as e:
                    logger.debug(f"生成 {symbol} 的历史预测页面失败: {e}")
            logger.debug(f"历史预测页面生成完成: {history_success_count}/{len(unique_symbols)}")
        
        # 保存HTML文件
        try:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            result_info['success'] = True
            logger.debug(f"股票列表页面已生成: {html_file}")
        except Exception as e:
            logger.error(f"保存HTML文件失败: {e}")
            result_info['success'] = False
        
        return result_info
    
    def _update_historical_actual_data(self, include_today: bool = True):
        """
        更新历史预测记录的实际数据（从数据库读取，更新到数据库）
        
        逻辑：
          - 从数据库读取所有 target_date <= 今天 且 actual_price 为空的记录（如果include_today=True）
          - 或 target_date < 今天 且 actual_price 为空的记录（如果include_today=False）
          - 调用 StockDataSource.get_actual_stock_change(symbol, target_date) 获取实际数据
          - 更新数据库中的 actual_price / actual_change_pct / actual_direction / prediction_hit
          - 同时计算并更新偏差字段：deviation_pct / absolute_deviation_pct / deviation_price
        
        Args:
            include_today: 是否包含今天的预测记录（默认True，用于设置页面预测后立即更新）
        """
        try:
            from datetime import datetime
            import importlib.util
            
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 从数据库读取需要更新的记录
            try:
                from utils.stock_prediction_db import StockPredictionDB
                from config_db import USE_DATABASE
                
                if not USE_DATABASE:
                    return
                
                db = StockPredictionDB()
                today = datetime.now().strftime('%Y-%m-%d')
                
                # 查询需要更新的记录（target_date <= 今天 且 actual_price 为空）
                # 同时查询预测值字段，用于计算偏差
                # 注意：使用 <= 而不是 <，这样可以更新今天的预测记录（如果实际数据已存在）
                from utils.db_connection import DatabaseConnection
                date_condition = "target_date <= %s" if include_today else "target_date < %s"
                sql = f"""
                    SELECT symbol, target_date, prediction, current_price,
                           predicted_change_pct, predicted_close_price
                    FROM stock_predictions 
                    WHERE {date_condition}
                    AND (actual_price IS NULL OR actual_price = '' OR actual_price = 0)
                """
                records = DatabaseConnection.execute_query(sql, (today,))
                
                if not records:
                    return
                
                # 动态导入 StockDataSource
                ds_spec = importlib.util.spec_from_file_location(
                    "stock_data_source_for_update",
                    os.path.join(project_root, "data_source", "stock_data_source.py")
                )
                ds_module = importlib.util.module_from_spec(ds_spec)
                ds_spec.loader.exec_module(ds_module)
                StockDataSourceForUpdate = ds_module.StockDataSource
                ds = StockDataSourceForUpdate()
                
                updated_count = 0
                for record in records:
                    symbol = str(record.get('symbol', '')).zfill(6)
                    target_date_str = str(record.get('target_date', '')).strip()
                    prediction = str(record.get('prediction', '')).strip()
                    current_price = float(record.get('current_price', 0)) if record.get('current_price') else None
                    predicted_change_pct = record.get('predicted_change_pct')
                    predicted_close_price = record.get('predicted_close_price')
                    
                    if not symbol or not target_date_str:
                        continue
                    
                    # 调用数据源获取实际表现
                    try:
                        actual = ds.get_actual_stock_change(symbol, target_date_str, current_price)
                    except Exception as e:
                        continue
                    
                    if not actual or actual.get('success') != True:
                        continue
                    
                    actual_price = actual.get('close')
                    actual_change_pct = actual.get('change_pct')
                    actual_dir = actual.get('direction', '')
                    
                    if actual_price is None or actual_change_pct is None:
                        continue
                    
                    # 计算 prediction_hit（优先用预测涨跌幅方向 vs 实际涨跌幅方向判断）
                    try:
                        change_val = float(actual_change_pct)
                    except Exception:
                        change_val = None
                    try:
                        pred_change_val = float(predicted_change_pct) if predicted_change_pct is not None else None
                    except Exception:
                        pred_change_val = None
                    
                    hit = '未知'
                    SIDEWAYS_THRESHOLD_PCT = 1.5  # 有预测涨跌幅时的震荡阈值
                    SIDEWAYS_THRESHOLD_LABEL = 1.0  # 无预测涨跌幅时的震荡阈值（标签判断）
                    
                    if change_val is not None:
                        if pred_change_val is not None:
                            # 优先用预测涨跌幅方向 vs 实际涨跌幅方向判断
                            pred_dir = '涨' if pred_change_val > SIDEWAYS_THRESHOLD_PCT else ('跌' if pred_change_val < -SIDEWAYS_THRESHOLD_PCT else '震')
                            actual_dir = '涨' if change_val > SIDEWAYS_THRESHOLD_PCT else ('跌' if change_val < -SIDEWAYS_THRESHOLD_PCT else '震')
                            if pred_dir == actual_dir:
                                hit = '命中'
                            elif pred_dir == '震' and actual_dir == '震':
                                # 震荡区间内偏差 ≤ 1.5% 视为命中
                                abs_dev = abs(pred_change_val - change_val)
                                hit = '命中' if abs_dev <= SIDEWAYS_THRESHOLD_PCT else '未命中'
                            else:
                                hit = '未命中'
                        else:
                            # 若无预测涨跌幅，则退回标签判断，震荡阈值放宽到 ±1.0%
                            if prediction == '上涨':
                                hit = '命中' if change_val > 0 else '未命中'
                            elif prediction == '下跌':
                                hit = '命中' if change_val < 0 else '未命中'
                            elif prediction == '震荡':
                                hit = '命中' if -SIDEWAYS_THRESHOLD_LABEL <= change_val <= SIDEWAYS_THRESHOLD_LABEL else '未命中'
                    
                    # 计算偏差值（如果预测值存在）
                    deviation_pct = None
                    absolute_deviation_pct = None
                    deviation_price = None
                    
                    if predicted_change_pct is not None and actual_change_pct is not None:
                        try:
                            deviation_pct = float(predicted_change_pct) - float(actual_change_pct)
                            absolute_deviation_pct = abs(deviation_pct)
                        except (ValueError, TypeError):
                            pass
                    
                    if predicted_close_price is not None and actual_price is not None:
                        try:
                            deviation_price = float(predicted_close_price) - float(actual_price)
                        except (ValueError, TypeError):
                            pass
                    
                    # 更新数据库（包括偏差字段）
                    if db.update_prediction_actual(symbol, target_date_str, actual_price, actual_change_pct, 
                                                   actual_dir, hit, deviation_pct, absolute_deviation_pct, deviation_price):
                        updated_count += 1
                
                if updated_count > 0:
                    try:
                        from utils.logger import get_logger
                        logger = get_logger(__name__)
                        logger.info(f"更新了 {updated_count} 条历史预测记录的实际数据（包括偏差字段）")
                    except:
                        pass
                else:
                    try:
                        from utils.logger import get_logger
                        logger = get_logger(__name__)
                        logger.debug(f"没有需要更新的历史预测记录（target_date <= {today} 且 actual_price 为空）")
                    except:
                        pass
            except Exception as e:
                try:
                    from utils.logger import get_logger
                    logger = get_logger(__name__)
                    logger.warning(f"从数据库更新历史实际数据失败: {str(e)}")
                except:
                    print(f"从数据库更新历史实际数据失败: {e}")
        except Exception as e:
            try:
                from utils.logger import get_logger
                logger = get_logger(__name__)
                logger.error(f"_update_historical_actual_data 执行失败: {e}")
            except:
                print(f"_update_historical_actual_data 执行失败: {e}")
    
    def _generate_stock_list_html(self, records):
        """生成股票列表HTML内容（从CSV读取的数据）"""
        import os
        
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票预测列表</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 20px;
        }
        .search-box {
            margin-bottom: 20px;
        }
        .search-box input {
            width: 100%;
            padding: 12px;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 5px;
        }
        .stock-item-wrapper {
            margin-bottom: 10px;
        }
        .stock-item {
            display: flex;
            align-items: center;
            padding: 15px;
            background-color: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            transition: all 0.3s;
        }
        .stock-item:hover {
            background-color: #f0f7ff;
            border-color: #3498db;
            box-shadow: 0 2px 8px rgba(52, 152, 219, 0.2);
            transform: translateY(-2px);
        }
        .stock-code {
            width: 100px;
            font-weight: bold;
            font-size: 16px;
            color: #2c3e50;
        }
        .stock-name {
            flex: 1;
            font-size: 15px;
            color: #555;
            margin-left: 20px;
        }
        .stock-price {
            width: 100px;
            text-align: right;
            font-size: 15px;
            color: #2c3e50;
        }
        .stock-prediction {
            width: 120px;
            text-align: center;
            font-size: 14px;
            padding: 5px 10px;
            border-radius: 3px;
            margin: 0 10px;
        }
        .prediction-up {
            background-color: #d4edda;
            color: #155724;
        }
        .prediction-down {
            background-color: #f8d7da;
            color: #721c24;
        }
        .prediction-neutral {
            background-color: #e2e3e5;
            color: #383d41;
        }
        .stock-probability {
            width: 150px;
            text-align: right;
            font-size: 13px;
            color: #666;
        }
        .stock-actions {
            display: flex;
            gap: 8px;
            margin-left: 15px;
        }
        .btn-report {
            padding: 6px 12px;
            font-size: 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
        }
        .btn-graph {
            background-color: #3498db;
            color: white;
        }
        .btn-graph:hover {
            background-color: #2980b9;
        }
        .btn-graph:disabled,
        .btn-graph.disabled {
            background-color: #ccc;
            color: #666;
            cursor: not-allowed;
        }
        .btn-text {
            background-color: #2ecc71;
            color: white;
        }
        .btn-text:hover {
            background-color: #27ae60;
        }
        .btn-detail {
            background-color: #f39c12;
            color: white;
        }
        .btn-detail:hover {
            background-color: #e67e22;
        }
        .btn-history {
            background-color: #95a5a6;
            color: white;
        }
        .btn-history:hover {
            background-color: #7f8c8d;
        }
        .btn-monitor {
            background-color: #e74c3c;
            color: white;
        }
        .btn-monitor:hover {
            background-color: #c0392b;
        }
        /* 模态框样式 */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: #fefefe;
            margin: 10% auto;
            padding: 30px;
            border: 1px solid #888;
            border-radius: 10px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        .modal-header h2 {
            margin: 0;
            color: #2c3e50;
            font-size: 20px;
        }
        .close {
            color: #aaa;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            line-height: 20px;
        }
        .close:hover,
        .close:focus {
            color: #000;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #3498db;
        }
        .form-group .help-text {
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 25px;
        }
        .btn-confirm {
            background-color: #3498db;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s;
        }
        .btn-confirm:hover {
            background-color: #2980b9;
        }
        .btn-cancel {
            background-color: #95a5a6;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s;
        }
        .btn-cancel:hover {
            background-color: #7f8c8d;
        }
        .summary-panel {
            display: none;
            padding: 15px;
            margin-top: 10px;
            background-color: #f9fafb;
            border-left: 4px solid #2ecc71;
            border-radius: 5px;
            font-size: 13px;
            line-height: 1.8;
            color: #333;
        }
        .summary-panel.show {
            display: block;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 股票预测列表</h1>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="输入股票代码或名称进行搜索..." 
                   onkeyup="filterStocks()">
        </div>
        
        <div class="stock-list" id="stockList">
            <!-- 股票列表将通过JavaScript动态加载 -->
            <div class="empty-state">正在加载数据...</div>
        </div>
"""
        
            # 不再生成静态股票项，改为通过JavaScript动态加载
            # 保留records变量供JavaScript使用（作为备用数据）
        html += f"""
        <script>
            // 备用静态数据(如果API不可用)
            window.staticStockRecords = {json.dumps(records, ensure_ascii=False)};
        </script>
"""
        
        # 不再生成静态股票项，改为通过JavaScript动态加载
        # 以下代码已注释，不再使用静态生成方式
        if False:  # 使用if False来注释掉整个代码块
            for record in records:
                symbol = str(record.get('symbol', '')).strip()
            name = str(record.get('name', '')).strip()
            # 确保数值类型正确转换
            try:
                current_price = float(record.get('current_price', 0) or 0)
            except (ValueError, TypeError):
                current_price = 0.0
            
            prediction = str(record.get('prediction', '震荡')).strip()
            
            try:
                up_prob = float(record.get('up_probability', 0) or 0)
            except (ValueError, TypeError):
                up_prob = 0.0
            
            try:
                down_prob = float(record.get('down_probability', 0) or 0)
            except (ValueError, TypeError):
                down_prob = 0.0
            
            try:
                confidence = float(record.get('confidence', 0) or 0)
            except (ValueError, TypeError):
                confidence = 0.0
            
            prediction_date = str(record.get('prediction_date', '')).strip()
            target_date = str(record.get('target_date', '')).strip()
            png_file = str(record.get('png_file', '') or '').strip()
            full_report_html = str(record.get('full_report_html', '') or '').strip()
            summary = str(record.get('summary', '暂无文字报告') or '暂无文字报告').strip()
            
            # 预测样式
            pred_class = 'prediction-neutral'
            pred_icon = 'neutral'
            if prediction == '上涨':
                pred_class = 'prediction-up'
                pred_icon = 'up'
            elif prediction == '下跌':
                pred_class = 'prediction-down'
                pred_icon = 'down'
            
            # 按钮 - 文件路径转换为相对路径（从根目录到reports目录）
            graph_btn = ''
            if png_file:
                # 将绝对路径转换为相对路径
                if os.path.isabs(png_file):
                    # 如果是绝对路径，提取文件名
                    png_basename = os.path.basename(png_file)
                    png_relative = f'reports/{png_basename}'
                else:
                    png_relative = png_file if png_file.startswith('reports/') else f'reports/{os.path.basename(png_file)}'
                
                if os.path.exists(png_file):
                    graph_btn = f'<a href="{png_relative}" target="_blank" class="btn-report btn-graph">图形报告</a>'
                else:
                    graph_btn = '<span class="btn-report btn-graph disabled" style="cursor: not-allowed;">图形报告</span>'
            else:
                graph_btn = '<span class="btn-report btn-graph disabled" style="cursor: not-allowed;">图形报告</span>'
            
            text_btn = f'<button class="btn-report btn-text" onclick="toggleSummary(\'{symbol}\'); event.stopPropagation(); return false;">文字报告</button>'
            
            detail_btn = ''
            if full_report_html:
                # 将绝对路径转换为相对路径
                if os.path.isabs(full_report_html):
                    html_basename = os.path.basename(full_report_html)
                    html_relative = f'reports/{html_basename}'
                else:
                    html_relative = full_report_html if full_report_html.startswith('reports/') else f'reports/{os.path.basename(full_report_html)}'
                
                if os.path.exists(full_report_html):
                    detail_btn = f'<a href="{html_relative}" target="_blank" class="btn-report btn-detail">文字详情</a>'
                else:
                    detail_btn = '<span class="btn-report btn-detail disabled" style="cursor: not-allowed;">文字详情</span>'
            else:
                detail_btn = '<span class="btn-report btn-detail disabled" style="cursor: not-allowed;">文字详情</span>'
            
            history_btn = f'<a href="reports/history_{symbol}.html" target="_blank" class="btn-report btn-history">历史预测</a>'
            monitor_btn = f'<button class="btn-report btn-monitor" onclick="openMonitorModal(\'{symbol}\', \'{name}\', {current_price:.2f}); event.stopPropagation(); return false;">实时监控</button>'
            
            conf_pct = confidence * 100
            up_pct = up_prob * 100
            down_pct = down_prob * 100
            
            # 使用字符串拼接避免f-string中的编码问题
            html += '<div class="stock-item-wrapper" data-symbol="' + str(symbol) + '">'
            html += '<div class="stock-item" data-symbol="' + str(symbol) + '" data-name="' + str(name) + '">'
            html += '<div class="stock-code">' + str(symbol) + '</div>'
            html += '<div class="stock-name">'
            html += '<div style="font-weight: 500;">' + str(name) + '</div>'
            html += '<div style="font-size: 11px; color: #999; margin-top: 2px;">'
            html += '预测日期: ' + str(prediction_date) + ' | 目标: ' + str(target_date) + ' | 置信度: ' + f'{conf_pct:.1f}' + '%'
            html += '</div>'
            html += '</div>'
            html += '<div class="stock-price">'
            html += '<div>' + f'{current_price:.2f}' + '元</div>'
            html += '</div>'
            html += '<div class="stock-prediction ' + str(pred_class) + '">' + str(pred_icon) + ' ' + str(prediction) + '</div>'
            html += '<div class="stock-probability">↑' + f'{up_pct:.1f}' + '% ↓' + f'{down_pct:.1f}' + '%</div>'
            html += '<div class="stock-actions">'
            html += graph_btn
            html += text_btn
            html += detail_btn
            html += history_btn
            html += monitor_btn
            html += '</div>'
            html += '</div>'
            html += '<div id="summary-' + str(symbol) + '" class="summary-panel">'
            html += '<strong>预测分析摘要:</strong><br>'
            html += str(summary)
            html += '</div>'
            html += '</div>'
        
        # 关闭if False块
        pass
        
        html += """
        
        <div id="loadingIndicator" style="text-align: center; padding: 40px; display: none;">
            <div style="font-size: 16px; color: #666;">Loading data...</div>
        </div>
        
        <div id="errorMessage" style="display: none; padding: 20px; background-color: #f8d7da; color: #721c24; border-radius: 5px; margin: 20px 0;">
            <strong>Error:</strong><span id="errorText"></span>
            <br><br>
            <div style="margin-top: 10px;">
                <strong>Solution:</strong>
                <ol style="margin: 10px 0 0 20px; line-height: 2;">
                    <li>Start API server: <code>py api_server.py</code></li>
                    <li>Refresh this page</li>
                    <li>Or open static HTML file directly (cached data will be shown if API server is not running)</li>
                </ol>
            </div>
        </div>
    </div>
    
    <!-- 实时监控设置模态框 -->
    <div id="monitorModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>实时监控设置</h2>
                <span class="close" onclick="closeMonitorModal()">&times;</span>
            </div>
            <form id="monitorForm" onsubmit="startMonitor(event); return false;">
                <input type="hidden" id="monitorSymbol" name="symbol">
                <input type="hidden" id="monitorName" name="name">
                
                <div class="form-group">
                    <label for="monitorCost">持仓成本价(元)</label>
                    <input type="number" id="monitorCost" name="cost" step="0.01" placeholder="留空表示未持仓">
                    <div class="help-text">如果已持有该股票,请输入买入成本价,用于计算盈亏</div>
                </div>
                
                <div class="form-group">
                    <label for="monitorInterval">刷新间隔(秒)</label>
                    <select id="monitorInterval" name="interval" required>
                        <option value="10">10秒(高频)</option>
                        <option value="30" selected>30秒(推荐)</option>
                        <option value="60">60秒(标准)</option>
                        <option value="120">120秒(低频)</option>
                        <option value="300">300秒(5分钟)</option>
                    </select>
                    <div class="help-text">页面自动刷新的时间间隔,建议30-60秒</div>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="monitorHolding" name="holding" onchange="toggleCostInput()">
                        我已持有该股票
                    </label>
                </div>
                
                <div class="form-actions">
                    <button type="button" class="btn-cancel" onclick="closeMonitorModal()">取消</button>
                    <button type="submit" class="btn-confirm">开始监控</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        // API配置 - 使用当前域名(通过Flask应用)
        const API_ENDPOINT = '/api/stocks';
        
        // 全局变量
        let allStockRecords = [];
        
        // 页面加载时获取数据
        window.addEventListener('DOMContentLoaded', function() {
            loadStockData();
            
            // 设置自动刷新(每30秒)
            setInterval(loadStockData, 30000);
        });
        
        // 加载股票数据
        async function loadStockData() {
            const stockList = document.getElementById('stockList');
            const loadingIndicator = document.getElementById('loadingIndicator');
            const errorMessage = document.getElementById('errorMessage');
            const errorText = document.getElementById('errorText');
            
            // 显示加载指示器
            loadingIndicator.style.display = 'block';
            errorMessage.style.display = 'none';
            
            try {
                const response = await fetch(API_ENDPOINT);
                const result = await response.json();
                
                if (result.success && result.data) {
                    allStockRecords = result.data;
                    renderStockList(result.data);
                    loadingIndicator.style.display = 'none';
                } else {
                    throw new Error(result.message || '获取数据失败');
                }
            } catch (error) {
                console.error('加载数据失败:', error);
                errorText.textContent = error.message;
                errorMessage.style.display = 'block';
                loadingIndicator.style.display = 'none';
                
                // 如果API失败,尝试使用静态数据(如果有)
                if (allStockRecords.length === 0 && window.staticStockRecords && window.staticStockRecords.length > 0) {
                    console.log('API失败，使用备用静态数据');
                    renderStockList(window.staticStockRecords);
                    loadingIndicator.style.display = 'none';
                }
            }
        }
        
        // 渲染股票列表
        function renderStockList(records) {
            const stockList = document.getElementById('stockList');
            stockList.innerHTML = '';
            
            if (!records || records.length === 0) {
                stockList.innerHTML = '<div class="empty-state">暂无预测记录</div>';
                return;
            }
            
            // 按预测时间排序(最新的在前)
            records.sort((a, b) => {
                const timeA = a.prediction_time || '';
                const timeB = b.prediction_time || '';
                return timeB.localeCompare(timeA);
            });
            
            records.forEach(record => {
                const stockItem = createStockItemHTML(record);
                stockList.innerHTML += stockItem;
            });
        }
        
        // 创建股票项HTML
        function createStockItemHTML(record) {
            const symbol = String(record.symbol || '').trim();
            const name = String(record.name || '').trim();
            const current_price = parseFloat(record.current_price || 0);
            const prediction = String(record.prediction || '震荡').trim();
            const up_prob = parseFloat(record.up_probability || 0);
            const down_prob = parseFloat(record.down_probability || 0);
            const confidence = parseFloat(record.confidence || 0);
            const prediction_date = String(record.prediction_date || '').trim();
            const target_date = String(record.target_date || '').trim();
            const png_file = String(record.png_file || '').trim();
            const full_report_html = String(record.full_report_html || '').trim();
            const summary = String(record.summary || '暂无文字报告').trim();
            
            // 预测样式
            let pred_class = 'prediction-neutral';
            let pred_icon = '📊';
            if (prediction === '上涨') {
                pred_class = 'prediction-up';
                pred_icon = '📈';
            } else if (prediction === '下跌') {
                pred_class = 'prediction-down';
                pred_icon = '📉';
            }
            
            // 按钮生成 - 优先使用HTML交互式图表
            const interactive_html = String(record.interactive_html || '').trim();
            let graph_btn = '';
            if (interactive_html) {
                const html_basename = interactive_html.split(/[/\\\\]/).pop();
                const html_relative = `/reports/${html_basename}`;
                graph_btn = `<a href="${html_relative}" target="_blank" class="btn-report btn-graph">交互图表</a>`;
            } else if (png_file) {
                const png_basename = png_file.split(/[/\\\\]/).pop();
                const png_relative = `/reports/${png_basename}`;
                graph_btn = `<a href="${png_relative}" target="_blank" class="btn-report btn-graph">图形报告</a>`;
            } else {
                graph_btn = '<span class="btn-report btn-graph disabled" style="cursor: not-allowed;">图形报告</span>';
            }
            
            const text_btn = `<button class="btn-report btn-text" onclick="toggleSummary('${symbol}'); event.stopPropagation(); return false;">文字报告</button>`;
            
            let detail_btn = '';
            if (full_report_html) {
                const html_basename = full_report_html.split(/[/\\\\]/).pop();
                const html_relative = `/reports/${html_basename}`;
                detail_btn = `<a href="${html_relative}" target="_blank" class="btn-report btn-detail">文字详情</a>`;
            } else {
                detail_btn = '<span class="btn-report btn-detail disabled" style="cursor: not-allowed;">文字详情</span>';
            }
            
            const history_btn = `<a href="/reports/history_${symbol}.html" target="_blank" class="btn-report btn-history">历史预测</a>`;
            const monitor_btn = `<button class="btn-report btn-monitor" onclick="openMonitorModal('${symbol}', '${name}', ${current_price.toFixed(2)}); event.stopPropagation(); return false;">实时监控</button>`;
            
            return `
            <div class="stock-item-wrapper" data-symbol="${symbol}">
                <div class="stock-item" data-symbol="${symbol}" data-name="${name}">
                    <div class="stock-code">${symbol}</div>
                    <div class="stock-name">
                        <div style="font-weight: 500;">${name}</div>
                        <div style="font-size: 11px; color: #999; margin-top: 2px;">
                            预测日期: ${prediction_date} | 目标: ${target_date} | 置信度: ${(confidence * 100).toFixed(1)}%
                        </div>
                    </div>
                    <div class="stock-price">
                        <div>${current_price.toFixed(2)}元</div>
                    </div>
                    <div class="stock-prediction ${pred_class}">${pred_icon} ${prediction}</div>
                    <div class="stock-probability">↑${(up_prob * 100).toFixed(1)}% ↓${(down_prob * 100).toFixed(1)}%</div>
                    <div class="stock-actions">
                        ${graph_btn}
                        ${text_btn}
                        ${detail_btn}
                        ${history_btn}
                        ${monitor_btn}
                    </div>
                </div>
                <div id="summary-${symbol}" class="summary-panel">
                    <strong>预测分析摘要:</strong><br>
                    ${summary}
                </div>
            </div>
            `;
        }
        
        function filterStocks() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toUpperCase();
            const stockWrappers = document.querySelectorAll('.stock-item-wrapper');
            
            stockWrappers.forEach(wrapper => {
                const symbol = wrapper.getAttribute('data-symbol') || '';
                const item = wrapper.querySelector('.stock-item');
                const name = item.getAttribute('data-name') || '';
                const text = (symbol + ' ' + name).toUpperCase();
                
                if (text.indexOf(filter) > -1) {
                    wrapper.style.display = '';
                } else {
                    wrapper.style.display = 'none';
                }
            });
        }
        
        function toggleSummary(symbol) {
            const panel = document.getElementById('summary-' + symbol);
            if (panel) {
                panel.classList.toggle('show');
            }
        }
        
        // 打开监控设置模态框
        function openMonitorModal(symbol, name, currentPrice) {
            document.getElementById('monitorSymbol').value = symbol;
            document.getElementById('monitorName').value = name;
            document.getElementById('monitorCost').value = '';
            document.getElementById('monitorInterval').value = '30';
            document.getElementById('monitorHolding').checked = false;
            document.getElementById('monitorCost').disabled = true;
            document.getElementById('monitorModal').style.display = 'block';
        }
        
        // 关闭模态框
        function closeMonitorModal() {
            document.getElementById('monitorModal').style.display = 'none';
        }
        
        // 切换成本价输入框
        function toggleCostInput() {
            const holding = document.getElementById('monitorHolding').checked;
            const costInput = document.getElementById('monitorCost');
            costInput.disabled = !holding;
            if (!holding) {
                costInput.value = '';
            }
        }
        
        // 开始监控
        function startMonitor(event) {
            event.preventDefault();
            const symbol = document.getElementById('monitorSymbol').value;
            const name = document.getElementById('monitorName').value;
            const cost = document.getElementById('monitorCost').value;
            const interval = document.getElementById('monitorInterval').value;
            const holding = document.getElementById('monitorHolding').checked;
            
            // 构建URL参数
            const params = new URLSearchParams({
                symbol: symbol,
                name: name,
                interval: interval,
                holding: holding ? '1' : '0'
            });
            if (cost && holding) {
                params.append('cost', cost);
            }
            
            // 跳转到监控页面
            window.location.href = 'reports/monitor_' + symbol + '.html?' + params.toString();
        }
        
        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('monitorModal');
            if (event.target == modal) {
                closeMonitorModal();
            }
        }
    </script>
</body>
</html>
"""
        return html
    
    def _generate_empty_stock_list_html(self):
        """生成空列表HTML"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>股票预测列表</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
        }
        .empty-state {
            color: #999;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <div class="empty-state">
        <h1>📊</h1>
        <p>暂无预测记录</p>
    </div>
</body>
</html>
"""
    
    def create_stock_history_page(self, symbol: str):
        """
        创建单个股票的历史预测页面（已废弃：不再生成HTML，数据从数据库读取）
        
        Args:
            symbol: 股票代码
        
        Returns:
            None: 不再生成HTML页面
        """
        # 不再生成HTML页面，所有数据都从数据库读取（页面由前端通过API动态获取）
        try:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.debug(f"create_stock_history_page 已废弃，不再生成HTML页面，数据从数据库读取: {symbol}")
        except:
            pass
        
        return None
    
    def create_realtime_monitor_page(self, symbol: str, interval: int = 30, holding: bool = False, cost_price: float = None):
        """
        创建实时监控页面（HTML文件，包含自动刷新）
        
        Args:
            symbol: 股票代码
            interval: 刷新间隔（秒）
            holding: 是否持有
            cost_price: 持仓成本价
            
        Returns:
            str: HTML文件路径
        """
        import os
        from datetime import datetime
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        monitor_html_file = os.path.join(self.reports_dir, f'monitor_{symbol}.html')
        
        # 获取股票信息
        try:
            ds_spec = importlib.util.spec_from_file_location(
                "stock_data_source",
                os.path.join(project_root, "data_source", "stock_data_source.py")
            )
            ds_module = importlib.util.module_from_spec(ds_spec)
            ds_spec.loader.exec_module(ds_module)
            StockDataSource = ds_module.StockDataSource
            data_source = StockDataSource()
            
            stock_info = data_source.get_stock_info(symbol)
            stock_name = stock_info.get('name', symbol) if stock_info else symbol
        except Exception as e:
            self.logger.warning(f"获取股票信息失败: {e}")
            stock_name = symbol
        
        # 生成HTML内容
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="{interval}">
    <title>{symbol} {stock_name} - 实时监控</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid #e74c3c;
        }}
        .header h1 {{
            color: #2c3e50;
            font-size: 24px;
        }}
        .header .monitor-badge {{
            background-color: #e74c3c;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }}
        .status-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #666;
        }}
        .section {{
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            background-color: #fff;
            border-left: 4px solid #3498db;
        }}
        .section h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .info-item {{
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }}
        .info-label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }}
        .info-value {{
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .info-value.positive {{
            color: #27ae60;
        }}
        .info-value.negative {{
            color: #e74c3c;
        }}
        .decision-box {{
            padding: 20px;
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 5px;
            margin-top: 15px;
        }}
        .decision-action {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .decision-action.buy {{
            color: #27ae60;
        }}
        .decision-action.sell {{
            color: #e74c3c;
        }}
        .decision-action.hold {{
            color: #f39c12;
        }}
        .decision-reasons {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
        }}
        .decision-reasons ul {{
            margin-left: 20px;
            margin-top: 10px;
        }}
        .decision-reasons li {{
            margin: 5px 0;
            color: #555;
        }}
        .price-suggestions {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
        }}
        .price-suggestions .price-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .price-suggestions .price-item:last-child {{
            border-bottom: none;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #3498db;
            text-decoration: none;
            padding: 8px 15px;
            background-color: #e8f4f8;
            border-radius: 5px;
        }}
        .back-link:hover {{
            background-color: #d4e6f1;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        .error {{
            padding: 15px;
            background-color: #f8d7da;
            color: #721c24;
            border-radius: 5px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../stock_list.html" class="back-link">← 返回股票列表</a>
        
        <div class="header">
            <h1>{symbol} {stock_name} - 实时监控</h1>
            <span class="monitor-badge">🔴 监控中（每{interval}秒刷新）</span>
        </div>
        
        <div class="status-bar">
            <span>最后更新: <span id="lastUpdate">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></span>
            <span>下次刷新: <span id="nextRefresh">{interval}秒后</span></span>
        </div>
        
        <div id="content">
            <div class="loading">正在加载实时数据...</div>
        </div>
    </div>
    
    <script>
        // 从URL参数获取设置
        const urlParams = new URLSearchParams(window.location.search);
        const symbol = urlParams.get('symbol') || '{symbol}';
        const interval = parseInt(urlParams.get('interval') || '{interval}');
        const holding = urlParams.get('holding') === '1';
        const cost = parseFloat(urlParams.get('cost') || '0');
        
        let refreshCountdown = interval;
        
        // 更新倒计时
        function updateCountdown() {{
            refreshCountdown--;
            if (refreshCountdown <= 0) {{
                refreshCountdown = interval;
            }}
            document.getElementById('nextRefresh').textContent = refreshCountdown + '秒后';
        }}
        
        setInterval(updateCountdown, 1000);
        
        // 加载实时数据
        function loadRealtimeData() {{
            // 这里应该通过API获取实时数据
            // 由于是静态HTML,我们显示提示信息
            const holdingCmd = holding && cost > 0 ? ` --holding --cost ${{cost}}` : '';
            const monitorCmd = `py main.py --monitor --symbol {symbol} --interval ${{interval}}${{holdingCmd}}`;
            
            const content = document.getElementById('content');
            content.innerHTML = `
                <div class="section">
                    <h2>📊 实时行情数据</h2>
                    <div style="padding: 15px; background-color: #e8f4f8; border-left: 4px solid #3498db; border-radius: 5px;">
                        <strong>💡 使用说明：</strong>
                        <ol style="margin: 10px 0 0 20px; line-height: 2;">
                            <li>在命令行中运行以下命令启动监控服务：</li>
                            <li style="margin: 10px 0;">
                                <code style="background-color: #f4f4f4; padding: 8px 12px; border-radius: 4px; display: block; font-size: 13px;">${{monitorCmd}}</code>
                            </li>
                            <li>监控服务启动后，此页面将自动刷新并显示实时数据</li>
                            <li>页面每 ${{interval}} 秒自动刷新一次</li>
                        </ol>
                    </div>
                </div>
                
                <div class="section">
                    <h2>💰 实时资金流向</h2>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">主力净流入</div>
                            <div class="info-value">--</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">总净流入</div>
                            <div class="info-value">--</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">资金趋势</div>
                            <div class="info-value">--</div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🎯 实时交易决策</h2>
                    <div class="decision-box">
                        <div class="decision-action hold">建议：等待数据加载</div>
                        <div class="decision-reasons">
                            <strong>决策理由：</strong>
                            <ul>
                                <li>请启动后端监控服务以获取实时决策</li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                ${{holding && cost > 0 ? `
                <div class="section">
                    <h2>💼 持仓信息</h2>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">持仓成本</div>
                            <div class="info-value">${{cost.toFixed(2)}}元</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">当前价格</div>
                            <div class="info-value">--</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">盈亏</div>
                            <div class="info-value">--</div>
                        </div>
                    </div>
                </div>
                ` : ''}}
            `;
            
            document.getElementById('lastUpdate').textContent = new Date().toLocaleString('zh-CN');
        }}
        
        // 页面加载时执行
        loadRealtimeData();
        
        // 页面刷新时重新加载
        window.addEventListener('beforeunload', function() {{
            // 可以在这里保存状态
        }});
    </script>
</body>
</html>
"""
        
        # 保存HTML文件
        try:
            with open(monitor_html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.logger.info(f"实时监控页面已生成: {monitor_html_file}")
            return monitor_html_file
        except Exception as e:
            self.logger.error(f"保存监控页面失败: {e}")
            return None

