"""
新闻去重优化模块
使用SimHash算法进行内容相似度检测，提高去重准确性
"""
import hashlib
import re
from typing import Optional, Dict, List
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection as DBConnection
from config_db import USE_DATABASE

logger = get_logger(__name__)


class NewsDeduplication:
    """新闻去重优化类"""
    
    def __init__(self, hash_bits: int = 64, threshold: int = 3):
        """
        初始化去重器
        
        Args:
            hash_bits: SimHash位数（默认64位）
            threshold: 相似度阈值，汉明距离小于此值认为是重复（默认3）
        """
        self.logger = logger
        self.hash_bits = hash_bits
        self.threshold = threshold
        self.use_database = USE_DATABASE
    
    def calculate_simhash(self, text: str) -> int:
        """
        计算文本的SimHash值
        
        Args:
            text: 文本内容
        
        Returns:
            SimHash值（整数）
        """
        if not text:
            return 0
        
        # 1. 分词（简单的中文分词，实际可以使用jieba等）
        words = self._tokenize(text)
        
        if not words:
            return 0
        
        # 2. 计算每个词的hash值并加权
        v = [0] * self.hash_bits
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 3. 计算特征向量
        for word, freq in word_freq.items():
            # 计算词的hash值
            word_hash = self._hash_word(word)
            
            # 对hash的每一位加权
            for i in range(self.hash_bits):
                if word_hash & (1 << i):
                    v[i] += freq
                else:
                    v[i] -= freq
        
        # 4. 生成SimHash
        simhash = 0
        for i in range(self.hash_bits):
            if v[i] > 0:
                simhash |= (1 << i)
        
        return simhash
    
    def _tokenize(self, text: str) -> List[str]:
        """
        简单的中文分词（基于字符）
        可以使用jieba等专业分词库优化
        
        Args:
            text: 文本内容
        
        Returns:
            词列表
        """
        # 移除标点符号和空格
        text = re.sub(r'[^\w\s]', '', text)
        
        # 中文分词：按字符（简化实现）
        words = []
        # 匹配中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        for chars in chinese_chars:
            # 如果是单个字符，直接添加
            if len(chars) == 1:
                words.append(chars)
            else:
                # 如果是多个字符，可以拆分为2-gram
                for i in range(len(chars) - 1):
                    words.append(chars[i:i+2])
                # 也保留完整词
                if len(chars) <= 4:
                    words.append(chars)
        
        # 匹配英文单词
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        words.extend(english_words)
        
        # 匹配数字
        numbers = re.findall(r'\d+', text)
        words.extend(numbers)
        
        return words
    
    def _hash_word(self, word: str) -> int:
        """计算词的hash值"""
        return int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16) % (2 ** self.hash_bits)
    
    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """
        计算两个SimHash值的汉明距离
        
        Args:
            hash1: SimHash值1
            hash2: SimHash值2
        
        Returns:
            汉明距离
        """
        x = hash1 ^ hash2
        distance = 0
        while x:
            distance += 1
            x &= x - 1  # 清除最低位的1
        return distance
    
    def is_similar(self, hash1: int, hash2: int) -> bool:
        """
        判断两个SimHash值是否相似（是否重复）
        
        Args:
            hash1: SimHash值1
            hash2: SimHash值2
        
        Returns:
            True表示相似（可能是重复），False表示不相似
        """
        if hash1 == 0 or hash2 == 0:
            return False
        
        distance = self.hamming_distance(hash1, hash2)
        return distance <= self.threshold
    
    def find_similar_news(self, simhash: int, limit: int = 10) -> List[Dict]:
        """
        查找相似的新闻（基于SimHash）
        
        Args:
            simhash: 新闻的SimHash值
            limit: 返回数量限制
        
        Returns:
            相似新闻列表
        """
        if not self.use_database or simhash == 0:
            return []
        
        try:
            # 查询所有新闻的SimHash（分批查询，避免内存过大）
            # 先检查字段是否存在，如果不存在则返回空列表
            try:
                sql = """
                    SELECT id, title, simhash, publish_time, source
                    FROM news_articles
                    WHERE simhash IS NOT NULL AND simhash != 0
                    ORDER BY publish_time DESC
                    LIMIT 1000
                """
                results = DBConnection.execute_query(sql)
            except Exception as e:
                # 如果字段不存在，记录警告并返回空列表
                if "Unknown column 'simhash'" in str(e) or "1054" in str(e):
                    self.logger.warning("simhash字段不存在，跳过SimHash相似度检测。请运行 database/add_simhash_field.sql 添加字段。")
                    return []
                raise
            
            similar_news = []
            for news in results:
                news_simhash = news.get('simhash')
                if news_simhash and self.is_similar(simhash, news_simhash):
                    similar_news.append({
                        'id': news['id'],
                        'title': news['title'],
                        'source': news['source'],
                        'publish_time': news.get('publish_time'),
                        'distance': self.hamming_distance(simhash, news_simhash)
                    })
                    
                    if len(similar_news) >= limit:
                        break
            
            # 按相似度排序（距离越小越相似）
            similar_news.sort(key=lambda x: x['distance'])
            
            return similar_news
            
        except Exception as e:
            self.logger.error(f"查找相似新闻失败: {str(e)}")
            return []
    
    def check_duplicate_by_content(self, title: str, content: str, source: str = None) -> Optional[int]:
        """
        基于内容相似度检查重复新闻
        
        Args:
            title: 新闻标题
            content: 新闻内容
            source: 新闻来源（可选）
        
        Returns:
            如果找到相似新闻，返回相似新闻的ID；否则返回None
        """
        if not self.use_database:
            return None
        
        try:
            # 1. 先检查精确匹配（基于标题和来源）
            if title and source:
                sql = "SELECT id FROM news_articles WHERE title = %s AND source = %s LIMIT 1"
                result = DBConnection.execute_query(sql, (title[:200], source))
                if result:
                    return result[0]['id']
            
            # 2. 计算SimHash
            full_text = f"{title} {content or ''}"
            simhash = self.calculate_simhash(full_text)
            
            if simhash == 0:
                return None
            
            # 3. 查找相似新闻
            similar_news = self.find_similar_news(simhash, limit=5)
            
            if similar_news:
                # 返回最相似的新闻ID
                return similar_news[0]['id']
            
            return None
            
        except Exception as e:
            self.logger.error(f"基于内容检查重复失败: {str(e)}")
            return None
    
    def save_simhash(self, news_id: int, simhash: int) -> bool:
        """
        保存新闻的SimHash值到数据库
        
        Args:
            news_id: 新闻ID
            simhash: SimHash值
        
        Returns:
            是否成功
        """
        if not self.use_database:
            return False
        
        try:
            sql = "UPDATE news_articles SET simhash = %s WHERE id = %s"
            DBConnection.execute_update(sql, (simhash, news_id))
            return True
        except Exception as e:
            self.logger.error(f"保存SimHash失败: {str(e)}")
            return False
    
    def mark_duplicate(self, news_id: int, duplicate_of: int, similarity_score: float = None) -> bool:
        """
        标记新闻为重复新闻
        
        Args:
            news_id: 新闻ID
            duplicate_of: 原始新闻ID
            similarity_score: 相似度得分（可选）
        
        Returns:
            是否成功
        """
        if not self.use_database:
            return False
        
        try:
            sql = """
                UPDATE news_articles 
                SET is_duplicate = 1, duplicate_of = %s
                WHERE id = %s
            """
            DBConnection.execute_update(sql, (duplicate_of, news_id))
            return True
        except Exception as e:
            self.logger.error(f"标记重复新闻失败: {str(e)}")
            return False
