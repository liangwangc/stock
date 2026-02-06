import akshare as ak
import pandas as pd
import hashlib
import json
from datetime import datetime
from sqlalchemy import create_engine, text
import time
from ..config.config import DATABASE_URL
from .stock_mapper import StockMapper
from .simple_sentiment_analyzer import SimpleSentimentAnalyzer

# 初始化数据库引擎
engine = create_engine(DATABASE_URL)

# 初始化股票匹配器
stock_mapper = StockMapper()

# 初始化情感分析器
sentiment_analyzer = SimpleSentimentAnalyzer()

def generate_hash(row):
    """根据新闻标题和内容生成唯一哈希"""
    combined = row['title'] + row['content']
    return hashlib.md5(combined.encode('utf-8')).hexdigest()

def filter_new_hashes(df):
    """过滤掉已经存在的 hash"""
    existing_hashes = set()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT content_hash FROM news_articles WHERE content_hash IN :hashes"),
                              {"hashes": tuple(df['content_hash'].unique())})
        existing_hashes = {row[0] for row in result.fetchall()}

    # 筛选出未存在的 hash
    return df[~df['content_hash'].isin(existing_hashes)]

def fetch_and_store_news():
    print(f"[{datetime.now()}] 开始抓取财联社新闻...")
    try:
        # 优化：多次调用API，获取更多新闻
        all_news_list = []
        max_calls = 3  # 最多调用3次，获取更多新闻
        min_news_per_call = 15  # 每次至少获取15条新闻才继续
        
        for i in range(max_calls):
            try:
                news_df = ak.stock_info_global_cls(symbol="全部")
                if news_df is not None and len(news_df) > 0:
                    all_news_list.append(news_df)
                    print(f"第 {i+1} 次调用获取 {len(news_df)} 条新闻")
                    
                    # 如果获取的新闻少于阈值，说明没有更多新闻了
                    if len(news_df) < min_news_per_call:
                        print(f"第 {i+1} 次调用获取的新闻少于 {min_news_per_call} 条，停止继续调用")
                        break
                    
                    # 短暂延迟，避免请求过快（最后一次调用不需要延迟）
                    if i < max_calls - 1:
                        time.sleep(1)
                else:
                    print(f"第 {i+1} 次调用未获取到新闻，停止继续调用")
                    break
            except Exception as e:
                print(f"第 {i+1} 次调用失败: {str(e)}")
                # 如果第一次调用就失败，直接退出
                if i == 0:
                    raise
                break
        
        # 合并所有新闻
        if all_news_list:
            news_df = pd.concat(all_news_list, ignore_index=True)
            # 去重（根据标题和内容）
            news_df = news_df.drop_duplicates(subset=['标题', '内容'], keep='first')
            print(f"合并后共 {len(news_df)} 条新闻（去重后）")
        else:
            print("未获取到任何新闻")
            return
        
        # 重命名列
        news_df = news_df.rename(columns={
            '标题': 'title',
            '内容': 'content',
            '发布日期': 'publish_date',
            '发布时间': 'publish_time'
        })
        
        print(f"成功获取 {len(news_df)} 条新闻（去重后）")

        # 添加 hash 列
        news_df['content_hash'] = news_df.apply(generate_hash, axis=1)

        # 添加入库时间和抓取时间（news_articles 表需要 fetch_time）
        news_df['fetch_time'] = datetime.now()
        news_df['created_at'] = datetime.now()

        # 过滤掉已存在的 hash
        new_news_df = filter_new_hashes(news_df).copy()  # 使用 .copy() 避免 SettingWithCopyWarning
        if len(new_news_df) == 0:
            print("没有新新闻需要写入数据库")
            return

        # 添加默认字段
        new_news_df.loc[:, 'source'] = '财联社'
        new_news_df.loc[:, 'source_url'] = None
        new_news_df.loc[:, 'news_type'] = 'market'  # news_articles 表需要 news_type 字段
        
        # 初始化股票关联字段
        new_news_df.loc[:, 'symbol'] = None
        new_news_df.loc[:, 'sector'] = None
        new_news_df.loc[:, 'industry'] = None
        new_news_df.loc[:, 'concept'] = None
        
        # 处理发布时间字段（合并 publish_date 和 publish_time）
        # news_articles 表使用 publish_time (DATETIME)，而不是分开的 date 和 time
        def combine_datetime(row):
            """合并日期和时间"""
            try:
                if pd.notna(row.get('publish_date')) and pd.notna(row.get('publish_time')):
                    if isinstance(row['publish_date'], str) and isinstance(row['publish_time'], str):
                        return pd.to_datetime(f"{row['publish_date']} {row['publish_time']}")
                    elif isinstance(row['publish_date'], pd.Timestamp):
                        date_str = row['publish_date'].strftime('%Y-%m-%d')
                        time_str = str(row['publish_time'])
                        return pd.to_datetime(f"{date_str} {time_str}")
                elif pd.notna(row.get('publish_date')):
                    return pd.to_datetime(row['publish_date'])
                return None
            except:
                return None
        
        new_news_df.loc[:, 'publish_time'] = new_news_df.apply(combine_datetime, axis=1)
        
        # 对每条新闻进行股票匹配
        print(f"开始股票匹配，共 {len(new_news_df)} 条新闻...")
        matched_count = 0
        stock_relations_map = {}  # 存储每条新闻的所有股票关联关系 {content_hash: [stock_info_dicts]}
        
        for idx, row in new_news_df.iterrows():
            try:
                stock_info = stock_mapper.map_news_to_stocks(
                    title=str(row.get('title', '')),
                    content=str(row.get('content', ''))
                )
                
                # 添加股票信息到 DataFrame（主要股票）
                if stock_info.get('primary_symbol'):
                    new_news_df.at[idx, 'symbol'] = stock_info.get('primary_symbol')
                    new_news_df.at[idx, 'sector'] = stock_info.get('sector')
                    new_news_df.at[idx, 'industry'] = stock_info.get('industry')
                    matched_count += 1
                    
                    # 保存所有关联的股票信息（用于多对多关系）
                    content_hash = row.get('content_hash')
                    if content_hash:
                        relations = []
                        for symbol in stock_info.get('symbols', []):
                            # 获取每个股票的行业信息
                            symbol_info = stock_mapper.get_stock_industry_sector(symbol)
                            relations.append({
                                'symbol': symbol,
                                'relevance_score': stock_info.get('relevance_score', 1.0),
                                'relation_type': 'direct' if symbol == stock_info.get('primary_symbol') else 'related'
                            })
                        stock_relations_map[content_hash] = relations
            except Exception as e:
                print(f"股票匹配失败（索引 {idx}）: {str(e)}")
        
        print(f"股票匹配完成: {matched_count}/{len(new_news_df)} 条新闻匹配到股票")
        
        # 进行情感分析
        print("开始情感分析...")
        sentiment_results = []
        for idx, row in new_news_df.iterrows():
            try:
                title = str(row.get('title', ''))
                content = str(row.get('content', ''))
                sentiment_result = sentiment_analyzer.analyze(title, content)
                sentiment_results.append(sentiment_result)
            except Exception as e:
                print(f"情感分析失败（索引 {idx}）: {str(e)}")
                # 使用默认值
                sentiment_results.append({
                    'sentiment': 'neutral',
                    'sentiment_score': 0.0,
                    'sentiment_confidence': 0.0,
                    'keywords': [],
                    'is_positive': 0,
                    'is_negative': 0,
                    'is_policy': 0,
                    'relevance_type': 'market',
                    'relevance_score': 0.5
                })
        
        # 将情感分析结果添加到 DataFrame
        for idx, result in enumerate(sentiment_results):
            new_news_df.at[new_news_df.index[idx], 'sentiment'] = result['sentiment']
            new_news_df.at[new_news_df.index[idx], 'sentiment_score'] = result['sentiment_score']
            new_news_df.at[new_news_df.index[idx], 'sentiment_confidence'] = result['sentiment_confidence']
            new_news_df.at[new_news_df.index[idx], 'is_positive'] = result['is_positive']
            new_news_df.at[new_news_df.index[idx], 'is_negative'] = result['is_negative']
            new_news_df.at[new_news_df.index[idx], 'is_policy'] = result['is_policy']
            new_news_df.at[new_news_df.index[idx], 'keywords'] = json.dumps(result['keywords'], ensure_ascii=False) if result['keywords'] else None
            new_news_df.at[new_news_df.index[idx], 'relevance_type'] = result['relevance_type']
            new_news_df.at[new_news_df.index[idx], 'relevance_score'] = result['relevance_score']
        
        # 更新相关性类型（如果有股票关联）
        for idx, row in new_news_df.iterrows():
            if pd.notna(row.get('symbol')):
                new_news_df.at[idx, 'relevance_type'] = 'direct'
                new_news_df.at[idx, 'relevance_score'] = 1.0
            elif pd.notna(row.get('industry')) or pd.notna(row.get('sector')):
                new_news_df.at[idx, 'relevance_type'] = 'industry'
                new_news_df.at[idx, 'relevance_score'] = 0.7
        
        print(f"情感分析完成: {sum(1 for r in sentiment_results if r['sentiment'] != 'neutral')}/{len(sentiment_results)} 条新闻有明确情感倾向")

        # 处理空标题（避免唯一索引冲突）
        new_news_df.loc[:, 'title'] = new_news_df['title'].fillna('').astype(str)
        # 如果标题为空，使用内容前50字作为标题
        empty_title_mask = new_news_df['title'].str.strip() == ''
        new_news_df.loc[empty_title_mask, 'title'] = new_news_df.loc[empty_title_mask, 'content'].str[:50]
        
        # 准备写入 news_articles 表的字段（包含情感分析字段）
        columns_to_write = [
            'title', 'content', 'publish_time', 'fetch_time', 'source', 'source_url',
            'news_type', 'symbol', 'sector', 'industry', 'concept', 'content_hash', 'created_at',
            'sentiment', 'sentiment_score', 'sentiment_confidence',
            'is_positive', 'is_negative', 'is_policy', 'keywords',
            'relevance_type', 'relevance_score'
        ]
        
        # 确保所有需要的字段都存在
        for col in columns_to_write:
            if col not in new_news_df.columns:
                new_news_df.loc[:, col] = None
        
        # 使用逐条插入的方式，处理唯一索引冲突
        write_df = new_news_df[columns_to_write].copy()
        inserted_count = 0
        skipped_count = 0
        
        with engine.connect() as conn:
            for idx, row in write_df.iterrows():
                try:
                    # 使用 INSERT IGNORE 或检查 content_hash 是否已存在
                    check_sql = text("SELECT COUNT(*) FROM news_articles WHERE content_hash = :hash")
                    result = conn.execute(check_sql, {"hash": row['content_hash']})
                    if result.fetchone()[0] > 0:
                        skipped_count += 1
                        continue
                    
                    # 插入数据（包含情感分析字段）
                    insert_sql = text("""
                        INSERT INTO news_articles 
                        (title, content, publish_time, fetch_time, source, source_url,
                         news_type, symbol, sector, industry, concept, content_hash, created_at,
                         sentiment, sentiment_score, sentiment_confidence,
                         is_positive, is_negative, is_policy, keywords,
                         relevance_type, relevance_score)
                        VALUES (:title, :content, :publish_time, :fetch_time, :source, :source_url,
                                :news_type, :symbol, :sector, :industry, :concept, :content_hash, :created_at,
                                :sentiment, :sentiment_score, :sentiment_confidence,
                                :is_positive, :is_negative, :is_policy, :keywords,
                                :relevance_type, :relevance_score)
                    """)
                    
                    params = {
                        'title': str(row['title'])[:500] if pd.notna(row['title']) else '',  # 限制长度
                        'content': str(row['content']) if pd.notna(row['content']) else None,
                        'publish_time': row['publish_time'] if pd.notna(row['publish_time']) else None,
                        'fetch_time': row['fetch_time'],
                        'source': str(row['source']),
                        'source_url': str(row['source_url']) if pd.notna(row['source_url']) else None,
                        'news_type': str(row['news_type']),
                        'symbol': str(row['symbol']) if pd.notna(row['symbol']) else None,
                        'sector': str(row['sector']) if pd.notna(row['sector']) else None,
                        'industry': str(row['industry']) if pd.notna(row['industry']) else None,
                        'concept': str(row['concept']) if pd.notna(row['concept']) else None,
                        'content_hash': str(row['content_hash']),
                        'created_at': row['created_at'],
                        # 情感分析字段
                        'sentiment': str(row.get('sentiment', 'neutral')) if pd.notna(row.get('sentiment')) else 'neutral',
                        'sentiment_score': float(row.get('sentiment_score', 0.0)) if pd.notna(row.get('sentiment_score')) else 0.0,
                        'sentiment_confidence': float(row.get('sentiment_confidence', 0.0)) if pd.notna(row.get('sentiment_confidence')) else 0.0,
                        'is_positive': int(row.get('is_positive', 0)) if pd.notna(row.get('is_positive')) else 0,
                        'is_negative': int(row.get('is_negative', 0)) if pd.notna(row.get('is_negative')) else 0,
                        'is_policy': int(row.get('is_policy', 0)) if pd.notna(row.get('is_policy')) else 0,
                        'keywords': str(row.get('keywords')) if pd.notna(row.get('keywords')) else None,
                        'relevance_type': str(row.get('relevance_type', 'market')) if pd.notna(row.get('relevance_type')) else 'market',
                        'relevance_score': float(row.get('relevance_score', 0.5)) if pd.notna(row.get('relevance_score')) else 0.5
                    }
                    
                    conn.execute(insert_sql, params)
                    conn.commit()
                    inserted_count += 1
                except Exception as e:
                    # 如果是唯一索引冲突，跳过
                    if 'Duplicate entry' in str(e) or '1062' in str(e):
                        skipped_count += 1
                    else:
                        print(f"插入新闻失败（索引 {idx}）: {str(e)}")
                    conn.rollback()
        
        print(f"成功写入 {inserted_count} 条新新闻到数据库")
        if skipped_count > 0:
            print(f"跳过 {skipped_count} 条重复新闻")
        
        # 保存股票关联关系到 news_stock_relation 表（如果表存在）
        try:
            # 检查 news_stock_relation 表是否存在
            with engine.connect() as conn:
                check_table_sql = """
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'news_stock_relation'
                """
                table_exists = conn.execute(text(check_table_sql)).fetchone()[0] > 0
            
            if not table_exists:
                print("提示: news_stock_relation 表不存在，跳过股票关联关系保存")
                print("   股票关联信息已保存在 news_articles 表的 symbol 字段中")
            else:
                # 获取刚插入的新闻ID（通过content_hash，只获取本次插入的）
                sql = """
                    SELECT id, content_hash
                    FROM news_articles
                    WHERE content_hash IN :hashes
                    AND fetch_time >= :fetch_time_start
                    ORDER BY id DESC
                """
                hashes = tuple(new_news_df['content_hash'].tolist())
                fetch_time_start = new_news_df['fetch_time'].min()
                with engine.connect() as conn:
                    result = conn.execute(text(sql), {
                        "hashes": hashes,
                        "fetch_time_start": fetch_time_start
                    })
                    news_id_map = {row[1]: row[0] for row in result.fetchall()}
                
                # 构建关联关系数据（支持多对多关系）
                relations = []
                for idx, row in new_news_df.iterrows():
                    news_id = news_id_map.get(row['content_hash'])
                    content_hash = row['content_hash']
                    
                    if news_id and content_hash in stock_relations_map:
                        # 保存该新闻的所有关联股票
                        for rel_info in stock_relations_map[content_hash]:
                            relations.append({
                                'news_id': news_id,
                                'symbol': rel_info['symbol'],
                                'relevance_score': rel_info['relevance_score'],
                                'relation_type': rel_info['relation_type']
                            })
                
                # 保存关联关系
                if relations:
                    relations_df = pd.DataFrame(relations)
                    relations_df.to_sql(
                        name='news_stock_relation',
                        con=engine,
                        if_exists='append',
                        index=False
                    )
                    print(f"成功保存 {len(relations)} 条股票关联关系到 news_stock_relation 表")
        except Exception as e:
            print(f"保存股票关联关系失败: {str(e)}")
            print("提示: 股票关联信息已保存在 news_articles 表的 symbol 字段中")
            # 不影响主流程，继续执行

    except Exception as e:
        print(f"抓取或写入失败: {e}")


if __name__ == "__main__":

    while True:
        fetch_and_store_news()
        print("等待 1 分钟后再次抓取...\n")
        time.sleep(60)  # 每1分钟执行一次