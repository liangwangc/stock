# 股票预测系统 Web 应用使用说明

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包括：
- Flask（Web框架）
- Flask-SocketIO（WebSocket支持）
- Plotly（交互式图表）
- pymysql（MySQL数据库）
- akshare（股票数据源）
- 其他项目依赖

### 2. 初始化数据库（如果使用数据库模式）

```bash
# 创建数据库（在MySQL中执行）
CREATE DATABASE IF NOT EXISTS stock_data DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 初始化数据库表
py database/init_database.py
```

### 3. 配置数据库（可选）

编辑 `config_db.py` 文件，修改数据库连接信息：
- 如果不需要数据库，设置 `USE_DATABASE = False`（使用CSV模式）

### 4. 启动Web应用

```bash
# Windows
start_web.bat

# Linux/Mac
chmod +x start_web.sh
./start_web.sh

# 或直接运行
py web_app.py
```

### 5. 访问应用

浏览器打开：**http://localhost:5000**

默认账号：
- 用户名：`admin`
- 密码：`admin123`

## 功能说明

### 1. 用户登录
- 访问首页会自动跳转到登录页面
- 输入用户名和密码登录
- 支持退出登录功能

### 2. 股票列表页面（主页面）
- 显示所有股票的预测结果
- 顶部导航栏：系统标题、设置按钮、退出按钮
- 实时大盘信息栏：显示上证指数、深证成指、创业板指（每秒自动刷新）
- 搜索功能：支持按股票代码或名称搜索
- 每只股票显示：
  - 股票代码和名称
  - 当前价格
  - 预测方向（上涨/下跌/震荡）
  - 上涨/下跌概率
  - 操作按钮：
    - 📊 交互图表（优先显示HTML交互式图表，支持缩放、悬停等操作）
    - 📝 文字报告
    - 📄 文字详情
    - 📚 历史预测
    - 🔴 实时监控

### 3. 设置页面
访问方式：点击导航栏"设置"按钮

#### 任务管理
- **全量分析**：分析所有A股（按成交额排序）
- **部分分析**：分析指定数量的股票
  - 可设置分析数量（1-1000）
- **任务进度显示**：
  - 进度条（百分比）
  - 当前进度（已完成/总数）
  - 成功数量
  - 失败数量
  - 当前正在分析的股票代码
  - 实时更新（使用WebSocket）

#### 参数设置（开发中）
- 预测模型参数配置
- 其他系统参数

### 4. 实时大盘信息
- 在主页面顶部显示
- 显示主要指数：
  - 上证指数（sh000001）
  - 深证成指（sz399001）
  - 创业板指（sz399006）
- 实时显示：
  - 当前点位
  - 涨跌额
  - 涨跌幅（百分比）
- 每秒自动刷新（局部刷新，不影响页面其他内容）
- 颜色区分：
  - 红色：上涨
  - 绿色：下跌

### 5. 交互式图表
- 优先使用HTML交互式图表（Plotly）
- 支持功能：
  - 鼠标悬停查看详细信息
  - 缩放、平移操作
  - 数据点选择
  - 图例交互
- 如果HTML图表不存在，自动回退到PNG静态图片

## API接口

### RESTful API

- `GET /api/stocks` - 获取股票列表
- `GET /api/market/index` - 获取大盘指数实时数据
- `POST /api/tasks/start` - 启动分析任务
  - Body: `{"type": "all" | "limited", "limit": 50}`
- `GET /api/tasks/<task_id>` - 获取任务状态
- `GET /api/tasks` - 获取所有任务列表

### WebSocket事件

- `task_started` - 任务启动事件
- `task_progress` - 任务进度更新事件
- `task_completed` - 任务完成事件

## 目录结构

```
smart_stock_advisor/
├── web_app.py              # Flask Web应用主文件
├── templates/              # HTML模板目录
│   ├── login.html          # 登录页面
│   └── settings.html       # 设置页面
├── static/                 # 静态文件目录
│   └── common.css          # 通用样式
├── stock_list.html         # 股票列表页面（主页面）
├── reports/                # 报告文件目录
│   ├── *.png              # PNG图形报告
│   ├── *_interactive.html # 交互式图表
│   └── *_full_report.html # 完整HTML报告
└── database/               # 数据库相关
    ├── init_database.sql   # 数据库初始化SQL
    └── init_database.py    # 数据库初始化脚本
```

## 技术架构

- **后端**：Flask + Flask-SocketIO
- **前端**：HTML + CSS + JavaScript + Plotly
- **实时通信**：WebSocket（Socket.IO）
- **数据库**：MySQL（可选，支持回退到CSV）
- **数据源**：AkShare

## 注意事项

1. **默认账号**：生产环境请修改默认密码
2. **数据库**：首次使用需要初始化数据库表
3. **端口**：默认端口5000，可在 `web_app.py` 中修改
4. **性能**：全量分析可能需要较长时间，建议使用部分分析测试
5. **数据更新**：大盘信息每秒刷新，股票列表每30秒刷新

## 故障排查

### 1. 无法访问
- 检查端口5000是否被占用
- 检查防火墙设置

### 2. 登录失败
- 确认用户名和密码正确（默认：admin/admin123）
- 检查浏览器Cookie是否被禁用

### 3. 数据库连接失败
- 检查MySQL服务是否启动
- 检查 `config_db.py` 中的配置是否正确
- 可设置 `USE_DATABASE = False` 使用CSV模式

### 4. 任务无法启动
- 检查是否有足够的系统资源
- 查看控制台日志中的错误信息

### 5. 大盘信息不显示
- 检查网络连接（需要访问AkShare API）
- 检查交易时间（非交易时间可能无法获取实时数据）

## 开发说明

### 添加新功能
1. 在 `web_app.py` 中添加路由处理
2. 在 `templates/` 目录下添加HTML模板
3. 在 `static/` 目录下添加CSS/JS文件

### 修改样式
- 通用样式：`static/common.css`
- 页面特定样式：各HTML文件中的 `<style>` 标签

## 更新日志

详细的更新记录请查看 `CHANGELOG.md` 文件。
