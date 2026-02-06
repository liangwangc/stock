"""
估算LLM分析所需时间
根据数据库中的未分析新闻数量和硬件性能进行估算
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_connection import DatabaseConnection
import torch

def estimate_analysis_time():
    """估算LLM分析所需时间"""
    
    print("=" * 80)
    print("LLM深度分析时间估算")
    print("=" * 80)
    
    # 1. 查询未分析的新闻数量
    print("\n1. 查询数据库中的未分析新闻数量...")
    sql = """
        SELECT COUNT(*) as unanalyzed_count
        FROM news_articles
        WHERE llm_analyzed_at IS NULL
    """
    result = DatabaseConnection.execute_query(sql)
    unanalyzed_count = result[0]['unanalyzed_count'] if result else 0
    
    # 查询已分析的新闻数量
    sql_analyzed = """
        SELECT COUNT(*) as analyzed_count
        FROM news_articles
        WHERE llm_analyzed_at IS NOT NULL
    """
    result_analyzed = DatabaseConnection.execute_query(sql_analyzed)
    analyzed_count = result_analyzed[0]['analyzed_count'] if result_analyzed else 0
    
    # 查询总新闻数量
    sql_total = "SELECT COUNT(*) as total_count FROM news_articles"
    result_total = DatabaseConnection.execute_query(sql_total)
    total_count = result_total[0]['total_count'] if result_total else 0
    
    print(f"   总新闻数: {total_count:,} 条")
    print(f"   已分析: {analyzed_count:,} 条 ({analyzed_count/total_count*100:.1f}%)" if total_count > 0 else "   已分析: 0 条")
    print(f"   未分析: {unanalyzed_count:,} 条 ({unanalyzed_count/total_count*100:.1f}%)" if total_count > 0 else "   未分析: 0 条")
    
    if unanalyzed_count == 0:
        print("\n✓ 所有新闻已分析完成！")
        return
    
    # 2. 检测硬件配置
    print("\n2. 检测硬件配置...")
    has_cuda = torch.cuda.is_available()
    if has_cuda:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
        print(f"   GPU: {gpu_name}")
        print(f"   显存: {gpu_memory:.1f} GB")
        print(f"   CUDA版本: {torch.version.cuda}")
    else:
        print("   GPU: 未检测到CUDA设备（将使用CPU）")
        import platform
        cpu_info = platform.processor()
        print(f"   CPU: {cpu_info}")
    
    # 3. 估算处理时间
    print("\n3. 时间估算（基于Qwen3-4B模型）...")
    
    # 模型加载时间（首次运行）
    model_load_time = 60  # 秒（首次加载模型需要约1分钟）
    
    # 根据硬件配置估算每条新闻的处理时间
    if has_cuda:
        # GPU模式：根据显存大小估算速度
        if gpu_memory >= 8:
            # 8GB+ 显存：可以完整加载模型，速度较快
            time_per_news = 3  # 每条新闻约3秒
            print(f"   处理模式: GPU加速（显存充足）")
        elif gpu_memory >= 4:
            # 4-8GB 显存：可能需要量化或部分卸载，速度中等
            time_per_news = 5  # 每条新闻约5秒
            print(f"   处理模式: GPU加速（显存中等，可能使用量化）")
        else:
            # <4GB 显存：可能使用CPU+GPU混合，速度较慢
            time_per_news = 8  # 每条新闻约8秒
            print(f"   处理模式: GPU+CPU混合（显存不足）")
    else:
        # CPU模式：速度较慢
        import multiprocessing
        cpu_cores = multiprocessing.cpu_count()
        if cpu_cores >= 8:
            time_per_news = 20  # 每条新闻约20秒（8核+）
            print(f"   处理模式: CPU多核（{cpu_cores}核）")
        elif cpu_cores >= 4:
            time_per_news = 30  # 每条新闻约30秒（4-8核）
            print(f"   处理模式: CPU多核（{cpu_cores}核）")
        else:
            time_per_news = 45  # 每条新闻约45秒（<4核）
            print(f"   处理模式: CPU（{cpu_cores}核，性能较低）")
    
    # 计算总时间
    total_processing_time = unanalyzed_count * time_per_news
    total_time_with_load = total_processing_time + model_load_time
    
    # 转换为可读格式
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}小时{minutes}分钟{secs}秒"
        elif minutes > 0:
            return f"{minutes}分钟{secs}秒"
        else:
            return f"{secs}秒"
    
    print(f"\n   每条新闻处理时间: ~{time_per_news}秒")
    print(f"   模型加载时间（首次）: ~{format_time(model_load_time)}")
    print(f"   总处理时间（不含加载）: ~{format_time(total_processing_time)}")
    print(f"   总预计时间（含首次加载）: ~{format_time(total_time_with_load)}")
    
    # 4. 建议
    print("\n4. 建议：")
    if total_time_with_load > 3600:  # 超过1小时
        hours = total_time_with_load / 3600
        print(f"   [警告] 预计需要 {hours:.1f} 小时，建议：")
        print(f"      - 分批处理：可以分多次运行，系统会记录进度")
        print(f"      - 使用GPU：如果有GPU，可以显著加速（预计可提速5-10倍）")
        print(f"      - 后台运行：可以在后台运行，不影响其他操作")
    elif total_time_with_load > 1800:  # 超过30分钟
        print(f"   [警告] 预计需要约 {format_time(total_time_with_load)}，建议分批处理")
    else:
        print(f"   [成功] 预计时间较短，可以一次性完成")
    
    if not has_cuda:
        print(f"   [提示] 如果您的电脑有NVIDIA GPU，安装CUDA后可以大幅提升速度")
    
    # 5. 性能优化建议
    print("\n5. 性能优化建议：")
    if has_cuda and gpu_memory < 8:
        print(f"   - 考虑使用量化模型（4-bit/8-bit）以降低显存占用")
        print(f"   - 调整batch_size（当前是逐条处理，可以尝试批量处理）")
    elif not has_cuda:
        print(f"   - 考虑使用API模式（如果配置了API密钥）")
        print(f"   - 或者使用云端GPU服务")
    
    print("\n" + "=" * 80)
    print("估算完成")
    print("=" * 80)

if __name__ == '__main__':
    try:
        estimate_analysis_time()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
