# 开始训练ML模型 - 完整指南

**创建日期**：2026-01-14

---

## 一、快速开始（3步）

### 步骤1：安装依赖库

**方法1：使用requirements.txt（推荐）**
```bash
cd d:\wjw_work\smart_stock_advisor
pip install -r requirements.txt
```

**方法2：仅安装ML训练所需依赖**
```bash
pip install scikit-learn>=1.3.0 xgboost>=2.0.0 lightgbm>=4.0.0 pandas>=2.0.0 numpy>=1.24.0
```

**方法3：使用国内镜像（如果网络较慢）**
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 步骤2：运行准备脚本

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

这个脚本会：
- ✅ 检查依赖库是否安装
- ✅ 创建`trained_models`表（如果不存在）
- ✅ 检查数据完整性
- ✅ 显示可训练样本数

### 步骤3：开始训练

**小规模测试（推荐先运行）**：
```bash
# Windows
py scripts/train_base_model.py --train-start 2023-01-01 --train-end 2023-06-30 --val-start 2023-07-01 --val-end 2023-12-31 --models xgb_classifier

# Linux/Mac
python scripts/train_base_model.py --train-start 2023-01-01 --train-end 2023-06-30 --val-start 2023-07-01 --val-end 2023-12-31 --models xgb_classifier
```

**完整训练（使用10年数据）**：
```bash
# Windows
py scripts/train_base_model.py --train-start 2014-01-01 --train-end 2022-12-31 --val-start 2023-01-01 --val-end 2023-12-31 --test-start 2024-01-01 --test-end 2024-12-31 --models xgb_classifier lgb_classifier

# Linux/Mac
python scripts/train_base_model.py --train-start 2014-01-01 --train-end 2022-12-31 --val-start 2023-01-01 --val-end 2023-12-31 --test-start 2024-01-01 --test-end 2024-12-31 --models xgb_classifier lgb_classifier
```

---

## 二、训练过程说明

### 2.1 训练流程

```
1. 加载训练数据
   ├── 从stock_predictions表加载有实际结果的预测记录
   └── 从stock_history_data表加载对应的历史数据

2. 提取特征（50+个特征）
   ├── 基础价格特征（7个）
   ├── 成交特征（4个）
   ├── 技术指标特征（9个）
   ├── 资金流向特征（5个）
   ├── 估值特征（4个）
   ├── 融资融券特征（3个）
   ├── 衍生特征（10+个）
   └── 时间序列特征（10+个）

3. 准备训练集和验证集
   ├── 按时间划分（避免未来信息泄露）
   └── 处理缺失值和异常值

4. 训练模型
   ├── XGBoost分类器
   └── LightGBM分类器

5. 评估模型
   ├── 训练集准确率
   └── 验证集准确率

6. 保存模型
   ├── 模型文件（.pkl）
   ├── 特征列表（.json）
   ├── 特征重要性（.json）
   └── 模型信息（数据库）
```

### 2.2 训练时间预估

- **小规模测试**（1年数据，1000条样本）：5-10分钟
- **中等规模**（5年数据，5000条样本）：30-60分钟
- **大规模**（10年数据，10000+条样本）：1-3小时

---

## 三、训练结果

训练完成后，你会得到：

### 3.1 模型文件

保存在 `models/` 目录下：
```
models/
├── xgb_classifier/
│   ├── xgb_classifier_v20240114_120000.pkl      # 模型文件
│   ├── xgb_classifier_v20240114_120000_features.json    # 特征列表
│   ├── xgb_classifier_v20240114_120000_importance.json   # 特征重要性
│   └── xgb_classifier_v20240114_120000_config.json      # 配置和指标
└── lgb_classifier/
    └── ...
```

### 3.2 数据库记录

保存在 `trained_models` 表中：
- 模型名称、类型、版本
- 特征列表、特征重要性
- 训练指标（准确率、MAE等）
- 训练时间范围

### 3.3 日志输出

训练过程中的详细信息：
- 数据加载进度
- 特征提取进度
- 模型训练进度
- 评估结果

---

## 四、验证训练结果

### 4.1 查看模型列表

```python
from utils.ml_model_manager import MLModelManager

manager = MLModelManager()

# 列出所有模型
models = manager.list_models()
for model in models:
    print(f"{model['model_name']} - {model['model_type']}")
    print(f"  创建时间: {model['created_at']}")
    print(f"  样本数: {model['sample_count']}")
    print(f"  是否激活: {'是' if model['is_active'] else '否'}")
    print()
```

### 4.2 查看模型详细信息

```python
from utils.ml_model_manager import MLModelManager

manager = MLModelManager()

# 获取模型信息
model_info = manager.get_model_info('xgb_classifier')
if model_info:
    print(f"模型名称: {model_info['model_name']}")
    print(f"模型版本: {model_info['model_version']}")
    print(f"训练样本数: {model_info['sample_count']}")
    print(f"特征数量: {model_info['feature_count']}")
    
    metrics = model_info['training_metrics']
    print(f"\n训练指标:")
    print(f"  训练准确率: {metrics.get('train_accuracy', 'N/A'):.4f}")
    print(f"  验证准确率: {metrics.get('val_accuracy', 'N/A'):.4f}")
    
    # 显示前10个重要特征
    importance = model_info['feature_importance']
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    print(f"\n前10个重要特征:")
    for i, (feat, imp) in enumerate(sorted_features[:10], 1):
        print(f"  {i}. {feat}: {imp:.4f}")
```

