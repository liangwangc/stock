"""
新闻与股票关联模块
实现新闻与股票的自动关联，通过股票名称、行业、板块等信息进行匹配
适配 news-analysis-system-main，连接到 smart_stock_advisor 数据库获取股票信息
"""
import os
import sys
import re
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ..config.config import MAIN_DATABASE_URL, MAIN_DB_CONFIG

# 初始化主数据库连接（用于获取股票信息）
main_engine = create_engine(MAIN_DATABASE_URL)


class StockMapper:
    """新闻与股票关联器（适配 news-analysis-system-main）"""
    
    def __init__(self):
        """初始化股票匹配器"""
        # 缓存股票信息（避免重复查询）
        self._stock_info_cache = {}
        self._stock_name_map = {}  # 股票名称到代码的映射
        self._stock_code_map = {}  # 股票代码到信息的映射
        
        # 加载股票信息
        self._load_stock_info()
    
    def _load_stock_info(self):
        """从 smart_stock_advisor 数据库加载股票信息到内存缓存"""
        try:
            print("正在加载股票信息...")
            
            stock_info_dict = {}  # {symbol: {name, sector, industry}}
            
            # 1. 主要从 stock_history_data 表获取所有股票代码和名称（包含所有有历史数据的股票）
            try:
                sql_history = """
                    SELECT DISTINCT symbol, name
                    FROM stock_history_data
                    WHERE symbol IS NOT NULL AND symbol != '' AND name IS NOT NULL
                    ORDER BY symbol
                """
                df_history = pd.read_sql(sql_history, main_engine)
                print(f"从 stock_history_data 表找到 {len(df_history)} 只股票（含名称）")
                
                # 初始化股票信息字典
                for _, row in df_history.iterrows():
                    symbol = str(row.get('symbol', '')).strip().zfill(6)
                    name = str(row.get('name', '')).strip()
                    if symbol and name:
                        stock_info_dict[symbol] = {
                            'symbol': symbol,
                            'name': name,
                            'sector': None,
                            'industry': None
                        }
            except Exception as e:
                print(f"从 stock_history_data 表加载股票信息失败: {str(e)}")
                # 如果失败，尝试只获取代码
                try:
                    sql_history_code_only = """
                        SELECT DISTINCT symbol
                        FROM stock_history_data
                        WHERE symbol IS NOT NULL AND symbol != ''
                        ORDER BY symbol
                    """
                    df_history = pd.read_sql(sql_history_code_only, main_engine)
                    print(f"从 stock_history_data 表找到 {len(df_history)} 只股票（仅代码）")
                    for _, row in df_history.iterrows():
                        symbol = str(row.get('symbol', '')).strip().zfill(6)
                        if symbol:
                            stock_info_dict[symbol] = {
                                'symbol': symbol,
                                'name': None,
                                'sector': None,
                                'industry': None
                            }
                except Exception as e2:
                    print(f"从 stock_history_data 表加载股票代码也失败: {str(e2)}")
            
            # 2. 可选：从 stock_predictions 表补充行业、板块信息（如果表存在且有数据）
            # 注意：stock_predictions 表不是必须的，只有部分股票有预测数据
            try:
                sql_predictions = """
                    SELECT DISTINCT symbol, name, sector, industry
                    FROM stock_predictions
                    WHERE symbol IS NOT NULL AND name IS NOT NULL
                    ORDER BY prediction_date DESC
                """
                df_predictions = pd.read_sql(sql_predictions, main_engine)
                
                if len(df_predictions) > 0:
                    print(f"从 stock_predictions 表补充 {len(df_predictions)} 条股票的行业信息（可选）")
                    
                    # 更新股票信息字典（补充行业信息）
                    for _, row in df_predictions.iterrows():
                        symbol = str(row.get('symbol', '')).strip().zfill(6)
                        name = str(row.get('name', '')).strip()
                        sector = row.get('sector')
                        industry = row.get('industry')
                        
                        if symbol:
                            if symbol not in stock_info_dict:
                                # 如果 stock_history_data 中没有，添加（但这种情况应该很少）
                                stock_info_dict[symbol] = {
                                    'symbol': symbol,
                                    'name': name,
                                    'sector': sector,
                                    'industry': industry
                                }
                            else:
                                # 补充名称（如果 stock_history_data 中没有）
                                if not stock_info_dict[symbol]['name'] and name:
                                    stock_info_dict[symbol]['name'] = name
                                # 补充行业、板块信息（如果之前没有）
                                if not stock_info_dict[symbol]['sector'] and sector:
                                    stock_info_dict[symbol]['sector'] = sector
                                if not stock_info_dict[symbol]['industry'] and industry:
                                    stock_info_dict[symbol]['industry'] = industry
            except Exception as e:
                # stock_predictions 表不存在或查询失败不影响主要功能，只记录警告
                print(f"注意：无法从 stock_predictions 表补充行业信息（不影响主要功能）: {str(e)}")
            
            # 3. 构建缓存映射（只有有名称的股票才加入映射，用于名称匹配）
            for symbol, info in stock_info_dict.items():
                name = info.get('name')
                if name:  # 只有有名称的股票才加入映射
                    # 股票代码到信息的映射
                    self._stock_code_map[symbol] = {
                        'symbol': symbol,
                        'name': name,
                        'sector': info.get('sector'),
                        'industry': info.get('industry')
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
            
            total_stocks = len(stock_info_dict)
            stocks_with_name = len(self._stock_code_map)
            stocks_with_industry = sum(1 for info in stock_info_dict.values() if info.get('industry'))
            
            print(f"已加载 {stocks_with_name} 只股票信息到缓存（共 {total_stocks} 只股票代码，其中 {stocks_with_industry} 只有行业信息）")
            
        except Exception as e:
            print(f"加载股票信息失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print("提示：请确保 smart_stock_advisor 数据库可访问，且 stock_history_data 表存在")
    
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
            if symbol in self._stock_code_map:
                stock_info = self._stock_code_map[symbol]
                return {
                    'sector': stock_info.get('sector'),
                    'industry': stock_info.get('industry'),
                    'concepts': []  # 概念信息可以从数据库获取，这里简化处理
                }
            
            # 如果缓存中没有，从数据库查询
            sql = """
                SELECT sector, industry
                FROM stock_predictions
                WHERE symbol = %s
                ORDER BY prediction_date DESC
                LIMIT 1
            """
            df = pd.read_sql(sql, main_engine, params=(symbol,))
            
            if not df.empty:
                row = df.iloc[0]
                return {
                    'sector': row.get('sector'),
                    'industry': row.get('industry'),
                    'concepts': []
                }
            
            return {'sector': None, 'industry': None, 'concepts': []}
            
        except Exception as e:
            print(f"获取股票行业信息失败 {symbol}: {str(e)}")
            return {'sector': None, 'industry': None, 'concepts': []}
    
    def map_news_to_stocks(self, title: str, content: str) -> Dict:
        """
        将新闻关联到相关股票
        
        Args:
            title: 新闻标题
            content: 新闻内容
        
        Returns:
            关联结果字典: {
                'primary_symbol': 主要股票代码,
                'symbols': [所有关联的股票代码列表],
                'sector': 板块,
                'industry': 行业,
                'relevance_score': 相关性得分
            }
        """
        result = {
            'primary_symbol': None,
            'symbols': [],
            'sector': None,
            'industry': None,
            'relevance_score': 0.0
        }
        
        if not title and not content:
            return result
        
        # 合并标题和内容
        text = f"{title} {content}"
        
        # 1. 直接匹配股票代码和名称
        symbols = self.extract_stock_symbols_from_text(text)
        
        if symbols:
            # 选择第一个作为主要股票
            primary_symbol = symbols[0]
            stock_info = self.get_stock_industry_sector(primary_symbol)
            
            result['primary_symbol'] = primary_symbol
            result['symbols'] = symbols
            result['sector'] = stock_info.get('sector')
            result['industry'] = stock_info.get('industry')
            result['relevance_score'] = 1.0  # 直接匹配，相关性最高
            
            return result
        
        # 2. 通过行业和板块匹配（如果没有直接匹配）
        industry_matches = self._match_by_industry(text)
        if industry_matches:
            primary_match = industry_matches[0]
            result['primary_symbol'] = primary_match.get('symbol')
            result['symbols'] = [m.get('symbol') for m in industry_matches[:5]]  # 最多5个
            result['sector'] = primary_match.get('sector')
            result['industry'] = primary_match.get('industry')
            result['relevance_score'] = primary_match.get('relevance_score', 0.5)
        
        return result
    
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
            
            # 查询匹配这些行业的股票（使用参数化查询避免格式化错误）
            if not matched_industries:
                return results
            
            # 构建参数化查询
            # 为每个行业创建 LIKE 条件
            like_conditions = []
            params_list = []
            for industry in matched_industries:
                like_conditions.append("industry LIKE %s")
                params_list.append(f'%{industry}%')
            
            sql = f"""
                SELECT DISTINCT symbol, name, industry, sector
                FROM stock_predictions
                WHERE ({' OR '.join(like_conditions)})
                ORDER BY prediction_date DESC
                LIMIT 50
            """
            
            # pandas read_sql 需要参数是元组格式
            df = pd.read_sql(sql, main_engine, params=tuple(params_list))
            
            for _, row in df.iterrows():
                symbol = row.get('symbol')
                industry = row.get('industry', '')
                
                # 计算相关性得分（基于行业匹配）
                relevance_score = 0.5  # 基础得分
                
                # 如果行业完全匹配，提高得分
                for matched_industry in matched_industries:
                    if matched_industry in str(industry):
                        relevance_score = 0.7
                        break
                
                results.append({
                    'symbol': symbol,
                    'relevance_score': relevance_score,
                    'match_type': 'industry',
                    'sector': row.get('sector'),
                    'industry': industry
                })
            
        except Exception as e:
            print(f"通过行业匹配股票失败: {str(e)}")
        
        return results
    
    def save_stock_relations(self, news_df: pd.DataFrame, news_ids: List[int] = None):
        """
        保存股票关联关系到数据库
        
        Args:
            news_df: 新闻DataFrame（包含symbol, sector, industry等字段）
            news_ids: 新闻ID列表（如果为None，则从数据库查询）
        """
        try:
            from ..config.config import DATABASE_URL
            cls_engine = create_engine(DATABASE_URL)
            
            # 如果没有提供news_ids，从数据库查询（通过content_hash）
            if news_ids is None:
                # 获取最近插入的新闻ID
                sql = """
                    SELECT id, content_hash
                    FROM news
                    WHERE content_hash IN :hashes
                    ORDER BY id DESC
                """
                hashes = tuple(news_df['content_hash'].tolist())
                with cls_engine.connect() as conn:
                    result = conn.execute(text(sql), {"hashes": hashes})
                    news_id_map = {row[1]: row[0] for row in result.fetchall()}
                
                news_ids = [news_id_map.get(hash_val) for hash_val in news_df['content_hash'].tolist()]
            
            # 保存到 news_stock_relation 表
            relations = []
            for idx, (news_id, row) in enumerate(zip(news_ids, news_df.itertuples())):
                if not news_id:
                    continue
                
                symbol = getattr(row, 'symbol', None)
                if symbol:
                    relations.append({
                        'news_id': news_id,
                        'symbol': symbol,
                        'relevance_score': 1.0,
                        'relation_type': 'direct'
                    })
            
            if relations:
                # 按 (news_id, symbol) 去重，并用 INSERT IGNORE 避免 uk_news_symbol 重复报错
                seen = set()
                unique_relations = []
                for r in relations:
                    key = (r['news_id'], r['symbol'])
                    if key not in seen:
                        seen.add(key)
                        unique_relations.append(r)
                insert_sql = text("""
                    INSERT IGNORE INTO news_stock_relation (news_id, symbol, relevance_score, relation_type)
                    VALUES (:news_id, :symbol, :relevance_score, :relation_type)
                """)
                with cls_engine.connect() as conn:
                    conn.execute(insert_sql, unique_relations)
                    conn.commit()
                print(f"成功保存 {len(unique_relations)} 条股票关联关系")
        
        except Exception as e:
            print(f"保存股票关联关系失败: {str(e)}")


if __name__ == '__main__':
    # 测试股票匹配功能
    mapper = StockMapper()
    
    test_news = {
        'title': '贵州茅台发布2024年业绩报告',
        'content': '贵州茅台(600519)今日发布2024年业绩报告，净利润同比增长15%'
    }
    
    result = mapper.map_news_to_stocks(test_news['title'], test_news['content'])
    print(f"匹配结果: {result}")
