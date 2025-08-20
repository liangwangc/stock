# Python项目

这是一个标准的Python项目模板，包含了完整的项目结构和配置。

## 项目结构

```
project/
├── src/                    # 源代码目录
│   └── project_name/      # 主包目录
│       ├── __init__.py    # 包初始化文件
│       └── main.py        # 主程序入口
├── tests/                 # 测试目录
│   ├── __init__.py
│   └── test_main.py      # 测试文件
├── docs/                  # 文档目录
├── requirements.txt       # 项目依赖
├── setup.py              # 安装配置
├── .env.example          # 环境变量示例
├── .gitignore            # Git忽略文件
├── README.md             # 项目说明
└── Makefile              # 构建脚本
```

## 安装

1. 克隆项目
```bash
git clone <repository-url>
cd project
```

2. 创建虚拟环境
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

运行主程序：
```bash
python src/project_name/main.py
```

运行测试：
```bash
pytest
```

代码格式化：
```bash
black src/ tests/
```

代码检查：
```bash
flake8 src/ tests/
```

## 开发

- 使用 `black` 进行代码格式化
- 使用 `flake8` 进行代码风格检查
- 使用 `mypy` 进行类型检查
- 使用 `pytest` 进行测试

## 许可证

MIT License 