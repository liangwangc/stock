import json
import pymysql
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from datetime import datetime
from ..config.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

def get_last_processed_hash():
    """获取最后处理的 content_hash（从 news_articles 表中 llm_analyzed_at 不为空的记录）"""
    sql = """
    SELECT content_hash 
    FROM news_articles 
    WHERE llm_analyzed_at IS NOT NULL 
    ORDER BY llm_analyzed_at DESC 
    LIMIT 1
    """
    df = pd.read_sql(sql, engine)
    return df['content_hash'].iloc[0] if not df.empty else None

def load_news_after_last_processed(start_date=None, end_date=None):
    """
    从最后处理的新闻之后开始加载（适配 news_articles 表）
    
    Args:
        start_date: 开始日期（可选），格式：'2026-01-23' 或 datetime对象，只分析此日期之后的新闻
        end_date: 结束日期（可选），格式：'2026-01-23' 或 datetime对象，只分析此日期之前的新闻
    
    Returns:
        DataFrame: 包含未分析新闻的DataFrame
    """
    last_hash = get_last_processed_hash()
    
    # 构建时间范围过滤条件
    time_conditions = []
    time_params = []
    
    if start_date:
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        time_conditions.append("publish_time >= %s")
        time_params.append(start_date)
    
    if end_date:
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        time_conditions.append("publish_time <= %s")
        time_params.append(end_date)
    
    time_filter = " AND " + " AND ".join(time_conditions) if time_conditions else ""
    
    if last_hash is not None:
        # 获取最后处理的新闻ID
        sql_id = "SELECT id FROM news_articles WHERE content_hash = %s"
        df_id = pd.read_sql(sql_id, engine, params=(last_hash,))
        last_id = df_id['id'].iloc[0] if not df_id.empty else None
        
        if last_id is not None:
            sql = f"""
                SELECT id, publish_time, content, content_hash, title 
                FROM news_articles 
                WHERE id > %s AND llm_analyzed_at IS NULL{time_filter}
                ORDER BY id
            """
            params = (last_id,) + tuple(time_params)
        else:
            sql = f"""
                SELECT id, publish_time, content, content_hash, title 
                FROM news_articles 
                WHERE llm_analyzed_at IS NULL{time_filter}
                ORDER BY id
            """
            params = tuple(time_params)
    else:
        # 如果没有已处理的记录，加载所有未分析的新闻
        sql = f"""
            SELECT id, publish_time, content, content_hash, title 
            FROM news_articles 
            WHERE llm_analyzed_at IS NULL{time_filter}
            ORDER BY id
        """
        params = tuple(time_params)
    
    df = pd.read_sql(sql, engine, params=params)
    
    # 格式化内容（使用 publish_time 而不是 publish_date）
    def format_content(row):
        date_str = str(row['publish_time']) if pd.notna(row['publish_time']) else ''
        return f"id:{row['id']};date:{date_str};{row['content']}"
    
    df['formatted_content'] = df.apply(format_content, axis=1)
    return df[['id', 'content_hash', 'formatted_content']]


