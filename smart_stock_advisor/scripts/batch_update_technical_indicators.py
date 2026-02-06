#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量更新数据库中的技术指标字段
重新计算ma5、ma10、ma20、ma60、rsi、macd、macd_signal、macd_hist、x2
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from tqdm import tqdm

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from data_source.stock_data_source import StockDataSource
from utils.logger import get_logger

logger = get_logger(__name__)

def calculate_indicators_with_talib(closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> Dict:
    """使用talib计算技术指标"""
    try:
        import talib
        TALIB_AVAILABLE = True
    except ImportError:
        TALIB_AVAILABLE = False
    
    results = {}
    
    if TALIB_AVAILABLE:
        # 使用talib计算（与证券公司算法一致）
        # MA
        if len(closes) >= 5:
            ma5_values = talib.MA(closes, timeperiod=5)
            results['ma5'] = float(ma5_values[-1]) if pd.notna(ma5_values[-1]) else None
        else:
            results['ma5'] = None
        
        if len(closes) >= 10:
            ma10_values = talib.MA(closes, timeperiod=10)
            results['ma10'] = float(ma10_values[-1]) if pd.notna(ma10_values[-1]) else None
        else:
            results['ma10'] = None
        
        if len(closes) >= 20:
            ma20_values = talib.MA(closes, timeperiod=20)
            results['ma20'] = float(ma20_values[-1]) if pd.notna(ma20_values[-1]) else None
        else:
            results['ma20'] = None
        
        if len(closes) >= 60:
            ma60_values = talib.MA(closes, timeperiod=60)
            results['ma60'] = float(ma60_values[-1]) if pd.notna(ma60_values[-1]) else None
        else:
            results['ma60'] = None
        
        # RSI（使用Wilder平滑，与证券公司一致）
        if len(closes) >= 14:
            rsi_values = talib.RSI(closes, timeperiod=14)
            results['rsi'] = float(rsi_values[-1]) if pd.notna(rsi_values[-1]) else None
        else:
            results['rsi'] = None
        
        # MACD
        if len(closes) >= 26:
            macd_values, macd_signal_values, macd_hist_values = talib.MACD(
                closes, 
                fastperiod=12, 
                slowperiod=26, 
                signalperiod=9
            )
            results['macd'] = float(macd_values[-1]) if pd.notna(macd_values[-1]) else None
            results['macd_signal'] = float(macd_signal_values[-1]) if pd.notna(macd_signal_values[-1]) else None
            results['macd_hist'] = float(macd_hist_values[-1]) if pd.notna(macd_hist_values[-1]) else None
        else:
            results['macd'] = None
            results['macd_signal'] = None
            results['macd_hist'] = None
        
        # X2（自定义指标，talib没有，使用pandas计算）
        if len(closes) >= 20:
            current_close = closes[-1]
            llv_low = lows[-20:].min()
            hhv_high = highs[-20:].max()
            range_width = hhv_high - llv_low
            if range_width > 0:
                x2_value = (current_close - llv_low) / range_width * 100
                results['x2'] = float(round(x2_value, 4))
            else:
                results['x2'] = 50.0
        else:
            results['x2'] = None
    else:
        # 使用pandas计算（可能与证券公司值不一致）
        closes_series = pd.Series(closes)
        
        # MA
        results['ma5'] = float(closes_series.tail(5).mean()) if len(closes_series) >= 5 else None
        results['ma10'] = float(closes_series.tail(10).mean()) if len(closes_series) >= 10 else None
        results['ma20'] = float(closes_series.tail(20).mean()) if len(closes_series) >= 20 else None
        results['ma60'] = float(closes_series.tail(60).mean()) if len(closes_series) >= 60 else None
        
        # RSI
        if len(closes_series) >= 14:
            delta = closes_series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            results['rsi'] = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
        else:
            results['rsi'] = None
        
        # MACD
        if len(closes_series) >= 26:
            ema12 = closes_series.ewm(span=12, adjust=False).mean()
            ema26 = closes_series.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            results['macd'] = float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None
            results['macd_signal'] = float(signal.iloc[-1]) if pd.notna(signal.iloc[-1]) else None
            results['macd_hist'] = float(histogram.iloc[-1]) if pd.notna(histogram.iloc[-1]) else None
        else:
            results['macd'] = None
            results['macd_signal'] = None
            results['macd_hist'] = None
        
        # X2
        if len(closes) >= 20:
            highs_series = pd.Series(highs)
            lows_series = pd.Series(lows)
            current_close = closes_series.iloc[-1]
            llv_low = lows_series.tail(20).min()
            hhv_high = highs_series.tail(20).max()
            range_width = hhv_high - llv_low
            if range_width > 0:
                x2_value = (current_close - llv_low) / range_width * 100
                results['x2'] = float(round(x2_value, 4))
            else:
                results['x2'] = 50.0
        else:
            results['x2'] = None
    
    return results

def batch_update_indicators(symbol: str = None, start_date: str = None, end_date: str = None, 
                           batch_size: int = 500, use_talib: bool = True):
    """
    批量更新技术指标
    
    Args:
        symbol: 股票代码（如果为None，则更新所有股票）
        start_date: 开始日期（YYYY-MM-DD），如果为None，则从最早的数据开始
        end_date: 结束日期（YYYY-MM-DD），如果为None，则到最新的数据
        batch_size: 批量更新大小
        use_talib: 是否使用talib库（如果可用）
    """
    db = DatabaseConnection()
    data_source = StockDataSource()
    
    # 检查talib是否可用
    try:
        import talib
        TALIB_AVAILABLE = True
        if use_talib:
            logger.info("使用talib库计算技术指标（与证券公司算法一致）")
        else:
            logger.info("使用pandas计算技术指标（可能与证券公司值不一致）")
    except ImportError:
        TALIB_AVAILABLE = False
        logger.warning("talib库未安装，将使用pandas计算（可能与证券公司值不一致）")
        logger.warning("建议安装talib: pip install TA-Lib")
    
    # 1. 查询需要更新的记录
    print("\n" + "=" * 80)
    print("查询需要更新的记录...")
    print("=" * 80)
    
    sql_conditions = ["period_type = 'daily'"]
    params = []
    
    if symbol:
        sql_conditions.append("symbol = %s")
        params.append(str(symbol).zfill(6))
    
    if start_date:
        sql_conditions.append("trade_date >= %s")
        params.append(start_date)
    
    if end_date:
        sql_conditions.append("trade_date <= %s")
        params.append(end_date)
    
    sql = f"""
        SELECT DISTINCT symbol, trade_date
        FROM stock_history_data
        WHERE {' AND '.join(sql_conditions)}
        ORDER BY symbol, trade_date
    """
    
    records = db.execute_query(sql, tuple(params))
    
    if not records:
        print("\n[错误] 没有找到需要更新的记录")
        return
    
    print(f"\n找到 {len(records)} 条记录需要更新")
    
    # 2. 按股票分组处理
    print("\n" + "=" * 80)
    print("开始批量更新技术指标...")
    print("=" * 80)
    
    # 按股票分组
    symbol_groups = {}
    for record in records:
        sym = record['symbol']
        if sym not in symbol_groups:
            symbol_groups[sym] = []
        symbol_groups[sym].append(record['trade_date'])
    
    print(f"\n共 {len(symbol_groups)} 只股票需要更新")
    
    # 3. 批量更新
    update_batch = []
    total_updated = 0
    total_failed = 0
    
    # 准备更新SQL
    update_sql = """
        UPDATE stock_history_data
        SET ma5 = %s, ma10 = %s, ma20 = %s, ma60 = %s,
            rsi = %s, macd = %s, macd_signal = %s, macd_hist = %s, x2 = %s
        WHERE symbol = %s AND trade_date = %s AND period_type = 'daily'
    """
    
    # 为每只股票获取历史数据并计算指标
    for symbol, dates in tqdm(symbol_groups.items(), desc="处理股票"):
        try:
            # 获取该股票的所有历史数据（至少需要90天，确保有足够数据计算MA60）
            # 获取日期范围
            dates_sorted = sorted(dates)
            # 处理日期类型（可能是字符串或date对象）
            first_date_str = dates_sorted[0]
            last_date_str = dates_sorted[-1]
            if isinstance(first_date_str, str):
                first_date = datetime.strptime(first_date_str, '%Y-%m-%d')
            else:
                first_date = datetime.combine(first_date_str, datetime.min.time())
            if isinstance(last_date_str, str):
                last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
            else:
                last_date = datetime.combine(last_date_str, datetime.min.time())
            
            # 获取更早的数据用于计算（需要至少90天）
            data_start_date = (first_date - timedelta(days=90)).strftime('%Y-%m-%d')
            data_end_date = last_date.strftime('%Y-%m-%d')
            
            # 从数据库获取历史数据
            sql_history = """
                SELECT trade_date, close_price, high_price, low_price
                FROM stock_history_data
                WHERE symbol = %s 
                  AND trade_date <= %s 
                  AND period_type = 'daily'
                ORDER BY trade_date ASC
            """
            history_records = db.execute_query(sql_history, (symbol, data_end_date))
            
            if not history_records or len(history_records) < 5:
                logger.warning(f"{symbol} 历史数据不足，跳过")
                total_failed += len(dates)
                continue
            
            # 转换为DataFrame
            history_list = []
            for r in history_records:
                history_list.append({
                    'date': pd.to_datetime(r['trade_date']),
                    'close': float(r['close_price']) if r['close_price'] else None,
                    'high': float(r['high_price']) if r['high_price'] else None,
                    'low': float(r['low_price']) if r['low_price'] else None,
                })
            
            df_history = pd.DataFrame(history_list)
            df_history.set_index('date', inplace=True)
            df_history = df_history.sort_index()
            
            # 为每个日期计算指标
            for date_obj in dates:
                try:
                    # 处理日期类型（可能是字符串或date对象）
                    if isinstance(date_obj, str):
                        date_str = date_obj
                        target_date = pd.to_datetime(date_str)
                    else:
                        date_str = date_obj.strftime('%Y-%m-%d')
                        target_date = pd.to_datetime(date_str)
                    
                    # 只使用目标日期及之前的数据
                    df_filtered = df_history.loc[df_history.index <= target_date].copy()
                    
                    if len(df_filtered) < 5:
                        # 数据不足，设置为None
                        update_batch.append((
                            None, None, None, None, None, None, None, None, None,
                            symbol, date_str
                        ))
                        continue
                    
                    # 准备数据
                    closes = df_filtered['close'].values
                    highs = df_filtered['high'].values
                    lows = df_filtered['low'].values
                    
                    # 计算指标
                    indicators = calculate_indicators_with_talib(closes, highs, lows)
                    
                    # 添加到批量更新列表
                    update_batch.append((
                        indicators.get('ma5'),
                        indicators.get('ma10'),
                        indicators.get('ma20'),
                        indicators.get('ma60'),
                        indicators.get('rsi'),
                        indicators.get('macd'),
                        indicators.get('macd_signal'),
                        indicators.get('macd_hist'),
                        indicators.get('x2'),
                        symbol,
                        date_str
                    ))
                    
                    # 批量更新
                    if len(update_batch) >= batch_size:
                        try:
                            db.execute_many(update_sql, update_batch)
                            total_updated += len(update_batch)
                            update_batch = []
                        except Exception as e:
                            logger.error(f"批量更新失败: {str(e)}")
                            total_failed += len(update_batch)
                            update_batch = []
                            
                except Exception as e:
                    logger.error(f"计算 {symbol} {date_str} 指标失败: {str(e)}")
                    total_failed += 1
                    continue
                    
        except Exception as e:
            logger.error(f"处理股票 {symbol} 失败: {str(e)}")
            total_failed += len(dates)
            continue
    
    # 更新剩余的记录
    if update_batch:
        try:
            db.execute_many(update_sql, update_batch)
            total_updated += len(update_batch)
        except Exception as e:
            logger.error(f"批量更新失败: {str(e)}")
            total_failed += len(update_batch)
    
    # 4. 显示结果
    print("\n" + "=" * 80)
    print("更新完成！")
    print("=" * 80)
    print(f"\n成功更新: {total_updated} 条记录")
    print(f"失败: {total_failed} 条记录")
    print(f"总计: {total_updated + total_failed} 条记录")
    
    if TALIB_AVAILABLE and use_talib:
        print("\n[OK] 使用talib库计算（与证券公司算法一致）")
    else:
        print("\n[WARN] 使用pandas计算（可能与证券公司值不一致，建议安装talib）")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='批量更新数据库中的技术指标字段')
    parser.add_argument('--symbol', '-s', type=str, default=None, help='股票代码（如果为None，则更新所有股票）')
    parser.add_argument('--start-date', type=str, default=None, help='开始日期（YYYY-MM-DD）')
    parser.add_argument('--end-date', type=str, default=None, help='结束日期（YYYY-MM-DD）')
    parser.add_argument('--batch-size', type=int, default=500, help='批量更新大小（默认500）')
    parser.add_argument('--no-talib', action='store_true', help='不使用talib库（即使已安装）')
    
    args = parser.parse_args()
    
    batch_update_indicators(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        batch_size=args.batch_size,
        use_talib=not args.no_talib
    )
