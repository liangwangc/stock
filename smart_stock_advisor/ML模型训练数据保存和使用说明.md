# ML模型训练数据保存和使用说明

## 一、训练后保存的数据

### 1.1 模型文件（文件系统）

**保存位置**：`smart_stock_advisor/models/<模型类型>/`

**文件结构**：
```
models/
├── xgb_classifier/
│   ├── xgb_classifier_base_v20260114_153000.pkl          # 模型文件（核心）
│   ├── xgb_classifier_base_v20260114_153000_features.json # 特征列表
│   ├── xgb_classifier_base_v20260114_153000_importance.json # 特征重要性
│   └── xgb_classifier_base_v20260114_153000_config.json   # 训练配置和指标
├── lgb_classifier/
│   └── ...
├── xgb_regressor/
│   └── ...
└── lgb_regressor/
    └── ...
```

**文件说明**：

| 文件类型 | 文件名格式 | 内容 | 用途 |
|---------|-----------|------|------|
| **模型文件** | `*.pkl` | 训练好的模型对象（pickle格式） | 用于预测 |
| **特征列表** | `*_features.json` | 模型使用的特征名称列表 | 确保预测时特征顺序一致 |
| **特征重要性** | `*_importance.json` | 每个特征的重要性得分 | 分析模型，了解哪些特征最重要 |
| **配置和指标** | `*_config.json` | 训练指标、配置参数、保存时间 | 评估模型性能 |

**保存代码位置**：
- `utils/ml_model_trainer.py` 第418-468行：`save_model()` 方法

---

### 1.2 模型元数据（数据库）

**保存位置**：`trained_models` 表

**表结构**：
```sql
CREATE TABLE IF NOT EXISTS `trained_models` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `model_name` VARCHAR(255) NOT NULL,              -- 模型名称
    `model_type` VARCHAR(50) NOT NULL,               -- 模型类型
    `model_version` VARCHAR(50) NOT NULL,            -- 模型版本
    `model_file_path` VARCHAR(1000) NOT NULL,        -- 模型文件路径
    `feature_list` JSON DEFAULT NULL,                 -- 特征列表
    `feature_importance` JSON DEFAULT NULL,           -- 特征重要性
    `training_config` JSON DEFAULT NULL,              -- 训练配置
    `training_metrics` JSON DEFAULT NULL,              -- 训练指标
    `train_start_date` DATE NOT NULL,                 -- 训练集开始日期
    `train_end_date` DATE NOT NULL,                   -- 训练集结束日期
    `val_start_date` DATE DEFAULT NULL,                -- 验证集开始日期
    `val_end_date` DATE DEFAULT NULL,                 -- 验证集结束日期
    `sample_count` INT DEFAULT 0,                     -- 训练样本数量
    `feature_count` INT DEFAULT 0,                    -- 特征数量
    `is_active` TINYINT(1) DEFAULT 0,                 -- 是否激活
    `description` TEXT DEFAULT NULL,                  -- 模型描述
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
```

**保存内容示例**：
```json
{
    "model_name": "xgb_classifier_base_v20260114_153000",
    "model_type": "xgb_classifier",
    "model_version": "v20260114_153000",
    "model_file_path": "models/xgb_classifier/xgb_classifier_base_v20260114_153000.pkl",
    "feature_list": ["close_price", "volume", "ma5", "ma20", "rsi", ...],
    "feature_importance": {
        "rsi": 0.1234,
        "ma5": 0.0987,
        "volume": 0.0876,
        ...
    },
    "training_config": {
        "model_type": "xgb_classifier",
        "model_category": "base",
        "data_source": "stock_history_data"
    },
    "training_metrics": {
        "train_accuracy": 0.6523,
        "val_accuracy": 0.6234,
        "train_logloss": 0.5432,
        "val_logloss": 0.5678
    },
    "train_start_date": "2023-01-01",
    "train_end_date": "2024-12-31",
    "val_start_date": "2025-01-01",
    "val_end_date": "2025-12-31",
    "sample_count": 1250000,
    "feature_count": 45,
    "is_active": 1
}
```

**保存代码位置**：
- `utils/ml_model_manager.py` 第31-115行：`save_model_info()` 方法
- `scripts/train_base_model.py` 第227-247行：调用保存方法

---

### 1.3 训练过程数据（日志）

**保存位置**：日志文件（`logs/` 目录）

**日志内容**：
- 训练进度信息
- 数据加载统计
- 特征提取进度
- 模型训练指标
- 错误信息（如果有）

