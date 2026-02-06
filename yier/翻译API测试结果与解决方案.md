# 翻译API测试结果与解决方案

## 📊 测试结果（2024年1月）

### 测试文本
- 英文：`Hello, everyone.`
- 期望中文：`大家好。`

### API测试结果

| API | HTTP状态 | 结果 | 说明 |
|-----|----------|------|------|
| Google Translate | 0 (超时) | ❌ 失败 | 连接超时，可能无法访问 |
| MyMemory | 429 | ❌ 失败 | 被限流（请求过多） |
| LibreTranslate | 400 | ❌ 失败 | **现在需要API Key** |
| 百度翻译 | 200 (errno:1022) | ❌ 失败 | 接口已失效 |
| 有道翻译 | 200 (errorCode:50) | ❌ 失败 | 接口已失效 |
| Google备用端点1 | 0 (超时) | ❌ 失败 | 连接超时 |
| Google备用端点2 | 0 (超时) | ❌ 失败 | 连接超时 |

## ⚠️ 问题分析

### 1. Google Translate
- **问题**：连接超时
- **可能原因**：
  - 网络无法访问Google服务
  - 防火墙/代理限制
  - Google加强了反爬虫机制

### 2. MyMemory
- **问题**：HTTP 429（请求过多）
- **原因**：免费API有频率限制
- **解决方案**：增加延迟时间，减少并发

### 3. LibreTranslate
- **问题**：HTTP 400，需要API Key
- **变化**：LibreTranslate公共服务器现在需要API Key
- **解决方案**：
  - 注册获取免费API Key
  - 或自托管LibreTranslate服务器

### 4. 百度/有道翻译
- **问题**：非官方接口已失效
- **原因**：这些服务加强了安全验证
- **解决方案**：使用官方API（需要API Key）

## 💡 解决方案

### 方案1：使用官方API（推荐）

#### 1.1 LibreTranslate（免费，推荐）
- **注册地址**：https://portal.libretranslate.com
- **免费额度**：足够使用
- **优点**：开源，免费，质量好
- **步骤**：
  1. 注册账号
  2. 获取API Key
  3. 修改代码使用API Key

#### 1.2 DeepL API（推荐）
- **免费额度**：500,000字符/月
- **注册地址**：https://www.deepl.com/pro-api
- **优点**：翻译质量最高
- **缺点**：需要信用卡（但免费额度足够）

#### 1.3 百度翻译API
- **免费额度**：2,000,000字符/月
- **注册地址**：https://fanyi-api.baidu.com/
- **优点**：中文翻译质量好，免费额度大

#### 1.4 腾讯翻译API
- **免费额度**：5,000,000字符/月
- **注册地址**：https://cloud.tencent.com/product/tmt
- **优点**：免费额度最大

### 方案2：增加延迟和重试机制

如果继续使用免费API，可以：

1. **增加延迟时间**
   ```php
   // 在 update_word_bank_examples.php 中
   usleep(2000000); // 从 0.2 秒增加到 2 秒
   ```

2. **减少并发数**
   ```bash
   # 使用更少的进程
   php update_word_bank_examples_parallel.php 1  # 单进程
   ```

3. **分批处理**
   - 将单词分成小批次
   - 每批处理完后等待一段时间

### 方案3：使用本地翻译（离线方案）

可以考虑使用本地翻译库，但需要：
- 安装Python和翻译库
- 或使用其他离线翻译工具

## 🔧 代码修改建议

### 如果使用LibreTranslate API Key：

```php
// 在 translateToChinese 函数中添加
function translateToChinese($text, $apiKey = '') {
    // ... 其他代码 ...
    
    // LibreTranslate with API Key
    if (!empty($apiKey)) {
        $url = "https://libretranslate.com/translate";
        $postData = json_encode([
            'q' => $text,
            'source' => 'en',
            'target' => 'zh',
            'format' => 'text',
            'api_key' => $apiKey
        ]);
        // ... curl请求 ...
    }
}
```

### 如果使用DeepL API：

```php
function translateToChinese($text, $apiKey = '') {
    if (!empty($apiKey)) {
        $url = "https://api-free.deepl.com/v2/translate";
        $postData = http_build_query([
            'auth_key' => $apiKey,
            'text' => $text,
            'source_lang' => 'EN',
            'target_lang' => 'ZH'
        ]);
        // ... curl请求 ...
    }
}
```

## 📝 当前建议

1. **短期方案**：
   - 增加延迟时间到2秒
   - 使用单进程处理
   - 分批处理单词

2. **长期方案**：
   - 注册LibreTranslate账号获取免费API Key（推荐）
   - 或注册DeepL API（翻译质量最高）
   - 或注册百度/腾讯翻译API（免费额度大）

3. **如果网络无法访问Google**：
   - 必须使用其他API
   - 建议使用LibreTranslate或DeepL

## 🚀 下一步操作

1. **立即可以做的**：
   - 修改 `update_word_bank_examples.php`，增加延迟时间
   - 使用单进程模式运行

2. **推荐做的**：
   - 注册LibreTranslate账号：https://portal.libretranslate.com
   - 获取API Key并修改代码
   - 这样就能稳定使用了

3. **如果急需大量翻译**：
   - 注册腾讯翻译API（免费额度最大）
   - 或注册百度翻译API（中文翻译质量好）

## ⚙️ 配置文件建议

可以创建一个配置文件来管理API Key：

```php
// config_translation.php
<?php
return [
    'libretranslate_api_key' => '', // LibreTranslate API Key
    'deepl_api_key' => '', // DeepL API Key
    'baidu_app_id' => '', // 百度翻译 App ID
    'baidu_secret_key' => '', // 百度翻译 Secret Key
];
```

然后在代码中读取配置使用。
