# ML模型训练实施说明

**创建日期**：2026-01-14  
**状态**：第一阶段完成 ✅

---

## 一、已完成的工作

### ✅ 1.1 数据库表创建

**文件**：`database/trained_models_table.sql`

**表结构**：
- `trained_models` 表：存储训练好的模型元数据
- 包含模型名称、类型、版本、文件路径、特征列表、特征重要性、训练指标等
- 支持多版本管理和激活/停用功能

**使用方法**：
```sql
-- 执行SQL文件创建表
source database/trained_models_table.sql;

-- 或直接执行SQL语句
mysql -u root -p stock_data < database/trained_models_table.sql
```

---

### ✅ 1.2 目录结构创建

**创建的目录**：
```
smart_stock_advisor/
├── models/
│   ├── xgb_classifier/    # XGBoost分类器模型
│   ├── lgb_classifier/    # LightGBM分类器模型
│   ├── xgb_regressor/     # XGBoost回归器模型
│   ├── lgb_regressor/     # LightGBM回归器模型
│   └── ensemble/          # 集成模型
```

---

### ✅ 1.3 核心模块创建

#### 1. 数据加载模块 (`utils/ml_data_loader.py`)

**功能**：
- 从数据库加载训练数据
- 从`stock_predictions`表获取标签数据
- 从`stock_history_data`表获取特征数据
- 构建特征和标签

**主要方法**：
- `load_training_data()`: 加载训练数据
- `_extract_features_from_history()`: 从历史数据提取特征
- `split_data_by_time()`: 按时间划分数据

**特征提取**：
- 基础价格特征（7个）
- 成交特征（4个）
- 技术指标特征（9个）
- 资金流向特征（5个）
- 估值特征（4个）
- 融资融券特征（3个）
- 衍生特征（10+个）
- 时间序列特征（10+个）

**总计**：约50+个特征

---

#### 2. 特征工程模块 (`utils/ml_feature_engineering.py`)

**功能**：
- 特征准备和选择
- 缺失值处理
- 特征标准化/归一化
- 特征重要性计算

**主要方法**：
- `prepare_features()`: 准备特征和标签
- `normalize_features()`: 特征标准化
- `select_features()`: 特征选择
- `get_feature_importance()`: 获取特征重要性

---

#### 3. 模型训练模块 (`utils/ml_model_trainer.py`)

**功能**：
- 训练XGBoost分类器
- 训练LightGBM分类器
- 训练XGBoost回归器
- 模型保存

**主要方法**：
- `train_xgb_classifier()`: 训练XGBoost分类器
- `train_lgb_classifier()`: 训练LightGBM分类器
- `train_xgb_regressor()`: 训练XGBoost回归器
- `save_model()`: 保存模型

---

#### 4. 模型管理模块 (`utils/ml_model_manager.py`)

**功能**：
- 保存模型信息到数据库
- 加载模型
- 列出模型
- 激活/停用模型
- 模型缓存

**主要方法**：
- `save_model_info()`: 保存模型信息
- `load_model()`: 加载模型
- `get_model_info()`: 获取模型信息
- `list_models()`: 列出所有模型
- `activate_model()`: 激活模型

---

#### 5. 训练脚本 (`scripts/train_ml_models.py`)

**功能**：
- 完整的模型训练流程
- 支持命令行参数
- 自动保存模型和信息

**使用方法**：
```bash
# 基本使用（使用默认参数）
python scripts/train_ml_models.py

# 指定训练时间范围
python scripts/train_ml_models.py \
    --train-start 2014-01-01 \
    --train-end 2022-12-31 \
    --val-start 2023-01-01 \
    --val-end 2023-12-31

# 指定要训练的模型类型
python scripts/train_ml_models.py \
    --models xgb_classifier lgb_classifier

# 不激活训练好的模型
python scripts/train_ml_models.py --no-activate
```

---

## 二、下一步工作

### 📋 2.1 安装依赖库

**需要安装的库**：
```bash
pip install scikit-learn xgboost lightgbm pandas numpy
```

**验证安装**：
```python
import sklearn
import xgboost
import lightgbm
print("所有库已安装")
```

---

### 📋 2.2 创建数据库表

**执行SQL文件**：
```bash
# 方法1：使用mysql命令行
mysql -u root -p stock_data < database/trained_models_table.sql

# 方法2：在Python中执行
python -c "
from utils.db_connection import DatabaseConnection
db = DatabaseConnection()
with open('database/trained_models_table.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
    db.execute_update(sql)
print('表创建成功')
"
```

---

### 📋 2.3 准备训练数据

**检查数据完整性**：
```sql
-- 检查是否有足够的预测记录（有实际结果）
SELECT COUNT(*) as count
FROM stock_predictions
WHERE actual_price IS NOT NULL
  AND actual_direction IS NOT NULL
  AND target_date >= '2014-01-01'
  AND target_date <= '2024-12-31';

-- 应该至少有几千条记录
```

**如果数据不足**：
- 需要先运行预测任务，生成预测记录
- 等待实际结果更新（需要时间）

---

### 📋 2.4 开始训练

**第一次训练（小规模测试）**：
```bash
# 使用最近1年的数据测试
python scripts/train_ml_models.py \
    --train-start 2023-01-01 \
    --train-end 2023-06-30 \
    --val-start 2023-07-01 \
    --val-end 2023-12-31 \
    --models xgb_classifier
```