**日志示例**：
```
2026-01-14 15:30:00 - INFO - 开始训练基础模型
2026-01-14 15:30:05 - INFO - 训练数据加载完成：1,250,000 条样本
2026-01-14 15:30:10 - INFO - 特征准备完成：45 个特征
2026-01-14 15:35:20 - INFO - XGBoost分类器训练完成：训练准确率 0.6523
2026-01-14 15:35:25 - INFO - Top 10 重要特征: rsi: 0.1234, ma5: 0.0987, ...
2026-01-14 15:35:30 - INFO - 模型文件保存成功
2026-01-14 15:35:35 - INFO - 模型信息保存成功: xgb_classifier_base_v20260114_153000
```

---

## 二、模型如何运用到股票预测

### 2.1 模型加载流程

**步骤1：预测时自动加载模型**

当执行股票预测时，系统会自动尝试加载激活的ML模型：

```python
# 代码位置：predictor/stock_predictor.py 第2770-2788行

# 尝试获取ML模型预测结果（如果可用）
ml_score = 0.0
ml_weight = 0.0
ml_prediction_result = None
try:
    from utils.ml_predictor_integration import MLPredictorIntegration
    ml_integration = MLPredictorIntegration()
    ml_prediction_result = ml_integration.get_ml_prediction(symbol, data)
    
    if ml_prediction_result and ml_prediction_result.get('available'):
        ml_score = ml_prediction_result.get('ml_score', 0.0)
        ml_weight = 0.15  # ML模型权重15%
```

**步骤2：从数据库查询激活的模型**

```python
# 代码位置：utils/ml_model_manager.py 第117-190行

# 查询数据库，查找激活的模型
sql = """
    SELECT model_file_path, feature_list
    FROM trained_models
    WHERE model_type = %s AND is_active = 1
    ORDER BY created_at DESC
    LIMIT 1
"""
```

**步骤3：加载模型文件**

```python
# 从文件系统加载模型对象
with open(full_path, 'rb') as f:
    model = pickle.load(f)
```

**步骤4：缓存模型**

```python
# 模型加载后会被缓存，避免重复加载
self._model_cache[cache_key] = model
```

---

### 2.2 预测流程

**完整预测流程**：

```
1. 用户请求预测股票（如：000001）
   ↓
2. StockPredictor.predict('000001')
   ↓
3. 获取股票历史数据（60天）
   ↓
4. 并行计算8个传统因子得分
   ├── 技术指标得分
   ├── 新闻情感得分
   ├── 资金流向得分
   ├── 市场情绪得分
   ├── 板块轮动得分
   ├── 历史模式得分
   ├── 估值指标得分
   └── 美股板块得分
   ↓
5. 【ML模型预测】（如果模型已激活）
   ├── MLPredictorIntegration.get_ml_prediction()
   ├── 加载激活的模型（从缓存或文件系统）
   ├── 准备特征数据（与训练时一致）
   ├── 调用模型预测
   └── 返回ML得分和概率
   ↓
6. 权重归一化（包含ML权重）
   ├── 8个因子权重总和：85%
   ├── ML模型权重：15%
   └── 归一化确保总和为100%
   ↓
7. 计算最终得分
   final_score = Σ(因子得分 × 归一化权重)
   ↓
8. 转换为概率
   up_probability = sigmoid(final_score × 3)
   ↓
9. 生成预测结果
   ├── 预测方向（上涨/下跌/震荡）
   ├── 上涨/下跌概率
   ├── 置信度
   └── ML模型预测信息（如果可用）
```

---

### 2.3 ML模型预测详细流程

**代码位置**：`utils/ml_predictor_integration.py`

**步骤1：加载激活的模型**

```python
# 优先使用分类器模型
classifier_model = self._load_active_model('xgb_classifier')
if not classifier_model:
    classifier_model = self._load_active_model('lgb_classifier')

# 如果没有分类器，使用回归器
if not classifier_model:
    regressor_model = self._load_active_model('xgb_regressor')
```

**步骤2：准备特征数据**

```python
# 从股票历史数据提取特征
features_df = self._prepare_features_for_prediction(symbol, stock_data)

# 确保特征顺序与训练时一致
if model_info and model_info.get('feature_list'):
    feature_list = model_info['feature_list']
    features_df = features_df[feature_list]  # 按训练时的顺序排列
```

**步骤3：执行预测**

```python
# 分类器模型
if hasattr(model, 'predict_proba'):
    proba = model.predict_proba(features_df)
    up_probability = float(proba[0][1])  # 上涨概率

# 回归器模型
else:
    predicted_change_pct = model.predict(features_df)[0]
    up_probability = 0.5 + (predicted_change_pct / 20.0)  # 转换为概率
```

**步骤4：计算得分**