def import_results(results, news_ids_and_hashes):
    """
    将 LLM 分析结果更新到 news_articles 表的 LLM 字段中
    
    Args:
        results: LLM 分析结果列表
        news_ids_and_hashes: 新闻ID和content_hash的对应关系列表 [(id, hash), ...]
    """
    try:
        # 解析 LLM 分析结果
        analysis_data = []
        parse_errors = []
        for idx, item in enumerate(results):
            try:
                # 检查结果格式
                if not item:
                    parse_errors.append(f"结果 {idx}: 空结果")
                    continue
                
                # 转换为列表并获取第一个元素
                item_list = list(item)
                if not item_list:
                    parse_errors.append(f"结果 {idx}: 集合为空")
                    continue
                
                result_str = item_list[0]
                if not isinstance(result_str, str):
                    parse_errors.append(f"结果 {idx}: 不是字符串类型，类型为 {type(result_str)}")
                    continue
                
                # 尝试解析JSON
                try:
                    result_json = json.loads(result_str)
                    analysis_data.append(result_json)
                except json.JSONDecodeError as json_err:
                    parse_errors.append(f"结果 {idx}: JSON解析失败 - {str(json_err)[:100]}")
                    print(f"解析分析结果失败（索引 {idx}）: {str(json_err)[:200]}", flush=True)
                    print(f"问题内容（前500字符）: {result_str[:500]}", flush=True)
                    continue
            except Exception as e:
                parse_errors.append(f"结果 {idx}: 处理异常 - {str(e)}")
                print(f"处理分析结果失败（索引 {idx}）: {e}", flush=True)
                import traceback
                traceback.print_exc()
                continue
        
        if not analysis_data:
            print(f"没有有效的分析结果（共 {len(results)} 条结果，{len(parse_errors)} 条解析失败）", flush=True)
            if parse_errors:
                print("解析错误详情（前10条）:", flush=True)
                for err in parse_errors[:10]:
                    print(f"  - {err}", flush=True)
            return
        
        print(f"成功解析 {len(analysis_data)}/{len(results)} 条分析结果", flush=True)
        
        # 确保 news_ids_and_hashes 的长度与 analysis_data 匹配
        if len(news_ids_and_hashes) != len(analysis_data):
            print(f"警告: 新闻数量({len(news_ids_and_hashes)})与分析结果数量({len(analysis_data)})不匹配")
            min_len = min(len(news_ids_and_hashes), len(analysis_data))
            news_ids_and_hashes = news_ids_and_hashes[:min_len]
            analysis_data = analysis_data[:min_len]
        
        # 更新数据库
        analyzed_at = datetime.now()
        
        with engine.begin() as connection:
            for (news_id, content_hash), analysis in zip(news_ids_and_hashes, analysis_data):
                try:
                    # 映射字段
                    # 注意：如果content_hash为NULL，WHERE条件需要特殊处理
                    if content_hash:
                        update_sql = text("""
                            UPDATE news_articles 
                            SET 
                                llm_category = :category,
                                llm_subcategory = :subcategory,
                                llm_keywords = :keywords,
                                llm_sentiment_score = :sentiment,
                                llm_summary = :summary,
                                llm_impact_markets = :impact_markets,
                                llm_is_market_relevant = :is_market_relevant,
                                llm_analyzed_at = :analyzed_at
                            WHERE id = :news_id AND content_hash = :content_hash
                        """)
                    else:
                        # 如果content_hash为NULL，只使用id更新
                        update_sql = text("""
                            UPDATE news_articles 
                            SET 
                                llm_category = :category,
                                llm_subcategory = :subcategory,
                                llm_keywords = :keywords,
                                llm_sentiment_score = :sentiment,
                                llm_summary = :summary,
                                llm_impact_markets = :impact_markets,
                                llm_is_market_relevant = :is_market_relevant,
                                llm_analyzed_at = :analyzed_at
                            WHERE id = :news_id AND (content_hash IS NULL OR content_hash = '')
                        """)
                    
                    # 处理 is_market_relevant（可能是布尔值或整数）
                    is_market_relevant = analysis.get('is_market_relevant', True)
                    if isinstance(is_market_relevant, bool):
                        is_market_relevant = 1 if is_market_relevant else 0
                    elif isinstance(is_market_relevant, str):
                        is_market_relevant = 1 if is_market_relevant.lower() == 'true' else 0
                    
                    # 将 LLM 分析结果映射到股票预测使用的字段
                    llm_sentiment_score = float(analysis.get('sentiment', 0.0)) if analysis.get('sentiment') is not None else None
                    
                    # 如果 LLM 有情感得分，更新 sentiment_score（优先使用 LLM 结果）
                    if llm_sentiment_score is not None:
                        # 根据 LLM 情感得分设置 is_positive 和 is_negative
                        llm_is_positive = 1 if llm_sentiment_score > 0.1 else 0
                        llm_is_negative = 1 if llm_sentiment_score < -0.1 else 0
                        llm_sentiment = 'positive' if llm_sentiment_score > 0.1 else ('negative' if llm_sentiment_score < -0.1 else 'neutral')
                    else:
                        llm_is_positive = None
                        llm_is_negative = None
                        llm_sentiment = None
                    
                    # 处理关键词（LLM 关键词可能是逗号分隔的字符串）
                    llm_keywords = analysis.get('keywords', '')
                    if llm_keywords:
                        if isinstance(llm_keywords, str):
                            # 如果是逗号分隔的字符串，转换为列表再转JSON
                            keywords_list = [k.strip() for k in llm_keywords.split(',') if k.strip()]
                            keywords_json = json.dumps(keywords_list, ensure_ascii=False) if keywords_list else None
                        else:
                            keywords_json = json.dumps(llm_keywords, ensure_ascii=False) if llm_keywords else None
                    else:
                        keywords_json = None
                    
                    params = {
                        # LLM 分析字段
                        'category': str(analysis.get('category', ''))[:50] if analysis.get('category') else None,
                        'subcategory': str(analysis.get('subcategory', ''))[:100] if analysis.get('subcategory') else None,
                        'keywords': keywords_json,  # LLM 关键词（JSON格式）
                        'sentiment': llm_sentiment_score,  # LLM 情感得分
                        'summary': str(analysis.get('summary', '')) if analysis.get('summary') else None,
                        'impact_markets': str(analysis.get('impact_markets', ''))[:200] if analysis.get('impact_markets') else None,
                        'is_market_relevant': is_market_relevant,
                        'analyzed_at': analyzed_at,
                        'news_id': news_id,
                        'content_hash': content_hash
                    }
                    
                    # 更新 LLM 字段
                    result = connection.execute(update_sql, params)
                    rows_updated = result.rowcount
                    
                    if rows_updated == 0:
                        print(f"警告: 新闻ID {news_id} 更新失败，WHERE条件不匹配（id={news_id}, content_hash={content_hash}）", flush=True)
                        # 尝试只使用id更新（如果content_hash不匹配）
                        if content_hash:
                            fallback_sql = text("""
                                UPDATE news_articles 
                                SET 
                                    llm_category = :category,
                                    llm_subcategory = :subcategory,
                                    llm_keywords = :keywords,
                                    llm_sentiment_score = :sentiment,
                                    llm_summary = :summary,
                                    llm_impact_markets = :impact_markets,
                                    llm_is_market_relevant = :is_market_relevant,
                                    llm_analyzed_at = :analyzed_at
                                WHERE id = :news_id
                            """)
                            fallback_result = connection.execute(fallback_sql, params)
                            if fallback_result.rowcount > 0:
                                print(f"使用备用方案（仅使用id）成功更新新闻ID {news_id}", flush=True)
                            else:
                                print(f"备用方案也失败：新闻ID {news_id} 不存在", flush=True)
                    
                    # 如果 LLM 有情感得分，同时更新股票预测使用的字段
                    if llm_sentiment_score is not None:
                        if content_hash:
                            update_prediction_fields_sql = text("""
                                UPDATE news_articles 
                                SET 
                                    sentiment = :sentiment,
                                    sentiment_score = :sentiment_score,
                                    is_positive = :is_positive,
                                    is_negative = :is_negative,
                                    keywords = COALESCE(:keywords, keywords)
                                WHERE id = :news_id AND content_hash = :content_hash
                            """)
                        else:
                            update_prediction_fields_sql = text("""
                                UPDATE news_articles 
                                SET 
                                    sentiment = :sentiment,
                                    sentiment_score = :sentiment_score,
                                    is_positive = :is_positive,
                                    is_negative = :is_negative,
                                    keywords = COALESCE(:keywords, keywords)
                                WHERE id = :news_id AND (content_hash IS NULL OR content_hash = '')
                            """)
                        
                        prediction_params = {
                            'sentiment': llm_sentiment,
                            'sentiment_score': llm_sentiment_score,
                            'is_positive': llm_is_positive,
                            'is_negative': llm_is_negative,
                            'keywords': keywords_json,
                            'news_id': news_id,
                            'content_hash': content_hash
                        }
                        
                        connection.execute(update_prediction_fields_sql, prediction_params)
                    
                except Exception as e:
                    print(f"更新新闻 {news_id} 的分析结果失败: {e}")
                    continue
        
        print(f"成功更新 {len(analysis_data)} 条新闻的 LLM 分析结果")

    except Exception as e:
        print(f"导入数据时出错: {e}", flush=True)
        import traceback
        traceback.print_exc()
        # 注意：engine.begin() 自动 rollback 出错事务，这里不用手动 rollback
        raise
