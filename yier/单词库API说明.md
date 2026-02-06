# 单词库API使用说明

## 📋 表结构

### word_bank 表

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | INT | 主键，自增 | 1 |
| grade | VARCHAR(20) | 年级（grade1-grade12） | grade1 |
| word | VARCHAR(100) | 单词 | hello |
| pronunciation | VARCHAR(100) | 音标 | /həˈloʊ/ |
| meaning | TEXT | 中文释义 | 你好 |
| example | TEXT | 例句 | Hello, how are you? |
| word_order | INT | 单词顺序 | 1 |
| created_at | TIMESTAMP | 创建时间 | 2026-01-29 10:00:00 |

## 🔌 使用的API

### 1. Free Dictionary API（主要）
- **地址**: `https://api.dictionaryapi.dev/api/v2/entries/en/{word}`
- **特点**: 免费，无需API Key，返回英文释义
- **返回内容**:
  - 音标（phonetic）
  - 英文释义（meanings）
  - 例句（examples）

### 2. 中文单词API（备用）
- **地址**: `https://api.52vmy.cn/api/wl/word?word={word}`
- **特点**: 返回中文释义，更适合中文用户
- **返回内容**:
  - 音标（accent）
  - 中文词义（mean_cn）
  - 例句（sentence）

## 🚀 导入方式

### 方式1：使用内置单词列表（推荐）

运行脚本：
```bash
php import_word_bank.php
```

然后选择要导入的年级：
- 输入 `all` 导入所有年级
- 输入 `1,2,3` 导入指定年级

**内置单词列表包含**：
- 每个年级30个常用单词
- 涵盖基础词汇、日常用语、学科词汇等

### 方式2：从文件导入

**CSV格式**（推荐）：
```csv
word,pronunciation,meaning,example
hello,/həˈloʊ/,你好,Hello, how are you?
good,/ɡʊd/,好的,Have a good day!
```

**纯文本格式**：
```
hello
good
thank
```

运行：
```bash
php import_word_bank_from_file.php words.csv grade1
```

## 📝 使用示例

### 示例1：导入一年级单词

```bash
php import_word_bank.php
# 输入: 1
```

### 示例2：导入多个年级

```bash
php import_word_bank.php
# 输入: 1,2,3
```

### 示例3：从CSV文件导入

创建 `words.csv`:
```csv
apple,/ˈæpl/,苹果,I like apples.
banana,/bəˈnænə/,香蕉,Bananas are yellow.
```

运行：
```bash
php import_word_bank_from_file.php words.csv grade1
```

## ⚙️ 配置说明

### 数据库配置

脚本中的数据库配置需要与 `api.php` 保持一致：

```php
$db_host = 'localhost';
$db_port = 3307;
$db_user = 'root';
$db_pass = 'root';
$db_name = 'word_app';
```

### API请求限制

- 每个请求间隔0.2秒（避免API限流）
- 如果API失败，会尝试备用API
- 如果所有API都失败，单词会被跳过

## 🔍 导入逻辑

1. **检查重复**：如果单词已存在（相同年级+单词），跳过
2. **获取信息**：
   - 优先使用中文API（如果有中文释义）
   - 失败则使用Free Dictionary API
3. **插入数据库**：成功获取信息后插入数据库

## 📊 年级对应

| 年级代码 | 显示名称 | 单词数量（内置） |
|---------|---------|-----------------|
| grade1 | 一年级 | 30 |
| grade2 | 二年级 | 30 |
| grade3 | 三年级 | 30 |
| grade4 | 四年级 | 30 |
| grade5 | 五年级 | 30 |
| grade6 | 六年级 | 30 |
| grade7 | 初一 | 30 |
| grade8 | 初二 | 30 |
| grade9 | 初三 | 30 |
| grade10 | 高一 | 30 |
| grade11 | 高二 | 30 |
| grade12 | 高三 | 30 |

## 💡 注意事项

1. **网络连接**：需要能够访问外网API
2. **API限制**：某些API可能有请求频率限制
3. **数据质量**：API返回的数据质量可能不同，建议导入后检查
4. **中文释义**：Free Dictionary API返回英文释义，如需中文可手动补充
5. **批量导入**：大量单词导入可能需要较长时间

## 🛠️ 故障排除

### 问题1：API请求失败

**原因**：网络问题或API不可用

**解决**：
- 检查网络连接
- 尝试使用备用API
- 手动补充单词信息

### 问题2：数据库连接失败

**原因**：数据库配置不正确

**解决**：
- 检查 `api.php` 中的数据库配置
- 确保数据库服务正在运行
- 检查端口号是否正确（默认3307）

### 问题3：单词导入失败

**原因**：API无该单词数据

**解决**：
- 检查单词拼写是否正确
- 尝试手动添加单词信息
- 使用CSV文件导入，手动填写信息

## 📚 扩展单词库

### 获取更多单词

可以从以下来源获取单词列表：

1. **教育网站**：各年级英语教材单词表
2. **单词书**：如新概念英语、牛津词典等
3. **在线资源**：如Quizlet、Memrise等
4. **API数据**：使用API批量获取

### 批量导入建议

1. **准备CSV文件**：包含单词、音标、词义、例句
2. **分批导入**：每次导入一个年级
3. **验证数据**：导入后检查数据质量
4. **补充信息**：手动补充缺失的音标或例句

---

**提示**：建议先导入少量单词测试，确认功能正常后再批量导入。