```python
# 分类器：将概率转换为-1到1的得分
ml_score = (up_probability - 0.5) * 2

# 回归器：将涨跌幅转换为得分
ml_score = predicted_change_pct / 10.0
```

**步骤5：返回预测结果**

```python
return {
    'available': True,
    'ml_score': ml_score,                    # ML模型得分（-1到1）
    'ml_up_probability': up_probability,     # 上涨概率（0到1）
    'ml_down_probability': 1.0 - up_probability,
    'ml_prediction': '上涨'/'下跌'/'震荡',
    'ml_confidence': ml_confidence,         # ML模型置信度
    'model_type': 'xgb_classifier'           # 使用的模型类型
}
```

---

### 2.4 模型得分融合到最终预测

**代码位置**：`predictor/stock_predictor.py` 第2814-2825行

**融合公式**：
```python
# 计算包含ML模型的总权重
total_weight = (
    adjusted_technical_weight +      # 技术指标权重
    adjusted_news_weight +            # 新闻权重
    adjusted_capital_flow_weight +    # 资金流向权重
    adjusted_market_weight +          # 市场情绪权重
    adjusted_sector_rotation_weight + # 板块轮动权重
    adjusted_history_weight +        # 历史模式权重
    adjusted_valuation_weight +      # 估值指标权重
    adjusted_us_sector_weight +       # 美股板块权重
    ml_weight                         # ML模型权重（15%）
)

# 归一化所有权重
normalized_weight = original_weight / total_weight

# 计算最终得分
final_score = (
    technical_score * normalized_technical_weight +
    news_score * normalized_news_weight +
    capital_flow_score * normalized_capital_flow_weight +
    market_score * normalized_market_weight +
    sector_rotation_score * normalized_sector_rotation_weight +
    history_score * normalized_history_weight +
    valuation_score * normalized_valuation_weight +
    us_sector_score * normalized_us_sector_weight +
    ml_score * normalized_ml_weight  # ML模型得分 × 15%
)
```

**示例计算**：

假设：
- 技术指标得分：0.5，权重：20%
- 新闻得分：0.3，权重：25%
- ML模型得分：0.7，权重：15%
- 其他因子得分：0.4，权重：40%

归一化后（ML权重15%，其他权重85%）：
- 技术指标权重：20% / 100% = 0.20
- 新闻权重：25% / 100% = 0.25
- ML模型权重：15% / 100% = 0.15
- 其他因子权重：40% / 100% = 0.40

最终得分：
```
final_score = 0.5 × 0.20 + 0.3 × 0.25 + 0.7 × 0.15 + 0.4 × 0.40
            = 0.10 + 0.075 + 0.105 + 0.16
            = 0.44
```

转换为概率：
```
up_probability = 1 / (1 + exp(-0.44 × 3))
               = 1 / (1 + exp(-1.32))
               = 1 / (1 + 0.267)
               = 0.789 (78.9%)
```

---

## 三、模型激活机制

### 3.1 如何激活模型

**方式1：训练时自动激活**

```python
# 训练脚本中可以设置 is_active=True
train_base_models(
    ...,
    is_active=True  # 训练完成后自动激活
)
```

**方式2：手动激活（推荐）**

1. 在设置页面 > 模型学习 > 模型训练 > 已训练模型列表
2. 找到要激活的模型
3. 点击"激活"按钮
4. 系统会自动：
   - 取消同类型其他模型的激活状态
   - 激活选定的模型
   - 清除模型缓存，确保使用新模型

**代码位置**：`utils/ml_model_manager.py` 第280-320行

```python
def activate_model(self, model_id: int) -> bool:
    # 1. 获取模型类型
    # 2. 取消同类型其他模型的激活状态
    # 3. 激活指定模型
    # 4. 清除缓存
```

---

### 3.2 模型优先级

**加载优先级**：
1. **分类器模型**（优先）
   - XGBoost分类器 > LightGBM分类器
2. **回归器模型**（备选）
   - XGBoost回归器 > LightGBM回归器
3. **无模型**（降级）
   - 自动降级为传统多因子预测

**代码位置**：`utils/ml_predictor_integration.py` 第51-77行

---

## 四、模型缓存机制

### 4.1 缓存策略

**内存缓存**：
- 模型加载后缓存在内存中（`_model_cache`）
- 避免重复从文件系统加载
- 提高预测速度

**缓存键**：
```python
cache_key = f"{model_type}_{version or 'active'}"
# 例如：'xgb_classifier_active'
```

**缓存清除时机**：
- 激活新模型时自动清除
- 可以手动调用 `clear_cache()` 方法

---

### 4.2 模型文件检查

