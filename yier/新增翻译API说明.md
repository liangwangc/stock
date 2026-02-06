# 新增翻译API说明

## 🆕 新增的翻译API

根据搜索结果，我添加了以下新的翻译API选项：

### 1. Lingvanex API（方法7）
- **URL**: `https://api-b2b.backenster.com/b1/api/v3/translate`
- **类型**: 免费试用（可能有次数限制）
- **优点**: 翻译质量好
- **缺点**: 免费试用可能有限制
- **状态**: ✅ 已添加

### 2. Reverso Context（方法8）
- **URL**: `https://context.reverso.net/translation/english-chinese/`
- **类型**: 免费网页翻译服务
- **优点**: 提供上下文翻译
- **缺点**: 需要从HTML中提取，可能不稳定
- **状态**: ✅ 已添加

### 3. Google Translate 移动端（方法9）
- **URL**: `https://translate.google.com/m?sl=en&tl=zh-CN&q=`
- **类型**: Google Translate移动版接口
- **优点**: 可能比桌面版更容易访问
- **缺点**: 需要解析HTML
- **状态**: ✅ 已添加

## 📊 当前支持的API列表（共9个）

按优先级顺序：

1. **Google Translate**（主要接口）
2. **MyMemory Translation API**
3. **LibreTranslate**（需要API Key）
4. **Free Translate API**
5. **Google Translate**（备用接口1）
6. **Google Translate**（备用接口2）
7. **Lingvanex API**（新增）
8. **Reverso Context**（新增）
9. **Google Translate 移动端**（新增）

## ⚠️ 注意事项

### Lingvanex API
- 免费试用可能有次数限制
- 如果超过限制，需要注册付费账号
- 建议作为备用选项

### Reverso Context
- 这是网页翻译服务，不是API
- 需要从HTML中提取翻译结果
- 可能因为网页结构变化而失效
- 建议作为最后备选

### Google Translate 移动端
- 移动端接口可能比桌面版更容易访问
- 需要解析HTML页面
- 如果Google服务无法访问，这个也会失败

## 🔄 使用建议

1. **优先使用前6个API**（原有的API）
2. **新增的3个API作为最后备选**
3. **如果所有API都失败**：
   - 考虑注册LibreTranslate API Key（免费）
   - 或使用DeepL API（免费额度大）
   - 或增加延迟时间，减少并发

## 📝 API调用顺序

脚本会按以下顺序尝试：

```
Google Translate (主) 
  ↓ 失败
MyMemory 
  ↓ 失败
LibreTranslate 
  ↓ 失败
Free Translate 
  ↓ 失败
Google Translate (备用1) 
  ↓ 失败
Google Translate (备用2) 
  ↓ 失败
Lingvanex 
  ↓ 失败
Reverso Context 
  ↓ 失败
Google Translate (移动端) 
  ↓ 失败
返回空字符串
```

## 🎯 成功率预期

- **前6个API**：如果网络正常，应该能成功
- **新增的3个API**：作为最后备选，成功率可能较低
- **总体成功率**：应该比之前有所提升

## 💡 如果仍然失败

如果所有9个API都失败，建议：

1. **检查网络连接**：确保可以访问外网
2. **注册官方API**：
   - LibreTranslate（免费）：https://portal.libretranslate.com
   - DeepL（免费额度大）：https://www.deepl.com/pro-api
3. **增加延迟**：已设置为2秒，可以进一步增加
4. **减少并发**：使用单进程模式
