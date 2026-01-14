"""
新闻情感分析器（增强版）
分析新闻的情感倾向（利好/利空/中性）
支持jieba分词、新闻重要性评分
"""
from typing import Dict, List, Optional
from datetime import datetime
import re
from utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入jieba分词库（如果不存在则使用简单分词）
JIEBA_AVAILABLE = False
JIEBA_ERROR = None

try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
    logger.info(f"jieba分词库已加载 (版本: {jieba.__version__ if hasattr(jieba, '__version__') else '未知'})")
except ImportError as e:
    JIEBA_AVAILABLE = False
    JIEBA_ERROR = str(e)
    logger.warning(
        "jieba分词库不可用，将使用简单分词（字符串匹配）。\n"
        "提示：安装jieba可以提升中文分词准确性，运行命令: pip install jieba\n"
        f"错误详情: {JIEBA_ERROR}"
    )
except Exception as e:
    JIEBA_AVAILABLE = False
    JIEBA_ERROR = str(e)
    logger.warning(
        f"jieba分词库加载失败: {JIEBA_ERROR}，将使用简单分词（字符串匹配）"
    )

class NewsSentimentAnalyzer:
    """新闻情感分析器"""
    
    def __init__(self):
        self.logger = logger
        
        # 利好关键词（扩展版）
        self.positive_keywords = [
            # 价格相关
            '上涨', '增长', '大涨', '涨停', '创新高', '突破', '拉升', '飙升', '暴涨',
            '稳步上涨', '持续上涨', '强劲上涨', '大幅上涨', '急涨',
            # 业绩相关
            '盈利', '业绩', '增长', '超预期', '业绩超预期', '业绩大增', '业绩暴增',
            '净利润增长', '营收增长', '利润增长', '业绩亮眼', '业绩靓丽',
            '扭亏为盈', '盈利能力', '盈利能力提升',
            # 利好消息
            '利好', '积极', '乐观', '看好', '推荐', '买入', '增持', '增持评级',
            '强烈推荐', '强烈买入', '买入评级', '维持买入', '上调评级',
            # 业务扩展
            '扩张', '收购', '合并', '重组', '资产注入', '业务拓展',
            '订单', '签约', '中标', '合作', '投资', '战略合作',
            '重大合同', '大单', '订单饱满', '订单充足',
            # 回购分红
            '回购', '分红', '派息', '高送转', '送转', '现金分红',
            '股份回购', '增持股份', '股权激励',
            # 政策支持
            '政策支持', '政策利好', '扶持', '补贴', '优惠', '税收优惠',
            # 其他正面
            '创新', '技术突破', '新产品', '新业务', '市场拓展',
            '竞争优势', '行业龙头', '市场份额提升'
        ]
        
        # 利空关键词（扩展版）
        self.negative_keywords = [
            # 价格相关
            '下跌', '下降', '大跌', '跌停', '创新低', '破位', '下挫', '暴跌',
            '持续下跌', '大幅下跌', '急跌', '跳水', '崩盘',
            # 业绩相关
            '亏损', '业绩下滑', '业绩下降', '业绩不佳', '业绩预警',
            '低于预期', '业绩不达预期', '净利润下降', '营收下降',
            '业绩承压', '业绩疲软', '业绩恶化',
            # 利空消息
            '利空', '悲观', '看空', '减持', '减持评级', '卖出', '卖出评级',
            '下调评级', '维持减持', '下调目标价',
            # 风险警示
            '风险', '警告', '风险提示', '风险警示', '风险因素',
            '调查', '处罚', '违规', '违规操作', '监管处罚',
            '立案调查', '涉嫌违规', '被立案',
            # 业务收缩
            '收缩', '裁员', '关停', '停产', '业务收缩',
            '解约', '违约', '债务违约', '资金链紧张',
            # 退市风险
            '退市', 'ST', '退市风险', '退市预警', '可能退市',
            # 其他负面
            '事故', '火灾', '爆炸', '质量门', '召回',
            '诉讼', '法律纠纷', '仲裁', '仲裁败诉',
            '高管离职', '重要人员变动', '管理层变动'
        ]
        
        # 强度关键词（增强情感强度，扩展版）
        self.intensity_keywords = {
            'high': [
                '大幅', '暴涨', '暴跌', '重大', '重磅', '紧急', '突发',
                '剧烈', '猛烈', '急速', '疯狂', '极速', '空前',
                '历史性', '里程碑', '突破性', '革命性'
            ],
            'medium': [
                '明显', '显著', '持续', '连续', '稳步', '逐步',
                '加速', '放缓', '波动', '震荡'
            ],
            'low': [
                '小幅', '轻微', '可能', '或', '或将', '有望',
                '预计', '预期', '或将'
            ]
        }
        
        # 否定词（用于反转情感）
        self.negation_words = [
            '不', '没', '未', '非', '无', '别', '勿',
            '没有', '未能', '不会', '不会', '不可能',
            '难以', '不易', '不太', '不够'
        ]
        
        # 情感词权重（不同关键词的重要性）
        self.keyword_weights = {
            # 高权重（强烈信号）
            'high_weight': [
                '涨停', '跌停', '暴涨', '暴跌', '创新高', '创新低',
                '业绩超预期', '业绩暴增', '业绩预警', '退市',
                '重大合同', '重大事故', '立案调查'
            ],
            # 中权重
            'medium_weight': [
                '上涨', '下跌', '增长', '下降', '推荐', '减持',
                '收购', '重组', '订单', '违约'
            ],
            # 低权重
            'low_weight': [
                '可能', '预计', '或将', '有望'
            ]
        }
        
        # 新闻重要性关键词（用于重要性评分）
        self.importance_keywords = {
            'very_high': [  # 极高重要性（政策、重大事件）
                '央行', '证监会', '银保监会', '财政部', '发改委',
                '重大政策', '重磅', '突发', '紧急', '立案调查',
                '退市', '重组', '收购', '合并', '重大合同',
                '业绩暴增', '业绩暴亏', '涨停', '跌停'
            ],
            'high': [  # 高重要性
                '业绩', '盈利', '亏损', '订单', '中标', '合作',
                '回购', '分红', '增持', '减持', '评级',
                '创新高', '创新低', '突破', '破位'
            ],
            'medium': [  # 中等重要性
                '上涨', '下跌', '增长', '下降', '推荐',
                '新产品', '新业务', '市场拓展'
            ],
            'low': [  # 低重要性
                '预计', '可能', '或将', '有望', '或将'
            ]
        }
        
        # 如果jieba可用，初始化自定义词典
        if JIEBA_AVAILABLE:
            try:
                # 添加股票相关专业词汇
                jieba.add_word('涨停', freq=1000, tag='n')
                jieba.add_word('跌停', freq=1000, tag='n')
                jieba.add_word('创新高', freq=1000, tag='v')
                jieba.add_word('创新低', freq=1000, tag='v')
                jieba.add_word('业绩超预期', freq=1000, tag='n')
                jieba.add_word('业绩暴增', freq=1000, tag='n')
                jieba.add_word('立案调查', freq=1000, tag='n')
                jieba.add_word('退市风险', freq=1000, tag='n')
            except Exception as e:
                logger.debug(f"初始化jieba自定义词典失败: {str(e)}")
    
    def analyze(self, news: Dict) -> Dict:
        """
        分析单条新闻的情感
        
        Args:
            news: 新闻字典，包含title和content
            
        Returns:
            情感分析结果: {
                'sentiment': 'positive'/'negative'/'neutral',
                'score': 情感分数 (-1到1),
                'confidence': 置信度 (0到1),
                'keywords': 匹配的关键词列表
            }
        """
        try:
            # 合并标题和内容
            title = news.get('title', '')
            content = news.get('content', '')
            text = f"{title} {content}"
            original_text = text  # 保留原始文本（不转小写，用于jieba分词）
            text_lower = text.lower()  # 转为小写用于关键词匹配
            
            # 使用jieba分词（如果可用）
            words = []
            words_text = ''
            words_text_lower = ''
            if JIEBA_AVAILABLE:
                try:
                    # 提取关键词（TF-IDF）
                    keywords_tfidf = jieba.analyse.extract_tags(original_text, topK=20, withWeight=True)
                    words = [kw[0] for kw in keywords_tfidf]
                    # 也可以进行全文分词
                    words_full = list(jieba.cut(original_text))
                    words.extend(words_full)
                    words_text = ' '.join(words)
                    words_text_lower = words_text.lower()
                except Exception as e:
                    logger.debug(f"jieba分词失败，使用简单匹配: {str(e)}")
                    words = []
                    words_text = ''
                    words_text_lower = text_lower
            
            # 用于否定词和强度检查的文本
            text_for_analysis = words_text_lower if (JIEBA_AVAILABLE and words) else text_lower
            
            # 统计关键词匹配
            positive_count = 0
            negative_count = 0
            matched_keywords = []
            intensity = 1.0
            
            # 使用jieba分词后的词列表进行更精确的匹配
            if JIEBA_AVAILABLE and words:
                # 使用分词后的词列表匹配（更精确）
                words_text = ' '.join(words)
                words_text_lower = words_text.lower()
                
                # 检查利好关键词（带权重）
                for keyword in self.positive_keywords:
                    # 在分词结果中查找（更精确）
                    if keyword in words_text or keyword in text_lower:
                        weight = self._get_keyword_weight(keyword)
                        positive_count += weight
                        matched_keywords.append(('positive', keyword, weight))
                
                # 检查利空关键词（带权重）
                for keyword in self.negative_keywords:
                    if keyword in words_text or keyword in text_lower:
                        weight = self._get_keyword_weight(keyword)
                        negative_count += weight
                        matched_keywords.append(('negative', keyword, weight))
            else:
                # 使用简单字符串匹配（回退方案）
                # 改进：使用正则表达式进行更精确的匹配，避免部分匹配
                # 检查利好关键词（带权重）
                for keyword in self.positive_keywords:
                    # 使用单词边界匹配，避免部分匹配（如"上涨"匹配到"持续上涨"）
                    pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                    if pattern.search(text):
                        weight = self._get_keyword_weight(keyword)
                        positive_count += weight
                        matched_keywords.append(('positive', keyword, weight))
                
                # 检查利空关键词（带权重）
                for keyword in self.negative_keywords:
                    pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                    if pattern.search(text):
                        weight = self._get_keyword_weight(keyword)
                        negative_count += weight
                        matched_keywords.append(('negative', keyword, weight))
            
            # 检查否定词（反转情感）- 改进版
            negation_count = sum(1 for neg in self.negation_words if neg in text_for_analysis)
            if negation_count > 0:
                # 改进的否定词处理：检查否定词与关键词的上下文关系
                # 1. 检查否定词是否在关键词附近（前后5个字符内）
                for neg_word in self.negation_words:
                    if neg_word in text:
                        neg_positions = [i for i in range(len(text)) if text[i:i+len(neg_word)] == neg_word]
                        
                        # 检查利好关键词附近的否定词
                        for keyword in self.positive_keywords:
                            if keyword in text:
                                keyword_positions = [i for i in range(len(text)) if text[i:i+len(keyword)] == keyword]
                                # 检查是否有否定词在关键词附近（前后10个字符）
                                for kw_pos in keyword_positions:
                                    for neg_pos in neg_positions:
                                        if abs(kw_pos - neg_pos) <= 10:
                                            # 如果否定词在关键词前面，反转情感
                                            if neg_pos < kw_pos:
                                                negative_count += positive_count * 0.6
                                                positive_count *= 0.2
                                            break
                        
                        # 检查利空关键词附近的否定词
                        for keyword in self.negative_keywords:
                            if keyword in text:
                                keyword_positions = [i for i in range(len(text)) if text[i:i+len(keyword)] == keyword]
                                # 检查是否有否定词在关键词附近（前后10个字符）
                                for kw_pos in keyword_positions:
                                    for neg_pos in neg_positions:
                                        if abs(kw_pos - neg_pos) <= 10:
                                            # 如果否定词在关键词前面，反转情感
                                            if neg_pos < kw_pos:
                                                positive_count += negative_count * 0.6
                                                negative_count *= 0.2
                                            break
                
                # 2. 如果没有匹配到上下文，使用原来的逻辑（作为备用）
                if positive_count > 0 and negation_count > 0 and '不' in text_for_analysis[:200]:
                    negative_count += positive_count * 0.4
                    positive_count *= 0.4
                if negative_count > 0 and negation_count > 0 and '不' in text_for_analysis[:200]:
                    positive_count += negative_count * 0.4
                    negative_count *= 0.4
            
            # 检查强度关键词
            for level, keywords in self.intensity_keywords.items():
                for keyword in keywords:
                    if keyword in text_for_analysis:
                        if level == 'high':
                            intensity = 1.5
                        elif level == 'medium':
                            intensity = 1.2
                        elif level == 'low':
                            intensity = 0.8
                        break
            
            # 计算情感分数
            total_count = positive_count + negative_count
            if total_count == 0:
                sentiment = 'neutral'
                score = 0.0
                confidence = 0.0
            else:
                score = (positive_count - negative_count) / max(total_count, 1) * intensity
                score = max(-1.0, min(1.0, score))  # 限制在-1到1之间
                
                # 改进的置信度计算：考虑关键词权重、强度和上下文
                base_confidence = min(total_count / 5.0, 1.0)
                # 如果有高强度关键词，提高置信度
                intensity_boost = 0.2 if intensity > 1.3 else 0.0
                # 如果关键词较多，提高置信度
                keyword_boost = min(matched_keywords.__len__() / 10.0, 0.2)
                # 最终置信度
                confidence = min(base_confidence + intensity_boost + keyword_boost, 1.0)
                
                if score > 0.1:
                    sentiment = 'positive'
                elif score < -0.1:
                    sentiment = 'negative'
                else:
                    sentiment = 'neutral'
            
            # 计算新闻重要性评分
            importance_score = self._calculate_importance_score(title, content, text_for_analysis)
            
            return {
                'sentiment': sentiment,
                'score': score,
                'confidence': confidence,
                'keywords': matched_keywords,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'importance_score': importance_score,  # 新增：重要性评分
                'importance_level': self._get_importance_level(importance_score)  # 新增：重要性级别
            }
            
        except Exception as e:
            self.logger.error(f"情感分析失败: {str(e)}")
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'keywords': []
            }
    
    def _get_keyword_weight(self, keyword: str) -> float:
        """获取关键词权重"""
        for weight_type, keywords in self.keyword_weights.items():
            if keyword in keywords:
                if weight_type == 'high_weight':
                    return 2.0
                elif weight_type == 'medium_weight':
                    return 1.0
                elif weight_type == 'low_weight':
                    return 0.5
        return 1.0  # 默认权重
    
    def _calculate_importance_score(self, title: str, content: str, text: str) -> float:
        """
        计算新闻重要性评分（0-1，越高越重要）
        
        Args:
            title: 新闻标题
            content: 新闻内容
            text: 文本（已处理）
        
        Returns:
            重要性评分（0-1）
        """
        try:
            score = 0.0
            
            # 1. 检查重要性关键词（在标题中权重更高）
            for level, keywords in self.importance_keywords.items():
                weight = {'very_high': 1.0, 'high': 0.7, 'medium': 0.4, 'low': 0.1}.get(level, 0.1)
                
                for keyword in keywords:
                    # 标题中的关键词权重翻倍
                    if keyword in title:
                        score += weight * 2.0
                    elif keyword in content[:500]:  # 只检查内容前500字符
                        score += weight
            
            # 2. 新闻来源重要性（权威来源更重要）
            source_importance = {
                '央行': 0.9, '证监会': 0.9, '银保监会': 0.9, '财政部': 0.9,
                '上交所': 0.8, '深交所': 0.8, '巨潮资讯': 0.8,
                '财新': 0.7, '证券时报': 0.7, '中国证券报': 0.7
            }
            
            for source, importance in source_importance.items():
                if source in title or source in content[:200]:
                    score += importance * 0.3
                    break
            
            # 3. 新闻长度（重要新闻通常内容更丰富）
            content_length = len(content) if content else 0
            if content_length > 1000:
                score += 0.1
            elif content_length > 500:
                score += 0.05
            
            # 4. 包含数字（重要新闻通常包含具体数据）
            if re.search(r'\d+', text):
                score += 0.05
            
            # 归一化到0-1范围
            importance_score = min(1.0, score / 3.0)  # 除以3作为归一化因子
            
            return round(importance_score, 3)
            
        except Exception as e:
            logger.debug(f"计算重要性评分失败: {str(e)}")
            return 0.5  # 默认中等重要性
    
    def _get_importance_level(self, score: float) -> str:
        """获取重要性级别"""
        if score >= 0.7:
            return 'very_high'  # 极高
        elif score >= 0.5:
            return 'high'  # 高
        elif score >= 0.3:
            return 'medium'  # 中等
        else:
            return 'low'  # 低
    
    def analyze_batch(self, news_list: List[Dict]) -> List[Dict]:
        """
        批量分析新闻情感
        
        Args:
            news_list: 新闻列表
            
        Returns:
            包含情感分析结果的新闻列表
        """
        results = []
        for news in news_list:
            sentiment_result = self.analyze(news)
            news_with_sentiment = {**news, 'sentiment': sentiment_result}
            results.append(news_with_sentiment)
        return results
    
    def get_aggregated_sentiment(self, news_list: List[Dict]) -> Dict:
        """
        获取聚合情感（多条新闻的综合情感）
        
        Args:
            news_list: 新闻列表（已包含sentiment字段）
            
        Returns:
            聚合情感结果: {
                'overall_sentiment': 'positive'/'negative'/'neutral',
                'average_score': 平均分数,
                'weighted_score': 加权分数（根据置信度）,
                'news_count': 新闻数量
            }
        """
        if not news_list:
            return {
                'overall_sentiment': 'neutral',
                'average_score': 0.0,
                'weighted_score': 0.0,
                'news_count': 0
            }
        
        total_score = 0.0
        total_weighted_score = 0.0
        total_confidence = 0.0
        
        for news in news_list:
            if 'sentiment' in news:
                sentiment = news['sentiment']
                score = sentiment.get('score', 0.0)
                confidence = sentiment.get('confidence', 0.0)
                
                total_score += score
                total_weighted_score += score * confidence
                total_confidence += confidence
        
        news_count = len(news_list)
        average_score = total_score / news_count if news_count > 0 else 0.0
        weighted_score = total_weighted_score / total_confidence if total_confidence > 0 else 0.0
        
        # 确定整体情感
        if weighted_score > 0.15:
            overall_sentiment = 'positive'
        elif weighted_score < -0.15:
            overall_sentiment = 'negative'
        else:
            overall_sentiment = 'neutral'
        
        return {
            'overall_sentiment': overall_sentiment,
            'average_score': average_score,
            'weighted_score': weighted_score,
            'news_count': news_count
        }

