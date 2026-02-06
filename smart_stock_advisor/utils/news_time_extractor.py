"""
新闻时间提取工具
从新闻内容（HTML/文本）中提取发布时间
"""
import re
from datetime import datetime, timedelta
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class NewsTimeExtractor:
    """从新闻内容中提取发布时间"""
    
    # 常见的时间格式模式
    TIME_PATTERNS = [
        # 标准格式: 2026-01-14 15:30:00
        (r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})', '%Y-%m-%d %H:%M:%S'),
        # 标准格式（无秒）: 2026-01-14 15:30
        (r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2})', '%Y-%m-%d %H:%M'),
        # 日期格式: 2026-01-14
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
        # 中文格式: 2026年1月14日 15:30:00
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{1,2}):(\d{1,2})', '%Y年%m月%d日 %H:%M:%S'),
        # 中文格式（无秒）: 2026年1月14日 15:30
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{1,2})', '%Y年%m月%d日 %H:%M'),
        # 中文日期: 2026年1月14日
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日', '%Y年%m月%d日'),
        # 斜杠格式: 2026/01/14 15:30:00
        (r'(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})', '%Y/%m/%d %H:%M:%S'),
        # 斜杠格式（无秒）: 2026/01/14 15:30
        (r'(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{1,2})', '%Y/%m/%d %H:%M'),
        # 点格式: 2026.01.14 15:30:00
        (r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})', '%Y.%m.%d %H:%M:%S'),
        # 点格式（无秒）: 2026.01.14 15:30
        (r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{1,2})', '%Y.%m.%d %H:%M'),
    ]
    
    # 相对时间关键词
    RELATIVE_TIME_KEYWORDS = {
        '刚刚': 0,
        '刚才': 0,
        '1分钟前': 1,
        '2分钟前': 2,
        '3分钟前': 3,
        '5分钟前': 5,
        '10分钟前': 10,
        '30分钟前': 30,
        '1小时前': 60,
        '2小时前': 120,
        '3小时前': 180,
        '今天': 0,
        '今日': 0,
        '昨天': 1440,  # 24小时 * 60分钟
        '昨日': 1440,
        '前天': 2880,  # 48小时
    }
    
    @staticmethod
    def extract_from_content(content: str, title: str = '') -> Optional[datetime]:
        """
        从新闻内容中提取发布时间（兼容旧方法，内部调用extract_publish_time）
        
        Args:
            content: 新闻内容（HTML或纯文本）
            title: 新闻标题（可选，也可能包含时间信息）
        
        Returns:
            datetime对象，如果提取失败返回None
        """
        return NewsTimeExtractor.extract_publish_time(content, title)
    
    @staticmethod
    def extract_publish_time(content: str, title: str = '') -> Optional[datetime]:
        """
        专门提取发布时间（不是事件时间）
        
        策略：
        1. 优先从HTML meta标签提取（最准确）
        2. 从新闻开头/结尾提取（通常是发布时间）
        3. 如果提取的时间在内容中间，且上下文包含"于"、"在"等关键词，可能是事件时间，忽略
        
        Args:
            content: 新闻内容（HTML或纯文本）
            title: 新闻标题（可选，也可能包含时间信息）
        
        Returns:
            datetime对象，如果提取失败返回None
        """
        if not content and not title:
            return None
        
        # 合并标题和内容
        text = f"{title} {content}".strip()
        if not text:
            return None
        
        # 方法1: 尝试从HTML的meta标签中提取（最优先，肯定是发布时间）
        publish_time = NewsTimeExtractor._extract_from_meta_tags(text)
        if publish_time:
            logger.debug(f"从meta标签提取到发布时间: {publish_time}")
            return publish_time
        
        # 方法2: 尝试从常见的时间位置提取（开头、结尾）
        publish_time = NewsTimeExtractor._extract_from_common_positions(text)
        if publish_time:
            # 验证是否是发布时间（不是事件时间）
            time_str = NewsTimeExtractor._format_time_for_search(publish_time, text)
            if time_str and NewsTimeExtractor._is_publish_time(time_str, text):
                logger.debug(f"从常见位置提取到发布时间: {time_str} -> {publish_time}")
                return publish_time
        
        # 方法3: 使用正则表达式匹配时间模式（但要验证不是事件时间）
        publish_time = NewsTimeExtractor._extract_with_patterns_checked(text)
        if publish_time:
            logger.debug(f"从内容中提取到发布时间: {publish_time}")
            return publish_time
        
        # 方法4: 尝试解析相对时间（相对时间通常是发布时间）
        publish_time = NewsTimeExtractor._extract_relative_time(text)
        if publish_time:
            logger.debug(f"从相对时间提取到发布时间: {publish_time}")
            return publish_time
        
        return None
    
    @staticmethod
    def _format_time_for_search(dt: datetime, text: str) -> Optional[str]:
        """将datetime格式化为字符串，用于在文本中查找"""
        # 尝试多种格式，找到在文本中存在的格式
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y年%m月%d日 %H:%M:%S',
            '%Y年%m月%d日 %H:%M',
            '%Y年%m月%d日',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y.%m.%d %H:%M:%S',
            '%Y.%m.%d %H:%M',
        ]
        
        for fmt in formats:
            time_str = dt.strftime(fmt)
            if time_str in text:
                return time_str
        
        return None
    
    @staticmethod
    def _is_publish_time(time_str: str, text: str) -> bool:
        """
        判断提取的时间是否是发布时间（而不是事件时间）
        
        规则：
        1. 如果时间在meta标签中，肯定是发布时间（已经在方法1中处理）
        2. 如果时间在开头/结尾500字符内，且附近有"发布时间"关键词，是发布时间
        3. 如果时间在内容中间，且附近有"于"、"在"等关键词，可能是事件时间
        4. 如果时间在开头/结尾，默认认为是发布时间
        
        Args:
            time_str: 时间字符串
            text: 完整文本
        
        Returns:
            True如果是发布时间，False如果是事件时间
        """
        # 查找时间在文本中的位置
        time_pos = text.find(time_str)
        if time_pos == -1:
            return False
        
        # 提取时间前后150字符的上下文
        context_start = max(0, time_pos - 150)
        context_end = min(len(text), time_pos + len(time_str) + 150)
        context = text[context_start:context_end]
        
        # 发布时间关键词（明确表示发布时间）
        publish_keywords = ['发布时间', '发布时间', '发布时间', '发布时间', '发布时间', '发布时间', 
                           '发布时间', '发布时间', '发布时间', '发布时间', '发布时间', '发布时间',
                           '发布时间', '发布时间', '发布时间', '发布时间', '发布时间', '发布时间']
        
        # 事件时间关键词（可能表示事件发生时间）
        event_keywords = ['于', '在', '时间', '日期', '发布', '公告', '披露', '发生', '举行', 
                         '召开', '召开', '召开', '召开', '召开', '召开', '召开', '召开']
        
        # 如果上下文包含明确的发布时间关键词，是发布时间
        if any(keyword in context for keyword in publish_keywords):
            return True
        
        # 判断时间是否在开头或结尾（开头500字符或结尾500字符）
        is_at_start = time_pos < 500
        is_at_end = time_pos > len(text) - 500
        
        # 如果时间在开头或结尾，默认认为是发布时间
        if is_at_start or is_at_end:
            # 但如果上下文包含事件时间关键词，且没有发布时间关键词，可能是事件时间
            if any(keyword in context for keyword in event_keywords):
                # 进一步检查：如果时间明显早于当前时间很多（超过7天），可能是事件时间
                try:
                    parsed_time = NewsTimeExtractor._parse_time_string(time_str)
                    if parsed_time:
                        time_delta = (datetime.now() - parsed_time).total_seconds() / 86400  # 天数
                        if time_delta > 7:  # 超过7天，可能是事件时间
                            return False
                except:
                    pass
            return True
        
        # 如果时间在内容中间，且上下文包含事件时间关键词，可能是事件时间
        if any(keyword in context for keyword in event_keywords):
            return False
        
        # 默认认为是发布时间（保守策略）
        return True
    
    @staticmethod
    def _extract_with_patterns_checked(text: str) -> Optional[datetime]:
        """使用正则表达式匹配时间模式，并验证是否是发布时间"""
        # 尝试所有时间格式模式
        for pattern, fmt in NewsTimeExtractor.TIME_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                time_str = match.group(0)
                parsed_time = NewsTimeExtractor._parse_time_string(time_str, fmt)
                if parsed_time:
                    # 验证时间是否合理（不能是未来时间，不能太早）
                    now = datetime.now()
                    if parsed_time <= now and parsed_time.year >= 2000:
                        # 验证是否是发布时间（不是事件时间）
                        if NewsTimeExtractor._is_publish_time(time_str, text):
                            return parsed_time
        
        return None
    
    @staticmethod
    def _extract_from_meta_tags(text: str) -> Optional[datetime]:
        """从HTML meta标签中提取时间"""
        # 查找常见的meta标签
        meta_patterns = [
            r'<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*name=["\']publishdate["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*name=["\']pubdate["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*name=["\']date["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*itemprop=["\']datePublished["\'][^>]*content=["\']([^"\']+)["\']',
            r'<time[^>]*datetime=["\']([^"\']+)["\']',
            r'<time[^>]*>([^<]+)</time>',
        ]
        
        for pattern in meta_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                time_str = match.group(1).strip()
                parsed_time = NewsTimeExtractor._parse_time_string(time_str)
                if parsed_time:
                    logger.debug(f"从meta标签提取到时间: {time_str} -> {parsed_time}")
                    return parsed_time
        
        return None
    
    @staticmethod
    def _extract_from_common_positions(text: str) -> Optional[datetime]:
        """从常见的时间位置提取（开头、结尾）"""
        # 提取前500字符和后500字符（时间通常在开头或结尾）
        start_text = text[:500]
        end_text = text[-500:] if len(text) > 500 else text
        
        # 查找时间模式（优先查找完整的时间格式）
        for text_part in [start_text, end_text]:
            # 尝试匹配完整的时间格式
            for pattern, fmt in NewsTimeExtractor.TIME_PATTERNS:
                match = re.search(pattern, text_part)
                if match:
                    time_str = match.group(0)
                    parsed_time = NewsTimeExtractor._parse_time_string(time_str)
                    if parsed_time:
                        logger.debug(f"从常见位置提取到时间: {time_str} -> {parsed_time}")
                        return parsed_time
        
        return None
    
    @staticmethod
    def _extract_with_patterns(text: str) -> Optional[datetime]:
        """使用正则表达式匹配时间模式"""
        # 尝试所有时间格式模式
        for pattern, fmt in NewsTimeExtractor.TIME_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                time_str = match.group(0)
                parsed_time = NewsTimeExtractor._parse_time_string(time_str, fmt)
                if parsed_time:
                    # 验证时间是否合理（不能是未来时间，不能太早）
                    now = datetime.now()
                    if parsed_time <= now and parsed_time.year >= 2000:
                        logger.debug(f"从内容中提取到时间: {time_str} -> {parsed_time}")
                        return parsed_time
        
        return None
    
    @staticmethod
    def _extract_relative_time(text: str) -> Optional[datetime]:
        """提取相对时间（今天、1小时前等）"""
        now = datetime.now()
        
        for keyword, minutes in NewsTimeExtractor.RELATIVE_TIME_KEYWORDS.items():
            if keyword in text:
                if minutes == 0:
                    # "刚刚"、"今天"等，返回当前时间
                    return now
                else:
                    # "1小时前"、"昨天"等，计算时间
                    return now - timedelta(minutes=minutes)
        
        return None
    
    @staticmethod
    def _parse_time_string(time_str: str, fmt: Optional[str] = None) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None
        
        time_str = time_str.strip()
        now = datetime.now()
        
        if fmt:
            # 使用指定的格式解析
            try:
                parsed_time = datetime.strptime(time_str, fmt)
                # 如果没有年份，假设是今年
                if parsed_time.year == 1900:
                    parsed_time = parsed_time.replace(year=now.year)
                return parsed_time
            except:
                return None
        else:
            # 尝试所有格式
            for pattern, fmt_pattern in NewsTimeExtractor.TIME_PATTERNS:
                match = re.match(pattern, time_str)
                if match:
                    try:
                        parsed_time = datetime.strptime(time_str, fmt_pattern)
                        # 如果没有年份，假设是今年
                        if parsed_time.year == 1900:
                            parsed_time = parsed_time.replace(year=now.year)
                        return parsed_time
                    except:
                        continue
            
            # 尝试ISO格式
            try:
                from dateutil import parser
                return parser.parse(time_str)
            except:
                pass
            
            return None
    
    @staticmethod
    def _extract_all_times_from_content(content: str, title: str = '') -> list:
        """
        从内容中提取所有时间（包括发布时间和事件时间）
        
        Args:
            content: 新闻内容
            title: 新闻标题
        
        Returns:
            时间列表（datetime对象列表）
        """
        if not content and not title:
            return []
        
        text = f"{title} {content}".strip()
        if not text:
            return []
        
        times = []
        
        # 提取所有匹配的时间模式
        for pattern, fmt in NewsTimeExtractor.TIME_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                time_str = match.group(0)
                parsed_time = NewsTimeExtractor._parse_time_string(time_str, fmt)
                if parsed_time:
                    # 验证时间是否合理
                    now = datetime.now()
                    if parsed_time <= now and parsed_time.year >= 2000:
                        if parsed_time not in times:
                            times.append(parsed_time)
        
        return times