"""
测试存储逻辑（不依赖模型）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db_handle import import_results
import json

def test_storage_logic():
    """测试存储逻辑"""
    
    print("=" * 80)
    print("测试LLM分析结果存储逻辑")
    print("=" * 80)
    
    # 模拟LLM分析结果（正确的JSON格式）
    test_results = [
        {json.dumps({
            "news_index": "1",
            "date": "2026-01-23",
            "category": "宏观经济类",
            "subcategory": "央行政策",
            "is_market_relevant": True,
            "keywords": "降息,货币政策,流动性",
            "sentiment": 0.65,
            "impact_markets": "A股,债券市场",
            "summary": "央行宣布降息0.25个百分点，释放流动性"
        }, ensure_ascii=False)}
    ]
    
    # 模拟新闻ID和hash（需要从数据库获取真实的）
    print("\n1. 获取一条未分析的新闻...")
    from src.database.db_handle import load_news_after_last_processed
    df_unprocessed = load_news_after_last_processed()
    
    if df_unprocessed.empty:
        print("   [警告] 没有未分析的新闻")
        return
    
    print(f"   找到 {len(df_unprocessed)} 条未分析的新闻")
    
    # 只测试第一条
    test_news_id = df_unprocessed.iloc[0]['id']
    test_content_hash = df_unprocessed.iloc[0]['content_hash']
    test_ids_and_hashes = [(test_news_id, test_content_hash)]
    
    print(f"   测试新闻ID: {test_news_id}")
    if test_content_hash:
        print(f"   测试Hash: {test_content_hash[:20]}...")
    else:
        print(f"   测试Hash: None（警告：content_hash为空）")
    
    # 2. 测试存储
    print("\n2. 测试存储到数据库...")
    try:
        import_results(test_results, test_ids_and_hashes)
        print("   [成功] 存储完成")
        
        # 3. 验证存储
        print("\n3. 验证存储结果...")
        from src.database.db_handle import engine
        import pandas as pd
        
        # 检查更新是否成功（检查受影响的行数）
        sql_check = "SELECT id, llm_analyzed_at, llm_category, llm_sentiment_score, content_hash FROM news_articles WHERE id = %s"
        df_check = pd.read_sql(sql_check, engine, params=(test_news_id,))
        
        if not df_check.empty:
            row = df_check.iloc[0]
            print(f"   数据库中的content_hash: {row['content_hash']}")
            print(f"   测试使用的content_hash: {test_content_hash}")
            
            if row['llm_analyzed_at'] is not None:
                print(f"   [成功] 新闻ID {test_news_id} 已存储分析结果")
                print(f"   分析时间: {row['llm_analyzed_at']}")
                print(f"   分类: {row['llm_category']}")
                print(f"   情感得分: {row['llm_sentiment_score']}")
            else:
                print(f"   [失败] 新闻ID {test_news_id} 的分析时间仍为NULL")
                print(f"   可能原因：WHERE条件不匹配（id={test_news_id}, content_hash={test_content_hash}）")
        else:
            print(f"   [失败] 未找到新闻ID {test_news_id}")
            
    except Exception as e:
        print(f"   [错误] 存储失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == '__main__':
    try:
        test_storage_logic()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
