# 项目文档

这个目录包含项目的所有文档。

## 文档结构

- `README.md` - 本文档
- `api.md` - API文档
- `deployment.md` - 部署指南
- `development.md` - 开发指南

## 生成文档

项目使用Sphinx生成文档：

```bash
# 安装Sphinx
pip install sphinx sphinx-rtd-theme

# 生成文档
cd docs
make html

# 查看文档
# 打开 docs/_build/html/index.html
```

## 文档规范

- 使用Markdown格式
- 包含代码示例
- 提供完整的API说明
- 包含使用示例和最佳实践 