"""
信号质量评估脚本

用途：
 1. 对静态预测结果做简单回顾（按上涨概率分桶看命中率）
 2. 对实时交易决策数据做简单统计（各操作建议分布、不同模式的使用情况）

运行方式（在 smart_stock_advisor 目录下）：
  py -m analysis.review_signal_quality

注意：
 - 依赖已存在的 CSV：
   data/prediction_factors_data.csv
   stock_predictions.csv
   data/realtime_trading_decisions_data.csv   （实时决策由 RealtimeTradingAdvisor 写入）
"""

import os
from datetime import datetime

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


def analyze_static_prediction():
    """
    静态预测质量简单评估：
      - 按上涨概率分桶（例如 [0,0.5),[0.5,0.6)...）统计命中率
    """
    print("\n" + "=" * 80)
    print("一、静态预测信号质量（基于 stock_predictions.csv）")
    print("=" * 80)

    sp_path = os.path.join(PROJECT_ROOT, "stock_predictions.csv")
    df = load_csv_safely(sp_path)
    if df.empty:
        print("  [信息] stock_predictions.csv 为空或不存在，暂无法评估静态预测质量。")
        return

    # 只保留有实际结果的数据
    hit_df = df.copy()
    if "prediction_hit" not in hit_df.columns:
        print("  [信息] 没有 prediction_hit 字段，暂无法评估命中率。")
        return

    hit_df = hit_df[hit_df["prediction_hit"].isin(["命中", "未命中"])]
    if hit_df.empty:
        print("  [信息] 还没有足够的实际结果（命中/未命中），稍后再来看这部分。")
        return

    # 涨跌概率字段名兼容
    up_col = "up_probability"
    if up_col not in hit_df.columns:
        # 有的版本可能是大写/其它字段名，这里做一次兜底
        candidates = [c for c in hit_df.columns if "up" in c and "prob" in c]
        if candidates:
            up_col = candidates[0]
        else:
            print("  [信息] 找不到上涨概率列，暂无法按概率分桶评估。")
            return

    # 确保是数值型
    hit_df[up_col] = pd.to_numeric(hit_df[up_col], errors="coerce")
    hit_df = hit_df.dropna(subset=[up_col])

    # 把 [0,1] 的概率放大到百分比方便阅读
    hit_df["up_pct"] = hit_df[up_col] * 100.0

    # 定义分桶边界
    bins = [0, 50, 60, 70, 80, 90, 100]
    labels = ["0-50", "50-60", "60-70", "70-80", "80-90", "90-100"]
    hit_df["up_bucket"] = pd.cut(hit_df["up_pct"], bins=bins, labels=labels, right=True, include_lowest=True)

    # 统计每个分桶的样本数和命中率
    summary = (
        hit_df.groupby("up_bucket")["prediction_hit"]
        .value_counts()
        .unstack(fill_value=0)
        .rename(columns={"命中": "hit", "未命中": "miss"})
    )
    summary["total"] = summary["hit"] + summary["miss"]
    summary["hit_rate"] = summary["hit"] / summary["total"].where(summary["total"] > 0, 1)

    print("\n  按上涨概率分桶的命中情况：")
    print("  （up_probability 区间 -> 命中率 / 样本数）\n")
    for idx, row in summary.iterrows():
        bucket = str(idx)
        total = int(row["total"])
        if total == 0:
            continue
        hit_rate = row["hit_rate"] * 100
        print(f"    {bucket:>7}: 命中率 {hit_rate:5.1f}%  | 样本数 {total:4d}")


def analyze_realtime_decisions():
    """
    实时交易决策数据简单统计：
      - 各模式（single / realtime / monitor / scan）的记录数
      - 各操作建议（BUY/SELL/ADD/REDUCE/HOLD 等）的占比
    """
    print("\n" + "=" * 80)
    print("二、实时交易决策数据（基于 data/realtime_trading_decisions_data.csv）")
    print("=" * 80)

    rt_path = os.path.join(DATA_DIR, "realtime_trading_decisions_data.csv")
    df = load_csv_safely(rt_path)
    if df.empty:
        print("  [信息] realtime_trading_decisions_data.csv 为空或不存在，暂还没有实时决策被记录。")
        print("  提示：可以在交易时间运行例如：")
        print("    py main.py --realtime --symbol 600519")
        print("    py main.py --monitor --symbol 600519 --interval 30")
        print("  来产生实时决策并写入该文件。")
        return

    total = len(df)
    print(f"\n  当前共有 {total} 条实时决策快照。")

    # 各模式分布
    if "mode" in df.columns:
        print("\n  按模式统计（mode）：")
        mode_counts = df["mode"].value_counts()
        for mode, cnt in mode_counts.items():
            pct = cnt / total * 100
            print(f"    {mode:>8}: {cnt:5d} 条 ({pct:5.1f}%)")

    # 各操作建议分布
    if "action" in df.columns:
        print("\n  按操作建议统计（action）：")
        act_counts = df["action"].value_counts()
        for act, cnt in act_counts.items():
            pct = cnt / total * 100
            print(f"    {act:>8}: {cnt:5d} 条 ({pct:5.1f}%)")

    # 不同 session 下的 BUY/SELL 频率（只做一个简单视图）
    if {"action", "trading_session"}.issubset(df.columns):
        print("\n  不同交易时段下的关键操作（BUY / SELL / ADD / REDUCE）次数：")
        key_actions = df[df["action"].isin(["BUY", "SELL", "ADD", "REDUCE"])].copy()
        if key_actions.empty:
            print("    暂无 BUY/SELL/ADD/REDUCE 记录。")
        else:
            pivot = (
                key_actions.pivot_table(
                    index="trading_session",
                    columns="action",
                    values="timestamp",
                    aggfunc="count",
                    fill_value=0,
                )
            )
            for session, row in pivot.iterrows():
                print(f"    时段 {session}: ", end="")
                pieces = []
                for act in ["BUY", "ADD", "REDUCE", "SELL"]:
                    if act in row.index:
                        pieces.append(f"{act}={int(row[act])}")
                print(" | ".join(pieces))


def main():
    print("\n信号质量评估开始时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    analyze_static_prediction()
    analyze_realtime_decisions()
    print("\n评估完成。")


if __name__ == "__main__":
    main()



