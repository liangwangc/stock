# 翻译API使用建议

## ⚠️ 重要提示

根据测试结果，**所有免费翻译API都不可用或有限制**：

1. **Google Translate** - 连接超时（可能无法访问）
2. **MyMemory** - 被限流（HTTP 429）
3. **LibreTranslate** - 现在需要API Key
4. **百度/有道翻译** - 非官方接口已失效

## 🎯 推荐解决方案

### 方案1：注册LibreTranslate API Key（最简单）

1. **注册账号**：
   - 访问：https://portal.libretranslate.com
   - 免费注册，获取API Key

2. **修改代码**：
   - 在 `update_word_bank_examples.php` 中添加API Key支持
   - 使用LibreTranslate的官方API

3. **优点**：
   - 免费
   - 开源
   - 翻译质量好
   - 稳定可靠

### 方案2：使用DeepL API（翻译质量最高）

1. **注册账号**：
   - 访问：https://www.deepl.com/pro-api
   - 免费额度：500,000字符/月

2. **优点**：
   - 翻译质量最高
   - 免费额度足够使用

### 方案3：临时解决方案（增加延迟）

如果暂时无法注册API Key，可以：

1. **增加延迟时间**：
   - 已修改为2秒延迟
   - 可以减少API限流

2. **使用单进程**：
   ```bash
   php update_word_bank_examples_parallel.php 1
   ```

3. **分批处理**：
   - 每次处理少量单词
   - 处理完后等待一段时间

## 📋 当前代码状态

- ✅ 已增加延迟时间到2秒
- ✅ 已移除失效的百度和有道接口
- ✅ 已添加Google Translate备用接口
- ⚠️ 免费API仍然可能失败

## 🔄 下一步

1. **立即**：使用当前代码尝试更新（延迟已增加）
2. **推荐**：注册LibreTranslate API Key
3. **长期**：考虑使用官方API获得更好的稳定性
