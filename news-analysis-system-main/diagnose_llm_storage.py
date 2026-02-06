"""
诊断LLM分析结果存储问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db_handle import load_news_after_last_processed, import_results
from src.models.local_model import qwen3_model_by_local
import pandas as pd
import json

def diagnose_storage_issue():
    """诊断存储问题"""
    
    print("=" * 80)
    print("LLM分析结果存储诊断")
    print("=" * 80)
    
    # 1. 检查是否有未分析的新闻
    print("\n1. 检查未分析的新闻...")
    df_unprocessed = load_news_after_last_processed()
    print(f"   未分析的新闻数: {len(df_unprocessed)}")
    
    if df_unprocessed.empty:
        print("   [警告] 没有未分析的新闻")
        return
    
    # 2. 测试分析一条新闻
    print("\n2. 测试分析一条新闻...")
    test_batch = df_unprocessed.head(1)
    news_batch = pd.DataFrame([{"content": content} for content in test_batch['formatted_content']])
    
    try:
        print("   开始分析...")
        results = qwen3_model_by_local(news_batch)
        print(f"   分析完成，得到 {len(results)} 条结果")
        
        # 3. 检查结果格式
        print("\n3. 检查结果格式...")
        if results:
            print(f"   结果类型: {type(results)}")
            print(f"   结果长度: {len(results)}")
            
            first_result = results[0]
            print(f"   第一条结果类型: {type(first_result)}")
            print(f"   第一条结果内容: {str(first_result)[:200]}...")
            
            # 检查是否可以转换为列表
            try:
                if isinstance(first_result, (set, dict)):
                    result_list = list(first_result)
                    print(f"   转换为列表成功，长度: {len(result_list)}")
                    if result_list:
                        print(f"   第一个元素类型: {type(result_list[0])}")
                        print(f"   第一个元素内容（前200字符）: {str(result_list[0])[:200]}...")
                        
                        # 尝试解析JSON
                        try:
                            result_json = json.loads(result_list[0])
                            print(f"   JSON解析成功！")
                            print(f"   JSON键: {list(result_json.keys())}")
                        except json.JSONDecodeError as e:
                            print(f"   JSON解析失败: {e}")
                            print(f"   尝试解析的内容: {result_list[0][:500]}")
                else:
                    print(f"   结果不是集合或字典类型")
            except Exception as e:
                print(f"   转换失败: {e}")
        
        # 4. 测试存储
        print("\n4. 测试存储到数据库...")
        news_ids_and_hashes = list(zip(test_batch['id'].tolist(), test_batch['content_hash'].tolist()))
        print(f"   新闻ID和Hash: {news_ids_and_hashes}")
        
        try:
            import_results(results, news_ids_and_hashes)
            print("   [成功] 存储成功！")
            
            # 验证是否真的存储了
            from src.database.db_handle import engine
            sql_check = "SELECT id, llm_analyzed_at, llm_category FROM news_articles WHERE id = %s"
            df_check = pd.read_sql(sql_check, engine, params=(news_ids_and_hashes[0][0],))
            if not df_check.empty and df_check.iloc[0]['llm_analyzed_at'] is not None:
                print(f"   [验证成功] 新闻ID {news_ids_and_hashes[0][0]} 已存储分析结果")
                print(f"   分析时间: {df_check.iloc[0]['llm_analyzed_at']}")
                print(f"   分类: {df_check.iloc[0]['llm_category']}")
            else:
                print(f"   [警告] 验证失败：数据库中没有找到分析结果")
        except Exception as e:
            print(f"   [错误] 存储失败: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"   [错误] 分析失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

if __name__ == '__main__':
    try:
        diagnose_storage_issue()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
