"""
为实时交易决策打上“事后收益标签”的脚本

用途：
  - 读取 data/realtime_trading_decisions_data.csv 中的每一条实时决策
  - 根据决策时间之后的价格表现，计算简单的收益率，并根据阈值打上 outcome_label
  - 结果直接写回同一个 CSV，新增三列：
      future_price, future_return_pct, outcome_label

标签规则（简单版，可以后续再调）：
  - 对 BUY / ADD 信号：
      future_return_pct >= +2% -> 'good'
      -2% < future_return_pct < +2% -> 'neutral'
      future_return_pct <= -2% -> 'bad'
  - 对 SELL / REDUCE 信号：
      future_return_pct <= -2% -> 'good'   （卖出后确实跌了）
      -2% < future_return_pct < +2% -> 'neutral'
      future_return_pct >= +2% -> 'bad'    （卖飞了）
  - 其它 action -> 'unknown'

未来价格定义（简单起步版）：
  - 以 T+1 日（决策日期之后的下一个交易日）的收盘价为 future_price

运行方式（在 smart_stock_advisor 目录下）：
  py -m analysis.label_realtime_outcomes
"""

import os
from datetime import datetime, timedelta

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def load_csv_safely(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        print(f"[WARN] 找不到文件: {path}")
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception as e:
        print(f"[ERROR] 读取 {path} 失败: {e}")
        return pd.DataFrame()


def get_stock_data_source():
    """动态加载 StockDataSource，避免直接依赖包结构。"""
    import importlib.util

    ds_path = os.path.join(PROJECT_ROOT, "data_source", "stock_data_source.py")
    spec = importlib.util.spec_from_file_location("stock_data_source_module", ds_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.StockDataSource()


def get_next_trading_close(ds, symbol: str, decision_date: str):
    """
    获取决策日期之后的下一个交易日的收盘价。

    Args:
        ds: StockDataSource 实例
        symbol: 股票代码（字符串，可能带/不带交易所前缀）
        decision_date: 'YYYY-MM-DD'
    """
    try:
        # 取决策日之后一段时间的日线，然后找第一天 > 决策日 的记录
        start_dt = datetime.strptime(decision_date, "%Y-%m-%d") + timedelta(days=1)
        end_dt = start_dt + timedelta(days=15)  # 往后找一段时间

        # StockDataSource.get_stock_data 接受 days，不接受日期区间，这里简单用最近 N 天近似
        # 为了稳妥，获取最近 90 天，再从中筛选 > 决策日 的记录
        df = ds.get_stock_data(symbol, days=90)
        if df is None or df.empty:
            return None

        # 假定 df.index 或 'date' 列是日期
        if "date" in df.columns:
            dates = pd.to_datetime(df["date"])
        else:
            dates = pd.to_datetime(df.index)

        mask = dates > pd.to_datetime(decision_date)
        future_df = df.loc[mask]
        if future_df.empty:
            return None

        # 取第一天的收盘价
        if "close" in future_df.columns:
            return float(future_df.iloc[0]["close"])
        # 兜底：尝试 price 列
        if "price" in future_df.columns:
            return float(future_df.iloc[0]["price"])
        return None
    except Exception as e:
        print(f"[WARN] 获取 {symbol} 决策日后的价格失败: {e}")
        return None


def label_row(row, good_thr=2.0, bad_thr=-2.0):
    """
    根据 action 和 future_return_pct 打标签。
    """
    action = str(row.get("action", "")).upper()
    ret = row.get("future_return_pct", None)
    if ret is None or pd.isna(ret):
        return "unknown"

    if action in ("BUY", "ADD"):
        if ret >= good_thr:
            return "good"
        if ret <= bad_thr:
            return "bad"
        return "neutral"
    if action in ("SELL", "REDUCE"):
        if ret <= bad_thr:
            return "good"
        if ret >= good_thr:
            return "bad"
        return "neutral"
    return "unknown"


def main():
    print("\n为实时交易决策打事后收益标签  开始时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    csv_path = os.path.join(DATA_DIR, "realtime_trading_decisions_data.csv")
    df = load_csv_safely(csv_path)
    if df.empty:
        print("  [信息] realtime_trading_decisions_data.csv 为空或不存在，暂无法标注。")
        return

    # 确保 required 列存在
    for col in ["symbol", "date", "current_price", "action"]:
        if col not in df.columns:
            print(f"  [WARN] 缺少列 {col}，无法完整标注。")
            return

    # 只处理还没有 future_price / future_return_pct 的记录
    if "future_price" not in df.columns:
        df["future_price"] = pd.NA
    if "future_return_pct" not in df.columns:
        df["future_return_pct"] = pd.NA
    if "outcome_label" not in df.columns:
        df["outcome_label"] = pd.NA

    mask_unlabeled = df["future_price"].isna()
    target_df = df[mask_unlabeled].copy()
    if target_df.empty:
        print("  [信息] 所有记录都已经有 future_price，无需重复标注。")
        return

    print(f"  待标注记录数: {len(target_df)}")

    ds = get_stock_data_source()

    updated_rows = 0
    for idx, row in target_df.iterrows():
        symbol = str(row["symbol"]).zfill(6)
        decision_date = str(row["date"])
        current_price = row.get("current_price", None)
        if current_price is None or pd.isna(current_price):
            continue

        future_price = get_next_trading_close(ds, symbol, decision_date)
        if future_price is None:
            continue

        future_return_pct = (future_price - float(current_price)) / float(current_price) * 100.0

        df.loc[idx, "future_price"] = future_price
        df.loc[idx, "future_return_pct"] = future_return_pct
        df.loc[idx, "outcome_label"] = label_row(
            df.loc[idx], good_thr=2.0, bad_thr=-2.0
        )
        updated_rows += 1

    # 保存回 CSV
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  已成功为 {updated_rows} 条记录打上 future_price / future_return_pct / outcome_label。")
    print("完成时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()



