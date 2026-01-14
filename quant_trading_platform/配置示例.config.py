# 配置示例文件
# 请复制此文件内容到 config.py，并填写您的真实信息

# 广发证券API配置示例
GF_API_CONFIG = {
    "api_key": "your_api_key_here",        # 替换为您的API Key
    "api_secret": "your_api_secret_here",  # 替换为您的API Secret
    "app_id": "your_app_id_here",          # 替换为您的App ID
    "base_url": "https://openapi.gf.com.cn",
    "enabled": True  # 设置为True启用广发证券API
}

# 注意事项：
# 1. 请妥善保管您的API密钥，不要泄露
# 2. 建议使用环境变量或配置文件来存储敏感信息
# 3. 不要将包含真实密钥的config.py提交到代码仓库

