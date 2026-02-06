# PHP 安装指南

## ❌ 当前问题

系统提示：`无法将"php"项识别为 cmdlet、函数、脚本文件或可运行程序的名称`

这说明 PHP 未安装或未添加到系统 PATH。

## ✅ 解决方案（3选1）

### 方案1：安装 XAMPP（推荐 ⭐⭐⭐⭐⭐）

**优点：**
- 一键安装，包含 PHP + MySQL + Apache
- 图形界面管理，操作简单
- 适合初学者

**步骤：**

1. **下载 XAMPP**
   - 访问：https://www.apachefriends.org/
   - 选择 Windows 版本下载
   - 推荐下载 PHP 8.x 版本

2. **安装 XAMPP**
   - 运行安装程序
   - 安装到默认位置：`C:\xampp\`
   - 安装过程中选择安装 Apache、MySQL、PHP

3. **启动项目**
   ```bash
   # 方法1：使用完整路径
   C:\xampp\php\php.exe -S localhost:8000
   
   # 方法2：双击运行
   查找PHP并启动.bat
   ```

4. **或使用 XAMPP Control Panel**
   - 打开 XAMPP Control Panel
   - 启动 Apache 和 MySQL
   - 将项目复制到 `C:\xampp\htdocs\yier\`
   - 访问：`http://localhost/yier/`

---

### 方案2：安装 WAMP

**步骤：**

1. **下载 WAMP**
   - 访问：https://www.wampserver.com/
   - 下载适合的版本（32位或64位）

2. **安装 WAMP**
   - 运行安装程序
   - 安装到默认位置：`C:\wamp64\`

3. **启动项目**
   ```bash
   # 使用完整路径（版本号可能不同）
   C:\wamp64\bin\php\php7.4.33\php.exe -S localhost:8000
   
   # 或双击运行
   查找PHP并启动.bat
   ```

---

### 方案3：单独安装 PHP

**步骤：**

1. **下载 PHP**
   - 访问：https://windows.php.net/download/
   - 选择 **Thread Safe** 版本
   - 选择 **ZIP** 格式下载
   - 推荐 PHP 7.4 或 8.x

2. **解压 PHP**
   - 解压到 `C:\php\`
   - 确保 `php.exe` 在 `C:\php\php.exe`

3. **添加到系统 PATH**
   - 右键"此电脑" → "属性"
   - "高级系统设置" → "环境变量"
   - 在"系统变量"中找到 `Path`
   - 点击"编辑" → "新建"
   - 添加：`C:\php`
   - 确定保存

4. **验证安装**
   ```bash
   php --version
   ```

5. **启动项目**
   ```bash
   cd d:\wjw_work\yier
   php -S localhost:8000
   ```

---

## 🚀 快速启动（安装后）

### 如果安装了 XAMPP：

**方法1：使用批处理文件**
```bash
双击运行: 查找PHP并启动.bat
```

**方法2：手动启动**
```bash
C:\xampp\php\php.exe -S localhost:8000
```

**方法3：使用 XAMPP Control Panel**
1. 打开 XAMPP Control Panel
2. 启动 Apache 和 MySQL
3. 将项目复制到 `C:\xampp\htdocs\yier\`
4. 访问：`http://localhost/yier/`

### 如果安装了 WAMP：

**方法1：使用批处理文件**
```bash
双击运行: 查找PHP并启动.bat
```

**方法2：手动启动**
```bash
# 找到你的 PHP 版本路径，例如：
C:\wamp64\bin\php\php7.4.33\php.exe -S localhost:8000
```

### 如果单独安装了 PHP：

```bash
cd d:\wjw_work\yier
php -S localhost:8000
```

---

## 📋 安装后检查清单

- [ ] PHP 已安装
- [ ] 可以运行 `php --version`（如果添加到PATH）
- [ ] MySQL 服务已启动（XAMPP/WAMP会自动安装）
- [ ] 数据库已导入（`word_app_backup_20260129.sql`）
- [ ] `api.php` 中的密码已配置正确

---

## 🎯 推荐方案

**强烈推荐使用 XAMPP**，因为：

1. ✅ 一键安装，包含所有必需组件
2. ✅ 图形界面，操作简单
3. ✅ 自动配置，无需手动设置
4. ✅ 包含 MySQL，数据库管理方便
5. ✅ 包含 phpMyAdmin，可视化数据库管理

---

## 💡 安装后下一步

1. **启动 MySQL 服务**
   - XAMPP: 在 Control Panel 启动 MySQL
   - WAMP: 确保 MySQL 服务运行

2. **导入数据库**
   ```bash
   mysql -u root -p < word_app_backup_20260129.sql
   ```

3. **配置数据库密码**
   - 编辑 `api.php` 第20行
   - 修改：`$db_pass = '你的密码';`

4. **启动项目**
   - 运行 `查找PHP并启动.bat`
   - 或使用 XAMPP Control Panel

5. **访问项目**
   - `http://localhost:8000`（PHP内置服务器）
   - 或 `http://localhost/yier/`（XAMPP）

---

## ❓ 常见问题

### Q: 安装 XAMPP 后还是找不到 PHP？

A: 使用完整路径启动：
```bash
C:\xampp\php\php.exe -S localhost:8000
```

或运行 `查找PHP并启动.bat`，它会自动查找。

### Q: 端口 8000 被占用？

A: 使用其他端口：
```bash
php -S localhost:8080
```

### Q: MySQL 服务启动失败？

A: 
- 检查端口是否被占用（默认3306）
- 检查是否有其他 MySQL 实例运行
- 查看 XAMPP/WAMP 的错误日志

---

**安装完成后，运行 `查找PHP并启动.bat` 即可自动启动项目！**
