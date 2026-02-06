# ML模型训练完整命令参考

**创建日期**：2026-01-15  
**最后更新**：2026-01-15

---

## 一、环境准备

### 1.1 安装依赖包

**方法1：使用requirements.txt（推荐）**
```bash
# Windows
cd d:\wjw_work\smart_stock_advisor
pip install -r requirements.txt

# Linux/Mac
cd /path/to/smart_stock_advisor
pip install -r requirements.txt
```

**方法2：仅安装ML训练所需依赖**
```bash
pip install scikit-learn>=1.3.0 xgboost>=2.0.0 lightgbm>=4.0.0 pandas>=2.0.0 numpy>=1.24.0 pymysql>=1.1.0
```

**方法3：使用国内镜像（如果网络较慢）**
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 1.2 运行准备脚本

**Windows系统：**
```bash
cd d:\wjw_work\smart_stock_advisor
py scripts/prepare_ml_training.py
```

**Linux/Mac系统：**
```bash
cd /path/to/smart_stock_advisor
python scripts/prepare_ml_training.py
```

**功能**：
- ✅ 检查依赖库是否安装
- ✅ 创建`trained_models`表（如果不存在）
- ✅ 检查数据完整性
- ✅ 显示可训练样本数

---

## 二、基础模型训练命令（train_base_model.py）

### 2.1 小规模测试（推荐先运行）

**Windows系统：**
```bash
py scripts/train_base_model.py --train-start 2023-01-01 --train-end 2023-06-30 --val-start 2023-07-01 --val-end 2023-12-31 --models xgb_classifier
```

**Linux/Mac系统：**
```bash
python scripts/train_base_model.py --train-start 2023-01-01 --train-end 2023-06-30 --val-start 2023-07-01 --val-end 2023-12-31 --models xgb_classifier
```

**数据划分**：
- 训练集：2023年上半年（6个月）
- 验证集：2023年下半年（6个月）

**预期样本数**：约1-5万条  
**训练时间**：5-15分钟

---

### 2.2 使用最近3年数据（2023-2026）

**Windows系统：**
```bash
py scripts/train_base_model.py --train-start 2023-01-01 --train-end 2024-12-31 --val-start 2025-01-01 --val-end 2025-12-31 --test-start 2026-01-01 --test-end 2026-12-31 --models xgb_classifier lgb_classifier
```

**Linux/Mac系统：**
```bash
python scripts/train_base_model.py --train-start 2023-01-01 --train-end 2024-12-31 --val-start 2025-01-01 --val-end 2025-12-31 --test-start 2026-01-01 --test-end 2026-12-31 --models xgb_classifier lgb_classifier
```

**数据划分**：
- 训练集：2023-2024年（2年）
- 验证集：2025年（1年）
- 测试集：2026年（1年）

**预期样本数**：约10-50万条  
**训练时间**：30-90分钟

---

### 2.3 使用10年数据（2014-2024）

**Windows系统：**
```bash
py scripts/train_base_model.py --train-start 2014-01-01 --train-end 2022-12-31 --val-start 2023-01-01 --val-end 2023-12-31 --test-start 2024-01-01 --test-end 2024-12-31 --models xgb_classifier lgb_classifier
```

**Linux/Mac系统：**
```bash
python scripts/train_base_model.py --train-start 2014-01-01 --train-end 2022-12-31 --val-start 2023-01-01 --val-end 2023-12-31 --test-start 2024-01-01 --test-end 2024-12-31 --models xgb_classifier lgb_classifier
```

**数据划分**：
- 训练集：2014-2022年（9年）
- 验证集：2023年（1年）
- 测试集：2024年（1年）

**预期样本数**：约100万+条  
**训练时间**：1-3小时

---

### 2.4 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--train-start` | 训练集开始日期 | 2014-01-01 |
| `--train-end` | 训练集结束日期 | 2022-12-31 |
| `--val-start` | 验证集开始日期 | 2023-01-01 |
| `--val-end` | 验证集结束日期 | 2023-12-31 |
| `--test-start` | 测试集开始日期 | 2024-01-01 |
| `--test-end` | 测试集结束日期 | 2024-12-31 |
| `--models` | 要训练的模型类型，多个用空格分隔 | xgb_classifier lgb_classifier |
| `--no-activate` | 不激活训练好的模型 | False（默认自动激活） |

**模型类型选项**：
- `xgb_classifier` - XGBoost分类器
- `lgb_classifier` - LightGBM分类器
- `xgb_regressor` - XGBoost回归器
- `lgb_regressor` - LightGBM回归器

---

## 三、微调模型命令（fine_tune_model.py）

### 3.1 使用最近90天预测数据微调

**Windows系统：**
```bash
py scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000
```

**Linux/Mac系统：**
```bash
python scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000
```

**说明**：
- 自动使用最近90天的预测数据
- 需要至少1000+条有实际结果的预测记录

---

### 3.2 指定微调数据时间范围

**Windows系统：**
```bash
py scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000 --start-date 2024-01-01 --end-date 2024-12-31
```

