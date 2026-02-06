#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
按指定时间段刷新技术指标字段脚本

用途：
    只更新 stock_history_data 表中【2016-01-12 ~ 2016-01-14】这三天的：
        - ma5, ma10, ma20, ma60
        - rsi
        - macd, macd_signal, macd_hist
        - x2

    不修改其他日期的数据。

计算方式：
    全部基于 stock_history_data 表中已经存在的价格字段：
        - close_price, high_price, low_price
    不依赖外部 API。
"""

import sys
import os
from datetime import datetime
from typing import List, Dict

import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


# 说明：
#   最初脚本是为 2016-01-12~14 准备的，
#   现在根据你的实际需求，改为 2026-01-12~14（最近三天）。
TARGET_DATES = ["2026-01-12", "2026-01-13", "2026-01-14"]
PERIOD_TYPE = "daily"


def _load_symbols_for_dates(dates: List[str]) -> List[str]:
    """获取在指定日期范围内有数据的股票代码列表"""
    sql = """
        SELECT DISTINCT symbol
        FROM stock_history_data
        WHERE trade_date BETWEEN %s AND %s
          AND period_type = %s
    """
    start_date = min(dates)
    end_date = max(dates)
    rows = DBConnection.execute_query(sql, (start_date, end_date, PERIOD_TYPE))
    symbols = [r["symbol"] for r in rows] if rows else []
    return symbols


def _load_history(symbol: str, end_date: str, lookback_days: int = 500) -> pd.DataFrame:
    """从 stock_history_data 表加载指定股票的一段历史数据"""
    # 从目标日期往前取足够多的数据（至少 200 天，确保能计算 MA60 等指标）
    # 先取最后 lookback_days 条记录，然后按日期正序排列
    sql = """
        SELECT trade_date, close_price, high_price, low_price
        FROM (
            SELECT trade_date, close_price, high_price, low_price
            FROM stock_history_data
            WHERE symbol = %s
              AND period_type = %s
              AND trade_date <= %s
            ORDER BY trade_date DESC
            LIMIT %s
        ) AS sub
        ORDER BY trade_date ASC
    """
    # 从后往前取 lookback_days 条记录（足够覆盖 60 日指标计算）
    rows = DBConnection.execute_query(sql, (symbol, PERIOD_TYPE, end_date, lookback_days))
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df.set_index("trade_date", inplace=True)
    # 确保按照日期排序
    df.sort_index(inplace=True)
    return df


def _compute_indicators_for_date(df: pd.DataFrame, trade_date: str) -> Dict[str, float]:
    """
    基于一段历史数据，计算某一天的技术指标。

    df:  按日期索引的 DataFrame，包含 close_price, high_price, low_price
    trade_date:  目标日期（字符串）
    """
    if df.empty:
        return {}

    date_idx = pd.to_datetime(trade_date)
    if date_idx not in df.index:
        # 该天没有记录，跳过
        return {}

    # 只使用 date_idx 之前（含当日）的数据
    df_hist = df.loc[:date_idx].copy()
    closes = df_hist["close_price"]
    highs = df_hist["high_price"]
    lows = df_hist["low_price"]

    result: Dict[str, float] = {}

    # ===== 均线 =====
    def _ma(window: int):
        return float(closes.tail(window).mean()) if len(closes) >= window else None

    result["ma5"] = _ma(5)
    result["ma10"] = _ma(10)
    result["ma20"] = _ma(20)
    result["ma60"] = _ma(60)

    # ===== RSI（14日） =====
    if len(closes) >= 14:
        delta = closes.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]
        result["rsi"] = float(rsi_val) if pd.notna(rsi_val) else None
    else:
        result["rsi"] = None

    # ===== MACD =====
    if len(closes) >= 26:
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal

        result["macd"] = float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None
        result["macd_signal"] = float(signal.iloc[-1]) if pd.notna(signal.iloc[-1]) else None
        result["macd_hist"] = float(hist.iloc[-1]) if pd.notna(hist.iloc[-1]) else None
    else:
        result["macd"] = None
        result["macd_signal"] = None
        result["macd_hist"] = None

    # ===== X2（20日区间位置） =====
    if len(df_hist) >= 20:
        window_highs = highs.tail(20)
        window_lows = lows.tail(20)
        llv_low = window_lows.min()
        hhv_high = window_highs.max()
        current_close = closes.iloc[-1]
        if pd.notna(current_close) and pd.notna(llv_low) and pd.notna(hhv_high):
            range_width = hhv_high - llv_low
            if range_width > 0:
                x2_val = (current_close - llv_low) / range_width * 100
                result["x2"] = float(round(x2_val, 4))
            else:
                # 区间无波动，给中间值
                result["x2"] = 50.0
        else:
            result["x2"] = None
    else:
        result["x2"] = None

    return result


def refresh_indicators_for_dates(dates: List[str]) -> None:
    """刷新指定日期列表的技术指标字段"""
    # 确保日期按从小到大顺序处理：先 12 号，再 13 号，再 14 号
    dates = sorted(set(dates))
    logger.info("=" * 60)
    logger.info("开始刷新指定日期的技术指标字段")
    logger.info(f"目标日期: {', '.join(dates)}")
    logger.info("=" * 60)

    symbols = _load_symbols_for_dates(dates)
    if not symbols:
        logger.warning("在指定日期范围内未找到任何股票记录，任务结束。")
        return

    logger.info(f"在指定日期范围内找到 {len(symbols)} 只股票，将逐一更新。")

    total_updates = 0

    for idx, symbol in enumerate(symbols, 1):
        try:
            logger.info(f"\n[{idx}/{len(symbols)}] 处理股票: {symbol}")
            # 加载到最大日期的历史，用于所有目标日的指标计算
            history_df = _load_history(symbol, max(dates))
            if history_df.empty:
                logger.warning(f"  无历史数据，跳过。")
                continue

            for d in dates:
                if pd.to_datetime(d) not in history_df.index:
                    logger.info(f"  {d} 无记录，跳过。")
                    continue

                indicators = _compute_indicators_for_date(history_df, d)
                if not indicators:
                    logger.info(f"  {d} 指标计算失败或无有效数据，跳过。")
                    continue

                sql = """
                    UPDATE stock_history_data
                    SET ma5 = %s,
                        ma10 = %s,
                        ma20 = %s,
                        ma60 = %s,
                        rsi = %s,
                        macd = %s,
                        macd_signal = %s,
                        macd_hist = %s,
                        x2 = %s
                    WHERE symbol = %s
                      AND trade_date = %s
                      AND period_type = %s
                """
                params = (
                    indicators.get("ma5"),
                    indicators.get("ma10"),
                    indicators.get("ma20"),
                    indicators.get("ma60"),
                    indicators.get("rsi"),
                    indicators.get("macd"),
                    indicators.get("macd_signal"),
                    indicators.get("macd_hist"),
                    indicators.get("x2"),
                    symbol,
                    d,
                    PERIOD_TYPE,
                )

                affected = DBConnection.execute_update(sql, params)
                if affected > 0:
                    logger.info(
                        f"  更新 {symbol} {d} 成功："
                        f"ma5={indicators.get('ma5')}, "
                        f"ma10={indicators.get('ma10')}, "
                        f"ma20={indicators.get('ma20')}, "
                        f"ma60={indicators.get('ma60')}, "
                        f"rsi={indicators.get('rsi')}, "
                        f"macd={indicators.get('macd')}, "
                        f"x2={indicators.get('x2')}"
                    )
                    total_updates += affected
                else:
                    logger.warning(f"  更新 {symbol} {d} 失败或无匹配行。")

        except Exception as e:
            logger.error(f"处理股票 {symbol} 时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    logger.info("\n" + "=" * 60)
    logger.info(f"任务完成，共更新 {total_updates} 行记录。")
    logger.info("=" * 60)


if __name__ == "__main__":
    refresh_indicators_for_dates(TARGET_DATES)

