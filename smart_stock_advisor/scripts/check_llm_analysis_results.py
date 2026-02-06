"""
检查LLM分析结果是否已存储到数据库
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_connection import DatabaseConnection

def check_llm_analysis_results():
    """检查LLM分析结果"""
    
    print("=" * 80)
    print("LLM分析结果检查")
    print("=" * 80)
    
    # 1. 统计总体情况
    print("\n1. 总体统计...")
    sql_total = """
        SELECT 
            COUNT(*) as total_news,
            SUM(CASE WHEN llm_analyzed_at IS NOT NULL THEN 1 ELSE 0 END) as analyzed_count,
            SUM(CASE WHEN llm_analyzed_at IS NULL THEN 1 ELSE 0 END) as unanalyzed_count
        FROM news_articles
    """
    result_total = DatabaseConnection.execute_query(sql_total)
    if result_total:
        total = result_total[0]['total_news']
        analyzed = result_total[0]['analyzed_count']
        unanalyzed = result_total[0]['unanalyzed_count']
        print(f"   总新闻数: {total:,} 条")
        print(f"   已分析: {analyzed:,} 条 ({analyzed/total*100:.1f}%)" if total > 0 else "   已分析: 0 条")
        print(f"   未分析: {unanalyzed:,} 条 ({unanalyzed/total*100:.1f}%)" if total > 0 else "   未分析: 0 条")
    
    # 2. 检查最近的分析结果
    print("\n2. 最近的分析结果（前10条）...")
    sql_recent = """
        SELECT 
            id, title, publish_time,
            llm_category, llm_subcategory,
            llm_sentiment_score, llm_summary,
            llm_analyzed_at
        FROM news_articles
        WHERE llm_analyzed_at IS NOT NULL
        ORDER BY llm_analyzed_at DESC
        LIMIT 10
    """
    result_recent = DatabaseConnection.execute_query(sql_recent)
    if result_recent:
        print(f"   找到 {len(result_recent)} 条已分析的新闻")
        for i, news in enumerate(result_recent, 1):
            print(f"\n   [{i}] ID: {news['id']}")
            print(f"       标题: {news['title'][:50] if news['title'] else 'N/A'}...")
            print(f"       发布时间: {news['publish_time']}")
            print(f"       分析时间: {news['llm_analyzed_at']}")
            print(f"       分类: {news['llm_category']} / {news['llm_subcategory']}")
            print(f"       情感得分: {news['llm_sentiment_score']}")
            if news['llm_summary']:
                summary = news['llm_summary'][:100] if len(news['llm_summary']) > 100 else news['llm_summary']
                print(f"       总结: {summary}...")
    else:
        print("   [警告] 没有找到已分析的新闻！")
    
    # 3. 检查LLM字段的完整性
    print("\n3. LLM字段完整性检查...")
    sql_fields = """
        SELECT 
            COUNT(*) as total_analyzed,
            SUM(CASE WHEN llm_category IS NOT NULL THEN 1 ELSE 0 END) as has_category,
            SUM(CASE WHEN llm_subcategory IS NOT NULL THEN 1 ELSE 0 END) as has_subcategory,
            SUM(CASE WHEN llm_keywords IS NOT NULL THEN 1 ELSE 0 END) as has_keywords,
            SUM(CASE WHEN llm_sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as has_sentiment,
            SUM(CASE WHEN llm_summary IS NOT NULL THEN 1 ELSE 0 END) as has_summary,
            SUM(CASE WHEN llm_impact_markets IS NOT NULL THEN 1 ELSE 0 END) as has_impact_markets
        FROM news_articles
        WHERE llm_analyzed_at IS NOT NULL
    """
    result_fields = DatabaseConnection.execute_query(sql_fields)
    if result_fields and result_fields[0]['total_analyzed'] > 0:
        fields = result_fields[0]
        total = fields['total_analyzed']
        print(f"   已分析的新闻数: {total}")
        print(f"   有分类: {fields['has_category']}/{total} ({fields['has_category']/total*100:.1f}%)")
        print(f"   有子分类: {fields['has_subcategory']}/{total} ({fields['has_subcategory']/total*100:.1f}%)")
        print(f"   有关键词: {fields['has_keywords']}/{total} ({fields['has_keywords']/total*100:.1f}%)")
        print(f"   有情感得分: {fields['has_sentiment']}/{total} ({fields['has_sentiment']/total*100:.1f}%)")
        print(f"   有总结: {fields['has_summary']}/{total} ({fields['has_summary']/total*100:.1f}%)")
        print(f"   有影响市场: {fields['has_impact_markets']}/{total} ({fields['has_impact_markets']/total*100:.1f}%)")
    else:
        print("   [警告] 没有已分析的新闻，无法检查字段完整性")
    
    # 4. 检查最近的备份文件
    print("\n4. 检查备份文件...")
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'news-analysis-system-main', 'data', 'backup_results')
    if os.path.exists(backup_dir):
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
        if backup_files:
            backup_files.sort(reverse=True)
            print(f"   找到 {len(backup_files)} 个备份文件")
            print(f"   最新的备份文件: {backup_files[0]}")
            print(f"   文件大小: {os.path.getsize(os.path.join(backup_dir, backup_files[0])) / 1024:.2f} KB")
        else:
            print("   [警告] 没有找到备份文件")
    else:
        print(f"   [警告] 备份目录不存在: {backup_dir}")
    
    # 5. 检查分析时间分布
    print("\n5. 分析时间分布...")
    sql_time_dist = """
        SELECT 
            DATE(llm_analyzed_at) as analyze_date,
            COUNT(*) as count
        FROM news_articles
        WHERE llm_analyzed_at IS NOT NULL
        GROUP BY DATE(llm_analyzed_at)
        ORDER BY analyze_date DESC
        LIMIT 10
    """
    result_time_dist = DatabaseConnection.execute_query(sql_time_dist)
    if result_time_dist:
        print("   按日期统计:")
        for row in result_time_dist:
            print(f"      {row['analyze_date']}: {row['count']} 条")
    else:
        print("   [警告] 没有找到分析时间记录")
    
    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)

if __name__ == '__main__':
    try:
        check_llm_analysis_results()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
