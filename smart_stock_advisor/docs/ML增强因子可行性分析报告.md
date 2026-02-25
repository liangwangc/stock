# ML 机构级增强因子 — 可行性分析报告

> 目标：在**不删除现有 50 个因子**的前提下，对 `ml_feature_engineering.prepare_features` 进行增强，新增横截面排名、相对强弱、Delta、突破、市场因子。  
> 约束：无未来函数、不破坏训练结构、不改变 target、所有 rolling 必须 shift(1)、新增因子自动处理 NaN。  
> **结论：仅靠 prepare_features 无法完成全部增强，需与 ml_data_loader 协同；部分因子可仅在 prepare_features 内实现。**

---

## 一、现有数据流与 prepare_features 的输入

### 1.1 两条训练数据来源

| 路径 | 入口 | 输出 DataFrame 结构 |
|------|------|----------------------|
| **A** | `load_training_data(start_date, end_date)` | 来自 `stock_predictions` + 每只股票 **60 日** `stock_history_data`；每行 = 一个 (symbol, target_date) 样本，特征为 **目标日前一天** 的截面快照 |
| **B** | `load_training_data_from_history(start_date, end_date)` | 直接来自 `stock_history_data` 全表；每行 = 一个 (symbol, target_date) 样本，特征为 **target_date 当日** 的快照 |

共同点：

- 传入 `prepare_features(df, ...)` 的 `df` 是 **行=样本、列=特征+元数据+标签** 的扁平表。
- 每行只有 **一个截面**：每个特征列在该行只有一个数值（例如一个 `close_price`、一个 `rsi`），**没有该股票的时间序列**。
- 元数据列包含：`symbol`、`target_date`，路径 B 还有 `future_date`。  
- 标签列：`label_up`、`label_direction`、`label_change_pct` 等。

因此：

- **横截面**：可以按 `target_date` 做 `groupby('target_date')`，同一交易日多只股票在同一组内。
- **时间序列**：在 `df` 内**没有**每只股票的多日序列，无法在 `prepare_features` 里用 `pct_change(5)`、`rolling(20).max()`、`shift(5)` 等做“单股时序”计算。

### 1.2 prepare_features 当前逻辑（摘要）

- 从 `df` 中排除元数据与标签列（如 `symbol`, `target_date`, `prediction_date`, `label_*`），得到候选特征列。
- 可选：按列缺失率过滤（`filter_by_completeness`）。
- 提取 `X = df[feature_columns]`，`y = df[label_column]`。
- 对 `X` 做缺失/无穷处理（`_handle_missing_values`, `_handle_inf_values`），不改变现有列集合外的逻辑。

因此，“仅在 prepare_features 内增强” = 只能使用 **当前 df 已有列** 做**截面或简单变换**（如排名、与外部表 merge），**不能**从无到有造出需要多日序列的因子（如 return_5d、rolling 突破、delta）。

---

## 二、五类增强因子的可行性

### 2.1 第一类：横截面排名因子

需求：

- `return_5d_rank_all`, `return_20d_rank_all`：需先有 `return_5d` / `return_20d`（例如 5/20 日收益率，且**必须 shift(1)** 再参与排名，避免未来函数）。
- `volume_rank_all`, `turnover_rank_all`, `amount_rank_all`：对当日（或当前截面日）的 volume / turnover_rate / amount 做截面排名。

结论：

- **return_*_rank_all**：  
  - `return_5d` / `return_20d` 需要“过去 5/20 日收盘价”，当前 `df` 只有截面快照，**无法在 prepare_features 内计算**。  
  - 必须在 **ml_data_loader** 中，在构造每行时从该股的 60 日序列里算出 `return_5d` / `return_20d`（并保证 shift(1)，即用 T-1 及之前数据），写入该行。  
  - `prepare_features` 在拿到含 `return_5d`、`return_20d` 的 `df` 后，可做：  
    `df.groupby('target_date')['return_5d'].rank(pct=True)`（同理 return_20d），**可行**。
