#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
其他数据获取任务测试脚本

测试6种数据类型的数据获取接口：
1. 北向资金 (north_bound_capital)
2. 市场指数 (market_index)
3. 融资融券 (margin_trading)
4. 主力资金 (main_force_capital)
5. 股票行业信息 (stock_industry_info)
6. 板块轮动 (sector_rotation)

测试顺序：akshare -> tushare -> 其他接口
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import traceback

# 设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

# 禁用代理（避免代理连接错误）
def disable_proxy():
    """临时禁用代理设置（改进版）"""
    import requests
    proxy_env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                      'NO_PROXY', 'no_proxy', 'ALL_PROXY', 'all_proxy']
    original_proxy = {}
    
    # 保存原始代理环境变量
    for var in proxy_env_vars:
        original_proxy[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    # 设置NO_PROXY为*，禁用所有代理
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    # 保存并清除requests库的代理设置
    original_requests_proxies = {}
    if hasattr(requests, 'proxies'):
        original_requests_proxies = getattr(requests, 'proxies', {})
        requests.proxies = {}
    
    # 尝试清除akshare内部session的代理设置
    original_akshare_session_proxies = None
    try:
        if AKSHARE_AVAILABLE:
            import akshare as ak
            if hasattr(ak, 'tool') and hasattr(ak.tool, 'session'):
                if hasattr(ak.tool.session, 'proxies'):
                    original_akshare_session_proxies = ak.tool.session.proxies
                    ak.tool.session.proxies = {}
    except:
        pass
    
    return {
        'env': original_proxy,
        'requests': original_requests_proxies,
        'akshare_session': original_akshare_session_proxies
    }

def restore_proxy(original_proxy):
    """恢复代理设置"""
    if not isinstance(original_proxy, dict):
        return
    
    # 恢复环境变量
    if 'env' in original_proxy:
        for var, value in original_proxy['env'].items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    # 恢复requests库的代理设置
    if 'requests' in original_proxy:
        try:
            import requests
            requests.proxies = original_proxy['requests']
        except:
            pass
    
    # 恢复akshare session的代理设置
    if 'akshare_session' in original_proxy and original_proxy['akshare_session'] is not None:
        try:
            if AKSHARE_AVAILABLE:
                import akshare as ak
                if hasattr(ak, 'tool') and hasattr(ak.tool, 'session'):
                    if hasattr(ak.tool.session, 'proxies'):
                        ak.tool.session.proxies = original_proxy['akshare_session']
        except:
            pass

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: akshare未安装")

# 导入tushare
try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
    pro = None
    # 初始化tushare（需要token）
    try:
        # 添加项目根目录到路径，确保能导入config
        import sys
        import os
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from config import TUSHARE_TOKEN
        if TUSHARE_TOKEN and TUSHARE_TOKEN.strip():
            # 设置token，避免文件权限问题
            try:
                # 方法1: 先设置环境变量，然后设置token
                os.environ['TUSHARE_TOKEN'] = TUSHARE_TOKEN
                ts.set_token(TUSHARE_TOKEN)
                pro = ts.pro_api()
                print(f"Tushare初始化成功，token已配置")
            except (PermissionError, OSError) as pe:
                # 如果文件权限问题，尝试使用临时目录
                print(f"警告: Tushare文件权限问题，尝试使用临时目录: {str(pe)}")
                try:
                    import tempfile
                    # 设置Tushare使用临时目录保存token文件
                    temp_dir = tempfile.gettempdir()
                    # 尝试在临时目录创建token文件
                    token_file = os.path.join(temp_dir, 'tushare_token.txt')
                    try:
                        with open(token_file, 'w') as f:
                            f.write(TUSHARE_TOKEN)
                        # 设置环境变量指向临时目录
                        os.environ['TUSHARE_TOKEN'] = TUSHARE_TOKEN
                        ts.set_token(TUSHARE_TOKEN)
                        pro = ts.pro_api()
                        print(f"Tushare初始化成功（使用临时目录）")
                    except Exception as e3:
                        # 如果临时目录也不行，直接使用环境变量
                        print(f"警告: 临时目录方式失败，尝试直接使用环境变量: {str(e3)}")
                        os.environ['TUSHARE_TOKEN'] = TUSHARE_TOKEN
                        # 不调用set_token，直接使用pro_api（如果支持从环境变量读取）
                        try:
                            pro = ts.pro_api()
                            print(f"Tushare初始化成功（使用环境变量）")
                        except:
                            # 最后尝试：手动设置token到tushare内部
                            if hasattr(ts, 'set_token'):
                                ts.set_token(TUSHARE_TOKEN)
                            pro = ts.pro_api()
                            print(f"Tushare初始化成功（手动设置）")
                except Exception as e2:
                    print(f"警告: Tushare初始化失败: {str(e2)}")
                    TUSHARE_AVAILABLE = False
                    pro = None
            except Exception as e:
                # 其他异常
                print(f"警告: Tushare初始化失败: {str(e)}")
                # 尝试最后一次：直接使用环境变量
                try:
                    os.environ['TUSHARE_TOKEN'] = TUSHARE_TOKEN
                    pro = ts.pro_api()
                    print(f"Tushare初始化成功（最后尝试）")
                except:
                    TUSHARE_AVAILABLE = False
                    pro = None
        else:
            print("警告: TUSHARE_TOKEN未配置或为空")
            TUSHARE_AVAILABLE = False
    except ImportError as e:
        print(f"警告: 无法导入config模块: {str(e)}")
        TUSHARE_AVAILABLE = False
        pro = None
    except Exception as e:
        print(f"警告: Tushare初始化失败: {str(e)}")
        TUSHARE_AVAILABLE = False
        pro = None
except ImportError:
    TUSHARE_AVAILABLE = False
    pro = None
    print("警告: tushare未安装")

# 导入日志
try:
    from utils.logger import get_logger
    logger = get_logger(__name__)
except:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class OtherDataCollectionTester:
    """其他数据获取任务测试类"""
    
    def __init__(self):
        self.test_results = {}
        self.test_symbol = "600519"  # 测试股票代码（贵州茅台）
        self.test_index_code = "sh000001"  # 测试指数代码（上证指数）
    
    def test_north_bound_capital(self):
        """测试北向资金数据获取"""
        print("\n" + "="*60)
        print("测试1: 北向资金数据获取")
        print("="*60)
        
        result = {
            'data_type': 'north_bound_capital',
            'akshare': {'success': False, 'data': None, 'error': None},
            'tushare': {'success': False, 'data': None, 'error': None},
            'other': {'success': False, 'data': None, 'error': None}
        }
        
        # 1. 测试akshare接口
        print("\n[1.1] 测试 AkShare 接口...")
        if AKSHARE_AVAILABLE:
            # 禁用代理以避免连接错误
            original_proxy = disable_proxy()
            try:
                # 方法1: 尝试多种akshare方法
                try:
                    north_data = None
                    # 尝试方法1: stock_connect_north_flow_em
                    try:
                        if hasattr(ak, 'stock_connect_north_flow_em'):
                            north_data = ak.stock_connect_north_flow_em(indicator="北向资金")
                    except AttributeError:
                        pass
                    except Exception as e:
                        print(f"    方法1调用失败: {str(e)}")
                    
                    # 如果方法1失败，尝试方法2: stock_connect_north_sina
                    if north_data is None or (hasattr(north_data, 'empty') and north_data.empty):
                        try:
                            if hasattr(ak, 'stock_connect_north_sina'):
                                north_data = ak.stock_connect_north_sina()
                        except AttributeError:
                            pass
                        except Exception as e:
                            print(f"    方法2调用失败: {str(e)}")
                    
                    # 如果都失败，尝试其他方法
                    if north_data is None:
                        # 尝试方法3: tool_trade_date_hist_sina（可能包含北向资金数据）
                        try:
                            if hasattr(ak, 'tool_trade_date_hist_sina'):
                                # 这个方法可能不直接返回北向资金，但可以作为最后尝试
                                pass
                        except:
                            pass
                        
                        if north_data is None:
                            raise AttributeError("未找到可用的AkShare北向资金接口")
                    
                    if not north_data.empty:
                        print(f"  [OK] AkShare方法1成功: 获取到 {len(north_data)} 条数据")
                        print(f"    数据列: {list(north_data.columns)}")
                        print(f"    最新数据: {north_data.iloc[-1].to_dict()}")
                        result['akshare'] = {'success': True, 'data': north_data, 'error': None, 'method': 'stock_connect_north_flow_em'}
                    else:
                        print("  [FAIL] AkShare方法1失败: 返回空数据")
                except Exception as e:
                    print(f"  [FAIL] AkShare方法1失败: {str(e)}")
                    result['akshare']['error'] = str(e)
                
                # 方法2: stock_connect_north_sina
                if not result['akshare']['success']:
                    try:
                        north_data = ak.stock_connect_north_sina()
                        if not north_data.empty:
                            print(f"  [OK] AkShare方法2成功: 获取到 {len(north_data)} 条数据")
                            print(f"    数据列: {list(north_data.columns)}")
                            print(f"    最新数据: {north_data.iloc[-1].to_dict()}")
                            result['akshare'] = {'success': True, 'data': north_data, 'error': None, 'method': 'stock_connect_north_sina'}
                        else:
                            print("  [FAIL] AkShare方法2失败: 返回空数据")
                    except Exception as e:
                        print(f"  [FAIL] AkShare方法2失败: {str(e)}")
                        if not result['akshare']['error']:
                            result['akshare']['error'] = str(e)
            except Exception as e:
                print(f"  [FAIL] AkShare测试失败: {str(e)}")
                result['akshare']['error'] = str(e)
        else:
            print("  [FAIL] AkShare不可用")
            result['akshare']['error'] = 'AkShare未安装'
        
        # 2. 测试tushare接口
        print("\n[1.2] 测试 Tushare 接口...")
        if TUSHARE_AVAILABLE and pro:
            try:
                # Tushare可能没有直接的北向资金接口，尝试其他方法
                # 注意：Tushare的北向资金接口可能需要付费权限
                try:
                    # 尝试使用moneyflow_hsgt（沪深港通资金流向）
                    today = datetime.now().strftime('%Y%m%d')
                    # 获取最近5天的数据
                    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                    north_data = pro.moneyflow_hsgt(start_date=start_date, end_date=today)
                    if not north_data.empty:
                        print(f"  [OK] Tushare成功: 获取到 {len(north_data)} 条数据")
                        print(f"    数据列: {list(north_data.columns)}")
                        print(f"    最新数据: {north_data.iloc[-1].to_dict()}")
                        result['tushare'] = {'success': True, 'data': north_data, 'error': None, 'method': 'moneyflow_hsgt'}
                    else:
                        print("  [FAIL] Tushare失败: 返回空数据")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [FAIL] Tushare失败: {error_msg}")
                    # 检查是否是权限问题
                    if '权限' in error_msg or 'permission' in error_msg.lower() or '访问' in error_msg:
                        print(f"    [提示] 该接口需要付费权限，建议使用AkShare接口")
                        result['tushare']['error'] = error_msg
                        result['tushare']['permission_required'] = True
                    elif '每天最多访问' in error_msg or '访问次数' in error_msg:
                        print(f"    [提示] 免费用户访问频率受限，建议控制访问频率或升级权限")
                        result['tushare']['error'] = error_msg
                        result['tushare']['rate_limited'] = True
                    else:
                        result['tushare']['error'] = error_msg
            except Exception as e:
                print(f"  [FAIL] Tushare测试失败: {str(e)}")
                result['tushare']['error'] = str(e)
        else:
            print("  [FAIL] Tushare不可用")
            result['tushare']['error'] = 'Tushare未安装或未配置token'
        
        # 3. 测试其他接口（如果有）
        print("\n[1.3] 测试其他接口...")
        # 可以在这里添加其他数据源的测试
        print("  - 暂无其他接口")
        
        self.test_results['north_bound_capital'] = result
        return result
    
    def test_market_index(self):
        """测试市场指数数据获取"""
        print("\n" + "="*60)
        print("测试2: 市场指数数据获取")
        print("="*60)
        
        result = {
            'data_type': 'market_index',
            'akshare': {'success': False, 'data': None, 'error': None},
            'tushare': {'success': False, 'data': None, 'error': None},
            'other': {'success': False, 'data': None, 'error': None}
        }
        
        index_code = self.test_index_code
        index_symbol = index_code.replace('sh', '').replace('sz', '')
        
        # 1. 测试akshare接口
        print(f"\n[2.1] 测试 AkShare 接口 (指数代码: {index_code})...")
        if AKSHARE_AVAILABLE:
            original_proxy = disable_proxy()
            try:
                # 方法1: index_zh_a_hist
                try:
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                    index_data = ak.index_zh_a_hist(symbol=index_symbol, period="日k", 
                                                   start_date=start_date, end_date=end_date)
                    if not index_data.empty:
                        print(f"  [OK] AkShare方法1成功: 获取到 {len(index_data)} 条数据")
                        print(f"    数据列: {list(index_data.columns)}")
                        print(f"    最新数据: {index_data.iloc[-1].to_dict()}")
                        result['akshare'] = {'success': True, 'data': index_data, 'error': None, 'method': 'index_zh_a_hist'}
                    else:
                        print("  [FAIL] AkShare方法1失败: 返回空数据")
                except Exception as e:
                    print(f"  [FAIL] AkShare方法1失败: {str(e)}")
                    result['akshare']['error'] = str(e)
                
                # 方法2: stock_zh_index_daily
                if not result['akshare']['success']:
                    try:
                        index_data = ak.stock_zh_index_daily(symbol=index_code)
                        if not index_data.empty:
                            print(f"  [OK] AkShare方法2成功: 获取到 {len(index_data)} 条数据")
                            print(f"    数据列: {list(index_data.columns)}")
                            print(f"    最新数据: {index_data.iloc[-1].to_dict()}")
                            result['akshare'] = {'success': True, 'data': index_data, 'error': None, 'method': 'stock_zh_index_daily'}
                        else:
                            print("  [FAIL] AkShare方法2失败: 返回空数据")
                    except Exception as e:
                        print(f"  [FAIL] AkShare方法2失败: {str(e)}")
                        if not result['akshare']['error']:
                            result['akshare']['error'] = str(e)
            except Exception as e:
                print(f"  [FAIL] AkShare测试失败: {str(e)}")
                result['akshare']['error'] = str(e)
            finally:
                restore_proxy(original_proxy)
        else:
            print("  [FAIL] AkShare不可用")
            result['akshare']['error'] = 'AkShare未安装'
        
        # 2. 测试tushare接口
        print(f"\n[2.2] 测试 Tushare 接口 (指数代码: {index_code})...")
        if TUSHARE_AVAILABLE and pro:
            try:
                # Tushare使用index_daily接口
                try:
                    # Tushare的指数代码格式：000001.SH
                    tushare_code = f"{index_symbol}.SH" if index_code.startswith('sh') else f"{index_symbol}.SZ"
                    today = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                    index_data = pro.index_daily(ts_code=tushare_code, start_date=start_date, end_date=today)
                    if not index_data.empty:
                        print(f"  [OK] Tushare成功: 获取到 {len(index_data)} 条数据")
                        print(f"    数据列: {list(index_data.columns)}")
                        print(f"    最新数据: {index_data.iloc[-1].to_dict()}")
                        result['tushare'] = {'success': True, 'data': index_data, 'error': None, 'method': 'index_daily'}
                    else:
                        print("  [FAIL] Tushare失败: 返回空数据")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [FAIL] Tushare失败: {error_msg}")
                    # 检查是否是权限问题
                    if '权限' in error_msg or 'permission' in error_msg.lower() or '访问' in error_msg:
                        print(f"    [提示] 该接口需要付费权限，建议使用AkShare接口")
                        result['tushare']['error'] = error_msg
                        result['tushare']['permission_required'] = True
                    elif '每天最多访问' in error_msg or '访问次数' in error_msg:
                        print(f"    [提示] 免费用户访问频率受限，建议控制访问频率或升级权限")
                        result['tushare']['error'] = error_msg
                        result['tushare']['rate_limited'] = True
                    else:
                        result['tushare']['error'] = error_msg
            except Exception as e:
                print(f"  [FAIL] Tushare测试失败: {str(e)}")
                result['tushare']['error'] = str(e)
        else:
            print("  [FAIL] Tushare不可用")
            result['tushare']['error'] = 'Tushare未安装或未配置token'
        
        # 3. 测试其他接口
        print("\n[2.3] 测试其他接口...")
        print("  - 暂无其他接口")
        
        self.test_results['market_index'] = result
        return result
    
    def test_margin_trading(self):
        """测试融资融券数据获取"""
        print("\n" + "="*60)
        print("测试3: 融资融券数据获取")
        print("="*60)
        
        result = {
            'data_type': 'margin_trading',
            'akshare': {'success': False, 'data': None, 'error': None},
            'tushare': {'success': False, 'data': None, 'error': None},
            'other': {'success': False, 'data': None, 'error': None}
        }
        
        symbol = self.test_symbol
        
        # 1. 测试akshare接口
        print(f"\n[3.1] 测试 AkShare 接口 (股票代码: {symbol})...")
        if AKSHARE_AVAILABLE:
            original_proxy = disable_proxy()
            try:
                # 判断是上交所还是深交所
                if symbol.startswith('6'):
                    # 上交所股票
                    try:
                        # 检查方法是否存在，如果不存在尝试其他方法
                        if hasattr(ak, 'stock_margin_underlying_info_sse'):
                            margin_data = ak.stock_margin_underlying_info_sse(symbol=symbol)
                        elif hasattr(ak, 'stock_margin_sse'):
                            # 尝试替代方法（注意：stock_margin_sse可能不接受symbol参数）
                            try:
                                # 先尝试不带参数
                                margin_data = ak.stock_margin_sse()
                                # 如果返回所有股票数据，需要筛选
                                if not margin_data.empty and '代码' in margin_data.columns:
                                    margin_data = margin_data[margin_data['代码'].astype(str).str.contains(symbol)]
                            except TypeError:
                                # 如果必须带参数，尝试其他参数名
                                try:
                                    margin_data = ak.stock_margin_sse(date=datetime.now().strftime('%Y%m%d'))
                                except:
                                    raise AttributeError("stock_margin_sse参数不正确")
                        else:
                            raise AttributeError("stock_margin_underlying_info_sse方法不存在，且未找到替代方法")
                        if not margin_data.empty:
                            print(f"  [OK] AkShare成功(上交所): 获取到 {len(margin_data)} 条数据")
                            print(f"    数据列: {list(margin_data.columns)}")
                            print(f"    最新数据: {margin_data.iloc[-1].to_dict()}")
                            result['akshare'] = {'success': True, 'data': margin_data, 'error': None, 'method': 'stock_margin_underlying_info_sse'}
                        else:
                            print("  [FAIL] AkShare失败: 返回空数据")
                    except Exception as e:
                        print(f"  [FAIL] AkShare失败(上交所): {str(e)}")
                        result['akshare']['error'] = str(e)
                else:
                    # 深交所股票
                    try:
                        # 检查方法是否存在，如果不存在尝试其他方法
                        if hasattr(ak, 'stock_margin_underlying_info_szse'):
                            margin_data = ak.stock_margin_underlying_info_szse(symbol=symbol)
                        elif hasattr(ak, 'stock_margin_szse'):
                            # 尝试替代方法（注意：stock_margin_szse可能不接受symbol参数）
                            try:
                                # 先尝试不带参数
                                margin_data = ak.stock_margin_szse()
                                # 如果返回所有股票数据，需要筛选
                                if not margin_data.empty and '代码' in margin_data.columns:
                                    margin_data = margin_data[margin_data['代码'].astype(str).str.contains(symbol)]
                            except TypeError:
                                # 如果必须带参数，尝试其他参数名
                                try:
                                    margin_data = ak.stock_margin_szse(date=datetime.now().strftime('%Y%m%d'))
                                except:
                                    raise AttributeError("stock_margin_szse参数不正确")
                        else:
                            raise AttributeError("stock_margin_underlying_info_szse方法不存在，且未找到替代方法")
                        if not margin_data.empty:
                            print(f"  [OK] AkShare成功(深交所): 获取到 {len(margin_data)} 条数据")
                            print(f"    数据列: {list(margin_data.columns)}")
                            print(f"    最新数据: {margin_data.iloc[-1].to_dict()}")
                            result['akshare'] = {'success': True, 'data': margin_data, 'error': None, 'method': 'stock_margin_underlying_info_szse'}
                        else:
                            print("  [FAIL] AkShare失败: 返回空数据")
                    except Exception as e:
                        print(f"  [FAIL] AkShare失败(深交所): {str(e)}")
                        result['akshare']['error'] = str(e)
            except Exception as e:
                print(f"  [FAIL] AkShare测试失败: {str(e)}")
                result['akshare']['error'] = str(e)
            finally:
                restore_proxy(original_proxy)
        else:
            print("  [FAIL] AkShare不可用")
            result['akshare']['error'] = 'AkShare未安装'
        
        # 2. 测试tushare接口
        print(f"\n[3.2] 测试 Tushare 接口 (股票代码: {symbol})...")
        if TUSHARE_AVAILABLE and pro:
            try:
                # Tushare使用margin接口
                try:
                    # Tushare的股票代码格式：600519.SH
                    tushare_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                    today = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                    margin_data = pro.margin(ts_code=tushare_code, start_date=start_date, end_date=today)
                    if not margin_data.empty:
                        print(f"  [OK] Tushare成功: 获取到 {len(margin_data)} 条数据")
                        print(f"    数据列: {list(margin_data.columns)}")
                        print(f"    最新数据: {margin_data.iloc[-1].to_dict()}")
                        result['tushare'] = {'success': True, 'data': margin_data, 'error': None, 'method': 'margin'}
                    else:
                        print("  [FAIL] Tushare失败: 返回空数据")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [FAIL] Tushare失败: {error_msg}")
                    # 检查是否是权限问题
                    if '权限' in error_msg or 'permission' in error_msg.lower() or '访问' in error_msg:
                        print(f"    [提示] 该接口需要付费权限，建议使用AkShare接口")
                        result['tushare']['error'] = error_msg
                        result['tushare']['permission_required'] = True
                    elif '每天最多访问' in error_msg or '访问次数' in error_msg:
                        print(f"    [提示] 免费用户访问频率受限，建议控制访问频率或升级权限")
                        result['tushare']['error'] = error_msg
                        result['tushare']['rate_limited'] = True
                    else:
                        result['tushare']['error'] = error_msg
            except Exception as e:
                print(f"  [FAIL] Tushare测试失败: {str(e)}")
                result['tushare']['error'] = str(e)
        else:
            print("  [FAIL] Tushare不可用")
            result['tushare']['error'] = 'Tushare未安装或未配置token'
        
        # 3. 测试其他接口
        print("\n[3.3] 测试其他接口...")
        print("  - 暂无其他接口")
        
        self.test_results['margin_trading'] = result
        return result
    
    def test_main_force_capital(self):
        """测试主力资金数据获取"""
        print("\n" + "="*60)
        print("测试4: 主力资金数据获取")
        print("="*60)
        
        result = {
            'data_type': 'main_force_capital',
            'akshare': {'success': False, 'data': None, 'error': None},
            'tushare': {'success': False, 'data': None, 'error': None},
            'other': {'success': False, 'data': None, 'error': None}
        }
        
        symbol = self.test_symbol
        
        # 1. 测试akshare接口
        print(f"\n[4.1] 测试 AkShare 接口 (股票代码: {symbol})...")
        if AKSHARE_AVAILABLE:
            original_proxy = disable_proxy()
            try:
                # 方法1: stock_individual_fund_flow
                try:
                    market = "sh" if symbol.startswith('6') else "sz"
                    capital_flow = ak.stock_individual_fund_flow(stock=symbol, market=market)
                    if not capital_flow.empty:
                        print(f"  [OK] AkShare方法1成功: 获取到 {len(capital_flow)} 条数据")
                        print(f"    数据列: {list(capital_flow.columns)}")
                        print(f"    最新数据: {capital_flow.iloc[-1].to_dict()}")
                        result['akshare'] = {'success': True, 'data': capital_flow, 'error': None, 'method': 'stock_individual_fund_flow'}
                    else:
                        print("  [FAIL] AkShare方法1失败: 返回空数据")
                except Exception as e:
                    print(f"  [FAIL] AkShare方法1失败: {str(e)}")
                    result['akshare']['error'] = str(e)
                
                # 方法2: stock_individual_fund_flow_rank
                if not result['akshare']['success']:
                    try:
                        capital_flow = ak.stock_individual_fund_flow_rank(indicator="今日")
                        if not capital_flow.empty:
                            # 查找该股票的数据
                            code_col = None
                            for col in capital_flow.columns:
                                if '代码' in str(col) or 'code' in str(col).lower():
                                    code_col = col
                                    break
                            if code_col:
                                row = capital_flow[capital_flow[code_col].astype(str).str.contains(symbol)]
                                if not row.empty:
                                    print(f"  [OK] AkShare方法2成功: 找到股票数据")
                                    print(f"    数据列: {list(capital_flow.columns)}")
                                    print(f"    股票数据: {row.iloc[0].to_dict()}")
                                    result['akshare'] = {'success': True, 'data': row, 'error': None, 'method': 'stock_individual_fund_flow_rank'}
                                else:
                                    print("  [FAIL] AkShare方法2失败: 未找到该股票数据")
                            else:
                                print("  [FAIL] AkShare方法2失败: 未找到代码列")
                        else:
                            print("  [FAIL] AkShare方法2失败: 返回空数据")
                    except Exception as e:
                        print(f"  [FAIL] AkShare方法2失败: {str(e)}")
                        if not result['akshare']['error']:
                            result['akshare']['error'] = str(e)
            except Exception as e:
                print(f"  [FAIL] AkShare测试失败: {str(e)}")
                result['akshare']['error'] = str(e)
            finally:
                restore_proxy(original_proxy)
        else:
            print("  [FAIL] AkShare不可用")
            result['akshare']['error'] = 'AkShare未安装'
        
        # 2. 测试tushare接口
        print(f"\n[4.2] 测试 Tushare 接口 (股票代码: {symbol})...")
        if TUSHARE_AVAILABLE and pro:
            try:
                # Tushare可能没有直接的主力资金接口，尝试moneyflow接口
                try:
                    tushare_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                    today = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                    moneyflow_data = pro.moneyflow(ts_code=tushare_code, start_date=start_date, end_date=today)
                    if not moneyflow_data.empty:
                        print(f"  [OK] Tushare成功: 获取到 {len(moneyflow_data)} 条数据")
                        print(f"    数据列: {list(moneyflow_data.columns)}")
                        print(f"    最新数据: {moneyflow_data.iloc[-1].to_dict()}")
                        result['tushare'] = {'success': True, 'data': moneyflow_data, 'error': None, 'method': 'moneyflow'}
                    else:
                        print("  [FAIL] Tushare失败: 返回空数据")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [FAIL] Tushare失败: {error_msg}")
                    # 检查是否是权限问题
                    if '权限' in error_msg or 'permission' in error_msg.lower() or '访问' in error_msg:
                        print(f"    [提示] 该接口需要付费权限，建议使用AkShare接口")
                        result['tushare']['error'] = error_msg
                        result['tushare']['permission_required'] = True
                    elif '每天最多访问' in error_msg or '访问次数' in error_msg:
                        print(f"    [提示] 免费用户访问频率受限，建议控制访问频率或升级权限")
                        result['tushare']['error'] = error_msg
                        result['tushare']['rate_limited'] = True
                    else:
                        result['tushare']['error'] = error_msg
            except Exception as e:
                print(f"  [FAIL] Tushare测试失败: {str(e)}")
                result['tushare']['error'] = str(e)
        else:
            print("  [FAIL] Tushare不可用")
            result['tushare']['error'] = 'Tushare未安装或未配置token'
        
        # 3. 测试其他接口
        print("\n[4.3] 测试其他接口...")
        print("  - 暂无其他接口")
        
        self.test_results['main_force_capital'] = result
        return result
    
    def test_stock_industry_info(self):
        """测试股票行业信息数据获取"""
        print("\n" + "="*60)
        print("测试5: 股票行业信息数据获取")
        print("="*60)
        
        result = {
            'data_type': 'stock_industry_info',
            'akshare': {'success': False, 'data': None, 'error': None},
            'tushare': {'success': False, 'data': None, 'error': None},
            'other': {'success': False, 'data': None, 'error': None}
        }
        
        symbol = self.test_symbol
        
        # 1. 测试akshare接口
        print(f"\n[5.1] 测试 AkShare 接口 (股票代码: {symbol})...")
        if AKSHARE_AVAILABLE:
            original_proxy = disable_proxy()
            try:
                # 方法1: stock_individual_info_em
                try:
                    # 检查方法是否存在
                    if hasattr(ak, 'stock_individual_info_em'):
                        stock_info = ak.stock_individual_info_em(symbol=symbol)
                    elif hasattr(ak, 'stock_individual_info'):
                        # 尝试替代方法
                        stock_info = ak.stock_individual_info(symbol=symbol)
                    else:
                        raise AttributeError("stock_individual_info_em方法不存在，且未找到替代方法")
                    
                    if not stock_info.empty:
                        method_name = 'stock_individual_info_em' if hasattr(ak, 'stock_individual_info_em') else 'stock_individual_info'
                        print(f"  [OK] AkShare方法1成功: 获取到 {len(stock_info)} 条数据")
                        print(f"    数据列: {list(stock_info.columns)}")
                        # 查找行业和概念信息
                        industry_info = {}
                        for _, row in stock_info.iterrows():
                            key = str(row.iloc[0]).strip()
                            value = str(row.iloc[1]).strip()
                            if '行业' in key or '概念' in key:
                                industry_info[key] = value
                        print(f"    行业/概念信息: {industry_info}")
                        result['akshare'] = {'success': True, 'data': stock_info, 'error': None, 'method': method_name}
                    else:
                        print("  [FAIL] AkShare方法1失败: 返回空数据")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [FAIL] AkShare方法1失败: {error_msg}")
                    # 如果是代理错误，添加重试提示
                    if 'ProxyError' in error_msg or '代理' in error_msg:
                        print(f"    [提示] 代理连接错误，已尝试禁用代理，如仍失败请检查网络设置")
                    result['akshare']['error'] = error_msg
                
                # 方法2: stock_board_concept_name_em
                if result['akshare']['success']:
                    try:
                        concept_data = ak.stock_board_concept_name_em()
                        if not concept_data.empty:
                            print(f"  [OK] AkShare方法2成功: 获取到 {len(concept_data)} 个概念板块")
                            result['akshare']['concept_data'] = concept_data
                    except Exception as e:
                        print(f"  [FAIL] AkShare方法2失败: {str(e)}")
            except Exception as e:
                print(f"  [FAIL] AkShare测试失败: {str(e)}")
                result['akshare']['error'] = str(e)
            finally:
                restore_proxy(original_proxy)
        else:
            print("  [FAIL] AkShare不可用")
            result['akshare']['error'] = 'AkShare未安装'
        
        # 2. 测试tushare接口
        print(f"\n[5.2] 测试 Tushare 接口 (股票代码: {symbol})...")
        if TUSHARE_AVAILABLE and pro:
            try:
                # Tushare使用stock_basic接口获取股票基本信息
                try:
                    tushare_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                    stock_basic = pro.stock_basic(ts_code=tushare_code, fields='ts_code,symbol,name,area,industry,list_date')
                    if not stock_basic.empty:
                        print(f"  [OK] Tushare成功: 获取到股票基本信息")
                        print(f"    数据列: {list(stock_basic.columns)}")
                        print(f"    股票信息: {stock_basic.iloc[0].to_dict()}")
                        result['tushare'] = {'success': True, 'data': stock_basic, 'error': None, 'method': 'stock_basic'}
                    else:
                        print("  [FAIL] Tushare失败: 返回空数据")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [FAIL] Tushare失败: {error_msg}")
                    # 检查是否是权限问题
                    if '权限' in error_msg or 'permission' in error_msg.lower() or '访问' in error_msg:
                        print(f"    [提示] 该接口需要付费权限，建议使用AkShare接口")
                        result['tushare']['error'] = error_msg
                        result['tushare']['permission_required'] = True
                    elif '每天最多访问' in error_msg or '访问次数' in error_msg:
                        print(f"    [提示] 免费用户访问频率受限，建议控制访问频率或升级权限")
                        result['tushare']['error'] = error_msg
                        result['tushare']['rate_limited'] = True
                    else:
                        result['tushare']['error'] = error_msg
            except Exception as e:
                print(f"  [FAIL] Tushare测试失败: {str(e)}")
                result['tushare']['error'] = str(e)
        else:
            print("  [FAIL] Tushare不可用")
            result['tushare']['error'] = 'Tushare未安装或未配置token'
        
        # 3. 测试其他接口
        print("\n[5.3] 测试其他接口...")
        print("  - 暂无其他接口")
        
        self.test_results['stock_industry_info'] = result
        return result
    
    def test_sector_rotation(self):
        """测试板块轮动数据获取"""
        print("\n" + "="*60)
        print("测试6: 板块轮动数据获取")
        print("="*60)
        
        result = {
            'data_type': 'sector_rotation',
            'akshare': {'success': False, 'data': None, 'error': None},
            'tushare': {'success': False, 'data': None, 'error': None},
            'other': {'success': False, 'data': None, 'error': None}
        }
        
        # 1. 测试akshare接口
        print("\n[6.1] 测试 AkShare 接口...")
        if AKSHARE_AVAILABLE:
            original_proxy = disable_proxy()
            try:
                # 方法1: stock_board_industry_name_em
                try:
                    # 检查方法是否存在，如果不存在尝试其他方法
                    if hasattr(ak, 'stock_board_industry_name_em'):
                        industry_board = ak.stock_board_industry_name_em()
                    elif hasattr(ak, 'stock_board_industry_name'):
                        # 尝试替代方法
                        industry_board = ak.stock_board_industry_name()
                    else:
                        raise AttributeError("stock_board_industry_name_em方法不存在，且未找到替代方法")
                    
                    if not industry_board.empty:
                        method_name = 'stock_board_industry_name_em' if hasattr(ak, 'stock_board_industry_name_em') else 'stock_board_industry_name'
                        print(f"  [OK] AkShare方法1成功: 获取到 {len(industry_board)} 个行业板块")
                        print(f"    数据列: {list(industry_board.columns)}")
                        print(f"    前5个板块: {industry_board.head(5).to_dict('records')}")
                        result['akshare'] = {'success': True, 'data': industry_board, 'error': None, 'method': method_name}
                    else:
                        print("  [FAIL] AkShare方法1失败: 返回空数据")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [FAIL] AkShare方法1失败: {error_msg}")
                    # 如果是代理错误，添加重试提示
                    if 'ProxyError' in error_msg or '代理' in error_msg:
                        print(f"    [提示] 代理连接错误，已尝试禁用代理，如仍失败请检查网络设置")
                    result['akshare']['error'] = error_msg
                
                # 方法2: stock_board_concept_name_em
                if result['akshare']['success']:
                    try:
                        if not hasattr(ak, 'stock_board_concept_name_em'):
                            raise AttributeError("stock_board_concept_name_em方法不存在")
                        concept_board = ak.stock_board_concept_name_em()
                        if not concept_board.empty:
                            print(f"  [OK] AkShare方法2成功: 获取到 {len(concept_board)} 个概念板块")
                            result['akshare']['concept_data'] = concept_board
                    except Exception as e:
                        print(f"  [FAIL] AkShare方法2失败: {str(e)}")
            except Exception as e:
                print(f"  [FAIL] AkShare测试失败: {str(e)}")
                result['akshare']['error'] = str(e)
            finally:
                restore_proxy(original_proxy)
        else:
            print("  [FAIL] AkShare不可用")
            result['akshare']['error'] = 'AkShare未安装'
        
        # 2. 测试tushare接口
        print("\n[6.2] 测试 Tushare 接口...")
        if TUSHARE_AVAILABLE and pro:
            try:
                # Tushare可能没有直接的板块轮动接口，尝试其他方法
                try:
                    # 尝试使用index_classify接口获取行业分类
                    industry_classify = pro.index_classify(level='L1', src='SW2021')
                    if not industry_classify.empty:
                        print(f"  [OK] Tushare成功: 获取到 {len(industry_classify)} 个行业分类")
                        print(f"    数据列: {list(industry_classify.columns)}")
                        print(f"    前5个分类: {industry_classify.head(5).to_dict('records')}")
                        result['tushare'] = {'success': True, 'data': industry_classify, 'error': None, 'method': 'index_classify'}
                    else:
                        print("  [FAIL] Tushare失败: 返回空数据")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [FAIL] Tushare失败: {error_msg}")
                    # 检查是否是权限问题
                    if '权限' in error_msg or 'permission' in error_msg.lower() or '访问' in error_msg:
                        print(f"    [提示] 该接口需要付费权限，建议使用AkShare接口")
                        result['tushare']['error'] = error_msg
                        result['tushare']['permission_required'] = True
                    elif '每天最多访问' in error_msg or '访问次数' in error_msg:
                        print(f"    [提示] 免费用户访问频率受限，建议控制访问频率或升级权限")
                        result['tushare']['error'] = error_msg
                        result['tushare']['rate_limited'] = True
                    else:
                        result['tushare']['error'] = error_msg
            except Exception as e:
                print(f"  [FAIL] Tushare测试失败: {str(e)}")
                result['tushare']['error'] = str(e)
        else:
            print("  [FAIL] Tushare不可用")
            result['tushare']['error'] = 'Tushare未安装或未配置token'
        
        # 3. 测试其他接口
        print("\n[6.3] 测试其他接口...")
        print("  - 暂无其他接口")
        
        self.test_results['sector_rotation'] = result
        return result
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("开始测试其他数据获取任务的6种数据类型")
        print("="*60)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试股票代码: {self.test_symbol}")
        print(f"测试指数代码: {self.test_index_code}")
        
        # 运行所有测试
        self.test_north_bound_capital()
        self.test_market_index()
        self.test_margin_trading()
        self.test_main_force_capital()
        self.test_stock_industry_info()
        self.test_sector_rotation()
        
        # 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("测试报告汇总")
        print("="*60)
        
        report = []
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        data_type_names = {
            'north_bound_capital': '北向资金',
            'market_index': '市场指数',
            'margin_trading': '融资融券',
            'main_force_capital': '主力资金',
            'stock_industry_info': '股票行业信息',
            'sector_rotation': '板块轮动'
        }
        
        # 统计信息
        success_count = {'akshare': 0, 'tushare': 0, 'other': 0}
        fail_count = {'akshare': 0, 'tushare': 0, 'other': 0}
        
        for data_type, result in self.test_results.items():
            data_name = data_type_names.get(data_type, data_type)
            report.append(f"\n【{data_name}】")
            report.append("-" * 40)
            
            # AkShare测试结果
            if result['akshare']['success']:
                report.append(f"[OK] AkShare: 成功 (方法: {result['akshare'].get('method', 'unknown')})")
                success_count['akshare'] += 1
            else:
                report.append(f"[FAIL] AkShare: 失败")
                fail_count['akshare'] += 1
                if result['akshare']['error']:
                    error_msg = result['akshare']['error']
                    report.append(f"  错误: {error_msg}")
                    # 添加错误类型提示
                    if 'ProxyError' in error_msg or '代理' in error_msg:
                        report.append(f"  [提示] 代理连接错误，已尝试禁用代理，如仍失败请检查网络设置")
                    elif '方法不存在' in error_msg or 'has no attribute' in error_msg:
                        report.append(f"  [提示] API方法不存在，可能需要更新AkShare版本或查找替代方法")
            
            # Tushare测试结果
            if result['tushare']['success']:
                report.append(f"[OK] Tushare: 成功 (方法: {result['tushare'].get('method', 'unknown')})")
                success_count['tushare'] += 1
            else:
                report.append(f"[FAIL] Tushare: 失败")
                fail_count['tushare'] += 1
                if result['tushare']['error']:
                    error_msg = result['tushare']['error']
                    report.append(f"  错误: {error_msg}")
                    # 添加权限和频率限制提示
                    if result['tushare'].get('permission_required'):
                        report.append(f"  [提示] 该接口需要付费权限，建议使用AkShare接口")
                    elif result['tushare'].get('rate_limited'):
                        report.append(f"  [提示] 免费用户访问频率受限，建议控制访问频率或升级权限")
            
            # 其他接口测试结果
            if result['other']['success']:
                report.append(f"[OK] 其他接口: 成功")
                success_count['other'] += 1
            else:
                report.append(f"[FAIL] 其他接口: 未测试")
                fail_count['other'] += 1
            
            # 添加推荐方案
            report.append("")
            if result['akshare']['success'] and result['tushare']['success']:
                report.append(f"  [推荐] 优先使用AkShare（免费），Tushare作为备选")
            elif result['akshare']['success']:
                report.append(f"  [推荐] 使用AkShare接口")
            elif result['tushare']['success']:
                report.append(f"  [推荐] 使用Tushare接口")
            else:
                report.append(f"  [警告] 所有接口均失败，需要进一步排查问题")
        
        # 添加统计信息
        report.append("\n" + "="*60)
        report.append("统计信息")
        report.append("="*60)
        report.append(f"AkShare: 成功 {success_count['akshare']}/6, 失败 {fail_count['akshare']}/6")
        report.append(f"Tushare: 成功 {success_count['tushare']}/6, 失败 {fail_count['tushare']}/6")
        report.append(f"其他接口: 成功 {success_count['other']}/6, 失败 {fail_count['other']}/6")
        
        # 输出报告
        report_text = "\n".join(report)
        print(report_text)
        
        # 保存报告到文件
        report_file = os.path.join(project_root, 'reports', 'other_data_collection_test_report.txt')
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"\n测试报告已保存到: {report_file}")


if __name__ == '__main__':
    tester = OtherDataCollectionTester()
    tester.run_all_tests()
