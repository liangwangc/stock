"""
测试LLM分析（带时间范围）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.analysis.main import job
from datetime import datetime, timedelta

def test_analyze_today():
    """分析今天的新闻"""
    today = datetime.now().strftime('%Y-%m-%d')
    start_date = f'{today} 00:00:00'
    end_date = f'{today} 23:59:59'
    
    print(f"分析今天（{today}）的新闻...")
    print(f"时间范围：{start_date} 到 {end_date}")
    job(start_date=start_date, end_date=end_date)

def test_analyze_last_7_days():
    """分析最近7天的新闻"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"分析最近7天的新闻...")
    print(f"时间范围：{start_date} 到 {end_date}")
    job(start_date=start_date, end_date=end_date)

def test_analyze_specific_date():
    """分析指定日期的新闻"""
    start_date = '2026-01-23 00:00:00'
    end_date = '2026-01-23 23:59:59'
    
    print(f"分析指定日期（2026-01-23）的新闻...")
    print(f"时间范围：{start_date} 到 {end_date}")
    job(start_date=start_date, end_date=end_date)

def test_analyze_all():
    """分析所有未分析的新闻（不限制时间范围）"""
    print("分析所有未分析的新闻（不限制时间范围）...")
    job()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'today':
            test_analyze_today()
        elif mode == '7days':
            test_analyze_last_7_days()
        elif mode == 'date':
            if len(sys.argv) > 2:
                date_str = sys.argv[2]
                start_date = f'{date_str} 00:00:00'
                end_date = f'{date_str} 23:59:59'
                print(f"分析指定日期（{date_str}）的新闻...")
                job(start_date=start_date, end_date=end_date)
            else:
                test_analyze_specific_date()
        else:
            print("用法：")
            print("  py test_llm_analysis_with_date_range.py today      # 分析今天的新闻")
            print("  py test_llm_analysis_with_date_range.py 7days     # 分析最近7天的新闻")
            print("  py test_llm_analysis_with_date_range.py date 2026-01-23  # 分析指定日期的新闻")
            print("  py test_llm_analysis_with_date_range.py all       # 分析所有未分析的新闻")
    else:
        print("=" * 80)
        print("LLM分析测试（带时间范围）")
        print("=" * 80)
        print("\n用法：")
        print("  py test_llm_analysis_with_date_range.py today      # 分析今天的新闻")
        print("  py test_llm_analysis_with_date_range.py 7days     # 分析最近7天的新闻")
        print("  py test_llm_analysis_with_date_range.py date 2026-01-23  # 分析指定日期的新闻")
        print("  py test_llm_analysis_with_date_range.py all       # 分析所有未分析的新闻")
        print("\n默认：分析所有未分析的新闻")
        print("=" * 80)
        test_analyze_all()
