# DashScope API 密钥配置说明

**DashScope** 是阿里云的大模型服务平台，提供通义千问（Qwen）等模型的API服务。

---

## 一、获取 API 密钥

### 步骤1：登录阿里云并开通服务

1. **访问阿里云官网**
   - 网址：https://www.aliyun.com/
   - 如果没有账号，需要先注册（需要实名认证）

2. **开通 DashScope 服务**
   - 登录后，进入控制台
   - 搜索 "DashScope" 或 "通义千问API" 或 "模型服务灵积"
   - 点击"立即开通"或"免费试用"
   - 完成服务开通（可能需要实名认证）

### 步骤2：创建 API 密钥

1. **进入密钥管理页面**
   - 登录阿里云控制台
   - 点击右上角头像 → **AccessKey管理**
   - 或直接访问：https://usercenter.console.aliyun.com/

2. **创建 API 密钥**
   - 点击"创建新的API密钥"或"创建AccessKey"
   - 完成安全验证（如手机验证码）
   - 系统会生成密钥字符串，格式类似：`dashscope-xxxxxxxxxxxxxxxxxxxx`
   - **⚠️ 重要：立即复制并保存到安全地方**（密钥只显示一次，丢失需重新生成）

### 步骤3：查看密钥（如果已创建）

如果之前已经创建过密钥：
- 进入 AccessKey 管理页面
- 可以看到已有的密钥列表
- 如果忘记密钥，需要重新创建（旧密钥会失效）

---

## 二、配置 API 密钥

### 方式1：Windows 环境变量配置（推荐）

#### 方法A：通过系统设置（永久配置）

1. **打开环境变量设置**
   - 按 `Win + Q` 搜索"编辑系统环境变量"
   - 或：右键"此电脑" → "属性" → "高级系统设置" → "环境变量"

2. **添加环境变量**
   - 在"用户变量"或"系统变量"中点击"新建"
   - **变量名**：`DASHSCOPE_API_KEY`
   - **变量值**：你的密钥（例如：`dashscope-xxxxxxxxxxxxxxxxxxxx`）
   - 点击"确定"保存

3. **验证配置**
   - 打开新的 PowerShell 或 CMD 窗口
   - 输入：`echo $env:DASHSCOPE_API_KEY`（PowerShell）
   - 或：`echo %DASHSCOPE_API_KEY%`（CMD）
   - 应该显示你的密钥

#### 方法B：通过 PowerShell（当前会话）

```powershell
# 当前会话有效（关闭窗口后失效）
$env:DASHSCOPE_API_KEY = "dashscope-你的密钥"
```

#### 方法C：通过 CMD（永久配置）

```cmd
# 永久设置（需要重启终端）
setx DASHSCOPE_API_KEY "dashscope-你的密钥"
```

**注意**：使用 `setx` 后需要关闭并重新打开 CMD/PowerShell 才能生效。

---

### 方式2：配置文件方式（可选）

如果不想使用环境变量，可以修改代码支持从配置文件读取（需要修改代码）。

---

## 三、验证配置

### 方法1：使用检查脚本

运行我们提供的检查脚本：

```powershell
cd d:\wjw_work\smart_stock_advisor
py scripts/check_api_keys.py
```

如果配置成功，会显示：
```
DASHSCOPE_API_KEY: dashscope-xxxx...xxxx [已配置]
```

### 方法2：直接测试

启动 LLM 分析，如果配置成功，会自动使用 API 模式（速度更快）。

---

## 四、使用 API 模式的优势

配置了 `DASHSCOPE_API_KEY` 后，LLM 分析会自动使用 API 模式，具有以下优势：

| 项目 | 本地CPU模式 | API模式 |
|------|------------|---------|
| **速度** | ~12-15秒/条 | ~2-5秒/条 |
| **资源占用** | 占用CPU和内存 | 不占用本地资源 |
| **稳定性** | 受硬件限制 | 云端稳定 |
| **成本** | 免费（本地） | 按调用量收费 |

### 预计性能提升

- **508条新闻分析时间**：
  - 本地CPU模式：~1小时40分钟 - 2小时10分钟
  - API模式：**~17-42分钟**（提升3-6倍）

---

## 五、费用说明

### 免费额度

- 新用户通常有免费额度（具体以阿里云官网为准）
- 建议先查看 DashScope 的定价页面：https://help.aliyun.com/zh/model-studio/pricing

### 计费方式

- 按调用量计费（每1000个token）
- 不同模型价格不同
- Qwen3-4B 相对较便宜

### 成本估算

- 每条新闻约消耗 500-1000 tokens（输入+输出）
- 508条新闻约消耗 25-50万 tokens
- 具体费用请查看阿里云定价页面

---

## 六、常见问题

### Q1: 密钥格式是什么？

A: DashScope API 密钥格式通常是：`dashscope-` 开头，后面跟着一串字符，例如：
```
dashscope-xxxxxxxxxxxxxxxxxxxx
```

### Q2: 密钥丢失了怎么办？

A: 需要重新创建新的 API 密钥。旧密钥会失效，建议立即删除旧密钥。

### Q3: 配置后还是使用本地模式？

A: 检查以下几点：
1. 环境变量是否正确配置（重启终端后验证）
2. 密钥格式是否正确
3. 查看日志输出，看是否有错误信息

### Q4: API 调用失败怎么办？

A: 可能的原因：
1. 密钥错误或已过期
2. 账户余额不足
3. 网络连接问题
4. API 服务暂时不可用

查看错误日志可以获取更详细的错误信息。

---

## 七、安全提示

1. **不要泄露密钥**：API 密钥等同于账户密码，不要分享给他人
2. **不要提交到代码仓库**：不要在代码中硬编码密钥，使用环境变量
3. **定期轮换**：建议定期更换密钥以保证安全
4. **限制权限**：如果可能，使用最小权限原则

---

## 八、相关链接

- **阿里云 DashScope 官网**：https://dashscope.aliyun.com/
- **API 文档**：https://help.aliyun.com/zh/model-studio/
- **定价页面**：https://help.aliyun.com/zh/model-studio/pricing
- **密钥管理**：https://usercenter.console.aliyun.com/

---

## 九、快速开始

1. **获取密钥**：登录阿里云 → AccessKey管理 → 创建新密钥
2. **配置环境变量**：`DASHSCOPE_API_KEY = "你的密钥"`
3. **验证配置**：运行 `py scripts/check_api_keys.py`
4. **开始使用**：启动 LLM 分析，自动使用 API 模式

---

**配置完成后，LLM 分析速度将提升 3-6 倍！** 🚀
