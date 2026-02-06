"""
新闻内容分析模块
负责分析新闻的发布时间和真实性，避免误导股票预测
"""
import os
import sys
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import hashlib

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection as DBConnection
from config_db import USE_DATABASE

logger = get_logger(__name__)


class NewsContentAnalyzer:
    """新闻内容分析器"""
    
    def __init__(self):
        self.logger = logger
        self.db = DBConnection() if USE_DATABASE else None
        
        # 可疑关键词（可能表示虚假新闻）
        self.suspicious_keywords = [
            '内幕消息', '绝密', '独家爆料', '内部消息', '小道消息',
            '保证收益', '稳赚不赔', '100%', '绝对', '一定',
            '紧急通知', '最后机会', '限时', '立即行动',
            '免费推荐', '免费送', '免费领取',
            '加微信', '加QQ', '联系QQ', '联系微信', '扫码',
            '点击链接', '点击查看', '立即查看',
            '投资群', '股票群', '交流群', 'VIP群',
            '代操盘', '代操作', '代理', '分成',
            '涨停板', '连续涨停', '必涨', '必跌'
        ]
        
        # 可信来源（官方、权威媒体）
        self.trusted_sources = [
            '上交所', '深交所', '证监会', '银监会', '保监会',
            '央行', '财政部', '发改委', '工信部',
            '新华社', '人民日报', '央视', '中央',
            '证券时报', '中国证券报', '上海证券报', '证券日报',
            '第一财经', '21世纪经济报道', '经济观察报',
            '财新', '财新网', '财新传媒',
            '官方', '公告', '披露', '公告'
        ]
        
        # 可疑来源（可能不可靠）
        self.untrusted_sources = [
            '个人', '网友', '爆料', '传闻', '传言',
            '据传', '据说', '听说', '消息称', '有消息',
            '未经证实', '待核实', '疑似'
        ]
    
    def analyze_news(self, news: Dict) -> Dict:
        """
        综合分析新闻内容
        
        Args:
            news: 新闻字典，包含title, content, source, publish_time等字段
            
        Returns:
            分析结果字典，包含：
            - time_analysis: 发布时间分析结果
            - credibility_analysis: 真实性分析结果
            - is_reliable: 是否可靠（True/False）
            - reliability_score: 可靠性得分（0-1）
            - warnings: 警告信息列表
        """
        result = {
            'time_analysis': {},
            'credibility_analysis': {},
            'is_reliable': True,
            'reliability_score': 1.0,
            'warnings': []
        }
        
        # 1. 分析发布时间
        time_analysis = self.analyze_publish_time(news)
        result['time_analysis'] = time_analysis
        
        # 2. 分析真实性
        credibility_analysis = self.analyze_credibility(news)
        result['credibility_analysis'] = credibility_analysis
        
        # 3. 综合判断可靠性
        reliability_score = self._calculate_reliability_score(time_analysis, credibility_analysis)
        result['reliability_score'] = reliability_score
        result['is_reliable'] = reliability_score >= 0.6  # 阈值0.6
        
        # 4. 生成警告信息
        warnings = []
        if not time_analysis.get('is_valid', False):
            warnings.append(f"发布时间异常: {time_analysis.get('reason', '')}")
        if credibility_analysis.get('suspicious_count', 0) > 0:
            warnings.append(f"发现 {credibility_analysis.get('suspicious_count')} 个可疑关键词")
        if credibility_analysis.get('is_untrusted_source', False):
            warnings.append(f"来源不可靠: {news.get('source', '未知')}")
        if reliability_score < 0.6:
            warnings.append(f"新闻可靠性较低（得分: {reliability_score:.2f}），可能误导预测")
        
        result['warnings'] = warnings
        
        return result
    
    def analyze_publish_time(self, news: Dict) -> Dict:
        """
        分析新闻发布时间
        
        Args:
            news: 新闻字典
            
        Returns:
            发布时间分析结果：
            - publish_time: 解析后的发布时间
            - event_time: 事件发生时间（如果存在）
            - time_type: 时间类型（publish_time/event_time/both/unknown）
            - is_valid: 时间是否有效
            - time_quality: 时间质量（good/normal/suspicious/invalid）
            - reason: 原因说明
            - time_delta: 与当前时间的差值（小时）
        """
        result = {
            'publish_time': None,
            'event_time': None,
            'time_type': 'unknown',
            'is_valid': False,
            'time_quality': 'invalid',
            'reason': '',
            'time_delta': None
        }
        
        # 获取发布时间
        news_time = news.get('time') or news.get('publish_time') or news.get('pub_time')
        
        # 如果字段中没有时间，尝试从内容中提取发布时间
        if not news_time:
            content = news.get('content', '')
            title = news.get('title', '')
            if content or title:
                try:
                    from utils.news_time_extractor import NewsTimeExtractor
                    extracted_time = NewsTimeExtractor.extract_publish_time(content, title)
                    if extracted_time:
                        news_time = extracted_time
                        result['time_type'] = 'publish_time'
                        self.logger.debug(f"从内容中提取到发布时间: {title[:50] if title else '无标题'}... -> {extracted_time}")
                except Exception as e:
                    self.logger.debug(f"从内容提取发布时间失败: {str(e)}")
        
        if not news_time:
            result['reason'] = '未找到发布时间信息'
            return result
        
        # 如果已经是datetime对象，直接使用
        if isinstance(news_time, datetime):
            publish_time = news_time
        else:
            # 解析发布时间
            publish_time = self._parse_time(news_time)
            if not publish_time:
                result['reason'] = f'无法解析发布时间: {news_time}'
                return result
        
        result['publish_time'] = publish_time
        result['is_valid'] = True
        
        # 新增：尝试提取事件时间（从内容中间）
        content = news.get('content', '')
        title = news.get('title', '')
        if content or title:
            try:
                from utils.news_time_extractor import NewsTimeExtractor
                # 尝试提取事件时间（从内容中间，不是发布时间）
                # 使用_extract_all_times_from_content获取所有时间，然后判断是否是事件时间
                all_times = NewsTimeExtractor._extract_all_times_from_content(content, title)
                if all_times:
                    # 找到与发布时间不同的时间，可能是事件时间
                    text = f"{title} {content}".strip()
                    for time_dt in all_times:
                        if time_dt != publish_time:
                            # 检查这个时间是否可能是事件时间
                            time_str = NewsTimeExtractor._format_time_for_search(time_dt, text)
                            if time_str and not NewsTimeExtractor._is_publish_time(time_str, text):
                                result['event_time'] = time_dt
                                if result['time_type'] == 'unknown':
                                    result['time_type'] = 'event_time'
                                else:
                                    result['time_type'] = 'both'
                                self.logger.debug(f"检测到事件时间: {time_dt}")
                                break
            except Exception as e:
                self.logger.debug(f"提取事件时间失败: {str(e)}")
        
        # 如果还没有设置time_type，设置为publish_time
        if result['time_type'] == 'unknown':
            result['time_type'] = 'publish_time'
        
        # 计算时间差
        now = datetime.now()
        time_delta = (now - publish_time).total_seconds() / 3600  # 转换为小时
        result['time_delta'] = time_delta
        
        # 判断时间质量
        if time_delta < 0:
            # 未来时间，不合理
            result['time_quality'] = 'suspicious'
            result['reason'] = f'发布时间在未来（{time_delta:.1f}小时后）'
            result['is_valid'] = False
        elif time_delta > 720:  # 30天前
            result['time_quality'] = 'suspicious'
            result['reason'] = f'发布时间过旧（{time_delta/24:.1f}天前）'
        elif time_delta > 168:  # 7天前
            result['time_quality'] = 'normal'
            result['reason'] = f'发布时间较旧（{time_delta/24:.1f}天前）'
        elif time_delta <= 24:  # 24小时内
            result['time_quality'] = 'good'
            result['reason'] = f'发布时间较新（{time_delta:.1f}小时前）'
        else:
            result['time_quality'] = 'normal'
            result['reason'] = f'发布时间正常（{time_delta/24:.1f}天前）'
        
        return result
    
    def analyze_credibility(self, news: Dict) -> Dict:
        """
        分析新闻真实性
        
        Args:
            news: 新闻字典
            
        Returns:
            真实性分析结果：
            - suspicious_count: 可疑关键词数量
            - suspicious_keywords: 发现的可疑关键词列表
            - is_trusted_source: 是否可信来源
            - is_untrusted_source: 是否不可信来源
            - credibility_score: 可信度得分（0-1）
            - reason: 原因说明
        """
        result = {
            'suspicious_count': 0,
            'suspicious_keywords': [],
            'is_trusted_source': False,
            'is_untrusted_source': False,
            'credibility_score': 1.0,
            'reason': ''
        }
        
        # 获取新闻内容
        title = news.get('title', '')
        content = news.get('content', '') or news.get('summary', '')
        source = news.get('source', '').lower()
        text = f"{title} {content}".lower()
        
        # 1. 检查可疑关键词
        found_keywords = []
        for keyword in self.suspicious_keywords:
            if keyword in text:
                found_keywords.append(keyword)
        
        result['suspicious_count'] = len(found_keywords)
        result['suspicious_keywords'] = found_keywords
        
        # 2. 检查来源可信度
        is_trusted = any(trusted in source for trusted in self.trusted_sources)
        is_untrusted = any(untrusted in source for untrusted in self.untrusted_sources)
        
        result['is_trusted_source'] = is_trusted
        result['is_untrusted_source'] = is_untrusted
        
        # 3. 计算可信度得分
        credibility_score = 1.0
        
        # 可疑关键词扣分（每个关键词扣0.1分）
        credibility_score -= len(found_keywords) * 0.1
        
        # 不可信来源扣分
        if is_untrusted:
            credibility_score -= 0.3
        
        # 可信来源加分
        if is_trusted:
            credibility_score += 0.2
        
        # 标题或内容过短扣分
        if len(title) < 10 or len(content) < 50:
            credibility_score -= 0.2
        
        # 限制得分范围
        credibility_score = max(0.0, min(1.0, credibility_score))
        
        result['credibility_score'] = credibility_score
        
        # 生成原因说明
        reasons = []
        if found_keywords:
            reasons.append(f"发现可疑关键词: {', '.join(found_keywords[:3])}")
        if is_untrusted:
            reasons.append(f"来源不可靠: {source}")
        if is_trusted:
            reasons.append(f"来源可信: {source}")
        if len(title) < 10:
            reasons.append("标题过短")
        if len(content) < 50:
            reasons.append("内容过短")
        
        result['reason'] = '; '.join(reasons) if reasons else '无明显问题'
        
        return result
    
    def _parse_time(self, time_str) -> Optional[datetime]:
        """
        解析时间字符串
        
        Args:
            time_str: 时间字符串或datetime对象
            
        Returns:
            datetime对象，解析失败返回None
        """
        if not time_str:
            return None
        
        # 如果已经是datetime对象，直接返回
        if isinstance(time_str, datetime):
            return time_str
        
        # 转换为字符串
        if not isinstance(time_str, str):
            time_str = str(time_str)
        
        # 确保是字符串后再调用strip
        if not isinstance(time_str, str):
            return None
        
        time_str = time_str.strip()
        
        # 常见时间格式
        time_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y年%m月%d日 %H:%M',
            '%Y年%m月%d日',
            '%m-%d %H:%M',
            '%m/%d %H:%M',
        ]
        
        # 尝试各种格式
        for fmt in time_formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                # 如果是没有年份的格式，假设是今年
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt
            except ValueError:
                continue
        
        # 尝试解析相对时间（如"2小时前"、"昨天"等）
        relative_time = self._parse_relative_time(time_str)
        if relative_time:
            return relative_time
        
        return None
    
    def _parse_relative_time(self, time_str) -> Optional[datetime]:
        """
        解析相对时间（如"2小时前"、"昨天"等）
        
        Args:
            time_str: 时间字符串或datetime对象
            
        Returns:
            datetime对象，解析失败返回None
        """
        # 如果已经是datetime对象，直接返回
        if isinstance(time_str, datetime):
            return time_str
        
        # 转换为字符串
        if not isinstance(time_str, str):
            time_str = str(time_str)
        
        # 确保是字符串后再调用strip
        if not isinstance(time_str, str):
            return None
        
        time_str = time_str.strip().lower()
        now = datetime.now()
        
        # 匹配"X分钟前"
        match = re.search(r'(\d+)\s*分钟前', time_str)
        if match:
            minutes = int(match.group(1))
            return now - timedelta(minutes=minutes)
        
        # 匹配"X小时前"
        match = re.search(r'(\d+)\s*小时前', time_str)
        if match:
            hours = int(match.group(1))
            return now - timedelta(hours=hours)
        
        # 匹配"X天前"
        match = re.search(r'(\d+)\s*天前', time_str)
        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)
        
        # 匹配"昨天"
        if '昨天' in time_str or 'yesterday' in time_str:
            return now - timedelta(days=1)
        
        # 匹配"今天"
        if '今天' in time_str or 'today' in time_str:
            # 尝试提取时间部分
            match = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return None
    
    def _calculate_reliability_score(self, time_analysis: Dict, credibility_analysis: Dict) -> float:
        """
        计算综合可靠性得分
        
        Args:
            time_analysis: 发布时间分析结果
            credibility_analysis: 真实性分析结果
            
        Returns:
            可靠性得分（0-1）
        """
        score = 1.0
        
        # 时间质量影响
        time_quality = time_analysis.get('time_quality', 'invalid')
        if time_quality == 'invalid':
            score *= 0.3  # 时间无效，大幅降低可靠性
        elif time_quality == 'suspicious':
            score *= 0.6  # 时间可疑，降低可靠性
        elif time_quality == 'normal':
            score *= 0.8  # 时间正常，略微降低
        # good 不扣分
        
        # 可信度影响
        credibility_score = credibility_analysis.get('credibility_score', 1.0)
        score = (score + credibility_score) / 2  # 取平均值
        
        return score
    
    def should_use_for_prediction(self, news: Dict, analysis_result: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        判断新闻是否应该用于股票预测
        
        Args:
            news: 新闻字典
            analysis_result: 分析结果（如果已分析过，可以传入避免重复分析）
            
        Returns:
            (是否应该使用, 原因说明)
        """
        if analysis_result is None:
            analysis_result = self.analyze_news(news)
        
        # 可靠性得分低于阈值，不建议使用
        if analysis_result['reliability_score'] < 0.6:
            return False, f"可靠性得分过低（{analysis_result['reliability_score']:.2f}），不建议用于预测"
        
        # 时间无效，不建议使用
        if not analysis_result['time_analysis'].get('is_valid', False):
            return False, f"发布时间无效: {analysis_result['time_analysis'].get('reason', '')}"
        
        # 有严重警告，不建议使用
        if len(analysis_result['warnings']) >= 3:
            return False, f"发现多个问题: {', '.join(analysis_result['warnings'][:2])}"
        
        return True, "新闻质量良好，可以用于预测"
