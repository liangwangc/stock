## 项目环境安装说明（新环境快速上手）

本说明用于在一台全新的电脑/新环境中，快速配置运行以下三个项目：

- `smart_stock_advisor`
- `quant_trading_platform`
- `news-analysis-system-main`

推荐先使用 **虚拟环境**，避免不同项目之间的依赖冲突。

---

## 一、通用环境准备

```bash
cd d:\wjw_work

# 1. 创建并激活虚拟环境（Windows PowerShell）
python -m venv .venv
.\.venv\Scripts\activate

# 2. 升级 pip（可选但推荐）
python -m pip install --upgrade pip
```

> 提示：以后每次在新终端中使用这些项目时，都要先激活虚拟环境：  
> `cd d:\wjw_work` → `.\.venv\Scripts\activate`

---

## 二、smart_stock_advisor 安装步骤

项目路径：`d:\wjw_work\smart_stock_advisor`

```bash
cd d:\wjw_work\smart_stock_advisor

# 推荐使用国内镜像安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用默认源
# pip install -r requirements.txt
```

> 说明：
> - `requirements.txt` 中包含 `TA-Lib`，如果安装报错，再根据系统单独搜索 “TA-Lib 安装 + 操作系统名” 处理。
> - 安装完成后，可按项目 README 中的方法运行：`python main.py`。

---

## 三、quant_trading_platform 安装步骤

项目路径：`d:\wjw_work\quant_trading_platform`

```bash
cd d:\wjw_work\quant_trading_platform

# 推荐使用国内镜像安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用默认源
# pip install -r requirements.txt
```

> 说明：
> - 依赖中包含 `akshare`、`gf-api-client` 等，需保证可以访问外网。
> - 安装完成后，可通过：
>   - Windows：双击运行 `快速开始.bat`，或  
>   - 手动：`python main.py` / `python run.py`
>   启动示例策略或回测。

---

## 四、news-analysis-system-main 安装步骤

项目路径：`d:\wjw_work\news-analysis-system-main`

### 1. 修改 torch 版本（重要）

在安装依赖前，先根据你电脑的 **Python 版本 + CUDA / GPU 情况**，修改 `requirements.txt` 中的 `torch` 版本为合适的官方版本。  
（参考 PyTorch 官网生成命令，再同步改到 `requirements.txt`）

### 2. 安装依赖

```bash
cd d:\wjw_work\news-analysis-system-main

pip install -r requirements.txt
```

> 说明：
> - 该项目依赖 `openai`、`transformers`、`akshare`、`streamlit` 等包，建议使用 **Python 3.12**。
> - 如果下载过慢，可以在命令后加上清华镜像：  
>   `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 3. 数据库（MySQL）准备

- 安装 **MySQL 8.0+**。
- 在项目中配置数据库连接：
  - 在 `src/config/config.py` / `src/database/db_handle.py`（根据当前代码结构）中填写自己的 MySQL 账号、密码、库名。
  - 使用 `sql_table_create.txt` 中的 SQL 语句创建相关数据表。

### 4. 常用运行命令（备查）

```bash
# 获取新闻数据
python src/data_processing/get_cls_news.py

# 执行新闻分析（主程序）
python src/analysis/main.py

# 如有 JSON 错误，修复并导入
python src/data_processing/review_json.py
python src/data_processing/import_json.py

# 生成分类总结
python src/analysis/categories_summary.py

# 启动 Web 可视化界面
streamlit run src/visualization/streamlit_web.py
```

---

## 五、快速检查清单（新环境必做）

1. **安装 Python（建议 3.10+，news 项目建议 3.12）**。  
2. 在 `d:\wjw_work` 下创建并激活虚拟环境：`.venv`。  
3. 依次进入三个项目目录，执行对应的 `pip install -r requirements.txt` 命令。  
4. 对 `news-analysis-system-main`：
   - 先确认 `torch` 版本是否与本机 GPU/CPU 匹配；
   - 安装并配置好 MySQL，建表成功。  
5. 分别运行每个项目的主入口（如 `main.py` / Web 启动命令）确认无报错。

