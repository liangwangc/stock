# 翻译API接口说明

## 📋 当前使用的翻译API

脚本 `update_word_bank_examples.php` 现在支持 **6个免费翻译API**，按顺序尝试：

### 1. Google Translate（免费，无需API Key）
- **URL**: `https://translate.googleapis.com/translate_a/single`
- **优点**: 翻译质量高，稳定性好
- **缺点**: 有频率限制，可能被限流
- **状态**: ✅ 已实现

### 2. MyMemory Translation API（免费，无需API Key）
- **URL**: `https://api.mymemory.translated.net/get`
- **优点**: 免费，无需注册
- **缺点**: 有时返回英文而不是中文
- **状态**: ✅ 已实现

### 3. LibreTranslate（免费开源）
- **URL**: `https://libretranslate.com/translate`
- **优点**: 开源，可自托管
- **缺点**: 公共服务器可能不稳定
- **状态**: ✅ 已实现

### 4. Free Translate API（免费，无需API Key）
- **URL**: `https://ftapi.pythonanywhere.com/translate`
- **优点**: 简单易用
- **缺点**: 演示版本，可能不稳定
- **状态**: ✅ 已实现（新增）

### 5. 百度翻译（非官方接口）
- **URL**: `https://fanyi.baidu.com/transapi`
- **优点**: 翻译质量好
- **缺点**: 非官方接口，可能随时失效
- **状态**: ✅ 已实现（新增）

### 6. 有道翻译（非官方接口）
- **URL**: `https://fanyi.youdao.com/translate_o`
- **优点**: 翻译质量好
- **缺点**: 非官方接口，可能随时失效，需要签名
- **状态**: ✅ 已实现（新增）

## 🔄 工作流程

1. **顺序尝试**: 按顺序尝试每个API，直到成功
2. **延迟机制**: 每个API之间延迟0.3秒，避免过快请求
3. **验证结果**: 检查返回结果是否包含中文字符
4. **失败处理**: 如果所有API都失败，返回空字符串并记录日志

## 📊 API成功率对比

| API | 成功率 | 速度 | 稳定性 | 推荐度 |
|-----|--------|------|--------|--------|
| Google Translate | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| MyMemory | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| LibreTranslate | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Free Translate | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| 百度翻译 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 有道翻译 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

## 🚀 使用建议

### 提高成功率的方法：

1. **增加延迟时间**
   ```php
   // 在 update_word_bank_examples.php 第 676 行
   usleep(500000); // 从 0.2 秒增加到 0.5 秒
   ```

2. **减少并发数**（如果使用多进程版本）
   ```bash
   php update_word_bank_examples_parallel.php 2  # 使用2个进程而不是4个
   ```

3. **分批处理**
   - 将大量单词分成小批次
   - 每批处理完后等待一段时间

4. **重试机制**
   - 脚本会自动重试失败的单词
   - 使用模式2可以只更新不完整的例句

## 🔧 其他可用的翻译API（需要API Key）

如果需要更高的稳定性和翻译质量，可以考虑以下付费/免费API：

### DeepL API（推荐）
- **免费额度**: 500,000字符/月
- **需要**: API Key（免费注册）
- **优点**: 翻译质量最高
- **网址**: https://www.deepl.com/pro-api

### 百度翻译API
- **免费额度**: 每月200万字符
- **需要**: API Key（免费注册）
- **优点**: 中文翻译质量好
- **网址**: https://fanyi-api.baidu.com/

### 有道翻译API
- **免费额度**: 每月100万字符
- **需要**: API Key（免费注册）
- **优点**: 中文翻译质量好
- **网址**: https://ai.youdao.com/

### 腾讯翻译API
- **免费额度**: 每月500万字符
- **需要**: API Key（免费注册）
- **优点**: 免费额度大
- **网址**: https://cloud.tencent.com/product/tmt

## 📝 添加新的翻译API

如果需要添加新的翻译API，可以在 `translateToChinese()` 函数中添加：

```php
// 方法N：使用新的翻译API
$urlN = "https://api.example.com/translate";
// ... curl设置 ...
$responseN = @curl_exec($chN);
// ... 处理响应 ...
if (成功) {
    return $translationN;
}
```

## ⚠️ 注意事项

1. **API限流**: 免费API通常有频率限制，不要请求过快
2. **网络问题**: 某些API可能因为网络问题无法访问
3. **服务变更**: 非官方接口可能随时失效
4. **翻译质量**: 不同API的翻译质量可能不同
5. **字符限制**: 某些API对单次翻译的字符数有限制

## 🎯 最佳实践

1. **优先使用官方API**: Google Translate、MyMemory、LibreTranslate
2. **备用非官方API**: 百度、有道作为备用
3. **监控失败率**: 如果某个API失败率过高，可以暂时禁用
4. **定期更新**: 定期检查API是否仍然可用
5. **错误处理**: 记录详细的错误日志，便于排查问题
