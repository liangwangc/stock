# Web应用快速启动指南

## 一、启动步骤

### 1. 安装依赖
```bash
pip install flask flask-socketio werkzeug pymysql plotly
```

或者安装所有依赖：
```bash
pip install -r requirements.txt
```

### 2. 初始化数据库（可选）
```bash
# 在MySQL中创建数据库
CREATE DATABASE IF NOT EXISTS stock_data DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 初始化数据库表
py database/init_database.py
```

如果不想使用数据库，可在 `config_db.py` 中设置 `USE_DATABASE = False`

### 3. 启动Web应用
```bash
# Windows
start_web.bat

# Linux/Mac
chmod +x start_web.sh
./start_web.sh

# 或直接运行
py web_app.py
```

### 4. 访问应用
浏览器打开：**http://localhost:5000**

默认账号：
- 用户名：`admin`
- 密码：`admin123`

## 二、主要功能

### 1. 用户登录
- 访问首页自动跳转到登录页面
- 输入账号密码登录
- 点击"退出"按钮退出登录

### 2. 股票列表（主页面）
- 显示所有股票的预测结果
- **顶部导航栏**：系统标题、设置按钮、退出按钮
- **实时大盘信息栏**：
  - 显示上证指数、深证成指、创业板指
  - 实时显示当前点位、涨跌额、涨跌幅
  - **每秒自动刷新**（局部刷新，不影响页面其他内容）
  - 红色表示上涨，绿色表示下跌
- **搜索功能**：按股票代码或名称搜索
- **股票信息**：每只股票显示预测结果、概率、置信度等
- **操作按钮**：
  - 📊 交互图表（优先显示HTML交互式图表）
  - 📝 文字报告
  - 📄 文字详情
  - 📚 历史预测
  - 🔴 实时监控

### 3. 设置页面
点击导航栏"设置"按钮进入

#### 任务管理
- **全量分析**：分析所有A股
- **部分分析**：分析指定数量的股票（可设置1-1000）
- **实时进度显示**：
  - 进度条（百分比）
  - 已完成/总数
  - 成功数量
  - 失败数量
  - 当前正在分析的股票
  - 实时更新（WebSocket推送）

#### 参数设置（开发中）
- 预测模型参数配置

### 4. 交互式图表
- 使用Plotly生成的HTML交互式图表
- 支持功能：
  - 鼠标悬停查看详细信息
  - 缩放、平移
  - 数据点选择
  - 图例交互
- 如果没有HTML图表，自动显示PNG静态图片

## 三、API接口

### RESTful API
- `GET /api/stocks` - 获取股票列表
- `GET /api/market/index` - 获取大盘指数实时数据（每秒刷新）
- `POST /api/tasks/start` - 启动分析任务
- `GET /api/tasks/<task_id>` - 获取任务状态
- `GET /api/tasks` - 获取所有任务

### WebSocket事件
- `task_started` - 任务启动
- `task_progress` - 任务进度更新
- `task_completed` - 任务完成

## 四、技术特性

1. **实时性**：
   - 大盘信息每秒自动刷新
   - 任务进度实时推送（WebSocket）

2. **交互性**：
   - HTML交互式图表（Plotly）
   - 支持多种交互操作

3. **用户体验**：
   - 友好的Web界面
   - 无需命令行操作
   - 实时反馈

4. **可扩展性**：
   - 模块化设计
   - 易于添加新功能

## 五、注意事项

1. **默认密码**：生产环境请修改默认密码
2. **端口**：默认5000端口，可在 `web_app.py` 修改
3. **数据库**：首次使用需初始化数据库
4. **性能**：全量分析耗时较长，建议先用部分分析测试
5. **网络**：需要访问AkShare API获取数据

## 六、故障排查

### 无法启动
- 检查端口5000是否被占用
- 检查依赖是否安装完整

### 无法登录
- 确认用户名密码：admin/admin123
- 检查浏览器Cookie

### 数据库错误
- 检查MySQL服务是否启动
- 检查 `config_db.py` 配置
- 可设置 `USE_DATABASE = False` 使用CSV模式

### 大盘信息不显示
- 检查网络连接
- 检查交易时间（非交易时间可能无法获取实时数据）

## 七、更新记录

所有更新记录请查看 `CHANGELOG.md`
