# ML模型训练快速开始指南

**创建日期**：2026-01-14

---

## 一、快速开始（5步）

### 步骤1：安装依赖库

```bash
pip install scikit-learn xgboost lightgbm pandas numpy
```

### 步骤2：创建数据库表

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

### 步骤3：检查数据

```sql
-- 检查是否有足够的预测记录
SELECT COUNT(*) as count
FROM stock_predictions
WHERE actual_price IS NOT NULL
  AND actual_direction IS NOT NULL
  AND target_date >= '2020-01-01';

-- 应该至少有1000+条记录
```

### 步骤4：小规模测试训练

```bash
# 使用最近1年的数据测试
python scripts/train_ml_models.py \
    --train-start 2023-01-01 \
    --train-end 2023-06-30 \
    --val-start 2023-07-01 \
    --val-end 2023-12-31 \
    --models xgb_classifier
```

### 步骤5：完整训练（10年数据）

```bash
# 使用10年数据训练
python scripts/train_ml_models.py \
    --train-start 2014-01-01 \
    --train-end 2022-12-31 \
    --val-start 2023-01-01 \
    --val-end 2023-12-31 \
    --models xgb_classifier lgb_classifier
```

---

## 二、训练结果

训练完成后，你会得到：

1. **模型文件**：保存在 `models/` 目录下
   - `models/xgb_classifier/xgb_classifier_v20240114_120000.pkl`
   - `models/lgb_classifier/lgb_classifier_v20240114_120000.pkl`

2. **模型信息**：保存在数据库 `trained_models` 表中
   - 模型名称、版本、路径
   - 特征列表、特征重要性
   - 训练指标（准确率、MAE等）

3. **日志输出**：训练过程中的详细信息

---

## 三、验证训练结果

```python
from utils.ml_model_manager import MLModelManager

manager = MLModelManager()

# 列出所有模型
models = manager.list_models()
for model in models:
    print(f"{model['model_name']} - {model['model_type']} - 准确率: {model.get('training_metrics', {}).get('val_accuracy', 'N/A')}")

# 获取模型信息
model_info = manager.get_model_info('xgb_classifier')
if model_info:
    print(f"模型: {model_info['model_name']}")
    print(f"训练准确率: {model_info['training_metrics'].get('train_accuracy', 'N/A')}")
    print(f"验证准确率: {model_info['training_metrics'].get('val_accuracy', 'N/A')}")
```

---

## 四、常见问题

### Q1: 训练数据为空怎么办？

**A**: 检查以下几点：
1. `stock_predictions`表是否有数据
2. `actual_price`、`actual_direction`字段是否已填充
3. 调整时间范围（使用更近的日期）

### Q2: 训练时间太长怎么办？

**A**: 
1. 先使用小规模数据测试（1年数据）
2. 减少特征数量
3. 使用LightGBM（训练速度更快）

### Q3: 模型准确率不高怎么办？

**A**:
1. 增加训练数据量
2. 优化特征工程
3. 调整模型超参数
4. 尝试集成学习

---

## 五、下一步

训练完成后，下一步是**集成到预测系统**：

1. 修改`StockPredictor`类，加载ML模型
2. 在预测时使用ML模型预测
3. 融合ML模型和规则模型的预测结果

详见：`基于10年历史数据的模型训练方案.md`

---

**创建日期**：2026-01-14