- **volume / turnover / amount 排名**：  
  - 当前 `df` 已有 `volume`、`turnover_rate`、`amount`（均为截面值）。  
  - 在 **prepare_features 内** 直接做：  
    `df.groupby('target_date')['volume'].rank(pct=True)` 等，**无需改 loader，可行**。  
  - 若严格要求“排名用 T-1 数据”，则需 loader 提供 T-1 的 volume/turnover/amount 列（当前为 T 或 T-1 视路径 A/B 而定），再在 prepare_features 里只做排名。

**小结**：  
- 仅 prepare_features：可做 **volume_rank_all, turnover_rank_all, amount_rank_all**（3 个）。  
- return_5d_rank_all / return_20d_rank_all：**依赖 loader 先写入 return_5d / return_20d（且 shift(1)）**，prepare_features 只负责排名。

---

### 2.2 第二类：相对强弱因子（股票 vs 指数）

需求：

- `relative_strength_5d`, `relative_strength_20d`, `relative_strength_60d` = 个股 5/20/60 日收益 − 指数 5/20/60 日收益。

结论：

- 个股 5/20/60 日收益：同样需要**时序**，当前 `df` 没有，**必须在 loader 中**按股、按日算好并 shift(1)，写入每行（例如 `return_5d`, `return_20d`, `return_60d`）。
- 指数收益：项目内已有 **market_indices** 表（如 `index_code`, `trade_date`, `close_price`），可读沪深300/上证等。  
  - 若在 **prepare_features** 内：根据 `df['target_date']` 的日期范围拉取指数日线，算指数 1d/5d/20d/60d 收益（并 shift(1)），再按 `target_date` merge 回 `df`，然后计算 relative_strength_* = 个股 return_* − 指数 return_*。  
  - 前提：loader 已提供 `return_5d`, `return_20d`, `return_60d`。

**小结**：  
- **可行**，但**依赖 loader 先提供** `return_5d` / `return_20d` / `return_60d`（无未来函数）。  
- prepare_features 可负责：读指数表 → 算指数收益（shift(1)）→ merge → 算 relative_strength_*；或改为在 loader 里统一算好再进 prepare_features。

---

### 2.3 第三类：因子变化率（Delta）

需求：

- `rsi_change_5d`, `macd_hist_change_5d`, `volume_ratio_change_5d`, `turnover_rate_change_5d`, `main_net_inflow_change_5d`  
- 逻辑示例：`rsi_change_5d = rsi - rsi.shift(5)`，且需 shift(1) 再作为特征。

结论：

- 每行只有**一个** rsi / macd_hist / volume_ratio / turnover_rate / main_net_inflow，没有该股过去 5 日的序列，**无法在 prepare_features 内做 shift(5)**。  
- 必须在 **loader** 中，在构造该行时从该股 60 日序列里算：当前值 − 5 日前值（并保证整体 shift(1)），写入如 `rsi_change_5d` 等列。

**小结**：  
- **仅 prepare_features 不可行**；**必须在 ml_data_loader 中实现**（两处：`_extract_features_from_history` 与 `load_training_data_from_history` 的 process_single_stock 循环）。

---

### 2.4 第四类：突破因子

需求：

- `is_20d_high` = close_price >= rolling(20).max().shift(1)  
- `is_60d_high` = close_price >= rolling(60).max().shift(1)  
- `is_volume_breakout` = volume >= rolling(20).max().shift(1)  
- 输出 0/1。

结论：

- 同样需要**每只股票在当日的 rolling(20).max() / rolling(60).max()**，且必须用 shift(1) 避免未来函数。  
- 当前 `df` 只有截面 close_price、volume，**无法在 prepare_features 内计算**。  
- 必须在 **loader** 中，从该股 60 日（或更长）序列里算 rolling(20).max().shift(1) 等，再与当日 close/volume 比较，得到 0/1，写入该行。

**小结**：  
- **仅 prepare_features 不可行**；**必须在 ml_data_loader 中实现**。

---

