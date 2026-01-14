"""
新闻与股票关联模块
实现新闻与股票的自动关联，通过股票名称、行业、板块等信息进行匹配
"""
import os
import sys
import re
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


class NewsStockMapper:
    """新闻与股票关联器"""
    
    def __init__(self):
        self.logger = logger
        self.db = DatabaseConnection()
        self.use_database = USE_DATABASE
        
        # 缓存股票信息（避免重复查询）
        self._stock_info_cache = {}
        self._stock_name_map = {}  # 股票名称到代码的映射
        self._stock_code_map = {}  # 股票代码到信息的映射
        
        # 加载股票信息
        self._load_stock_info()
    
    def _load_stock_info(self):
        """加载股票信息到内存缓存"""
        try:
            if not self.use_database:
                return
            
            # 从stock_predictions表加载（包含最新预测的股票）
            sql = """
                SELECT DISTINCT symbol, name
                FROM stock_predictions
                WHERE symbol IS NOT NULL AND name IS NOT NULL
            """
            results = self.db.execute_query(sql)
            
            for row in results:
                symbol = row.get('symbol', '').strip()
                name = row.get('name', '').strip()
                
                if symbol and name:
                    # 股票代码到名称的映射
                    self._stock_code_map[symbol] = {
                        'symbol': symbol,
                        'name': name
                    }
                    
                    # 股票名称到代码的映射（多种形式）
                    # 1. 完整名称
                    self._stock_name_map[name] = symbol
                    # 2. 去除"股份"、"有限公司"等后缀
                    name_clean = re.sub(r'(股份|有限公司|公司|集团|企业|控股|A股|B股).*$', '', name)
                    if name_clean and name_clean != name:
                        self._stock_name_map[name_clean] = symbol
                    # 3. 去除前两个字（如"中国"、"北京"等）
                    if len(name_clean) > 2:
                        name_short = name_clean[2:]
                        if name_short:
                            self._stock_name_map[name_short] = symbol
            
            self.logger.info(f"已加载 {len(self._stock_code_map)} 只股票信息到缓存")
            
        except Exception as e:
            self.logger.error(f"加载股票信息失败: {str(e)}")
    
    def extract_stock_symbols_from_text(self, text: str) -> List[str]:
        """
        从文本中提取股票代码和名称
        
        Args:
            text: 文本内容（新闻标题或内容）
        
        Returns:
            股票代码列表
        """
        found_symbols = set()
        
        if not text:
            return list(found_symbols)
        
        # 1. 提取股票代码（6位数字，可能是股票代码）
        # 匹配模式：6位数字，可能前面有"代码"、"股票代码"等
        code_pattern = r'(?:代码|股票代码)?[：:：\s]?(\d{6})(?!\d)'
        codes = re.findall(code_pattern, text)
        for code in codes:
            # 验证是否是有效的股票代码（600xxx, 000xxx, 002xxx, 300xxx, 688xxx等）
            if code.startswith(('600', '601', '603', '605', '688', '689')):  # 上海
                found_symbols.add(code)
            elif code.startswith(('000', '001', '002', '003')):  # 深圳主板/中小板
                found_symbols.add(code)
            elif code.startswith(('300', '301')):  # 创业板
                found_symbols.add(code)
            elif code.startswith(('430', '830', '870', '871', '872', '873')):  # 新三板
                found_symbols.add(code)
        
        # 2. 通过股票名称匹配
        for name, symbol in self._stock_name_map.items():
            # 检查名称是否在文本中出现（至少3个字符）
            if len(name) >= 3 and name in text:
                found_symbols.add(symbol)
        
        # 3. 提取股票简称（通常在括号中）
        # 模式：股票名称(简称)
        short_name_pattern = r'(\S+)(?:股份|有限公司|公司|集团|企业|控股)?[\(（](\S+)[\)）]'
        matches = re.findall(short_name_pattern, text)
        for full_name, short_name in matches:
            # 尝试匹配股票简称
            if short_name in self._stock_name_map:
                found_symbols.add(self._stock_name_map[short_name])
        
        return list(found_symbols)
    
    def get_stock_industry_sector(self, symbol: str) -> Dict:
        """
        获取股票的行业和板块信息
        
        Args:
            symbol: 股票代码
        
        Returns:
            {'sector': 板块, 'industry': 行业, 'concepts': [概念列表]}
        """
        try:
            if symbol in self._stock_info_cache:
                return self._stock_info_cache[symbol]
            
            if not self.use_database:
                return {'sector': None, 'industry': None, 'concepts': []}
            
            # 从stock_predictions表获取
            # 先尝试包含sector字段的查询，如果失败则使用不包含sector的查询
            try:
                sql = """
                    SELECT sector, industry, concepts
                    FROM stock_predictions
                    WHERE symbol = %s
                    ORDER BY prediction_date DESC
                    LIMIT 1
                """
                results = self.db.execute_query(sql, (symbol,))
            except Exception as e:
                # 如果sector字段不存在，使用不包含sector的查询
                if "Unknown column 'sector'" in str(e) or "1054" in str(e):
                    self.logger.warning("sector字段不存在，使用不包含sector的查询。请运行 database/add_sector_field.sql 添加字段。")
                    sql = """
                        SELECT industry, concepts
                        FROM stock_predictions
                        WHERE symbol = %s
                        ORDER BY prediction_date DESC
                        LIMIT 1
                    """
                    results = self.db.execute_query(sql, (symbol,))
                    # 为结果添加sector字段（设为None）
                    if results:
                        results[0]['sector'] = None
                else:
                    raise
            
            if results:
                row = results[0]
                sector = row.get('sector')
                industry = row.get('industry')
                concepts = row.get('concepts', '[]')
                
                # 解析concepts JSON
                try:
                    import json
                    concepts_list = json.loads(concepts) if isinstance(concepts, str) else concepts
                    if not isinstance(concepts_list, list):
                        concepts_list = []
                except:
                    concepts_list = []
                
                result = {
                    'sector': sector,
                    'industry': industry,
                    'concepts': concepts_list
                }
                
                # 缓存结果
                self._stock_info_cache[symbol] = result
                return result
            
            return {'sector': None, 'industry': None, 'concepts': []}
            
        except Exception as e:
            self.logger.error(f"获取股票行业信息失败 {symbol}: {str(e)}")
            return {'sector': None, 'industry': None, 'concepts': []}
    
    def map_news_to_stocks(self, news: Dict) -> List[Dict]:
        """
        将新闻关联到相关股票
        
        Args:
            news: 新闻字典，包含title和content
        
        Returns:
            关联结果列表: [{'symbol': 股票代码, 'relevance_score': 相关性得分, 'match_type': 匹配类型}, ...]
        """
        results = []
        
        if not news:
            return results
        
        # 合并标题和内容
        text = f"{news.get('title', '')} {news.get('content', '')}"
        
        # 1. 直接匹配股票代码和名称
        symbols = self.extract_stock_symbols_from_text(text)
        
        for symbol in symbols:
            # 获取股票的行业和板块信息
            stock_info = self.get_stock_industry_sector(symbol)
            
            results.append({
                'symbol': symbol,
                'relevance_score': 1.0,  # 直接匹配，相关性最高
                'match_type': 'direct',
                'sector': stock_info.get('sector'),
                'industry': stock_info.get('industry'),
                'concepts': stock_info.get('concepts', [])
            })
        
        # 2. 通过行业和板块匹配
        if not symbols:  # 如果没有直接匹配，尝试行业匹配
            industry_matches = self._match_by_industry(text)
            results.extend(industry_matches)
        
        # 3. 去重和排序
        seen_symbols = set()
        unique_results = []
        for result in results:
            symbol = result['symbol']
            if symbol not in seen_symbols:
                seen_symbols.add(symbol)
                unique_results.append(result)
        
        # 按相关性得分排序
        unique_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return unique_results
    
    def _match_by_industry(self, text: str) -> List[Dict]:
        """
        通过行业和板块匹配股票
        
        Args:
            text: 文本内容
        
        Returns:
            匹配结果列表
        """
        results = []
        
        try:
            # 行业关键词列表（可以根据实际情况扩展）
            industry_keywords = {
                '银行': ['银行', '银行业', '金融机构'],
                '保险': ['保险', '保险业'],
                '证券': ['证券', '证券公司', '券商'],
                '房地产': ['房地产', '地产', '房地产行业'],
                '医药': ['医药', '医疗', '生物医药', '制药'],
                '科技': ['科技', '人工智能', 'AI', '互联网', '软件', '芯片', '半导体'],
                '新能源': ['新能源', '光伏', '风电', '锂电池', '电动汽车', '新能源车'],
                '消费': ['消费', '零售', '白酒', '食品', '饮料'],
                '制造业': ['制造', '工业', '机械设备'],
                '交通运输': ['交通', '物流', '航运', '航空'],
                '能源': ['能源', '石油', '天然气', '煤炭'],
                '化工': ['化工', '化学', '化学制品'],
                '钢铁': ['钢铁', '钢材'],
                '有色金属': ['有色金属', '铜', '铝', '锌', '黄金'],
                '建筑材料': ['建材', '水泥', '玻璃', '陶瓷'],
                '电力': ['电力', '电力行业', '发电'],
                '公用事业': ['公用事业', '水务', '燃气'],
                '通信': ['通信', '5G', '通信设备'],
                '传媒': ['传媒', '文化', '影视', '游戏'],
                '农业': ['农业', '养殖', '种植', '农产品']
            }
            
            # 在文本中查找行业关键词
            matched_industries = []
            for industry, keywords in industry_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        matched_industries.append(industry)
                        break
            
            if not matched_industries:
                return results
            
            # 查询匹配这些行业的股票
            if not self.use_database:
                return results
            
            # 构建查询条件
            industry_conditions = []
            for industry in matched_industries:
                industry_conditions.append(f"industry LIKE '%{industry}%'")
            
            if not industry_conditions:
                return results
            
            # 先尝试包含sector字段的查询，如果失败则使用不包含sector的查询
            try:
                sql = f"""
                    SELECT DISTINCT symbol, name, industry, sector
                    FROM stock_predictions
                    WHERE ({' OR '.join(industry_conditions)})
                    ORDER BY prediction_date DESC
                    LIMIT 50
                """
                query_results = self.db.execute_query(sql)
            except Exception as e:
                # 如果sector字段不存在，使用不包含sector的查询
                if "Unknown column 'sector'" in str(e) or "1054" in str(e):
                    self.logger.warning("sector字段不存在，使用不包含sector的查询。请运行 database/add_sector_field.sql 添加字段。")
                    sql = f"""
                        SELECT DISTINCT symbol, name, industry
                        FROM stock_predictions
                        WHERE ({' OR '.join(industry_conditions)})
                        ORDER BY prediction_date DESC
                        LIMIT 50
                    """
                    query_results = self.db.execute_query(sql)
                    # 为每个结果添加sector字段（设为None）
                    for row in query_results:
                        row['sector'] = None
                else:
                    raise
            
            for row in query_results:
                symbol = row.get('symbol')
                industry = row.get('industry', '')
                
                # 计算相关性得分（基于行业匹配）
                relevance_score = 0.5  # 基础得分
                
                # 如果行业完全匹配，提高得分
                for matched_industry in matched_industries:
                    if matched_industry in industry:
                        relevance_score = 0.7
                        break
                
                results.append({
                    'symbol': symbol,
                    'relevance_score': relevance_score,
                    'match_type': 'industry',
                    'sector': row.get('sector'),
                    'industry': industry,
                    'concepts': []
                })
            
        except Exception as e:
            self.logger.error(f"通过行业匹配股票失败: {str(e)}")
        
        return results
    
    def update_news_stock_mapping(self, news_id: int, mappings: List[Dict]) -> bool:
        """
        更新新闻的股票关联
        
        Args:
            news_id: 新闻ID
            mappings: 关联结果列表
        
        Returns:
            是否成功
        """
        try:
            if not self.use_database:
                return False
            
            # 将关联信息保存到news_articles表的相关字段
            # 如果有多个股票，选择相关性最高的一个作为主要关联
            if mappings:
                primary_mapping = mappings[0]
                symbol = primary_mapping.get('symbol')
                sector = primary_mapping.get('sector')
                industry = primary_mapping.get('industry')
                
                # 如果有多个股票，可能需要创建news_stock_mapping表来存储多对多关系
                # 这里先只更新主要关联
                sql = """
                    UPDATE news_articles
                    SET symbol = %s,
                        sector = %s,
                        industry = %s,
                        relevance_type = %s,
                        relevance_score = %s
                    WHERE id = %s
                """
                
                match_type = primary_mapping.get('match_type', 'market')
                relevance_score = primary_mapping.get('relevance_score', 0.5)
                
                self.db.execute_update(sql, (symbol, sector, industry, match_type, relevance_score, news_id))
                
                self.logger.debug(f"更新新闻 {news_id} 的股票关联: {symbol} (相关性: {relevance_score:.2f})")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"更新新闻股票关联失败 {news_id}: {str(e)}")
            return False
    
    def process_news_batch(self, limit: int = 100) -> Dict[str, int]:
        """
        批量处理未关联的新闻，自动关联股票
        
        Args:
            limit: 处理数量限制
        
        Returns:
            {'processed': 处理数量, 'mapped': 关联数量, 'failed': 失败数量}
        """
        result = {'processed': 0, 'mapped': 0, 'failed': 0}
        
        try:
            if not self.use_database:
                return result
            
            # 查询未关联的新闻（symbol为NULL或relevance_score为NULL）
            sql = """
                SELECT id, title, content, symbol, sector, industry
                FROM news_articles
                WHERE (symbol IS NULL OR relevance_score IS NULL)
                AND title IS NOT NULL
                ORDER BY fetch_time DESC
                LIMIT %s
            """
            
            news_list = self.db.execute_query(sql, (limit,))
            
            for news in news_list:
                news_id = news['id']
                title = news.get('title', '')
                content = news.get('content', '')
                
                # 如果已经有symbol，跳过
                if news.get('symbol'):
                    continue
                
                # 尝试关联股票
                try:
                    news_dict = {'title': title, 'content': content or ''}
                    mappings = self.map_news_to_stocks(news_dict)
                    
                    if mappings:
                        # 更新新闻关联
                        if self.update_news_stock_mapping(news_id, mappings):
                            result['mapped'] += 1
                        else:
                            result['failed'] += 1
                    
                    result['processed'] += 1
                    
                except Exception as e:
                    self.logger.error(f"处理新闻 {news_id} 失败: {str(e)}")
                    result['failed'] += 1
            
            self.logger.info(f"批量处理新闻完成: 处理 {result['processed']}, 关联 {result['mapped']}, 失败 {result['failed']}")
            
        except Exception as e:
            self.logger.error(f"批量处理新闻失败: {str(e)}")
        
        return result
