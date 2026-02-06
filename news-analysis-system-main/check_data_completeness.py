"""
检查新闻数据完整性
验证 news-analysis-system-main 存储的数据是否符合 smart_stock_advisor 股票预测的要求
"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import pymysql
from src.config.config import DB_CONFIG

def check_data_completeness():
    """检查数据完整性"""
    print("=" * 80)
    print("检查新闻数据完整性")
    print("=" * 80)
    
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG.get('charset', 'utf8mb4')
        )
        cursor = conn.cursor()
        
        # 1. 检查新闻总数
        cursor.execute("SELECT COUNT(*) FROM news_articles")
        total_count = cursor.fetchone()[0]
        print(f"\n1. 新闻总数: {total_count} 条")
        
        # 2. 检查基础字段完整性
        print("\n2. 基础字段完整性检查:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN title IS NOT NULL AND title != '' THEN 1 ELSE 0 END) as has_title,
                SUM(CASE WHEN content IS NOT NULL AND content != '' THEN 1 ELSE 0 END) as has_content,
                SUM(CASE WHEN publish_time IS NOT NULL THEN 1 ELSE 0 END) as has_publish_time,
                SUM(CASE WHEN source IS NOT NULL AND source != '' THEN 1 ELSE 0 END) as has_source,
                SUM(CASE WHEN content_hash IS NOT NULL THEN 1 ELSE 0 END) as has_content_hash
            FROM news_articles
        """)
        result = cursor.fetchone()
        print(f"   标题: {result[1]}/{result[0]} ({result[1]/result[0]*100:.1f}%)")
        print(f"   内容: {result[2]}/{result[0]} ({result[2]/result[0]*100:.1f}%)")
        print(f"   发布时间: {result[3]}/{result[0]} ({result[3]/result[0]*100:.1f}%)")
        print(f"   来源: {result[4]}/{result[0]} ({result[4]/result[0]*100:.1f}%)")
        print(f"   内容哈希: {result[5]}/{result[0]} ({result[5]/result[0]*100:.1f}%)")
        
        # 3. 检查股票关联字段
        print("\n3. 股票关联字段检查:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN symbol IS NOT NULL THEN 1 ELSE 0 END) as has_symbol,
                SUM(CASE WHEN sector IS NOT NULL THEN 1 ELSE 0 END) as has_sector,
                SUM(CASE WHEN industry IS NOT NULL THEN 1 ELSE 0 END) as has_industry
            FROM news_articles
        """)
        result = cursor.fetchone()
        print(f"   股票代码: {result[1]}/{result[0]} ({result[1]/result[0]*100:.1f}%)")
        print(f"   板块: {result[2]}/{result[0]} ({result[2]/result[0]*100:.1f}%)")
        print(f"   行业: {result[3]}/{result[0]} ({result[3]/result[0]*100:.1f}%)")
        
        # 4. 检查情感分析字段（股票预测需要）
        print("\n4. 情感分析字段检查（股票预测需要）:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN sentiment IS NOT NULL THEN 1 ELSE 0 END) as has_sentiment,
                SUM(CASE WHEN sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as has_sentiment_score,
                SUM(CASE WHEN sentiment_confidence IS NOT NULL THEN 1 ELSE 0 END) as has_sentiment_confidence,
                SUM(CASE WHEN is_positive IS NOT NULL THEN 1 ELSE 0 END) as has_is_positive,
                SUM(CASE WHEN is_negative IS NOT NULL THEN 1 ELSE 0 END) as has_is_negative,
                SUM(CASE WHEN is_policy IS NOT NULL THEN 1 ELSE 0 END) as has_is_policy,
                SUM(CASE WHEN keywords IS NOT NULL THEN 1 ELSE 0 END) as has_keywords,
                SUM(CASE WHEN relevance_type IS NOT NULL THEN 1 ELSE 0 END) as has_relevance_type,
                SUM(CASE WHEN relevance_score IS NOT NULL THEN 1 ELSE 0 END) as has_relevance_score
            FROM news_articles
        """)
        result = cursor.fetchone()
        total = result[0]
        print(f"   情感类型: {result[1]}/{total} ({result[1]/total*100:.1f}%)")
        print(f"   情感得分: {result[2]}/{total} ({result[2]/total*100:.1f}%)")
        print(f"   情感置信度: {result[3]}/{total} ({result[3]/total*100:.1f}%)")
        print(f"   是否利好: {result[4]}/{total} ({result[4]/total*100:.1f}%)")
        print(f"   是否利空: {result[5]}/{total} ({result[5]/total*100:.1f}%)")
        print(f"   是否政策: {result[6]}/{total} ({result[6]/total*100:.1f}%)")
        print(f"   关键词: {result[7]}/{total} ({result[7]/total*100:.1f}%)")
        print(f"   相关性类型: {result[8]}/{total} ({result[8]/total*100:.1f}%)")
        print(f"   相关性得分: {result[9]}/{total} ({result[9]/total*100:.1f}%)")
        
        # 5. 检查 LLM 分析字段
        print("\n5. LLM 分析字段检查:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN llm_category IS NOT NULL THEN 1 ELSE 0 END) as has_llm_category,
                SUM(CASE WHEN llm_sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as has_llm_sentiment_score,
                SUM(CASE WHEN llm_keywords IS NOT NULL THEN 1 ELSE 0 END) as has_llm_keywords,
                SUM(CASE WHEN llm_summary IS NOT NULL THEN 1 ELSE 0 END) as has_llm_summary,
                SUM(CASE WHEN llm_analyzed_at IS NOT NULL THEN 1 ELSE 0 END) as has_llm_analyzed_at
            FROM news_articles
        """)
        result = cursor.fetchone()
        total = result[0]
        print(f"   LLM分类: {result[1]}/{total} ({result[1]/total*100:.1f}%)")
        print(f"   LLM情感得分: {result[2]}/{total} ({result[2]/total*100:.1f}%)")
        print(f"   LLM关键词: {result[3]}/{total} ({result[3]/total*100:.1f}%)")
        print(f"   LLM总结: {result[4]}/{total} ({result[4]/total*100:.1f}%)")
        print(f"   LLM分析时间: {result[5]}/{total} ({result[5]/total*100:.1f}%)")
        
        # 6. 检查数据质量（有股票关联的新闻是否有情感分析）
        print("\n6. 数据质量检查（有股票关联的新闻）:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as has_sentiment_score,
                SUM(CASE WHEN llm_sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as has_llm_sentiment_score
            FROM news_articles
            WHERE symbol IS NOT NULL
        """)
        result = cursor.fetchone()
        if result[0] > 0:
            print(f"   有股票关联的新闻: {result[0]} 条")
            print(f"   有基础情感分析: {result[1]}/{result[0]} ({result[1]/result[0]*100:.1f}%)")
            print(f"   有LLM情感分析: {result[2]}/{result[0]} ({result[2]/result[0]*100:.1f}%)")
        else:
            print("   暂无有股票关联的新闻")
        
        # 7. 显示最近5条新闻的字段情况
        print("\n7. 最近5条新闻的字段情况:")
        cursor.execute("""
            SELECT 
                id, title, symbol, 
                sentiment, sentiment_score, is_positive, is_negative,
                llm_category, llm_sentiment_score, llm_analyzed_at
            FROM news_articles
            ORDER BY id DESC
            LIMIT 5
        """)
        news_list = cursor.fetchall()
        for news in news_list:
            print(f"\n   新闻ID: {news[0]}")
            print(f"   标题: {news[1][:50]}...")
            print(f"   股票: {news[2] or '无'}")
            print(f"   基础情感: {news[3] or 'NULL'}, 得分: {news[4] or 'NULL'}, 利好: {news[5] or 'NULL'}, 利空: {news[6] or 'NULL'}")
            print(f"   LLM分类: {news[7] or 'NULL'}, LLM得分: {news[8] or 'NULL'}, LLM分析时间: {news[9] or 'NULL'}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("[完成] 数据完整性检查")
        print("=" * 80)
        
        # 8. 总结和建议
        print("\n总结和建议:")
        print("- 如果情感分析字段为0%，说明需要运行新闻获取功能（已添加情感分析）")
        print("- 如果LLM分析字段为0%，说明需要运行LLM分析功能")
        print("- 股票预测需要 sentiment_score, is_positive, is_negative 等字段")
        print("- LLM分析结果会自动映射到这些字段（如果LLM分析完成）")
        
    except Exception as e:
        print(f"\n[失败] 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_data_completeness()
