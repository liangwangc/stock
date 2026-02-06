# Tushare网页登录功能说明

**日期**：2026-01-16  
**功能**：支持使用账号密码登录Tushare后从网页获取新闻

---

## 一、功能概述

新增了Tushare网页登录功能，支持使用账号密码登录后从以下页面获取新闻：

1. **第一财经** - https://tushare.pro/news/yicai
2. **凤凰财经** - https://tushare.pro/news/fenghuang
3. **同花顺** - https://tushare.pro/news/10jqka
4. **金融界** - https://tushare.pro/news/jinrongjie
5. **新浪财经** - https://tushare.pro/news/sina
6. **云财经** - https://tushare.pro/news/yuncaijing
7. **东方财富** - https://tushare.pro/news/eastmoney

---

## 二、配置方法

### 2.1 在config.py中配置

在 `smart_stock_advisor/config.py` 中添加：

```python
# Tushare网页登录配置（可选）
TUSHARE_USERNAME = "your_username"  # 您的Tushare账号（手机或邮箱）
TUSHARE_PASSWORD = "your_password"  # 您的Tushare密码
```

### 2.2 自动启用

配置后，系统会自动：
1. 尝试使用账号密码登录
2. 如果登录成功，启用 `TushareWebNewsSource`
3. 如果登录失败，自动禁用（不影响其他新闻源）

---

## 三、验证码处理

### 3.1 自动识别（推荐）

如果安装了 `pytesseract`，系统会自动识别验证码：

```bash
pip install pytesseract pillow
```

**注意**：还需要安装 Tesseract OCR：
- Windows: 下载安装包 https://github.com/UB-Mannheim/tesseract/wiki
- 或使用: `choco install tesseract`

### 3.2 手动输入

如果没有安装OCR工具，系统会：
1. 保存验证码图片到 `smart_stock_advisor/captcha_temp.png`
2. 记录日志提示查看图片
3. 需要手动输入验证码（当前版本需要修改代码支持）

---

## 四、使用方法

### 4.1 自动使用（推荐）

配置账号密码后，系统会自动使用：

```python
from quant_trading_platform.news.unified_news_source import UnifiedNewsSource

# 自动从config.py读取账号密码
unified = UnifiedNewsSource()
news = unified.get_market_news(limit=20)
```

### 4.2 手动指定

```python
from quant_trading_platform.news.tushare_web_news_source import TushareWebNewsSource

source = TushareWebNewsSource(username="your_username", password="your_password")
if source._logged_in:
    news = source.get_market_news(limit=20)
```

---

## 五、登录流程

1. **访问登录页面**：获取 `_xsrf` token
2. **获取验证码**：下载验证码图片
3. **识别验证码**：
   - 如果安装了OCR，自动识别
   - 否则保存图片供手动输入
4. **提交登录**：发送登录请求
5. **验证登录**：检查登录状态
6. **重试机制**：如果验证码错误，自动重试（最多3次）

---

## 六、注意事项

### 6.1 安全性

- ⚠️ **密码安全**：密码存储在配置文件中，请妥善保管
- ⚠️ **不要提交**：确保 `config.py` 在 `.gitignore` 中，不要提交到版本控制

### 6.2 验证码

- 验证码识别可能不准确，如果登录失败，可以：
  1. 安装OCR工具提高识别率
  2. 手动查看验证码图片并输入
  3. 多次重试（代码会自动重试）

### 6.3 登录状态

- 登录状态会保存在 `Session` 中
- 如果登录过期，需要重新登录
- 建议定期检查登录状态

---

## 七、测试

### 7.1 测试脚本

运行测试脚本：

```bash
python scripts/test_tushare_login_with_captcha.py
```

脚本会：
1. 提示输入账号密码
2. 自动获取验证码图片
3. 提示手动输入验证码
4. 测试登录和获取新闻

### 7.2 验证功能

登录成功后，应该能够：
- ✅ 访问需要登录的新闻页面
- ✅ 获取新闻数据
- ✅ 解析新闻内容

---

## 八、与API方式的对比

### 8.1 网页方式（TushareWebNewsSource）

**优势**：
- ✅ 可以获取多个新闻源的数据
- ✅ 不受API频率限制影响

**劣势**：
- ❌ 需要处理登录和验证码
- ❌ 页面结构可能变化
- ❌ 需要维护登录状态

### 8.2 API方式（TuShareNewsSource）

**优势**：
- ✅ 稳定可靠
- ✅ 数据格式规范
- ✅ 无需处理登录

**劣势**：
- ❌ 受API频率限制（每分钟1次）
- ❌ 需要足够的积分等级

### 8.3 推荐

**建议同时使用两种方式**：
- 主要使用API方式（稳定可靠）
- 网页方式作为补充（不受频率限制）

---

## 九、故障排除

### 9.1 登录失败

**可能原因**：
1. 账号密码错误
2. 验证码识别错误
3. 网络问题
4. Tushare网站变更

**解决方法**：
1. 检查账号密码是否正确
2. 手动查看验证码图片并输入
3. 检查网络连接
4. 查看日志了解详细错误

### 9.2 无法获取新闻

**可能原因**：
1. 登录状态过期
2. 页面结构变化
3. 该时间段内没有新闻

**解决方法**：
1. 重新登录
2. 检查页面结构是否变化
3. 调整时间范围

---

## 十、总结

### 10.1 功能状态

- ✅ 登录功能已实现
- ✅ 支持自动OCR识别验证码
- ✅ 支持手动输入验证码
- ✅ 自动重试机制
- ✅ 已集成到统一新闻源

### 10.2 使用建议

1. **配置账号密码**：在 `config.py` 中配置
2. **安装OCR工具**（可选）：提高验证码识别率
3. **测试登录**：使用测试脚本验证登录功能
4. **监控日志**：关注登录状态和错误信息

---

**最后更新**：2026-01-16