### 2.5 第五类：市场环境因子

需求：

- `index_return_1d`, `index_return_5d`, `index_return_20d`, `index_volatility_20d`  
- 指数收益率 = index_close.pct_change()，波动率 = rolling(20).std()，且均需 shift(1)。

结论：

- 不依赖个股时序，只依赖**指数日线**。  
- 项目已有 **market_indices** 表（或可用的指数数据源），可按 `df['target_date']` 的日期范围取指数序列，在 **prepare_features** 内（或单独工具函数中）：  
  - 算 index 的 1d/5d/20d 收益、20d 波动率；  
  - 全部 shift(1) 后，按 `trade_date` 对齐到 `target_date`，merge 进 `df`。  
- 不在 loader 里改个股循环，**仅改 prepare_features（及可选的小工具）即可**。

**小结**：  
- **可行，且可仅在 prepare_features 侧实现**（需传入或内部读取指数数据，并保证 shift(1)）。

---

## 三、无未来函数与训练兼容性

### 3.1 无未来函数

- 所有 rolling / pct_change 若作为**特征**使用，必须在计算后 **shift(1)**，保证预测 T+1 时只用 T 及之前信息。  
- 在 **loader** 中新增的 return_*、delta_*、突破_*：在单股时序上算完后，取的是“当前行对应日 T 的 T-1 及之前”的衍生值，等价于 shift(1)。  
- 在 **prepare_features** 中：  
  - 截面排名是对“当日截面”排名，若该截面值本身已是 T 或 T-1（由 loader 约定），则不再额外 shift；若需“用 T-1 截面做排名”，需 loader 提供 T-1 截面列。  
  - 指数收益/波动：必须在指数序列上 shift(1) 后再 merge 到 target_date。

### 3.2 不破坏现有训练结构

- 不删现有 50 个因子，只**追加**新列。  
- `prepare_features` 仍返回 `(X, y, feature_columns)`；feature_columns 在排除 `symbol/target_date/prediction_date/future_date/label_*` 后，**自动包含所有数值型新列**（含新增因子）。  
- 若在 prepare_features 内做“先加列再排除”，只需保证新列名不落在 default_exclude 内，且新列均为数值型；NaN 用现有 `_handle_missing_values` 或新增因子的显式 fillna 即可。

### 3.3 target 与训练脚本

- 不修改 `label_column`、不改 `label_up` 等构造方式；`y = df[label_column]` 不变。  
- `train_ml_models.py` / `train_base_model.py` 等仅调用 `prepare_features(train_df, label_column='label_up')`，无需改接口；只要 `train_df` 列变多（loader 或 prepare_features 加列），新列会自动进入特征集。

---

## 四、实现分工建议（与“仅改 prepare_features”的差异）

若**严格只改 prepare_features**，可实现：

1. **横截面排名（3 个）**：`volume_rank_all`, `turnover_rank_all`, `amount_rank_all`（用现有 volume, turnover_rate, amount，按 target_date groupby 后 rank(pct=True)）。  
2. **市场环境（4 个）**：`index_return_1d`, `index_return_5d`, `index_return_20d`, `index_volatility_20d`（读指数表 → 算收益/波动 → shift(1) → 按 target_date merge）。

合计 **7 个新因子**，且需保证 index 数据可被 prepare_features 访问（如入参传入或内部按 df 的 target_date 范围查询 DB）。

若**允许同时改 ml_data_loader**，则可实现全部需求：

1. **Loader 增加**（两路径都需对齐）：  
   - return_5d, return_20d, return_60d（shift(1)）；  
   - rsi_change_5d, macd_hist_change_5d, volume_ratio_change_5d, turnover_rate_change_5d, main_net_inflow_change_5d；  
   - is_20d_high, is_60d_high, is_volume_breakout。  
