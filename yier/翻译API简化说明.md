# 翻译API简化说明

## 📋 修改内容

根据要求，**已删除所有其他翻译API，只保留百度和有道翻译API**。

## 🔄 当前使用的翻译API

### 1. 百度翻译（方法1，优先）
- **URL**: `https://fanyi.baidu.com/transapi`
- **类型**: 非官方接口（无需API Key）
- **优点**: 中文翻译质量好
- **缺点**: 非官方接口，可能随时失效
- **状态**: ✅ 已保留

### 2. 有道翻译（方法2，备用）
- **URL**: `https://fanyi.youdao.com/translate_o`
- **类型**: 非官方接口（无需API Key）
- **优点**: 中文翻译质量好
- **缺点**: 非官方接口，可能随时失效，需要签名算法
- **状态**: ✅ 已保留

## 🗑️ 已删除的API

以下API已从代码中删除：

1. ❌ Google Translate（所有变体）
2. ❌ MyMemory Translation API
3. ❌ LibreTranslate
4. ❌ Free Translate API
5. ❌ Lingvanex API
6. ❌ Reverso Context
7. ❌ Google Translate 移动端

## 📝 修改的文件

以下文件已更新，只保留百度和有道翻译API：

1. ✅ `update_word_bank_examples.php`
2. ✅ `import_all_grades.php`
3. ✅ `import_word_bank.php`

## ⚠️ 注意事项

### 百度翻译
- 如果返回 `errno: 997` 或 `errno: 1022`，表示接口已失效
- 需要检查接口是否仍然可用

### 有道翻译
- 如果返回 `errorCode: 50`，表示接口需要验证，已失效
- 需要检查接口是否仍然可用

## 🔧 工作流程

1. **优先尝试百度翻译**
   - 如果成功 → 返回翻译结果
   - 如果失败 → 等待0.5秒后尝试有道翻译

2. **备用尝试有道翻译**
   - 如果成功 → 返回翻译结果
   - 如果失败 → 返回空字符串

## 💡 如果两个API都失效

如果百度和有道的非官方接口都失效，建议：

1. **使用官方API**：
   - 百度翻译API：https://fanyi-api.baidu.com/（免费200万字符/月）
   - 有道翻译API：https://ai.youdao.com/（免费100万字符/月）

2. **修改代码使用官方API**：
   - 需要注册账号获取API Key
   - 修改 `translateToChinese` 函数使用官方API

## 📊 当前状态

- ✅ 只保留百度和有道翻译API
- ✅ 已删除其他所有翻译API
- ✅ 代码已简化
- ⚠️ 如果两个API都失效，翻译功能将无法使用
