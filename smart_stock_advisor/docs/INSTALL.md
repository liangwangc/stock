# 安装指南

## 快速开始

### 1. 环境要求

- Python 3.8 或更高版本（推荐 Python 3.10+）
- pip（Python 包管理器）
- MySQL 数据库（可选，用于数据存储）

### 2. 克隆或下载项目

```bash
# 如果使用 Git
git clone <repository_url>
cd smart_stock_advisor

# 或直接下载并解压项目文件
```

### 3. 安装依赖

#### 方法1：使用 requirements.txt（推荐）

```bash
pip install -r requirements.txt
```

#### 方法2：使用国内镜像源（如果网络较慢）

```bash
# 使用清华镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用阿里云镜像
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

#### 方法3：手动安装核心依赖

```bash
pip install pandas numpy akshare requests beautifulsoup4 lxml pymysql flask flask-socketio schedule tqdm python-dateutil
```

### 4. 验证安装

运行依赖检查脚本：

```bash
python check_dependencies.py
```

或手动验证：

```python
python -c "import pandas, numpy, akshare, flask, pymysql; print('核心依赖安装成功！')"
```

### 5. 配置数据库（可选）

如果使用数据库存储功能，需要：

1. 安装并启动 MySQL 数据库
2. 创建数据库（如 `stock_data`）
3. 修改 `config_db.py` 中的数据库配置

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': 'your_password',
    'database': 'stock_data',
    'charset': 'utf8mb4',
}
```

### 6. 启动应用

#### Web 应用

```bash
# Windows
python web_app.py

# 或使用启动脚本
start_web.bat

# Linux/Mac
python web_app.py
# 或
chmod +x start_web.sh
./start_web.sh
```

#### 命令行应用

```bash
python main.py
```

## 详细依赖说明

请参考 [依赖安装指南](./依赖安装指南.md) 了解：
- 所有依赖包的详细说明
- 按功能分类的安装指南
- 常见问题解决方案

## 故障排除

### 问题1：pip 命令不存在

**解决方案**：
```bash
# Windows
python -m pip install -r requirements.txt

# Linux/Mac
python3 -m pip install -r requirements.txt
```

### 问题2：权限错误

**解决方案**：
```bash
# Linux/Mac - 使用 sudo（不推荐）
sudo pip install -r requirements.txt

# 推荐：使用用户安装
pip install --user -r requirements.txt

# 或使用虚拟环境（最佳实践）
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 问题3：某些包安装失败

**解决方案**：
1. 升级 pip：`pip install --upgrade pip`
2. 单独安装失败的包：`pip install <package_name>`
3. 查看详细错误信息：`pip install <package_name> -v`

### 问题4：数据库连接失败

**解决方案**：
1. 确认 MySQL 服务已启动
2. 检查 `config_db.py` 中的配置是否正确
3. 确认数据库用户有足够权限
4. 检查防火墙设置

## 下一步

安装完成后，请查看：
- [使用说明](../README.md)
- [快速开始指南](../快速开始.bat)
- [Web 应用启动说明](../Web应用启动说明.md)