2. **prepare_features 增加**：  
   - return_5d_rank_all, return_20d_rank_all（依赖 loader 已写入 return_5d/return_20d）；  
   - volume_rank_all, turnover_rank_all, amount_rank_all；  
   - index_return_1d/5d/20d, index_volatility_20d；  
   - relative_strength_5d/20d/60d（依赖 loader 的 return_5d/20d/60d + 指数收益 merge）。

这样可得到全部 **约 22 个** 新增因子（5+3+5+3+4+2），且满足无未来函数、不破坏训练结构、不改变 target、rolling 均 shift(1)、新因子可统一做 NaN 处理。

---

## 五、指数数据与 NaN 处理

- **指数**：`market_indices` 表存在（index_code, trade_date, close_price 等）；需确认训练用日期范围内是否有足够覆盖（如 000300.SH / sh000300）。若某 target_date 无指数，对应行的新指数因子可为 NaN，再在 prepare_features 内 fillna(0) 或中位数。  
- **NaN**：所有新增列在写入时若不可算则置 NaN；在 prepare_features 末尾的 `_handle_missing_values` 之前或之内，对新增因子列做一次统一 fillna（例如 0 或截面中位数），即可满足“自动处理 NaN”。

---

## 六、结论汇总

| 类别           | 仅 prepare_features | 需 loader 配合 | 说明 |
|----------------|---------------------|-----------------|------|
| 横截面排名     | 3 个（volume/turnover/amount_rank） | 2 个（return_5d/20d_rank 需先有 return_*） | return_* 必须从时序算，只能在 loader |
| 相对强弱       | 否                  | 是              | 需个股 return_* + 指数收益，loader 提供 return_* |
| Delta 因子     | 否                  | 是              | 需时序 shift(5)，只能在 loader |
| 突破因子       | 否                  | 是              | 需 rolling(20/60).max().shift(1)，只能在 loader |
| 市场环境       | 是（4 个）          | 否              | 仅用指数表 + shift(1) merge |

- **仅改 prepare_features**：最多增加 **7 个** 因子（3 个排名 + 4 个指数），且需具备指数数据源。  
- **prepare_features + ml_data_loader 协同**：可完整实现全部 **约 22 个** 机构级增强因子，并满足无未来函数、不破坏训练、不改 target、rolling 全部 shift(1)、新因子统一处理 NaN。

建议：若希望“机构级、五类因子齐全”，采用 **loader + prepare_features 协同** 方案；若先做最小改动，可先只在 **prepare_features** 内实现上述 7 个因子，并为 loader 预留 return_5d/return_20d 等列名，后续再在 loader 中补全并增加其余因子。

---

## 七、已实现说明（与上文一致）

- **Loader**（`utils/ml_data_loader.py`）：  
  - `_extract_features_from_history`：新增 return_5d、return_20d、return_60d；rsi_change_5d、macd_hist_change_5d、volume_ratio_change_5d、turnover_rate_change_5d、main_net_inflow_change_5d；is_20d_high、is_60d_high、is_volume_breakout。  
  - `load_training_data_from_history` 内 process_single_stock：同上，与上述字段一致。  
- **prepare_features**（`utils/ml_feature_engineering.py`）：  
  - 新增 `_add_enhanced_factors(df)`：横截面排名（volume_rank_all、turnover_rank_all、amount_rank_all、return_5d_rank_all、return_20d_rank_all）；指数因子（index_return_1d、index_return_5d、index_return_20d、index_volatility_20d，均 shift(1) 后按 target_date merge）；相对强弱（relative_strength_5d、relative_strength_20d、relative_strength_60d）。  
  - 新增列 NaN 已统一处理（排名填 0.5，其余填 0）。  
- **新增因子数量**：约 22 个（5 排名 + 3 收益 + 5 delta + 3 突破 + 4 指数 + 3 相对强弱，部分列在无指数数据时退化为 0）。  
- **无未来函数**：loader 中区间收益/突破均用“当前截面日及之前”数据；prepare_features 中指数序列 shift(1) 后 merge。  
- **训练兼容**：未改 target、未删原有因子；新列自动进入 feature_columns（未加入 exclude_set），训练脚本无需改接口。
