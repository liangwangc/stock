========================================
付一二项目 - 启动说明（重要！）
========================================

【当前状态】
系统未安装 PHP，需要先安装 XAMPP

【解决方案】
========================================

方案1: 安装 XAMPP（推荐，最简单）
----------------------------------------
1. 下载 XAMPP
   网址: https://www.apachefriends.org/
   选择: Windows版本，PHP 8.x

2. 安装 XAMPP
   - 运行安装程序
   - 安装到默认位置: C:\xampp\
   - 选择安装: Apache, MySQL, PHP

3. 使用 XAMPP Control Panel 启动
   a) 打开 XAMPP Control Panel
   b) 启动 Apache 和 MySQL
   c) 复制项目到: C:\xampp\htdocs\yier\
   d) 访问: http://localhost/yier/

方案2: 安装后使用命令行
----------------------------------------
安装 XAMPP 后，运行:
  快速启动.bat
或
  C:\xampp\php\php.exe -S localhost:8000

========================================
详细步骤
========================================

【步骤1】安装 XAMPP
----------------------------------------
1. 访问: https://www.apachefriends.org/
2. 下载 Windows 版本
3. 运行安装程序
4. 安装到: C:\xampp\（保持默认）

【步骤2】启动服务
----------------------------------------
1. 打开 XAMPP Control Panel
   (开始菜单 → XAMPP → XAMPP Control Panel)

2. 启动服务
   - 点击 Apache 的 "Start" 按钮
   - 点击 MySQL 的 "Start" 按钮
   - 等待两个都显示绿色（Running）

【步骤3】复制项目
----------------------------------------
方法1: 使用 PowerShell
  Copy-Item -Path "d:\wjw_work\yier" -Destination "C:\xampp\htdocs\yier" -Recurse

方法2: 手动复制
  - 复制整个 yier 文件夹
  - 粘贴到 C:\xampp\htdocs\ 目录

【步骤4】导入数据库
----------------------------------------
方法1: 使用 phpMyAdmin
  - 在 XAMPP Control Panel 点击 MySQL 的 "Admin"
  - 创建数据库: word_app
  - 导入文件: word_app_backup_20260129.sql

方法2: 使用命令行
  cd C:\xampp\mysql\bin
  mysql.exe -u root < "d:\wjw_work\yier\word_app_backup_20260129.sql"

【步骤5】访问项目
----------------------------------------
浏览器打开: http://localhost/yier/

========================================
重要提示
========================================

1. 必须安装 XAMPP 才能运行项目
2. 推荐使用 XAMPP Control Panel 方式（最可靠）
3. 确保 Apache 和 MySQL 服务都启动
4. 确保数据库已导入
5. 检查 api.php 中的数据库密码配置

========================================
需要帮助？
================================--------

查看详细文档:
  - 安装XAMPP指南.md
  - README.md
  - 配置指南.md

========================================
