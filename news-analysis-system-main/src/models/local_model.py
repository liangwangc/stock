import pandas as pd
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 模型路径或 HuggingFace ID
MODEL_NAME = "Qwen/Qwen3-4B"

# 延迟加载：模型和分词器在首次使用时才加载
_tokenizer = None
_model = None

def _get_model():
    """延迟加载模型（单例模式）"""
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        print("正在加载LLM模型（首次使用，可能需要几分钟）...", flush=True)
        
        # 尝试检测是否有GPU可用
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"检测到设备: {device}", flush=True)
        
        # 尝试禁用代理或使用本地缓存
        import os
        # 保存原始代理设置
        original_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        if original_proxy:
            print(f"检测到代理设置: {original_proxy}", flush=True)
            # 如果代理配置错误（如127.0.0.1:9），尝试禁用代理
            if '127.0.0.1:9' in original_proxy or 'localhost:9' in original_proxy:
                print("检测到无效代理配置，临时禁用代理以使用本地缓存...", flush=True)
                if 'HTTP_PROXY' in os.environ:
                    del os.environ['HTTP_PROXY']
                if 'HTTPS_PROXY' in os.environ:
                    del os.environ['HTTPS_PROXY']
                if 'http_proxy' in os.environ:
                    del os.environ['http_proxy']
                if 'https_proxy' in os.environ:
                    del os.environ['https_proxy']
        
        # 设置使用本地缓存（如果模型已下载）
        # 先尝试在线模式，如果失败则切换到离线模式
        hf_hub_offline_original = os.environ.get('HF_HUB_OFFLINE', '0')
        
        try:
            # 加载分词器
            try:
                # 先尝试在线模式（允许下载）
                os.environ['HF_HUB_OFFLINE'] = '0'
                _tokenizer = AutoTokenizer.from_pretrained(
                    MODEL_NAME, 
                    local_files_only=False,
                    trust_remote_code=True,
                    timeout=10  # 设置10秒超时
                )
                print("分词器加载成功（在线模式）", flush=True)
            except Exception as e:
                error_msg = str(e).lower()
                print(f"在线加载分词器失败: {str(e)}", flush=True)
                
                # 检查是否是网络连接问题
                if 'timeout' in error_msg or 'connection' in error_msg or 'connect' in error_msg:
                    print("检测到网络连接问题，切换到离线模式...", flush=True)
                    # 强制离线模式，避免尝试连接HuggingFace Hub
                    os.environ['HF_HUB_OFFLINE'] = '1'
                    try:
                        _tokenizer = AutoTokenizer.from_pretrained(
                            MODEL_NAME, 
                            local_files_only=True,
                            trust_remote_code=True
                        )
                        print("分词器加载成功（离线模式，使用本地缓存）", flush=True)
                    except Exception as e2:
                        print(f"离线模式加载分词器也失败: {str(e2)}", flush=True)
                        # 恢复环境变量
                        os.environ['HF_HUB_OFFLINE'] = hf_hub_offline_original
                        raise Exception(f"分词器加载失败。在线模式错误: {str(e)}; 离线模式错误: {str(e2)}")
                else:
                    # 其他错误，也尝试离线模式
                    print("尝试使用本地缓存的分词器...", flush=True)
                    os.environ['HF_HUB_OFFLINE'] = '1'
                    try:
                        _tokenizer = AutoTokenizer.from_pretrained(
                            MODEL_NAME, 
                            local_files_only=True,
                            trust_remote_code=True
                        )
                        print("分词器加载成功（使用本地缓存）", flush=True)
                    except Exception as e2:
                        print(f"本地缓存加载分词器也失败: {str(e2)}", flush=True)
                        # 恢复环境变量
                        os.environ['HF_HUB_OFFLINE'] = hf_hub_offline_original
                        raise Exception(f"分词器加载失败。在线模式错误: {str(e)}; 离线模式错误: {str(e2)}")
            
            # 检查是否有accelerate库
            try:
                import accelerate
                has_accelerate = True
            except ImportError:
                has_accelerate = False
            
            # 尝试使用device_map（需要accelerate库），如果失败则使用传统方式
            try:
                if has_accelerate:
                    print("检测到accelerate库，使用device_map='auto'加载模型...", flush=True)
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_NAME,
                        dtype="auto",
                        device_map="auto",
                        local_files_only=(os.environ.get('HF_HUB_OFFLINE') == '1'),
                        trust_remote_code=True,
                        timeout=30  # 设置30秒超时
                    )
                    print("LLM模型加载完成（使用device_map='auto'）", flush=True)
                else:
                    print("未检测到accelerate库，使用传统方式加载模型...", flush=True)
                    print("提示：安装accelerate库可以提升加载效率: pip install accelerate", flush=True)
                    # 使用传统方式加载（不使用device_map）
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_NAME,
                        dtype="auto",
                        local_files_only=(os.environ.get('HF_HUB_OFFLINE') == '1'),
                        trust_remote_code=True,
                        timeout=30  # 设置30秒超时
                    )
                    _model = _model.to(device)
                    print(f"LLM模型加载完成（使用传统方式，设备: {device}）", flush=True)
            except Exception as e:
                error_msg = str(e).lower()
                is_network_error = 'timeout' in error_msg or 'connection' in error_msg or 'connect' in error_msg
                
                if "accelerate" in error_msg:
                    print(f"device_map需要accelerate库，改用传统方式加载...", flush=True)
                    print("提示：安装accelerate库可以提升加载效率: pip install accelerate", flush=True)
                    # 使用传统方式加载（不使用device_map）
                    try:
                        # 如果是网络错误，切换到离线模式
                        if is_network_error:
                            os.environ['HF_HUB_OFFLINE'] = '1'
                            print("检测到网络问题，切换到离线模式...", flush=True)
                        
                        _model = AutoModelForCausalLM.from_pretrained(
                            MODEL_NAME,
                            dtype="auto",
                            local_files_only=(os.environ.get('HF_HUB_OFFLINE') == '1'),
                            trust_remote_code=True,
                            timeout=30 if os.environ.get('HF_HUB_OFFLINE') != '1' else None
                        )
                        _model = _model.to(device)
                        print(f"LLM模型加载完成（使用传统方式，设备: {device}）", flush=True)
                    except Exception as e2:
                        print(f"传统方式加载也失败: {str(e2)}", flush=True)
                        # 尝试使用本地缓存
                        print("尝试使用本地缓存的模型...", flush=True)
                        os.environ['HF_HUB_OFFLINE'] = '1'
                        try:
                            _model = AutoModelForCausalLM.from_pretrained(
                                MODEL_NAME,
                                dtype="auto",
                                local_files_only=True,
                                trust_remote_code=True
                            )
                            _model = _model.to(device)
                            print(f"LLM模型加载完成（使用本地缓存，设备: {device}）", flush=True)
                        except Exception as e3:
                            # 恢复环境变量
                            os.environ['HF_HUB_OFFLINE'] = hf_hub_offline_original
                            raise Exception(f"模型加载失败。device_map错误: {str(e)}; 传统方式错误: {str(e2)}; 本地缓存错误: {str(e3)}")
                else:
                    # 其他错误，尝试使用本地缓存
                    print(f"在线加载失败: {str(e)}", flush=True)
                    if is_network_error:
                        print("检测到网络连接问题，切换到离线模式...", flush=True)
                        os.environ['HF_HUB_OFFLINE'] = '1'
                    
                    print("尝试使用本地缓存的模型...", flush=True)
                    try:
                        _model = AutoModelForCausalLM.from_pretrained(
                            MODEL_NAME,
                            dtype="auto",
                            local_files_only=True,
                            trust_remote_code=True
                        )
                        _model = _model.to(device)
                        print(f"LLM模型加载完成（使用本地缓存，设备: {device}）", flush=True)
                    except Exception as e_cache:
                        print(f"本地缓存加载也失败: {str(e_cache)}", flush=True)
                        # 恢复环境变量
                        os.environ['HF_HUB_OFFLINE'] = hf_hub_offline_original
                        raise Exception(f"模型加载失败。在线加载错误: {str(e)}; 本地缓存错误: {str(e_cache)}")
        finally:
            # 恢复原始环境变量设置
            if 'HF_HUB_OFFLINE' in locals():
                os.environ['HF_HUB_OFFLINE'] = hf_hub_offline_original
            
            # 恢复原始代理设置
            if original_proxy:
                if 'HTTP_PROXY' not in os.environ and 'HTTPS_PROXY' not in os.environ:
                    # 只在确实删除了代理设置时才恢复
                    pass  # 不恢复无效的代理配置
        
        print("LLM模型加载完成", flush=True)
    return _tokenizer, _model

