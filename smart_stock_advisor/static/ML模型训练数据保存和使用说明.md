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
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `model_name` VARCHAR(100) NOT NULL COMMENT '模型名称',
    `model_type` VARCHAR(50) NOT NULL COMMENT '模型类型：xgb_classifier, lgb_classifier等',
    `version` VARCHAR(50) NOT NULL COMMENT '版本号',
    `file_path` VARCHAR(500) NOT NULL COMMENT '模型文件路径',
    `features` TEXT COMMENT '特征列表（JSON格式）',
    `feature_importance` TEXT COMMENT '特征重要性（JSON格式）',
    `training_metrics` TEXT COMMENT '训练指标（JSON格式）',
    `train_start_date` DATE COMMENT '训练集开始日期',
    `train_end_date` DATE COMMENT '训练集结束日期',
    `val_start_date` DATE COMMENT '验证集开始日期',
    `val_end_date` DATE COMMENT '验证集结束日期',
    `is_active` TINYINT(1) DEFAULT 0 COMMENT '是否激活（0=未激活，1=激活）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_model_type` (`model_type`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='已训练模型表';
```

**保存的字段说明**：

| 字段 | 说明 | 示例 |
|------|------|------|
| `model_name` | 模型名称 | `xgb_classifier_base_v20260114_153000` |
| `model_type` | 模型类型 | `xgb_classifier` |
| `version` | 版本号 | `v20260114_153000` |
| `file_path` | 模型文件路径 | `models/xgb_classifier/xgb_classifier_base_v20260114_153000.pkl` |
| `features` | 特征列表（JSON） | `["open", "high", "low", "close", ...]` |
| `feature_importance` | 特征重要性（JSON） | `{"close": 0.15, "volume": 0.12, ...}` |
| `training_metrics` | 训练指标（JSON） | `{"accuracy": 0.65, "precision": 0.68, ...}` |
| `is_active` | 是否激活 | `1`（激活）或 `0`（未激活） |

**保存代码位置**：
- `utils/ml_model_trainer.py` 第470-520行：`save_model_metadata()` 方法

---

## 二、模型的使用

### 2.1 模型加载流程

**代码位置**：`predictor/ml_predictor.py`

**加载步骤**：

1. **从数据库查询激活的模型**
   ```python
   SELECT * FROM trained_models 
   WHERE model_type = ? AND is_active = 1 
   ORDER BY created_at DESC LIMIT 1
   ```

2. **加载模型文件**
   ```python
   import pickle
   with open(model_file_path, 'rb') as f:
       model = pickle.load(f)
   ```

3. **加载特征列表**
   ```python
   import json
   with open(features_file_path, 'r', encoding='utf-8') as f:
       features = json.load(f)
   ```

4. **准备预测数据**
   - 从 `stock_history_data` 表获取股票历史数据
   - 提取与训练时相同的特征
   - 确保特征顺序与训练时一致

5. **执行预测**
   ```python
   prediction = model.predict_proba(features_array)
   ```

---

### 2.2 模型在预测系统中的权重

**权重分配**：
- ML模型权重：**15%**
- 其他8个因子权重：**85%**

**权重平衡**：
- 系统会自动归一化权重，确保总权重为100%
- ML模型预测失败时，自动降级为传统多因子预测（不影响主流程）

**预测逻辑**：
```
最终得分 = ML模型得分 × 15% + 其他因子得分 × 85%
上涨概率 = Sigmoid(最终得分)
```

**代码位置**：
- `predictor/stock_predictor.py` 第200-250行：`predict()` 方法

---

## 三、模型激活

### 3.1 激活方式

**方式1：通过Web界面激活**
1. 进入"设置"页面
2. 点击"模型学习"页签
3. 在"已训练模型列表"中找到要激活的模型
4. 点击"激活"按钮

**方式2：通过API激活**
```bash
POST /api/ml/models/<model_id>/activate
```

**方式3：通过数据库直接激活**
```sql
-- 先取消所有模型的激活状态
UPDATE trained_models SET is_active = 0;

