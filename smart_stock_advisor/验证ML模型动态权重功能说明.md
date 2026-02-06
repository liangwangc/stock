# 验证ML模型动态权重功能说明

## 问题诊断

**现象**：执行 `py main.py --symbol 600519` 时，没有看到 "ML模型预测: … 动态权重 xx.xx%" 的日志。

**原因**：数据库中没有激活的ML模型，所以ML预测被跳过了。

## 解决步骤

### 步骤1：训练ML模型

执行以下命令训练一个分类器模型：

```bash
cd D:\wjw_work\smart_stock_advisor
py scripts/train_base_model.py --train-start 2023-01-01 --train-end 2024-12-31 --val-start 2025-01-01 --val-end 2025-12-31 --test-start 2026-01-01 --test-end 2026-12-31 --models xgb_classifier lgb_classifier
```

**注意**：训练可能需要较长时间（根据数据量，可能需要几分钟到几十分钟）。

### 步骤2：激活模型

训练完成后，有两种方式激活模型：

#### 方式1：通过Web界面（推荐）

1. 启动Web应用：
   ```bash
   py web_app.py
   ```

2. 打开浏览器访问：`http://localhost:5000`

3. 登录后，进入：**设置页面 -> 模型训练 -> 已训练模型列表**

4. 找到刚才训练的模型，点击 **"激活"** 按钮

#### 方式2：通过数据库直接激活

```sql
-- 查看所有模型
SELECT id, model_name, model_type, is_active, created_at 
FROM trained_models 
ORDER BY created_at DESC;

-- 激活指定模型（将 {model_id} 替换为实际的模型ID）
UPDATE trained_models SET is_active = 1 WHERE id = {model_id};

-- 取消其他同类型模型的激活状态
UPDATE trained_models 
SET is_active = 0 
WHERE model_type = (SELECT model_type FROM trained_models WHERE id = {model_id})
  AND id != {model_id};
```

### 步骤3：验证功能

激活模型后，再次执行预测命令：

```bash
py main.py --symbol 600519
```

**预期输出**：你应该能看到类似这样的日志：

```
ML模型预测: 得分 0.25, 上涨概率 56.25%, 方向 上涨, 置信度 12.50%, 动态权重 15.00%
```

**说明**：
- 如果模型性能数据不存在，会使用默认权重 **15.00%**
- 如果模型有性能数据，权重会根据准确率动态调整（0-25%之间）

## 验证动态权重调整

### 方法1：手动更新模型性能数据

可以通过以下方式测试动态权重：

```python
from utils.ml_model_performance_monitor import get_performance_monitor

monitor = get_performance_monitor()

# 更新模型性能（假设模型ID为1，准确率为65%）
monitor.update_performance(model_id=1, accuracy=0.65, prediction_count=100)

# 再次执行预测，应该看到权重变为 15-25% 之间
```

### 方法2：查看权重计算逻辑

权重计算规则（在 `utils/ml_model_performance_monitor.py` 中）：

- **性能好（准确率>60%）**：权重 15-25%
  - 准确率 60% → 权重 15%
  - 准确率 100% → 权重 25%
  
- **性能一般（准确率50-60%）**：权重 10-15%
  - 准确率 50% → 权重 10%
  - 准确率 60% → 权重 15%
  
- **性能差（准确率<50%）**：权重 0-10%
  - 准确率 0% → 权重 0%
  - 准确率 50% → 权重 10%

## 检查脚本

我已经创建了一个检查脚本，可以随时查看ML模型状态：

```bash
py scripts/check_ml_model_status.py
```

这个脚本会：
1. 列出所有ML模型（包括激活状态）
2. 测试ML模型集成是否正常工作
3. 显示每个激活模型的动态权重

## 总结

**当前状态**：没有激活的ML模型，所以看不到ML预测日志。

**下一步**：
1. 训练ML模型
2. 激活模型
3. 再次执行预测，就能看到 "ML模型预测: … 动态权重 xx.xx%" 的日志了

**注意**：即使没有ML模型，预测系统仍然可以正常工作，只是不会使用ML模型的预测结果（ML权重为0）。