def qwen3_model_by_local(news_batch, batch_size=1):
    """
    使用本地加载的 Qwen3-4B 模型批量处理新闻，返回模型生成的原始文本。
    
    性能优化：
    - 减少输出长度（max_new_tokens: 1024 -> 512）
    - 使用贪心解码（num_beams=1）加快生成速度
    - 降低top_p以加快采样速度
    - 支持批量处理（batch_size > 1时，内存允许的情况下可以批量处理）

    Args:
        news_batch (pd.DataFrame): 包含新闻内容的 DataFrame，每行至少包含 'content' 字段
        batch_size (int): 批量处理大小，默认1（逐条处理）。如果内存充足可以设置为2-4

    Returns:
        List[Dict]: 每个元素包含原始新闻索引和模型输出的 raw text
    """
    results = []

    # 分类体系提示词（保持不变）
    system_prompt = """你是一个专业的金融新闻分析师，专注于为期货量化交易提供新闻分类和分析服务。你需要将每条新闻准确分类，并提取有价值的信息。

分类体系如下：
1. 宏观经济类：央行政策、经济数据、政府财政政策、就业数据等
2. 商品期货相关：农产品、能源、金属、工业品等
3. 金融市场类：股市动态、债券市场、外汇市场、其他期货市场情况
4. 地缘政治类：国际冲突、贸易争端、重大国际事件
5. 行业政策类：监管变化、产业政策调整、环保政策
6. 非金融类：天气、自然灾害、非经济类社会新闻等"""

    # 获取模型和分词器（延迟加载，只加载一次）
    tokenizer, model = _get_model()
    
    # 批量处理新闻
    total_news = len(news_batch)
    for batch_start in tqdm(range(0, total_news, batch_size), desc="Processing News Batches"):
        batch_end = min(batch_start + batch_size, total_news)
        batch_data = news_batch.iloc[batch_start:batch_end]
        
        for idx, (_, row) in enumerate(batch_data.iterrows()):
            content = row['content']

            user_prompt = """请对以下新闻进行分类和分析：

                        新闻内容: {content}

                        不包含任何其他内容,并严格按照以下json格式进行输出：
                          "news_index": "新闻序号"(与输入新闻的id号相同),
                          "date": "发布日期"(与输入新闻内容中的date相同),
                          "category": "主分类(从上述6类中选择一个)",
                          "subcategory": "子分类(具体说明该新闻属于主分类中的哪一小类)",
                          "is_market_relevant": true/false, (是否与金融市场相关)
                          "keywords": "关键词1,关键词2, 关键词3,关键词4",
                          "sentiment": 0.0, (情感得分,范围为-1~1，-1表示极度负面，0表示中性，1表示极度正面)
                          "impact_markets": "市场,品种"（可能受到影响的市场或品种）,
                          "summary": "一句话总结这条新闻的核心内容"

                        现在请你处理当前新闻。
                        """
            user_prompt = user_prompt.replace("{content}", content)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            try:
                # 使用 chat template 构造输入（关闭 thinking mode）
                text = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False
                )

                # Tokenize 输入
                inputs = tokenizer([text], return_tensors="pt").to(model.device)

                # 模型生成（优化参数以提升速度）
                # 注意：对于CPU模式，批量处理可能不会带来太大提升，但可以减少模型调用开销
                with torch.no_grad():  # 禁用梯度计算以节省内存和加速
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=400,      # 进一步减少输出长度（512->400）以提升速度
                        temperature=0.1,         # 更确定性的输出
                        top_p=0.85,              # 进一步降低top_p以加快生成速度（0.9->0.85）
                        do_sample=True,
                        num_beams=1,            # 使用贪心解码（beam=1）而不是beam search，速度更快
                        pad_token_id=tokenizer.eos_token_id,  # 设置pad_token以避免警告
                        use_cache=True           # 使用KV缓存以加速生成
                    )

                # 解码生成内容
                output_text = tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True).strip()

                # 保存结果（格式：集合，包含JSON字符串）
                results.append({output_text})

            except Exception as e:
                print(f"处理新闻时出错: {e}", flush=True)
                results.append({
                    "error": str(e)
                })

    return results