"""
基于新闻的交易策略
根据市场新闻情感进行快速买入/卖出
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict
from .base_strategy import BaseStrategy
from news import UnifiedNewsSource, NewsSentimentAnalyzer
from utils.logger import get_logger

logger = get_logger(__name__)

class NewsBasedStrategy(BaseStrategy):
    """基于新闻的交易策略"""
    
    def __init__(
        self,
        sentiment_threshold: float = 0.3,  # 情感阈值，超过此值才交易
        confidence_threshold: float = 0.5,  # 置信度阈值
        news_count: int = 5,  # 需要分析的最新新闻数量
        fast_trade: bool = True  # 是否快速交易（立即执行）
    ):
        """
        初始化新闻策略
        
        Args:
            sentiment_threshold: 情感分数阈值，超过此值才触发交易
            confidence_threshold: 置信度阈值，低于此值不交易
            news_count: 分析的最新新闻数量
            fast_trade: 是否快速交易模式
        """
        super().__init__("新闻驱动策略")
        self.sentiment_threshold = sentiment_threshold
        self.confidence_threshold = confidence_threshold
        self.news_count = news_count
        self.fast_trade = fast_trade
        self.news_source = UnifiedNewsSource()  # 使用统一新闻源，聚合多个新闻源
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        self.logger = logger
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号（基于新闻）
        
        注意：这个方法需要实时新闻数据，在实际使用时需要结合实时交易系统
        这里提供一个框架实现
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        
        try:
            # 获取最新日期的新闻（在实际应用中应该实时获取）
            # 这里使用最新日期作为示例
            latest_date = data.index[-1]
            
            # 尝试获取新闻（实际使用时需要传入股票代码）
            # 由于当前框架限制，这里提供一个逻辑框架
            
            # 实际实现应该：
            # 1. 获取股票代码（从data或其他方式）
            # 2. 获取该股票的最新新闻
            # 3. 分析新闻情感
            # 4. 根据情感生成信号
            
            # 示例逻辑（需要在实际使用时实现）
            # news_list = self.news_source.get_stock_news(symbol, self.news_count)
            # sentiment_results = self.sentiment_analyzer.analyze_batch(news_list)
            # aggregated = self.sentiment_analyzer.get_aggregated_sentiment(sentiment_results)
            
            # if aggregated['overall_sentiment'] == 'positive' and \
            #    aggregated['weighted_score'] > self.sentiment_threshold and \
            #    aggregated['weighted_score'] > self.confidence_threshold:
            #     signals.loc[latest_date, 'signal'] = 1  # 买入信号
            # elif aggregated['overall_sentiment'] == 'negative' and \
            #      aggregated['weighted_score'] < -self.sentiment_threshold and \
            #      aggregated['weighted_score'] < -self.confidence_threshold:
            #     signals.loc[latest_date, 'signal'] = -1  # 卖出信号
            
            self.logger.warning("新闻策略需要实时新闻数据，当前为框架实现")
            self.logger.info("请使用 NewsRealtimeStrategy 进行实时新闻交易")
            
        except Exception as e:
            self.logger.error(f"生成新闻信号失败: {str(e)}")
        
        return signals

class NewsRealtimeStrategy(BaseStrategy):
    """
    实时新闻交易策略
    用于实时交易系统，需要实时新闻数据
    """
    
    def __init__(
        self,
        symbol: str,
        sentiment_threshold: float = 0.3,
        confidence_threshold: float = 0.5,
        news_count: int = 5,
        fast_trade: bool = True
    ):
        """
        初始化实时新闻策略
        
        Args:
            symbol: 股票代码
            sentiment_threshold: 情感阈值
            confidence_threshold: 置信度阈值
            news_count: 分析的新闻数量
            fast_trade: 快速交易模式
        """
        super().__init__(f"实时新闻策略-{symbol}")
        self.symbol = symbol
        self.sentiment_threshold = sentiment_threshold
        self.confidence_threshold = confidence_threshold
        self.news_count = news_count
        self.fast_trade = fast_trade
        self.news_source = UnifiedNewsSource()  # 使用统一新闻源，聚合多个新闻源
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        self.logger = logger
    
    def check_news_and_generate_signal(self) -> Dict:
        """
        检查新闻并生成交易信号（用于实时交易）
        
        Returns:
            信号字典: {
                'signal': 1(买入)/-1(卖出)/0(无信号),
                'sentiment': 情感分析结果,
                'confidence': 置信度,
                'news_count': 新闻数量
            }
        """
        try:
            # 获取最新新闻
            self.logger.info(f"正在获取 {self.symbol} 的最新新闻...")
            news_list = self.news_source.get_stock_news(self.symbol, self.news_count)
            
            if not news_list:
                # 如果没有股票特定新闻，尝试获取市场新闻
                self.logger.info("未获取到股票新闻，尝试获取市场新闻...")
                news_list = self.news_source.get_market_news(self.news_count)
            
            if not news_list:
                self.logger.warning("未获取到新闻数据")
                return {
                    'signal': 0,
                    'sentiment': 'neutral',
                    'confidence': 0.0,
                    'news_count': 0,
                    'message': '无新闻数据'
                }
            
            # 分析新闻情感
            sentiment_results = self.sentiment_analyzer.analyze_batch(news_list)
            aggregated = self.sentiment_analyzer.get_aggregated_sentiment(sentiment_results)
            
            self.logger.info(f"新闻情感分析结果: {aggregated['overall_sentiment']}, "
                           f"分数: {aggregated['weighted_score']:.2f}, "
                           f"置信度: {aggregated.get('confidence', 0):.2f}")
            
            # 生成交易信号
            signal = 0
            weighted_score = aggregated['weighted_score']
            confidence = min([s.get('confidence', 0) for s in sentiment_results if 'sentiment' in s], default=0.0)
            
            # 买入条件：正面情感 + 分数超过阈值 + 置信度足够
            if aggregated['overall_sentiment'] == 'positive' and \
               weighted_score > self.sentiment_threshold and \
               confidence > self.confidence_threshold:
                signal = 1
                self.logger.info(f"✅ 生成买入信号: 情感分数 {weighted_score:.2f}, 置信度 {confidence:.2f}")
            
            # 卖出条件：负面情感 + 分数低于阈值 + 置信度足够
            elif aggregated['overall_sentiment'] == 'negative' and \
                 weighted_score < -self.sentiment_threshold and \
                 confidence > self.confidence_threshold:
                signal = -1
                self.logger.info(f"✅ 生成卖出信号: 情感分数 {weighted_score:.2f}, 置信度 {confidence:.2f}")
            
            else:
                self.logger.info(f"无交易信号: 情感分数 {weighted_score:.2f}, 置信度 {confidence:.2f}")
            
            return {
                'signal': signal,
                'sentiment': aggregated['overall_sentiment'],
                'score': weighted_score,
                'confidence': confidence,
                'news_count': len(news_list),
                'message': '信号生成成功'
            }
            
        except Exception as e:
            self.logger.error(f"检查新闻失败: {str(e)}")
            return {
                'signal': 0,
                'sentiment': 'neutral',
                'confidence': 0.0,
                'news_count': 0,
                'message': f'错误: {str(e)}'
            }
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号（历史数据模式，不适用实时新闻）
        实时新闻策略应该使用 check_news_and_generate_signal
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        self.logger.warning("实时新闻策略应使用 check_news_and_generate_signal 方法")
        return signals

