# XAMPP 安装指南

## 📋 当前状态

系统提示：**PHP not found!**

这说明您的系统上**未安装 PHP** 或 PHP 未正确配置。

## ✅ 解决方案：安装 XAMPP

XAMPP 是最简单的解决方案，因为它包含：
- ✅ PHP（运行项目）
- ✅ MySQL（数据库）
- ✅ Apache（Web服务器）
- ✅ phpMyAdmin（数据库管理工具）

## 🚀 安装步骤

### 步骤1：下载 XAMPP

1. **访问官网**
   ```
   https://www.apachefriends.org/
   ```

2. **选择版本**
   - 点击 "Download" 按钮
   - 选择 **Windows** 版本
   - 推荐下载 **PHP 8.x** 版本（最新稳定版）

3. **下载文件**
   - 文件大小约 150-200 MB
   - 文件名类似：`xampp-windows-x64-8.x.x-installer.exe`

### 步骤2：安装 XAMPP

1. **运行安装程序**
   - 双击下载的 `.exe` 文件
   - 如果提示用户账户控制，点击"是"

2. **选择组件**
   - ✅ Apache（必需）
   - ✅ MySQL（必需）
   - ✅ PHP（必需）
   - ✅ phpMyAdmin（推荐）
   - ⬜ Tomcat（不需要）
   - ⬜ FileZilla（不需要）
   - ⬜ Mercury（不需要）

3. **选择安装位置**
   - 默认：`C:\xampp\`
   - **建议保持默认**，这样启动脚本才能找到

4. **完成安装**
   - 等待安装完成（约5-10分钟）
   - 安装完成后，**不要立即启动** XAMPP Control Panel

### 步骤3：配置防火墙（如果需要）

- Windows 可能会提示防火墙警告
- 选择"允许访问"（允许 Apache 和 MySQL 通过防火墙）

## 🎯 安装后操作

### 方法1：使用 XAMPP Control Panel（推荐 ⭐⭐⭐⭐⭐）

**这是最可靠的方式！**

1. **打开 XAMPP Control Panel**
   - 开始菜单 → 搜索 "XAMPP"
   - 或直接运行：`C:\xampp\xampp-control.exe`

2. **启动服务**
   - 点击 **Apache** 旁边的 "Start" 按钮
   - 点击 **MySQL** 旁边的 "Start" 按钮
   - 等待两个服务都显示绿色（Running）

3. **复制项目到 XAMPP**
   ```powershell
   # 在 PowerShell 中运行（以管理员身份）
   Copy-Item -Path "d:\wjw_work\yier" -Destination "C:\xampp\htdocs\yier" -Recurse -Force
   ```
   
   或手动复制：
   - 复制整个 `yier` 文件夹
   - 粘贴到 `C:\xampp\htdocs\` 目录下

4. **访问项目**
   ```
   http://localhost/yier/
   ```

### 方法2：使用命令行启动（安装后）

安装 XAMPP 后，可以运行：

```powershell
# 方法1：使用启动脚本
快速启动.bat

# 方法2：直接命令
C:\xampp\php\php.exe -S localhost:8000
```

## 📝 完整启动流程（安装 XAMPP 后）

### 1. 启动 MySQL 服务

**在 XAMPP Control Panel：**
- 点击 MySQL 的 "Start" 按钮
- 等待状态变为绿色（Running）

### 2. 导入数据库

**方法A：使用命令行**
```bash
# 打开命令提示符（CMD）
cd C:\xampp\mysql\bin
mysql.exe -u root -p < "d:\wjw_work\yier\word_app_backup_20260129.sql"
```
输入密码（默认可能为空，直接回车）

**方法B：使用 phpMyAdmin**
1. 在 XAMPP Control Panel 点击 MySQL 的 "Admin" 按钮
2. 打开 phpMyAdmin
3. 点击左侧 "新建" 创建数据库 `word_app`
4. 选择 `word_app` 数据库
5. 点击 "导入" 标签
6. 选择文件：`d:\wjw_work\yier\word_app_backup_20260129.sql`
7. 点击 "执行"

### 3. 配置数据库密码

编辑 `C:\xampp\htdocs\yier\api.php` 第20行：
```php
$db_pass = 'root';  // 如果MySQL密码为空，改为 ''
// 或
$db_pass = '';      // 如果MySQL默认密码为空
```

### 4. 启动 Apache

**在 XAMPP Control Panel：**
- 点击 Apache 的 "Start" 按钮
- 等待状态变为绿色（Running）

### 5. 访问项目

打开浏览器，访问：
```
http://localhost/yier/
```

## 🔍 验证安装

安装 XAMPP 后，验证 PHP 是否可用：

```powershell
# 在 PowerShell 中运行
C:\xampp\php\php.exe --version
```

应该看到类似输出：
```
PHP 8.x.x (cli) ...
```

## ❓ 常见问题

### Q: 安装后还是找不到 PHP？

A: 
1. 检查安装路径是否为 `C:\xampp\`
2. 如果安装在其他位置，修改启动脚本中的路径
3. 或使用 XAMPP Control Panel 方式（最可靠）

### Q: Apache 启动失败？

A:
- 检查端口是否被占用（默认80端口）
- 查看 XAMPP Control Panel 中的错误信息
- 可能需要修改端口或关闭占用端口的程序

### Q: MySQL 启动失败？

A:
- 检查端口3306是否被占用
- 检查是否有其他MySQL实例运行
- 查看 XAMPP 日志文件

### Q: 访问 localhost 显示403错误？

A:
- 确保项目文件在 `C:\xampp\htdocs\yier\`
- 检查文件权限
- 确保 Apache 服务正在运行

## 💡 推荐配置

安装 XAMPP 后，推荐使用 **XAMPP Control Panel** 方式：

1. ✅ 图形界面，操作简单
2. ✅ 自动处理路径和权限
3. ✅ 可以同时管理 Apache 和 MySQL
4. ✅ 包含 phpMyAdmin，方便管理数据库

## 📞 下一步

1. **下载并安装 XAMPP**
2. **使用 XAMPP Control Panel 启动服务**
3. **复制项目到 `C:\xampp\htdocs\yier\`**
4. **导入数据库**
5. **访问 `http://localhost/yier/`**

安装完成后，项目就可以正常运行了！
