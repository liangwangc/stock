# stock_list.html 页面预测方向逻辑说明

## 概述

`stock_list.html` 页面显示的**震荡、上涨、下跌**预测方向，是根据**上涨概率**和**下跌概率**计算得出的。

## 前端显示逻辑

### 1. 数据来源

**文件位置**：`smart_stock_advisor/stock_list.html`

**数据获取**（第1306-1320行）：
```javascript
const prediction = String(record.prediction || '震荡').trim();
const up_prob = parseFloat(record.up_probability || 0);
const down_prob = parseFloat(record.down_probability || 0);
```

- `prediction`：预测方向（'上涨'/'下跌'/'震荡'），从后端API返回
- `up_probability`：上涨概率（0-1）
- `down_probability`：下跌概率（0-1）

### 2. 样式和图标设置

**代码位置**：第1322-1331行

```javascript
// 预测样式
let pred_class = 'prediction-neutral';
let pred_icon = '📊';
if (prediction === '上涨') {
    pred_class = 'prediction-up';
    pred_icon = '📈';
} else if (prediction === '下跌') {
    pred_class = 'prediction-down';
    pred_icon = '📉';
}
```

**样式类**：
- `prediction-up`：绿色背景（`#d4edda`），深绿色文字（`#155724`）
- `prediction-down`：红色背景（`#f8d7da`），深红色文字（`#721c24`）
- `prediction-neutral`：灰色背景（`#e2e3e5`），深灰色文字（`#383d41`）

### 3. 显示内容

**代码位置**：第1378-1381行

```javascript
'<div class="stock-prediction ' + pred_class + '">' +
    '<span class="inline-tooltip">' + pred_icon + ' ' + prediction +
    '<span class="tooltip-text">预测方向：<br>• <strong>上涨</strong>：上涨概率 > 60%<br>• <strong>下跌</strong>：下跌概率 > 60%<br>• <strong>震荡</strong>：上涨和下跌概率都 ≤ 60%<br><br>预测方向由综合得分转换为概率后确定，综合考虑技术指标、新闻情感、资金流向、市场情绪等多个因子。</span></span>' +
'</div>'
```

**Tooltip说明**：
- **上涨**：上涨概率 > 60%
- **下跌**：下跌概率 > 60%
- **震荡**：上涨和下跌概率都 ≤ 60%

## 后端计算逻辑

### 1. 预测方向计算

**文件位置**：`smart_stock_advisor/predictor/stock_predictor.py`

**代码位置**：第2820-2826行

```python
# 确定预测方向
if up_probability > 0.6:
    prediction = '上涨'
elif down_probability > 0.6:
    prediction = '下跌'
else:
    prediction = '震荡'
```

**判断规则**：
1. **上涨**：`up_probability > 0.6`（上涨概率 > 60%）
2. **下跌**：`down_probability > 0.6`（下跌概率 > 60%）
3. **震荡**：以上两个条件都不满足（上涨和下跌概率都 ≤ 60%）

### 2. 概率计算

**代码位置**：第2770-2780行（推测位置）

**计算流程**：

#### 步骤1：计算综合得分（final_score）

```python
final_score = (
    technical_score * adjusted_technical_weight +
    news_score * adjusted_news_weight +
    capital_flow_score * adjusted_capital_flow_weight +
    market_score * adjusted_market_weight +
    sector_rotation_score * adjusted_sector_rotation_weight +
    history_score * adjusted_history_weight +
    valuation_score * adjusted_valuation_weight +
    us_sector_score * adjusted_us_sector_weight
)
```

**8个因子及其默认权重**：
- 技术指标：20%
- 新闻情感：25%
- 资金流向：18%
- 市场情绪：17%
- 板块轮动：5%
- 历史模式：8%
- 估值指标：2%
- 美股板块：5%

**权重总和**：100%

#### 步骤2：转换为概率（Sigmoid函数）

**代码位置**：第2770-2775行（推测位置）

```python
# 使用Sigmoid函数将综合得分转换为上涨概率
up_probability = 1 / (1 + np.exp(-final_score * 3))
down_probability = 1 - up_probability
```

**说明**：
- `final_score`：综合得分（范围通常在 -3 到 +3）
- `* 3`：缩放因子，用于调整Sigmoid函数的陡峭程度
- `up_probability`：上涨概率（0-1）
- `down_probability`：下跌概率（0-1），等于 `1 - up_probability`

#### 步骤3：置信度调整（可选）

**代码位置**：第2815-2818行

```python
# 如果置信度太低，降低概率差异
if confidence < min_confidence_threshold:
    up_probability = 0.5 + (up_probability - 0.5) * (confidence / min_confidence_threshold)
    down_probability = 1 - up_probability
```

**说明**：
- 如果置信度低于阈值，会缩小概率差异，使预测更保守
- 这可能导致原本判断为"上涨"或"下跌"的预测变为"震荡"

## 完整数据流程