**加载前检查**：
1. 检查数据库中的模型记录是否存在
2. 检查模型文件是否存在
3. 如果文件不存在，记录错误并返回None

**错误处理**：
- 如果模型加载失败，自动降级为传统预测
- 不影响主流程，只记录警告日志

---

## 五、数据持久化保证

### 5.1 数据保存保证

**模型文件保存**：
- ✅ 使用 `pickle.dump()` 保存模型对象
- ✅ 文件保存在 `models/` 目录下
- ✅ 文件名包含时间戳，避免覆盖

**数据库保存**：
- ✅ 使用事务保证数据一致性
- ✅ 保存完整的模型元数据
- ✅ 支持版本管理（通过 `model_version`）

**备份建议**：
- 定期备份 `models/` 目录
- 定期备份 `trained_models` 表
- 建议使用系统备份功能

---

### 5.2 数据恢复

**如果模型文件丢失**：
- ❌ 无法恢复，需要重新训练
- ✅ 数据库中的元数据仍然保留，可以查看训练历史

**如果数据库记录丢失**：
- ✅ 可以从文件系统恢复（通过文件名识别）
- ⚠️ 需要手动重新创建数据库记录

**最佳实践**：
- 定期备份模型文件和数据库
- 训练完成后立即验证文件是否保存成功
- 保留多个版本的模型，方便回退

---

## 六、使用示例

### 6.1 查看已保存的模型

**通过Web界面**：
1. 设置页面 > 模型学习 > 模型训练
2. 在"已训练模型列表"中查看所有模型
3. 点击"详情"查看完整的模型信息

**通过数据库查询**：
```sql
-- 查看所有模型
SELECT * FROM trained_models ORDER BY created_at DESC;

-- 查看激活的模型
SELECT * FROM trained_models WHERE is_active = 1;

-- 查看特定类型的模型
SELECT * FROM trained_models WHERE model_type = 'xgb_classifier';
```

**通过文件系统**：
```bash
# 查看模型文件
ls -lh models/xgb_classifier/

# 查看模型配置
cat models/xgb_classifier/*_config.json
```

---

### 6.2 验证模型是否生效

**方法1：查看预测日志**
```
2026-01-14 15:40:00 - INFO - ML模型预测: 得分 0.65, 上涨概率 82.50%, 方向 上涨, 置信度 65.00%
```

**方法2：查看预测结果**
- 预测结果中包含 `ml_prediction` 字段
- 如果 `available: true`，说明ML模型已生效

**方法3：对比预测准确率**
- 使用ML模型前后的预测准确率对比
- 在"性能评估"中查看

---

## 七、常见问题

### Q1: 训练后模型保存在哪里？

**A**: 
- **模型文件**：`smart_stock_advisor/models/<模型类型>/` 目录
- **模型元数据**：数据库 `trained_models` 表
- **训练日志**：`logs/` 目录

### Q2: 模型如何自动应用到预测？

**A**: 
- 训练完成后需要**手动激活**模型
- 激活后，系统在每次预测时自动加载并使用
- 模型会被缓存，提高预测速度

### Q3: 如果模型文件被删除怎么办？

**A**: 
- 模型文件被删除后无法使用
- 需要重新训练模型
- 建议定期备份模型文件

### Q4: 如何知道ML模型是否在预测中生效？

**A**: 
- 查看预测日志，如果有"ML模型预测"信息，说明已生效
- 查看预测结果中的 `ml_prediction` 字段
- 对比使用ML模型前后的预测准确率

### Q5: 可以同时使用多个模型吗？

**A**: 
- 同一类型只能有一个激活的模型
- 但可以训练多个模型，然后选择表现最好的激活
- 不同类型的模型可以同时激活（如分类器和回归器）

### Q6: 模型文件会占用多少空间？

**A**: 
- 单个模型文件：通常 5-50 MB（取决于特征数量和模型复杂度）
- 10个模型：约 50-500 MB
- 建议定期清理旧版本的模型文件

---

## 八、最佳实践

1. **训练后立即验证**：
   - 检查模型文件是否保存成功
   - 检查数据库记录是否创建
   - 查看训练指标是否合理

2. **激活前评估**：
   - 对比多个模型的验证准确率
   - 查看特征重要性是否合理
   - 选择表现最好的模型激活

3. **定期备份**：
   - 备份模型文件目录
   - 备份数据库表
   - 保留多个版本的模型

4. **监控模型表现**：
   - 定期查看预测准确率
   - 如果表现下降，考虑重训
   - 记录模型使用情况

5. **清理旧模型**：
   - 定期删除旧版本的模型文件
   - 保留最近3-5个版本的模型
   - 清理未激活的模型（可选）

---

**最后更新**：2026-01-14
