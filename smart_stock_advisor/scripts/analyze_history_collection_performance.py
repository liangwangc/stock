"""
分析历史股票数据获取的完整流程性能
找出API返回50秒但存入数据库需要几分钟的原因
"""
import os
import sys
import time
from datetime import datetime, timedelta

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage
from data_source.stock_data_source import StockDataSource

logger = get_logger(__name__)


def analyze_collection_performance(symbol: str = '000001', years: int = 10):
    """分析单只股票的历史数据收集性能"""
    print("=" * 80)
    print(f"分析 {symbol} 历史数据收集性能（{years}年）")
    print("=" * 80)
    
    collector = StockHistoryCollector()
    storage = StockHistoryStorage()
    data_source = StockDataSource()
    
    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    print(f"\n日期范围: {start_date_str} 至 {end_date_str}")
    
    # 步骤1: 扫描缺失日期
    print("\n步骤1: 扫描缺失日期...")
    start_time = time.time()
    missing_dates = storage.get_missing_dates(symbol, start_date_str, end_date_str)
    step1_time = time.time() - start_time
    print(f"  缺失日期数量: {len(missing_dates)}")
    print(f"  耗时: {step1_time:.2f}秒")
    
    if not missing_dates:
        print("  没有缺失数据，退出")
        return
    
    # 步骤2: 批量获取K线数据
    print("\n步骤2: 批量获取K线数据...")
    start_time = time.time()
    min_date = min(missing_dates)
    max_date = max(missing_dates)
    min_date_obj = datetime.strptime(min_date, '%Y-%m-%d') - timedelta(days=5)
    max_date_obj = datetime.strptime(max_date, '%Y-%m-%d') + timedelta(days=5)
    extended_start = min_date_obj.strftime('%Y-%m-%d')
    extended_end = max_date_obj.strftime('%Y-%m-%d')
    
    kline_data = data_source.get_stock_data(
        symbol=symbol,
        start_date=extended_start,
        end_date=extended_end
    )
    step2_time = time.time() - start_time
    print(f"  获取数据条数: {len(kline_data)}")
    print(f"  耗时: {step2_time:.2f}秒")
    print(f"  [注意] 这是API调用时间，用户反映约50秒")
    
    if kline_data.empty:
        print("  [错误] 获取K线数据失败")
        return
    
    # 步骤3: 获取股票基本信息
    print("\n步骤3: 获取股票基本信息...")
    start_time = time.time()
    # 优化：历史数据收集时跳过PE/PB获取，提升性能
    stock_info = data_source.get_stock_info(symbol, skip_pe_pb=True)
    step3_time = time.time() - start_time
    print(f"  耗时: {step3_time:.2f}秒")
    if step3_time > 1:
        print(f"  [警告] 耗时较长，可能是ak.stock_zh_a_spot_em()调用导致的")
    
    # 步骤4: 获取股票名称（如果需要）
    print("\n步骤4: 获取股票名称...")
    start_time = time.time()
    stock_name = ''
    if stock_info:
        stock_name = stock_info.get('name', '') or stock_info.get('股票简称', '') or stock_info.get('股票名称', '')
    
    if not stock_name or stock_name == '':
        stock_list = data_source.get_all_stock_list(limit=None, sort_by_turnover=False, use_cache=True)
        stock_dict = {str(stock.get('symbol', '')).strip(): stock.get('name', '') for stock in stock_list}
        stock_name = stock_dict.get(str(symbol).strip(), '')
    
    step4_time = time.time() - start_time
    print(f"  股票名称: {stock_name}")
    print(f"  耗时: {step4_time:.2f}秒")
    
    # 步骤5: 预计算技术指标
    print("\n步骤5: 预计算技术指标...")
    start_time = time.time()
    import pandas as pd
    import numpy as np
    
    technical_indicators = {}
    closes = kline_data['close'] if 'close' in kline_data.columns and len(kline_data) > 0 else pd.Series(dtype=float)
    
    if len(kline_data) >= 60:
        highs = kline_data['high']
        lows = kline_data['low']
        volumes = kline_data['volume'] if 'volume' in kline_data.columns else None
        
        # 计算移动平均线
        ma5_series = closes.rolling(window=5, min_periods=1).mean()
        ma10_series = closes.rolling(window=10, min_periods=1).mean()
        ma20_series = closes.rolling(window=20, min_periods=1).mean()
        ma60_series = closes.rolling(window=60, min_periods=1).mean()
        
        # 计算RSI
        rsi_series = None
        if len(closes) >= 14:
            delta = closes.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
        
        # 计算MACD
        macd_series = None
        macd_signal_series = None
        macd_hist_series = None
        if len(closes) >= 26:
            ema12 = closes.ewm(span=12, adjust=False).mean()
            ema26 = closes.ewm(span=26, adjust=False).mean()
            macd_series = ema12 - ema26
            macd_signal_series = macd_series.ewm(span=9, adjust=False).mean()
            macd_hist_series = macd_series - macd_signal_series
        
        # 计算X2指标
        x2_series = None
        if len(kline_data) >= 20:
            llv_low = lows.rolling(window=20, min_periods=1).min()
            hhv_high = highs.rolling(window=20, min_periods=1).max()
            range_width = hhv_high - llv_low
            x2_series = pd.Series(
                np.where(range_width > 0,
                        (closes - llv_low) / range_width * 100,
                        50.0),
                index=kline_data.index
            )
        
        # 计算量比
        volume_ratio_series = None
        if volumes is not None and len(volumes) >= 5:
            avg_volume = volumes.rolling(window=5, min_periods=1).mean()
            volume_ratio_series = volumes / avg_volume
        
        # 提取技术指标
        missing_dates_objs = [pd.to_datetime(d) for d in missing_dates]
        missing_dates_in_kline = [d for d in missing_dates_objs if d in kline_data.index]
        
        if missing_dates_in_kline:
            indicators_df = pd.DataFrame(index=missing_dates_in_kline)
            
            if len(ma5_series) > 0:
                indicators_df['ma5'] = ma5_series.reindex(missing_dates_in_kline)
                indicators_df['ma10'] = ma10_series.reindex(missing_dates_in_kline)
                indicators_df['ma20'] = ma20_series.reindex(missing_dates_in_kline)
                indicators_df['ma60'] = ma60_series.reindex(missing_dates_in_kline)
            
            if rsi_series is not None and len(rsi_series) > 0:
                indicators_df['rsi'] = rsi_series.reindex(missing_dates_in_kline)
            
            if macd_series is not None and len(macd_series) > 0:
                indicators_df['macd'] = macd_series.reindex(missing_dates_in_kline)
                indicators_df['macd_signal'] = macd_signal_series.reindex(missing_dates_in_kline)
                indicators_df['macd_hist'] = macd_hist_series.reindex(missing_dates_in_kline)
            
            if x2_series is not None and len(x2_series) > 0:
                indicators_df['x2'] = x2_series.reindex(missing_dates_in_kline)
            
            if volume_ratio_series is not None and len(volume_ratio_series) > 0:
                indicators_df['volume_ratio'] = volume_ratio_series.reindex(missing_dates_in_kline)
            
            # 转换为字典格式
            for date_obj in missing_dates_in_kline:
                date_str = date_obj.strftime('%Y-%m-%d')
                indicators = {}
                
                row = indicators_df.loc[date_obj]
                if pd.notna(row.get('ma5')):
                    indicators['ma5'] = float(row['ma5'])
                if pd.notna(row.get('ma10')):
                    indicators['ma10'] = float(row['ma10'])
                if pd.notna(row.get('ma20')):
                    indicators['ma20'] = float(row['ma20'])
                if pd.notna(row.get('ma60')):
                    indicators['ma60'] = float(row['ma60'])
                if pd.notna(row.get('rsi')):
                    indicators['rsi'] = float(row['rsi'])
                if pd.notna(row.get('macd')):
                    indicators['macd'] = float(row['macd'])
                if pd.notna(row.get('macd_signal')):
                    indicators['macd_signal'] = float(row['macd_signal'])
                if pd.notna(row.get('macd_hist')):
                    indicators['macd_hist'] = float(row['macd_hist'])
                if pd.notna(row.get('x2')):
                    indicators['x2'] = float(round(row['x2'], 4))
                if pd.notna(row.get('volume_ratio')):
                    indicators['volume_ratio'] = float(row['volume_ratio'])
                
                if indicators:
                    technical_indicators[date_str] = indicators
    
    step5_time = time.time() - start_time
    print(f"  技术指标数量: {len(technical_indicators)}")
    print(f"  耗时: {step5_time:.2f}秒")
    
    # 步骤6: 构建数据字典
    print("\n步骤6: 构建数据字典...")
    start_time = time.time()
    batch_data = []
    pre_close_series = closes.shift(1) if len(closes) > 0 else pd.Series(dtype=float)
    
    # 只处理在kline_data中存在的日期
    missing_dates_in_kline = [d for d in missing_dates if pd.to_datetime(d) in kline_data.index]
    test_count = min(100, len(missing_dates_in_kline)) if len(missing_dates_in_kline) > 0 else 0  # 只测试前100条，避免太慢
    
    for date_str in (missing_dates_in_kline[:test_count] if test_count > 0 else []):
        date_obj = pd.to_datetime(date_str)
        
        if date_obj in kline_data.index:
            row = kline_data.loc[date_obj]
            
            data = {
                'symbol': symbol,
                'name': stock_name,
                'trade_date': date_str,
                'period_type': 'daily',
                'data_source': 'akshare',
                'data_quality_score': 1.0,
                'is_valid': True,
                'open_price': float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
                'close_price': float(row.get('close', 0)) if pd.notna(row.get('close')) else None,
                'high_price': float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
                'low_price': float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
                'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
            }
            
            # 添加成交额
            if 'amount' in kline_data.columns and pd.notna(row.get('amount')):
                data['amount'] = float(row.get('amount'))
            elif data.get('close_price') and data.get('volume'):
                data['amount'] = float(data['close_price'] * data['volume'] * 100)
            
            # 添加前一日收盘价
            if date_obj in pre_close_series.index and pd.notna(pre_close_series.loc[date_obj]):
                prev_close = pre_close_series.loc[date_obj]
                if data.get('close_price'):
                    data['pre_close'] = float(prev_close)
                    data['change_amount'] = data['close_price'] - data['pre_close']
                    data['change_pct'] = (data['change_amount'] / data['pre_close']) * 100 if data['pre_close'] > 0 else 0
            
            # 计算价格区间和振幅
            if data.get('high_price') and data.get('low_price'):
                data['price_range'] = data['high_price'] - data['low_price']
            
            if data.get('pre_close') and data.get('high_price') and data.get('low_price'):
                amplitude = ((data['high_price'] - data['low_price']) / data['pre_close']) * 100 if data['pre_close'] > 0 else 0
                data['amplitude'] = round(amplitude, 2)
            
            # 添加估值指标
            if stock_info:
                if stock_info.get('pe_ratio'):
                    data['pe_ratio'] = stock_info.get('pe_ratio')
                if stock_info.get('pb_ratio'):
                    data['pb_ratio'] = stock_info.get('pb_ratio')
            
            # 计算涨跌停价
            if data.get('pre_close'):
                pre_close = data['pre_close']
                if symbol.startswith('688') or symbol.startswith('300'):
                    limit_pct = 0.20
                else:
                    limit_pct = 0.10
                
                data['limit_up'] = round(pre_close * (1 + limit_pct), 2)
                data['limit_down'] = round(pre_close * (1 - limit_pct), 2)
                data['limit_pct'] = limit_pct * 100
                
                if data.get('close_price'):
                    if abs(data['close_price'] - data['limit_up']) < 0.01:
                        data['is_limit_up'] = True
                    elif abs(data['close_price'] - data['limit_down']) < 0.01:
                        data['is_limit_down'] = True
            
            # 添加技术指标
            if date_str in technical_indicators:
                data.update(technical_indicators[date_str])
            
            # 序列化JSON字段
            import json
            if 'cost_distribution' in data and data['cost_distribution']:
                data['cost_distribution_json'] = json.dumps(data['cost_distribution'], ensure_ascii=False)
            if 'cost_distribution_history' in data and data['cost_distribution_history']:
                data['cost_distribution_history_json'] = json.dumps(data['cost_distribution_history'], ensure_ascii=False)
            if 'extra_data' in data and data['extra_data']:
                data['extra_data_json'] = json.dumps(data['extra_data'], ensure_ascii=False)
            
            batch_data.append((date_str, data))
    
    step6_time = time.time() - start_time
    missing_dates_in_kline_count = len(missing_dates_in_kline) if 'missing_dates_in_kline' in locals() else 0
    test_count_val = test_count if 'test_count' in locals() else 0
    print(f"  构建数据条数: {len(batch_data)} (测试前{test_count_val}条，实际在kline_data中的有{missing_dates_in_kline_count}条)")
    print(f"  耗时: {step6_time:.2f}秒")
    if len(batch_data) > 0 and missing_dates_in_kline_count > 0:
        print(f"  预估全部{missing_dates_in_kline_count}条耗时: {step6_time * missing_dates_in_kline_count / len(batch_data):.2f}秒")
    else:
        print(f"  没有数据可构建（数据可能已在数据库中）")
    
    # 步骤7: 批量保存
    print("\n步骤7: 批量保存到数据库...")
    start_time = time.time()
    step7_time = 0
    if batch_data:
        batch_save_data = [(symbol, date_str_item, data_item) for date_str_item, data_item in batch_data]
        save_result = storage.save_stock_daily_data_batch(batch_save_data, batch_size=200)
        step7_time = time.time() - start_time
        print(f"  成功: {save_result.get('success_count', 0)}/{save_result.get('total_count', 0)}")
        print(f"  耗时: {step7_time:.2f}秒")
        if len(batch_data) > 0:
            print(f"  预估全部{len(missing_dates)}条耗时: {step7_time * len(missing_dates) / len(batch_data):.2f}秒")
    else:
        print(f"  没有数据需要保存（数据可能已在数据库中）")
        step7_time = 0
    
    # 总结
    print("\n" + "=" * 80)
    print("性能分析总结")
    print("=" * 80)
    print(f"步骤1 - 扫描缺失日期: {step1_time:.2f}秒")
    print(f"步骤2 - 批量获取K线数据: {step2_time:.2f}秒 [注意] 用户反映约50秒")
    print(f"步骤3 - 获取股票基本信息: {step3_time:.2f}秒")
    print(f"步骤4 - 获取股票名称: {step4_time:.2f}秒")
    print(f"步骤5 - 预计算技术指标: {step5_time:.2f}秒")
    missing_dates_in_kline_count = len([d for d in missing_dates if pd.to_datetime(d) in kline_data.index])
    if len(batch_data) > 0:
        print(f"步骤6 - 构建数据字典: {step6_time:.2f}秒 (前{test_count}条)")
        print(f"      预估全部{missing_dates_in_kline_count}条: {step6_time * missing_dates_in_kline_count / len(batch_data):.2f}秒")
    else:
        print(f"步骤6 - 构建数据字典: {step6_time:.2f}秒 (没有数据可构建)")
        print(f"      预估全部{missing_dates_in_kline_count}条: 0.00秒")
    if len(batch_data) > 0:
        print(f"步骤7 - 批量保存到数据库: {step7_time:.2f}秒 (前{len(batch_data)}条)")
        print(f"      预估全部{len(missing_dates)}条: {step7_time * len(missing_dates) / len(batch_data):.2f}秒")
    else:
        print(f"步骤7 - 批量保存到数据库: {step7_time:.2f}秒 (没有数据需要保存)")
        print(f"      预估全部{len(missing_dates)}条: 0.00秒")
    
    missing_dates_in_kline_count = len([d for d in missing_dates if pd.to_datetime(d) in kline_data.index])
    if len(batch_data) > 0:
        step6_estimated = step6_time * missing_dates_in_kline_count / len(batch_data)
        step7_estimated = step7_time * missing_dates_in_kline_count / len(batch_data) if step7_time > 0 else 0
    else:
        step6_estimated = 0
        step7_estimated = 0
    
    total_estimated_time = step1_time + step2_time + step3_time + step4_time + step5_time + step6_estimated + step7_estimated
    
    print(f"\n总预估耗时: {total_estimated_time:.2f}秒 ({total_estimated_time/60:.2f}分钟)")
    print(f"\nAPI调用耗时: {step2_time:.2f}秒")
    print(f"数据处理和保存耗时: {total_estimated_time - step2_time:.2f}秒")
    
    # 找出瓶颈
    print("\n" + "=" * 80)
    print("性能瓶颈分析")
    print("=" * 80)
    
    bottlenecks = [
        ("步骤2 - 批量获取K线数据", step2_time),
        ("步骤3 - 获取股票基本信息", step3_time),
        ("步骤4 - 获取股票名称", step4_time),
        ("步骤5 - 预计算技术指标", step5_time),
        ("步骤6 - 构建数据字典", step6_estimated),
        ("步骤7 - 批量保存到数据库", step7_estimated),
    ]
    
    bottlenecks.sort(key=lambda x: x[1], reverse=True)
    
    print("耗时排序（从高到低）:")
    for i, (name, time_cost) in enumerate(bottlenecks, 1):
        percentage = (time_cost / total_estimated_time * 100) if total_estimated_time > 0 else 0
        print(f"  {i}. {name}: {time_cost:.2f}秒 ({percentage:.1f}%)")


if __name__ == '__main__':
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else '000001'
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    analyze_collection_performance(symbol, years)
