# CMD执行说明

## ⚠️ 重要提示

在Windows CMD中执行Python脚本时，请使用 **`py`** 命令而不是 `python` 命令。

## 正确的执行方式

### Windows CMD

```cmd
# 切换到项目目录
cd D:\wjw_work\smart_stock_advisor

# 使用 py 命令执行（正确）
py scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0

# 美股数据收集
py scripts\batch_collect_10years_data.py --market us --batch-size 50 --delay 1.0
```

### PowerShell

```powershell
# 切换到项目目录
cd D:\wjw_work\smart_stock_advisor

# 使用 py 命令执行（正确）
py scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0

# 或使用完整路径
python scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
```

## 常见问题

### 1. 执行命令没有任何反应

**原因**：
- 使用了 `python` 命令，但Windows系统上Python Launcher使用的是 `py` 命令
- 脚本可能在初始化阶段遇到了错误，但错误被捕获了

**解决方法**：

1. **使用 `py` 命令**：
   ```cmd
   py scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
   ```

2. **检查Python是否正确安装**：
   ```cmd
   py --version
   ```
   应该显示类似：`Python 3.13.2`

3. **检查脚本是否有语法错误**：
   ```cmd
   py -m py_compile scripts\batch_collect_10years_data.py
   ```

4. **添加详细输出测试**：
   ```cmd
   py scripts\batch_collect_10years_data.py --market cn --batch-size 3 --years 1 --delay 0.5
   ```

### 2. 命令不存在错误

如果 `py` 命令也不可用，请：

1. **检查Python安装路径是否在PATH中**
2. **使用完整路径**：
   ```cmd
   C:\Python\Python313\python.exe scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
   ```

### 3. 脚本执行但没有输出

如果脚本开始执行但没有输出，可能是：

1. **脚本正在初始化**（获取股票列表可能需要一些时间）
2. **数据库连接问题**（检查数据库配置）
3. **日志输出被重定向**（检查日志文件）

**检查方法**：
```cmd
# 查看是否有日志文件
dir logs\*.log

# 检查数据库连接
py -c "from config_db import USE_DATABASE; print(USE_DATABASE)"
```

### 4. 编码问题（中文乱码）

如果看到中文乱码，可以：

1. **更改CMD代码页**：
   ```cmd
   chcp 65001
   py scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
   ```

2. **使用UTF-8输出**（PowerShell）：
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   py scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
   ```

## 快速测试

### 测试1：检查Python和脚本

```cmd
cd D:\wjw_work\smart_stock_advisor
py --version
py scripts\batch_collect_10years_data.py --help
```

应该能看到帮助信息。

### 测试2：小规模测试

```cmd
cd D:\wjw_work\smart_stock_advisor
py scripts\batch_collect_10years_data.py --market cn --batch-size 3 --years 1 --delay 0.5
```

这会收集3只A股，1年数据，用于快速测试。

### 测试3：正式收集

```cmd
cd D:\wjw_work\smart_stock_advisor
py scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
```

这会开始正式的大规模数据收集。

## 推荐的执行方式

### 方式1：使用批处理文件（推荐）

创建 `start_cn_collection.bat`：
```batch
@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 开始收集A股数据...
py scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
pause
```

然后双击运行。

### 方式2：在CMD中执行

```cmd
cd D:\wjw_work\smart_stock_advisor
py scripts\batch_collect_10years_data.py --market cn --batch-size 50 --delay 1.0
```

## 验证脚本是否在执行

1. **查看进度文件**：
   ```cmd
   type data\collection_progress\collect_progress_cn.json
   ```

2. **查看日志文件**（如果有）：
   ```cmd
   type logs\*.log
   ```

3. **查看数据库**（如果有数据库访问权限）：
   ```sql
   SELECT COUNT(*) FROM stock_history_data;
   ```

## 如果仍然没有反应

请检查：

1. ✅ 是否使用了 `py` 命令（不是 `python`）
2. ✅ 是否在正确的目录（`D:\wjw_work\smart_stock_advisor`）
3. ✅ Python是否正确安装（`py --version`）
4. ✅ 脚本文件是否存在（`dir scripts\batch_collect_10years_data.py`）
5. ✅ 是否有依赖包（可能需要先安装：`pip install akshare yfinance pandas pymysql`）

如果以上都正常，但仍然没有反应，请：
- 检查任务管理器，看是否有Python进程在运行
- 查看是否有错误日志
- 尝试添加 `-u` 参数强制无缓冲输出：
  ```cmd
  py -u scripts\batch_collect_10years_data.py --market cn --batch-size 3 --years 1 --delay 0.5
  ```