-- 激活指定模型
UPDATE trained_models SET is_active = 1 WHERE id = ?;
```

---

### 3.2 激活后的影响

**立即生效**：
- 激活后，下一次预测时会自动使用新激活的模型
- 不需要重启服务

**影响范围**：
- 所有股票的预测都会使用新激活的模型
- ML模型权重仍为15%，不会改变

**代码位置**：
- `web_app.py` 第5162-5183行：`api_activate_model()` 方法

---

## 四、模型版本管理

### 4.1 版本号规则

**格式**：`v<日期>_<时间>`

**示例**：
- `v20260114_153000`：2026年1月14日15:30:00训练的模型
- `v20260115_090000`：2026年1月15日09:00:00训练的模型

**代码位置**：
- `utils/ml_model_trainer.py` 第100-120行：`_generate_version()` 方法

---

### 4.2 多版本共存

**特点**：
- 可以同时存在多个版本的模型
- 只有激活的模型会被使用
- 历史版本可以保留用于对比分析

**管理建议**：
- 保留最近3-5个版本的模型
- 定期清理旧版本模型文件（手动删除）

---

## 五、常见问题

### Q1: 训练完成后模型没有自动激活？

**A**: 是的，训练完成后模型不会自动激活，需要手动激活。这是为了避免新训练的模型影响正在运行的预测系统。

---

### Q2: 如何查看模型的训练指标？

**A**: 
1. 通过Web界面：在"模型学习"页签的"已训练模型列表"中查看
2. 通过数据库：查询 `trained_models` 表的 `training_metrics` 字段（JSON格式）

---

### Q3: 模型文件可以删除吗？

**A**: 
- **已激活的模型**：不能删除，删除后会导致预测失败
- **未激活的模型**：可以删除，但建议先备份

---

### Q4: 如何备份模型？

**A**: 
1. **备份模型文件**：复制 `models/` 目录下的文件
2. **备份数据库记录**：导出 `trained_models` 表的数据

---

### Q5: 模型训练失败怎么办？

**A**: 
1. 查看训练日志：`logs/` 目录下的日志文件
2. 检查数据完整性：确保有足够的训练样本
3. 检查依赖库：确保所有依赖库已正确安装

---

## 六、最佳实践

### 6.1 训练频率建议

**基础模型（历史数据训练）**：
- 首次训练：系统部署后必须训练一次
- 定期重训：建议每3-6个月重新训练一次
- 不建议频繁训练：历史数据相对稳定，频繁训练可能导致过拟合

**微调模型（预测数据训练）**：
- 建议频率：每周执行1-2次（如每周日晚上）
- 最少样本：需要至少1000条有实际结果的预测记录
- 数据积累：新系统需要运行1-2周积累足够数据后才能进行微调

---

### 6.2 模型评估建议

**评估指标**：
- 方向准确率：预测方向（上涨/下跌）的准确率
- 收益率：使用模型预测进行模拟交易的收益率
- 胜率：盈利交易占总交易的比例
- 最大回撤：最大亏损幅度

**评估频率**：
- 每次训练后评估一次
- 每月定期评估一次

---

### 6.3 模型激活建议

**激活前检查**：
1. 查看训练指标，确保模型性能良好
2. 对比新旧模型的性能差异
3. 在非交易时间激活，避免影响实时预测

**激活后监控**：
1. 监控预测准确率变化
2. 观察系统运行是否正常
3. 如有问题，及时回退到之前的模型

---

## 七、技术细节

### 7.1 特征提取

**特征类型**：
- 基础价格特征（7个）：开盘价、最高价、最低价、收盘价、涨跌幅等
- 成交特征（4个）：成交量、成交额、换手率等
- 技术指标特征（9个）：MA、MACD、RSI、KDJ等
- 资金流向特征（5个）：主力资金、散户资金等
- 估值特征（4个）：PE、PB、市值等
- 融资融券特征（3个）：融资余额、融券余额等
- 衍生特征（10+个）：价格变化率、成交量变化率等
- 时间序列特征（10+个）：历史价格趋势、波动率等

**总计**：约50+个特征

**代码位置**：
- `utils/ml_data_loader.py` 第100-300行：特征提取逻辑

---

### 7.2 数据划分

**训练集**：用于训练模型
**验证集**：用于调整超参数和评估模型性能
**测试集**：用于最终评估模型性能（可选）

**划分方式**：按时间顺序划分，确保时间序列的连续性

**代码位置**：
- `utils/ml_data_loader.py` 第400-500行：数据划分逻辑

---

### 7.3 模型保存格式

**Pickle格式**：
- Python标准序列化格式
- 可以保存完整的Python对象
- 文件大小较大，但加载速度快

**JSON格式**：
- 用于保存配置和元数据
- 人类可读，便于调试
- 文件大小较小

---

## 八、相关文档

- [ML模型训练完整命令参考.md](../ML模型训练完整命令参考.md)
- [ML模型训练快速开始.md](../ML模型训练快速开始.md)
- [开始训练ML模型.md](../开始训练ML模型.md)
- [训练命令参考.md](../训练命令参考.md)

---

**最后更新**：2026-01-15
