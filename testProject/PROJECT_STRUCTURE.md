# 稽核档案管理系统 - 项目结构说明

## 📁 项目目录结构

```
testProject/
├── 📁 audit_system/           # 核心系统模块
│   ├── __init__.py
│   ├── auth.py                # 认证和权限管理
│   ├── database.py            # 数据库操作
│   ├── database_schema.sql    # 数据库表结构
│   ├── init_system.py         # 系统初始化
│   ├── main.py                # 命令行主程序
│   └── models.py              # 数据模型
├── 📁 scripts/                # Python脚本文件
│   ├── 📁 main/              # 主要应用脚本
│   │   ├── web_app.py        # Web应用主程序
│   │   └── run.py            # 启动脚本
│   ├── 📁 database/          # 数据库相关脚本
│   │   ├── config.py         # 数据库配置
│   │   ├── database.py       # 数据库管理器
│   │   ├── mysql_database.py # MySQL数据库操作
│   │   ├── create_tables.py  # 创建数据表
│   │   ├── recreate_tables.py # 重建数据表
│   │   ├── fix_*.py          # 数据库修复脚本
│   │   ├── check_*.py        # 数据库检查脚本
│   │   └── clean_database.py # 清理数据库
│   └── 📁 test/              # 测试脚本
│       ├── test_log_details.py      # 日志详情测试
│       ├── test_template.py         # 模板测试
│       ├── test_edit_functionality.py # 编辑功能测试
│       └── test_user_management.py  # 用户管理测试
├── 📁 sql/                   # SQL脚本文件
│   ├── create_tables_manual.sql     # 手动创建表
│   ├── fix_database_*.sql          # 数据库修复脚本
│   ├── add_attachment_fields.sql   # 添加附件字段
│   └── add_notes_field.sql         # 添加备注字段
├── 📁 config/                # 配置文件
│   ├── requirements.txt      # Python依赖
│   ├── pyproject.toml       # 项目配置
│   ├── Makefile             # 构建脚本
│   ├── env.example          # 环境变量示例
│   └── .gitignore           # Git忽略文件
├── 📁 docs/                  # 文档文件
│   ├── README.md            # 项目说明
│   ├── USER_MANAGEMENT_README.md # 用户管理说明
│   ├── SOLUTION_README.md   # 解决方案说明
│   └── EDIT_FIX_README.md   # 编辑修复说明
├── 📁 templates/             # HTML模板文件
│   ├── base.html            # 基础模板
│   ├── login.html           # 登录页面
│   ├── dashboard.html       # 仪表板
│   ├── files.html           # 档案管理
│   ├── users.html           # 用户管理
│   ├── logs.html            # 操作日志
│   └── ...                  # 其他模板
├── 📁 uploads/              # 文件上传目录
├── 📁 tests/                # 测试目录
├── 📁 src/                  # 源代码目录
├── 📁 __pycache__/          # Python缓存
├── start.py                  # 项目根目录启动脚本
├── PROJECT_STRUCTURE.md      # 项目结构说明（本文件）
└── README.md                 # 项目说明
```

## 🚀 启动方式

### 方式1：使用项目根目录启动脚本（推荐）
```bash
cd testProject
python start.py
```

### 方式2：使用scripts目录下的启动脚本
```bash
cd testProject/scripts/main
python run.py
```

### 方式3：直接运行Web应用
```bash
cd testProject/scripts/main
python web_app.py
```

## 🔧 主要功能模块

### 1. 核心系统 (audit_system/)
- **认证管理**: 用户登录、权限控制
- **数据库操作**: 数据增删改查
- **数据模型**: 档案、用户、部门等实体

### 2. Web应用 (scripts/main/)
- **Web界面**: Flask框架的Web应用
- **用户管理**: 用户增删改查
- **档案管理**: 档案的增删改查
- **操作日志**: 系统操作记录

### 3. 数据库管理 (scripts/database/)
- **数据库配置**: 连接配置
- **表结构管理**: 创建、修改、重建表
- **数据修复**: 修复数据问题
- **数据清理**: 清理无用数据

### 4. 测试脚本 (scripts/test/)
- **功能测试**: 测试各项功能
- **数据库测试**: 测试数据库操作
- **用户管理测试**: 测试用户管理功能

## 📝 注意事项

1. **路径引用**: 所有脚本文件都已修复路径引用问题
2. **依赖安装**: 确保已安装requirements.txt中的依赖
3. **数据库配置**: 在config.py中配置正确的数据库连接信息
4. **权限要求**: 某些功能需要管理员权限

## 🔍 故障排除

### 常见问题
1. **模块导入错误**: 检查Python路径设置
2. **数据库连接失败**: 检查数据库配置和网络连接
3. **模板文件找不到**: 检查templates目录路径

### 日志查看
- 系统日志: 访问Web界面的操作日志页面
- 错误日志: 查看控制台输出

## 📞 技术支持

如有问题，请检查：
1. Python版本兼容性
2. 数据库连接配置
3. 依赖包安装状态
4. 文件路径和权限
