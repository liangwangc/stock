#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票数据源综合测试脚本

测试所有可用的API接口，评估：
1. 稳定性（成功率、错误率）
2. 数据完整性（字段覆盖度）
3. 性能（响应时间、速度）
4. 数据质量（数据准确性）

测试的数据源：
- akshare (stock_zh_a_hist) - 当前主要使用
- Tushare (pro.daily) - 备用数据源
- Baostock - 免费A股数据源
- akshare其他接口（stock_zh_a_hist_sina等）
"""
import os
import sys
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from collections import defaultdict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_storage import StockHistoryStorage

logger = get_logger(__name__)

# 数据库表需要的字段（与 stock_history_data 表完全对齐）
# 参考：database/stock_history_table.sql
REQUIRED_FIELDS = {
    # 基本信息
    'basic': ['symbol', 'name', 'trade_date', 'period_type'],
    
    # 基本价格数据
    'price': ['open_price', 'close_price', 'high_price', 'low_price', 'pre_close'],
    
    # 涨跌数据
    'change': ['change_amount', 'change_pct'],
    
    # 成交数据
    'volume': ['volume', 'amount', 'turnover_rate', 'volume_ratio'],
    
    # 盘口数据（实时数据，历史数据通常不可用）
    'bid_ask': ['outer_volume', 'inner_volume', 'bid_ask_ratio'],
    
    # 五档买卖盘数据（实时数据，历史数据通常不可用）
    'bid_ask_levels': ['bid_levels', 'ask_levels', 'bid_total_volume', 'ask_total_volume'],
    
    # 成本分布数据
    'cost_distribution': ['cost_distribution', 'cost_distribution_history', 'cost_distribution_intraday'],
    
    # 市值和估值
    'valuation': ['total_market_cap', 'float_market_cap', 'pe_ratio', 'pb_ratio'],
    
    # 涨跌停信息
    'limit': ['limit_up', 'limit_down', 'limit_pct', 'is_limit_up', 'is_limit_down'],
    
    # 振幅和波动
    'volatility': ['amplitude', 'price_range'],
    
    # 技术指标（收盘时计算）
    'technical': ['ma5', 'ma10', 'ma20', 'ma60', 'rsi', 'macd', 'macd_signal', 'macd_hist', 'x2'],
    
    # 资金流向数据（实时数据，历史数据通常不可用）
    'capital_flow': ['main_net_inflow', 'super_large_inflow', 'large_inflow', 'medium_inflow', 'small_inflow'],
    
    # 融资融券数据
    'margin': ['margin_balance', 'short_balance', 'margin_ratio'],
    
    # 其他数据
    'other': ['extra_data', 'data_source', 'data_quality_score', 'is_valid']
}

# 所有字段列表
ALL_REQUIRED_FIELDS = []
for field_group in REQUIRED_FIELDS.values():
    ALL_REQUIRED_FIELDS.extend(field_group)

# 历史数据API通常能提供的基础字段（核心字段）
# 这些字段是评估API数据质量的关键指标
CORE_FIELDS = [
    'symbol', 'name', 'trade_date',
    'open_price', 'close_price', 'high_price', 'low_price', 'pre_close',
    'change_amount', 'change_pct',
    'volume', 'amount'
]

# 历史数据API可能提供的高级字段（加分项）
ADVANCED_FIELDS = [
    'turnover_rate', 'volume_ratio', 'amplitude',
    'pe_ratio', 'pb_ratio',
    'limit_up', 'limit_down', 'limit_pct',
    'ma5', 'ma10', 'ma20', 'ma60',
    'rsi', 'macd', 'macd_signal', 'macd_hist'
]

# 实时数据字段（历史数据API通常不可用，不计入数据质量评估）
REALTIME_FIELDS = [
    'outer_volume', 'inner_volume', 'bid_ask_ratio',
    'bid_levels', 'ask_levels', 'bid_total_volume', 'ask_total_volume',
    'cost_distribution_intraday',
    'total_market_cap', 'float_market_cap',
    'main_net_inflow', 'super_large_inflow', 'large_inflow', 'medium_inflow', 'small_inflow'
]


class DataSourceTester:
    """数据源测试器"""
    
    def __init__(self):
        self.logger = logger
        self.results = []
        
    def test_akshare_stock_zh_a_hist(self, symbol: str, start_date: str, end_date: str, 
                                     test_name: str = "akshare.stock_zh_a_hist") -> Dict:
        """测试 akshare.stock_zh_a_hist 接口"""
        result = {
            'source': test_name,
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'success': False,
            'error': None,
            'response_time': 0,
            'records_count': 0,
            'fields_available': [],
            'fields_missing': [],
            'data_quality': 0.0,
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            import akshare as ak
            
            start_time = time.time()
            
            # 转换日期格式
            start_date_str = start_date.replace('-', '')
            end_date_str = end_date.replace('-', '')
            
            # 调用API
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date_str,
                end_date=end_date_str,
                adjust="qfq"
            )
            
            response_time = time.time() - start_time
            result['response_time'] = response_time
            
            if df.empty:
                result['error'] = '返回空数据'
                return result
            
            result['success'] = True
            result['records_count'] = len(df)
            
            # 检查字段映射
            field_mapping = {
                '日期': 'trade_date',
                '开盘': 'open_price',
                '收盘': 'close_price',
                '最高': 'high_price',
                '最低': 'low_price',
                '成交量': 'volume',
                '成交额': 'amount',
                '换手率': 'turnover_rate',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '振幅': 'amplitude'
            }
            
            # 检查可用字段
            available_fields = []
            for col in df.columns:
                col_clean = col.strip()
                if col_clean in field_mapping:
                    available_fields.append(field_mapping[col_clean])
                elif col_clean.lower() in ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']:
                    available_fields.append(col_clean.lower())
            
            result['fields_available'] = available_fields
            
            # 计算数据质量得分（基于字段覆盖度）
            # 对于历史数据API，主要评估核心字段和高级字段，不评估实时数据字段
            evaluable_fields = CORE_FIELDS + ADVANCED_FIELDS
            required_count = len(evaluable_fields)
            available_count = len([f for f in evaluable_fields if f in available_fields])
            result['data_quality'] = available_count / required_count if required_count > 0 else 0.0
            
            # 检查缺失字段（只检查可评估字段）
            result['fields_missing'] = [f for f in evaluable_fields if f not in available_fields]
            
            # 额外记录：核心字段覆盖度
            core_available = len([f for f in CORE_FIELDS if f in available_fields])
            result['core_fields_coverage'] = core_available / len(CORE_FIELDS) if CORE_FIELDS else 0.0
            
            self.logger.info(f"  ✓ {test_name}: 成功获取 {len(df)} 条记录，响应时间 {response_time:.2f}秒，数据质量 {result['data_quality']:.2%}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"  ✗ {test_name}: {str(e)}")
        
        return result
    
    def test_tushare_daily(self, symbol: str, start_date: str, end_date: str) -> Dict:
        """测试 Tushare pro.daily 接口"""
        result = {
            'source': 'Tushare.pro.daily',
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'success': False,
            'error': None,
            'response_time': 0,
            'records_count': 0,
            'fields_available': [],
            'fields_missing': [],
            'data_quality': 0.0,
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            import tushare as ts
            from config import TUSHARE_TOKEN
            
            if not TUSHARE_TOKEN:
                result['error'] = 'Tushare token未配置'
                return result
            
            ts.set_token(TUSHARE_TOKEN)
            pro = ts.pro_api()
            
            start_time = time.time()
            
            # 转换股票代码格式（Tushare格式：000001.SZ 或 600519.SH）
            if symbol.startswith('6'):
                ts_code = f"{symbol}.SH"
            elif symbol.startswith(('0', '3')):
                ts_code = f"{symbol}.SZ"
            else:
                ts_code = symbol
            
            # 转换日期格式
            start_date_str = start_date.replace('-', '')
            end_date_str = end_date.replace('-', '')
            
            # 调用API
            df = pro.daily(
                ts_code=ts_code,
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            response_time = time.time() - start_time
            result['response_time'] = response_time
            
            if df.empty:
                result['error'] = '返回空数据'
                return result
            
            result['success'] = True
            result['records_count'] = len(df)
            
            # Tushare字段映射
            field_mapping = {
                'trade_date': 'trade_date',
                'open': 'open_price',
                'close': 'close_price',
                'high': 'high_price',
                'low': 'low_price',
                'vol': 'volume',
                'amount': 'amount',
                'pct_chg': 'change_pct',
                'change': 'change_amount',
                'pre_close': 'pre_close',
                'turnover': 'turnover_rate'
            }
            
            # 检查可用字段
            available_fields = []
            for col in df.columns:
                if col in field_mapping:
                    available_fields.append(field_mapping[col])
            
            result['fields_available'] = available_fields
            
            # 计算数据质量得分（基于核心字段和高级字段）
            evaluable_fields = CORE_FIELDS + ADVANCED_FIELDS
            required_count = len(evaluable_fields)
            available_count = len([f for f in evaluable_fields if f in available_fields])
            result['data_quality'] = available_count / required_count if required_count > 0 else 0.0
            
            result['fields_missing'] = [f for f in evaluable_fields if f not in available_fields]
            
            # 额外记录：核心字段覆盖度
            core_available = len([f for f in CORE_FIELDS if f in available_fields])
            result['core_fields_coverage'] = core_available / len(CORE_FIELDS) if CORE_FIELDS else 0.0
            
            self.logger.info(f"  ✓ Tushare: 成功获取 {len(df)} 条记录，响应时间 {response_time:.2f}秒，数据质量 {result['data_quality']:.2%}")
            
        except Exception as e:
            result['error'] = str(e)
            error_str = str(e).lower()
            if 'rate limit' in error_str or '429' in error_str or 'too many requests' in error_str:
                result['error'] = f"速率限制: {str(e)}"
            elif 'permission' in error_str or '权限' in error_str:
                result['error'] = f"权限不足: {str(e)}"
            else:
                result['error'] = str(e)
            self.logger.error(f"  ✗ Tushare: {result['error']}")
        
        return result
    
    def test_baostock(self, symbol: str, start_date: str, end_date: str) -> Dict:
        """测试 Baostock 接口"""
        result = {
            'source': 'Baostock',
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'success': False,
            'error': None,
            'response_time': 0,
            'records_count': 0,
            'fields_available': [],
            'fields_missing': [],
            'data_quality': 0.0,
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            import baostock as bs
            
            start_time = time.time()
            
            # 转换股票代码格式（Baostock格式：sh.600519 或 sz.000001）
            if symbol.startswith('6'):
                bs_code = f"sh.{symbol}"
            elif symbol.startswith(('0', '3')):
                bs_code = f"sz.{symbol}"
            else:
                bs_code = symbol
            
            # 登录Baostock
            lg = bs.login()
            if lg.error_code != '0':
                result['error'] = f"Baostock登录失败: {lg.error_msg}"
                return result
            
            try:
                # 查询历史数据
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="2"  # 前复权
                )
                
                if rs.error_code != '0':
                    result['error'] = f"Baostock查询失败: {rs.error_msg}"
                    return result
                
                # 转换为DataFrame
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                if not data_list:
                    result['error'] = '返回空数据'
                    return result
                
                df = pd.DataFrame(data_list, columns=rs.fields)
                
                response_time = time.time() - start_time
                result['response_time'] = response_time
                
                result['success'] = True
                result['records_count'] = len(df)
                
                # Baostock字段映射
                field_mapping = {
                    'date': 'trade_date',
                    'open': 'open_price',
                    'close': 'close_price',
                    'high': 'high_price',
                    'low': 'low_price',
                    'preclose': 'pre_close',
                    'volume': 'volume',
                    'amount': 'amount',
                    'turn': 'turnover_rate',
                    'pctChg': 'change_pct'
                }
                
                # 检查可用字段
                available_fields = []
                for col in df.columns:
                    if col in field_mapping:
                        available_fields.append(field_mapping[col])
                
                result['fields_available'] = available_fields
                
                # 计算数据质量得分（基于核心字段和高级字段）
                evaluable_fields = CORE_FIELDS + ADVANCED_FIELDS
                required_count = len(evaluable_fields)
                available_count = len([f for f in evaluable_fields if f in available_fields])
                result['data_quality'] = available_count / required_count if required_count > 0 else 0.0
                
                result['fields_missing'] = [f for f in evaluable_fields if f not in available_fields]
                
                # 额外记录：核心字段覆盖度
                core_available = len([f for f in CORE_FIELDS if f in available_fields])
                result['core_fields_coverage'] = core_available / len(CORE_FIELDS) if CORE_FIELDS else 0.0
                
                self.logger.info(f"  ✓ Baostock: 成功获取 {len(df)} 条记录，响应时间 {response_time:.2f}秒，数据质量 {result['data_quality']:.2%}")
                
            finally:
                bs.logout()
                
        except ImportError:
            result['error'] = 'Baostock库未安装（pip install baostock）'
            self.logger.warning(f"  - Baostock: {result['error']}")
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"  ✗ Baostock: {str(e)}")
        
        return result
    
    def test_akshare_alternative(self, symbol: str, start_date: str, end_date: str, 
                                 api_func_name: str, api_func) -> Dict:
        """测试 akshare 的其他接口"""
        result = {
            'source': f'akshare.{api_func_name}',
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'success': False,
            'error': None,
            'response_time': 0,
            'records_count': 0,
            'fields_available': [],
            'fields_missing': [],
            'data_quality': 0.0,
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            start_time = time.time()
            
            # 转换日期格式
            start_date_str = start_date.replace('-', '')
            end_date_str = end_date.replace('-', '')
            
            # 尝试调用API（不同接口参数可能不同）
            try:
                df = api_func(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date_str,
                    end_date=end_date_str,
                    adjust="qfq"
                )
            except TypeError:
                # 如果参数不匹配，尝试其他参数组合
                try:
                    df = api_func(symbol=symbol, start_date=start_date_str, end_date=end_date_str)
                except TypeError:
                    df = api_func(symbol=symbol)
            
            response_time = time.time() - start_time
            result['response_time'] = response_time
            
            if df.empty:
                result['error'] = '返回空数据'
                return result
            
            result['success'] = True
            result['records_count'] = len(df)
            
            # 检查字段
            field_mapping = {
                '日期': 'trade_date',
                '开盘': 'open_price',
                '收盘': 'close_price',
                '最高': 'high_price',
                '最低': 'low_price',
                '成交量': 'volume',
                '成交额': 'amount'
            }
            
            available_fields = []
            for col in df.columns:
                col_clean = col.strip()
                if col_clean in field_mapping:
                    available_fields.append(field_mapping[col_clean])
            
            result['fields_available'] = available_fields
            
            # 计算数据质量得分（基于核心字段和高级字段）
            evaluable_fields = CORE_FIELDS + ADVANCED_FIELDS
            required_count = len(evaluable_fields)
            available_count = len([f for f in evaluable_fields if f in available_fields])
            result['data_quality'] = available_count / required_count if required_count > 0 else 0.0
            
            result['fields_missing'] = [f for f in evaluable_fields if f not in available_fields]
            
            # 额外记录：核心字段覆盖度
            core_available = len([f for f in CORE_FIELDS if f in available_fields])
            result['core_fields_coverage'] = core_available / len(CORE_FIELDS) if CORE_FIELDS else 0.0
            
            self.logger.info(f"  ✓ {result['source']}: 成功获取 {len(df)} 条记录，响应时间 {response_time:.2f}秒，数据质量 {result['data_quality']:.2%}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.debug(f"  ✗ {result['source']}: {str(e)}")
        
        return result
    
    def run_stability_test(self, symbol: str, start_date: str, end_date: str, 
                           iterations: int = 10) -> Dict:
        """运行稳定性测试（多次调用，统计成功率）"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"稳定性测试: {symbol} ({iterations}次调用)")
        self.logger.info(f"{'='*60}")
        
        test_results = defaultdict(list)
        
        # 测试各个数据源
        sources_to_test = [
            ('akshare.stock_zh_a_hist', self.test_akshare_stock_zh_a_hist),
            ('Tushare.pro.daily', self.test_tushare_daily),
            ('Baostock', self.test_baostock)
        ]
        
        for source_name, test_func in sources_to_test:
            self.logger.info(f"\n测试数据源: {source_name}")
            success_count = 0
            total_time = 0
            errors = []
            
            for i in range(iterations):
                try:
                    result = test_func(symbol, start_date, end_date)
                    test_results[source_name].append(result)
                    
                    if result['success']:
                        success_count += 1
                        total_time += result['response_time']
                    else:
                        errors.append(result['error'])
                    
                    # 避免请求过快
                    if i < iterations - 1:
                        time.sleep(1.0)  # 每次调用间隔1秒
                        
                except Exception as e:
                    errors.append(str(e))
                    test_results[source_name].append({
                        'success': False,
                        'error': str(e)
                    })
            
            # 统计结果
            success_rate = success_count / iterations
            avg_time = total_time / success_count if success_count > 0 else 0
            
            self.logger.info(f"\n{source_name} 稳定性测试结果:")
            self.logger.info(f"  成功率: {success_count}/{iterations} ({success_rate:.2%})")
            self.logger.info(f"  平均响应时间: {avg_time:.2f}秒")
            if errors:
                error_counts = {}
                for err in errors:
                    error_counts[err] = error_counts.get(err, 0) + 1
                self.logger.info(f"  错误类型: {dict(error_counts)}")
        
        return dict(test_results)
    
    def run_comprehensive_test(self, symbols: List[str], start_date: str, end_date: str, 
                               batch_size: int = 50, delay_between_stocks: float = 1.0,
                               delay_between_batches: float = 5.0) -> List[Dict]:
        """
        运行综合测试
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            batch_size: 批次大小（每批测试多少只股票，默认50）
            delay_between_stocks: 每只股票之间的延迟（秒，默认1.0）
            delay_between_batches: 批次之间的延迟（秒，默认5.0）
        """
        self.logger.info("=" * 80)
        self.logger.info("股票数据源综合测试")
        self.logger.info("=" * 80)
        self.logger.info(f"测试股票数量: {len(symbols)}")
        self.logger.info(f"日期范围: {start_date} 至 {end_date}")
        self.logger.info(f"批次大小: {batch_size} 只股票/批次")
        self.logger.info(f"股票间延迟: {delay_between_stocks} 秒")
        self.logger.info(f"批次间延迟: {delay_between_batches} 秒")
        self.logger.info("=" * 80)
        
        all_results = []
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        
        # 统计限制情况
        rate_limit_stats = defaultdict(int)
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(symbols))
            batch_symbols = symbols[start_idx:end_idx]
            
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"批次 {batch_idx + 1}/{total_batches}: 测试股票 {start_idx + 1}-{end_idx} ({len(batch_symbols)} 只)")
            self.logger.info(f"{'='*80}")
            
            batch_results = []
            batch_rate_limit_count = 0
            
            for symbol_idx, symbol in enumerate(batch_symbols):
                self.logger.info(f"\n[{symbol_idx + 1}/{len(batch_symbols)}] 测试股票: {symbol}")
                
                # 测试各个数据源
                symbol_results = []
                
                # 1. akshare.stock_zh_a_hist (主要接口)
                try:
                    result = self.test_akshare_stock_zh_a_hist(symbol, start_date, end_date)
                    symbol_results.append(result)
                    
                    # 检测速率限制
                    if not result['success'] and result.get('error'):
                        error_lower = result['error'].lower()
                        if any(keyword in error_lower for keyword in ['rate limit', '429', 'too many requests', 
                                                                      '请求过于频繁', '访问频率', '请求次数', 
                                                                      '请求限制', '频率限制', '访问限制']):
                            batch_rate_limit_count += 1
                            rate_limit_stats['akshare.stock_zh_a_hist'] += 1
                            self.logger.warning(f"  ⚠ 检测到速率限制！已处理 {len(all_results) + len(batch_results)} 只股票")
                            
                            # 如果连续触发限制，增加延迟
                            if batch_rate_limit_count >= 3:
                                self.logger.warning(f"  ⚠ 连续触发限制，增加延迟到 {delay_between_stocks * 2} 秒")
                                time.sleep(delay_between_stocks * 2)
                            else:
                                time.sleep(delay_between_stocks)
                        else:
                            time.sleep(delay_between_stocks)
                    else:
                        time.sleep(delay_between_stocks)
                except Exception as e:
                    self.logger.error(f"  ✗ akshare.stock_zh_a_hist 测试异常: {str(e)}")
                    symbol_results.append({
                        'source': 'akshare.stock_zh_a_hist',
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
                    time.sleep(delay_between_stocks)
                
                # 2. Tushare
                try:
                    result = self.test_tushare_daily(symbol, start_date, end_date)
                    symbol_results.append(result)
                    
                    # 检测速率限制
                    if not result['success'] and result.get('error'):
                        error_lower = result['error'].lower()
                        if any(keyword in error_lower for keyword in ['rate limit', '429', 'too many requests', 
                                                                      '请求过于频繁', '访问频率', '请求次数', 
                                                                      '请求限制', '频率限制', '访问限制']):
                            rate_limit_stats['Tushare.pro.daily'] += 1
                            self.logger.warning(f"  ⚠ Tushare速率限制")
                    
                    time.sleep(delay_between_stocks)
                except Exception as e:
                    self.logger.error(f"  ✗ Tushare 测试异常: {str(e)}")
                    symbol_results.append({
                        'source': 'Tushare.pro.daily',
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
                    time.sleep(delay_between_stocks)
                
                # 3. Baostock
                try:
                    result = self.test_baostock(symbol, start_date, end_date)
                    symbol_results.append(result)
                    time.sleep(delay_between_stocks)
                except Exception as e:
                    self.logger.error(f"  ✗ Baostock 测试异常: {str(e)}")
                    symbol_results.append({
                        'source': 'Baostock',
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
                    time.sleep(delay_between_stocks)
                
                batch_results.extend(symbol_results)
                
                # 每10只股票显示一次进度
                if (symbol_idx + 1) % 10 == 0 or symbol_idx + 1 == len(batch_symbols):
                    total_processed = len(all_results) + len(batch_results)
                    success_count = sum(1 for r in batch_results if r.get('success'))
                    self.logger.info(f"  进度: {total_processed}/{len(symbols) * 3} 次测试 - "
                                   f"本批次成功: {success_count}/{len(batch_results)}")
            
            all_results.extend(batch_results)
            
            # 批次间延迟
            if batch_idx < total_batches - 1:
                # 如果本批次触发限制较多，增加延迟
                if batch_rate_limit_count >= 5:
                    extra_delay = delay_between_batches * 2
                    self.logger.info(f"\n批次完成，本批次触发限制 {batch_rate_limit_count} 次，"
                                   f"增加延迟到 {extra_delay} 秒后继续下一批次...")
                    time.sleep(extra_delay)
                else:
                    self.logger.info(f"\n批次完成，等待 {delay_between_batches} 秒后继续下一批次...")
                    time.sleep(delay_between_batches)
            
            # 如果连续多个批次都触发限制，建议停止
            if batch_rate_limit_count >= len(batch_symbols) * 0.5:  # 超过50%触发限制
                self.logger.warning(f"\n⚠ 警告：本批次超过50%的请求触发限制，建议：")
                self.logger.warning(f"  1. 增加延迟时间（当前: {delay_between_stocks}秒）")
                self.logger.warning(f"  2. 减小批次大小（当前: {batch_size}）")
                self.logger.warning(f"  3. 等待一段时间后继续")
        
        # 打印限制统计
        if rate_limit_stats:
            self.logger.info(f"\n{'='*80}")
            self.logger.info("速率限制统计:")
            for source, count in rate_limit_stats.items():
                self.logger.info(f"  {source}: {count} 次")
        
        return all_results
    
    def generate_report(self, results: List[Dict]) -> Dict:
        """生成测试报告"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("测试报告")
        self.logger.info("=" * 80)
        
        # 按数据源分组统计
        source_stats = defaultdict(lambda: {
            'total': 0,
            'success': 0,
            'failed': 0,
            'total_time': 0,
            'avg_time': 0,
            'total_records': 0,
            'avg_records': 0,
            'total_quality': 0,
            'avg_quality': 0,
            'errors': []
        })
        
        for result in results:
            source = result['source']
            stats = source_stats[source]
            stats['total'] += 1
            
            if result['success']:
                stats['success'] += 1
                stats['total_time'] += result.get('response_time', 0)
                stats['total_records'] += result.get('records_count', 0)
                stats['total_quality'] += result.get('data_quality', 0)
            else:
                stats['failed'] += 1
                if result.get('error'):
                    stats['errors'].append(result['error'])
        
        # 计算平均值
        for source, stats in source_stats.items():
            if stats['success'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['success']
                stats['avg_records'] = stats['total_records'] / stats['success']
                stats['avg_quality'] = stats['total_quality'] / stats['success']
                # 计算平均核心字段覆盖度
                total_core_coverage = sum(r.get('core_fields_coverage', 0) for r in results if r.get('source') == source and r.get('success'))
                stats['avg_core_coverage'] = total_core_coverage / stats['success'] if stats['success'] > 0 else 0.0
        
        # 打印报告
        self.logger.info("\n数据源对比:")
        self.logger.info("-" * 80)
        
        report_data = []
        for source, stats in sorted(source_stats.items(), key=lambda x: x[1]['success'] / max(x[1]['total'], 1), reverse=True):
            success_rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
            
            self.logger.info(f"\n{source}:")
            self.logger.info(f"  总测试次数: {stats['total']}")
            self.logger.info(f"  成功: {stats['success']} ({success_rate:.2%})")
            self.logger.info(f"  失败: {stats['failed']}")
            if stats['success'] > 0:
                self.logger.info(f"  平均响应时间: {stats['avg_time']:.2f}秒")
                self.logger.info(f"  平均记录数: {stats['avg_records']:.0f}条")
                self.logger.info(f"  平均数据质量: {stats['avg_quality']:.2%}")
                if 'avg_core_coverage' in stats:
                    self.logger.info(f"  核心字段覆盖度: {stats['avg_core_coverage']:.2%}")
            error_counts = {}
            if stats['errors']:
                for err in stats['errors']:
                    error_counts[err] = error_counts.get(err, 0) + 1
                self.logger.info(f"  错误类型: {dict(error_counts)}")
            
            report_data.append({
                'source': source,
                'total_tests': stats['total'],
                'success_count': stats['success'],
                'success_rate': success_rate,
                'avg_response_time': stats['avg_time'],
                'avg_records': stats['avg_records'],
                'avg_quality': stats['avg_quality'],
                'avg_core_coverage': stats.get('avg_core_coverage', 0.0),
                'errors': error_counts
            })
        
        # 推荐最佳数据源
        self.logger.info("\n" + "=" * 80)
        self.logger.info("推荐数据源排序（综合考虑稳定性、速度、数据质量）:")
        self.logger.info("=" * 80)
        
        # 计算综合得分（成功率权重50%，速度权重20%，数据质量权重30%）
        scored_sources = []
        for data in report_data:
            if data['success_rate'] > 0:
                # 速度得分（响应时间越短得分越高，假设5秒为基准）
                speed_score = max(0, 1 - data['avg_response_time'] / 5.0) if data['avg_response_time'] > 0 else 0
                
                # 综合得分
                composite_score = (
                    data['success_rate'] * 0.5 +  # 稳定性权重50%
                    speed_score * 0.2 +  # 速度权重20%
                    data['avg_quality'] * 0.3  # 数据质量权重30%
                )
                
                scored_sources.append({
                    **data,
                    'composite_score': composite_score
                })
        
        # 按综合得分排序
        scored_sources.sort(key=lambda x: x['composite_score'], reverse=True)
        
        for i, data in enumerate(scored_sources, 1):
            self.logger.info(f"\n{i}. {data['source']}")
            self.logger.info(f"   综合得分: {data['composite_score']:.3f}")
            self.logger.info(f"   成功率: {data['success_rate']:.2%}")
            self.logger.info(f"   平均响应时间: {data['avg_response_time']:.2f}秒")
            self.logger.info(f"   数据质量: {data['avg_quality']:.2%}")
        
        # 详细的字段对比总结
        self.logger.info("\n" + "=" * 80)
        self.logger.info("各接口字段获取情况详细对比")
        self.logger.info("=" * 80)
        
        # 收集每个数据源的字段信息
        source_fields_info = defaultdict(lambda: {
            'all_fields': set(),
            'core_fields': set(),
            'advanced_fields': set(),
            'success_count': 0
        })
        
        for result in results:
            if result.get('success'):
                source = result['source']
                fields = set(result.get('fields_available', []))
                source_fields_info[source]['all_fields'].update(fields)
                source_fields_info[source]['core_fields'].update([f for f in fields if f in CORE_FIELDS])
                source_fields_info[source]['advanced_fields'].update([f for f in fields if f in ADVANCED_FIELDS])
                source_fields_info[source]['success_count'] += 1
        
        # 为每个数据源生成详细报告
        for source in sorted(source_stats.keys()):
            if source_stats[source]['success'] == 0:
                continue
                
            fields_info = source_fields_info[source]
            all_fields = sorted(list(fields_info['all_fields']))
            core_fields_available = sorted(list(fields_info['core_fields']))
            advanced_fields_available = sorted(list(fields_info['advanced_fields']))
            
            # 计算缺失字段
            core_fields_missing = sorted([f for f in CORE_FIELDS if f not in fields_info['core_fields']])
            advanced_fields_missing = sorted([f for f in ADVANCED_FIELDS if f not in fields_info['advanced_fields']])
            
            # 计算完整性
            core_completeness = len(core_fields_available) / len(CORE_FIELDS) if CORE_FIELDS else 0.0
            advanced_completeness = len(advanced_fields_available) / len(ADVANCED_FIELDS) if ADVANCED_FIELDS else 0.0
            
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"数据源: {source}")
            self.logger.info(f"{'='*80}")
            
            # 核心字段情况
            self.logger.info(f"\n【核心字段】完整性: {len(core_fields_available)}/{len(CORE_FIELDS)} ({core_completeness:.2%})")
            if core_fields_available:
                self.logger.info(f"  ✓ 已获取字段 ({len(core_fields_available)}个):")
                for field in core_fields_available:
                    self.logger.info(f"    - {field}")
            else:
                self.logger.info(f"  ✗ 未获取任何核心字段")
            
            if core_fields_missing:
                self.logger.info(f"  ✗ 缺失字段 ({len(core_fields_missing)}个):")
                for field in core_fields_missing:
                    self.logger.info(f"    - {field}")
            else:
                self.logger.info(f"  ✓ 核心字段完整！")
            
            # 高级字段情况
            self.logger.info(f"\n【高级字段】完整性: {len(advanced_fields_available)}/{len(ADVANCED_FIELDS)} ({advanced_completeness:.2%})")
            if advanced_fields_available:
                self.logger.info(f"  ✓ 已获取字段 ({len(advanced_fields_available)}个):")
                for field in advanced_fields_available:
                    self.logger.info(f"    - {field}")
            else:
                self.logger.info(f"  ✗ 未获取任何高级字段")
            
            if advanced_fields_missing:
                self.logger.info(f"  ✗ 缺失字段 ({len(advanced_fields_missing)}个):")
                for field in advanced_fields_missing:
                    self.logger.info(f"    - {field}")
            else:
                self.logger.info(f"  ✓ 高级字段完整！")
            
            # 所有获取的字段
            self.logger.info(f"\n【所有获取字段】共 {len(all_fields)} 个:")
            if all_fields:
                # 按类别分组显示
                field_categories = {
                    '基本信息': [f for f in all_fields if f in ['symbol', 'name', 'trade_date', 'period_type']],
                    '价格数据': [f for f in all_fields if 'price' in f or f in ['pre_close']],
                    '涨跌数据': [f for f in all_fields if 'change' in f],
                    '成交数据': [f for f in all_fields if f in ['volume', 'amount', 'turnover_rate', 'volume_ratio']],
                    '技术指标': [f for f in all_fields if f in ['ma5', 'ma10', 'ma20', 'ma60', 'rsi', 'macd', 'macd_signal', 'macd_hist', 'x2']],
                    '估值数据': [f for f in all_fields if f in ['pe_ratio', 'pb_ratio']],
                    '其他': [f for f in all_fields if f not in CORE_FIELDS + ADVANCED_FIELDS]
                }
                
                for category, fields in field_categories.items():
                    if fields:
                        self.logger.info(f"  {category}: {', '.join(sorted(fields))}")
            else:
                self.logger.info("  （无）")
            
            # 总结
            self.logger.info(f"\n【总结】")
            if core_completeness == 1.0:
                self.logger.info(f"  ✓ 核心字段完整，满足基本数据需求")
            elif core_completeness >= 0.8:
                self.logger.info(f"  ⚠ 核心字段基本完整（{core_completeness:.2%}），缺少 {len(core_fields_missing)} 个字段")
            else:
                self.logger.info(f"  ✗ 核心字段不完整（{core_completeness:.2%}），缺少 {len(core_fields_missing)} 个字段，可能影响数据质量")
            
            if advanced_completeness == 1.0:
                self.logger.info(f"  ✓ 高级字段完整，数据质量优秀")
            elif advanced_completeness >= 0.5:
                self.logger.info(f"  ⚠ 高级字段部分可用（{advanced_completeness:.2%}），缺少 {len(advanced_fields_missing)} 个字段")
            else:
                self.logger.info(f"  ✗ 高级字段较少（{advanced_completeness:.2%}），缺少 {len(advanced_fields_missing)} 个字段")
        
        # 生成字段对比总结到返回数据
        fields_summary = {}
        for source, fields_info in source_fields_info.items():
            if source_stats[source]['success'] > 0:
                fields_summary[source] = {
                    'all_fields': sorted(list(fields_info['all_fields'])),
                    'core_fields_available': sorted(list(fields_info['core_fields'])),
                    'advanced_fields_available': sorted(list(fields_info['advanced_fields'])),
                    'core_fields_missing': sorted([f for f in CORE_FIELDS if f not in fields_info['core_fields']]),
                    'advanced_fields_missing': sorted([f for f in ADVANCED_FIELDS if f not in fields_info['advanced_fields']]),
                    'core_completeness': len(fields_info['core_fields']) / len(CORE_FIELDS) if CORE_FIELDS else 0.0,
                    'advanced_completeness': len(fields_info['advanced_fields']) / len(ADVANCED_FIELDS) if ADVANCED_FIELDS else 0.0
                }
        
        return {
            'summary': report_data,
            'recommendations': scored_sources,
            'fields_summary': fields_summary,
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


    def run_pressure_test(self, start_date: str, end_date: str, 
                          max_stocks: int = None, batch_size: int = 100,
                          delay_between_batches: float = 2.0) -> Dict:
        """运行压力测试（全量获取股票信息，检测API限制）"""
        self.logger.info("=" * 80)
        self.logger.info("压力测试：全量获取股票信息，检测API限制")
        self.logger.info("=" * 80)
        self.logger.info(f"日期范围: {start_date} 至 {end_date}")
        self.logger.info(f"批次大小: {batch_size} 只股票/批次")
        self.logger.info(f"批次间延迟: {delay_between_batches} 秒")
        if max_stocks:
            self.logger.info(f"最大测试股票数: {max_stocks}")
        self.logger.info("=" * 80)
        
        # 获取全量股票列表
        try:
            from data_source.stock_data_source import StockDataSource
            data_source = StockDataSource()
            self.logger.info("\n正在获取全量股票列表...")
            all_stocks = data_source.get_all_stock_list(limit=max_stocks, sort_by_turnover=False, use_cache=True)
            symbols = [s.get('symbol') for s in all_stocks if s.get('symbol')]
            
            if not symbols:
                self.logger.error("未能获取到股票列表")
                return {}
            
            self.logger.info(f"成功获取 {len(symbols)} 只股票")
            
            if max_stocks and len(symbols) > max_stocks:
                symbols = symbols[:max_stocks]
                self.logger.info(f"限制为前 {max_stocks} 只股票进行测试")
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return {}
        
        # 测试各个数据源
        sources_to_test = [
            ('akshare.stock_zh_a_hist', self.test_akshare_stock_zh_a_hist),
            ('Tushare.pro.daily', self.test_tushare_daily),
            ('Baostock', self.test_baostock)
        ]
        
        pressure_test_results = {}
        
        for source_name, test_func in sources_to_test:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"压力测试数据源: {source_name}")
            self.logger.info(f"{'='*80}")
            
            source_results = {
                'source': source_name,
                'total_stocks': len(symbols),
                'success_count': 0,
                'fail_count': 0,
                'rate_limit_count': 0,
                'rate_limit_threshold': None,  # 首次触发限制的股票数量
                'rate_limit_errors': [],
                'other_errors': [],
                'response_times': [],
                'success_symbols': [],
                'failed_symbols': [],
                'test_start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 分批测试
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            rate_limit_triggered = False
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(symbols))
                batch_symbols = symbols[start_idx:end_idx]
                
                self.logger.info(f"\n批次 {batch_idx + 1}/{total_batches}: 测试股票 {start_idx + 1}-{end_idx} ({len(batch_symbols)} 只)")
                
                for symbol_idx, symbol in enumerate(batch_symbols):
                    try:
                        result = test_func(symbol, start_date, end_date)
                        
                        if result['success']:
                            source_results['success_count'] += 1
                            source_results['success_symbols'].append(symbol)
                            if result.get('response_time'):
                                source_results['response_times'].append(result['response_time'])
                        else:
                            source_results['fail_count'] += 1
                            source_results['failed_symbols'].append(symbol)
                            
                            error = result.get('error', '')
                            error_lower = error.lower()
                            
                            # 检测速率限制
                            if any(keyword in error_lower for keyword in ['rate limit', '429', 'too many requests', 
                                                                          '请求过于频繁', '访问频率', '请求次数', 
                                                                          '请求限制', '频率限制', '访问限制']):
                                source_results['rate_limit_count'] += 1
                                source_results['rate_limit_errors'].append({
                                    'symbol': symbol,
                                    'error': error,
                                    'batch': batch_idx + 1,
                                    'position': symbol_idx + 1,
                                    'total_processed': source_results['success_count'] + source_results['fail_count']
                                })
                                
                                # 记录首次触发限制的阈值
                                if not rate_limit_triggered:
                                    rate_limit_triggered = True
                                    source_results['rate_limit_threshold'] = source_results['success_count'] + source_results['fail_count']
                                    self.logger.warning(f"  ⚠ 检测到速率限制！已处理 {source_results['rate_limit_threshold']} 只股票")
                                    
                                    # 如果触发限制，询问是否继续
                                    self.logger.warning(f"  建议：停止测试或增加延迟时间")
                            else:
                                source_results['other_errors'].append({
                                    'symbol': symbol,
                                    'error': error
                                })
                        
                        # 每10只股票显示一次进度
                        if (symbol_idx + 1) % 10 == 0 or symbol_idx + 1 == len(batch_symbols):
                            total_processed = source_results['success_count'] + source_results['fail_count']
                            success_rate = source_results['success_count'] / total_processed if total_processed > 0 else 0
                            self.logger.info(f"  进度: {total_processed}/{len(symbols)} ({total_processed*100//len(symbols)}%) - "
                                           f"成功: {source_results['success_count']}, 失败: {source_results['fail_count']}, "
                                           f"成功率: {success_rate:.2%}")
                        
                        # 延迟（避免请求过快）
                        if symbol_idx < len(batch_symbols) - 1:
                            time.sleep(0.3)  # 每只股票之间延迟0.3秒
                    
                    except Exception as e:
                        source_results['fail_count'] += 1
                        source_results['failed_symbols'].append(symbol)
                        source_results['other_errors'].append({
                            'symbol': symbol,
                            'error': str(e)
                        })
                        self.logger.error(f"  ✗ {symbol}: 异常 - {str(e)}")
                
                # 批次间延迟
                if batch_idx < total_batches - 1:
                    self.logger.info(f"  批次完成，等待 {delay_between_batches} 秒后继续下一批次...")
                    time.sleep(delay_between_batches)
            
            # 计算统计信息
            total_processed = source_results['success_count'] + source_results['fail_count']
            source_results['success_rate'] = source_results['success_count'] / total_processed if total_processed > 0 else 0
            source_results['avg_response_time'] = sum(source_results['response_times']) / len(source_results['response_times']) if source_results['response_times'] else 0
            source_results['test_end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 打印结果
            self.logger.info(f"\n{source_name} 压力测试结果:")
            self.logger.info(f"  总股票数: {len(symbols)}")
            self.logger.info(f"  成功: {source_results['success_count']} ({source_results['success_rate']:.2%})")
            self.logger.info(f"  失败: {source_results['fail_count']}")
            self.logger.info(f"  速率限制次数: {source_results['rate_limit_count']}")
            if source_results['rate_limit_threshold']:
                self.logger.info(f"  ⚠ 首次触发限制阈值: {source_results['rate_limit_threshold']} 只股票")
            if source_results['response_times']:
                self.logger.info(f"  平均响应时间: {source_results['avg_response_time']:.2f}秒")
            
            pressure_test_results[source_name] = source_results
        
        return pressure_test_results
    
    def generate_pressure_test_report(self, results: Dict) -> Dict:
        """生成压力测试报告"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("压力测试报告总结")
        self.logger.info("=" * 80)
        
        for source_name, result in results.items():
            self.logger.info(f"\n{source_name}:")
            self.logger.info(f"  成功率: {result['success_count']}/{result['total_stocks']} ({result['success_rate']:.2%})")
            self.logger.info(f"  速率限制次数: {result['rate_limit_count']}")
            
            if result['rate_limit_threshold']:
                self.logger.info(f"  ⚠ 限制阈值: 约 {result['rate_limit_threshold']} 只股票后开始触发限制")
                self.logger.info(f"  建议: 每批次处理不超过 {result['rate_limit_threshold']} 只股票，或增加延迟时间")
            else:
                if result['rate_limit_count'] == 0:
                    self.logger.info(f"  ✓ 未检测到速率限制，接口稳定")
                else:
                    self.logger.info(f"  ⚠ 检测到速率限制，但未记录首次触发阈值")
            
            if result['response_times']:
                self.logger.info(f"  平均响应时间: {result['avg_response_time']:.2f}秒")
                self.logger.info(f"  预计全量获取时间: {result['avg_response_time'] * result['total_stocks'] / 60:.1f} 分钟")
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='股票数据源综合测试脚本')
    parser.add_argument('--symbols', type=str, nargs='+', 
                       default=['000001', '600519', '000002', '600036', '000858'],
                       help='测试股票代码列表（默认：000001, 600519, 000002, 600036, 000858）')
    parser.add_argument('--all-stocks', action='store_true',
                       help='获取全部股票进行测试（综合测试模式，会获取所有A股股票）')
    parser.add_argument('--start-date', type=str, default='2026-01-16',
                       help='开始日期（格式：YYYY-MM-DD，默认2026-01-16）')
    parser.add_argument('--end-date', type=str, default=None,
                       help='结束日期（格式：YYYY-MM-DD，默认今天）')
    parser.add_argument('--stability-test', action='store_true',
                       help='运行稳定性测试（多次调用，统计成功率）')
    parser.add_argument('--pressure-test', action='store_true',
                       help='运行压力测试（全量获取股票信息，检测API限制）')
    parser.add_argument('--iterations', type=int, default=10,
                       help='稳定性测试迭代次数（默认10次）')
    parser.add_argument('--max-stocks', type=int, default=None,
                       help='压力测试或全量测试最大股票数量（默认：全量，约5000+只）')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='批次大小（综合测试和压力测试，默认50只股票/批次）')
    parser.add_argument('--batch-delay', type=float, default=5.0,
                       help='批次间延迟（秒，默认5.0秒）')
    parser.add_argument('--stock-delay', type=float, default=1.0,
                       help='股票间延迟（秒，默认1.0秒，用于综合测试）')
    parser.add_argument('--output', type=str, default=None,
                       help='输出报告文件路径（JSON格式）')
    
    args = parser.parse_args()
    
    if args.end_date is None:
        args.end_date = datetime.now().strftime('%Y-%m-%d')
    
    tester = DataSourceTester()
    
    if args.pressure_test:
        # 压力测试
        logger.info("运行压力测试模式...")
        results = tester.run_pressure_test(
            start_date=args.start_date,
            end_date=args.end_date,
            max_stocks=args.max_stocks,
            batch_size=args.batch_size,
            delay_between_batches=args.batch_delay
        )
        
        # 生成报告
        report = tester.generate_pressure_test_report(results)
        
        # 保存报告
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_config': {
                        'test_type': 'pressure_test',
                        'start_date': args.start_date,
                        'end_date': args.end_date,
                        'max_stocks': args.max_stocks,
                        'batch_size': args.batch_size,
                        'batch_delay': args.batch_delay
                    },
                    'results': results,
                    'report': report
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"\n报告已保存到: {args.output}")
    
    elif args.stability_test:
        # 稳定性测试
        logger.info("运行稳定性测试模式...")
        for symbol in args.symbols[:1]:  # 稳定性测试只测试第一只股票
            results = tester.run_stability_test(
                symbol=symbol,
                start_date=args.start_date,
                end_date=args.end_date,
                iterations=args.iterations
            )
    else:
        # 综合测试
        symbols = args.symbols
        
        # 如果指定了 --all-stocks，获取全部股票列表
        if args.all_stocks:
            logger.info("运行综合测试模式（全量股票）...")
            try:
                from data_source.stock_data_source import StockDataSource
                data_source = StockDataSource()
                logger.info("正在获取全量股票列表...")
                all_stocks = data_source.get_all_stock_list(limit=args.max_stocks, sort_by_turnover=False, use_cache=True)
                symbols = [s.get('symbol') for s in all_stocks if s.get('symbol')]
                logger.info(f"成功获取 {len(symbols)} 只股票")
            except Exception as e:
                logger.error(f"获取股票列表失败: {str(e)}")
                logger.info("使用默认股票列表继续测试...")
                symbols = args.symbols
        else:
            logger.info("运行综合测试模式...")
        
        results = tester.run_comprehensive_test(
            symbols=symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            batch_size=args.batch_size,
            delay_between_stocks=args.stock_delay,
            delay_between_batches=args.batch_delay
        )
        
        # 生成报告
        report = tester.generate_report(results)
        
        # 保存报告
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_config': {
                        'symbols': args.symbols,
                        'start_date': args.start_date,
                        'end_date': args.end_date
                    },
                    'results': results,
                    'report': report
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"\n报告已保存到: {args.output}")
    
    logger.info("\n测试完成！")


if __name__ == '__main__':
    main()
