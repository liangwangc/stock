# stock_type字段支持说明

## 📋 修改概述

已修改代码以支持使用 `stock_type` 字段来分类显示预测数据。代码会自动检测数据库中是使用 `stock_type` 还是 `prediction_type` 字段，并自动进行值映射。

## 🔄 字段映射

### prediction_type → stock_type 值映射

| prediction_type值 | stock_type值 | 说明 |
|------------------|-------------|------|
| `after_close` | `收盘-明日` | 收盘后预测的明日走势 |
| `before_close` | `未收盘-明日` | 未收盘时预测的明日走势 |

### stock_type → prediction_type 值映射（反向）

| stock_type值 | prediction_type值 | 说明 |
|-------------|------------------|------|
| `收盘-明日` | `after_close` | 收盘后预测的明日走势 |
| `未收盘-明日` | `before_close` | 未收盘时预测的明日走势 |

## 🔧 代码修改

### 1. 添加映射函数（`utils/stock_prediction_db.py`）

```python
@staticmethod
def _map_prediction_type_to_stock_type(prediction_type: str) -> str:
    """将prediction_type值映射到stock_type值"""
    mapping = {
        'after_close': '收盘-明日',
        'before_close': '未收盘-明日'
    }
    return mapping.get(prediction_type, prediction_type)

@staticmethod
def _map_stock_type_to_prediction_type(stock_type: str) -> str:
    """将stock_type值映射回prediction_type值"""
    mapping = {
        '收盘-明日': 'after_close',
        '未收盘-明日': 'before_close'
    }
    return mapping.get(stock_type, stock_type)
```

### 2. 修改字段检测逻辑

代码会优先检查 `stock_type` 字段是否存在：
- ✅ 如果存在 `stock_type` 字段，使用该字段
- ✅ 如果不存在，回退到 `prediction_type` 字段（向后兼容）

### 3. 修改查询逻辑（`get_predictions` 方法）

- 自动检测字段类型
- 如果使用 `stock_type`，自动映射查询值
- 支持两种字段的查询

### 4. 修改保存逻辑（`save_prediction` 方法）

- 自动检测字段类型
- 如果使用 `stock_type`，自动映射保存值
- 所有SQL分支都支持两种字段

### 5. 修改最新预测查询（`get_latest_predictions` 方法）

- 自动检测字段类型
- 如果使用 `stock_type`，自动映射查询值

## 📊 页面显示逻辑

### stock_list.html 页面

**页签1：收盘-明日**
- 查询参数：`prediction_type=after_close`
- 数据库查询：`stock_type='收盘-明日'` 或 `prediction_type='after_close'`
- 显示：收盘后预测的明日走势

**页签2：未收盘-明天**
- 查询参数：`prediction_type=before_close`
- 数据库查询：`stock_type='未收盘-明日'` 或 `prediction_type='before_close'`
- 显示：未收盘时预测的明日走势

## ✅ 兼容性

### 向后兼容

代码完全向后兼容：
- ✅ 如果数据库有 `stock_type` 字段，使用该字段
- ✅ 如果数据库只有 `prediction_type` 字段，使用该字段
- ✅ 前端代码无需修改，继续使用 `prediction_type` 参数

### 自动映射

- ✅ 保存时：`after_close` → `收盘-明日`，`before_close` → `未收盘-明日`
- ✅ 查询时：自动识别字段类型并使用正确的值

## 🔍 验证方法

### 1. 检查数据库字段

```sql
-- 检查字段是否存在
SHOW COLUMNS FROM stock_predictions LIKE 'stock_type';
SHOW COLUMNS FROM stock_predictions LIKE 'prediction_type';

-- 查看数据分布
SELECT stock_type, COUNT(*) as count 
FROM stock_predictions 
GROUP BY stock_type;
```

### 2. 测试页面显示

1. 打开 `stock_list.html`
2. 切换到"📈 股票预测列表（收盘-明日）"页签
   - 应该只显示 `stock_type='收盘-明日'` 或 `prediction_type='after_close'` 的记录
3. 切换到"⏰ 股票预测列表（未收盘-明天）"页签
   - 应该只显示 `stock_type='未收盘-明日'` 或 `prediction_type='before_close'` 的记录

### 3. 测试保存

1. 执行"收盘-明日"预测
   - 应该保存为 `stock_type='收盘-明日'` 或 `prediction_type='after_close'`
2. 执行"未收盘-明天"预测
   - 应该保存为 `stock_type='未收盘-明日'` 或 `prediction_type='before_close'`

## 📝 注意事项

1. **字段优先级**：代码优先使用 `stock_type` 字段，如果不存在则使用 `prediction_type` 字段
2. **值映射**：如果使用 `stock_type` 字段，值会自动映射
3. **前端无需修改**：前端继续使用 `prediction_type` 参数，后端自动处理映射
4. **数据迁移**：如果需要从 `prediction_type` 迁移到 `stock_type`，可以运行迁移脚本

## 🚀 下一步

1. ✅ 确认数据库中有 `stock_type` 字段
2. ✅ 验证页面正确分类显示
3. ✅ 测试保存功能是否正确映射值
4. ✅ 检查旧数据是否需要迁移
