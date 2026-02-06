"""
修复16号及之后MACD值异常问题

问题原因：
- get_historical_data_for_indicators() 使用 trade_date <= %s，会包含当前日期
- calculate_technical_indicators() 又添加了一次 current_close
- 导致当前收盘价被重复添加，MACD计算错误

修复方案：
- 重新计算16号及之后所有日期的MACD值
- 使用修复后的逻辑（trade_date < %s）
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from utils.stock_history_storage import StockHistoryStorage

logger = get_logger(__name__)


class MACDFixer:
    """MACD值修复器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.storage = StockHistoryStorage()
        self.logger = logger
    
    def get_historical_data_for_indicators(self, symbol: str, trade_date: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取历史数据用于计算技术指标（修复版本：使用 trade_date < %s）
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期
            days: 需要的历史天数
        
        Returns:
            DataFrame（包含close, volume等字段）或None
        """
        try:
            # 修复：使用 trade_date < %s 而不是 trade_date <= %s
            # 原因：避免历史数据包含当前日期，导致在calculate_technical_indicators中重复添加current_close
            sql = """
                SELECT trade_date, close_price, volume
                FROM stock_history_data
                WHERE symbol = %s AND trade_date < %s
                ORDER BY trade_date DESC
                LIMIT %s
            """
            results = self.db.execute_query(sql, (symbol, trade_date, days))
            
            if not results:
                return None
            
            # 转换为DataFrame
            data = []
            for row in results:
                data.append({
                    'trade_date': str(row['trade_date']),
                    'close': float(row['close_price']) if row.get('close_price') else None,
                    'volume': int(row['volume']) if row.get('volume') else None
                })
            
            df = pd.DataFrame(data)
            if df.empty:
                return None
            
            # 按日期排序（从旧到新）
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            df = df.set_index('trade_date')
            
            return df
        except Exception as e:
            self.logger.debug(f"获取历史数据失败 {symbol} {trade_date}: {str(e)}")
            return None
    
    def calculate_technical_indicators(self, history_df: pd.DataFrame, current_close: float) -> Dict:
        """
        计算技术指标（修复版本）
        
        Args:
            history_df: 历史数据DataFrame（包含close和volume列）
            current_close: 当前收盘价
        
        Returns:
            包含技术指标的字典
        """
        indicators = {
            'ma5': None,
            'ma10': None,
            'ma20': None,
            'ma60': None,
            'rsi': None,
            'macd': None,
            'macd_signal': None,
            'macd_hist': None,
            'x2': None
        }
        
        if history_df is None or history_df.empty or 'close' not in history_df.columns:
            return indicators
        
        try:
            closes = history_df['close'].dropna()
            if len(closes) == 0:
                return indicators
            
            # 添加当前收盘价（历史数据已经排除了当前日期，所以可以安全添加）
            closes = pd.concat([closes, pd.Series([current_close])])
            
            # 计算移动平均线
            if len(closes) >= 5:
                indicators['ma5'] = float(closes.tail(5).mean())
            if len(closes) >= 10:
                indicators['ma10'] = float(closes.tail(10).mean())
            if len(closes) >= 20:
                indicators['ma20'] = float(closes.tail(20).mean())
            if len(closes) >= 60:
                indicators['ma60'] = float(closes.tail(60).mean())
            
            # 计算RSI（14周期）
            if len(closes) >= 14:
                delta = closes.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                indicators['rsi'] = float(rsi.iloc[-1]) if not rsi.empty else None
            
            # 计算MACD
            if len(closes) >= 26:
                ema12 = closes.ewm(span=12, adjust=False).mean()
                ema26 = closes.ewm(span=26, adjust=False).mean()
                macd = ema12 - ema26
                macd_signal = macd.ewm(span=9, adjust=False).mean()
                macd_hist = macd - macd_signal
                indicators['macd'] = float(macd.iloc[-1]) if not macd.empty else None
                indicators['macd_signal'] = float(macd_signal.iloc[-1]) if not macd_signal.empty else None
                indicators['macd_hist'] = float(macd_hist.iloc[-1]) if not macd_hist.empty else None
            
            # 计算X2指标（收盘价在20日价格区间中的相对位置，0-100）
            if len(closes) >= 20:
                recent_20 = closes.tail(20)
                high_20 = recent_20.max()
                low_20 = recent_20.min()
                if high_20 > low_20:
                    x2 = ((current_close - low_20) / (high_20 - low_20)) * 100
                    indicators['x2'] = float(x2)
        except Exception as e:
            self.logger.debug(f"计算技术指标失败: {str(e)}")
        
        return indicators
    
    def fix_single_stock_date(self, symbol: str, trade_date: str) -> bool:
        """
        修复单只股票在指定日期的MACD值
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期
        
        Returns:
            是否成功
        """
        try:
            # 获取当前收盘价
            sql = """
                SELECT close_price
                FROM stock_history_data
                WHERE symbol = %s AND trade_date = %s
            """
            result = self.db.execute_query(sql, (symbol, trade_date))
            
            if not result or not result[0].get('close_price'):
                self.logger.debug(f"{symbol} {trade_date}: 未找到收盘价，跳过")
                return False
            
            current_close = float(result[0]['close_price'])
            
            # 获取历史数据（使用修复后的逻辑）
            history_df = self.get_historical_data_for_indicators(symbol, trade_date, days=60)
            
            if history_df is None or history_df.empty:
                self.logger.debug(f"{symbol} {trade_date}: 历史数据不足，跳过")
                return False
            
            # 计算技术指标
            indicators = self.calculate_technical_indicators(history_df, current_close)
            
            # 更新数据库
            update_data = {
                'macd': indicators.get('macd'),
                'macd_signal': indicators.get('macd_signal'),
                'macd_hist': indicators.get('macd_hist'),
                'ma5': indicators.get('ma5'),
                'ma10': indicators.get('ma10'),
                'ma20': indicators.get('ma20'),
                'ma60': indicators.get('ma60'),
                'rsi': indicators.get('rsi'),
                'x2': indicators.get('x2')
            }
            
            success = self.storage.update_stock_daily_data(symbol, trade_date, update_data)
            
            if success:
                self.logger.debug(f"{symbol} {trade_date}: MACD修复成功 (macd={indicators.get('macd'):.4f})")
            else:
                self.logger.warning(f"{symbol} {trade_date}: MACD修复失败（更新数据库失败）")
            
            return success
            
        except Exception as e:
            self.logger.error(f"{symbol} {trade_date}: MACD修复异常: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def fix_all_after_date(self, start_date: str = '2026-01-16', max_workers: int = 10) -> Dict:
        """
        修复指定日期之后所有股票的MACD值
        
        Args:
            start_date: 开始日期（格式：YYYY-MM-DD）
            max_workers: 最大线程数
        
        Returns:
            修复结果统计
        """
        self.logger.info(f"开始修复 {start_date} 及之后所有股票的MACD值...")
        
        # 查询需要修复的数据
        sql = """
            SELECT DISTINCT symbol, trade_date
            FROM stock_history_data
            WHERE trade_date >= %s
            AND close_price IS NOT NULL
            ORDER BY symbol, trade_date
        """
        
        results = self.db.execute_query(sql, (start_date,))
        
        if not results:
            self.logger.warning(f"未找到需要修复的数据")
            return {
                'total': 0,
                'success': 0,
                'failed': 0
            }
        
        total = len(results)
        self.logger.info(f"找到 {total} 条需要修复的数据")
        
        success_count = 0
        failed_count = 0
        
        # 多线程处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for row in results:
                symbol = row['symbol']
                trade_date = str(row['trade_date'])
                future = executor.submit(self.fix_single_stock_date, symbol, trade_date)
                futures.append(future)
            
            # 等待完成并统计
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    if future.result():
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"处理失败: {str(e)}")
                
                if i % 100 == 0:
                    self.logger.info(f"进度: {i}/{total} (成功: {success_count}, 失败: {failed_count})")
        
        result = {
            'total': total,
            'success': success_count,
            'failed': failed_count
        }
        
        self.logger.info(f"修复完成: 总计 {total}, 成功 {success_count}, 失败 {failed_count}")
        
        return result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='修复16号及之后MACD值异常问题')
    parser.add_argument('--start-date', type=str, default='2026-01-16',
                       help='开始日期（格式：YYYY-MM-DD），默认：2026-01-16')
    parser.add_argument('--symbol', type=str, default=None,
                       help='只修复指定股票（可选）')
    parser.add_argument('--date', type=str, default=None,
                       help='只修复指定日期（可选，需要配合--symbol使用）')
    parser.add_argument('--threads', type=int, default=10,
                       help='最大线程数，默认：10')
    
    args = parser.parse_args()
    
    fixer = MACDFixer()
    
    if args.symbol and args.date:
        # 修复单只股票的单日数据
        print(f"修复 {args.symbol} {args.date} 的MACD值...")
        success = fixer.fix_single_stock_date(args.symbol, args.date)
        if success:
            print("修复成功")
        else:
            print("修复失败")
    elif args.symbol:
        # 修复单只股票的所有数据
        print(f"修复 {args.symbol} 从 {args.start_date} 开始的所有MACD值...")
        sql = """
            SELECT DISTINCT trade_date
            FROM stock_history_data
            WHERE symbol = %s AND trade_date >= %s
            ORDER BY trade_date
        """
        results = fixer.db.execute_query(sql, (args.symbol, args.start_date))
        dates = [str(row['trade_date']) for row in results]
        
        success_count = 0
        for date in dates:
            if fixer.fix_single_stock_date(args.symbol, date):
                success_count += 1
        
        print(f"修复完成: {success_count}/{len(dates)}")
    else:
        # 修复所有数据
        print(f"修复从 {args.start_date} 开始的所有MACD值...")
        result = fixer.fix_all_after_date(args.start_date, max_workers=args.threads)
        print(f"\n修复结果:")
        print(f"  总计: {result['total']}")
        print(f"  成功: {result['success']}")
        print(f"  失败: {result['failed']}")


if __name__ == '__main__':
    main()
