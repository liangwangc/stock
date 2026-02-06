from ..database.db_handle import load_news_after_last_processed, import_results
import pandas as pd
import json
import schedule
import time
import os
from datetime import datetime

# 尝试导入本地模型和API模型
LOCAL_MODEL_AVAILABLE = False
API_MODEL_AVAILABLE = False

# 尝试导入本地模型
try:
    from ..models.local_model import qwen3_model_by_local
    LOCAL_MODEL_AVAILABLE = True
except ImportError as e:
    print(f"本地模型不可用（缺少依赖: {str(e)}），将尝试使用API模式", flush=True)

# 尝试导入API模型（无论本地模型是否可用，都尝试导入API模型作为备选）
try:
    from ..models.api_model import qwen3_model_by_api
    API_MODEL_AVAILABLE = True
except ImportError as e:
    print(f"API模型不可用（缺少依赖: {str(e)}）", flush=True)

# 检查是否有可用的模型
if not LOCAL_MODEL_AVAILABLE and not API_MODEL_AVAILABLE:
    print("警告：本地模型和API模型都不可用，请安装依赖（pip install transformers torch）或配置API密钥", flush=True)

def job(start_date=None, end_date=None):
    """
    执行LLM分析任务
    
    Args:
        start_date: 开始日期（可选），格式：'2026-01-23' 或 datetime对象，只分析此日期之后的新闻
        end_date: 结束日期（可选），格式：'2026-01-23' 或 datetime对象，只分析此日期之前的新闻
    
    示例：
        # 只分析2026-01-23的新闻
        job(start_date='2026-01-23 00:00:00', end_date='2026-01-23 23:59:59')
        
        # 只分析最近7天的新闻
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        job(start_date=start_date, end_date=end_date)
    """
    df_unprocessed = load_news_after_last_processed(start_date=start_date, end_date=end_date)
    if df_unprocessed.empty:
        if start_date or end_date:
            print(f"在指定时间范围内无新数据（开始：{start_date}，结束：{end_date}），等待下次运行。", flush=True)
        else:
            print("无新数据，等待下次运行。", flush=True)
        return

    if start_date or end_date:
        print(f"找到 {len(df_unprocessed)} 条未分析的新闻（时间范围：{start_date} 到 {end_date}）", flush=True)
    else:
        print(f"找到 {len(df_unprocessed)} 条未分析的新闻", flush=True)

    # 创建新闻数据批次
    news_batch = pd.DataFrame([{"content": content} for content in df_unprocessed['formatted_content']])
    
    # 根据可用性选择模型
    print("开始 LLM 分析...", flush=True)
    
    if LOCAL_MODEL_AVAILABLE:
        try:
            print("使用本地模型进行分析...", flush=True)
            results = qwen3_model_by_local(news_batch)
            print(f"LLM 分析完成，共 {len(results)} 条结果", flush=True)
        except Exception as e:
            error_msg = str(e).lower()
            print(f"本地模型分析失败: {str(e)}", flush=True)
            import traceback
            print(f"错误详情: {traceback.format_exc()}", flush=True)
            
            # 检查是否是网络连接问题（超时、连接失败等）
            is_network_error = (
                'timeout' in error_msg or 
                'connection' in error_msg or 
                'connect' in error_msg or
                'huggingface.co' in error_msg or
                'max retries' in error_msg
            )
            
            if is_network_error:
                print("检测到网络连接问题，本地模型无法连接HuggingFace Hub", flush=True)
                print("提示：如果模型已下载到本地缓存，请设置环境变量 HF_HUB_OFFLINE=1 强制使用离线模式", flush=True)
            
            # 尝试切换到API模式（即使API_MODEL_AVAILABLE是False，也尝试动态导入）
            print("尝试切换到API模式...", flush=True)
            api_model_func = None
            
            # 如果API模型未导入，尝试动态导入
            if not API_MODEL_AVAILABLE:
                try:
                    from ..models.api_model import qwen3_model_by_api
                    api_model_func = qwen3_model_by_api
                    print("成功动态导入API模型", flush=True)
                except ImportError as import_err:
                    print(f"无法导入API模型: {str(import_err)}", flush=True)
                    api_model_func = None
            else:
                api_model_func = qwen3_model_by_api
            
            # 如果API模型可用，尝试使用
            if api_model_func:
                try:
                    # 尝试从环境变量获取API密钥
                    api_key = os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('OPENAI_API_KEY')
                    if api_key:
                        print("使用环境变量中的API密钥", flush=True)
                        results = api_model_func(news_batch, api_key=api_key)
                    else:
                        print("未找到API密钥，尝试使用默认配置...", flush=True)
                        results = api_model_func(news_batch)
                    print(f"LLM 分析完成（API模式），共 {len(results)} 条结果", flush=True)
                except Exception as api_e:
                    print(f"API模式也失败: {str(api_e)}", flush=True)
                    import traceback
                    print(f"API模式错误详情: {traceback.format_exc()}", flush=True)
                    
                    # 提供更详细的错误信息
                    if is_network_error:
                        error_summary = (
                            f"本地模型因网络连接问题失败（无法连接HuggingFace Hub），"
                            f"且API模式也失败。\n"
                            f"建议：\n"
                            f"1. 检查网络连接\n"
                            f"2. 如果模型已下载，设置 HF_HUB_OFFLINE=1 强制离线模式\n"
                            f"3. 配置API密钥（DASHSCOPE_API_KEY 或 OPENAI_API_KEY）\n"
                            f"本地模型错误: {str(e)}\n"
                            f"API模型错误: {str(api_e)}"
                        )
                    else:
                        error_summary = (
                            f"本地模型和API模型都失败。\n"
                            f"本地模型错误: {str(e)}\n"
                            f"API模型错误: {str(api_e)}"
                        )
                    raise Exception(error_summary)
            else:
                # 无法使用API模型
                if is_network_error:
                    error_summary = (
                        f"本地模型因网络连接问题失败（无法连接HuggingFace Hub），"
                        f"且无法使用API模型。\n"
                        f"建议：\n"
                        f"1. 检查网络连接\n"
                        f"2. 如果模型已下载到本地缓存，设置环境变量 HF_HUB_OFFLINE=1 强制使用离线模式\n"
                        f"3. 安装API模型依赖并配置API密钥\n"
                        f"错误详情: {str(e)}"
                    )
                else:
                    error_summary = (
                        f"本地模型失败且无法使用API模型。\n"
                        f"错误: {str(e)}"
                    )
                raise Exception(error_summary)
    elif API_MODEL_AVAILABLE:
        print("使用API模式进行分析...", flush=True)
        # 尝试从环境变量获取API密钥
        api_key = os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise Exception("API模式需要配置API密钥。请设置环境变量 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")
        results = qwen3_model_by_api(news_batch, api_key=api_key)
        print(f"LLM 分析完成（API模式），共 {len(results)} 条结果", flush=True)
    else:
        raise Exception("无法使用任何LLM模型：本地模型和API模型都不可用。请安装依赖（pip install transformers torch）或配置API密钥（设置环境变量 DASHSCOPE_API_KEY）")
    
    # 准备新闻ID和hash的对应关系
    news_ids_and_hashes = list(zip(df_unprocessed['id'].tolist(), df_unprocessed['content_hash'].tolist()))

    # 保存 results 到本地 JSON 文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    last_hash = df_unprocessed['content_hash'].iloc[-1] if not df_unprocessed.empty else 'unknown'
    filename = f"analysis_results_{timestamp}_{last_hash}.json"
    save_path = os.path.join("../../data/backup_results", filename)

    # 确保目录存在
    os.makedirs("../../data/backup_results", exist_ok=True)

    try:
        # 保存为 JSON 文件
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump([list(item)[0] for item in results], f, ensure_ascii=False, indent=2)
        print(f"分析结果已备份到：{save_path}", flush=True)
    except Exception as e:
        print(f"保存分析结果 JSON 文件失败: {e}", flush=True)

    # 尝试导入到数据库
    try:
        import_results(results, news_ids_and_hashes)
        print("分析结果已成功更新到数据库", flush=True)
    except Exception as e:
        print(f"写入数据库失败: {e}", flush=True)
        print("请稍后使用备份文件手动恢复。", flush=True)
        import traceback
        traceback.print_exc()


# 调度循环只在直接运行此脚本时执行，导入时不会执行
if __name__ == '__main__':
    # 每120分钟执行一次，可以替换成固定间隔时间启动
    # schedule.every(120).minutes.do(job)
    
    # 每天凌晨1点执行，可以修改成你具体需要启动的时间
    schedule.every().day.at("09:27").do(job)
    
    # 启动时是否立即执行一次（如果需要，可以保留这句）
    # job()
    
    # 开始调度循环
    print("开始任务调度，每天09:27执行一次任务", flush=True)
    while True:
        schedule.run_pending()
        time.sleep(1)