**Linux/Mac系统：**
```bash
python scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000 --start-date 2024-01-01 --end-date 2024-12-31
```

---

### 3.3 自定义微调参数

**Windows系统：**
```bash
py scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000 --lr-multiplier 0.05 --n-estimators 100
```

**Linux/Mac系统：**
```bash
python scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000 --lr-multiplier 0.05 --n-estimators 100
```

---

### 3.4 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--base-model` | 基础模型名称（必需） | - |
| `--start-date` | 微调数据开始日期 | 最近90天 |
| `--end-date` | 微调数据结束日期 | 今天 |
| `--lr-multiplier` | 学习率倍数（降低学习率） | 0.1 |
| `--n-estimators` | 微调时的树数量 | 50 |
| `--no-activate` | 不激活微调后的模型 | False（默认自动激活） |

---

## 四、Web界面训练（推荐）

### 4.1 启动Web服务

**Windows系统：**
```bash
cd d:\wjw_work\smart_stock_advisor
py web_app.py
```

**Linux/Mac系统：**
```bash
cd /path/to/smart_stock_advisor
python web_app.py
```

### 4.2 使用Web界面训练

1. 打开浏览器访问：`http://localhost:5000`
2. 登录系统（默认账号：admin / admin123）
3. 进入"设置"页面
4. 点击左侧菜单"模型学习"
5. 在"模型训练"部分：
   - **历史数据训练（基础模型）**：点击"开始训练"按钮
   - **预测数据训练（模型微调）**：点击"检查数据"按钮，然后点击"开始微调训练"

### 4.3 Web界面优势

- ✅ 可视化训练进度
- ✅ 实时查看训练日志
- ✅ 无需手动输入命令
- ✅ 自动管理训练任务
- ✅ 训练完成后自动显示在"已训练模型列表"

---

## 五、查看训练结果

### 5.1 Web界面查看

1. 进入"设置"页面 > "模型学习" > "模型训练"
2. 在"已训练模型列表"区域点击"刷新"按钮
3. 查看所有已训练的模型：
   - 模型名称和版本
   - 是否激活状态
   - 训练准确率和验证准确率
   - 训练样本数
   - 训练时间范围

### 5.2 命令行查看

```python
from utils.ml_model_manager import MLModelManager

manager = MLModelManager()
models = manager.list_models()

for model in models:
    print(f"{model['model_name']} - {model['model_type']}")
    print(f"  创建时间: {model['created_at']}")
    print(f"  样本数: {model['sample_count']}")
    print(f"  是否激活: {'是' if model['is_active'] else '否'}")
    print()
```

---

## 六、激活模型

### 6.1 Web界面激活（推荐）

1. 进入"设置"页面 > "模型学习" > "模型训练"
2. 在"已训练模型列表"中找到要激活的模型
3. 点击模型右侧的"激活"按钮
4. 确认激活操作
5. 激活成功后，模型会显示"✓ 已激活"标签

### 6.2 命令行激活

```python
from utils.ml_model_manager import MLModelManager

manager = MLModelManager()
success = manager.activate_model(model_id)  # model_id是模型在数据库中的ID

if success:
    print("模型激活成功！")
else:
    print("模型激活失败！")
```

---

## 七、训练时间预估

| 数据量 | 样本数 | 训练时间 |
|--------|--------|----------|
| 1年数据 | 1-5万条 | 5-15分钟 |
| 3年数据 | 10-50万条 | 30-90分钟 |
| 10年数据 | 100万+条 | 1-3小时 |

**影响因素**：
- 数据量
- 特征数量（50+个特征）
- 模型复杂度
- 硬件性能（CPU、内存）

---

## 八、常见问题

### Q1: 训练时间太长怎么办？

**解决方案**：
1. 使用更短的时间范围（如1-2年）
2. 只训练一个模型（如只训练xgb_classifier）
3. 减少特征数量（修改特征工程）
4. 使用LightGBM（训练速度更快）

### Q2: 内存不足怎么办？

**解决方案**：
1. 使用更短的时间范围
2. 分批训练（先训练部分股票）
3. 减少特征数量
4. 增加系统内存

### Q3: 如何查看训练进度？

**解决方案**：
- **Web界面**：实时查看训练进度条和日志
- **命令行**：查看终端输出的日志
- **文件系统**：检查`models/`目录下的文件（训练过程中会保存）
- **数据库**：查看`trained_models`表

### Q4: 训练数据为空怎么办？

**检查步骤**：
1. 运行 `py scripts/prepare_ml_training.py` 查看数据情况
2. 检查 `stock_history_data` 表是否有数据
3. 检查指定时间范围内是否有数据
4. 如果数据不足，需要先运行数据抓取任务

---

## 九、相关文档

- [开始训练ML模型.md](./开始训练ML模型.md) - 快速开始指南
- [训练命令参考.md](./训练命令参考.md) - 详细命令参考
- [ML模型训练策略说明.md](./ML模型训练策略说明.md) - 训练策略说明
- [依赖安装指南.md](./docs/依赖安装指南.md) - 依赖包安装指南

---

**创建日期**：2026-01-15  
**最后更新**：2026-01-15
