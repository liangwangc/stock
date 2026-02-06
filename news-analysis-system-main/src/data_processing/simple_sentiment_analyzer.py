"""
简单情感分析器（基于关键词匹配）
用于在新闻获取时进行基础情感分析，填充股票预测所需字段
"""
import re
from typing import Dict, List


class SimpleSentimentAnalyzer:
    """简单情感分析器（基于关键词匹配）"""
    
    def __init__(self):
        # 利好关键词
        self.positive_keywords = [
            '上涨', '增长', '大涨', '涨停', '创新高', '突破', '拉升', '飙升', '暴涨',
            '盈利', '业绩', '超预期', '业绩超预期', '业绩大增', '业绩暴增',
            '净利润增长', '营收增长', '利润增长', '业绩亮眼', '业绩靓丽',
            '扭亏为盈', '盈利能力', '盈利能力提升',
            '利好', '积极', '乐观', '看好', '推荐', '买入', '增持', '增持评级',
            '强烈推荐', '强烈买入', '买入评级', '维持买入', '上调评级',
            '扩张', '收购', '合并', '重组', '资产注入', '业务拓展',
            '订单', '签约', '中标', '合作', '投资', '战略合作',
            '重大合同', '大单', '订单饱满', '订单充足',
            '回购', '分红', '派息', '高送转', '送转', '现金分红',
            '股份回购', '增持股份', '股权激励',
            '政策支持', '政策利好', '扶持', '补贴', '优惠', '税收优惠',
            '创新', '技术突破', '新产品', '新业务', '市场拓展',
            '竞争优势', '行业龙头', '市场份额提升'
        ]
        
        # 利空关键词
        self.negative_keywords = [
            '下跌', '下降', '大跌', '跌停', '创新低', '破位', '暴跌', '急跌',
            '亏损', '业绩下滑', '业绩下降', '业绩预警', '业绩预亏',
            '净利润下降', '营收下降', '利润下降', '业绩不佳', '业绩疲软',
            '利空', '消极', '悲观', '看空', '卖出', '减持', '减持评级',
            '强烈卖出', '卖出评级', '下调评级', '维持卖出',
            '退市', 'ST', '风险警示', '监管', '调查', '处罚', '违规',
            '债务', '负债', '资金链', '破产', '清算', '重组失败',
            '竞争激烈', '市场份额下降', '行业低迷', '市场萎缩',
            '政策收紧', '政策限制', '监管加强', '整顿'
        ]
        
        # 政策关键词
        self.policy_keywords = [
            '政策', '监管', '规定', '通知', '公告', '意见', '办法',
            '降准', '降息', 'MLF', 'LPR', '货币政策', '利率', '准备金',
            '减税', '基建', '财政', '专项债', '财政政策', '税收',
            '扶持', '补贴', '产业政策', '行业政策', '产业扶持',
            '规范', '整顿', '监管政策', '监管规定', '监管措施'
        ]
    
    def analyze(self, title: str, content: str) -> Dict:
        """
        分析新闻情感
        
        Args:
            title: 新闻标题
            content: 新闻内容
            
        Returns:
            {
                'sentiment': 'positive'/'negative'/'neutral',
                'sentiment_score': -1.0 到 1.0,
                'sentiment_confidence': 0.0 到 1.0,
                'keywords': [关键词列表],
                'is_positive': 0/1,
                'is_negative': 0/1,
                'is_policy': 0/1,
                'relevance_type': 'direct'/'industry'/'market',
                'relevance_score': 0.0 到 1.0
            }
        """
        text = f"{title} {content}".lower()
        
        # 统计关键词匹配
        positive_count = 0
        negative_count = 0
        policy_count = 0
        matched_keywords = []
        
        # 检查利好关键词
        for keyword in self.positive_keywords:
            if keyword in text:
                positive_count += 1
                matched_keywords.append(keyword)
        
        # 检查利空关键词
        for keyword in self.negative_keywords:
            if keyword in text:
                negative_count += 1
                matched_keywords.append(keyword)
        
        # 检查政策关键词
        for keyword in self.policy_keywords:
            if keyword in text:
                policy_count += 1
        
        # 计算情感得分（-1.0 到 1.0）
        total_keywords = positive_count + negative_count
        if total_keywords > 0:
            sentiment_score = (positive_count - negative_count) / max(total_keywords, 1)
            # 归一化到 -1.0 到 1.0
            sentiment_score = max(-1.0, min(1.0, sentiment_score))
        else:
            sentiment_score = 0.0
        
        # 确定情感类型
        if sentiment_score > 0.1:
            sentiment = 'positive'
            is_positive = 1
            is_negative = 0
        elif sentiment_score < -0.1:
            sentiment = 'negative'
            is_positive = 0
            is_negative = 1
        else:
            sentiment = 'neutral'
            is_positive = 0
            is_negative = 0
        
        # 计算置信度（基于关键词数量）
        confidence = min(1.0, total_keywords / 5.0)  # 最多5个关键词达到最高置信度
        
        # 判断是否为政策新闻
        is_policy = 1 if policy_count > 0 else 0
        
        # 相关性类型和得分（如果有股票关联，在调用时设置）
        relevance_type = 'market'
        relevance_score = 0.5
        
        return {
            'sentiment': sentiment,
            'sentiment_score': round(sentiment_score, 4),
            'sentiment_confidence': round(confidence, 4),
            'keywords': matched_keywords[:10],  # 最多返回10个关键词
            'is_positive': is_positive,
            'is_negative': is_negative,
            'is_policy': is_policy,
            'relevance_type': relevance_type,
            'relevance_score': relevance_score
        }