**完整训练（使用10年数据）**：
```bash
# 使用10年数据训练
python scripts/train_ml_models.py \
    --train-start 2014-01-01 \
    --train-end 2022-12-31 \
    --val-start 2023-01-01 \
    --val-end 2023-12-31 \
    --test-start 2024-01-01 \
    --test-end 2024-12-31 \
    --models xgb_classifier lgb_classifier
```

---

## 三、训练流程说明

### 3.1 数据流程

```
1. 从stock_predictions表加载预测记录（有实际结果的）
   ↓
2. 对每条预测记录，从stock_history_data表加载对应的历史数据
   ↓
3. 从历史数据中提取特征（50+个特征）
   ↓
4. 构建训练样本（特征 + 标签）
   ↓
5. 按时间划分：训练集 / 验证集 / 测试集
```

### 3.2 训练流程

```
1. 准备特征和标签
   ↓
2. 特征标准化（可选）
   ↓
3. 训练模型（XGBoost/LightGBM）
   ↓
4. 评估模型（准确率、MAE等）
   ↓
5. 获取特征重要性
   ↓
6. 保存模型文件（.pkl）
   ↓
7. 保存模型信息到数据库
   ↓
8. 激活模型（可选）
```

---

## 四、模型使用

### 4.1 加载模型

```python
from utils.ml_model_manager import MLModelManager

manager = MLModelManager()

# 加载激活的模型
model = manager.load_model('xgb_classifier')

# 加载指定版本的模型
model = manager.load_model('xgb_classifier', version='v20240114_120000')

# 获取模型信息
model_info = manager.get_model_info('xgb_classifier')
feature_list = model_info['feature_list']
```

### 4.2 使用模型预测

```python
from utils.ml_model_manager import MLModelManager
from utils.ml_data_loader import MLDataLoader
from utils.ml_feature_engineering import MLFeatureEngineering

# 加载模型
manager = MLModelManager()
model = manager.load_model('xgb_classifier')
model_info = manager.get_model_info('xgb_classifier')
feature_list = model_info['feature_list']

# 准备特征
data_loader = MLDataLoader()
feature_engineering = MLFeatureEngineering()

# 获取股票历史数据
history_data = data_loader.storage.get_stock_history_data(
    symbol='600519',
    start_date='2024-01-01',
    end_date='2024-01-15'
)

# 提取特征
features = data_loader._extract_features_from_history(history_data[-60:])

# 构建特征向量（按照训练时的特征顺序）
import pandas as pd
feature_df = pd.DataFrame([features])
feature_df = feature_df[feature_list]  # 只选择训练时使用的特征

# 预测
if hasattr(model, 'predict_proba'):
    # 分类器
    proba = model.predict_proba(feature_df)[0]
    up_probability = proba[1]  # 上涨概率
else:
    # 回归器
    prediction = model.predict(feature_df)[0]
    up_probability = 1.0 if prediction > 0 else 0.0

print(f"预测上涨概率: {up_probability:.4f}")
```

---

## 五、注意事项

### ⚠️ 5.1 数据要求

1. **必须有足够的预测记录**：
   - 至少需要1000+条有实际结果的预测记录
   - 建议时间范围：至少1-2年

2. **历史数据完整性**：
   - 每只股票需要有足够的历史数据（至少60天）
   - 技术指标需要已计算

3. **数据质量**：
   - 确保`actual_price`、`actual_direction`字段已更新
   - 确保`prediction_hit`字段已计算

---

### ⚠️ 5.2 训练时间

**预估训练时间**：
- 小规模测试（1年数据，1000条样本）：5-10分钟
- 中等规模（5年数据，5000条样本）：30-60分钟
- 大规模（10年数据，10000+条样本）：1-3小时

**影响因素**：
- 数据量
- 特征数量
- 模型复杂度
- 硬件性能

---

### ⚠️ 5.3 模型选择

**推荐顺序**：
1. **XGBoost分类器**：最稳定，推荐先训练
2. **LightGBM分类器**：训练速度快，准确率相近
3. **XGBoost回归器**：如果需要预测涨跌幅

**不推荐**：
- 神经网络：需要大量数据，训练时间长
- 集成模型：需要先训练多个基模型

---

## 六、故障排查

### 🔧 6.1 常见错误

**错误1：XGBoost未安装**
```
ImportError: No module named 'xgboost'
```
**解决**：`pip install xgboost`

**错误2：LightGBM未安装**
```
ImportError: No module named 'lightgbm'
```
**解决**：`pip install lightgbm`

**错误3：数据为空**
```
训练数据为空，无法继续训练
```
**解决**：
- 检查`stock_predictions`表是否有数据
- 检查`actual_price`、`actual_direction`字段是否已填充
- 调整时间范围

**错误4：特征数量不匹配**
```
ValueError: feature_names mismatch
```
**解决**：
- 确保使用训练时的特征列表
- 检查特征工程逻辑

---

## 七、下一步计划

### 📅 第二阶段：集成到预测系统（1-2周）

1. 修改`StockPredictor`类，集成ML模型
2. 实现混合预测（ML模型 + 规则模型）
3. 添加模型预测结果到预测输出
4. 测试和验证

### 📅 第三阶段：优化和监控（持续）

1. 定期重新训练（每周/每月）
2. A/B测试对比效果
3. 监控模型性能
4. 优化特征工程

---

**创建日期**：2026-01-14  
**最后更新**：2026-01-14