```
1. 获取8个因子的得分
   ↓
2. 根据权重计算综合得分（final_score）
   ↓
3. 使用Sigmoid函数转换为上涨概率（up_probability）
   ↓
4. 计算下跌概率（down_probability = 1 - up_probability）
   ↓
5. 根据概率判断预测方向：
   - up_probability > 0.6 → '上涨'
   - down_probability > 0.6 → '下跌'
   - 其他 → '震荡'
   ↓
6. 保存到数据库（stock_predictions表）
   ↓
7. API返回给前端（/api/stocks）
   ↓
8. 前端显示预测方向和样式
```

## 示例说明

### 示例1：上涨预测

**场景**：
- 综合得分：`final_score = 1.5`
- 上涨概率：`up_probability = 1 / (1 + exp(-1.5 * 3)) ≈ 0.989`（98.9%）
- 下跌概率：`down_probability = 1 - 0.989 = 0.011`（1.1%）

**判断**：
- `up_probability = 0.989 > 0.6` ✅
- **预测方向**：`'上涨'`

**前端显示**：
- 样式：绿色背景（`prediction-up`）
- 图标：📈
- 文字：上涨

### 示例2：下跌预测

**场景**：
- 综合得分：`final_score = -1.2`
- 上涨概率：`up_probability = 1 / (1 + exp(-(-1.2) * 3)) ≈ 0.027`（2.7%）
- 下跌概率：`down_probability = 1 - 0.027 = 0.973`（97.3%）

**判断**：
- `down_probability = 0.973 > 0.6` ✅
- **预测方向**：`'下跌'`

**前端显示**：
- 样式：红色背景（`prediction-down`）
- 图标：📉
- 文字：下跌

### 示例3：震荡预测

**场景1**：概率接近50%
- 综合得分：`final_score = 0.1`
- 上涨概率：`up_probability = 1 / (1 + exp(-0.1 * 3)) ≈ 0.574`（57.4%）
- 下跌概率：`down_probability = 1 - 0.574 = 0.426`（42.6%）

**判断**：
- `up_probability = 0.574 ≤ 0.6` ❌
- `down_probability = 0.426 ≤ 0.6` ❌
- **预测方向**：`'震荡'`

**场景2**：置信度调整后
- 原始上涨概率：`up_probability = 0.65`（65%）
- 置信度：`confidence = 0.4`（40%，低于阈值）
- 调整后上涨概率：`up_probability = 0.5 + (0.65 - 0.5) * (0.4 / 0.5) = 0.62`（62%）

**判断**：
- `up_probability = 0.62 > 0.6`，但置信度调整后可能变为震荡

**前端显示**：
- 样式：灰色背景（`prediction-neutral`）
- 图标：📊
- 文字：震荡

## 关键代码位置

| 功能 | 文件 | 位置 | 说明 |
|------|------|------|------|
| 前端显示 | `stock_list.html` | 第1322-1331行 | 根据prediction设置样式和图标 |
| 前端Tooltip | `stock_list.html` | 第1378-1381行 | 显示预测方向说明 |
| 预测方向计算 | `predictor/stock_predictor.py` | 第2820-2826行 | 根据概率判断预测方向 |
| 概率计算 | `predictor/stock_predictor.py` | 第2770-2775行 | Sigmoid函数转换 |
| 综合得分计算 | `predictor/stock_predictor.py` | 第2368-2377行 | 8个因子加权求和 |

## 注意事项

1. **阈值固定**：
   - 上涨/下跌的判断阈值固定为 **60%**
   - 如果概率正好等于60%，会被判断为震荡

2. **概率关系**：
   - `up_probability + down_probability = 1`
   - 如果 `up_probability > 0.6`，则 `down_probability < 0.4`
   - 如果 `down_probability > 0.6`，则 `up_probability < 0.4`

3. **置信度影响**：
   - 如果置信度太低，可能会调整概率，使预测更保守
   - 这可能导致原本判断为"上涨"或"下跌"的预测变为"震荡"

4. **数据来源**：
   - 预测方向在后端计算，前端只是显示
   - 前端无法修改预测方向，只能根据后端返回的数据显示

5. **过滤功能**：
   - 前端提供了按预测方向过滤的功能（第515-520行，560-565行）
   - 用户可以选择只显示"上涨"、"下跌"或"震荡"的股票

## 总结

**预测方向判断规则**：
- **上涨**：上涨概率 > 60%
- **下跌**：下跌概率 > 60%
- **震荡**：上涨和下跌概率都 ≤ 60%

**计算流程**：
1. 8个因子得分 → 综合得分（加权求和）
2. 综合得分 → 上涨概率（Sigmoid函数）
3. 上涨概率 → 下跌概率（1 - 上涨概率）
4. 概率 → 预测方向（阈值判断）

**前端显示**：
- 根据预测方向设置不同的样式和图标
- 提供Tooltip说明预测方向的判断规则
