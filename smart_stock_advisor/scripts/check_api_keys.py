"""
检查API密钥配置情况
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_api_keys():
    """检查API密钥配置"""
    
    print("=" * 80)
    print("API密钥配置检查")
    print("=" * 80)
    
    # 1. 检查环境变量
    print("\n1. 检查环境变量...")
    dashscope_key = os.environ.get('DASHSCOPE_API_KEY')
    openai_key = os.environ.get('OPENAI_API_KEY')
    
    if dashscope_key:
        masked_key = dashscope_key[:8] + "..." + dashscope_key[-4:] if len(dashscope_key) > 12 else "***"
        print(f"   DASHSCOPE_API_KEY: {masked_key} [已配置]")
    else:
        print(f"   DASHSCOPE_API_KEY: [未配置]")
    
    if openai_key:
        masked_key = openai_key[:8] + "..." + openai_key[-4:] if len(openai_key) > 12 else "***"
        print(f"   OPENAI_API_KEY: {masked_key} [已配置]")
    else:
        print(f"   OPENAI_API_KEY: [未配置]")
    
    # 2. 检查配置文件（news-analysis-system-main）
    print("\n2. 检查news-analysis-system-main配置文件...")
    try:
        import sys
        news_system_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'news-analysis-system-main')
        if os.path.exists(news_system_path):
            config_path = os.path.join(news_system_path, 'src', 'config', 'config.py')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'DASHSCOPE_API_KEY' in content or 'OPENAI_API_KEY' in content:
                        print(f"   配置文件: {config_path}")
                        print(f"   状态: 包含API密钥配置")
                    else:
                        print(f"   配置文件: {config_path}")
                        print(f"   状态: 未找到API密钥配置")
            else:
                print(f"   配置文件: 不存在 ({config_path})")
        else:
            print(f"   项目路径: 不存在 ({news_system_path})")
    except Exception as e:
        print(f"   检查失败: {e}")
    
    # 3. 检查smart_stock_advisor配置文件
    print("\n3. 检查smart_stock_advisor配置文件...")
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.py')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'DASHSCOPE_API_KEY' in content or 'OPENAI_API_KEY' in content:
                    print(f"   配置文件: {config_path}")
                    print(f"   状态: 包含API密钥配置")
                else:
                    print(f"   配置文件: {config_path}")
                    print(f"   状态: 未找到API密钥配置")
        else:
            print(f"   配置文件: 不存在")
    except Exception as e:
        print(f"   检查失败: {e}")
    
    # 4. 总结
    print("\n4. 总结...")
    has_api_key = bool(dashscope_key or openai_key)
    
    if has_api_key:
        print("   [成功] 已找到API密钥配置（环境变量）")
        print("   可以使用API模式进行LLM分析")
    else:
        print("   [警告] 未找到API密钥配置")
        print("   当前代码只支持从环境变量读取API密钥")
        print("   如果需要从配置文件读取，需要修改代码")
    
    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)

if __name__ == '__main__':
    try:
        check_api_keys()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