---

## 五、常见问题

### Q1: 训练数据为空怎么办？

**检查步骤**：
1. 运行 `python scripts/prepare_ml_training.py` 查看数据情况
2. 检查 `stock_predictions` 表是否有数据
3. 检查 `actual_price`、`actual_direction` 字段是否已填充
4. 如果数据不足，需要先运行预测任务生成更多预测记录

**解决方案**：
```sql
-- 检查预测记录
SELECT COUNT(*) FROM stock_predictions WHERE actual_price IS NOT NULL;

-- 如果数据不足，需要等待实际结果更新或运行预测任务
```

### Q2: 训练时间太长怎么办？

**优化方案**：
1. 先使用小规模数据测试（1年数据）
2. 减少特征数量（修改特征工程）
3. 使用LightGBM（训练速度更快）
4. 减少模型参数（如n_estimators）

### Q3: 模型准确率不高怎么办？

**优化方案**：
1. 增加训练数据量
2. 优化特征工程（添加更多特征）
3. 调整模型超参数
4. 尝试集成学习（多个模型融合）

### Q4: 内存不足怎么办？

**优化方案**：
1. 减少训练数据量（使用更短的时间范围）
2. 减少特征数量
3. 使用分批训练
4. 增加系统内存

---

## 六、下一步：集成到预测系统

训练完成后，下一步是将ML模型集成到预测系统中：

### 6.1 修改StockPredictor类

在 `predictor/stock_predictor.py` 中：
1. 添加ML模型加载逻辑
2. 在预测时使用ML模型
3. 融合ML模型和规则模型的预测结果

### 6.2 测试和验证

1. 对比ML模型和规则模型的预测结果
2. 评估融合后的预测准确性
3. A/B测试选择最优方案

详见：`基于10年历史数据的模型训练方案.md`

---

## 七、训练命令参考

### 7.1 基础模型训练命令（train_base_model.py）

**Windows系统：**
```bash
# 使用默认参数（10年数据）
py scripts/train_base_model.py

# 指定时间范围
py scripts/train_base_model.py --train-start 2014-01-01 --train-end 2022-12-31 --val-start 2023-01-01 --val-end 2023-12-31 --test-start 2024-01-01 --test-end 2024-12-31

# 指定模型类型
py scripts/train_base_model.py --models xgb_classifier lgb_classifier

# 不激活训练好的模型
py scripts/train_base_model.py --no-activate

# 使用最近3年数据（2023-2026）
py scripts/train_base_model.py --train-start 2023-01-01 --train-end 2024-12-31 --val-start 2025-01-01 --val-end 2025-12-31 --test-start 2026-01-01 --test-end 2026-12-31 --models xgb_classifier lgb_classifier
```

**Linux/Mac系统：**
```bash
# 使用默认参数（10年数据）
python scripts/train_base_model.py

# 指定时间范围
python scripts/train_base_model.py --train-start 2014-01-01 --train-end 2022-12-31 --val-start 2023-01-01 --val-end 2023-12-31 --test-start 2024-01-01 --test-end 2024-12-31

# 指定模型类型
python scripts/train_base_model.py --models xgb_classifier lgb_classifier

# 不激活训练好的模型
python scripts/train_base_model.py --no-activate
```

### 7.2 微调模型命令（fine_tune_model.py）

**Windows系统：**
```bash
# 使用最近90天预测数据微调
py scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000

# 指定微调数据时间范围
py scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000 --start-date 2024-01-01 --end-date 2024-12-31

# 自定义微调参数
py scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000 --lr-multiplier 0.05 --n-estimators 100
```

**Linux/Mac系统：**
```bash
# 使用最近90天预测数据微调
python scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000

# 指定微调数据时间范围
python scripts/fine_tune_model.py --base-model xgb_classifier_base_v20240114_120000 --start-date 2024-01-01 --end-date 2024-12-31
```

### 7.3 train_base_model.py 参数说明

- `--train-start`: 训练集开始日期（默认：2014-01-01）
- `--train-end`: 训练集结束日期（默认：2022-12-31）
- `--val-start`: 验证集开始日期（默认：2023-01-01）
- `--val-end`: 验证集结束日期（默认：2023-12-31）
- `--test-start`: 测试集开始日期（默认：2024-01-01）
- `--test-end`: 测试集结束日期（默认：2024-12-31）
- `--models`: 要训练的模型类型，多个用空格分隔（默认：xgb_classifier lgb_classifier）
  - 可选值：`xgb_classifier`、`lgb_classifier`、`xgb_regressor`、`lgb_regressor`
- `--no-activate`: 不激活训练好的模型（默认：训练完成后自动激活）

### 7.4 fine_tune_model.py 参数说明

- `--base-model`: 基础模型名称（必需），格式：`xgb_classifier_base_v20240114_120000`
- `--start-date`: 微调数据开始日期（默认：最近90天）
- `--end-date`: 微调数据结束日期（默认：今天）
- `--lr-multiplier`: 学习率倍数（默认：0.1，即降低10倍）
- `--n-estimators`: 微调时的树数量（默认：50）
- `--no-activate`: 不激活微调后的模型（默认：微调完成后自动激活）

---

**创建日期**：2026-01-14  
**最后更新**：2026-01-14
