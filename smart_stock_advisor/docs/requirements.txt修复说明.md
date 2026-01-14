# requirements.txt 修复说明

## 问题描述

执行 `pip install -r requirements.txt` 时报错：

```
UnicodeDecodeError: 'gbk' codec can't decode byte 0xa3 in position 135: illegal multibyte sequence
```

## 问题原因

1. **编码问题**：`requirements.txt` 文件包含中文注释，Windows 系统默认使用 GBK 编码，pip 在读取 UTF-8 编码的中文时无法正确解码。

2. **版本错误**：`schedule` 包的版本要求错误（写成了 `>=5.3.0`，实际最高版本是 `1.2.2`）。

## 解决方案

### 1. 移除中文注释

将 `requirements.txt` 文件中的中文注释改为英文注释，确保文件使用纯 ASCII 字符，避免编码问题。

**修改前：**
```
# ========== 核心依赖（必需） ==========
pandas>=2.0.0              # 数据处理和分析
```

**修改后：**
```
# ========== Core Dependencies (Required) ==========
pandas>=2.0.0
```

### 2. 修正版本号

将 `schedule` 包的版本要求从 `>=5.3.0` 改为 `>=1.2.0`。

**修改前：**
```
schedule>=5.3.0
```

**修改后：**
```
schedule>=1.2.0
```

## 验证

修复后，可以正常执行：

```bash
pip install -r requirements.txt
```

或使用国内镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 最佳实践

1. **避免在 requirements.txt 中使用非 ASCII 字符**：使用英文注释，确保跨平台兼容性。

2. **验证版本号**：在添加依赖时，确认包的版本号是否正确。

3. **使用虚拟环境**：推荐使用虚拟环境安装依赖，避免污染系统环境。

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 相关文件

- `smart_stock_advisor/requirements.txt` - 已修复的依赖文件
- `smart_stock_advisor/docs/依赖安装指南.md` - 详细的安装指南

---

**修复日期**：2024-01-13  
**修复内容**：移除中文注释，修正 schedule 版本号
