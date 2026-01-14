# Makefile for Python项目

.PHONY: help install install-dev test lint format clean build publish

# 默认目标
help:
	@echo "可用的命令:"
	@echo "  install      - 安装项目依赖"
	@echo "  install-dev  - 安装开发依赖"
	@echo "  test         - 运行测试"
	@echo "  lint         - 代码风格检查"
	@echo "  format       - 代码格式化"
	@echo "  clean        - 清理临时文件"
	@echo "  build        - 构建项目"
	@echo "  publish      - 发布到PyPI"

# 安装项目依赖
install:
	pip install -r requirements.txt

# 安装开发依赖
install-dev:
	pip install -e ".[dev]"

# 运行测试
test:
	pytest tests/ -v

# 代码风格检查
lint:
	flake8 src/ tests/
	mypy src/

# 代码格式化
format:
	black src/ tests/
	isort src/ tests/

# 清理临时文件
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# 构建项目
build: clean
	python setup.py sdist bdist_wheel

# 发布到PyPI (需要配置)
publish: build
	twine upload dist/*

# 创建虚拟环境
venv:
	python -m venv venv
	@echo "虚拟环境已创建，请运行:"
	@echo "  venv\\Scripts\\activate  # Windows"
	@echo "  source venv/bin/activate  # Linux/Mac"

# 运行主程序
run:
	python src/project_name/main.py

# 检查代码覆盖率
coverage:
	pytest --cov=src --cov-report=html
	@echo "覆盖率报告已生成在 htmlcov/ 目录中" 