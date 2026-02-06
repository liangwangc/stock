"""
验证新闻数据和股票关联关系是否正确写入数据库
"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import pymysql
from src.config.config import DB_CONFIG

def verify_data():
    """验证数据库中的数据"""
    print("=" * 80)
    print("验证新闻数据和股票关联关系")
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
        news_count = cursor.fetchone()[0]
        print(f"\n1. 新闻总数: {news_count} 条")
        
        # 2. 检查有股票关联的新闻数量
        cursor.execute("SELECT COUNT(*) FROM news_articles WHERE symbol IS NOT NULL")
        matched_news_count = cursor.fetchone()[0]
        print(f"2. 有股票关联的新闻: {matched_news_count} 条")
        
        # 3. 显示最近5条新闻
        print("\n3. 最近5条新闻:")
        cursor.execute("""
            SELECT id, title, symbol, sector, industry, source, created_at
            FROM news_articles
            ORDER BY id DESC
            LIMIT 5
        """)
        news_list = cursor.fetchall()
        for news in news_list:
            print(f"   ID: {news[0]}")
            print(f"   标题: {news[1][:50]}...")
            print(f"   股票: {news[2] or '无'}, 板块: {news[3] or '无'}, 行业: {news[4] or '无'}")
            print(f"   来源: {news[5]}, 时间: {news[6]}")
            print()
        
        # 4. 检查股票关联关系总数（如果表存在）
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'news_stock_relation'
        """)
        relation_table_exists = cursor.fetchone()[0] > 0
        
        if relation_table_exists:
            cursor.execute("SELECT COUNT(*) FROM news_stock_relation")
            relation_count = cursor.fetchone()[0]
            print(f"4. 股票关联关系总数: {relation_count} 条")
            
            # 5. 显示最近5条关联关系
            print("\n5. 最近5条股票关联关系:")
            cursor.execute("""
                SELECT nsr.id, nsr.news_id, n.title, nsr.symbol, nsr.relevance_score, nsr.relation_type
                FROM news_stock_relation nsr
                JOIN news_articles n ON nsr.news_id = n.id
                ORDER BY nsr.id DESC
                LIMIT 5
            """)
            relations = cursor.fetchall()
            for rel in relations:
                print(f"   关联ID: {rel[0]}, 新闻ID: {rel[1]}")
                print(f"   标题: {rel[2][:50]}...")
                print(f"   股票: {rel[3]}, 相关性: {rel[4]}, 类型: {rel[5]}")
                print()
            
            # 6. 统计各股票的关联新闻数量
            print("6. 股票关联新闻数量统计（前10名）:")
            cursor.execute("""
                SELECT symbol, COUNT(*) as count
                FROM news_stock_relation
                GROUP BY symbol
                ORDER BY count DESC
                LIMIT 10
            """)
        else:
            print("4. news_stock_relation 表不存在，跳过关联关系统计")
            print("   股票关联信息保存在 news_articles 表的 symbol 字段中")
            
            # 6. 统计各股票的关联新闻数量（从 news_articles 表）
            print("\n6. 股票关联新闻数量统计（前10名，从 news_articles 表）:")
            cursor.execute("""
                SELECT symbol, COUNT(*) as count
                FROM news_articles
                WHERE symbol IS NOT NULL
                GROUP BY symbol
                ORDER BY count DESC
                LIMIT 10
            """)
        stock_stats = cursor.fetchall()
        for stat in stock_stats:
            print(f"   股票 {stat[0]}: {stat[1]} 条新闻")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("[成功] 数据验证完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[失败] 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verify_data()
