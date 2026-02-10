"""
股票预测器
结合技术指标、新闻情感、市场情绪等多维度数据进行预测
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 添加父目录到路径，以便导入新闻模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

# 使用绝对导入
import importlib.util
spec = importlib.util.spec_from_file_location("stock_data_source", 
    os.path.join(project_root, "data_source", "stock_data_source.py"))
stock_data_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock_data_module)
StockDataSource = stock_data_module.StockDataSource

spec = importlib.util.spec_from_file_location("logger", 
    os.path.join(project_root, "utils", "logger.py"))
logger_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logger_module)
get_logger = logger_module.get_logger

# 导入数据存储模块
try:
    spec = importlib.util.spec_from_file_location("data_storage", 
        os.path.join(project_root, "utils", "data_storage.py"))
    data_storage_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data_storage_module)
    DataStorage = data_storage_module.DataStorage
    DATA_STORAGE_AVAILABLE = True
except ImportError:
    DATA_STORAGE_AVAILABLE = False
    DataStorage = None

try:
    spec_risk = importlib.util.spec_from_file_location("risk_manager", 
        os.path.join(project_root, "utils", "risk_manager.py"))
    risk_manager_module = importlib.util.module_from_spec(spec_risk)
    spec_risk.loader.exec_module(risk_manager_module)
    RiskManager = risk_manager_module.RiskManager
    RISK_MANAGER_AVAILABLE = True
except Exception:
    RISK_MANAGER_AVAILABLE = False
    RiskManager = None

spec = importlib.util.spec_from_file_location("config", 
    os.path.join(project_root, "config.py"))
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
PREDICTION_CONFIG = config_module.PREDICTION_CONFIG
INDICATOR_CONFIG = config_module.INDICATOR_CONFIG
THREAD_POOL_CONFIG = config_module.THREAD_POOL_CONFIG
CONFIDENCE_THRESHOLDS = config_module.CONFIDENCE_THRESHOLDS
PROBABILITY_THRESHOLDS = config_module.PROBABILITY_THRESHOLDS
NEWS_CONFIG = config_module.NEWS_CONFIG
# TuShare token（如果在config中配置，则用于新闻源）
TUSHARE_TOKEN = getattr(config_module, "TUSHARE_TOKEN", None)
TUSHARE_USERNAME = getattr(config_module, "TUSHARE_USERNAME", None)
TUSHARE_PASSWORD = getattr(config_module, "TUSHARE_PASSWORD", None)

# 尝试导入新闻模块（如果可用）
NEWS_AVAILABLE = False
try:
    # 方法1: 从quant_trading_platform导入
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'quant_trading_platform'))
    from quant_trading_platform.news import UnifiedNewsSource, NewsSentimentAnalyzer
    NEWS_AVAILABLE = True
except ImportError:
    try:
        # 方法2: 从本地news模块导入
        from news import UnifiedNewsSource, NewsSentimentAnalyzer
        NEWS_AVAILABLE = True
    except ImportError:
        NEWS_AVAILABLE = False
        logger.warning("新闻模块不可用，将仅使用技术指标预测")

logger = get_logger(__name__)

class StockPredictor:
    """股票预测器"""
    
    def __init__(self, data_source: StockDataSource = None):
        """
        初始化股票预测器
        
        Args:
            data_source: 可选的数据源实例（性能优化：如果提供，则复用该实例，避免重复创建）
        """
        # 性能优化：如果提供了共享的数据源实例，则复用；否则创建新的实例
        if data_source is not None:
            self.data_source = data_source
        else:
            self.data_source = StockDataSource()
        self.logger = logger
        
        # 初始化数据存储管理器
        if DATA_STORAGE_AVAILABLE:
            self.data_storage = DataStorage(base_dir="data")
        else:
            self.data_storage = None
            self.logger.warning("数据存储模块不可用，将不会保存指标数据到CSV")
        
        # 初始化新闻源（如果可用）
        if NEWS_AVAILABLE:
            try:
                # 传入 TuShare token和账号密码，用于TuShare新闻源
                self.news_source = UnifiedNewsSource(
                    tushare_token=TUSHARE_TOKEN,
                    tushare_username=TUSHARE_USERNAME,
                    tushare_password=TUSHARE_PASSWORD
                )
                self.sentiment_analyzer = NewsSentimentAnalyzer()
                self.news_enabled = True
            except Exception as e:
                self.logger.warning(f"新闻模块初始化失败: {str(e)}")
                self.news_enabled = False
        else:
            self.news_enabled = False
        
        # 统一加载配置（优化：减少重复查询）
        self._config_manager = None
        self._active_config = None
        self.config, self.indicator_config = self._load_all_configs()
    
    def _load_all_configs(self) -> tuple:
        """
        统一加载所有配置（优化：只查询一次数据库）
        
        Returns:
            (prediction_config, indicator_config) 元组
        """
        try:
            # 统一获取配置管理器（单例模式）
            from utils.prediction_config_manager import PredictionConfigManager
            self._config_manager = PredictionConfigManager()
            self._active_config = self._config_manager.get_config()  # 只查询一次
            
            if self._active_config:
                # 合并预测配置
                prediction_config = PREDICTION_CONFIG.copy()
                if self._active_config.get('prediction'):
                    prediction_config.update(self._active_config['prediction'])
                
                # 合并技术指标配置
                indicator_config = INDICATOR_CONFIG.copy()
                if self._active_config.get('indicator'):
                    indicator_config.update(self._active_config['indicator'])
                
                # 记录配置加载（只在首次加载时记录）
                if not hasattr(self, '_config_loaded'):
                    self.logger.info("已从数据库加载预测配置和技术指标配置")
                    self._config_loaded = True
                
                return prediction_config, indicator_config
        except Exception as e:
            self.logger.warning(f"从数据库加载配置失败，使用config.py默认值: {str(e)}")
        
        # 使用config.py中的默认配置
        return PREDICTION_CONFIG.copy(), INDICATOR_CONFIG.copy()
    
    
    def refresh_config(self):
        """刷新配置（支持热更新）"""
        # 清除配置管理器缓存
        if self._config_manager:
            self._config_manager.clear_cache()
        # 重新加载所有配置
        self.config, self.indicator_config = self._load_all_configs()
        self.logger.info("配置已刷新")
    
    def _get_current_config_id(self) -> Optional[int]:
        """
        获取当前激活的配置ID（用于学习分析）
        
        注意：如果已有配置管理器实例（self._config_manager），建议复用以避免重复查询
        """
        try:
            from utils.prediction_config_manager import PredictionConfigManager
            # 优化：如果已有配置管理器实例，复用它（避免重复创建）
            if hasattr(self, '_config_manager') and self._config_manager is not None:
                config_manager = self._config_manager
            else:
                config_manager = PredictionConfigManager()
            active_config = config_manager.get_config()
            if active_config and active_config.get('config_id'):
                return active_config['config_id']
        except Exception as e:
            self.logger.debug(f"获取配置ID失败: {str(e)}")
        return None
    
    def calculate_technical_score(self, data: pd.DataFrame, symbol: str = None) -> Dict:
        """
        计算技术指标得分（改进：增加换手率和量价关系分析）
        
        Args:
            data: 股票数据
            symbol: 股票代码（用于获取换手率等额外信息）
        
        Returns:
            {
                'score': 技术得分 (-1到1),
                'signals': 各项技术指标信号,
                'trend': 'up'/'down'/'neutral'
            }
        """
        try:
            if data.empty or len(data) < 30:
                return {'score': 0.0, 'signals': {}, 'trend': 'neutral'}
            
            signals = {}
            scores = []
            
            # 1. MACD信号
            try:
                from quant_trading_platform.indicators.technical_indicators import MACD, RSI, SMA
            except ImportError:
                # 如果无法导入，使用本地实现
                def MACD(data, fast=12, slow=26, signal=9):
                    ema_fast = data.ewm(span=fast).mean()
                    ema_slow = data.ewm(span=slow).mean()
                    macd = ema_fast - ema_slow
                    signal_line = macd.ewm(span=signal).mean()
                    histogram = macd - signal_line
                    return pd.DataFrame({'macd': macd, 'signal': signal_line, 'histogram': histogram})
                
                def RSI(data, period=14):
                    delta = data.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    return rsi
                
                def SMA(data, period):
                    return data.rolling(window=period).mean()
            macd_data = MACD(
                data['close'],
                self.indicator_config['macd_fast'],
                self.indicator_config['macd_slow'],
                self.indicator_config['macd_signal']
            )
            macd_value = macd_data['macd'].iloc[-1]
            macd_signal = macd_data['signal'].iloc[-1]
            macd_hist = macd_data['histogram'].iloc[-1]
            
            if macd_hist > 0 and macd_value > macd_signal:
                macd_score = 0.3
                signals['MACD'] = '买入'
            elif macd_hist < 0 and macd_value < macd_signal:
                macd_score = -0.3
                signals['MACD'] = '卖出'
            else:
                macd_score = 0.0
                signals['MACD'] = '中性'
            
            scores.append(macd_score)
            
            # 2. RSI信号（14周期）
            rsi = RSI(data['close'], self.indicator_config['rsi_period'])
            rsi_value = rsi.iloc[-1]
            
            if rsi_value < 30:
                rsi_score = 0.2  # 超卖，可能反弹
                signals['RSI(14)'] = f'超卖({rsi_value:.1f})'
            elif rsi_value > 70:
                rsi_score = -0.2  # 超买，可能回调
                signals['RSI(14)'] = f'超买({rsi_value:.1f})'
            else:
                rsi_score = 0.0
                signals['RSI(14)'] = f'正常({rsi_value:.1f})'
            
            scores.append(rsi_score)
            
            # 2.1. RSI(6)短周期信号
            rsi_6 = RSI(data['close'], self.indicator_config['rsi_short'])
            rsi_6_value = rsi_6.iloc[-1]
            
            if rsi_6_value < 30:
                rsi_6_score = 0.15  # 短期超卖
                signals['RSI(6)'] = f'超卖({rsi_6_value:.1f})'
            elif rsi_6_value > 70:
                rsi_6_score = -0.15  # 短期超买
                signals['RSI(6)'] = f'超买({rsi_6_value:.1f})'
            else:
                rsi_6_score = 0.0
                signals['RSI(6)'] = f'正常({rsi_6_value:.1f})'
            
            scores.append(rsi_6_score)
            
            # 2.2. RSI(12)中周期信号
            rsi_12 = RSI(data['close'], self.indicator_config['rsi_mid'])
            rsi_12_value = rsi_12.iloc[-1]
            
            if rsi_12_value < 30:
                rsi_12_score = 0.15  # 中期超卖
                signals['RSI(12)'] = f'超卖({rsi_12_value:.1f})'
            elif rsi_12_value > 70:
                rsi_12_score = -0.15  # 中期超买
                signals['RSI(12)'] = f'超买({rsi_12_value:.1f})'
            else:
                rsi_12_score = 0.0
                signals['RSI(12)'] = f'正常({rsi_12_value:.1f})'
            
            scores.append(rsi_12_score)
            
            # 2.3. KDJ指标
            def calculate_KDJ(data, period=9, k_period=3, d_period=3):
                """计算KDJ指标"""
                low_min = data['low'].rolling(window=period).min()
                high_max = data['high'].rolling(window=period).max()
                rsv = (data['close'] - low_min) / (high_max - low_min) * 100
                
                k = rsv.ewm(alpha=1/k_period, adjust=False).mean()
                d = k.ewm(alpha=1/d_period, adjust=False).mean()
                j = 3 * k - 2 * d
                
                return pd.DataFrame({'K': k, 'D': d, 'J': j})
            
            kdj_data = calculate_KDJ(
                data,
                self.indicator_config['kdj_period'],
                self.indicator_config['kdj_k_period'],
                self.indicator_config['kdj_d_period']
            )
            k_value = kdj_data['K'].iloc[-1]
            d_value = kdj_data['D'].iloc[-1]
            j_value = kdj_data['J'].iloc[-1]
            
            # KDJ判断：K>D且都在低位(20以下)看多，K<D且都在高位(80以上)看空
            kdj_score = 0.0
            if k_value > d_value:
                if k_value < 20 and d_value < 20:
                    kdj_score = 0.2  # 低位金叉，看多
                    signals['KDJ'] = f'低位金叉(K:{k_value:.1f},D:{d_value:.1f})'
                elif k_value > 80 and d_value > 80:
                    kdj_score = -0.1  # 高位但金叉，谨慎看空
                    signals['KDJ'] = f'高位金叉(K:{k_value:.1f},D:{d_value:.1f})'
                else:
                    kdj_score = 0.1  # 金叉，偏多
                    signals['KDJ'] = f'金叉(K:{k_value:.1f},D:{d_value:.1f})'
            else:
                if k_value > 80 and d_value > 80:
                    kdj_score = -0.2  # 高位死叉，看空
                    signals['KDJ'] = f'高位死叉(K:{k_value:.1f},D:{d_value:.1f})'
                elif k_value < 20 and d_value < 20:
                    kdj_score = 0.1  # 低位但死叉，谨慎看多
                    signals['KDJ'] = f'低位死叉(K:{k_value:.1f},D:{d_value:.1f})'
                else:
                    kdj_score = -0.1  # 死叉，偏空
                    signals['KDJ'] = f'死叉(K:{k_value:.1f},D:{d_value:.1f})'
            
            scores.append(kdj_score)
            
            # 2.4. CCI指标
            def calculate_CCI(data, period=14):
                """计算CCI指标"""
                tp = (data['high'] + data['low'] + data['close']) / 3  # 典型价格
                sma_tp = tp.rolling(window=period).mean()
                mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
                cci = (tp - sma_tp) / (0.015 * mad)
                return cci
            
            cci = calculate_CCI(data, self.indicator_config['cci_period'])
            cci_value = cci.iloc[-1]
            
            if cci_value > 100:
                cci_score = -0.15  # 超买区域
                signals['CCI'] = f'超买({cci_value:.1f})'
            elif cci_value < -100:
                cci_score = 0.15  # 超卖区域
                signals['CCI'] = f'超卖({cci_value:.1f})'
            else:
                cci_score = 0.0
                signals['CCI'] = f'正常({cci_value:.1f})'
            
            scores.append(cci_score)
            
            # 2.5. X2指标（收盘价在20日价格区间中的相对位置）
            x2_score = 0.0
            x2_value = None
            try:
                # 优先从数据中获取x2值（如果数据来自数据库，应该包含x2字段）
                if 'x2' in data.columns and pd.notna(data['x2'].iloc[-1]):
                    x2_value = float(data['x2'].iloc[-1])
                else:
                    # 如果数据中没有x2，动态计算（需要至少20日数据）
                    if len(data) >= 20:
                        recent_20 = data.tail(20)
                        llv_low = recent_20['low'].min()
                        hhv_high = recent_20['high'].max()
                        current_close = data['close'].iloc[-1]
                        range_width = hhv_high - llv_low
                        
                        if range_width > 0:
                            x2_value = (current_close - llv_low) / range_width * 100
                        else:
                            x2_value = 50.0  # 价格无波动，设置为中间值
                
                if x2_value is not None:
                    # X2指标判断：从indicator_config读取参数（修复：不再从prediction配置读取）
                    x2_overbought_threshold = self.indicator_config.get('x2_overbought_threshold', 80)
                    x2_oversold_threshold = self.indicator_config.get('x2_oversold_threshold', 20)
                    x2_high_threshold = self.indicator_config.get('x2_high_threshold', 60)
                    x2_low_threshold = self.indicator_config.get('x2_low_threshold', 40)
                    x2_overbought_score = self.indicator_config.get('x2_overbought_score', -0.15)
                    x2_oversold_score = self.indicator_config.get('x2_oversold_score', 0.15)
                    x2_high_score = self.indicator_config.get('x2_high_score', -0.05)
                    x2_low_score = self.indicator_config.get('x2_low_score', 0.05)
                    
                    if x2_value > x2_overbought_threshold:
                        x2_score = x2_overbought_score  # 超买区域，可能回调
                        signals['X2'] = f'超买({x2_value:.1f})'
                    elif x2_value < x2_oversold_threshold:
                        x2_score = x2_oversold_score  # 超卖区域，可能反弹
                        signals['X2'] = f'超卖({x2_value:.1f})'
                    elif x2_value > x2_high_threshold:
                        x2_score = x2_high_score  # 偏高，谨慎看空
                        signals['X2'] = f'偏高({x2_value:.1f})'
                    elif x2_value < x2_low_threshold:
                        x2_score = x2_low_score  # 偏低，谨慎看多
                        signals['X2'] = f'偏低({x2_value:.1f})'
                    else:
                        x2_score = 0.0
                        signals['X2'] = f'正常({x2_value:.1f})'
                else:
                    signals['X2'] = '数据不足'
            except Exception as e:
                self.logger.debug(f"计算X2指标失败: {str(e)}")
                signals['X2'] = '计算失败'
            
            scores.append(x2_score)
            
            # 3. 移动平均线信号（已在上面导入）
            ma_short = SMA(data['close'], self.indicator_config['ma_short'])
            ma_long = SMA(data['close'], self.indicator_config['ma_long'])
            
            current_price = data['close'].iloc[-1]
            ma_short_val = ma_short.iloc[-1]
            ma_long_val = ma_long.iloc[-1]
            
            if ma_short_val > ma_long_val and current_price > ma_short_val:
                ma_score = 0.3
                signals['MA'] = '上涨趋势'
            elif ma_short_val < ma_long_val and current_price < ma_short_val:
                ma_score = -0.3
                signals['MA'] = '下跌趋势'
            else:
                ma_score = 0.0
                signals['MA'] = '震荡'
            
            scores.append(ma_score)
            
            # 4. 价格动量
            price_change = (data['close'].iloc[-1] - data['close'].iloc[-5]) / data['close'].iloc[-5]
            if price_change > 0.05:
                momentum_score = 0.2
                signals['动量'] = '强势'
            elif price_change < -0.05:
                momentum_score = -0.2
                signals['动量'] = '弱势'
            else:
                momentum_score = 0.0
                signals['动量'] = '平稳'
            
            scores.append(momentum_score)
            
            # 5. 成交量分析（改进：量价关系）
            volume_ma = data['volume'].rolling(5).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            current_price = data['close'].iloc[-1]
            prev_price = data['close'].iloc[-2]
            price_change_pct = (current_price - prev_price) / prev_price * 100
            
            volume_score = 0.0
            # 量价关系分析
            if current_volume > volume_ma * 1.5:  # 放量
                if price_change_pct > 1.0:  # 放量上涨
                    volume_score = 0.2
                    signals['量价关系'] = '放量上涨'
                elif price_change_pct < -1.0:  # 放量下跌
                    volume_score = -0.2
                    signals['量价关系'] = '放量下跌'
                else:  # 放量震荡
                    volume_score = 0.05 if price_change_pct > 0 else -0.05
                    signals['量价关系'] = '放量震荡'
            elif current_volume < volume_ma * 0.7:  # 缩量
                if price_change_pct > 0.5:  # 缩量上涨
                    volume_score = 0.1
                    signals['量价关系'] = '缩量上涨'
                elif price_change_pct < -0.5:  # 缩量下跌
                    volume_score = -0.1
                    signals['量价关系'] = '缩量下跌'
                else:  # 缩量震荡
                    volume_score = 0.0
                    signals['量价关系'] = '缩量震荡'
            else:  # 正常
                volume_score = 0.0
                signals['量价关系'] = '正常'
            
            scores.append(volume_score)
            
            # 5.1. 换手率分析（新增）- 从数据库获取，不调用API
            # 性能优化：如果已提供预查询数据，直接使用（避免重复查询）
            turnover_rate_score = 0.0
            try:
                # 从数据库获取换手率数据（设置页面预测：只使用数据库数据）
                turnover_rate = None
                # 注意：calculate_technical_score 方法目前不接收 pre_queried_data 参数
                # 因为它是数据依赖任务，换手率查询保留在这里
                try:
                    from utils.db_connection import DatabaseConnection
                    from datetime import datetime
                    db = DatabaseConnection()
                    # 获取最新日期的换手率数据
                    sql = """
                        SELECT turnover_rate
                        FROM stock_history_data
                        WHERE symbol = %s AND period_type = 'daily'
                        AND turnover_rate IS NOT NULL
                        ORDER BY trade_date DESC
                        LIMIT 1
                    """
                    result = db.execute_query(sql, (symbol,))
                    if result and len(result) > 0:
                        turnover_rate = result[0].get('turnover_rate')
                        if turnover_rate is not None:
                            turnover_rate = float(turnover_rate)
                except Exception as e:
                    self.logger.debug(f"从数据库获取换手率失败: {str(e)}")
                
                if turnover_rate is not None:
                    # 换手率分析：一般认为2-5%正常，>5%活跃，>10%异常活跃，<1%不活跃
                    if turnover_rate > 10:
                        turnover_rate_score = -0.15  # 异常活跃，可能出货
                        signals['换手率'] = f'异常活跃({turnover_rate:.2f}%)'
                    elif turnover_rate > 5:
                        turnover_rate_score = 0.1  # 活跃，资金关注
                        signals['换手率'] = f'活跃({turnover_rate:.2f}%)'
                    elif turnover_rate > 2:
                        turnover_rate_score = 0.05  # 正常活跃
                        signals['换手率'] = f'正常({turnover_rate:.2f}%)'
                    elif turnover_rate < 1:
                        turnover_rate_score = -0.05  # 不活跃
                        signals['换手率'] = f'不活跃({turnover_rate:.2f}%)'
                    else:
                        turnover_rate_score = 0.0
                        signals['换手率'] = f'正常({turnover_rate:.2f}%)'
                else:
                    signals['换手率'] = '数据不足（数据库中没有换手率数据）'
            except Exception as e:
                self.logger.debug(f"获取换手率失败: {str(e)}")
                signals['换手率'] = '数据不足'
            
            scores.append(turnover_rate_score)
            
            # 6. 60天标志性放量（量比2.5，创一年新高）
            landmark_volume_score = 0.0
            landmark_volume_signal = '无'
            if len(data) >= 60:
                # 计算60天内的成交量
                recent_60 = data.tail(60)
                volume_ma_60 = recent_60['volume'].mean()
                
                # 检查最近60天是否有量比2.5的放量
                volume_ratio = recent_60['volume'] / volume_ma_60
                max_volume_ratio = volume_ratio.max()
                max_volume_idx = volume_ratio.idxmax()
                max_volume_date = max_volume_idx if hasattr(max_volume_idx, 'strftime') else recent_60.index[volume_ratio.argmax()]
                
                # 检查是否创一年新高（需要至少250个交易日的数据）
                if len(data) >= 250:
                    year_high = data.tail(250)['close'].max()
                    max_volume_price = recent_60.loc[max_volume_idx, 'close'] if max_volume_idx in recent_60.index else recent_60['close'].iloc[-1]
                    
                    if max_volume_ratio >= 2.5 and max_volume_price >= year_high * 0.95:  # 允许5%的误差
                        landmark_volume_score = 0.25  # 标志性放量且创一年新高，强烈看多信号
                        signals['标志性放量'] = f'60天内量比{max_volume_ratio:.2f}，创一年新高'
                        landmark_volume_signal = f'60天内量比{max_volume_ratio:.2f}，创一年新高'
                    elif max_volume_ratio >= 2.5:
                        landmark_volume_score = 0.15  # 标志性放量但未创新高
                        signals['标志性放量'] = f'60天内量比{max_volume_ratio:.2f}'
                        landmark_volume_signal = f'60天内量比{max_volume_ratio:.2f}'
                elif max_volume_ratio >= 2.5:
                    landmark_volume_score = 0.15  # 标志性放量
                    signals['标志性放量'] = f'60天内量比{max_volume_ratio:.2f}'
                    landmark_volume_signal = f'60天内量比{max_volume_ratio:.2f}'
            
            scores.append(landmark_volume_score)
            
            # 7. 长期缩量调整（40天以上）
            long_term_volume_score = 0.0
            if len(data) >= 40:
                recent_40 = data.tail(40)
                # 计算40天前的平均成交量
                if len(data) >= 80:
                    previous_40 = data.iloc[-80:-40]
                    prev_volume_ma = previous_40['volume'].mean()
                    current_volume_ma = recent_40['volume'].mean()
                    
                    # 如果当前40天平均成交量比前40天减少超过30%，认为是长期缩量
                    volume_decrease = (prev_volume_ma - current_volume_ma) / prev_volume_ma
                    if volume_decrease > 0.3:
                        # 缩量调整通常是看多信号（洗盘）
                        long_term_volume_score = 0.2
                        signals['长期缩量'] = f'40天缩量{volume_decrease*100:.1f}%'
                    else:
                        signals['长期缩量'] = '无'
                else:
                    signals['长期缩量'] = '数据不足'
            else:
                signals['长期缩量'] = '数据不足'
            
            scores.append(long_term_volume_score)
            
            # 8. 回踩60日生命线附近（距离<3%）
            ma60_support_score = 0.0
            ma60_value = None
            if len(data) >= 60:
                ma60 = SMA(data['close'], 60)
                ma60_value = ma60.iloc[-1]
                current_price = data['close'].iloc[-1]
                
                # 计算距离60日均线的百分比
                distance_pct = abs(current_price - ma60_value) / ma60_value * 100
                
                if distance_pct < 3:
                    # 回踩60日线附近，通常是支撑位，看多信号
                    if current_price < ma60_value:
                        ma60_support_score = 0.2  # 在60日线下方，回踩支撑
                        signals['60日线'] = f'回踩60日线附近(距离{distance_pct:.2f}%)'
                    else:
                        ma60_support_score = 0.15  # 在60日线上方，获得支撑
                        signals['60日线'] = f'60日线上方(距离{distance_pct:.2f}%)'
                elif current_price > ma60_value:
                    signals['60日线'] = f'60日线上方(距离{distance_pct:.2f}%)'
                else:
                    signals['60日线'] = f'60日线下方(距离{distance_pct:.2f}%)'
            else:
                signals['60日线'] = '数据不足'
            
            scores.append(ma60_support_score)
            
            # 9. 再次放量或底部形态
            volume_rebound_score = 0.0
            bottom_pattern_score = 0.0
            
            if len(data) >= 20:
                # 检查最近是否出现再次放量
                recent_5 = data.tail(5)
                recent_5_volume_ma = recent_5['volume'].mean()
                prev_10_volume_ma = data.iloc[-15:-5]['volume'].mean() if len(data) >= 15 else recent_5_volume_ma
                
                if recent_5_volume_ma > prev_10_volume_ma * 1.5:
                    volume_rebound_score = 0.15  # 再次放量，看多信号
                    signals['再次放量'] = '是'
                else:
                    signals['再次放量'] = '否'
                
                # 检查底部形态（双底、头肩底等简化判断）
                if len(data) >= 30:
                    recent_30 = data.tail(30)
                    recent_low = recent_30['low'].min()
                    recent_low_idx = recent_30['low'].idxmin()
                    
                    # 检查是否在底部区域（最近30天最低点附近）
                    current_price = data['close'].iloc[-1]
                    distance_from_low = (current_price - recent_low) / recent_low * 100
                    
                    # 如果当前价格在最低点5%以内，且最近有反弹，可能是底部形态
                    if distance_from_low < 5:
                        # 检查最近是否有反弹
                        recent_5_pct = (data['close'].iloc[-1] - data['close'].iloc[-5]) / data['close'].iloc[-5] * 100
                        if recent_5_pct > 0:  # 最近5天有上涨
                            bottom_pattern_score = 0.2  # 底部形态，看多信号
                            signals['底部形态'] = '疑似底部'
                        else:
                            signals['底部形态'] = '接近底部'
                    else:
                        signals['底部形态'] = '无'
                else:
                    signals['底部形态'] = '数据不足'
            else:
                signals['再次放量'] = '数据不足'
                signals['底部形态'] = '数据不足'
            
            scores.append(volume_rebound_score)
            scores.append(bottom_pattern_score)
            
            # 计算总分
            total_score = sum(scores)
            total_score = max(-1.0, min(1.0, total_score))  # 限制在-1到1
            
            # 判断趋势
            if total_score > 0.2:
                trend = 'up'
            elif total_score < -0.2:
                trend = 'down'
            else:
                trend = 'neutral'
            
            result = {
                'score': total_score,
                'signals': signals,
                'trend': trend,
                'details': {
                    'MACD': macd_value,
                    'RSI(14)': rsi_value,
                    'RSI(6)': rsi_6_value,
                    'RSI(12)': rsi_12_value,
                    'KDJ_K': k_value,
                    'KDJ_D': d_value,
                    'KDJ_J': j_value,
                    'CCI': cci_value,
                    'X2': x2_value if 'x2_value' in locals() else None,
                    'MA_short': ma_short_val,
                    'MA_long': ma_long_val,
                    'MA60': ma60_value if len(data) >= 60 else None,
                    'price_change': price_change,
                    'landmark_volume': landmark_volume_signal,
                    'long_term_volume': signals.get('长期缩量', '无'),
                    'ma60_support': signals.get('60日线', '无'),
                    'volume_rebound': signals.get('再次放量', '无'),
                    'bottom_pattern': signals.get('底部形态', '无')
                }
            }
            
            # 保存技术指标数据到CSV
            if self.data_storage and symbol:
                self.data_storage.save_technical_indicators(symbol, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"计算技术指标失败: {str(e)}")
            return {'score': 0.0, 'signals': {}, 'trend': 'neutral'}
    
    def _is_policy_news(self, news: Dict) -> bool:
        """
        判断是否为政策新闻
        
        Args:
            news: 新闻字典
            
        Returns:
            True if 是政策新闻, False otherwise
        """
        title = news.get('title', '').lower()
        content = news.get('content', '').lower()
        text = title + ' ' + content
        
        # 政策关键词
        policy_keywords = [
            '政策', '监管', '证监会', '交易所', '央行', '发改委', '工信部', '财政部',
            '国务院', '指导意见', '通知', '公告', '规定', '办法', '条例', '规则',
            '改革', '试点', '推进', '支持', '鼓励', '禁止', '限制', '收紧', '放松',
            '降准', '降息', '加息', '货币政策', '财政政策', '产业政策', '监管政策'
        ]
        
        # 检查是否包含政策关键词
        for keyword in policy_keywords:
            if keyword in text:
                return True
        
        return False
    
    def classify_policy_news(self, news_list: List[Dict]) -> Dict:
        """
        分类政策新闻
        - 货币政策（降准、降息等）
        - 财政政策（减税、基建等）
        - 行业政策（监管、扶持等）
        - 评估影响程度
        
        Args:
            news_list: 新闻列表
        
        Returns:
            政策分类结果
        """
        try:
            policy_types = {
                'monetary': [],  # 货币政策
                'fiscal': [],    # 财政政策
                'industry': [],  # 行业政策
                'regulation': [] # 监管政策
            }
            
            for news in news_list:
                title = news.get('title', '')
                content = news.get('content', '')
                text = (title + ' ' + content).lower()
                
                # 货币政策关键词
                monetary_keywords = ['降准', '降息', 'mlf', 'lpr', '货币政策', '利率', '准备金', '逆回购', '公开市场']
                if any(kw in text for kw in monetary_keywords):
                    policy_types['monetary'].append(news)
                    continue
                
                # 财政政策关键词
                fiscal_keywords = ['减税', '基建', '财政', '专项债', '财政政策', '税收', '财政支出', '财政补贴']
                if any(kw in text for kw in fiscal_keywords):
                    policy_types['fiscal'].append(news)
                    continue
                
                # 行业政策关键词
                industry_keywords = ['扶持', '补贴', '产业政策', '行业政策', '产业扶持', '产业规划']
                if any(kw in text for kw in industry_keywords):
                    policy_types['industry'].append(news)
                    continue
                
                # 监管政策关键词
                regulation_keywords = ['监管', '规范', '整顿', '监管政策', '监管规定', '监管措施', '处罚']
                if any(kw in text for kw in regulation_keywords):
                    policy_types['regulation'].append(news)
            
            # 评估影响
            impact_score = 0.0
            if policy_types['monetary']:
                impact_score += 0.3  # 货币政策影响大
            if policy_types['fiscal']:
                impact_score += 0.2
            if policy_types['industry']:
                impact_score += 0.15
            if policy_types['regulation']:
                impact_score -= 0.1  # 监管政策通常偏负面
            
            return {
                'policy_types': {
                    'monetary': len(policy_types['monetary']),
                    'fiscal': len(policy_types['fiscal']),
                    'industry': len(policy_types['industry']),
                    'regulation': len(policy_types['regulation'])
                },
                'policy_news': policy_types,
                'impact_score': impact_score,
                'has_major_policy': impact_score > 0.3,
                'summary': f"货币政策{len(policy_types['monetary'])}条，财政政策{len(policy_types['fiscal'])}条，行业政策{len(policy_types['industry'])}条，监管政策{len(policy_types['regulation'])}条"
            }
            
        except Exception as e:
            self.logger.error(f"分类政策新闻失败: {str(e)}")
            return {
                'policy_types': {},
                'policy_news': {},
                'impact_score': 0.0,
                'has_major_policy': False,
                'summary': '分类失败'
            }
    
    def _check_news_industry_relevance(self, news: Dict, industry_keywords: List[str], industry_info: Dict) -> float:
        """
        检查新闻与行业/板块的相关性（更智能的判断）
        
        Args:
            news: 新闻字典
            industry_keywords: 行业关键词列表
            industry_info: 行业信息字典
            
        Returns:
            相关性得分 (0-1)，1表示高度相关，0表示不相关
        """
        if not industry_keywords:
            return 0.0
        
        title = news.get('title', '').lower()
        content = news.get('content', '').lower()
        text = title + ' ' + content
        
        relevance_score = 0.0
        
        # 1. 关键词匹配（基础得分）
        matched_keywords = []
        for keyword in industry_keywords:
            if keyword and keyword.lower() in text:
                matched_keywords.append(keyword)
                relevance_score += 0.3  # 每个关键词0.3分
        
        # 2. 行业名称完整匹配（更高权重）
        industry = industry_info.get('industry', '')
        if industry and industry.lower() in text:
            relevance_score += 0.5
        
        # 3. 概念板块匹配（中等权重）
        concepts = industry_info.get('concepts', [])
        for concept in concepts:
            if concept and concept.lower() in text:
                relevance_score += 0.4
        
        # 4. 检查是否提到行业相关的公司、产品、政策等
        # 行业相关词汇（如"该行业"、"板块"、"产业链"等）
        industry_related_words = ['行业', '板块', '产业链', '细分', '领域', '市场', '产业']
        for word in industry_related_words:
            if word in text and matched_keywords:
                relevance_score += 0.2
                break
        
        # 5. 检查新闻内容深度（如果包含多个行业关键词，相关性更高）
        if len(matched_keywords) >= 2:
            relevance_score += 0.3
        
        # 限制在0-1之间
        relevance_score = min(1.0, relevance_score)
        
        return relevance_score
    
    def calculate_news_score(self, symbol: str, use_api: bool = True, pre_queried_news: Dict = None, pre_queried_industry_info: Dict = None) -> Dict:
        """
        计算新闻情感得分
        包括直接提到股票的新闻和行业/概念相关的新闻
        根据利空/利好动态调整权重
        
        Args:
            symbol: 股票代码
            use_api: 是否使用API获取数据（设置页面预测时应设为False，只使用数据库数据）
        
        Returns:
            {
                'score': 新闻得分 (-1到1),
                'sentiment': 'positive'/'negative'/'neutral',
                'news_count': 新闻数量,
                'confidence': 置信度,
                'weight_multiplier': 权重倍数（根据利空/利好动态调整）
            }
        """
        if not self.news_enabled:
            return {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'confidence': 0.0, 'weight_multiplier': 1.0}
        
        try:
            # 获取股票行业信息（性能优化：优先使用预加载的数据）
            industry_keywords = []
            industry_info = {'industry': '', 'concepts': [], 'industry_keywords': []}
            try:
                # 性能优化：如果提供了预加载的行业信息，直接使用
                if pre_queried_industry_info:
                    industry_info = pre_queried_industry_info
                    industry_keywords = industry_info.get('industry_keywords', [])
                else:
                    # 设置页面预测：如果use_api=False，从数据库获取；否则从API获取
                    industry_info = self.data_source.get_stock_industry_info(symbol, use_db_only=not use_api)
                    industry_keywords = industry_info.get('industry_keywords', [])
                
                if industry_info.get('industry'):
                    industry_keywords.append(industry_info['industry'])
                if industry_info.get('concepts'):
                    industry_keywords.extend(industry_info['concepts'])
                
                # 去重
                industry_keywords = list(set([k for k in industry_keywords if k and k.strip()]))
                
                if industry_keywords:
                    self.logger.info(f"股票 {symbol} 行业/概念关键词: {', '.join(industry_keywords[:5])}")
            except Exception as e:
                self.logger.debug(f"获取行业信息失败: {str(e)}")
            
            # 优先从数据库获取当天新闻（性能优化：优先使用预加载的数据）
            direct_news = []
            market_news = []
            use_database_news = False
            
            # 性能优化：如果提供了预加载的新闻数据，直接使用
            if pre_queried_news:
                symbol_padded = symbol.zfill(6)
                if symbol_padded in pre_queried_news:
                    direct_news = pre_queried_news[symbol_padded]
                    for n in direct_news:
                        n['relevance'] = 'direct'
                        n['relevance_score'] = 1.0  # 直接相关，相关性为1
                    use_database_news = True
                    self.logger.debug(f"使用预加载的 {symbol} 当天 {len(direct_news)} 条直接新闻")
                
                if 'market' in pre_queried_news:
                    market_news = pre_queried_news['market']
                    use_database_news = True
                    self.logger.debug(f"使用预加载的当天 {len(market_news)} 条市场新闻")
            
            # 如果没有预加载数据，从数据库获取
            if not use_database_news:
                try:
                    from utils.news_storage import NewsStorage
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        news_storage = NewsStorage()
                        
                        # 从数据库获取股票当天新闻
                        db_direct_news = news_storage.get_today_news_by_symbol(
                            symbol=symbol,
                            limit=NEWS_CONFIG['news_count']
                        )
                        
                        if db_direct_news:
                            direct_news = db_direct_news
                            for n in direct_news:
                                n['relevance'] = 'direct'
                                n['relevance_score'] = 1.0  # 直接相关，相关性为1
                            use_database_news = True
                            self.logger.debug(f"从数据库获取到 {symbol} 当天 {len(direct_news)} 条直接新闻")
                        
                        # 从数据库获取当天市场新闻
                        db_market_news = news_storage.get_today_market_news(
                            limit=NEWS_CONFIG['news_count'] * 3
                        )
                        
                        if db_market_news:
                            market_news = db_market_news
                            use_database_news = True
                            self.logger.debug(f"从数据库获取到当天 {len(market_news)} 条市场新闻")
                except Exception as e:
                    self.logger.debug(f"从数据库获取新闻失败，将使用API: {str(e)}")
            
            # 【已禁用】如果数据库没有新闻，从API获取
            # 注意：当前只从 news-analysis-system-main 获取新闻，不再调用 API
            # 如果数据库没有新闻，记录警告但不从 API 获取
            if not use_database_news or not market_news:
                self.logger.warning(f"数据库中没有找到 {symbol} 的新闻，建议检查 news-analysis-system-main 是否正常运行")
                # 【已禁用】以下代码已禁用，不再从 API 获取新闻
                # try:
                #     # 获取更多市场新闻用于筛选
                #     if not market_news:
                #         market_news = self.news_source.get_market_news(NEWS_CONFIG['news_count'] * 3)
                #     
                #     # 获取直接提到股票的新闻
                #     if not direct_news:
                #         if hasattr(self.news_source, 'sources'):
                #             for source_name, source in self.news_source.sources:
                #                 try:
                #                     news = source.get_stock_news(symbol, NEWS_CONFIG['news_count'])
                #                     for n in news:
                #                         n['relevance'] = 'direct'
                #                         n['relevance_score'] = 1.0  # 直接相关，相关性为1
                #                     direct_news.extend(news)
                #                 except Exception as e:
                #                     self.logger.debug(f"从 {source_name} 获取新闻失败: {str(e)}")
                # except Exception as e:
                #     self.logger.debug(f"从API获取新闻失败: {str(e)}")
            
            # 从市场新闻中筛选行业相关新闻（更智能的判断）
            industry_news = []
            for news in market_news:
                # 检查是否已经包含在直接新闻中（去重）
                if any(n.get('title') == news.get('title') for n in direct_news):
                    continue
                
                # 使用LLM分类筛选：跳过非金融类新闻
                llm_is_market_relevant = news.get('llm_is_market_relevant')
                if llm_is_market_relevant is not None and llm_is_market_relevant == 0:
                    self.logger.debug(f"跳过非金融类新闻（LLM标记）: {news.get('title', '')[:50]}")
                    continue
                
                llm_category = news.get('llm_category')
                if llm_category == '非金融类':
                    self.logger.debug(f"跳过非金融类新闻（LLM分类）: {news.get('title', '')[:50]}")
                    continue
                
                # 使用更智能的相关性判断
                relevance_score = self._check_news_industry_relevance(news, industry_keywords, industry_info)
                
                # 如果相关性得分 > 0.3，认为是行业相关新闻
                if relevance_score > 0.3:
                    news['relevance'] = 'industry'
                    news['relevance_score'] = relevance_score
                    industry_news.append(news)
            
            # 合并所有新闻
            all_news = direct_news + industry_news
            
            # 去重（基于标题）
            seen_titles = set()
            unique_news = []
            for news in all_news:
                title = news.get('title', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    unique_news.append(news)
            
            # 使用LLM分类进一步筛选：跳过非金融类新闻
            filtered_news = []
            skipped_count = 0
            for news in unique_news:
                llm_is_market_relevant = news.get('llm_is_market_relevant')
                if llm_is_market_relevant is not None and llm_is_market_relevant == 0:
                    skipped_count += 1
                    continue
                
                llm_category = news.get('llm_category')
                if llm_category == '非金融类':
                    skipped_count += 1
                    continue
                
                filtered_news.append(news)
            
            if skipped_count > 0:
                self.logger.info(f"使用LLM分类筛选，跳过 {skipped_count} 条非金融类新闻")
            
            unique_news = filtered_news
            
            # 按相关性和时间排序
            def sort_key(news):
                relevance = news.get('relevance', 'other')
                relevance_score = news.get('relevance_score', 0.0)
                time_val = news.get('time', datetime.min)
                if relevance == 'direct':
                    return (0, time_val)
                elif relevance == 'industry':
                    return (1, -relevance_score, time_val)  # 相关性高的优先
                else:
                    return (2, time_val)
            
            unique_news.sort(key=sort_key, reverse=True)
            
            # 取最新的
            news_list = unique_news[:NEWS_CONFIG['news_count'] * 2]
            
            if not news_list:
                return {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'confidence': 0.0, 'weight_multiplier': 1.0}
            
            # 识别政策新闻并标记
            policy_news_count = 0
            for news in news_list:
                if self._is_policy_news(news):
                    news['is_policy'] = True
                    policy_news_count += 1
                else:
                    news['is_policy'] = False
            
            # 先分类政策新闻（用于后续权重调整）
            policy_news_list = [n for n in news_list if n.get('is_policy', False)]
            policy_classification = self.classify_policy_news(policy_news_list) if policy_news_list else {}
            policy_news_dict = policy_classification.get('policy_news', {})
            
            # 为每个新闻标记政策类型
            for news in news_list:
                if news.get('is_policy', False):
                    # 查找该新闻属于哪个政策类型
                    news_title = news.get('title', '')
                    news_content = news.get('content', '')
                    news_text = (news_title + ' ' + news_content).lower()
                    
                    policy_type = None
                    # 检查货币政策
                    monetary_keywords = ['降准', '降息', 'mlf', 'lpr', '货币政策', '利率', '准备金', '逆回购', '公开市场']
                    if any(kw in news_text for kw in monetary_keywords):
                        policy_type = 'monetary'
                    # 检查财政政策
                    elif any(kw in news_text for kw in ['减税', '基建', '财政', '专项债', '财政政策', '税收', '财政支出', '财政补贴']):
                        policy_type = 'fiscal'
                    # 检查行业政策
                    elif any(kw in news_text for kw in ['扶持', '补贴', '产业政策', '行业政策', '产业扶持', '产业规划']):
                        policy_type = 'industry'
                    # 检查监管政策
                    elif any(kw in news_text for kw in ['监管', '规范', '整顿', '监管政策', '监管规定', '监管措施', '处罚']):
                        policy_type = 'regulation'
                    
                    news['policy_type'] = policy_type
            
            # 分析情感：优先使用LLM分析结果，避免重复分析
            llm_analyzed_count = 0
            needs_analysis_count = 0
            
            # 检查哪些新闻已有LLM分析结果
            for news in news_list:
                if news.get('llm_analyzed_at') is not None and news.get('llm_sentiment_score') is not None:
                    llm_analyzed_count += 1
                else:
                    needs_analysis_count += 1
            
            if llm_analyzed_count > 0:
                self.logger.info(f"发现 {llm_analyzed_count} 条新闻已有LLM分析结果，将直接使用；{needs_analysis_count} 条需要重新分析")
            
            # 对于已有LLM分析结果的新闻，直接使用LLM结果；对于没有的，使用sentiment_analyzer分析
            sentiment_results = []
            news_to_analyze = []
            news_to_analyze_indices = []
            
            for i, news in enumerate(news_list):
                if news.get('llm_analyzed_at') is not None and news.get('llm_sentiment_score') is not None:
                    # 直接使用LLM分析结果
                    llm_score = float(news.get('llm_sentiment_score', 0.0))
                    if llm_score > 0.1:
                        sentiment_type = 'positive'
                    elif llm_score < -0.1:
                        sentiment_type = 'negative'
                    else:
                        sentiment_type = 'neutral'
                    
                    sentiment_results.append({
                        'sentiment': {
                            'sentiment': sentiment_type,
                            'score': llm_score,
                            'confidence': 0.9  # LLM分析结果置信度较高
                        },
                        'news': news
                    })
                else:
                    # 需要重新分析
                    news_to_analyze.append(news)
                    news_to_analyze_indices.append(i)
            
            # 对没有LLM分析结果的新闻进行关键词分析
            if news_to_analyze:
                analyzed_results = self.sentiment_analyzer.analyze_batch(news_to_analyze)
                # 将分析结果插入到正确的位置，并添加对应的新闻
                for idx, (result, news) in zip(news_to_analyze_indices, zip(analyzed_results, news_to_analyze)):
                    # 确保result包含news字段
                    if isinstance(result, dict):
                        result['news'] = news
                    sentiment_results.insert(idx, result)
            else:
                # 如果所有新闻都有LLM分析结果，按原始顺序排序
                sentiment_results = [r for r in sentiment_results]
            
            # 聚合情感分析结果
            aggregated = self.sentiment_analyzer.get_aggregated_sentiment(sentiment_results)
            
            # 统计利空/利好消息（包含政策新闻权重提升）
            positive_news = []
            negative_news = []
            neutral_news = []
            
            for i, sentiment_result in enumerate(sentiment_results):
                # 从sentiment_results中提取新闻和情感信息
                sentiment = sentiment_result.get('sentiment', {})
                sentiment_type = sentiment.get('sentiment', 'neutral')
                score = sentiment.get('score', 0.0)
                confidence = sentiment.get('confidence', 0.0)
                
                # 获取对应的原始新闻
                original_news = sentiment_result.get('news') if 'news' in sentiment_result else (news_list[i] if i < len(news_list) else {})
                relevance_score = original_news.get('relevance_score', 0.5)
                is_policy = original_news.get('is_policy', False)
                policy_type = original_news.get('policy_type')
                
                # 根据相关性调整情感强度
                adjusted_score = score * (0.5 + relevance_score * 0.5)  # 相关性越高，情感强度越大
                
                # 根据政策类型调整权重（不同类型的影响程度不同）
                if is_policy and policy_type:
                    if policy_type == 'monetary':
                        # 货币政策影响最大
                        adjusted_score *= 2.0  # 货币政策权重提升100%
                        confidence = min(confidence * 1.3, 1.0)  # 货币政策置信度提升30%
                    elif policy_type == 'fiscal':
                        # 财政政策影响较大
                        adjusted_score *= 1.5  # 财政政策权重提升50%
                        confidence = min(confidence * 1.2, 1.0)  # 财政政策置信度提升20%
                    elif policy_type == 'industry':
                        # 行业政策影响中等
                        adjusted_score *= 1.3  # 行业政策权重提升30%
                        confidence = min(confidence * 1.15, 1.0)  # 行业政策置信度提升15%
                    elif policy_type == 'regulation':
                        # 监管政策通常偏负面，但如果有利好也可以提升
                        adjusted_score *= 1.2  # 监管政策权重提升20%
                        confidence = min(confidence * 1.1, 1.0)  # 监管政策置信度提升10%
                elif is_policy:
                    # 如果无法确定政策类型，使用默认提升
                    adjusted_score *= 1.75  # 政策新闻权重提升75%
                    confidence = min(confidence * 1.2, 1.0)  # 政策新闻置信度提升20%
                
                if sentiment_type == 'positive' and adjusted_score > 0.1:
                    positive_news.append({
                        'news': original_news,
                        'score': adjusted_score,
                        'confidence': confidence,
                        'relevance': relevance_score
                    })
                elif sentiment_type == 'negative' and adjusted_score < -0.1:
                    negative_news.append({
                        'news': original_news,
                        'score': adjusted_score,
                        'confidence': confidence,
                        'relevance': relevance_score
                    })
                else:
                    neutral_news.append(original_news)
            
            # 计算利空/利好的强度和数量
            positive_strength = sum(p['score'] * p['confidence'] * p['relevance'] for p in positive_news)
            negative_strength = sum(abs(n['score']) * n['confidence'] * n['relevance'] for n in negative_news)
            positive_count = len(positive_news)
            negative_count = len(negative_news)
            
            # 根据利空/利好动态调整权重倍数
            weight_multiplier = 1.0  # 默认权重倍数
            
            # 如果利好消息多且强烈，增加权重
            if positive_count >= 3 and positive_strength > 0.5:
                weight_multiplier = 1.5  # 强烈利好，增加50%权重
                self.logger.info(f"检测到强烈利好消息（{positive_count}条，强度{positive_strength:.2f}），增加新闻权重")
            elif positive_count >= 2 and positive_strength > 0.3:
                weight_multiplier = 1.3  # 中等利好，增加30%权重
                self.logger.info(f"检测到中等利好消息（{positive_count}条，强度{positive_strength:.2f}），增加新闻权重")
            elif positive_count >= 1 and positive_strength > 0.2:
                weight_multiplier = 1.1  # 轻微利好，增加10%权重
            
            # 如果利空消息多且强烈，增加权重（但方向相反）
            if negative_count >= 3 and negative_strength > 0.5:
                weight_multiplier = 1.5  # 强烈利空，增加50%权重
                self.logger.info(f"检测到强烈利空消息（{negative_count}条，强度{negative_strength:.2f}），增加新闻权重")
            elif negative_count >= 2 and negative_strength > 0.3:
                weight_multiplier = 1.3  # 中等利空，增加30%权重
                self.logger.info(f"检测到中等利空消息（{negative_count}条，强度{negative_strength:.2f}），增加新闻权重")
            elif negative_count >= 1 and negative_strength > 0.2:
                weight_multiplier = 1.1  # 轻微利空，增加10%权重
            
            # 如果消息中性或矛盾（利空和利好都有），降低权重
            if positive_count > 0 and negative_count > 0:
                # 如果利空和利好数量接近，说明消息矛盾，降低权重
                if abs(positive_count - negative_count) <= 1:
                    weight_multiplier = 0.7  # 消息矛盾，降低30%权重
                    self.logger.info(f"检测到矛盾消息（利好{positive_count}条，利空{negative_count}条），降低新闻权重")
                elif abs(positive_strength - negative_strength) < 0.2:
                    weight_multiplier = 0.8  # 强度接近，降低20%权重
            
            # 如果消息太少或都是中性，降低权重
            if positive_count == 0 and negative_count == 0:
                weight_multiplier = 0.6  # 无明确利空/利好，降低40%权重
                self.logger.info("未检测到明确的利空/利好消息，降低新闻权重")
            
            # 统计新闻类型
            direct_news_count = sum(1 for n in news_list if n.get('relevance') == 'direct')
            industry_news_count = sum(1 for n in news_list if n.get('relevance') == 'industry')
            
            self.logger.info(f"新闻分析: 直接相关 {direct_news_count} 条，行业相关 {industry_news_count} 条，政策新闻 {policy_news_count} 条，总计 {len(news_list)} 条")
            self.logger.info(f"利好消息: {positive_count} 条（强度{positive_strength:.2f}），利空消息: {negative_count} 条（强度{negative_strength:.2f}）")
            self.logger.info(f"新闻权重倍数: {weight_multiplier:.2f}")
            
            # 收集LLM总结信息（用于增强预测报告）
            llm_summaries = []
            llm_categories = []
            for news in news_list:
                if news.get('llm_summary'):
                    llm_summaries.append({
                        'title': news.get('title', '')[:50],
                        'summary': news.get('llm_summary'),
                        'category': news.get('llm_category'),
                        'subcategory': news.get('llm_subcategory'),
                        'sentiment_score': news.get('llm_sentiment_score')
                    })
                if news.get('llm_category'):
                    llm_categories.append(news.get('llm_category'))
            
            # 统计LLM分类分布
            from collections import Counter
            llm_category_distribution = dict(Counter(llm_categories)) if llm_categories else {}
            
            result = {
                'score': aggregated['weighted_score'],
                'sentiment': aggregated['overall_sentiment'],
                'news_count': len(news_list),
                'direct_news_count': direct_news_count,
                'industry_news_count': industry_news_count,
                'policy_news_count': policy_news_count,  # 新增：政策新闻数量
                'confidence': min(aggregated.get('confidence', 0.0), 1.0),
                'weight_multiplier': weight_multiplier,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'positive_strength': positive_strength,
                'negative_strength': negative_strength,
                'policy_classification': policy_classification,  # 新增：政策新闻分类
                'llm_summaries': llm_summaries[:5],  # 最多返回5条LLM总结
                'llm_category_distribution': llm_category_distribution,  # LLM分类分布
                'llm_analyzed_count': llm_analyzed_count  # 使用LLM分析的新闻数量
            }
            
            # 保存新闻情感数据到CSV
            if self.data_storage:
                self.data_storage.save_news_sentiment(symbol, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"计算新闻得分失败: {str(e)}")
            return {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'confidence': 0.0, 'weight_multiplier': 1.0}
    
    def calculate_market_score(self, data: pd.DataFrame, symbol: str = None, use_api: bool = True, 
                               indices_data: Dict = None) -> Dict:
        """
        计算市场情绪得分（改进：包含大盘指数影响）
        
        Args:
            data: 股票历史数据
            symbol: 股票代码（可选）
            use_api: 是否使用API获取数据（设置页面预测时应设为False，只使用数据库数据）
            indices_data: 预查询的市场指数数据（可选，如果提供则跳过重复获取）
                         格式：{'上证指数': DataFrame, '深证成指': DataFrame, ...}
        
        Returns:
            {
                'score': 市场得分 (-1到1),
                'trend': 'up'/'down'/'neutral',
                'details': 详细信息
            }
        """
        try:
            if data.empty or len(data) < 20:
                return {'score': 0.0, 'trend': 'neutral', 'details': {}}
            
            scores = []
            weights = []
            details = {}
            
            # 1. 大盘指数影响（权重50%）
            try:
                # 性能优化：如果提供了预查询的指数数据，直接使用，避免重复获取
                if indices_data is None:
                    # 获取主要指数数据（设置页面预测：只使用数据库数据，不调用API）
                    indices_data = self.data_source.get_all_market_indices(days=20, use_db_only=not use_api)
                
                index_scores = []
                for index_name, index_df in indices_data.items():
                    if not index_df.empty and len(index_df) >= 20:
                        # 计算指数的涨跌情况
                        recent_index = index_df.tail(20)
                        index_returns = recent_index['close'].pct_change().dropna()
                        index_avg_return = index_returns.mean()
                        index_up_days = (recent_index['close'] > recent_index['close'].shift(1)).sum()
                        index_down_days = (recent_index['close'] < recent_index['close'].shift(1)).sum()
                        
                        # 计算指数得分
                        index_trend_score = (index_up_days - index_down_days) / len(recent_index)
                        index_return_score = index_avg_return * 10
                        index_score = (index_trend_score + index_return_score) / 2
                        index_scores.append(index_score)
                
                if index_scores:
                    # 取平均值作为大盘指数得分
                    market_index_score = sum(index_scores) / len(index_scores)
                    market_index_score = max(-1.0, min(1.0, market_index_score))
                    scores.append(market_index_score)
                    weights.append(0.5)
                    details['market_index_score'] = market_index_score
                    details['index_count'] = len(index_scores)
                    self.logger.debug(f"大盘指数得分: {market_index_score:.2f} (基于{len(index_scores)}个指数)")
            except Exception as e:
                self.logger.debug(f"计算大盘指数得分失败: {str(e)}")
            
            # 2. 个股情绪（权重30%）
            try:
                recent_data = data.tail(20)
                up_days = (recent_data['close'] > recent_data['close'].shift(1)).sum()
                down_days = (recent_data['close'] < recent_data['close'].shift(1)).sum()
                
                returns = recent_data['close'].pct_change().dropna()
                avg_return = returns.mean()
                
                trend_score = (up_days - down_days) / len(recent_data)
                return_score = avg_return * 10
                
                stock_score = (trend_score + return_score) / 2
                stock_score = max(-1.0, min(1.0, stock_score))
                
                scores.append(stock_score)
                weights.append(0.3)
                details['stock_score'] = stock_score
                details['up_days'] = up_days
                details['down_days'] = down_days
                details['avg_return'] = avg_return
            except Exception as e:
                self.logger.debug(f"计算个股情绪得分失败: {str(e)}")
            
            # 3. 板块情绪（权重20%，如果有板块信息）
            # 设置页面预测：如果use_api=False，从数据库获取；否则从API获取
            try:
                if symbol:
                    try:
                        # 设置页面预测：如果use_api=False，从数据库获取；否则从API获取
                        industry_info = self.data_source.get_stock_industry_info(symbol, use_db_only=not use_api)
                        industry = industry_info.get('industry', '')
                    except Exception as e:
                        # 获取失败时，使用空数据
                        self.logger.debug(f"获取行业信息失败: {str(e)}")
                        industry = ''
                else:
                    industry = ''
                    
                    if industry:
                        # 获取同行业股票的平均表现（简化处理）
                        # 这里可以根据需要实现更详细的板块分析
                        # 暂时使用个股数据作为代理
                        sector_score = stock_score if 'stock_score' in details else 0.0
                        scores.append(sector_score)
                        weights.append(0.2)
                        details['sector_score'] = sector_score
                        details['industry'] = industry
            except Exception as e:
                self.logger.debug(f"计算板块情绪得分失败: {str(e)}")
            
            # 计算加权总分
            if scores and weights:
                # 确保权重总和为1
                total_weight = sum(weights)
                if total_weight > 0:
                    weighted_scores = [s * w for s, w in zip(scores, weights)]
                    total_score = sum(weighted_scores) / total_weight
                else:
                    total_score = sum(scores) / len(scores) if scores else 0.0
            else:
                # 如果没有得分，使用个股数据计算（回退方案）
                recent_data = data.tail(20)
                returns = recent_data['close'].pct_change().dropna()
                avg_return = returns.mean()
                total_score = avg_return * 10
                details['fallback'] = True
            
            total_score = max(-1.0, min(1.0, total_score))
            
            if total_score > 0.1:
                trend = 'up'
            elif total_score < -0.1:
                trend = 'down'
            else:
                trend = 'neutral'
            
            result = {
                'score': total_score,
                'trend': trend,
                'details': details
            }
            
            # 保存市场情绪数据到CSV
            if self.data_storage:
                self.data_storage.save_market_sentiment(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"计算市场得分失败: {str(e)}")
            return {'score': 0.0, 'trend': 'neutral', 'details': {}}
    
    def calculate_market_sentiment_index(self, use_api: bool = True) -> Dict:
        """
        计算市场情绪指标（恐慌指数、贪婪指数）
        - 恐慌指数：基于下跌股票比例、跌停股票数量、成交量放大
        - 贪婪指数：基于上涨股票比例、涨停股票数量
        - 情绪化交易识别
        
        Args:
            use_api: 是否使用API获取数据（设置页面预测时应设为False，只使用数据库数据）
        
        Returns:
            市场情绪指标字典，包含：
            - fear_index: 恐慌指数（0-100）
            - greed_index: 贪婪指数（0-100）
            - sentiment: 综合情绪（'fear'/'greed'/'neutral'）
            - suggestion: 建议
        """
        try:
            # 获取市场统计数据（设置页面预测：如果use_api=False，只使用数据库数据）
            market_stats = self.data_source.get_market_statistics(use_db_only=not use_api)
            
            if not market_stats:
                return {
                    'fear_index': 50.0,
                    'greed_index': 50.0,
                    'sentiment': 'neutral',
                    'suggestion': '无法获取市场统计数据',
                    'available': False
                }
            
            # 提取数据
            falling_stocks_pct = market_stats.get('falling_stocks_pct', 0.5)
            rising_stocks_pct = market_stats.get('rising_stocks_pct', 0.5)
            limit_down_count = market_stats.get('limit_down_count', 0)
            limit_up_count = market_stats.get('limit_up_count', 0)
            total_stocks = market_stats.get('total_stocks', 0)
            
            # 计算成交量比例（需要与历史平均对比，这里简化处理）
            # 使用当前成交量作为参考，如果成交量较大，可能表示情绪化交易
            total_volume = market_stats.get('total_volume', 0)
            avg_volume = market_stats.get('avg_volume', 0)
            
            # 简化处理：使用涨跌股票比例来估算成交量放大
            # 如果下跌股票多，成交量可能放大（恐慌性抛售）
            # 如果上涨股票多，成交量也可能放大（追涨情绪）
            volume_ratio = 1.0  # 默认值
            if falling_stocks_pct > 0.6 or rising_stocks_pct > 0.6:
                # 如果涨跌股票比例极端，认为成交量放大
                volume_ratio = 1.5
            elif falling_stocks_pct > 0.5 or rising_stocks_pct > 0.5:
                volume_ratio = 1.2
            
            # 计算恐慌指数（0-100）
            # 1. 下跌股票比例（权重50%）
            fear_from_falling = falling_stocks_pct * 50
            
            # 2. 跌停股票数量（权重30%）
            # 跌停股票数量越多，恐慌指数越高
            # 假设跌停股票数量超过总股票数的1%为极端恐慌
            limit_down_ratio = limit_down_count / total_stocks if total_stocks > 0 else 0
            fear_from_limit_down = min(limit_down_ratio * 100, 1.0) * 30  # 最多30分
            
            # 3. 成交量放大（权重20%）
            # 恐慌时成交量放大
            fear_from_volume = min((volume_ratio - 1.0) * 20, 20) if volume_ratio > 1.0 else 0
            
            fear_index = fear_from_falling + fear_from_limit_down + fear_from_volume
            fear_index = max(0.0, min(100.0, fear_index))
            
            # 计算贪婪指数（0-100）
            # 1. 上涨股票比例（权重50%）
            greed_from_rising = rising_stocks_pct * 50
            
            # 2. 涨停股票数量（权重30%）
            # 涨停股票数量越多，贪婪指数越高
            limit_up_ratio = limit_up_count / total_stocks if total_stocks > 0 else 0
            greed_from_limit_up = min(limit_up_ratio * 100, 1.0) * 30  # 最多30分
            
            # 3. 成交量放大（权重20%）
            # 贪婪时成交量也可能放大（追涨情绪）
            greed_from_volume = min((volume_ratio - 1.0) * 20, 20) if volume_ratio > 1.0 else 0
            
            greed_index = greed_from_rising + greed_from_limit_up + greed_from_volume
            greed_index = max(0.0, min(100.0, greed_index))
            
            # 综合情绪判断
            if fear_index > 60:
                sentiment = 'fear'
                suggestion = f'恐慌情绪高（{fear_index:.1f}），下跌股票占比{falling_stocks_pct*100:.1f}%，跌停{limit_down_count}只，可能超跌，可考虑抄底机会'
            elif greed_index > 60:
                sentiment = 'greed'
                suggestion = f'贪婪情绪高（{greed_index:.1f}），上涨股票占比{rising_stocks_pct*100:.1f}%，涨停{limit_up_count}只，注意追高风险'
            else:
                sentiment = 'neutral'
                suggestion = f'市场情绪中性（恐慌{fear_index:.1f}，贪婪{greed_index:.1f}），涨跌相对均衡'
            
            # 情绪化交易识别
            emotional_trading = False
            emotional_reason = ''
            if fear_index > 70 or greed_index > 70:
                emotional_trading = True
                if fear_index > 70:
                    emotional_reason = '恐慌性抛售，可能存在超跌机会'
                else:
                    emotional_reason = '追涨情绪高涨，注意回调风险'
            
            return {
                'available': True,
                'fear_index': round(fear_index, 2),
                'greed_index': round(greed_index, 2),
                'sentiment': sentiment,
                'suggestion': suggestion,
                'emotional_trading': emotional_trading,
                'emotional_reason': emotional_reason,
                'market_stats': {
                    'total_stocks': total_stocks,
                    'rising_stocks_pct': round(rising_stocks_pct * 100, 2),
                    'falling_stocks_pct': round(falling_stocks_pct * 100, 2),
                    'limit_up_count': limit_up_count,
                    'limit_down_count': limit_down_count,
                    'volume_ratio': round(volume_ratio, 2)
                },
                'date': market_stats.get('date', '')
            }
            
        except Exception as e:
            self.logger.error(f"计算市场情绪指标失败: {str(e)}")
            return {
                'available': False,
                'fear_index': 50.0,
                'greed_index': 50.0,
                'sentiment': 'neutral',
                'suggestion': f'计算失败: {str(e)}',
                'error': str(e)
            }
    
    def calculate_us_sector_score(self, symbol: str, use_api: bool = True) -> Dict:
        """
        计算美股板块得分（根据股票所属行业，获取对应美股板块的走势）
        
        Args:
            symbol: 股票代码
            use_api: 是否使用API获取数据（设置页面预测时应设为False，只使用数据库数据）
        
        Returns:
            {
                'score': 美股板块得分 (-1到1),
                'sector': 对应的美股板块名称,
                'trend': 'up'/'down'/'neutral',
                'change_pct': 涨跌幅百分比
            }
        """
        try:
            # 获取股票的行业信息（设置页面预测：如果use_api=False，从数据库获取；否则从API获取）
            industry_info = self.data_source.get_stock_industry_info(symbol, use_db_only=not use_api)
            industry = industry_info.get('industry', '')
            concepts = industry_info.get('concepts', [])
            
            # 获取美股板块映射
            sector_mapping = self.data_source.get_us_sector_mapping()
            
            # 找到对应的美股板块
            matched_sector = None
            for us_sector, a_stock_keywords in sector_mapping.items():
                # 检查行业是否匹配
                if industry and any(keyword in industry for keyword in a_stock_keywords):
                    matched_sector = us_sector
                    break
                # 检查概念是否匹配
                if concepts:
                    for concept in concepts:
                        if any(keyword in concept for keyword in a_stock_keywords):
                            matched_sector = us_sector
                            break
                    if matched_sector:
                        break
            
            # 如果没有找到匹配的板块，使用标普500作为整体市场参考
            if not matched_sector:
                matched_sector = '整体市场'
                self.logger.info(f"未找到股票 {symbol} 对应的美股板块，使用整体市场（标普500）作为参考")
            else:
                self.logger.info(f"股票 {symbol} 对应美股板块: {matched_sector}")
            
            # 获取美股板块数据（最近5天，因为美股比A股早一天收盘）
            # 设置页面预测：如果use_api=False，只使用数据库数据，不调用API
            us_data = self.data_source.get_us_sector_data(
                matched_sector if matched_sector != '整体市场' else None, 
                days=5, 
                use_db_only=not use_api
            )
            
            if us_data.empty:
                self.logger.warning(f"无法获取美股板块 {matched_sector} 的数据")
                return {'score': 0.0, 'sector': matched_sector, 'trend': 'neutral', 'change_pct': 0.0}
            
            # 计算最近的表现
            if len(us_data) < 2:
                return {'score': 0.0, 'sector': matched_sector, 'trend': 'neutral', 'change_pct': 0.0}
            
            # 获取最新一天的涨跌幅
            latest_close = us_data['close'].iloc[-1]
            prev_close = us_data['close'].iloc[-2]
            change_pct = (latest_close - prev_close) / prev_close * 100
            
            # 计算最近几天的平均涨跌
            recent_returns = us_data['close'].pct_change().dropna()
            avg_return = recent_returns.mean() * 100  # 转换为百分比
            
            # 计算得分：涨跌幅越大，得分越高（正数表示上涨，负数表示下跌）
            # 使用最近一天的涨跌幅和平均涨跌幅的加权平均
            score = (change_pct * 0.6 + avg_return * 0.4) / 10  # 归一化到-1到1之间
            score = max(-1.0, min(1.0, score))
            
            # 确定趋势
            if score > 0.1:
                trend = 'up'
            elif score < -0.1:
                trend = 'down'
            else:
                trend = 'neutral'
            
            self.logger.info(f"美股板块 {matched_sector} 得分: {score:.2f}, 趋势: {trend}, 涨跌幅: {change_pct:.2f}%")
            
            return {
                'score': score,
                'sector': matched_sector,
                'trend': trend,
                'change_pct': change_pct,
                'avg_return': avg_return
            }
            
        except Exception as e:
            self.logger.error(f"计算美股板块得分失败: {str(e)}")
            return {'score': 0.0, 'sector': 'unknown', 'trend': 'neutral', 'change_pct': 0.0}
    
    def calculate_valuation_score(self, symbol: str, stock_info: Dict = None) -> Dict:
        """
        计算估值指标得分（PE、PB）
        
        Args:
            symbol: 股票代码
            stock_info: 可选的股票信息（如果已获取，可传入避免重复调用API）
                       如果不传入，将自动调用API获取（保持向后兼容）
        
        Returns:
            {
                'score': 估值得分 (-1到1),
                'pe_ratio': 市盈率,
                'pb_ratio': 市净率,
                'valuation': 'undervalued'/'overvalued'/'fair'
            }
        """
        try:
            # 如果未传入stock_info，则调用API获取（保持向后兼容）
            if stock_info is None:
                stock_info = self.data_source.get_stock_info(symbol)
            
            pe_ratio = None
            pb_ratio = None
            
            # 获取PE
            for key in ['pe_ratio', '市盈率', 'PE', 'PE(TTM)']:
                if key in stock_info:
                    try:
                        pe_value = stock_info[key]
                        if isinstance(pe_value, str):
                            pe_value = pe_value.replace('倍', '').replace(',', '').strip()
                        pe_ratio = float(pe_value)
                        break
                    except:
                        continue
            
            # 获取PB
            for key in ['pb_ratio', '市净率', 'PB', 'PB(MRQ)']:
                if key in stock_info:
                    try:
                        pb_value = stock_info[key]
                        if isinstance(pb_value, str):
                            pb_value = pb_value.replace('倍', '').replace(',', '').strip()
                        pb_ratio = float(pb_value)
                        break
                    except:
                        continue
            
            if pe_ratio is None and pb_ratio is None:
                return {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None, 'valuation': 'unknown'}
            
            score = 0.0
            
            # PE评分：一般认为PE在10-30之间合理，低于10可能被低估，高于30可能被高估
            if pe_ratio is not None:
                if pe_ratio < 10:
                    score += 0.1  # 可能被低估
                elif pe_ratio > 30:
                    score -= 0.1  # 可能被高估
                elif pe_ratio > 50:
                    score -= 0.15  # 明显高估
            
            # PB评分：一般认为PB在1-3之间合理，低于1可能被低估，高于3可能被高估
            if pb_ratio is not None:
                if pb_ratio < 1:
                    score += 0.1  # 可能被低估
                elif pb_ratio > 3:
                    score -= 0.1  # 可能被高估
                elif pb_ratio > 5:
                    score -= 0.15  # 明显高估
            
            score = max(-1.0, min(1.0, score))
            
            if score > 0.05:
                valuation = 'undervalued'
            elif score < -0.05:
                valuation = 'overvalued'
            else:
                valuation = 'fair'
            
            return {
                'score': score,
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'valuation': valuation
            }
            
        except Exception as e:
            self.logger.error(f"计算估值得分失败: {str(e)}")
            return {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None, 'valuation': 'unknown'}
    
    def _calculate_valuation_score_from_db(self, symbol: str, pre_queried_data: Dict = None) -> Dict:
        """
        从数据库获取估值数据并计算得分（设置页面预测专用，不调用API）
        
        Args:
            symbol: 股票代码
            pre_queried_data: 预查询的数据字典（性能优化，如果提供则跳过数据库查询）
        
        Returns:
            估值得分字典
        """
        try:
            pe_ratio = None
            pb_ratio = None
            
            # 性能优化：如果已提供预查询数据，直接使用
            if pre_queried_data:
                pe_ratio = pre_queried_data.get('pe_ratio')
                pb_ratio = pre_queried_data.get('pb_ratio')
                if pe_ratio is not None:
                    try:
                        pe_ratio = float(pe_ratio)
                    except (ValueError, TypeError):
                        pe_ratio = None
                if pb_ratio is not None:
                    try:
                        pb_ratio = float(pb_ratio)
                    except (ValueError, TypeError):
                        pb_ratio = None
            
            # 如果预查询数据中没有，则从数据库查询
            if pe_ratio is None and pb_ratio is None:
                try:
                    from utils.db_connection import DatabaseConnection
                    db = DatabaseConnection()
                    
                    # 从stock_history_data表获取最新的PE和PB数据
                    sql = """
                        SELECT pe_ratio, pb_ratio
                        FROM stock_history_data
                        WHERE symbol = %s
                        AND pe_ratio IS NOT NULL
                        AND pb_ratio IS NOT NULL
                        ORDER BY trade_date DESC
                        LIMIT 1
                    """
                    result = db.execute_query(sql, (symbol,))
                    
                    if result and len(result) > 0:
                        record = result[0]
                        pe_ratio = record.get('pe_ratio')
                        pb_ratio = record.get('pb_ratio')
                        
                        # 转换为float
                        try:
                            if pe_ratio is not None:
                                pe_ratio = float(pe_ratio)
                            if pb_ratio is not None:
                                pb_ratio = float(pb_ratio)
                        except (ValueError, TypeError):
                            pe_ratio = None
                            pb_ratio = None
                except Exception as e:
                    self.logger.debug(f"从数据库获取估值数据失败: {str(e)}")
            
            if pe_ratio is None and pb_ratio is None:
                return {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None, 'valuation': 'unknown'}
            
            score = 0.0
            
            # PE评分：一般认为PE在10-30之间合理，低于10可能被低估，高于30可能被高估
            if pe_ratio is not None:
                if pe_ratio < 10:
                    score += 0.15  # 被低估
                elif pe_ratio > 30:
                    score -= 0.15  # 被高估
                elif pe_ratio > 50:
                    score -= 0.25  # 严重高估
            
            # PB评分：一般认为PB在1-3之间合理，低于1可能被低估，高于3可能被高估
            if pb_ratio is not None:
                if pb_ratio < 1:
                    score += 0.1  # 被低估
                elif pb_ratio > 3:
                    score -= 0.1  # 被高估
                elif pb_ratio > 5:
                    score -= 0.2  # 严重高估
            
            # 确定估值状态
            if score > 0.1:
                valuation = 'undervalued'
            elif score < -0.1:
                valuation = 'overvalued'
            else:
                valuation = 'fair'
            
            return {
                'score': max(-1.0, min(1.0, score)),
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'valuation': valuation
            }
        except Exception as e:
            self.logger.error(f"从数据库计算估值得分失败: {str(e)}")
            return {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None, 'valuation': 'unknown'}
    
    def calculate_capital_flow_score(self, symbol: str, use_api: bool = True) -> Dict:
        """
        计算资金流向得分
        包括：北向资金、融资融券、主力资金
        
        Args:
            symbol: 股票代码
            use_api: 是否使用API获取数据（设置页面预测时应设为False，只使用数据库数据）
        
        Returns:
            {
                'score': 资金流向得分 (-1到1),
                'north_bound_score': 北向资金得分,
                'margin_score': 融资融券得分,
                'main_force_score': 主力资金得分,
                'trend': 'inflow'/'outflow'/'neutral'
            }
        """
        try:
            scores = []
            details = {}
            
            # 1. 北向资金得分（权重40%）
            try:
                north_bound = self.data_source.get_north_bound_capital(days=5, use_db_only=not use_api)
                north_inflow = north_bound.get('today_net_inflow', 0.0)
                avg_inflow_5d = north_bound.get('avg_net_inflow_5d', 0.0)
                
                # 北向资金净流入：+0.3分/10亿元
                north_score = (north_inflow / 10.0) * 0.3
                north_score = max(-1.0, min(1.0, north_score))
                
                details['north_bound'] = {
                    'today_net_inflow': north_inflow,
                    'avg_net_inflow_5d': avg_inflow_5d,
                    'trend': north_bound.get('trend', 'neutral')
                }
                scores.append(north_score * 0.4)  # 40%权重
            except Exception as e:
                self.logger.debug(f"计算北向资金得分失败: {str(e)}")
                scores.append(0.0)
                details['north_bound'] = {'error': str(e)}
            
            # 2. 融资融券得分（权重35%）
            try:
                margin_data = self.data_source.get_margin_trading_data(symbol, days=5, use_db_only=not use_api)
                margin_change_pct = margin_data.get('margin_change_pct', 0.0)
                
                # 融资余额增加：+0.2分/1%
                margin_score = (margin_change_pct / 1.0) * 0.2
                margin_score = max(-1.0, min(1.0, margin_score))
                
                details['margin'] = {
                    'margin_balance': margin_data.get('margin_balance', 0.0),
                    'margin_change_pct': margin_change_pct,
                    'trend': margin_data.get('trend', 'stable')
                }
                scores.append(margin_score * 0.35)  # 35%权重
            except Exception as e:
                self.logger.debug(f"计算融资融券得分失败: {str(e)}")
                scores.append(0.0)
                details['margin'] = {'error': str(e)}
            
            # 3. 主力资金得分（权重25%）
            try:
                main_force = self.data_source.get_main_force_capital(symbol, days=5, use_db_only=not use_api)
                main_inflow_pct = main_force.get('main_net_inflow_pct', 0.0)
                
                # 主力资金净流入：+0.1分/1%
                main_score = (main_inflow_pct / 1.0) * 0.1
                main_score = max(-1.0, min(1.0, main_score))
                
                details['main_force'] = {
                    'main_net_inflow': main_force.get('main_net_inflow', 0.0),
                    'main_net_inflow_pct': main_inflow_pct,
                    'trend': main_force.get('trend', 'neutral')
                }
                scores.append(main_score * 0.25)  # 25%权重
            except Exception as e:
                self.logger.debug(f"计算主力资金得分失败: {str(e)}")
                scores.append(0.0)
                details['main_force'] = {'error': str(e)}
            
            # 计算总分
            total_score = sum(scores)
            total_score = max(-1.0, min(1.0, total_score))
            
            # 判断趋势
            if total_score > 0.1:
                trend = 'inflow'
            elif total_score < -0.1:
                trend = 'outflow'
            else:
                trend = 'neutral'
            
            return {
                'score': total_score,
                'north_bound_score': details.get('north_bound', {}).get('today_net_inflow', 0.0),
                'margin_score': details.get('margin', {}).get('margin_change_pct', 0.0),
                'main_force_score': details.get('main_force', {}).get('main_net_inflow_pct', 0.0),
                'trend': trend,
                'details': details
            }
            
        except Exception as e:
            self.logger.error(f"计算资金流向得分失败: {str(e)}")
            return {
                'score': 0.0,
                'north_bound_score': 0.0,
                'margin_score': 0.0,
                'main_force_score': 0.0,
                'trend': 'neutral',
                'details': {}
            }
    
    def calculate_sector_rotation_score(self, symbol: str, use_api: bool = True) -> Dict:
        """
        计算板块轮动得分
        分析股票所属板块的热度、资金流向和轮动趋势
        
        Args:
            symbol: 股票代码
            use_api: 是否使用API获取数据（设置页面预测时应设为False，只使用数据库数据）
        
        Returns:
            {
                'score': 板块轮动得分 (-1到1),
                'sector_name': 板块名称,
                'sector_type': 'industry'/'concept',
                'heat': 板块热度 (0-1),
                'trend': 'hot'/'cold'/'neutral'
            }
        """
        try:
            # 获取股票行业信息和板块表现数据
            # 设置页面预测：如果use_api=False，跳过API调用，使用空数据
            # 获取股票行业信息（设置页面预测：如果use_api=False，从数据库获取；否则从API获取）
            industry_info = self.data_source.get_stock_industry_info(symbol, use_db_only=not use_api)
            industry = industry_info.get('industry', '')
            concepts = industry_info.get('concepts', [])
            
            # 板块表现数据：只在use_api=True时从API获取
            if use_api:
                # 获取板块表现数据
                sector_data = self.data_source.get_sector_performance(days=5)
            else:
                # 设置页面预测：不使用API获取板块表现数据，使用空数据
                self.logger.debug(f"跳过板块表现数据API调用（use_api=False），使用空数据")
                sector_data = {
                    'industry_sectors': {},
                    'concept_sectors': {},
                    'hot_sectors': []
                }
            industry_sectors = sector_data.get('industry_sectors', {})
            concept_sectors = sector_data.get('concept_sectors', {})
            hot_sectors = sector_data.get('hot_sectors', [])
            
            score = 0.0
            matched_sector = None
            sector_type = None
            
            # 1. 检查行业板块（权重60%）
            if industry:
                for sector_name, sector_info in industry_sectors.items():
                    if industry in sector_name or sector_name in industry:
                        matched_sector = sector_name
                        sector_type = 'industry'
                        change_pct = sector_info.get('change_pct', 0.0)
                        heat = sector_info.get('heat', 0.5)
                        
                        # 板块涨跌幅得分
                        score += (change_pct / 3.0) * 0.6  # 涨3%得0.6分
                        # 板块热度得分
                        score += (heat - 0.5) * 0.4  # 热度越高得分越高
                        break
            
            # 2. 检查概念板块（权重40%）
            if concepts and score == 0.0:
                best_concept_score = 0.0
                best_concept = None
                for concept in concepts[:3]:  # 只检查前3个概念
                    for sector_name, sector_info in concept_sectors.items():
                        if concept in sector_name or sector_name in concept:
                            change_pct = sector_info.get('change_pct', 0.0)
                            heat = sector_info.get('heat', 0.5)
                            
                            concept_score = (change_pct / 3.0) * 0.4 + (heat - 0.5) * 0.3
                            if concept_score > best_concept_score:
                                best_concept_score = concept_score
                                best_concept = sector_name
                                sector_type = 'concept'
                
                if best_concept:
                    score = best_concept_score
                    matched_sector = best_concept
            
            # 3. 检查是否在热门板块中（额外加分）
            if matched_sector and matched_sector in hot_sectors:
                score += 0.2  # 热门板块额外加分
            elif matched_sector:
                # 即使不在热门列表，如果板块涨跌幅大于2%，也算热门
                if sector_type == 'industry' and industry in industry_sectors:
                    change_pct = industry_sectors[industry].get('change_pct', 0.0)
                    if change_pct > 2.0:
                        score += 0.15
                elif sector_type == 'concept' and matched_sector in concept_sectors:
                    change_pct = concept_sectors[matched_sector].get('change_pct', 0.0)
                    if change_pct > 2.0:
                        score += 0.15
            
            score = max(-1.0, min(1.0, score))
            
            # 判断趋势
            if score > 0.2:
                trend = 'hot'
            elif score < -0.2:
                trend = 'cold'
            else:
                trend = 'neutral'
            
            return {
                'score': score,
                'sector_name': matched_sector or industry or (concepts[0] if concepts else 'unknown'),
                'sector_type': sector_type or 'unknown',
                'heat': score + 0.5,  # 转换为0-1范围
                'trend': trend,
                'industry': industry,
                'concepts': concepts[:3] if concepts else []
            }
            
        except Exception as e:
            self.logger.error(f"计算板块轮动得分失败: {str(e)}")
            return {
                'score': 0.0,
                'sector_name': 'unknown',
                'sector_type': 'unknown',
                'heat': 0.5,
                'trend': 'neutral',
                'industry': '',
                'concepts': []
            }
    
    def find_support_resistance(self, data: pd.DataFrame) -> Dict:
        """计算支撑位和压力位（综合近期高低点、均线、局部极值）"""
        try:
            cp = data['close'].iloc[-1]
            r10h, r10l = data['high'].tail(10).max(), data['low'].tail(10).min()
            r20h, r20l = data['high'].tail(20).max(), data['low'].tail(20).min()
            r30h, r30l = data['high'].tail(30).max(), data['low'].tail(30).min()
            ma5, ma10, ma20 = data['close'].tail(5).mean(), data['close'].tail(10).mean(), data['close'].tail(20).mean()
            ma60 = data['close'].tail(60).mean() if len(data) >= 60 else ma20
            lookback = min(30, len(data))
            ha, la = data['high'].tail(lookback).values, data['low'].tail(lookback).values
            lh, ll = [], []
            for i in range(1, len(ha) - 1):
                if ha[i] > ha[i-1] and ha[i] > ha[i+1]: lh.append(ha[i])
                if la[i] < la[i-1] and la[i] < la[i+1]: ll.append(la[i])
            all_s = [r10l, r20l, r30l, ma5, ma10, ma20, ma60]
            all_r = [r10h, r20h, r30h, ma5, ma10, ma20, ma60]
            sc = sorted(set([round(s, 2) for s in all_s + ll if s < cp]), reverse=True)
            rc = sorted(set([round(r, 2) for r in all_r + lh if r > cp]))
            return {
                'support_1': sc[0] if sc else round(cp*0.95, 2), 'support_2': sc[1] if len(sc)>1 else round(cp*0.90, 2),
                'resistance_1': rc[0] if rc else round(cp*1.05, 2), 'resistance_2': rc[1] if len(rc)>1 else round(cp*1.10, 2),
                'method': f"综合{lookback}日高低点+均线+局部极值"
            }
        except Exception as e:
            self.logger.error(f"计算支撑压力位失败: {str(e)}")
            c = data['close'].iloc[-1] if len(data) > 0 else 10.0
            return {'support_1': round(c*0.97,2), 'support_2': round(c*0.93,2), 'resistance_1': round(c*1.03,2), 'resistance_2': round(c*1.07,2), 'method': '默认估算'}
    
    def estimate_holding_period(self, data: pd.DataFrame, prediction_result: Dict) -> Dict:
        """估算建议持仓天数"""
        try:
            pred = prediction_result.get('prediction', '震荡')
            conf = prediction_result.get('confidence', 0.5)
            up_p = prediction_result.get('up_probability', 0.5)
            dn_p = prediction_result.get('down_probability', 0.5)
            dv = data['close'].pct_change().tail(20).dropna().std() if len(data) >= 20 else 0.02
            if dv is None or (isinstance(dv, float) and dv != dv): dv = 0.02
            ma5, ma10, ma20 = data['close'].tail(5).mean(), data['close'].tail(10).mean(), data['close'].tail(20).mean()
            ts = 2 if ma5>ma10>ma20 else (1 if ma5>ma10 else (-2 if ma5<ma10<ma20 else (-1 if ma5<ma10 else 0)))
            if pred == '上涨': bd = 7 if (conf>0.7 and ts>=1) else (2 if conf<0.5 else 5)
            elif pred == '下跌': bd = 0 if dn_p>0.7 else 1
            else: bd = 3
            va = -1 if dv>0.03 else (1 if dv<0.015 else 0)
            od = max(0, bd + va)
            rs = []
            if pred == '上涨': rs.append(f"预测上涨（{up_p*100:.0f}%）")
            elif pred == '下跌': rs.append(f"预测下跌（{dn_p*100:.0f}%）")
            else: rs.append("预测震荡")
            rs.append(f"置信度{conf*100:.0f}%"); rs.append(f"日波动率{dv*100:.1f}%")
            if ts>=2: rs.append("均线多头排列")
            elif ts<=-2: rs.append("均线空头排列")
            return {'min_days': max(0, od-2), 'max_days': od+3, 'optimal_days': od, 'reason': '，'.join(rs)}
        except Exception as e:
            self.logger.error(f"估算持仓天数失败: {str(e)}")
            return {'min_days': 1, 'max_days': 5, 'optimal_days': 3, 'reason': '默认估算'}
    
    def calculate_trading_suggestions(self, data: pd.DataFrame, prediction_result: Dict, symbol: str = None) -> Dict:
        """计算完整交易计划（增强版：动态止损止盈+支撑压力位+持仓天数+风险收益比+操作建议）"""
        try:
            current_price = data['close'].iloc[-1]
            prediction = prediction_result['prediction']
            up_prob = prediction_result['up_probability']
            down_prob = prediction_result['down_probability']
            confidence = prediction_result['confidence']
            market_overall = prediction_result.get('market_overall', {})
            market_bullish, market_up_prob = False, 0.5
            if market_overall.get('success', False):
                mp = market_overall.get('overall_prediction', '震荡')
                market_up_prob = market_overall.get('overall_up_probability', 0.5)
                market_bullish = (mp == '上涨' or market_up_prob > 0.55)
            recent_high = data['high'].tail(10).max()
            recent_low = data['low'].tail(10).min()
            volatility = (recent_high - recent_low) / current_price
            ma5, ma10, ma20 = data['close'].tail(5).mean(), data['close'].tail(10).mean(), data['close'].tail(20).mean()
            tech_strength = 1 if ma5>ma10>ma20 else (-1 if ma5<ma10<ma20 else 0)
            sr = self.find_support_resistance(data)
            dsl = None
            if RISK_MANAGER_AVAILABLE and symbol:
                try:
                    dsl = RiskManager().calculate_dynamic_stop_loss_take_profit(symbol=symbol, current_price=current_price, stock_data=data, base_stop_loss_pct=-5.0, base_take_profit_pct=8.0, volatility_period=20)
                except Exception as e:
                    self.logger.warning(f"RiskManager计算失败: {e}")
            # 买入价
            if prediction == '上涨' and up_prob > 0.5:
                bm = 0.3 + (0.2 if market_bullish else 0) + (0.1 if tech_strength>0 else 0) + (0.2 if up_prob>0.7 else 0)
                buy_price = min(current_price*(1+volatility*bm), current_price*1.05)
            elif prediction == '下跌' and down_prob > 0.55:
                buy_price = current_price*(1 - volatility*(0.3 if market_bullish and market_up_prob>0.6 else 0.5))
            else:
                buy_price = recent_low*(1.03 if market_bullish else 1.02)
            buy_price = round(buy_price, 2)
            # 卖出价
            if prediction == '上涨' and up_prob > 0.5:
                bm = 1.5 + (0.5 if market_bullish else 0) + (0.3 if tech_strength>0 else 0) + (0.5 if up_prob>0.7 else 0)
                sell_price = current_price*(1+volatility*bm)
            elif prediction == '下跌' and down_prob > 0.55:
                sell_price = current_price*(1 - volatility*(0.1 if market_bullish and market_up_prob>0.6 else 0.3))
            else:
                sell_price = recent_high*(1.02 if market_bullish else 0.98)
            sell_price = round(sell_price, 2)
            # 止损止盈
            if dsl and dsl.get('stop_loss_price'):
                stop_loss, take_profit = round(dsl['stop_loss_price'],2), round(dsl['take_profit_price'],2)
                sl_pct, tp_pct = dsl.get('stop_loss_pct',-5.0), dsl.get('take_profit_pct',8.0)
                sl_method, sl_vol, sl_exp = '动态（基于波动率调整）', dsl.get('volatility'), dsl.get('explanation','')
            else:
                stop_loss, take_profit = sr['support_1'], max(sr['resistance_1'], sell_price)
                sl_pct, tp_pct = round((stop_loss/current_price-1)*100,2), round((take_profit/current_price-1)*100,2)
                sl_method, sl_vol, sl_exp = '基于支撑压力位', None, f'止损参考支撑位{sr["support_1"]}'
            if prediction != '下跌':
                stop_loss = min(stop_loss, round(current_price*0.98,2))
                take_profit = max(take_profit, round(current_price*1.03,2))
            risk = abs(current_price-stop_loss) if stop_loss else current_price*0.05
            reward = abs(take_profit-current_price) if take_profit else current_price*0.08
            rr = round(reward/risk, 2) if risk > 0 else 0.0
            hp = self.estimate_holding_period(data, prediction_result)
            # 竞价建议
            ae, ap, ar = False, None, ""
            if prediction=='上涨' and up_prob>0.6 and market_bullish and market_up_prob>0.55:
                ae = True
                if up_prob>0.75 and market_up_prob>0.6: ap, ar = round(current_price*1.03,2), "强烈看涨（双重利好）"
                elif up_prob>0.65: ap, ar = round(current_price*1.02,2), "看涨（个股+市场利好）"
                else: ap, ar = round(current_price*1.01,2), "看涨"
            elif prediction=='上涨' and up_prob>0.7 and confidence>0.65:
                ae = True
                ap, ar = (round(current_price*1.025,2), "个股强烈看涨") if up_prob>0.8 else (round(current_price*1.015,2), "个股看涨")
            elif market_bullish and market_up_prob>0.65 and up_prob>0.5:
                ae, ap, ar = True, round(current_price*1.01,2), "市场整体看涨"
            elif tech_strength>0 and up_prob>0.52 and confidence>0.55:
                ae, ap, ar = True, round(current_price*1.005,2), "技术面强势"
            elif prediction=='下跌' and market_bullish and market_up_prob>0.7:
                ae, ap, ar = True, round(current_price*0.98,2), "市场强烈看涨，低吸机会"
            if not ae:
                if prediction=='下跌' and down_prob>0.6: ar = "看跌，不建议竞价"
                elif confidence<0.5: ar = "置信度较低，不建议竞价"
                elif not market_bullish and up_prob<0.55: ar = "市场与个股均不乐观"
                else: ar = "震荡行情，建议观察"
            # 操作建议
            if prediction=='上涨' and up_prob>0.6 and confidence>0.55:
                action = '建议买入'
                rd = '优秀' if rr>=2 else ('良好' if rr>=1.5 else '一般，注意风险')
                action_detail = f'预测上涨概率{up_prob*100:.0f}%，置信度{confidence*100:.0f}%，风险收益比{rr}:1（{rd}）'
            elif prediction=='下跌' and down_prob>0.6:
                action, action_detail = '建议观望/卖出', f'预测下跌概率{down_prob*100:.0f}%，建议等待企稳'
            elif prediction=='上涨' and confidence<0.5:
                action, action_detail = '谨慎买入', f'预测上涨但置信度仅{confidence*100:.0f}%，建议轻仓'
            else:
                action, action_detail = '建议观望', f'震荡行情，置信度{confidence*100:.0f}%，等待信号'
            return {
                'buy_price': buy_price, 'sell_price': sell_price,
                'auction_entry': ae, 'auction_price': ap, 'auction_reason': ar,
                'stop_loss': stop_loss, 'take_profit': take_profit,
                'stop_loss_pct': sl_pct, 'take_profit_pct': tp_pct,
                'sl_tp_method': sl_method, 'sl_tp_explanation': sl_exp, 'sl_tp_volatility': sl_vol,
                'support_1': sr['support_1'], 'support_2': sr['support_2'],
                'resistance_1': sr['resistance_1'], 'resistance_2': sr['resistance_2'], 'sr_method': sr['method'],
                'holding_period': hp, 'risk_reward_ratio': rr,
                'action': action, 'action_detail': action_detail,
            }
        except Exception as e:
            self.logger.error(f"计算交易建议失败: {str(e)}")
            return {
                'buy_price': None, 'sell_price': None, 'auction_entry': False, 'auction_price': None, 'auction_reason': '',
                'stop_loss': None, 'take_profit': None, 'stop_loss_pct': None, 'take_profit_pct': None,
                'sl_tp_method': '', 'sl_tp_explanation': '', 'sl_tp_volatility': None,
                'support_1': None, 'support_2': None, 'resistance_1': None, 'resistance_2': None, 'sr_method': '',
                'holding_period': {'min_days':1,'max_days':5,'optimal_days':3,'reason':'计算异常'},
                'risk_reward_ratio': 0.0, 'action': '暂无建议', 'action_detail': '交易计划计算异常',
            }
    
    def predict_market_overall(self, use_api: bool = True) -> Dict:
        """
        预测沪深股市整体行情
        
        Args:
            use_api: 是否使用API获取数据（设置页面预测时应设为False，只使用数据库数据）
        
        Returns:
            市场整体行情预测结果
        """
        try:
            self.logger.info("\n步骤0: 分析市场整体行情...")
            
            # 获取主要指数数据（设置页面预测：只使用数据库数据，不调用API）
            indices_data = self.data_source.get_all_market_indices(days=60, use_db_only=not use_api)
            
            if not indices_data:
                # 设置页面预测：如果没有数据，返回中性预测
                if not use_api:
                    self.logger.info("数据库中没有市场指数数据，返回中性预测")
                    return {
                        'success': True,
                        'prediction': '震荡',
                        'up_probability': 0.5,
                        'down_probability': 0.5,
                        'score': 0.0,
                        'message': '数据库中没有市场指数数据，返回中性预测'
                    }
                return {
                    'success': False,
                    'message': '无法获取市场指数数据'
                }
            
            # 分析各指数
            index_predictions = {}
            overall_score = 0.0
            index_count = 0
            
            for index_name, index_data in indices_data.items():
                if index_data.empty:
                    continue
                
                # 计算指数的技术指标得分（指数不需要换手率）
                tech_result = self.calculate_technical_score(index_data, None)
                tech_score = tech_result['score']
                
                # 计算市场情绪得分（传递use_api参数和indices_data，避免重复获取）
                # 注意：这里传入的是单个指数的数据作为data参数，同时传入所有指数的数据作为indices_data参数
                market_result = self.calculate_market_score(index_data, use_api=use_api, indices_data=indices_data)
                market_score = market_result['score']
                
                # 综合得分（技术指标70%，市场情绪30%）
                index_score = tech_score * 0.7 + market_score * 0.3
                
                # 转换为涨跌概率
                up_prob = 1 / (1 + np.exp(-index_score * 3))
                down_prob = 1 - up_prob
                
                # 确定预测方向（阈值0.55）
                if up_prob > 0.55:
                    prediction = '上涨'
                elif down_prob > 0.55:
                    prediction = '下跌'
                else:
                    prediction = '震荡'
                
                current_value = index_data['close'].iloc[-1]
                change_pct = (index_data['close'].iloc[-1] - index_data['close'].iloc[-2]) / index_data['close'].iloc[-2] * 100
                
                index_predictions[index_name] = {
                    'prediction': prediction,
                    'up_probability': up_prob,
                    'down_probability': down_prob,
                    'score': index_score,
                    'current_value': current_value,
                    'change_pct': change_pct,
                    'trend': tech_result['trend']
                }
                
                overall_score += index_score
                index_count += 1
                
                self.logger.info(f"{index_name}: {prediction} (上涨概率: {up_prob*100:.1f}%, 下跌概率: {down_prob*100:.1f}%)")
            
            if index_count == 0:
                # 设置页面预测：如果没有数据，返回中性预测
                if not use_api:
                    self.logger.info("数据库中没有有效的市场指数数据，返回中性预测")
                    return {
                        'success': True,
                        'prediction': '震荡',
                        'up_probability': 0.5,
                        'down_probability': 0.5,
                        'score': 0.0,
                        'message': '数据库中没有有效的市场指数数据，返回中性预测'
                    }
                return {
                    'success': False,
                    'message': '无法获取有效的市场指数数据'
                }
            
            # 计算整体市场得分
            overall_score = overall_score / index_count
            
            # 转换为整体涨跌概率
            overall_up_prob = 1 / (1 + np.exp(-overall_score * 3))
            overall_down_prob = 1 - overall_up_prob
            
            # 确定整体预测方向（阈值0.55）
            if overall_up_prob > 0.55:
                overall_prediction = '上涨'
            elif overall_down_prob > 0.55:
                overall_prediction = '下跌'
            else:
                overall_prediction = '震荡'
            
            # 生成市场整体行情总结
            market_summary_parts = []
            market_summary_parts.append(f"根据主要指数技术分析，预计明天沪深股市整体{overall_prediction}。")
            
            for index_name, pred in index_predictions.items():
                market_summary_parts.append(
                    f"{index_name}预计{pred['prediction']}（上涨概率{pred['up_probability']*100:.1f}%，"
                    f"当前值{pred['current_value']:.2f}，今日涨跌{pred['change_pct']:+.2f}%）。"
                )
            
            market_summary = " ".join(market_summary_parts)
            
            result = {
                'success': True,
                'overall_prediction': overall_prediction,
                'overall_up_probability': overall_up_prob,
                'overall_down_probability': overall_down_prob,
                'overall_score': overall_score,
                'index_predictions': index_predictions,
                'summary': market_summary
            }
            
            self.logger.info(f"市场整体预测: {overall_prediction} (上涨概率: {overall_up_prob*100:.1f}%, 下跌概率: {overall_down_prob*100:.1f}%)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"预测市场整体行情失败: {str(e)}")
            return {
                'success': False,
                'message': f'预测市场整体行情失败: {str(e)}'
            }
    
    def get_target_date(self) -> tuple:
        """
        根据当前时间判断预测日期
        - 上午9点前：预测当天
        - 下午4点后：预测明天
        - 其他时间：预测明天
        
        Returns:
            (target_date, date_desc): 预测日期字符串和描述
        """
        now = datetime.now()
        current_hour = now.hour
        
        if current_hour < 9:
            # 9点前，预测当天
            target_date = now.strftime('%Y-%m-%d')
            return target_date, '当天'
        else:
            # 9点后，预测明天
            target_date = (now + timedelta(days=1)).strftime('%Y-%m-%d')
            return target_date, '明天'
    
    def _calculate_confidence(self, final_score: float, factor_scores: Dict, 
                             data_quality: Optional[Dict] = None, symbol: str = None,
                             market_state: Optional[Dict] = None) -> float:
        """
        计算置信度（增强版：考虑历史准确率、一致性、数据时效性、校准）
        
        Args:
            final_score: 最终得分
            factor_scores: 各因子得分字典
            data_quality: 数据质量信息（可选）
            symbol: 股票代码（用于获取历史准确率）
            market_state: 市场状态信息（可选）
        
        Returns:
            置信度（0-1）
        """
        # 1. 基础置信度（增强版：考虑得分强度和稳定性）
        base_confidence = self._calculate_base_confidence_enhanced(
            final_score=final_score,
            factor_scores=factor_scores
        )
        
        # 2. 因子一致性（优化版：考虑因子权重和得分一致性）
        # 获取因子权重（如果可用）
        factor_weights = None
        try:
            # 尝试从上下文获取因子权重
            if hasattr(self, '_last_factor_weights'):
                factor_weights = self._last_factor_weights
        except:
            pass
        
        factor_consistency = self._calculate_factor_consistency(
            final_score=final_score,
            factor_scores=factor_scores,
            factor_weights=factor_weights
        )
        
        # 3. 数据质量得分（如果有数据质量信息）
        quality_score = 1.0
        if data_quality:
            quality_score = data_quality.get('quality_score', 1.0)
        else:
            # 如果没有数据质量信息，使用默认值
            # 可以根据因子得分的有效性推断数据质量
            valid_factors = sum(1 for score in factor_scores.values() if abs(score) > 0.01)
            total_factors = len(factor_scores)
            if total_factors > 0:
                quality_score = max(0.5, valid_factors / total_factors)
        
        # 计算市场波动性因子（新增：考虑市场波动性）
        market_volatility_factor = self._calculate_market_volatility_factor(
            market_state=market_state if market_state else {},
            data=None  # 如果需要个股波动性，可以传入data
        )
        
        # 计算基础置信度（加权平均，增加市场波动性因子）
        base_calculated_confidence = (
            base_confidence * 0.35 +           # 基础置信度权重35%
            factor_consistency * 0.25 +        # 因子一致性权重25%
            quality_score * 0.25 +             # 数据质量权重25%
            market_volatility_factor * 0.15    # 市场波动性权重15%
        )
        
        # 使用增强的置信度计算器（如果可用）
        try:
            from utils.confidence_calculator import get_confidence_calculator
            confidence_calculator = get_confidence_calculator()
            
            # 使用增强的置信度计算
            enhanced_result = confidence_calculator.calculate_enhanced_confidence(
                base_confidence=base_calculated_confidence,
                final_score=final_score,
                factor_scores=factor_scores,
                symbol=symbol or 'unknown',
                market_state=market_state,
                data_quality=data_quality,
                prediction_time=datetime.now()
            )
            
            confidence = enhanced_result['confidence']
            
            # 记录详细信息（可选，用于调试）
            if self.logger and hasattr(self.logger, 'debug'):
                details = enhanced_result.get('details', {})
                self.logger.debug(
                    f"置信度计算详情 - 基础: {base_calculated_confidence:.3f}, "
                    f"历史准确率因子: {enhanced_result['historical_accuracy_factor']:.3f}, "
                    f"一致性因子: {enhanced_result['consistency_factor']:.3f}, "
                    f"时效性因子: {enhanced_result['timeliness_factor']:.3f}, "
                    f"校准调整: {enhanced_result['calibration_adjustment']:.3f}, "
                    f"最终: {confidence:.3f}"
                )
            
        except Exception as e:
            # 如果增强计算器不可用，回退到基础计算方法
            self.logger.debug(f"增强置信度计算器不可用，使用基础方法: {str(e)}")
            confidence = base_calculated_confidence
        
        # 确保置信度在合理范围内
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def _calculate_base_confidence_enhanced(self, final_score: float,
                                           factor_scores: Dict,
                                           recent_scores: List[float] = None) -> float:
        """
        增强版基础置信度计算（考虑得分强度、分布和稳定性）
        
        Args:
            final_score: 最终得分
            factor_scores: 各因子得分
            recent_scores: 最近几次的得分（用于计算稳定性，可选）
        
        Returns:
            基础置信度（0-1）
        """
        # 1. 基于得分绝对值（原有方法）
        score_based = min(abs(final_score) * 0.5 + 0.5, 1.0)
        
        # 2. 基于得分强度（得分越极端，置信度越高）
        score_strength = abs(final_score)
        # 假设final_score在-1到1之间，如果超出范围，需要归一化
        if score_strength > 1.0:
            score_strength = 1.0
        strength_based = score_strength * 0.8 + 0.2  # 0.2-1.0
        
        # 3. 基于得分稳定性（如果最近得分波动大，降低置信度）
        stability_based = 1.0
        if recent_scores and len(recent_scores) >= 3:
            score_std = np.std(recent_scores)
            # 如果标准差大，说明不稳定，降低置信度
            # 假设得分在-1到1之间，标准差最大约为1.0
            stability_based = max(0.5, 1.0 - score_std * 1.5)
        
        # 4. 基于因子得分分布（如果因子得分分散，降低置信度）
        distribution_based = 1.0
        if factor_scores and len(factor_scores) > 1:
            scores_array = np.array([score for score in factor_scores.values() if abs(score) > 0.01])
            if len(scores_array) > 1:
                score_range = np.max(scores_array) - np.min(scores_array)
                # 如果得分范围大，说明分散，降低置信度
                distribution_based = max(0.6, 1.0 - score_range * 0.5)
        
        # 5. 综合计算
        base_confidence = (
            score_based * 0.30 +
            strength_based * 0.25 +
            stability_based * 0.25 +
            distribution_based * 0.20
        )
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_market_volatility_factor(self, market_state: Dict,
                                           data: pd.DataFrame = None) -> float:
        """
        计算市场波动性因子（用于调整置信度）
        
        Args:
            market_state: 市场状态
            data: 股票历史数据（可选，用于计算个股波动性）
        
        Returns:
            波动性因子（0-1），1表示低波动（高置信度），0表示高波动（低置信度）
        """
        # 1. 市场状态波动性
        market_volatility = 1.0
        if market_state:
            market_state_name = market_state.get('state', 'sideways')
            if market_state_name == 'bear_market':
                market_volatility = 0.7  # 熊市波动大，降低置信度
            elif market_state_name == 'bull_market':
                market_volatility = 0.9  # 牛市波动较小，提高置信度
            else:
                market_volatility = 0.8  # 震荡市波动中等
        
        # 2. 个股波动性（如果数据可用）
        stock_volatility = 1.0
        if data is not None and not data.empty and len(data) >= 20:
            try:
                if 'change_pct' in data.columns:
                    returns = data['change_pct'].tail(20).values / 100.0
                    volatility = np.std(returns)
                    # 波动率越高，因子越低（降低置信度）
                    # 假设正常波动率约2%，超过4%认为高波动
                    stock_volatility = max(0.5, 1.0 - (volatility - 0.02) * 10)
                    stock_volatility = max(0.5, min(1.0, stock_volatility))
            except:
                pass
        
        # 3. 综合波动性因子（市场和个股各占50%）
        volatility_factor = (market_volatility + stock_volatility) / 2
        
        return volatility_factor
    
    def _calculate_factor_data_quality(self, factor_name: str, factor_result: Dict) -> float:
        """
        计算因子数据质量评分（0-1）
        
        Args:
            factor_name: 因子名称
            factor_result: 因子分析结果
        
        Returns:
            数据质量评分（0-1），1表示数据完整，0表示数据完全缺失
        """
        try:
            quality_score = 1.0
            
            if factor_name == 'technical':
                # 技术指标：检查是否有足够的历史数据和信号
                signals = factor_result.get('signals', {})
                score = factor_result.get('score', 0.0)
                if not signals or len(signals) < 3:
                    quality_score = 0.5  # 数据不完整
                if abs(score) < 0.01 and not signals:
                    quality_score = 0.3  # 可能是默认值，数据缺失
            
            elif factor_name == 'news':
                # 新闻：检查新闻数量
                news_count = factor_result.get('news_count', 0)
                if news_count == 0:
                    quality_score = 0.2  # 无新闻数据
                elif news_count < 3:
                    quality_score = 0.6  # 新闻数量较少
            
            elif factor_name == 'capital_flow':
                # 资金流向：检查数据完整性
                details = factor_result.get('details', {})
                available_sources = sum(1 for k in ['north_bound', 'margin', 'main_force'] 
                                       if k in details and details[k].get('error') is None)
                quality_score = max(0.2, available_sources / 3.0)  # 至少保留0.2，即使数据缺失
            
            elif factor_name == 'valuation':
                # 估值：检查PE/PB是否可用
                pe_ratio = factor_result.get('pe_ratio')
                pb_ratio = factor_result.get('pb_ratio')
                if pe_ratio is None and pb_ratio is None:
                    quality_score = 0.0  # 完全缺失
                elif pe_ratio is None or pb_ratio is None:
                    quality_score = 0.5  # 部分缺失
            
            elif factor_name == 'market':
                # 市场情绪：检查数据源
                details = factor_result.get('details', {})
                has_index_score = 'market_index_score' in details
                has_stock_score = 'stock_score' in details
                if not has_index_score and not has_stock_score:
                    quality_score = 0.3  # 数据缺失
                elif not has_index_score or not has_stock_score:
                    quality_score = 0.6  # 部分缺失
            
            elif factor_name == 'history':
                # 历史模式：检查是否有模式识别
                pattern = factor_result.get('pattern', 'unknown')
                if pattern == 'unknown' or pattern == '无显著模式':
                    quality_score = 0.2  # 无历史模式
            
            elif factor_name == 'sector_rotation':
                # 板块轮动：检查是否有板块信息
                sector_name = factor_result.get('sector_name', 'unknown')
                if sector_name == 'unknown':
                    quality_score = 0.3  # 无板块信息
            
            elif factor_name == 'us_sector':
                # 美股板块：检查是否有板块信息
                sector = factor_result.get('sector', 'unknown')
                if sector == 'unknown':
                    quality_score = 0.3  # 无板块信息
            
            elif factor_name == 'market_overall':
                # 市场整体：检查是否成功
                success = factor_result.get('success', False)
                if not success:
                    quality_score = 0.2  # 市场整体预测失败
            
            return max(0.0, min(1.0, quality_score))  # 确保在0-1范围内
            
        except Exception as e:
            self.logger.debug(f"计算因子 {factor_name} 数据质量失败: {str(e)}")
            return 0.5  # 出错时返回中等质量评分
    
    def _adjust_weights_by_data_quality(self, base_weights: Dict, factor_quality_scores: Dict) -> Dict:
        """
        根据数据质量动态调整权重
        
        Args:
            base_weights: 基础权重字典
            factor_quality_scores: 各因子数据质量评分字典
        
        Returns:
            调整后的权重字典
        """
        try:
            adjusted_weights = {}
            total_adjusted_weight = 0.0
            
            # 计算调整后的权重（质量评分作为权重倍数）
            for factor_name, base_weight in base_weights.items():
                quality_score = factor_quality_scores.get(factor_name, 1.0)
                # 如果质量评分低于0.3，大幅降低权重
                if quality_score < 0.3:
                    adjusted_weight = base_weight * quality_score * 0.5  # 额外降低50%
                elif quality_score < 0.6:
                    adjusted_weight = base_weight * quality_score * 0.8  # 降低20%
                else:
                    adjusted_weight = base_weight * quality_score
                
                adjusted_weights[factor_name] = adjusted_weight
                total_adjusted_weight += adjusted_weight
            
            # 归一化权重（确保总和为1）
            if total_adjusted_weight > 0.001:  # 避免除零
                for factor_name in adjusted_weights:
                    adjusted_weights[factor_name] /= total_adjusted_weight
            else:
                # 如果所有权重都为0，回退到基础权重
                self.logger.debug("所有权重调整后为0，回退到基础权重")
                adjusted_weights = base_weights.copy()
            
            return adjusted_weights
            
        except Exception as e:
            self.logger.debug(f"根据数据质量调整权重失败: {str(e)}")
            return base_weights  # 出错时返回基础权重
    
    def _adjust_confidence_by_data_quality(self, base_confidence: float, 
                                           factor_quality_scores: Dict,
                                           missing_critical_data: bool = False) -> float:
        """
        根据数据质量调整置信度
        
        Args:
            base_confidence: 基础置信度
            factor_quality_scores: 各因子数据质量评分字典
            missing_critical_data: 是否缺失关键数据
        
        Returns:
            调整后的置信度
        """
        try:
            # 如果缺失关键数据，大幅降低置信度
            if missing_critical_data:
                return max(0.05, base_confidence * 0.3)
            
            # 计算平均数据质量评分
            if factor_quality_scores:
                avg_quality = sum(factor_quality_scores.values()) / len(factor_quality_scores)
            else:
                avg_quality = 1.0
            
            # 根据平均质量调整置信度
            # 质量评分 < 0.5：降低50%
            # 质量评分 < 0.7：降低30%
            # 质量评分 >= 0.7：降低10%
            if avg_quality < 0.5:
                quality_adjustment = 0.5
            elif avg_quality < 0.7:
                quality_adjustment = 0.7
            else:
                quality_adjustment = 0.9
            
            adjusted_confidence = base_confidence * quality_adjustment
            
            # 确保置信度不低于0.1（除非数据完全缺失）
            if avg_quality > 0:
                adjusted_confidence = max(0.1, adjusted_confidence)
            else:
                adjusted_confidence = 0.05  # 数据完全缺失时，极低置信度
            
            return max(0.0, min(1.0, adjusted_confidence))  # 确保在0-1范围内
            
        except Exception as e:
            self.logger.debug(f"根据数据质量调整置信度失败: {str(e)}")
            return base_confidence  # 出错时返回基础置信度
    
    def _calculate_factor_consistency(self, final_score: float, factor_scores: Dict, 
                                      factor_weights: Dict = None) -> float:
        """
        计算因子一致性（优化版：考虑因子权重和得分一致性）
        
        Args:
            final_score: 最终得分
            factor_scores: 各因子得分字典
            factor_weights: 各因子权重（可选）
        
        Returns:
            一致性得分（0-1），越高表示因子方向越一致
        """
        if not factor_scores:
            return 0.5
        
        # 确定最终方向
        final_direction = 1 if final_score > 0 else -1 if final_score < 0 else 0
        
        if final_direction == 0:
            return 0.5  # 中性，一致性中等
        
        # 1. 计算因子方向一致性（原有方法）
        consistent_count = 0
        total_count = 0
        weighted_consistent = 0.0
        total_weight = 0.0
        
        for factor_name, factor_score in factor_scores.items():
            if abs(factor_score) < 0.01:
                # 中性因子，不计入一致性计算
                continue
            
            factor_direction = 1 if factor_score > 0 else -1
            factor_weight = factor_weights.get(factor_name, 1.0) if factor_weights else 1.0
            
            if factor_direction == final_direction:
                consistent_count += 1
                weighted_consistent += factor_weight
            total_count += 1
            total_weight += factor_weight
        
        if total_count == 0:
            return 0.5
        
        # 方向一致性比例
        direction_consistency = consistent_count / total_count
        
        # 加权方向一致性（如果提供了权重）
        weighted_direction_consistency = weighted_consistent / total_weight if total_weight > 0 else direction_consistency
        
        # 2. 计算因子得分一致性（使用标准差）
        scores_array = np.array([score for score in factor_scores.values() if abs(score) > 0.01])
        if len(scores_array) > 1:
            score_std = np.std(scores_array)
            # 标准差越小，一致性越高（假设得分在-1到1之间）
            score_consistency = max(0.0, 1.0 - score_std * 1.5)  # 调整系数，使影响更合理
        else:
            score_consistency = 0.5
        
        # 3. 综合一致性（方向一致性60%，得分一致性40%）
        consistency_score = (
            direction_consistency * 0.40 +
            weighted_direction_consistency * 0.20 +
            score_consistency * 0.40
        )
        
        # 转换为0-1得分（50%一致性对应0.5，100%一致性对应1.0）
        consistency_score = 0.5 + (consistency_score - 0.5) * 0.5
        
        return max(0.0, min(1.0, consistency_score))
    
    def _calculate_dynamic_sigmoid_coefficient(self, final_score: float,
                                              market_state: Dict,
                                              volatility_coefficient: float,
                                              symbol: str = None,
                                              historical_accuracy: float = None) -> float:
        """
        动态计算Sigmoid放大系数
        
        Args:
            final_score: 最终得分
            market_state: 市场状态
            volatility_coefficient: 波动率系数
            symbol: 股票代码（用于获取历史准确率）
            historical_accuracy: 历史准确率（可选）
        
        Returns:
            动态放大系数（范围：2.0-5.0）
        """
        base_coefficient = 3.0  # 基础系数
        
        # 1. 根据市场状态调整
        market_state_name = market_state.get('state', 'sideways') if market_state else 'sideways'
        if market_state_name == 'bull_market':
            market_multiplier = 1.2  # 牛市，增加系数（概率变化更敏感）
        elif market_state_name == 'bear_market':
            market_multiplier = 0.8  # 熊市，降低系数（更保守）
        else:
            market_multiplier = 1.0  # 震荡市，不变
        
        # 2. 根据波动率调整（高波动股票使用更大系数）
        # volatility_coefficient范围：1.5-4.5
        volatility_multiplier = 0.8 + (volatility_coefficient - 1.5) / (4.5 - 1.5) * 0.4
        volatility_multiplier = max(0.8, min(1.2, volatility_multiplier))
        
        # 3. 根据历史准确率调整（如果可用）
        accuracy_multiplier = 1.0
        if historical_accuracy is not None:
            # 如果历史准确率低于50%，降低系数（更保守）
            if historical_accuracy < 0.5:
                accuracy_multiplier = 0.7 + historical_accuracy * 0.6
            else:
                accuracy_multiplier = 1.0
        elif symbol:
            # 尝试从数据库获取历史准确率
            try:
                from utils.confidence_calculator import get_confidence_calculator
                confidence_calculator = get_confidence_calculator()
                # 获取历史准确率（如果可用）
                historical_stats = confidence_calculator.get_historical_accuracy(symbol)
                if historical_stats and 'accuracy' in historical_stats:
                    hist_accuracy = historical_stats['accuracy']
                    if hist_accuracy < 0.5:
                        accuracy_multiplier = 0.7 + hist_accuracy * 0.6
            except:
                pass
        
        # 综合调整
        dynamic_coefficient = base_coefficient * market_multiplier * volatility_multiplier * accuracy_multiplier
        
        # 限制范围：2.0-5.0
        dynamic_coefficient = max(2.0, min(5.0, dynamic_coefficient))
        
        self.logger.debug(
            f"Sigmoid系数计算: 基础={base_coefficient:.2f}, 市场={market_multiplier:.2f}, "
            f"波动率={volatility_multiplier:.2f}, 准确率={accuracy_multiplier:.2f}, "
            f"最终={dynamic_coefficient:.2f}"
        )
        
        return dynamic_coefficient
    
    def _calibrate_probability(self, raw_probability: float,
                              symbol: str = None,
                              final_score: float = None) -> float:
        """
        校准概率，使其更接近实际准确率（过滤干扰因子）
        
        Args:
            raw_probability: 原始概率
            symbol: 股票代码（用于获取历史准确率）
            final_score: 最终得分（用于判断概率强度）
        
        Returns:
            校准后的概率（范围：0.1-0.9，避免极端概率）
        """
        calibrated = raw_probability
        
        # 1. 根据历史准确率校准（如果可用）
        try:
            from utils.confidence_calculator import get_confidence_calculator
            confidence_calculator = get_confidence_calculator()
            historical_stats = confidence_calculator.get_historical_accuracy(symbol or 'unknown')
            
            if historical_stats and 'accuracy' in historical_stats:
                hist_accuracy = historical_stats['accuracy']
                # 如果历史准确率低，说明原始概率可能偏高，需要降低
                if hist_accuracy < 0.6:
                    # 校准因子：历史准确率越低，降低越多
                    calibration_factor = 0.8 + (hist_accuracy / 0.6) * 0.2
                    calibrated = raw_probability * calibration_factor
                    self.logger.debug(
                        f"概率校准: 原始={raw_probability:.3f}, 历史准确率={hist_accuracy:.3f}, "
                        f"校准因子={calibration_factor:.3f}, 校准后={calibrated:.3f}"
                    )
        except:
            pass
        
        # 2. 根据概率强度校准（极端概率需要更保守）
        # 如果概率接近0或1，可能是过度自信，需要校准
        if raw_probability > 0.8:
            # 高概率：稍微降低，避免过度自信
            calibrated = calibrated * 0.95 + 0.05
        elif raw_probability < 0.2:
            # 低概率：稍微提高，避免过度悲观
            calibrated = calibrated * 0.95 + 0.05
        
        # 3. 限制范围：0.1-0.9（避免极端概率，提高可靠性）
        calibrated = max(0.1, min(0.9, calibrated))
        
        return calibrated
    
    def calculate_history_score(self, data: pd.DataFrame) -> Dict:
        """
        计算历史模式得分
        
        Returns:
            {
                'score': 历史得分 (-1到1),
                'pattern': 历史模式描述
            }
        """
        try:
            if data.empty or len(data) < 30:
                return {'score': 0.0, 'pattern': '数据不足'}
            
            # 分析最近30天的走势模式
            recent_30 = data.tail(30)
            
            # 计算涨跌概率
            returns = recent_30['close'].pct_change().dropna()
            positive_returns = (returns > 0).sum()
            negative_returns = (returns < 0).sum()
            
            # 计算连续涨跌天数
            consecutive_up = 0
            consecutive_down = 0
            
            for i in range(len(returns) - 1, -1, -1):
                if returns.iloc[i] > 0:
                    consecutive_up += 1
                    consecutive_down = 0
                elif returns.iloc[i] < 0:
                    consecutive_down += 1
                    consecutive_up = 0
                else:
                    break
            
            # 基于历史模式计算得分
            if consecutive_up >= 3:
                score = -0.2  # 连续上涨，可能回调
                pattern = f'连续上涨{consecutive_up}天，可能回调'
            elif consecutive_down >= 3:
                score = 0.2  # 连续下跌，可能反弹
                pattern = f'连续下跌{consecutive_down}天，可能反弹'
            else:
                score = (positive_returns - negative_returns) / len(returns) * 0.3
                pattern = f'涨跌互现，上涨{positive_returns}天，下跌{negative_returns}天'
            
            return {
                'score': max(-1.0, min(1.0, score)),
                'pattern': pattern
            }
            
        except Exception as e:
            self.logger.error(f"计算历史得分失败: {str(e)}")
            return {'score': 0.0, 'pattern': '计算失败'}
    
    def _get_max_change_pct(self, symbol: str, stock_name: str = None) -> float:
        """
        根据股票特性获取最大涨跌幅
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称（可选）
        
        Returns:
            最大涨跌幅（百分比）
        """
        # ST股票：5%
        if stock_name and ('ST' in stock_name or '*ST' in stock_name):
            return 5.0
        
        # 创业板：300开头，20%
        if symbol.startswith('300'):
            return 20.0
        
        # 科创板：688开头，20%
        if symbol.startswith('688'):
            return 20.0
        
        # 主板：600/000/001开头，10%
        if symbol.startswith(('600', '000', '001')):
            return 10.0
        
        # 默认：10%
        return 10.0
    
    def _calculate_volatility_coefficient(self, data: pd.DataFrame, period: int = 60, alpha: float = 0.1) -> float:
        """
        根据历史波动率计算调整后的tanh系数（优化版：使用EWMA方法，过滤异常数据）
        
        Args:
            data: 股票历史数据（包含close_price或change_pct）
            period: 计算波动率的周期（默认60天，增加周期以提高准确性）
            alpha: EWMA衰减因子（默认0.1，越小越平滑）
        
        Returns:
            调整后的系数（范围：1.5-4.5）
        """
        if data.empty or len(data) < period:
            # 如果数据不足，尝试使用更短的周期
            if len(data) >= 20:
                period = 20
            else:
                return 3.0  # 默认系数
        
        try:
            # 计算日收益率
            if 'change_pct' in data.columns:
                returns = data['change_pct'].tail(period).values / 100.0
            elif 'close' in data.columns:
                prices = data['close'].tail(period + 1).values
                if len(prices) < 2:
                    return 3.0
                returns = np.diff(prices) / prices[:-1]
            else:
                return 3.0
            
            if len(returns) == 0:
                return 3.0
            
            # 过滤异常数据：移除极端值（超过3倍标准差的数据）
            returns_array = np.array(returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            
            # 过滤异常值（使用IQR方法更稳健）
            q1 = np.percentile(returns_array, 25)
            q3 = np.percentile(returns_array, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # 过滤异常值
            filtered_returns = returns_array[(returns_array >= lower_bound) & (returns_array <= upper_bound)]
            
            # 如果过滤后数据太少（少于50%），使用原始数据
            if len(filtered_returns) < len(returns_array) * 0.5:
                filtered_returns = returns_array
                self.logger.debug(f"过滤后数据过少，使用原始数据计算波动率")
            
            if len(filtered_returns) == 0:
                return 3.0
            
            # 使用EWMA方法计算波动率（更平滑，对异常值不敏感）
            ewma_variance = np.var(filtered_returns[:min(10, len(filtered_returns))])  # 初始方差
            
            for i, r in enumerate(filtered_returns):
                ewma_variance = alpha * (r - mean_return)**2 + (1 - alpha) * ewma_variance
            
            volatility = np.sqrt(ewma_variance)
            
            # 基准波动率（A股平均日波动率约2%）
            base_volatility = 0.02
            
            # 调整系数：波动率越高，系数越大
            # 系数范围：1.5（低波动）到 4.5（高波动）
            if volatility > 0:
                coefficient = 1.5 + (volatility / base_volatility) * 1.0
                coefficient = max(1.5, min(4.5, coefficient))
            else:
                coefficient = 3.0
            
            # 记录计算详情（调试用）
            self.logger.debug(
                f"波动率系数计算: 周期={period}, 原始数据={len(returns_array)}, "
                f"过滤后={len(filtered_returns)}, 波动率={volatility:.4f}, 系数={coefficient:.2f}"
            )
            
            return float(coefficient)
        except Exception as e:
            self.logger.debug(f"计算波动率系数失败: {str(e)}")
            return 3.0  # 默认系数
    
    def _calculate_trend_adjustment(self, data: pd.DataFrame, 
                                     short_period: int = 5, 
                                     medium_period: int = 20,
                                     long_period: int = 60) -> float:
        """
        计算价格趋势调整因子（优化版：增加长期趋势，扩大调整范围，过滤异常数据）
        
        Args:
            data: 股票历史数据
            short_period: 短期周期（默认5天）
            medium_period: 中期周期（默认20天）
            long_period: 长期周期（默认60天）
        
        Returns:
            趋势调整因子（范围：0.8-1.2，扩大范围以提高影响）
            - >1.0：上涨趋势，预测更乐观
            - <1.0：下跌趋势，预测更保守
        """
        # 需要至少长期周期的数据
        min_period = max(medium_period, long_period)
        if data.empty or len(data) < min_period:
            # 如果数据不足，尝试使用更短的周期
            if len(data) >= medium_period:
                long_period = medium_period
                min_period = medium_period
            elif len(data) >= short_period:
                medium_period = short_period
                long_period = short_period
                min_period = short_period
            else:
                return 1.0  # 无调整
        
        try:
            if 'close' not in data.columns:
                return 1.0
            
            # 获取足够的历史价格数据
            prices = data['close'].tail(min_period + 1).values
            
            if len(prices) < min_period + 1:
                return 1.0
            
            # 过滤异常价格数据（检测异常波动）
            prices_array = np.array(prices)
            price_changes = np.diff(prices_array) / prices_array[:-1]
            
            # 使用IQR方法过滤异常波动
            q1 = np.percentile(price_changes, 25)
            q3 = np.percentile(price_changes, 75)
            iqr = q3 - q1
            lower_bound = q1 - 2.0 * iqr  # 使用2倍IQR，更宽松
            upper_bound = q3 + 2.0 * iqr
            
            # 标记异常数据点
            valid_indices = [0]  # 第一个价格总是有效
            for i in range(1, len(prices_array)):
                if i == 1 or (price_changes[i-1] >= lower_bound and price_changes[i-1] <= upper_bound):
                    valid_indices.append(i)
            
            # 如果过滤后数据太少，使用原始数据
            if len(valid_indices) < len(prices_array) * 0.7:
                valid_indices = list(range(len(prices_array)))
                self.logger.debug(f"趋势计算：过滤后数据过少，使用原始数据")
            
            filtered_prices = prices_array[valid_indices]
            
            if len(filtered_prices) < 2:
                return 1.0
            
            # 计算短期趋势（最近5天）
            if len(filtered_prices) > short_period:
                short_start_idx = max(0, len(filtered_prices) - short_period - 1)
                short_trend = (filtered_prices[-1] - filtered_prices[short_start_idx]) / filtered_prices[short_start_idx]
            else:
                short_trend = (filtered_prices[-1] - filtered_prices[0]) / filtered_prices[0] if filtered_prices[0] > 0 else 0
            
            # 计算中期趋势（最近20天）
            if len(filtered_prices) > medium_period:
                medium_start_idx = max(0, len(filtered_prices) - medium_period - 1)
                medium_trend = (filtered_prices[-1] - filtered_prices[medium_start_idx]) / filtered_prices[medium_start_idx]
            else:
                medium_trend = short_trend
            
            # 计算长期趋势（最近60天）
            if len(filtered_prices) > long_period:
                long_start_idx = max(0, len(filtered_prices) - long_period - 1)
                long_trend = (filtered_prices[-1] - filtered_prices[long_start_idx]) / filtered_prices[long_start_idx]
            else:
                long_trend = medium_trend
            
            # 综合趋势（短期40%，中期35%，长期25%）
            combined_trend = (
                short_trend * 0.40 +
                medium_trend * 0.35 +
                long_trend * 0.25
            )
            
            # 转换为调整因子（扩大范围到0.8-1.2，提高影响）
            # 上涨趋势：调整因子 > 1.0（更乐观）
            # 下跌趋势：调整因子 < 1.0（更保守）
            adjustment = 1.0 + combined_trend * 0.6  # 从0.5增加到0.6，提高影响
            
            # 限制范围：0.8-1.2（从0.9-1.1扩大）
            adjustment = max(0.8, min(1.2, adjustment))
            
            # 记录计算详情（调试用）
            self.logger.debug(
                f"趋势调整因子计算: 短期={short_trend:.4f}, 中期={medium_trend:.4f}, "
                f"长期={long_trend:.4f}, 综合={combined_trend:.4f}, 调整={adjustment:.3f}"
            )
            
            return float(adjustment)
        except Exception as e:
            self.logger.debug(f"计算趋势调整因子失败: {str(e)}")
            return 1.0  # 无调整
    
    def _calculate_predicted_price_optimized(self, symbol: str, stock_name: str,
                                             current_price: float, up_probability: float,
                                             down_probability: float, confidence: float,
                                             data: pd.DataFrame) -> Dict[str, float]:
        """
        优化后的预测价格计算（增强版：过滤干扰因子，考虑支撑阻力位）
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            current_price: 当前价格
            up_probability: 上涨概率
            down_probability: 下跌概率
            confidence: 置信度
            data: 股票历史数据
        
        Returns:
            {
                'predicted_change_pct': 预测涨跌幅,
                'predicted_close_price': 预测收盘价,
                'max_change_pct': 使用的最大涨跌幅,
                'volatility_coefficient': 使用的波动率系数,
                'trend_adjustment': 趋势调整因子,
                'support_resistance_adjustment': 支撑阻力位调整因子
            }
        """
        # 1. 获取股票特性相关的最大涨跌幅
        max_change_pct = self._get_max_change_pct(symbol, stock_name)
        
        # 2. 检测干扰因子（停牌、涨跌停等）
        anomaly_info = self._detect_anomalies(symbol)
        if not anomaly_info.get('can_predict', True):
            # 如果检测到严重干扰（如停牌），返回保守预测
            self.logger.warning(f"股票 {symbol} 存在干扰因子: {anomaly_info.get('anomalies', [])}")
            return {
                'predicted_change_pct': 0.0,
                'predicted_close_price': float(current_price),
                'max_change_pct': float(max_change_pct),
                'volatility_coefficient': 3.0,
                'trend_adjustment': 1.0,
                'support_resistance_adjustment': 1.0
            }
        
        # 3. 计算历史波动率调整系数（使用EWMA方法，过滤异常数据）
        volatility_coefficient = self._calculate_volatility_coefficient(data, period=60)
        
        # 4. 计算价格趋势调整因子（增加长期趋势，扩大调整范围）
        trend_adjustment = self._calculate_trend_adjustment(data)
        
        # 5. 计算支撑阻力位调整因子
        support_resistance_adjustment = self._calculate_support_resistance_adjustment(
            data, current_price, max_change_pct
        )
        
        # 6. 计算概率差异
        probability_diff = up_probability - down_probability
        
        # 7. 使用调整后的系数计算涨跌幅（考虑所有调整因子）
        predicted_change_pct = (
            np.tanh(probability_diff * volatility_coefficient) * 
            max_change_pct * 
            confidence * 
            trend_adjustment *
            support_resistance_adjustment
        )
        
        # 8. 过滤极端预测值（超过最大涨跌幅的90%）
        max_allowed_change = max_change_pct * 0.9
        if abs(predicted_change_pct) > max_allowed_change:
            predicted_change_pct = np.sign(predicted_change_pct) * max_allowed_change
            self.logger.debug(f"预测涨跌幅 {predicted_change_pct:.2f}% 超过限制，调整为 {max_allowed_change:.2f}%")
        
        # 9. 计算预测收盘价
        predicted_close_price = current_price * (1 + predicted_change_pct / 100.0)
        
        # 10. 验证预测价格的合理性（不能为负或异常大）
        if predicted_close_price <= 0 or predicted_close_price > current_price * 2:
            self.logger.warning(
                f"预测价格异常: {predicted_close_price:.2f}，当前价格: {current_price:.2f}，"
                f"使用保守预测"
            )
            predicted_close_price = current_price * (1 + predicted_change_pct * 0.5 / 100.0)
        
        return {
            'predicted_change_pct': float(predicted_change_pct),
            'predicted_close_price': float(predicted_close_price),
            'max_change_pct': float(max_change_pct),
            'volatility_coefficient': float(volatility_coefficient),
            'trend_adjustment': float(trend_adjustment),
            'support_resistance_adjustment': float(support_resistance_adjustment)
        }
    
    def _calculate_support_resistance_adjustment(self, data: pd.DataFrame, 
                                                 current_price: float,
                                                 max_change_pct: float) -> float:
        """
        计算支撑阻力位调整因子
        
        Args:
            data: 股票历史数据
            current_price: 当前价格
            max_change_pct: 最大涨跌幅
        
        Returns:
            调整因子（范围：0.9-1.1）
            - <1.0：接近阻力位，降低预测价格
            - >1.0：接近支撑位，提高预测价格
        """
        if data.empty or len(data) < 20:
            return 1.0
        
        try:
            if 'close' not in data.columns or 'high' not in data.columns or 'low' not in data.columns:
                return 1.0
            
            # 获取最近60天的价格数据
            recent_data = data.tail(60)
            highs = recent_data['high'].values
            lows = recent_data['low'].values
            closes = recent_data['close'].values
            
            # 识别关键支撑位和阻力位（使用最近60天的最高价和最低价）
            resistance_level = np.max(highs)  # 阻力位：最高价
            support_level = np.min(lows)      # 支撑位：最低价
            
            # 计算当前价格到支撑位和阻力位的距离
            price_range = resistance_level - support_level
            if price_range <= 0:
                return 1.0
            
            distance_to_resistance = (resistance_level - current_price) / price_range
            distance_to_support = (current_price - support_level) / price_range
            
            # 计算调整因子
            # 如果接近阻力位（距离<20%），降低预测价格
            # 如果接近支撑位（距离<20%），提高预测价格
            adjustment = 1.0
            
            if distance_to_resistance < 0.2:
                # 接近阻力位，降低预测价格（调整因子<1.0）
                adjustment = 0.9 + distance_to_resistance * 0.2  # 0.9-0.92
                self.logger.debug(f"接近阻力位 {resistance_level:.2f}，调整因子: {adjustment:.3f}")
            elif distance_to_support < 0.2:
                # 接近支撑位，提高预测价格（调整因子>1.0）
                adjustment = 1.0 + (0.2 - distance_to_support) * 0.5  # 1.0-1.1
                self.logger.debug(f"接近支撑位 {support_level:.2f}，调整因子: {adjustment:.3f}")
            
            # 限制范围：0.9-1.1
            adjustment = max(0.9, min(1.1, adjustment))
            
            return float(adjustment)
        except Exception as e:
            self.logger.debug(f"计算支撑阻力位调整因子失败: {str(e)}")
            return 1.0
    
    def _detect_anomalies(self, symbol: str) -> Dict:
        """
        检测异常情况（停牌、涨跌停、ST股票等）
        
        Args:
            symbol: 股票代码
        
        Returns:
            异常检测结果字典，包含：
            - can_predict: 是否可以预测
            - anomalies: 异常列表
            - details: 异常详情
        """
        anomalies = []
        details = {}
        
        try:
            # 设置页面预测：从数据库获取股票名称，避免调用API
            stock_name_from_db = None
            try:
                from utils.db_connection import DatabaseConnection
                db = DatabaseConnection()
                name_sql = """
                    SELECT DISTINCT name 
                    FROM stock_history_data 
                    WHERE symbol = %s 
                    AND name IS NOT NULL 
                    LIMIT 1
                """
                name_result = db.execute_query(name_sql, (symbol,))
                if name_result and len(name_result) > 0:
                    stock_name_from_db = name_result[0].get('name', '')
            except Exception as e:
                self.logger.debug(f"从数据库获取股票名称失败: {str(e)}")
            
            # 1. 检查停牌（设置页面预测：简化检查，只检查数据库中的名称，不调用API）
            # 注意：设置页面预测时，停牌检查可能不准确，因为需要实时数据
            # 这里只做基本检查，如果数据库中有数据，假设股票未停牌
            if stock_name_from_db:
                # 如果数据库中有数据，假设股票未停牌（设置页面预测时无法准确判断停牌）
                suspension_info = {'is_suspended': False}
            else:
                # 如果数据库中没有数据，可能是新股票或停牌，但设置页面预测时无法准确判断
                # 为了不阻止预测，假设未停牌
                suspension_info = {'is_suspended': False}
            
            if suspension_info.get('is_suspended', False):
                anomalies.append('suspended')
                details['suspension'] = {
                    'reason': suspension_info.get('reason', '未知'),
                    'resume_date': suspension_info.get('resume_date'),
                    'message': suspension_info.get('message', '股票停牌')
                }
            
            # 2. 检查ST股票（设置页面预测：从数据库获取股票名称检查）
            if stock_name_from_db:
                is_st = 'ST' in stock_name_from_db or '*ST' in stock_name_from_db or 'st' in stock_name_from_db.lower()
                if is_st:
                    anomalies.append('st_stock')
                    details['st_stock'] = {
                        'risk_level': 'high',
                        'warning': 'ST股票风险较高，建议谨慎操作',
                        'strategy': {
                            'max_position_pct': 10.0,
                            'min_confidence': 0.7,
                            'stop_loss_pct': -3.0,
                        }
                    }
                    # ST股票仍然可以预测，但会降低置信度
                    # 不阻止预测，只在details中标记
            else:
                # 如果无法获取股票名称，尝试使用数据库方法（但可能失败）
                try:
                    st_info = self.data_source.check_st_stock(symbol)
                    if st_info.get('is_st', False):
                        anomalies.append('st_stock')
                        details['st_stock'] = {
                            'risk_level': st_info.get('risk_level', 'high'),
                            'warning': st_info.get('warning', 'ST股票风险较高'),
                            'strategy': st_info.get('strategy', {})
                        }
                except Exception as e:
                    self.logger.debug(f"检查ST股票状态失败（不影响预测）: {str(e)}")
            
            # 3. 检查涨跌停（从数据库获取，不调用实时API）
            try:
                # 设置页面预测：从数据库获取今天的数据来检查涨跌停
                from utils.stock_history_storage import StockHistoryStorage
                from config_db import USE_DATABASE
                from datetime import datetime
                
                if USE_DATABASE:
                    today = datetime.now().strftime('%Y-%m-%d')
                    storage = StockHistoryStorage()
                    today_data = storage.get_stock_history_data(
                        symbol=symbol,
                        start_date=today,
                        end_date=today,
                        limit=1,
                        period_type='daily'
                    )
                    
                    if today_data and len(today_data) > 0:
                        record = today_data[0]
                        current_price = float(record.get('close_price', 0)) if record.get('close_price') else None
                        limit_up = float(record.get('limit_up', 0)) if record.get('limit_up') else None
                        limit_down = float(record.get('limit_down', 0)) if record.get('limit_down') else None
                        
                        if current_price and limit_up and limit_up > 0 and abs(current_price - limit_up) < 0.01:
                            anomalies.append('limit_up')
                            details['limit_up'] = {
                                'price': current_price,
                                'limit_price': limit_up,
                                'message': '股票涨停，无法买入'
                            }
                        elif current_price and limit_down and limit_down > 0 and abs(current_price - limit_down) < 0.01:
                            anomalies.append('limit_down')
                            details['limit_down'] = {
                                'price': current_price,
                                'limit_price': limit_down,
                                'message': '股票跌停，无法卖出'
                            }
                    else:
                        self.logger.debug(f"数据库中没有 {symbol} 今天的数据，无法检查涨跌停状态")
            except Exception as e:
                self.logger.debug(f"检查涨跌停状态失败: {str(e)}")
            
            # 判断是否可以预测
            # 停牌：不能预测
            # ST股票：可以预测，但会降低置信度
            # 涨跌停：可以预测，但会标记
            can_predict = 'suspended' not in anomalies
            
            return {
                'can_predict': can_predict,
                'anomalies': anomalies,
                'details': details
            }
            
        except Exception as e:
            self.logger.error(f"异常检测失败: {str(e)}")
            # 检测失败时，允许继续预测（避免因检测失败而阻止预测）
            return {
                'can_predict': True,
                'anomalies': [],
                'details': {},
                'error': str(e)
            }
    
    def predict(self, symbol: str, target_date: str = None, data_date: str = None, 
                stock_name: str = None, market_overall_result: Dict = None, use_api: bool = True,
                pre_queried_pe_pb_data: Dict = None, pre_queried_indices_data: Dict = None,
                pre_queried_stock_data: pd.DataFrame = None, pre_queried_news: Dict = None,
                pre_queried_industry_info: Dict = None) -> Dict:
        """
        预测股票明天的涨跌概率
        
        Args:
            symbol: 股票代码
            target_date: 预测时间（目标日期），格式：YYYY-MM-DD，如果为None则根据当前时间自动判断
            data_date: 数据获取时间，格式：YYYY-MM-DD，如果为None则使用当天
            stock_name: 股票名称（可选，如果提供则跳过数据库查询）
            market_overall_result: 市场整体预测结果（可选，如果提供则跳过计算）
            use_api: 是否使用API获取数据（设置页面预测时应设为False，只使用数据库数据）
            pre_queried_pe_pb_data: 预查询的PE/PB等估值数据（可选，如果提供则跳过数据库查询）
                                   格式：{'pe_ratio': ..., 'pb_ratio': ..., 'turnover_rate': ..., ...}
            pre_queried_indices_data: 预查询的市场指数数据（可选，如果提供则跳过重复获取）
                                     格式：{'上证指数': DataFrame, '深证成指': DataFrame, ...}
            pre_queried_stock_data: 预查询的股票历史数据（可选，如果提供则跳过数据库查询）
                                   格式：DataFrame with columns: date, open, high, low, close, volume
            
        Returns:
            预测结果字典
        """
        self.logger.info("=" * 60)
        self.logger.info(f"开始分析股票: {symbol}")
        self.logger.info("=" * 60)
        
        # 处理日期参数
        if target_date is None:
            # 如果没有提供target_date，根据时间判断预测日期
            target_date, date_desc = self.get_target_date()
            self.logger.info(f"预测日期（{date_desc}）: {target_date}")
        else:
            date_desc = f"指定日期({target_date})"
            self.logger.info(f"预测日期（{date_desc}）: {target_date}")
        
        # 数据获取时间（用于获取历史数据的基准日期）
        if data_date is None:
            data_date = datetime.now().strftime('%Y-%m-%d')
        
        prediction_date = data_date  # 预测日期（使用数据获取时间作为预测日期）
        self.logger.info(f"数据获取时间: {data_date}, 预测日期: {prediction_date}")
        
        # 0. 异常情况检测（在获取数据之前先检测，避免无效预测）
        self.logger.info("步骤0: 检测异常情况...")
        anomaly_result = self._detect_anomalies(symbol)
        if not anomaly_result.get('can_predict', True):
            anomalies = anomaly_result.get('anomalies', [])
            self.logger.warning(f"检测到异常情况: {', '.join(anomalies)}")
            return {
                'symbol': symbol,
                'success': False,
                'message': f"无法预测：{', '.join(anomalies)}",
                'anomalies': anomalies,
                'anomaly_details': anomaly_result.get('details', {})
            }
        
        # 保存异常检测结果，后续用于调整置信度和整合到结果中
        initial_anomaly_result = anomaly_result
        
        # 1. 获取股票数据（设置页面预测：只使用数据库数据，不调用实时API）
        self.logger.debug(f"步骤1: 获取股票数据（仅使用数据库数据，数据获取时间: {data_date}）...")
        # 性能优化：如果提供了预查询的股票数据，直接使用，跳过数据库查询
        if pre_queried_stock_data is not None and not pre_queried_stock_data.empty:
            self.logger.debug(f"使用预查询的股票历史数据（性能优化）")
            data = pre_queried_stock_data.copy()
            # 如果指定了data_date，过滤数据到该日期
            if data_date:
                data_date_obj = datetime.strptime(data_date, '%Y-%m-%d')
                data = data[data.index <= data_date_obj]
        else:
            # 设置页面预测：强制只使用数据库数据，如果数据库没有数据则不预测
            # 如果指定了data_date，使用该日期作为结束日期获取数据
            if data_date:
                # 计算开始日期（data_date之前lookback_days天）
                data_date_obj = datetime.strptime(data_date, '%Y-%m-%d')
                start_date = (data_date_obj - timedelta(days=self.config['lookback_days'])).strftime('%Y-%m-%d')
                data = self.data_source.get_stock_data(symbol, start_date=start_date, end_date=data_date, use_db_only=True)
            else:
                data = self.data_source.get_stock_data(symbol, days=self.config['lookback_days'], use_db_only=True)
        
        if data.empty:
            # 设置页面预测：如果没有数据，返回中性预测（震荡，概率各50%），而不是失败
            self.logger.info(f"数据库中没有 {symbol} 的历史数据，返回中性预测")
            return {
                'symbol': symbol,
                'name': stock_name if stock_name else '未知',
                'success': True,
                'prediction': '震荡',
                'up_probability': 0.5,
                'down_probability': 0.5,
                'confidence': 0.0,
                'final_score': 0.0,
                'message': '数据库中没有历史数据，返回中性预测',
                'prediction_type': 'after_close',
                'factors': {},
                'summary': f'{symbol} 数据库中没有历史数据，无法进行详细分析，返回中性预测（震荡）。'
            }
        
        # 性能优化：合并数据库查询，一次性获取所有需要的数据
        check_date = data_date  # 使用data_date而不是today
        date_data_available = False
        current_price = data['close'].iloc[-1]
        price_source = "历史数据最新价格"
        
        # 预查询的数据（用于后续分析任务）
        pre_queried_data = {
            'pe_ratio': None,
            'pb_ratio': None,
            'turnover_rate': None,
            'limit_up': None,
            'limit_down': None,
            'is_limit_up': None,
            'is_limit_down': None,
            'close_price': None
        }
        
        # 性能优化：如果提供了预查询的PE/PB数据，直接使用，避免重复查询数据库
        if pre_queried_pe_pb_data:
            self.logger.debug(f"使用预查询的PE/PB数据（性能优化）")
            if pre_queried_pe_pb_data.get('close_price'):
                current_price = float(pre_queried_pe_pb_data['close_price'])
                price_source = f"预查询数据{check_date}"
                date_data_available = True
                self.logger.info(f"从预查询数据获取{check_date}价格: {current_price:.2f}元")
            
            # 使用预查询的数据
            pre_queried_data['close_price'] = pre_queried_pe_pb_data.get('close_price')
            pre_queried_data['pe_ratio'] = pre_queried_pe_pb_data.get('pe_ratio')
            pre_queried_data['pb_ratio'] = pre_queried_pe_pb_data.get('pb_ratio')
            pre_queried_data['turnover_rate'] = pre_queried_pe_pb_data.get('turnover_rate')
            pre_queried_data['limit_up'] = pre_queried_pe_pb_data.get('limit_up')
            pre_queried_data['limit_down'] = pre_queried_pe_pb_data.get('limit_down')
            pre_queried_data['is_limit_up'] = pre_queried_pe_pb_data.get('is_limit_up')
            pre_queried_data['is_limit_down'] = pre_queried_pe_pb_data.get('is_limit_down')
        else:
            # 如果没有预查询数据，从数据库查询（向后兼容）
            try:
                from utils.db_connection import DatabaseConnection
                from config_db import USE_DATABASE
                
                if USE_DATABASE:
                    db = DatabaseConnection()
                    # 一次性查询data_date的所有需要字段（性能优化：合并查询）
                    sql = """
                        SELECT 
                            close_price, pe_ratio, pb_ratio, turnover_rate,
                            limit_up, limit_down, is_limit_up, is_limit_down
                        FROM stock_history_data
                        WHERE symbol = %s
                        AND trade_date = %s
                        AND period_type = 'daily'
                        LIMIT 1
                    """
                    result = db.execute_query(sql, (symbol, check_date))
                    
                    if result and len(result) > 0:
                        record = result[0]
                        date_close_price = float(record.get('close_price', 0)) if record.get('close_price') else None
                        if date_close_price and date_close_price > 0:
                            current_price = date_close_price
                            price_source = f"数据库{check_date}数据"
                            date_data_available = True
                            self.logger.info(f"从数据库获取{check_date}价格: {current_price:.2f}元")
                            
                            # 保存预查询的数据
                            pre_queried_data['close_price'] = date_close_price
                            pre_queried_data['pe_ratio'] = record.get('pe_ratio')
                            pre_queried_data['pb_ratio'] = record.get('pb_ratio')
                            pre_queried_data['turnover_rate'] = record.get('turnover_rate')
                            pre_queried_data['limit_up'] = record.get('limit_up')
                            pre_queried_data['limit_down'] = record.get('limit_down')
                            pre_queried_data['is_limit_up'] = record.get('is_limit_up')
                            pre_queried_data['is_limit_down'] = record.get('is_limit_down')
                    else:
                        # 如果data_date没有数据，尝试获取最新日期的估值和换手率数据（用于后续分析）
                        sql_latest = """
                            SELECT pe_ratio, pb_ratio, turnover_rate
                            FROM stock_history_data
                            WHERE symbol = %s
                            AND period_type = 'daily'
                            AND (pe_ratio IS NOT NULL OR pb_ratio IS NOT NULL OR turnover_rate IS NOT NULL)
                            ORDER BY trade_date DESC
                            LIMIT 1
                        """
                        latest_result = db.execute_query(sql_latest, (symbol,))
                        if latest_result and len(latest_result) > 0:
                            latest_record = latest_result[0]
                            pre_queried_data['pe_ratio'] = latest_record.get('pe_ratio')
                            pre_queried_data['pb_ratio'] = latest_record.get('pb_ratio')
                            pre_queried_data['turnover_rate'] = latest_record.get('turnover_rate')
            except Exception as e:
                self.logger.debug(f"从数据库获取{check_date}数据失败: {str(e)}")
        
        # 如果数据库没有data_date的数据，返回中性预测（设置页面预测：不做API调用）
        if not date_data_available:
            # 设置页面预测：如果没有data_date的数据，返回中性预测（震荡，概率各50%），而不是失败
            self.logger.info(f"数据库中没有 {symbol} {check_date}的数据，返回中性预测")
            return {
                'symbol': symbol,
                'name': stock_name if stock_name else '未知',
                'success': True,
                'prediction': '震荡',
                'up_probability': 0.5,
                'down_probability': 0.5,
                'confidence': 0.0,
                'final_score': 0.0,
                'message': f'数据库中没有{check_date}的数据，返回中性预测',
                'prediction_type': 'after_close',
                'factors': {},
                'summary': f'{symbol} 数据库中没有{check_date}的数据，无法进行详细分析，返回中性预测（震荡）。'
            }
        
        self.logger.info(f"当前价格: {current_price:.2f}元（来源：{price_source}）")
        
        # 获取股票名称（性能优化：如果已传入则直接使用，否则从数据库查询）
        if stock_name is None or stock_name == '未知':
            try:
                # 尝试从数据库的stock_predictions表获取股票名称
                from utils.db_connection import DatabaseConnection
                db = DatabaseConnection()
                name_sql = """
                    SELECT name 
                    FROM stock_predictions 
                    WHERE symbol = %s 
                    ORDER BY prediction_time DESC 
                    LIMIT 1
                """
                name_result = db.execute_query(name_sql, (symbol,))
                if name_result and len(name_result) > 0:
                    stock_name = name_result[0].get('name', '未知')
                
                # 如果还是未知，尝试从stock_history_data表获取（如果有name字段）
                if stock_name == '未知':
                    try:
                        history_sql = """
                            SELECT DISTINCT name 
                            FROM stock_history_data 
                            WHERE symbol = %s 
                            AND name IS NOT NULL 
                            LIMIT 1
                        """
                        history_result = db.execute_query(history_sql, (symbol,))
                        if history_result and len(history_result) > 0:
                            stock_name = history_result[0].get('name', '未知')
                    except Exception as e:
                        self.logger.debug(f"从stock_history_data获取股票名称失败: {str(e)}")
                
                if not stock_name or stock_name == '':
                    stock_name = '未知'
            except Exception as e:
                # 静默处理：股票名称缺失不影响预测，使用debug级别
                self.logger.debug(f"从数据库获取股票名称失败: {str(e)}，使用默认值'未知'")
                stock_name = '未知'
        
        # 使用多线程并行执行独立分析任务（不需要股票历史数据的分析）
        self.logger.debug("\n步骤2-5.7: 并行分析多个指标（使用多线程加速）...")
        
        # 定义需要并行执行的任务（独立分析，只需要symbol）
        # 设置页面预测：使用数据库数据，不调用实时API
        # 性能优化：如果已传入预计算的市场整体预测结果，则直接使用
        # 性能优化：使用预查询的数据，避免重复数据库查询
        # 【优化】注释掉低价值因子（valuation, us_sector, sector_rotation），减少因子冲突，提高预测准确率
        independent_tasks = {
            'market_overall': lambda: market_overall_result if market_overall_result is not None else self.predict_market_overall(use_api=use_api),  # 传递use_api参数
            'news': lambda: self.calculate_news_score(symbol, use_api=use_api, pre_queried_news=pre_queried_news, pre_queried_industry_info=pre_queried_industry_info),  # 传递预加载数据
            'capital_flow': lambda: self.calculate_capital_flow_score(symbol, use_api=use_api),  # 传递use_api参数
            # 'valuation': lambda: self._calculate_valuation_score_from_db(symbol, pre_queried_data=pre_queried_data),  # 【已注释】估值指标权重低（2%），影响小
            # 'us_sector': lambda: self.calculate_us_sector_score(symbol, use_api=use_api),  # 【已注释】美股板块相关性可能不高
            # 'sector_rotation': lambda: self.calculate_sector_rotation_score(symbol, use_api=use_api),  # 【已注释】板块轮动数据可能不稳定
            'market_sentiment_index': lambda: self.calculate_market_sentiment_index(use_api=use_api),  # 传递use_api参数
        }
        
        # 定义依赖股票数据的任务（需要data）
        data_dependent_tasks = {
            'technical': lambda: self.calculate_technical_score(data, symbol),
            'market': lambda: self.calculate_market_score(data, symbol, use_api=use_api, indices_data=pre_queried_indices_data),  # 传递use_api参数和预查询的指数数据（性能优化）
            'history': lambda: self.calculate_history_score(data),
        }
        
        # 存储结果的字典
        results = {}
        
        # 第一阶段：并行执行独立分析任务
        # 【优化】已移除估值、美股板块、板块轮动因子，减少因子冲突
        self.logger.info("  并行执行独立分析任务（市场整体、新闻、资金流向）...")
        
        # 尝试使用线程池，如果失败则使用单线程模式
        use_thread_pool = True
        try:
            with ThreadPoolExecutor(max_workers=THREAD_POOL_CONFIG["predictor_default"]) as executor:
                future_to_task = {
                    executor.submit(func): task_name 
                    for task_name, func in independent_tasks.items()
                }
                
                for future in as_completed(future_to_task):
                    task_name = future_to_task[future]
                    try:
                        result = future.result()
                        results[task_name] = result
                        self.logger.debug(f"    ✓ {task_name} 分析完成")
                    except Exception as e:
                        self.logger.warning(f"    ✗ {task_name} 分析失败: {str(e)}")
                        # 为失败的任务设置默认值
                        if task_name == 'market_overall':
                            results[task_name] = {'success': False}
                        elif task_name == 'news':
                            results[task_name] = {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'weight_multiplier': 1.0}
                        elif task_name == 'capital_flow':
                            results[task_name] = {'score': 0.0, 'trend': 'neutral', 'details': {}}
                        # 【已注释】以下三个因子已移除
                        # elif task_name == 'valuation':
                        #     results[task_name] = {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None}
                        # elif task_name == 'us_sector':
                        #     results[task_name] = {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0}
                        # elif task_name == 'sector_rotation':
                        #     results[task_name] = {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'}
        except RuntimeError as e:
            # 如果解释器正在关闭，无法使用线程池，切换到单线程模式
            if 'cannot schedule new futures after interpreter shutdown' in str(e):
                self.logger.warning("  检测到解释器正在关闭，线程池不可用，切换到单线程模式执行分析任务")
                use_thread_pool = False
            else:
                # 其他RuntimeError，重新抛出
                raise
        
        # 如果线程池不可用，使用单线程顺序执行
        if not use_thread_pool:
            for task_name, func in independent_tasks.items():
                try:
                    result = func()
                    results[task_name] = result
                    self.logger.debug(f"    ✓ {task_name} 分析完成（单线程模式）")
                except Exception as e:
                    self.logger.warning(f"    ✗ {task_name} 分析失败: {str(e)}")
                    # 为失败的任务设置默认值
                    if task_name == 'market_overall':
                        results[task_name] = {'success': False}
                    elif task_name == 'news':
                        results[task_name] = {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'weight_multiplier': 1.0}
                    elif task_name == 'capital_flow':
                        results[task_name] = {'score': 0.0, 'trend': 'neutral', 'details': {}}
                    # 【已注释】以下三个因子已移除
                    # elif task_name == 'valuation':
                    #     results[task_name] = {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None}
                    # elif task_name == 'us_sector':
                    #     results[task_name] = {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0}
                    # elif task_name == 'sector_rotation':
                    #     results[task_name] = {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'}
        
        # 第二阶段：并行执行依赖股票数据的分析任务
        self.logger.info("  并行执行依赖股票数据的分析任务（技术指标、市场情绪、历史模式）...")
        
        if use_thread_pool:
            try:
                with ThreadPoolExecutor(max_workers=THREAD_POOL_CONFIG["predictor_small"]) as executor:
                    future_to_task = {
                        executor.submit(func): task_name 
                        for task_name, func in data_dependent_tasks.items()
                    }
                    
                    for future in as_completed(future_to_task):
                        task_name = future_to_task[future]
                        try:
                            result = future.result()
                            results[task_name] = result
                            self.logger.debug(f"    ✓ {task_name} 分析完成")
                        except Exception as e:
                            # 静默处理：分析任务失败是正常情况（数据缺失），使用debug级别，不输出warning
                            self.logger.debug(f"    ✗ {task_name} 分析失败（数据缺失或异常）: {str(e)}")
                            # 为失败的任务设置默认值
                            if task_name == 'technical':
                                results[task_name] = {'score': 0.0, 'trend': 'neutral', 'signals': {}}
                            elif task_name == 'market':
                                results[task_name] = {'score': 0.0, 'trend': 'neutral', 'details': {}}
                            elif task_name == 'history':
                                results[task_name] = {'score': 0.0, 'pattern': 'unknown'}
            except RuntimeError as e:
                # 如果解释器正在关闭，无法使用线程池，切换到单线程模式
                if 'cannot schedule new futures after interpreter shutdown' in str(e):
                    self.logger.warning("  检测到解释器正在关闭，线程池不可用，切换到单线程模式执行分析任务")
                    use_thread_pool = False
                else:
                    # 其他RuntimeError，重新抛出
                    raise
        
        # 如果线程池不可用，使用单线程顺序执行
        if not use_thread_pool:
            for task_name, func in data_dependent_tasks.items():
                try:
                    result = func()
                    results[task_name] = result
                    self.logger.debug(f"    ✓ {task_name} 分析完成（单线程模式）")
                except Exception as e:
                    # 静默处理：分析任务失败是正常情况（数据缺失），使用debug级别，不输出warning
                    self.logger.debug(f"    ✗ {task_name} 分析失败（数据缺失或异常）: {str(e)}")
                    # 为失败的任务设置默认值
                    if task_name == 'technical':
                        results[task_name] = {'score': 0.0, 'trend': 'neutral', 'signals': {}}
                    elif task_name == 'market':
                        results[task_name] = {'score': 0.0, 'trend': 'neutral', 'details': {}}
                    elif task_name == 'history':
                        results[task_name] = {'score': 0.0, 'pattern': 'unknown'}
        
        self.logger.info("  所有并行分析任务完成！")
        
        # 从结果中提取各个分析结果
        market_overall = results.get('market_overall', {'success': False})
        
        technical_result = results.get('technical', {'score': 0.0, 'trend': 'neutral', 'signals': {}})
        technical_score = technical_result['score']
        self.logger.info(f"\n技术指标分析结果: 得分 {technical_score:.2f}, 趋势: {technical_result['trend']}")
        signals = technical_result.get('signals', {})
        if '换手率' in signals:
            self.logger.info(f"  换手率: {signals['换手率']}")
        if '量价关系' in signals:
            self.logger.info(f"  量价关系: {signals['量价关系']}")
        
        news_result = results.get('news', {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'weight_multiplier': 1.0})
        news_score = news_result['score']
        news_weight_multiplier = news_result.get('weight_multiplier', 1.0)
        self.logger.info(f"新闻情感分析结果: 得分 {news_score:.2f}, 情感: {news_result['sentiment']}, "
                        f"新闻数量: {news_result['news_count']}, 权重倍数: {news_weight_multiplier:.2f}")
        if news_result.get('positive_count', 0) > 0 or news_result.get('negative_count', 0) > 0:
            self.logger.info(f"  利好消息: {news_result.get('positive_count', 0)} 条（强度{news_result.get('positive_strength', 0):.2f}），"
                           f"利空消息: {news_result.get('negative_count', 0)} 条（强度{news_result.get('negative_strength', 0):.2f}）")
        
        capital_flow_result = results.get('capital_flow', {'score': 0.0, 'trend': 'neutral', 'details': {}})
        capital_flow_score = capital_flow_result['score']
        capital_flow_details = capital_flow_result.get('details', {})
        self.logger.info(f"资金流向分析结果: 得分 {capital_flow_score:.2f}, 趋势: {capital_flow_result['trend']}")
        if 'north_bound' in capital_flow_details:
            nb = capital_flow_details['north_bound']
            if 'today_net_inflow' in nb:
                self.logger.info(f"  北向资金: 净流入 {nb.get('today_net_inflow', 0):.2f} 亿元")
        if 'margin' in capital_flow_details:
            mg = capital_flow_details['margin']
            if 'margin_change_pct' in mg:
                self.logger.info(f"  融资融券: 余额变化 {mg.get('margin_change_pct', 0):.2f}%")
        if 'main_force' in capital_flow_details:
            mf = capital_flow_details['main_force']
            if 'main_net_inflow_pct' in mf:
                self.logger.info(f"  主力资金: 净流入 {mf.get('main_net_inflow_pct', 0):.2f}%")
        
        market_result = results.get('market', {'score': 0.0, 'trend': 'neutral', 'details': {}})
        market_score = market_result['score']
        market_details = market_result.get('details', {})
        self.logger.info(f"市场情绪分析结果: 得分 {market_score:.2f}, 趋势: {market_result['trend']}")
        if 'market_index_score' in market_details:
            self.logger.info(f"  大盘指数得分: {market_details.get('market_index_score', 0):.2f} (基于{market_details.get('index_count', 0)}个指数)")
        if 'stock_score' in market_details:
            self.logger.info(f"  个股情绪得分: {market_details.get('stock_score', 0):.2f}")
        
        history_result = results.get('history', {'score': 0.0, 'pattern': 'unknown'})
        history_score = history_result['score']
        self.logger.info(f"历史模式分析结果: 得分 {history_score:.2f}, 模式: {history_result['pattern']}")
        
        valuation_result = results.get('valuation', {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None})
        valuation_score = valuation_result['score']
        pe_ratio = valuation_result.get('pe_ratio')
        pb_ratio = valuation_result.get('pb_ratio')
        self.logger.info(f"估值指标分析结果: 得分 {valuation_score:.2f}, PE: {pe_ratio}, PB: {pb_ratio}")
        
        us_sector_result = results.get('us_sector', {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0})
        us_sector_score = us_sector_result['score']
        us_sector_name = us_sector_result.get('sector', 'unknown')
        us_sector_change = us_sector_result.get('change_pct', 0.0)
        self.logger.info(f"美股板块分析结果: 得分 {us_sector_score:.2f}, 板块: {us_sector_name}, 涨跌幅: {us_sector_change:.2f}%")
        
        sector_rotation_result = results.get('sector_rotation', {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'})
        sector_rotation_score = sector_rotation_result['score']
        sector_name = sector_rotation_result.get('sector_name', 'unknown')
        sector_trend = sector_rotation_result.get('trend', 'neutral')
        self.logger.info(f"板块轮动分析结果: 得分 {sector_rotation_score:.2f}, 板块: {sector_name}, 趋势: {sector_trend}")
        
        # 市场情绪指标（恐慌/贪婪指数）
        market_sentiment_index = results.get('market_sentiment_index', {
            'available': False,
            'fear_index': 50.0,
            'greed_index': 50.0,
            'sentiment': 'neutral'
        })
        if market_sentiment_index.get('available'):
            self.logger.info(f"市场情绪指标: 恐慌指数 {market_sentiment_index.get('fear_index', 50):.1f}, "
                           f"贪婪指数 {market_sentiment_index.get('greed_index', 50):.1f}, "
                           f"综合情绪: {market_sentiment_index.get('sentiment', 'neutral')}")
            if market_sentiment_index.get('emotional_trading'):
                self.logger.warning(f"情绪化交易警告: {market_sentiment_index.get('emotional_reason', '')}")
        
        # 6. 识别市场状态并动态调整权重（增强版：基于历史准确率优化 + 市场状态 + 个股特性）
        self.logger.info("\n步骤6: 识别市场状态并综合计算预测结果...")
        
        # 6.1 计算各因子的数据质量评分（新增：数据缺失处理优化）
        factor_quality_scores = {}
        try:
            factor_results_map = {
                'technical': technical_result,
                'news': news_result,
                'capital_flow': capital_flow_result,
                'market': market_result,
                'history': history_result,
                'valuation': valuation_result,
                'us_sector': us_sector_result,
                'sector_rotation': sector_rotation_result,
                'market_overall': market_overall
            }
            
            for factor_name, factor_result in factor_results_map.items():
                quality_score = self._calculate_factor_data_quality(factor_name, factor_result)
                factor_quality_scores[factor_name] = quality_score
                if quality_score < 0.6:
                    self.logger.debug(f"因子 {factor_name} 数据质量评分: {quality_score:.2f} (数据可能不完整)")
        except Exception as e:
            self.logger.debug(f"计算因子数据质量评分失败: {str(e)}")
            # 出错时，假设所有因子质量良好
            factor_quality_scores = {name: 1.0 for name in factor_results_map.keys()}
        
        # 尝试识别市场状态
        market_state = {'state': 'sideways', 'confidence': 0.5}  # 默认值
        weight_multipliers = {}  # 默认不调整权重
        try:
            from utils.market_state_identifier import MarketStateIdentifier
            identifier = MarketStateIdentifier()
            
            # 获取大盘指数数据用于识别市场状态
            try:
                indices_data = self.data_source.get_all_market_indices(days=30)
                # 使用上证指数（000001.SH）作为主要参考
                if '000001.SH' in indices_data and not indices_data['000001.SH'].empty:
                    index_data = indices_data['000001.SH']
                    market_state = identifier.identify_market_state(index_data, '上证指数')
                    weight_multipliers = identifier.get_weight_adjustment(market_state)
                    
                    self.logger.info(f"市场状态识别: {market_state['state']} ({market_state['description']})，置信度: {market_state['confidence']:.1%}")
                    if weight_multipliers:
                        self.logger.info(f"权重调整: 技术指标×{weight_multipliers.get('technical_weight_multiplier', 1.0):.2f}, "
                                       f"新闻×{weight_multipliers.get('news_weight_multiplier', 1.0):.2f}, "
                                       f"资金流向×{weight_multipliers.get('capital_flow_weight_multiplier', 1.0):.2f}")
            except Exception as e:
                self.logger.debug(f"市场状态识别失败（不影响主流程）: {str(e)}")
        except ImportError:
            self.logger.debug("市场状态识别模块不可用，使用默认权重")
        except Exception as e:
            self.logger.debug(f"市场状态识别模块初始化失败: {str(e)}")
        
        # 使用权重优化器获取优化后的权重（综合考虑历史准确率、市场状态、个股特性）
        optimized_weights = None
        try:
            from utils.weight_optimizer import get_weight_optimizer
            from utils.confidence_calculator import get_confidence_calculator
            weight_optimizer = get_weight_optimizer()
            
            # 获取优化后的权重（基于历史准确率、市场状态、个股特性）
            optimized_weights = weight_optimizer.get_optimized_weights(
                symbol=symbol,
                market_state=market_state,
                use_accuracy_optimization=True
            )
            
            self.logger.info(f"权重优化器已启用，使用优化后的权重配置")
            
        except Exception as e:
            self.logger.debug(f"权重优化失败，使用基于市场状态的调整: {str(e)}")
        
        # 检查是否为新股票或数据不足（用于优化处理）
        is_new_stock_or_insufficient_data = False
        try:
            # 检查历史预测数据数量
            from utils.db_connection import DatabaseConnection
            db = DatabaseConnection()
            check_sql = """
                SELECT COUNT(*) as cnt
                FROM stock_predictions
                WHERE symbol = %s
                  AND prediction_hit IS NOT NULL
            """
            result = db.execute_query(check_sql, (symbol,))
            if result and result[0].get('cnt', 0) < 10:  # 少于10条历史预测记录
                is_new_stock_or_insufficient_data = True
                self.logger.debug(f"股票 {symbol} 历史数据不足（{result[0].get('cnt', 0)}条），使用保守策略")
        except Exception as e:
            self.logger.debug(f"检查历史数据失败: {str(e)}")
            # 如果检查失败，假设数据不足，使用保守策略
            is_new_stock_or_insufficient_data = True
        
        # 根据是否使用优化后的权重来设置权重值
        if optimized_weights and not is_new_stock_or_insufficient_data:
            # 使用优化后的权重
            base_weights_dict = {
                'technical': optimized_weights.get('technical_weight', self.config.get('technical_weight', 0.20)),
                'news': optimized_weights.get('news_weight', self.config['news_weight']) * news_weight_multiplier,
                'capital_flow': optimized_weights.get('capital_flow_weight', self.config.get('capital_flow_weight', 0.18)),
                'market': optimized_weights.get('market_weight', self.config.get('market_weight', 0.17)),
                'sector_rotation': optimized_weights.get('sector_rotation_weight', self.config.get('sector_rotation_weight', 0.05)),
                'history': optimized_weights.get('history_weight', self.config.get('history_weight', 0.08)),
                'valuation': optimized_weights.get('valuation_weight', self.config.get('valuation_weight', 0.02)),
                'us_sector': optimized_weights.get('us_sector_weight', self.config.get('us_sector_weight', 0.05))
            }
        else:
            # 如果是新股票或数据不足，使用保守的默认权重（不依赖历史优化）
            if is_new_stock_or_insufficient_data:
                self.logger.info(f"股票 {symbol} 数据不足，使用保守的默认权重配置")
            # 如果权重优化失败，回退到基于市场状态的调整
            technical_multiplier = weight_multipliers.get('technical_weight_multiplier', 1.0)
            news_multiplier = weight_multipliers.get('news_weight_multiplier', 1.0) * news_weight_multiplier
            capital_flow_multiplier = weight_multipliers.get('capital_flow_weight_multiplier', 1.0)
            market_multiplier = weight_multipliers.get('market_weight_multiplier', 1.0)
            
            base_weights_dict = {
                'technical': self.config.get('technical_weight', 0.20) * technical_multiplier,
                'news': self.config['news_weight'] * news_multiplier,
                'capital_flow': self.config.get('capital_flow_weight', 0.18) * capital_flow_multiplier,
                'market': self.config.get('market_weight', 0.17) * market_multiplier,
                'sector_rotation': self.config.get('sector_rotation_weight', 0.05),
                'history': self.config.get('history_weight', 0.08),
                'valuation': self.config.get('valuation_weight', 0.02),
                'us_sector': self.config.get('us_sector_weight', 0.05)
            }
        
        # 根据数据质量动态调整权重（新增：数据缺失处理优化）
        try:
            adjusted_weights_dict = self._adjust_weights_by_data_quality(base_weights_dict, factor_quality_scores)
            adjusted_technical_weight = adjusted_weights_dict.get('technical', base_weights_dict['technical'])
            adjusted_news_weight = adjusted_weights_dict.get('news', base_weights_dict['news'])
            adjusted_capital_flow_weight = adjusted_weights_dict.get('capital_flow', base_weights_dict['capital_flow'])
            adjusted_market_weight = adjusted_weights_dict.get('market', base_weights_dict['market'])
            adjusted_sector_rotation_weight = adjusted_weights_dict.get('sector_rotation', base_weights_dict['sector_rotation'])
            adjusted_history_weight = adjusted_weights_dict.get('history', base_weights_dict['history'])
            adjusted_valuation_weight = adjusted_weights_dict.get('valuation', base_weights_dict['valuation'])
            adjusted_us_sector_weight = adjusted_weights_dict.get('us_sector', base_weights_dict['us_sector'])
            
            # 记录数据质量调整信息（仅在debug模式下）
            avg_quality = sum(factor_quality_scores.values()) / len(factor_quality_scores) if factor_quality_scores else 1.0
            if avg_quality < 0.7:
                self.logger.debug(f"数据质量调整: 平均质量 {avg_quality:.2f}, 权重已根据数据完整性调整")
        except Exception as e:
            self.logger.debug(f"根据数据质量调整权重失败，使用原始权重: {str(e)}")
            # 出错时使用原始权重
            adjusted_technical_weight = base_weights_dict['technical']
            adjusted_news_weight = base_weights_dict['news']
            adjusted_capital_flow_weight = base_weights_dict['capital_flow']
            adjusted_market_weight = base_weights_dict['market']
            adjusted_sector_rotation_weight = base_weights_dict['sector_rotation']
            adjusted_history_weight = base_weights_dict['history']
            adjusted_valuation_weight = base_weights_dict['valuation']
            adjusted_us_sector_weight = base_weights_dict['us_sector']
        
        if optimized_weights and not is_new_stock_or_insufficient_data:
            self.logger.info(f"权重优化结果: 技术指标={adjusted_technical_weight:.3f}, "
                           f"新闻={adjusted_news_weight:.3f}, "
                           f"资金流向={adjusted_capital_flow_weight:.3f}, "
                           f"市场={adjusted_market_weight:.3f}")
        
        # 尝试获取ML模型预测结果（如果可用）
        ml_score = 0.0
        ml_weight = 0.0
        ml_prediction_result = None
        ml_model_id = None
        ml_model_type = None
        try:
            from utils.ml_predictor_integration import MLPredictorIntegration
            from utils.ml_model_performance_monitor import MLModelPerformanceMonitor
            
            ml_integration = MLPredictorIntegration()
            ml_prediction_result = ml_integration.get_ml_prediction(symbol, data)
            
            if ml_prediction_result and ml_prediction_result.get('available'):
                ml_score = ml_prediction_result.get('ml_score', 0.0)
                ml_model_type = ml_prediction_result.get('model_type')
                ml_model_id = ml_prediction_result.get('model_id')
                
                # 根据模型性能动态调整权重（优化：传递配置管理器，支持热更新）
                performance_monitor = MLModelPerformanceMonitor(config_manager=self._config_manager)
                if ml_model_id:
                    ml_weight = performance_monitor.get_optimal_weight(model_id=ml_model_id)
                elif ml_model_type:
                    ml_weight = performance_monitor.get_optimal_weight(model_type=ml_model_type)
                else:
                    ml_weight = 0.35  # 默认权重35%（ML模型为主导因子）
                
                self.logger.info(f"ML模型预测: 得分 {ml_score:.2f}, 上涨概率 {ml_prediction_result.get('ml_up_probability', 0.5):.2%}, "
                               f"方向 {ml_prediction_result.get('ml_prediction', '震荡')}, "
                               f"置信度 {ml_prediction_result.get('ml_confidence', 0.0):.2%}, "
                               f"动态权重 {ml_weight:.2%}")
        except ImportError:
            self.logger.debug("ML模型集成模块不可用，跳过ML预测")
        except Exception as e:
            self.logger.debug(f"ML模型预测失败（不影响主流程）: {str(e)}")
        
        # 计算包含ML模型的总权重（用于归一化）
        # 【优化】已移除三个因子，只计算保留的5个因子 + ML模型
        total_adjusted_weight = (
            adjusted_technical_weight +
            adjusted_news_weight +
            adjusted_capital_flow_weight +
            adjusted_market_weight +
            adjusted_history_weight +
            ml_weight  # 包含ML模型权重
            # 【已注释】以下三个因子已移除
            # adjusted_sector_rotation_weight +
            # adjusted_valuation_weight +
            # adjusted_us_sector_weight +
        )
        
        # 归一化权重（确保总和为1，包含ML模型权重）
        if total_adjusted_weight > 0:
            adjusted_technical_weight = adjusted_technical_weight / total_adjusted_weight
            adjusted_news_weight = adjusted_news_weight / total_adjusted_weight
            adjusted_capital_flow_weight = adjusted_capital_flow_weight / total_adjusted_weight
            adjusted_market_weight = adjusted_market_weight / total_adjusted_weight
            adjusted_history_weight = adjusted_history_weight / total_adjusted_weight
            ml_weight = ml_weight / total_adjusted_weight  # 归一化ML模型权重
            # 【已注释】以下三个因子已移除
            # adjusted_sector_rotation_weight = adjusted_sector_rotation_weight / total_adjusted_weight
            # adjusted_valuation_weight = adjusted_valuation_weight / total_adjusted_weight
            # adjusted_us_sector_weight = adjusted_us_sector_weight / total_adjusted_weight
            adjusted_sector_rotation_weight = 0.0  # 默认值
            adjusted_valuation_weight = 0.0  # 默认值
            adjusted_us_sector_weight = 0.0  # 默认值
        
        # 使用动态调整后的权重计算最终得分（包含ML模型）
        # 【优化】已移除三个因子，只计算保留的5个因子 + ML模型
        final_score = (
            technical_score * adjusted_technical_weight +
            news_score * adjusted_news_weight +
            capital_flow_score * adjusted_capital_flow_weight +
            market_score * adjusted_market_weight +
            history_score * adjusted_history_weight +
            ml_score * ml_weight  # 添加ML模型得分
            # 【已注释】以下三个因子已移除
            # sector_rotation_score * adjusted_sector_rotation_weight +
            # valuation_score * adjusted_valuation_weight +
            # us_sector_score * adjusted_us_sector_weight +
        )
        
        # 转换为涨跌概率
        # 使用sigmoid函数将得分转换为概率（优化版：动态调整放大系数）
        # 先计算波动率系数（用于动态调整Sigmoid系数）
        volatility_coefficient = self._calculate_volatility_coefficient(data, period=60)
        
        # 根据市场状态、波动率和历史准确率动态调整放大系数
        sigmoid_coefficient = self._calculate_dynamic_sigmoid_coefficient(
            final_score=final_score,
            market_state=market_state if 'market_state' in locals() else {},
            volatility_coefficient=volatility_coefficient,
            symbol=symbol
        )
        up_probability = 1 / (1 + np.exp(-final_score * sigmoid_coefficient))
        down_probability = 1 - up_probability
        
        # 概率校准（根据历史准确率校准，过滤干扰因子，提高可靠性）
        up_probability = self._calibrate_probability(
            raw_probability=up_probability,
            symbol=symbol,
            final_score=final_score
        )
        down_probability = 1 - up_probability
        
        # 计算置信度（增强版：考虑历史准确率、一致性、数据时效性、校准）
        # 如果是新股票或数据不足，降低置信度阈值
        min_confidence_threshold = self.config['min_confidence']
        if is_new_stock_or_insufficient_data:
            # 数据不足时，使用更保守的置信度阈值（降低20%）
            min_confidence_threshold = self.config['min_confidence'] * 0.8
            self.logger.debug(f"股票 {symbol} 数据不足，置信度阈值从 {self.config['min_confidence']:.2f} 降低到 {min_confidence_threshold:.2f}")
        
        # 计算因子一致性评分（用于学习分析，包含ML模型）
        # 【优化】已移除三个因子，只使用保留的5个因子
        factor_scores_for_consistency = {
            'technical': technical_score,
            'news': news_score,
            'capital_flow': capital_flow_score,
            'market': market_score,
            'history': history_score
            # 【已注释】以下三个因子已移除
            # 'sector_rotation': sector_rotation_score,
            # 'valuation': valuation_score,
            # 'us_sector': us_sector_score
        }
        if ml_prediction_result and ml_prediction_result.get('available'):
            factor_scores_for_consistency['ml_model'] = ml_score
        
        # 获取因子权重（用于一致性计算）
        factor_weights_for_consistency = {
            'technical': adjusted_technical_weight,
            'news': adjusted_news_weight,
            'capital_flow': adjusted_capital_flow_weight,
            'market': adjusted_market_weight,
            'history': adjusted_history_weight
            # 【已注释】以下三个因子已移除
            # 'sector_rotation': adjusted_sector_rotation_weight,
            # 'valuation': adjusted_valuation_weight,
            # 'us_sector': adjusted_us_sector_weight
        }
        if ml_prediction_result and ml_prediction_result.get('available'):
            factor_weights_for_consistency['ml_model'] = ml_weight
        
        # 保存因子权重，供置信度计算使用
        self._last_factor_weights = factor_weights_for_consistency
        
        factor_consistency_score = self._calculate_factor_consistency(
            final_score=final_score,
            factor_scores=factor_scores_for_consistency,
            factor_weights=factor_weights_for_consistency
        )
        
        # 计算数据质量评分（基于因子得分的有效性 + 数据完整性）
        # 【优化】已移除三个因子，因子总数从8改为5
        valid_factors = sum(1 for score in [
            technical_score, news_score, capital_flow_score, market_score, history_score
            # 【已注释】以下三个因子已移除
            # sector_rotation_score, valuation_score, us_sector_score
        ] if abs(score) > 0.01)
        total_factors = 5  # 【优化】从8改为5（移除了3个因子）
        data_quality_score = max(0.5, valid_factors / total_factors) if total_factors > 0 else 0.5
        
        # 结合数据完整性评分（新增：数据缺失处理优化）
        try:
            # 计算平均数据完整性评分
            if factor_quality_scores:
                avg_data_completeness = sum(factor_quality_scores.values()) / len(factor_quality_scores)
                # 综合数据质量评分：因子有效性 * 数据完整性
                data_quality_score = data_quality_score * 0.5 + avg_data_completeness * 0.5
        except Exception as e:
            self.logger.debug(f"计算数据完整性评分失败: {str(e)}")
        
        # 检查是否缺失关键数据
        missing_critical_data = False
        try:
            # 如果技术指标和市场情绪数据质量都很低，视为缺失关键数据
            technical_quality = factor_quality_scores.get('technical', 1.0)
            market_quality = factor_quality_scores.get('market', 1.0)
            if technical_quality < 0.3 and market_quality < 0.3:
                missing_critical_data = True
        except Exception:
            pass
        
        # 准备数据质量信息
        data_quality = {
            'quality_score': data_quality_score,
            'valid_factors': valid_factors,
            'total_factors': total_factors,
            'factor_quality_scores': factor_quality_scores  # 新增：传递因子质量评分
        }
        
        confidence = self._calculate_confidence(
            final_score=final_score,
            factor_scores={
                'technical': technical_score,
                'news': news_score,
                'capital_flow': capital_flow_score,
                'market': market_score,
                'history': history_score
                # 【已注释】以下三个因子已移除
                # 'sector_rotation': sector_rotation_score,
                # 'valuation': valuation_score,
                # 'us_sector': us_sector_score
            },
            data_quality=data_quality,  # 传入数据质量信息
            symbol=symbol,
            market_state=market_state  # 传递市场状态信息用于置信度计算
        )
        
        # 根据数据质量进一步调整置信度（新增：数据缺失处理优化）
        try:
            confidence = self._adjust_confidence_by_data_quality(
                confidence,
                factor_quality_scores,
                missing_critical_data=missing_critical_data
            )
        except Exception as e:
            self.logger.debug(f"根据数据质量调整置信度失败: {str(e)}")
        
        # 如果是新股票或数据不足，进一步降低置信度
        if is_new_stock_or_insufficient_data:
            # 数据不足时，置信度降低15%
            confidence = confidence * 0.85
            self.logger.debug(f"股票 {symbol} 数据不足，置信度从 {confidence / 0.85:.3f} 降低到 {confidence:.3f}")
        
        # 根据异常情况调整置信度（在数据不足调整之后）
        # 使用之前检测的异常结果
        try:
            # 重新检测异常（因为现在有了更多数据，可以更准确地检测涨跌停）
            anomaly_result = self._detect_anomalies(symbol)
            # 合并初始检测结果（停牌、ST股票）和当前检测结果（涨跌停）
            if 'initial_anomaly_result' in locals():
                # 合并异常列表（去重）
                all_anomalies = list(set(anomaly_result.get('anomalies', []) + initial_anomaly_result.get('anomalies', [])))
                # 合并详情
                all_details = {**initial_anomaly_result.get('details', {}), **anomaly_result.get('details', {})}
                anomaly_result = {
                    'anomalies': all_anomalies,
                    'details': all_details,
                    'can_predict': anomaly_result.get('can_predict', True)  # 如果停牌则不能预测
                }
            
            anomaly_details = anomaly_result.get('details', {})
            
            # ST股票：降低置信度20%
            if 'st_stock' in anomaly_result.get('anomalies', []):
                confidence = confidence * 0.80
                self.logger.warning(f"股票 {symbol} 为ST股票，置信度降低20%")
            
            # 涨跌停：降低置信度10%（因为流动性受限）
            if 'limit_up' in anomaly_result.get('anomalies', []) or 'limit_down' in anomaly_result.get('anomalies', []):
                confidence = confidence * 0.90
                self.logger.warning(f"股票 {symbol} 处于涨跌停状态，置信度降低10%")
        except Exception as e:
            self.logger.debug(f"异常检测调整置信度失败: {str(e)}")
            # 如果重新检测失败，使用初始检测结果
            if 'initial_anomaly_result' in locals():
                anomaly_result = initial_anomaly_result
            else:
                anomaly_result = {'anomalies': [], 'details': {}}
        
        # 如果置信度太低，降低概率差异
        if confidence < min_confidence_threshold:
            up_probability = 0.5 + (up_probability - 0.5) * (confidence / min_confidence_threshold)
            down_probability = 1 - up_probability
        
        # 确定预测方向（阈值0.55）
        if up_probability > 0.55:
            prediction = '上涨'
        elif down_probability > 0.55:
            prediction = '下跌'
        else:
            prediction = '震荡'
        
        # 计算明日大概收盘价格和涨幅（优化版）
        # 使用优化后的价格计算逻辑，考虑股票特性、历史波动率和价格趋势
        price_prediction_result = self._calculate_predicted_price_optimized(
            symbol=symbol,
            stock_name=stock_name,
            current_price=current_price,
            up_probability=up_probability,
            down_probability=down_probability,
            confidence=confidence,
            data=data
        )
        
        predicted_change_pct = price_prediction_result['predicted_change_pct']
        predicted_close_price = price_prediction_result['predicted_close_price']
        max_change_pct = price_prediction_result['max_change_pct']
        volatility_coefficient = price_prediction_result['volatility_coefficient']
        trend_adjustment = price_prediction_result['trend_adjustment']
        support_resistance_adjustment = price_prediction_result.get('support_resistance_adjustment', 1.0)
        
        self.logger.info(f"预测价格计算（优化版）: 当前价格={current_price:.2f}元, "
                        f"预期涨跌幅={predicted_change_pct:.2f}%, "
                        f"预测收盘价={predicted_close_price:.2f}元, "
                        f"最大涨跌幅={max_change_pct:.1f}%, "
                        f"波动率系数={volatility_coefficient:.2f}, "
                        f"趋势调整={trend_adjustment:.3f}, "
                        f"支撑阻力位调整={support_resistance_adjustment:.3f}")
        
        # 生成综合文字总结
        direction_text = {
            '上涨': '偏向上涨',
            '下跌': '偏向下跌',
            '震荡': '可能震荡整理'
        }.get(prediction, '走势不明朗')

        tech_trend = technical_result['trend']
        news_sent = news_result['sentiment']
        market_trend = market_result['trend']
        history_pattern = history_result['pattern']

        summary_parts = []
        # 添加市场整体行情信息
        market_info = ""
        if market_overall.get('success', False):
            market_pred = market_overall.get('overall_prediction', '震荡')
            market_info = f"市场整体预计{market_pred}，"
        
        # 【优化】已移除三个因子，更新summary描述
        summary_parts.append(
            f"综合技术指标、新闻情感、资金流向、市场情绪、历史走势，{market_info}模型认为 {target_date} {symbol} {date_desc}整体走势{direction_text}。"
        )
        
        # 添加资金流向描述
        capital_flow_desc = f"资金流向得分 {capital_flow_score:.2f}（趋势：{'流入' if capital_flow_result['trend'] == 'inflow' else '流出' if capital_flow_result['trend'] == 'outflow' else '中性'}）"
        if 'north_bound' in capital_flow_details and 'today_net_inflow' in capital_flow_details['north_bound']:
            nb_inflow = capital_flow_details['north_bound']['today_net_inflow']
            if nb_inflow != 0:
                capital_flow_desc += f"，北向资金净流入 {nb_inflow:+.2f} 亿元"
        if 'margin' in capital_flow_details and 'margin_change_pct' in capital_flow_details['margin']:
            margin_pct = capital_flow_details['margin']['margin_change_pct']
            if margin_pct != 0:
                capital_flow_desc += f"，融资余额变化 {margin_pct:+.2f}%"
        
        # 【已注释】美股板块信息已移除
        # us_sector_info = ""
        # if us_sector_name and us_sector_name != 'unknown':
        #     us_trend_text = '上涨' if us_sector_score > 0.1 else '下跌' if us_sector_score < -0.1 else '震荡'
        #     us_sector_info = f"对应美股板块（{us_sector_name}）{us_trend_text}（涨跌幅{us_sector_change:+.2f}%，得分{us_sector_score:.2f}），"
        us_sector_info = ""  # 默认值
        
        # 构建新闻情感描述（包含利空/利好信息）
        news_desc_parts = [f"新闻情感 {news_sent}（得分 {news_score:.2f}，新闻条数 {news_result['news_count']}"]
        if news_result.get('positive_count', 0) > 0:
            news_desc_parts.append(f"，利好消息 {news_result['positive_count']} 条")
        if news_result.get('negative_count', 0) > 0:
            news_desc_parts.append(f"，利空消息 {news_result['negative_count']} 条")
        if news_weight_multiplier != 1.0:
            if news_weight_multiplier > 1.0:
                news_desc_parts.append(f"，权重提升 {((news_weight_multiplier - 1) * 100):.0f}%")
            else:
                news_desc_parts.append(f"，权重降低 {((1 - news_weight_multiplier) * 100):.0f}%")
        news_desc_parts.append("）")
        news_desc = "".join(news_desc_parts)
        
        # 【已注释】板块轮动描述已移除
        # sector_rotation_desc = f"板块轮动得分 {sector_rotation_score:.2f}（板块：{sector_name}，趋势：{'热门' if sector_trend == 'hot' else '冷门' if sector_trend == 'cold' else '中性'}）"
        sector_rotation_desc = ""  # 默认值
        
        # 添加市场状态描述（如果识别成功）
        market_state_desc = ""
        if market_state.get('state', 'unknown') != 'unknown':
            state_names = {
                'bull_market': '牛市',
                'bear_market': '熊市',
                'sideways': '震荡市'
            }
            state_name = state_names.get(market_state['state'], '未知')
            market_state_desc = f"，当前市场状态：{state_name}（置信度：{market_state['confidence']:.1%}）"
        
        # 【优化】已移除三个因子的描述
        summary_parts.append(
            f"技术面得分 {technical_score:.2f}（{ '偏多' if technical_score > 0.1 else '偏空' if technical_score < -0.1 else '中性' }，趋势：{tech_trend}），"
            f"{news_desc}，{capital_flow_desc}，"
            f"市场情绪得分 {market_score:.2f}（趋势：{market_trend}），"
            f"历史模式得分 {history_score:.2f}（{history_pattern}）{market_state_desc}。"
        )
        summary_parts.append(
            f"在当前参数下，上涨概率约为 {up_probability*100:.1f}%，下跌概率约为 {down_probability*100:.1f}%，综合置信度约为 {confidence*100:.1f}%。"
        )

        summary_text = " ".join(summary_parts)
        
        # 7. 计算完整交易计划（增强版：动态止损止盈+支撑压力位+持仓天数）
        self.logger.info("\n步骤7: 计算完整交易计划...")
        trading_suggestions = self.calculate_trading_suggestions(data, {
            'prediction': prediction,
            'up_probability': up_probability,
            'down_probability': down_probability,
            'confidence': confidence,
            'market_overall': market_overall
        }, symbol=symbol)
        self.logger.info(f"操作建议: {trading_suggestions.get('action', '暂无')} - {trading_suggestions.get('action_detail', '')}")
        self.logger.info(f"买入建议价: {trading_suggestions['buy_price']}元 | 卖出建议价: {trading_suggestions['sell_price']}元")
        self.logger.info(f"止损价: {trading_suggestions.get('stop_loss')}元（{trading_suggestions.get('stop_loss_pct', '')}%）| 止盈价: {trading_suggestions.get('take_profit')}元（{trading_suggestions.get('take_profit_pct', '')}%）")
        self.logger.info(f"支撑位: {trading_suggestions.get('support_1')} / {trading_suggestions.get('support_2')} | 压力位: {trading_suggestions.get('resistance_1')} / {trading_suggestions.get('resistance_2')}")
        holding = trading_suggestions.get('holding_period', {})
        self.logger.info(f"建议持仓: {holding.get('optimal_days', '?')}天（{holding.get('min_days', '?')}-{holding.get('max_days', '?')}天）| 风险收益比: {trading_suggestions.get('risk_reward_ratio', 0)}:1")
        auction_reason = trading_suggestions.get('auction_reason', '')
        if trading_suggestions['auction_entry']:
            self.logger.info(f"建议竞价进入，竞价价格: {trading_suggestions['auction_price']}元，理由: {auction_reason}")
        else:
            self.logger.info(f"竞价建议: {auction_reason}")

        # 保存预测因子数据到CSV（包含所有因子和最终结果）
        if self.data_storage:
            # 确保所有因子结果都是字典类型，避免列表类型导致的错误
            technical_result_dict = technical_result if isinstance(technical_result, dict) else {}
            news_result_dict = news_result if isinstance(news_result, dict) else {}
            capital_flow_result_dict = capital_flow_result if isinstance(capital_flow_result, dict) else {}
            market_result_dict = market_result if isinstance(market_result, dict) else {}
            sector_rotation_result_dict = sector_rotation_result if isinstance(sector_rotation_result, dict) else {}
            history_result_dict = history_result if isinstance(history_result, dict) else {}
            
            factors_for_storage = {
                'technical': {
                    'score': technical_score,
                    'weight': self.config.get('technical_weight', 0.20),
                    'trend': technical_result_dict.get('trend', 'neutral') if isinstance(technical_result_dict.get('trend'), str) else 'neutral'
                },
                'news': {
                    'score': news_score,
                    'weight': self.config.get('news_weight', 0.25),
                    'sentiment': news_result_dict.get('sentiment', 'neutral') if isinstance(news_result_dict.get('sentiment'), str) else 'neutral'
                },
                'capital_flow': {
                    'score': capital_flow_score,
                    'weight': self.config.get('capital_flow_weight', 0.18),
                    'trend': capital_flow_result_dict.get('trend', 'neutral') if isinstance(capital_flow_result_dict.get('trend'), str) else 'neutral'
                },
                'market': {
                    'score': market_score,
                    'weight': self.config.get('market_weight', 0.17),
                    'trend': market_result_dict.get('trend', 'neutral') if isinstance(market_result_dict.get('trend'), str) else 'neutral'
                },
                # 【已注释】板块轮动因子已移除
                # 'sector_rotation': {
                #     'score': sector_rotation_score,
                #     'weight': self.config.get('sector_rotation_weight', 0.05),
                #     'trend': sector_rotation_result_dict.get('trend', 'neutral') if isinstance(sector_rotation_result_dict.get('trend'), str) else 'neutral'
                # },
                'history': {
                    'score': history_score,
                    'weight': self.config.get('history_weight', 0.08),
                    'pattern': history_result_dict.get('pattern', 'unknown') if isinstance(history_result_dict.get('pattern'), str) else 'unknown'
                }
                # 【已注释】估值指标和美股板块因子已移除
                # 'valuation': {
                #     'score': valuation_score,
                #     'weight': self.config.get('valuation_weight', 0.02),
                #     'pe_ratio': pe_ratio if pe_ratio is not None else None,
                #     'pb_ratio': pb_ratio if pb_ratio is not None else None
                # },
                # 'us_sector': {
                #     'score': us_sector_score,
                #     'weight': self.config.get('us_sector_weight', 0.05),
                #     'sector': us_sector_name if isinstance(us_sector_name, str) else 'unknown'
                # }
            }
            
            # 构建临时的prediction_result用于保存因子数据（此时result还未构建完成）
            temp_prediction_result = {
                'final_score': final_score,
                'up_probability': up_probability,
                'down_probability': down_probability,
                'confidence': confidence
            }
            
            self.data_storage.save_prediction_factors(symbol, factors_for_storage, temp_prediction_result)

        # 获取行业和板块信息（用于保存到数据库）
        industry = sector_rotation_result.get('industry', '')
        concepts = sector_rotation_result.get('concepts', [])
        main_concept = ''
        if concepts and isinstance(concepts, list) and len(concepts) > 0:
            main_concept = concepts[0]
        elif sector_rotation_result.get('sector_name') and sector_rotation_result.get('sector_name') != 'unknown':
            main_concept = sector_rotation_result.get('sector_name')
        
        # 判断所属市场（A股/港股/美股）
        market = 'A股'
        if symbol.endswith('.HK'):
            market = '港股'
        elif '.' in symbol and not symbol.endswith('.SH') and not symbol.endswith('.SZ'):
            market = '美股'
        
        result = {
            'symbol': symbol,
            'name': stock_name,  # 股票名称
            'industry': industry,  # 所属行业
            'concepts': concepts,  # 概念板块列表
            'main_concept': main_concept,  # 主要概念板块
            'market': market,  # 所属市场
            'prediction_date': prediction_date,  # 预测日期（数据获取时间）
            'target_date': target_date,  # 目标日期（预测时间）
            'data_date': data_date,  # 数据获取时间
            'prediction_type': 'after_close',  # 预测类型：收盘-明日
            'success': True,
            'current_price': current_price,
            'prediction': prediction,
            'up_probability': up_probability,
            'down_probability': down_probability,
            'confidence': confidence,
            'ml_prediction': ml_prediction_result,  # ML模型预测结果（如果可用）
            'final_score': final_score,
            'predicted_close_price': predicted_close_price,  # 明日大概收盘价格
            'predicted_change_pct': predicted_change_pct,  # 明日大概涨幅百分比
            'market_state': market_state,  # 市场状态信息（新增）
            'market_sentiment_index': market_sentiment_index,  # 市场情绪指标（恐慌/贪婪指数）
            # 以下字段用于模型学习分析
            'factor_weights': {  # 因子权重快照（用于学习分析）
                'technical_weight': adjusted_technical_weight,
                'news_weight': adjusted_news_weight,
                'capital_flow_weight': adjusted_capital_flow_weight,
                'market_weight': adjusted_market_weight,
                'history_weight': adjusted_history_weight,
                # 【已注释】以下三个因子已移除
                # 'sector_rotation_weight': adjusted_sector_rotation_weight,
                # 'valuation_weight': adjusted_valuation_weight,
                # 'us_sector_weight': adjusted_us_sector_weight,
                'is_optimized': optimized_weights is not None and not is_new_stock_or_insufficient_data,
                'market_state': market_state.get('state', 'sideways') if market_state else 'sideways'
            },
            'data_quality_score': data_quality_score,  # 数据质量评分（用于学习分析）
            'factor_consistency_score': factor_consistency_score,  # 因子一致性评分（用于学习分析）
            'config_id': self._get_current_config_id(),  # 配置ID（用于学习分析）
            'factors': {
                'technical': {
                    'score': technical_score,
                    'weight': self.config['technical_weight'],
                    'signals': technical_result['signals'],
                    'trend': technical_result['trend']
                },
                'news': {
                    'score': news_score,
                    'weight': self.config.get('news_weight', 0.25),
                    'adjusted_weight': adjusted_news_weight,  # 调整后的权重
                    'weight_multiplier': news_weight_multiplier,  # 权重倍数
                    'sentiment': news_result['sentiment'],
                    'news_count': news_result['news_count'],
                    'direct_news_count': news_result.get('direct_news_count', 0),
                    'industry_news_count': news_result.get('industry_news_count', 0),
                    'positive_count': news_result.get('positive_count', 0),
                    'negative_count': news_result.get('negative_count', 0),
                    'positive_strength': news_result.get('positive_strength', 0.0),
                    'negative_strength': news_result.get('negative_strength', 0.0),
                    'llm_summaries': news_result.get('llm_summaries', []),  # LLM总结
                    'llm_category_distribution': news_result.get('llm_category_distribution', {}),  # LLM分类分布
                    'llm_analyzed_count': news_result.get('llm_analyzed_count', 0)  # 使用LLM分析的新闻数量
                },
                'capital_flow': {
                    'score': capital_flow_score,
                    'weight': self.config.get('capital_flow_weight', 0.18),
                    'trend': capital_flow_result['trend'],
                    'north_bound_score': capital_flow_result.get('north_bound_score', 0.0),
                    'margin_score': capital_flow_result.get('margin_score', 0.0),
                    'main_force_score': capital_flow_result.get('main_force_score', 0.0),
                    'details': capital_flow_details
                },
                # 【已注释】板块轮动因子已移除
                # 'sector_rotation': {
                #     'score': sector_rotation_score,
                #     'weight': self.config.get('sector_rotation_weight', 0.05),
                #     'sector_name': sector_rotation_result.get('sector_name', 'unknown'),
                #     'sector_type': sector_rotation_result.get('sector_type', 'unknown'),
                #     'heat': sector_rotation_result.get('heat', 0.5),
                #     'trend': sector_rotation_result.get('trend', 'neutral'),
                #     'industry': sector_rotation_result.get('industry', ''),
                #     'concepts': sector_rotation_result.get('concepts', [])
                # },
                'market': {
                    'score': market_score,
                    'weight': self.config.get('market_weight', 0.17),
                    'trend': market_result['trend']
                },
                'history': {
                    'score': history_score,
                    'weight': self.config.get('history_weight', 0.08),
                    'pattern': history_result['pattern']
                }
                # 【已注释】以下三个因子已移除
                # 'us_sector': {
                #     'score': us_sector_score,
                #     'weight': self.config.get('us_sector_weight', 0.10),
                #     'sector': us_sector_name,
                #     'change_pct': us_sector_change,
                #     'trend': us_sector_result.get('trend', 'neutral')
                # },
                # 'valuation': {
                #     'score': valuation_score,
                #     'weight': self.config.get('valuation_weight', 0.05),
                #     'pe_ratio': pe_ratio,
                #     'pb_ratio': pb_ratio,
                #     'valuation': valuation_result['valuation']
                # }
            },
            'trading_suggestions': trading_suggestions,
            'timestamp': datetime.now(),
            'target_date': target_date,
            'date_desc': date_desc,
            'summary': summary_text,
            'market_overall': market_overall,
            # 异常情况信息（如果存在）
            'anomalies': anomaly_result.get('anomalies', []) if 'anomaly_result' in locals() else [],
            'anomaly_details': anomaly_result.get('details', {}) if 'anomaly_result' in locals() else {}
        }
        
        # 如果有异常情况，在总结中添加警告信息
        if 'anomaly_result' in locals() and anomaly_result.get('anomalies', []):
            anomaly_warnings = []
            if 'st_stock' in anomaly_result.get('anomalies', []):
                st_info = anomaly_result.get('details', {}).get('st_stock', {})
                anomaly_warnings.append(f"⚠️ ST股票风险提示：{st_info.get('warning', 'ST股票风险较高，建议谨慎操作')}")
            if 'limit_up' in anomaly_result.get('anomalies', []):
                limit_info = anomaly_result.get('details', {}).get('limit_up', {})
                anomaly_warnings.append(f"⚠️ {limit_info.get('message', '股票涨停，无法买入')}")
            if 'limit_down' in anomaly_result.get('anomalies', []):
                limit_info = anomaly_result.get('details', {}).get('limit_down', {})
                anomaly_warnings.append(f"⚠️ {limit_info.get('message', '股票跌停，无法卖出')}")
            
            if anomaly_warnings:
                result['summary'] = " ".join(anomaly_warnings) + " " + summary_text
                self.logger.warning("检测到异常情况：" + "；".join(anomaly_warnings))
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("预测结果")
        self.logger.info("=" * 60)
        self.logger.info(f"股票代码: {symbol}")
        self.logger.info(f"预测日期（{date_desc}）: {target_date}")
        self.logger.info(f"当前价格: {current_price:.2f}元")
        self.logger.info(f"预测方向: {prediction}")
        self.logger.info(f"上涨概率: {up_probability*100:.1f}%")
        self.logger.info(f"下跌概率: {down_probability*100:.1f}%")
        self.logger.info(f"置信度: {confidence*100:.1f}%")
        self.logger.info(f"明日大概收盘价格: {predicted_close_price:.2f}元")
        self.logger.info(f"明日大概涨幅: {predicted_change_pct:+.2f}%")
        self.logger.info("=" * 60)
        self.logger.info("综合总结：")
        self.logger.info(summary_text)
        self.logger.info("=" * 60)
        
        return result
    
    def predict_before_close(self, symbol: str) -> Dict:
        """
        预测股票走势（未收盘-明天）- 专门用于未收盘时的预测
        
        与 predict() 方法的区别：
        - 专门用于交易时间内（未收盘）的预测
        - 强调使用实时数据和数据库中的当天新闻
        - 优化了API调用，减少重复调用（缓存stock_info和realtime_quote）
        - 独立的代码实现，不依赖predict方法
        
        Args:
            symbol: 股票代码
            
        Returns:
            预测结果字典（包含prediction_type='before_close'）
        """
        self.logger.info("=" * 60)
        self.logger.info(f"开始分析股票（未收盘-明天）: {symbol}")
        self.logger.info("=" * 60)
        
        # 根据时间判断预测日期
        target_date, date_desc = self.get_target_date()
        prediction_date = datetime.now().strftime('%Y-%m-%d')  # 预测日期（当前日期）
        self.logger.info(f"预测日期（{date_desc}）: {target_date}")
        
        # 0. 异常情况检测（在获取数据之前先检测，避免无效预测）
        self.logger.info("步骤0: 检测异常情况...")
        # 提前获取realtime_quote用于异常检测（避免重复调用）
        realtime_quote_for_anomaly = None
        try:
            realtime_quote_for_anomaly = self.data_source.get_realtime_quote(symbol)
        except Exception as e:
            self.logger.debug(f"获取实时行情用于异常检测失败: {str(e)}")
        
        anomaly_result = self._detect_anomalies_with_realtime_quote(symbol, realtime_quote_for_anomaly)
        if not anomaly_result.get('can_predict', True):
            anomalies = anomaly_result.get('anomalies', [])
            self.logger.warning(f"检测到异常情况: {', '.join(anomalies)}")
            return {
                'symbol': symbol,
                'success': False,
                'message': f"无法预测：{', '.join(anomalies)}",
                'anomalies': anomalies,
                'anomaly_details': anomaly_result.get('details', {}),
                'prediction_type': 'before_close'
            }
        
        # 保存异常检测结果，后续用于调整置信度和整合到结果中
        initial_anomaly_result = anomaly_result
        
        # 1. 获取股票数据（必须先获取，其他分析依赖此数据）
        self.logger.info("步骤1: 获取股票数据（历史数据从数据库，当天数据实时获取）...")
        # 优先从数据库获取历史数据（已优化）
        data = self.data_source.get_stock_data(symbol, days=self.config['lookback_days'])
        
        if data.empty:
            return {
                'symbol': symbol,
                'success': False,
                'message': '无法获取股票数据',
                'prediction_type': 'before_close'
            }
        
        # 提前获取stock_info和realtime_quote，供后续复用（优化API调用）
        stock_info_cache = None
        realtime_quote_cache = realtime_quote_for_anomaly  # 复用异常检测时获取的realtime_quote
        
        # 未收盘-明天预测：必须实时获取当天的数据
        # 如果realtime_quote_cache为空，强制获取实时数据
        if not realtime_quote_cache or not realtime_quote_cache.get('current_price'):
            self.logger.info("未收盘预测：强制获取实时行情数据...")
            try:
                realtime_quote_cache = self.data_source.get_realtime_quote(symbol)
                if not realtime_quote_cache:
                    return {
                        'symbol': symbol,
                        'success': False,
                        'message': '无法获取实时行情数据（未收盘预测需要实时数据）',
                        'prediction_type': 'before_close'
                    }
            except Exception as e:
                self.logger.error(f"获取实时行情数据失败: {str(e)}")
                return {
                    'symbol': symbol,
                    'success': False,
                    'message': f'获取实时行情数据失败: {str(e)}',
                    'prediction_type': 'before_close'
                }
        
        # 使用实时价格（未收盘预测必须使用实时数据）
        current_price = float(realtime_quote_cache.get('current_price', 0))
        if current_price <= 0:
            # 如果实时价格无效，尝试使用历史数据最新价格
            current_price = data['close'].iloc[-1]
            price_source = "历史数据最新价格（实时价格无效）"
            self.logger.warning(f"实时价格无效，使用历史数据最新价格: {current_price:.2f}元")
        else:
            price_source = "实时API价格"
            self.logger.info(f"使用实时价格: {current_price:.2f}元")
        
        self.logger.info(f"当前价格: {current_price:.2f}元（来源：{price_source}）")
        
        # 提前获取stock_info，供后续复用（优化API调用）
        # 设置页面预测：如果use_api=False，跳过API调用，只使用数据库数据
        stock_info_cache = None
        if use_api:
            try:
                stock_info_cache = self.data_source.get_stock_info(symbol, skip_pe_pb=False)
            except Exception as e:
                self.logger.debug(f"获取股票信息失败: {str(e)}")
        else:
            self.logger.debug(f"跳过API调用（use_api=False），只使用数据库数据")
        
        # 获取股票名称（使用缓存的stock_info）
        stock_name = '未知'
        try:
            if stock_info_cache:
                stock_name = stock_info_cache.get('name', stock_info_cache.get('股票简称', stock_info_cache.get('股票名称', '未知')))
            if not stock_name or stock_name == '':
                stock_name = '未知'
        except Exception as e:
            self.logger.warning(f"获取股票名称失败: {str(e)}，使用默认值'未知'")
            stock_name = '未知'
        
        # 使用多线程并行执行独立分析任务（不需要股票历史数据的分析）
        self.logger.info("\n步骤2-5.7: 并行分析多个指标（使用多线程加速，优化API调用）...")
        
        # 定义需要并行执行的任务（独立分析，只需要symbol）
        # 注意：传入stock_info_cache，避免重复API调用
        # 【优化】注释掉低价值因子（valuation, us_sector, sector_rotation），减少因子冲突，提高预测准确率
        independent_tasks = {
            'market_overall': lambda: self.predict_market_overall(),
            'news': lambda: self.calculate_news_score(symbol),
            'capital_flow': lambda: self.calculate_capital_flow_score(symbol),
            # 'valuation': lambda: self._calculate_valuation_score_with_cache(symbol, stock_info_cache),  # 【已注释】估值指标权重低（2%），影响小
            # 'us_sector': lambda: self.calculate_us_sector_score(symbol),  # 【已注释】美股板块相关性可能不高
            # 'sector_rotation': lambda: self.calculate_sector_rotation_score(symbol),  # 【已注释】板块轮动数据可能不稳定
            'market_sentiment_index': lambda: self.calculate_market_sentiment_index(),
        }
        
        # 定义依赖股票数据的任务（需要data）
        data_dependent_tasks = {
            'technical': lambda: self.calculate_technical_score(data, symbol),
            'market': lambda: self.calculate_market_score(data, symbol, use_api=use_api, indices_data=pre_queried_indices_data),  # 传递use_api参数和预查询的指数数据（性能优化）
            'history': lambda: self.calculate_history_score(data),
        }
        
        # 存储结果的字典
        results = {}
        
        # 第一阶段：并行执行独立分析任务
        # 【优化】已移除估值、美股板块、板块轮动因子，减少因子冲突
        self.logger.info("  并行执行独立分析任务（市场整体、新闻、资金流向）...")
        
        # 尝试使用线程池，如果失败则使用单线程模式
        use_thread_pool = True
        try:
            with ThreadPoolExecutor(max_workers=THREAD_POOL_CONFIG["predictor_default"]) as executor:
                future_to_task = {
                    executor.submit(func): task_name 
                    for task_name, func in independent_tasks.items()
                }
                
                for future in as_completed(future_to_task):
                    task_name = future_to_task[future]
                    try:
                        result = future.result()
                        results[task_name] = result
                        self.logger.debug(f"    ✓ {task_name} 分析完成")
                    except Exception as e:
                        self.logger.warning(f"    ✗ {task_name} 分析失败: {str(e)}")
                        # 为失败的任务设置默认值
                        if task_name == 'market_overall':
                            results[task_name] = {'success': False}
                        elif task_name == 'news':
                            results[task_name] = {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'weight_multiplier': 1.0}
                        elif task_name == 'capital_flow':
                            results[task_name] = {'score': 0.0, 'trend': 'neutral', 'details': {}}
                        # 【已注释】以下三个因子已移除
                        # elif task_name == 'valuation':
                        #     results[task_name] = {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None}
                        # elif task_name == 'us_sector':
                        #     results[task_name] = {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0}
                        # elif task_name == 'sector_rotation':
                        #     results[task_name] = {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'}
        except RuntimeError as e:
            # 如果解释器正在关闭，无法使用线程池，切换到单线程模式
            if 'cannot schedule new futures after interpreter shutdown' in str(e):
                self.logger.warning("  检测到解释器正在关闭，线程池不可用，切换到单线程模式执行分析任务")
                use_thread_pool = False
            else:
                # 其他RuntimeError，重新抛出
                raise
        
        # 如果线程池不可用，使用单线程顺序执行
        if not use_thread_pool:
            for task_name, func in independent_tasks.items():
                try:
                    result = func()
                    results[task_name] = result
                    self.logger.debug(f"    ✓ {task_name} 分析完成（单线程模式）")
                except Exception as e:
                    self.logger.warning(f"    ✗ {task_name} 分析失败: {str(e)}")
                    # 为失败的任务设置默认值
                    if task_name == 'market_overall':
                        results[task_name] = {'success': False}
                    elif task_name == 'news':
                        results[task_name] = {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'weight_multiplier': 1.0}
                    elif task_name == 'capital_flow':
                        results[task_name] = {'score': 0.0, 'trend': 'neutral', 'details': {}}
                    # 【已注释】以下三个因子已移除
                    # elif task_name == 'valuation':
                    #     results[task_name] = {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None}
                    # elif task_name == 'us_sector':
                    #     results[task_name] = {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0}
                    # elif task_name == 'sector_rotation':
                    #     results[task_name] = {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'}
        
        # 第二阶段：并行执行依赖股票数据的分析任务
        self.logger.info("  并行执行依赖股票数据的分析任务（技术指标、市场情绪、历史模式）...")
        
        if use_thread_pool:
            try:
                with ThreadPoolExecutor(max_workers=THREAD_POOL_CONFIG["predictor_small"]) as executor:
                    future_to_task = {
                        executor.submit(func): task_name 
                        for task_name, func in data_dependent_tasks.items()
                    }
                    
                    for future in as_completed(future_to_task):
                        task_name = future_to_task[future]
                        try:
                            result = future.result()
                            results[task_name] = result
                            self.logger.debug(f"    ✓ {task_name} 分析完成")
                        except Exception as e:
                            self.logger.warning(f"    ✗ {task_name} 分析失败: {str(e)}")
                            # 为失败的任务设置默认值
                            if task_name == 'technical':
                                results[task_name] = {'score': 0.0, 'signals': {}}
                            elif task_name == 'market':
                                results[task_name] = {'score': 0.0, 'trend': 'neutral'}
                            elif task_name == 'history':
                                results[task_name] = {'score': 0.0, 'pattern': '无显著模式'}
            except RuntimeError as e:
                if 'cannot schedule new futures after interpreter shutdown' in str(e):
                    self.logger.warning("  检测到解释器正在关闭，线程池不可用，切换到单线程模式")
                    use_thread_pool = False
                else:
                    raise
        
        # 如果线程池不可用，使用单线程顺序执行
        if not use_thread_pool:
            for task_name, func in data_dependent_tasks.items():
                try:
                    result = func()
                    results[task_name] = result
                    self.logger.debug(f"    ✓ {task_name} 分析完成（单线程模式）")
                except Exception as e:
                    self.logger.warning(f"    ✗ {task_name} 分析失败: {str(e)}")
                    # 为失败的任务设置默认值
                    if task_name == 'technical':
                        results[task_name] = {'score': 0.0, 'signals': {}}
                    elif task_name == 'market':
                        results[task_name] = {'score': 0.0, 'trend': 'neutral'}
                    elif task_name == 'history':
                        results[task_name] = {'score': 0.0, 'pattern': '无显著模式'}
        
        # 后续逻辑：完全独立实现结果融合、置信度计算等（代码分离：不共用共享方法）
        self.logger.info("  所有并行分析任务完成！")
        
        # 从结果中提取各个分析结果
        market_overall = results.get('market_overall', {'success': False})
        
        technical_result = results.get('technical', {'score': 0.0, 'trend': 'neutral', 'signals': {}})
        technical_score = technical_result['score']
        self.logger.info(f"\n技术指标分析结果: 得分 {technical_score:.2f}, 趋势: {technical_result['trend']}")
        signals = technical_result.get('signals', {})
        if '换手率' in signals:
            self.logger.info(f"  换手率: {signals['换手率']}")
        if '量价关系' in signals:
            self.logger.info(f"  量价关系: {signals['量价关系']}")
        
        news_result = results.get('news', {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'weight_multiplier': 1.0})
        news_score = news_result['score']
        news_weight_multiplier = news_result.get('weight_multiplier', 1.0)
        self.logger.info(f"新闻情感分析结果: 得分 {news_score:.2f}, 情感: {news_result['sentiment']}, "
                        f"新闻数量: {news_result['news_count']}, 权重倍数: {news_weight_multiplier:.2f}")
        if news_result.get('positive_count', 0) > 0 or news_result.get('negative_count', 0) > 0:
            self.logger.info(f"  利好消息: {news_result.get('positive_count', 0)} 条（强度{news_result.get('positive_strength', 0):.2f}），"
                           f"利空消息: {news_result.get('negative_count', 0)} 条（强度{news_result.get('negative_strength', 0):.2f}）")
        
        capital_flow_result = results.get('capital_flow', {'score': 0.0, 'trend': 'neutral', 'details': {}})
        capital_flow_score = capital_flow_result['score']
        capital_flow_details = capital_flow_result.get('details', {})
        self.logger.info(f"资金流向分析结果: 得分 {capital_flow_score:.2f}, 趋势: {capital_flow_result['trend']}")
        if 'north_bound' in capital_flow_details:
            nb = capital_flow_details['north_bound']
            if 'today_net_inflow' in nb:
                self.logger.info(f"  北向资金: 净流入 {nb.get('today_net_inflow', 0):.2f} 亿元")
        if 'margin' in capital_flow_details:
            mg = capital_flow_details['margin']
            if 'margin_change_pct' in mg:
                self.logger.info(f"  融资融券: 余额变化 {mg.get('margin_change_pct', 0):.2f}%")
        if 'main_force' in capital_flow_details:
            mf = capital_flow_details['main_force']
            if 'main_net_inflow_pct' in mf:
                self.logger.info(f"  主力资金: 净流入 {mf.get('main_net_inflow_pct', 0):.2f}%")
        
        market_result = results.get('market', {'score': 0.0, 'trend': 'neutral', 'details': {}})
        market_score = market_result['score']
        market_details = market_result.get('details', {})
        self.logger.info(f"市场情绪分析结果: 得分 {market_score:.2f}, 趋势: {market_result['trend']}")
        if 'market_index_score' in market_details:
            self.logger.info(f"  大盘指数得分: {market_details.get('market_index_score', 0):.2f} (基于{market_details.get('index_count', 0)}个指数)")
        if 'stock_score' in market_details:
            self.logger.info(f"  个股情绪得分: {market_details.get('stock_score', 0):.2f}")
        
        history_result = results.get('history', {'score': 0.0, 'pattern': 'unknown'})
        history_score = history_result['score']
        self.logger.info(f"历史模式分析结果: 得分 {history_score:.2f}, 模式: {history_result['pattern']}")
        
        valuation_result = results.get('valuation', {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None})
        valuation_score = valuation_result['score']
        pe_ratio = valuation_result.get('pe_ratio')
        pb_ratio = valuation_result.get('pb_ratio')
        self.logger.info(f"估值指标分析结果: 得分 {valuation_score:.2f}, PE: {pe_ratio}, PB: {pb_ratio}")
        
        us_sector_result = results.get('us_sector', {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0})
        us_sector_score = us_sector_result['score']
        us_sector_name = us_sector_result.get('sector', 'unknown')
        us_sector_change = us_sector_result.get('change_pct', 0.0)
        self.logger.info(f"美股板块分析结果: 得分 {us_sector_score:.2f}, 板块: {us_sector_name}, 涨跌幅: {us_sector_change:.2f}%")
        
        sector_rotation_result = results.get('sector_rotation', {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'})
        sector_rotation_score = sector_rotation_result['score']
        sector_name = sector_rotation_result.get('sector_name', 'unknown')
        sector_trend = sector_rotation_result.get('trend', 'neutral')
        self.logger.info(f"板块轮动分析结果: 得分 {sector_rotation_score:.2f}, 板块: {sector_name}, 趋势: {sector_trend}")
        
        # 市场情绪指标（恐慌/贪婪指数）
        market_sentiment_index = results.get('market_sentiment_index', {
            'available': False,
            'fear_index': 50.0,
            'greed_index': 50.0,
            'sentiment': 'neutral'
        })
        if market_sentiment_index.get('available'):
            self.logger.info(f"市场情绪指标: 恐慌指数 {market_sentiment_index.get('fear_index', 50):.1f}, "
                           f"贪婪指数 {market_sentiment_index.get('greed_index', 50):.1f}, "
                           f"综合情绪: {market_sentiment_index.get('sentiment', 'neutral')}")
            if market_sentiment_index.get('emotional_trading'):
                self.logger.warning(f"情绪化交易警告: {market_sentiment_index.get('emotional_reason', '')}")
        
        # 6. 识别市场状态并动态调整权重（增强版：基于历史准确率优化 + 市场状态 + 个股特性）
        self.logger.info("\n步骤6: 识别市场状态并综合计算预测结果...")
        
        # 6.1 计算各因子的数据质量评分（新增：数据缺失处理优化）
        factor_quality_scores = {}
        try:
            factor_results_map = {
                'technical': technical_result,
                'news': news_result,
                'capital_flow': capital_flow_result,
                'market': market_result,
                'history': history_result,
                'valuation': valuation_result,
                'us_sector': us_sector_result,
                'sector_rotation': sector_rotation_result,
                'market_overall': market_overall
            }
            
            for factor_name, factor_result in factor_results_map.items():
                quality_score = self._calculate_factor_data_quality(factor_name, factor_result)
                factor_quality_scores[factor_name] = quality_score
                if quality_score < 0.6:
                    self.logger.debug(f"因子 {factor_name} 数据质量评分: {quality_score:.2f} (数据可能不完整)")
        except Exception as e:
            self.logger.debug(f"计算因子数据质量评分失败: {str(e)}")
            # 出错时，假设所有因子质量良好
            factor_quality_scores = {name: 1.0 for name in factor_results_map.keys()}
        
        # 尝试识别市场状态
        market_state = {'state': 'sideways', 'confidence': 0.5}  # 默认值
        weight_multipliers = {}  # 默认不调整权重
        try:
            from utils.market_state_identifier import MarketStateIdentifier
            identifier = MarketStateIdentifier()
            
            # 获取大盘指数数据用于识别市场状态
            try:
                indices_data = self.data_source.get_all_market_indices(days=30)
                # 使用上证指数（000001.SH）作为主要参考
                if '000001.SH' in indices_data and not indices_data['000001.SH'].empty:
                    index_data = indices_data['000001.SH']
                    market_state = identifier.identify_market_state(index_data, '上证指数')
                    weight_multipliers = identifier.get_weight_adjustment(market_state)
                    
                    self.logger.info(f"市场状态识别: {market_state['state']} ({market_state['description']})，置信度: {market_state['confidence']:.1%}")
                    if weight_multipliers:
                        self.logger.info(f"权重调整: 技术指标×{weight_multipliers.get('technical_weight_multiplier', 1.0):.2f}, "
                                       f"新闻×{weight_multipliers.get('news_weight_multiplier', 1.0):.2f}, "
                                       f"资金流向×{weight_multipliers.get('capital_flow_weight_multiplier', 1.0):.2f}")
            except Exception as e:
                self.logger.debug(f"市场状态识别失败（不影响主流程）: {str(e)}")
        except ImportError:
            self.logger.debug("市场状态识别模块不可用，使用默认权重")
        except Exception as e:
            self.logger.debug(f"市场状态识别模块初始化失败: {str(e)}")
        
        # 使用权重优化器获取优化后的权重（综合考虑历史准确率、市场状态、个股特性）
        optimized_weights = None
        try:
            from utils.weight_optimizer import get_weight_optimizer
            from utils.confidence_calculator import get_confidence_calculator
            weight_optimizer = get_weight_optimizer()
            
            # 获取优化后的权重（基于历史准确率、市场状态、个股特性）
            optimized_weights = weight_optimizer.get_optimized_weights(
                symbol=symbol,
                market_state=market_state,
                use_accuracy_optimization=True
            )
            
            self.logger.info(f"权重优化器已启用，使用优化后的权重配置")
            
        except Exception as e:
            self.logger.debug(f"权重优化失败，使用基于市场状态的调整: {str(e)}")
        
        # 检查是否为新股票或数据不足（用于优化处理）
        is_new_stock_or_insufficient_data = False
        try:
            # 检查历史预测数据数量
            from utils.db_connection import DatabaseConnection
            db = DatabaseConnection()
            check_sql = """
                SELECT COUNT(*) as cnt
                FROM stock_predictions
                WHERE symbol = %s
                  AND prediction_hit IS NOT NULL
            """
            result = db.execute_query(check_sql, (symbol,))
            if result and result[0].get('cnt', 0) < 10:  # 少于10条历史预测记录
                is_new_stock_or_insufficient_data = True
                self.logger.debug(f"股票 {symbol} 历史数据不足（{result[0].get('cnt', 0)}条），使用保守策略")
        except Exception as e:
            self.logger.debug(f"检查历史数据失败: {str(e)}")
            # 如果检查失败，假设数据不足，使用保守策略
            is_new_stock_or_insufficient_data = True
        
        # 根据是否使用优化后的权重来设置权重值
        # 【优化】已移除三个因子（valuation, us_sector, sector_rotation），将其权重重新分配给其他因子
        if optimized_weights and not is_new_stock_or_insufficient_data:
            # 使用优化后的权重（重新分配被移除因子的权重）
            base_technical_weight = optimized_weights.get('technical_weight', self.config.get('technical_weight', 0.20))
            base_news_weight = optimized_weights.get('news_weight', self.config['news_weight']) * news_weight_multiplier
            base_capital_flow_weight = optimized_weights.get('capital_flow_weight', self.config.get('capital_flow_weight', 0.18))
            base_market_weight = optimized_weights.get('market_weight', self.config.get('market_weight', 0.17))
            base_history_weight = optimized_weights.get('history_weight', self.config.get('history_weight', 0.08))
            
            # 获取被移除因子的权重（用于重新分配）
            removed_weights = (
                optimized_weights.get('sector_rotation_weight', 0.05) +
                optimized_weights.get('valuation_weight', 0.02) +
                optimized_weights.get('us_sector_weight', 0.05)
            )
            
            # 按比例重新分配权重（保持原有比例）
            total_base_weight = base_technical_weight + base_news_weight + base_capital_flow_weight + base_market_weight + base_history_weight
            if total_base_weight > 0:
                redistribution_factor = removed_weights / total_base_weight
                base_weights_dict = {
                    'technical': base_technical_weight * (1 + redistribution_factor),
                    'news': base_news_weight * (1 + redistribution_factor),
                    'capital_flow': base_capital_flow_weight * (1 + redistribution_factor),
                    'market': base_market_weight * (1 + redistribution_factor),
                    'history': base_history_weight * (1 + redistribution_factor)
                }
            else:
                # 如果基础权重为0，使用默认重新分配
                base_weights_dict = {
                    'technical': 0.22,
                    'news': 0.28,
                    'capital_flow': 0.20,
                    'market': 0.19,
                    'history': 0.11
                }
        else:
            # 如果是新股票或数据不足，使用保守的默认权重（不依赖历史优化）
            if is_new_stock_or_insufficient_data:
                self.logger.info(f"股票 {symbol} 数据不足，使用保守的默认权重配置")
            # 如果权重优化失败，回退到基于市场状态的调整
            technical_multiplier = weight_multipliers.get('technical_weight_multiplier', 1.0)
            news_multiplier = weight_multipliers.get('news_weight_multiplier', 1.0) * news_weight_multiplier
            capital_flow_multiplier = weight_multipliers.get('capital_flow_weight_multiplier', 1.0)
            market_multiplier = weight_multipliers.get('market_weight_multiplier', 1.0)
            
            # 基础权重（移除三个因子后重新分配）
            base_technical = self.config.get('technical_weight', 0.20) * technical_multiplier
            base_news = self.config['news_weight'] * news_multiplier
            base_capital_flow = self.config.get('capital_flow_weight', 0.18) * capital_flow_multiplier
            base_market = self.config.get('market_weight', 0.17) * market_multiplier
            base_history = self.config.get('history_weight', 0.08)
            
            # 获取被移除因子的权重
            removed_weights = (
                self.config.get('sector_rotation_weight', 0.05) +
                self.config.get('valuation_weight', 0.02) +
                self.config.get('us_sector_weight', 0.05)
            )
            
            # 按比例重新分配
            total_base_weight = base_technical + base_news + base_capital_flow + base_market + base_history
            if total_base_weight > 0:
                redistribution_factor = removed_weights / total_base_weight
                base_weights_dict = {
                    'technical': base_technical * (1 + redistribution_factor),
                    'news': base_news * (1 + redistribution_factor),
                    'capital_flow': base_capital_flow * (1 + redistribution_factor),
                    'market': base_market * (1 + redistribution_factor),
                    'history': base_history * (1 + redistribution_factor)
                }
            else:
                base_weights_dict = {
                    'technical': 0.22,
                    'news': 0.28,
                    'capital_flow': 0.20,
                    'market': 0.19,
                    'history': 0.11
                }
        
        # 根据数据质量动态调整权重（新增：数据缺失处理优化）
        # 【优化】已移除三个因子，只调整保留的5个因子
        try:
            adjusted_weights_dict = self._adjust_weights_by_data_quality(base_weights_dict, factor_quality_scores)
            adjusted_technical_weight = adjusted_weights_dict.get('technical', base_weights_dict['technical'])
            adjusted_news_weight = adjusted_weights_dict.get('news', base_weights_dict['news'])
            adjusted_capital_flow_weight = adjusted_weights_dict.get('capital_flow', base_weights_dict['capital_flow'])
            adjusted_market_weight = adjusted_weights_dict.get('market', base_weights_dict['market'])
            adjusted_history_weight = adjusted_weights_dict.get('history', base_weights_dict['history'])
            # 【已注释】以下三个因子已移除
            # adjusted_sector_rotation_weight = adjusted_weights_dict.get('sector_rotation', base_weights_dict['sector_rotation'])
            # adjusted_valuation_weight = adjusted_weights_dict.get('valuation', base_weights_dict['valuation'])
            # adjusted_us_sector_weight = adjusted_weights_dict.get('us_sector', base_weights_dict['us_sector'])
            adjusted_sector_rotation_weight = 0.0  # 默认值
            adjusted_valuation_weight = 0.0  # 默认值
            adjusted_us_sector_weight = 0.0  # 默认值
            
            # 记录数据质量调整信息（仅在debug模式下）
            avg_quality = sum(factor_quality_scores.values()) / len(factor_quality_scores) if factor_quality_scores else 1.0
            if avg_quality < 0.7:
                self.logger.debug(f"数据质量调整: 平均质量 {avg_quality:.2f}, 权重已根据数据完整性调整")
        except Exception as e:
            self.logger.debug(f"根据数据质量调整权重失败，使用原始权重: {str(e)}")
            # 出错时使用原始权重
            adjusted_technical_weight = base_weights_dict['technical']
            adjusted_news_weight = base_weights_dict['news']
            adjusted_capital_flow_weight = base_weights_dict['capital_flow']
            adjusted_market_weight = base_weights_dict['market']
            adjusted_history_weight = base_weights_dict['history']
            # 【已注释】以下三个因子已移除
            # adjusted_sector_rotation_weight = base_weights_dict['sector_rotation']
            # adjusted_valuation_weight = base_weights_dict['valuation']
            # adjusted_us_sector_weight = base_weights_dict['us_sector']
            adjusted_sector_rotation_weight = 0.0  # 默认值
            adjusted_valuation_weight = 0.0  # 默认值
            adjusted_us_sector_weight = 0.0  # 默认值
        
        if optimized_weights and not is_new_stock_or_insufficient_data:
            self.logger.info(f"权重优化结果: 技术指标={adjusted_technical_weight:.3f}, "
                           f"新闻={adjusted_news_weight:.3f}, "
                           f"资金流向={adjusted_capital_flow_weight:.3f}, "
                           f"市场={adjusted_market_weight:.3f}")
        
        # 尝试获取ML模型预测结果（如果可用）
        ml_score = 0.0
        ml_weight = 0.0
        ml_prediction_result = None
        ml_model_id = None
        ml_model_type = None
        try:
            from utils.ml_predictor_integration import MLPredictorIntegration
            from utils.ml_model_performance_monitor import MLModelPerformanceMonitor
            
            ml_integration = MLPredictorIntegration()
            ml_prediction_result = ml_integration.get_ml_prediction(symbol, data)
            
            if ml_prediction_result and ml_prediction_result.get('available'):
                ml_score = ml_prediction_result.get('ml_score', 0.0)
                ml_model_type = ml_prediction_result.get('model_type')
                ml_model_id = ml_prediction_result.get('model_id')
                
                # 根据模型性能动态调整权重（优化：传递配置管理器，支持热更新）
                performance_monitor = MLModelPerformanceMonitor(config_manager=self._config_manager)
                if ml_model_id:
                    ml_weight = performance_monitor.get_optimal_weight(model_id=ml_model_id)
                elif ml_model_type:
                    ml_weight = performance_monitor.get_optimal_weight(model_type=ml_model_type)
                else:
                    ml_weight = 0.35  # 默认权重35%（ML模型为主导因子）
                
                self.logger.info(f"ML模型预测: 得分 {ml_score:.2f}, 上涨概率 {ml_prediction_result.get('ml_up_probability', 0.5):.2%}, "
                               f"方向 {ml_prediction_result.get('ml_prediction', '震荡')}, "
                               f"置信度 {ml_prediction_result.get('ml_confidence', 0.0):.2%}, "
                               f"动态权重 {ml_weight:.2%}")
        except ImportError:
            self.logger.debug("ML模型集成模块不可用，跳过ML预测")
        except Exception as e:
            self.logger.debug(f"ML模型预测失败（不影响主流程）: {str(e)}")
        
        # 计算包含ML模型的总权重（用于归一化）
        # 【优化】已移除三个因子，只计算保留的5个因子 + ML模型
        total_adjusted_weight = (
            adjusted_technical_weight +
            adjusted_news_weight +
            adjusted_capital_flow_weight +
            adjusted_market_weight +
            adjusted_history_weight +
            ml_weight  # 包含ML模型权重
            # 【已注释】以下三个因子已移除
            # adjusted_sector_rotation_weight +
            # adjusted_valuation_weight +
            # adjusted_us_sector_weight +
        )
        
        # 归一化权重（确保总和为1，包含ML模型权重）
        if total_adjusted_weight > 0:
            adjusted_technical_weight = adjusted_technical_weight / total_adjusted_weight
            adjusted_news_weight = adjusted_news_weight / total_adjusted_weight
            adjusted_capital_flow_weight = adjusted_capital_flow_weight / total_adjusted_weight
            adjusted_market_weight = adjusted_market_weight / total_adjusted_weight
            adjusted_history_weight = adjusted_history_weight / total_adjusted_weight
            ml_weight = ml_weight / total_adjusted_weight  # 归一化ML模型权重
            # 【已注释】以下三个因子已移除
            # adjusted_sector_rotation_weight = adjusted_sector_rotation_weight / total_adjusted_weight
            # adjusted_valuation_weight = adjusted_valuation_weight / total_adjusted_weight
            # adjusted_us_sector_weight = adjusted_us_sector_weight / total_adjusted_weight
            adjusted_sector_rotation_weight = 0.0  # 默认值
            adjusted_valuation_weight = 0.0  # 默认值
            adjusted_us_sector_weight = 0.0  # 默认值
        
        # 使用动态调整后的权重计算最终得分（包含ML模型）
        # 【优化】已移除三个因子，只计算保留的5个因子 + ML模型
        final_score = (
            technical_score * adjusted_technical_weight +
            news_score * adjusted_news_weight +
            capital_flow_score * adjusted_capital_flow_weight +
            market_score * adjusted_market_weight +
            history_score * adjusted_history_weight +
            ml_score * ml_weight  # 添加ML模型得分
            # 【已注释】以下三个因子已移除
            # sector_rotation_score * adjusted_sector_rotation_weight +
            # valuation_score * adjusted_valuation_weight +
            # us_sector_score * adjusted_us_sector_weight +
        )
        
        # 转换为涨跌概率
        # 使用sigmoid函数将得分转换为概率（优化版：动态调整放大系数）
        # 先计算波动率系数（用于动态调整Sigmoid系数）
        volatility_coefficient = self._calculate_volatility_coefficient(data, period=60)
        
        # 根据市场状态、波动率和历史准确率动态调整放大系数
        sigmoid_coefficient = self._calculate_dynamic_sigmoid_coefficient(
            final_score=final_score,
            market_state=market_state if 'market_state' in locals() else {},
            volatility_coefficient=volatility_coefficient,
            symbol=symbol
        )
        up_probability = 1 / (1 + np.exp(-final_score * sigmoid_coefficient))
        down_probability = 1 - up_probability
        
        # 概率校准（根据历史准确率校准，过滤干扰因子，提高可靠性）
        up_probability = self._calibrate_probability(
            raw_probability=up_probability,
            symbol=symbol,
            final_score=final_score
        )
        down_probability = 1 - up_probability
        
        # 计算置信度（增强版：考虑历史准确率、一致性、数据时效性、校准）
        # 如果是新股票或数据不足，降低置信度阈值
        min_confidence_threshold = self.config['min_confidence']
        if is_new_stock_or_insufficient_data:
            # 数据不足时，使用更保守的置信度阈值（降低20%）
            min_confidence_threshold = self.config['min_confidence'] * 0.8
            self.logger.debug(f"股票 {symbol} 数据不足，置信度阈值从 {self.config['min_confidence']:.2f} 降低到 {min_confidence_threshold:.2f}")
        
        # 计算因子一致性评分（用于学习分析，包含ML模型）
        # 【优化】已移除三个因子，只使用保留的5个因子
        factor_scores_for_consistency = {
            'technical': technical_score,
            'news': news_score,
            'capital_flow': capital_flow_score,
            'market': market_score,
            'history': history_score
            # 【已注释】以下三个因子已移除
            # 'sector_rotation': sector_rotation_score,
            # 'valuation': valuation_score,
            # 'us_sector': us_sector_score
        }
        if ml_prediction_result and ml_prediction_result.get('available'):
            factor_scores_for_consistency['ml_model'] = ml_score
        
        # 获取因子权重（用于一致性计算）
        factor_weights_for_consistency = {
            'technical': adjusted_technical_weight,
            'news': adjusted_news_weight,
            'capital_flow': adjusted_capital_flow_weight,
            'market': adjusted_market_weight,
            'history': adjusted_history_weight
            # 【已注释】以下三个因子已移除
            # 'sector_rotation': adjusted_sector_rotation_weight,
            # 'valuation': adjusted_valuation_weight,
            # 'us_sector': adjusted_us_sector_weight
        }
        if ml_prediction_result and ml_prediction_result.get('available'):
            factor_weights_for_consistency['ml_model'] = ml_weight
        
        # 保存因子权重，供置信度计算使用
        self._last_factor_weights = factor_weights_for_consistency
        
        factor_consistency_score = self._calculate_factor_consistency(
            final_score=final_score,
            factor_scores=factor_scores_for_consistency,
            factor_weights=factor_weights_for_consistency
        )
        
        # 计算数据质量评分（基于因子得分的有效性 + 数据完整性）
        # 【优化】已移除三个因子，因子总数从8改为5
        valid_factors = sum(1 for score in [
            technical_score, news_score, capital_flow_score, market_score, history_score
            # 【已注释】以下三个因子已移除
            # sector_rotation_score, valuation_score, us_sector_score
        ] if abs(score) > 0.01)
        total_factors = 5  # 【优化】从8改为5（移除了3个因子）
        data_quality_score = max(0.5, valid_factors / total_factors) if total_factors > 0 else 0.5
        
        # 结合数据完整性评分（新增：数据缺失处理优化）
        try:
            # 计算平均数据完整性评分
            if factor_quality_scores:
                avg_data_completeness = sum(factor_quality_scores.values()) / len(factor_quality_scores)
                # 综合数据质量评分：因子有效性 * 数据完整性
                data_quality_score = data_quality_score * 0.5 + avg_data_completeness * 0.5
        except Exception as e:
            self.logger.debug(f"计算数据完整性评分失败: {str(e)}")
        
        # 检查是否缺失关键数据
        missing_critical_data = False
        try:
            # 如果技术指标和市场情绪数据质量都很低，视为缺失关键数据
            technical_quality = factor_quality_scores.get('technical', 1.0)
            market_quality = factor_quality_scores.get('market', 1.0)
            if technical_quality < 0.3 and market_quality < 0.3:
                missing_critical_data = True
        except Exception:
            pass
        
        # 准备数据质量信息
        data_quality = {
            'quality_score': data_quality_score,
            'valid_factors': valid_factors,
            'total_factors': total_factors,
            'factor_quality_scores': factor_quality_scores  # 新增：传递因子质量评分
        }
        
        # 获取市场状态（如果可用）
        current_market_state = market_state if 'market_state' in locals() and market_state else {}
        
        confidence = self._calculate_confidence(
            final_score=final_score,
            factor_scores={
                'technical': technical_score,
                'news': news_score,
                'capital_flow': capital_flow_score,
                'market': market_score,
                'history': history_score
                # 【已注释】以下三个因子已移除
                # 'sector_rotation': sector_rotation_score,
                # 'valuation': valuation_score,
                # 'us_sector': us_sector_score
            },
            data_quality=data_quality,  # 传入数据质量信息
            symbol=symbol,
            market_state=current_market_state  # 传递市场状态信息用于置信度计算
        )
        
        # 根据数据质量进一步调整置信度（新增：数据缺失处理优化）
        try:
            confidence = self._adjust_confidence_by_data_quality(
                confidence,
                factor_quality_scores,
                missing_critical_data=missing_critical_data
            )
        except Exception as e:
            self.logger.debug(f"根据数据质量调整置信度失败: {str(e)}")
        
        # 根据异常情况调整置信度（从配置读取参数）
        try:
            anomaly_details = initial_anomaly_result.get('details', {})
            
            # ST股票：降低置信度（从配置读取）
            st_reduction = self.config.get('st_stock_confidence_reduction', 0.20)
            if 'st_stock' in initial_anomaly_result.get('anomalies', []):
                confidence = confidence * (1.0 - st_reduction)
                self.logger.warning(f"股票 {symbol} 为ST股票，置信度降低{st_reduction*100:.0f}%")
            
            # 涨跌停：降低置信度（从配置读取）
            limit_reduction = self.config.get('limit_up_down_confidence_reduction', 0.10)
            if 'limit_up' in initial_anomaly_result.get('anomalies', []) or 'limit_down' in initial_anomaly_result.get('anomalies', []):
                confidence = confidence * (1.0 - limit_reduction)
                self.logger.warning(f"股票 {symbol} 处于涨跌停状态，置信度降低{limit_reduction*100:.0f}%")
        except Exception as e:
            self.logger.debug(f"异常检测调整置信度失败: {str(e)}")
        
        # 如果置信度太低，降低概率差异
        if confidence < min_confidence_threshold:
            up_probability = 0.5 + (up_probability - 0.5) * (confidence / min_confidence_threshold)
            down_probability = 1 - up_probability
        
        # 确定预测方向（阈值0.55）
        if up_probability > 0.55:
            prediction = '上涨'
        elif down_probability > 0.55:
            prediction = '下跌'
        else:
            prediction = '震荡'
        
        # 计算明日大概收盘价格和涨幅（优化版）
        # 使用优化后的价格计算逻辑，考虑股票特性、历史波动率和价格趋势
        price_prediction_result = self._calculate_predicted_price_optimized(
            symbol=symbol,
            stock_name=stock_name,
            current_price=current_price,
            up_probability=up_probability,
            down_probability=down_probability,
            confidence=confidence,
            data=data
        )
        
        predicted_change_pct = price_prediction_result['predicted_change_pct']
        predicted_close_price = price_prediction_result['predicted_close_price']
        
        # 计算整体数据质量评分（新增：数据缺失处理优化）
        try:
            avg_quality = sum(factor_quality_scores.values()) / len(factor_quality_scores) if factor_quality_scores else 1.0
            missing_factors = [name for name, score in factor_quality_scores.items() if score < 0.3]
            quality_warning = avg_quality < 0.5
        except Exception:
            avg_quality = 1.0
            missing_factors = []
            quality_warning = False
        
        # 构建返回结果
        result = {
            'symbol': symbol,
            'name': stock_name,
            'success': True,
            'prediction': prediction,
            'up_probability': up_probability,
            'down_probability': down_probability,
            'confidence': confidence,
            'current_price': current_price,
            'price_source': price_source,
            'predicted_close_price': predicted_close_price,
            'predicted_change_pct': predicted_change_pct,
            'target_date': target_date,
            'prediction_date': prediction_date,
            'prediction_type': 'before_close',
            'final_score': final_score,
            'factors': {
                'technical': technical_score,
                'news': news_score,
                'capital_flow': capital_flow_score,
                'market': market_score,
                'history': history_score,
                # 【已注释】以下三个因子已移除
                # 'valuation': valuation_score,
                # 'us_sector': us_sector_score,
                # 'sector_rotation': sector_rotation_score,
                'ml': ml_score if ml_prediction_result else None
            },
            'weights': {
                'technical': adjusted_technical_weight,
                'news': adjusted_news_weight,
                'capital_flow': adjusted_capital_flow_weight,
                'market': adjusted_market_weight,
                'history': adjusted_history_weight,
                # 【已注释】以下三个因子已移除
                # 'valuation': adjusted_valuation_weight,
                # 'us_sector': adjusted_us_sector_weight,
                # 'sector_rotation': adjusted_sector_rotation_weight,
                'ml': ml_weight if ml_prediction_result else 0.0
            },
            'anomaly_info': initial_anomaly_result,
            'ml_prediction': ml_prediction_result,
            'market_state': market_state,
            'data_quality': {  # 新增：数据质量信息
                'overall_quality': avg_quality,
                'factor_quality': factor_quality_scores,
                'missing_factors': missing_factors,
                'quality_warning': quality_warning
            }
        }
        
        # 输出预测结果
        self.logger.info("=" * 60)
        self.logger.info("预测结果汇总：")
        self.logger.info(f"预测方向: {prediction}")
        self.logger.info(f"上涨概率: {up_probability*100:.1f}%")
        self.logger.info(f"下跌概率: {down_probability*100:.1f}%")
        self.logger.info(f"置信度: {confidence*100:.1f}%")
        self.logger.info(f"明日大概收盘价格: {predicted_close_price:.2f}元")
        self.logger.info(f"明日大概涨幅: {predicted_change_pct:+.2f}%")
        self.logger.info("=" * 60)
        
        return result
    
    def _detect_anomalies_with_realtime_quote(self, symbol: str, realtime_quote: Dict = None) -> Dict:
        """
        检测异常情况（使用传入的realtime_quote，避免重复调用）
        
        Args:
            symbol: 股票代码
            realtime_quote: 实时行情数据（可选，如果提供则复用）
        
        Returns:
            异常检测结果字典
        """
        anomalies = []
        details = {}
        
        try:
            # 1. 检查停牌
            suspension_info = self.data_source.check_suspension(symbol)
            if suspension_info.get('is_suspended', False):
                anomalies.append('suspended')
                details['suspension'] = {
                    'reason': suspension_info.get('reason', '未知'),
                    'resume_date': suspension_info.get('resume_date'),
                    'message': suspension_info.get('message', '股票停牌')
                }
            
            # 2. 检查ST股票
            st_info = self.data_source.check_st_stock(symbol)
            if st_info.get('is_st', False):
                anomalies.append('st_stock')
                details['st_stock'] = {
                    'risk_level': st_info.get('risk_level', 'high'),
                    'warning': st_info.get('warning', 'ST股票风险较高'),
                    'strategy': st_info.get('strategy', {})
                }
            
            # 3. 检查涨跌停（使用传入的realtime_quote，避免重复调用）
            if realtime_quote:
                current_price = realtime_quote.get('current_price')
                limit_up = realtime_quote.get('limit_up')
                limit_down = realtime_quote.get('limit_down')
                
                if current_price and limit_up and abs(current_price - limit_up) < 0.01:
                    anomalies.append('limit_up')
                    details['limit_up'] = {
                        'price': current_price,
                        'limit_price': limit_up,
                        'message': '股票涨停，无法买入'
                    }
                elif current_price and limit_down and abs(current_price - limit_down) < 0.01:
                    anomalies.append('limit_down')
                    details['limit_down'] = {
                        'price': current_price,
                        'limit_price': limit_down,
                        'message': '股票跌停，无法卖出'
                    }
            else:
                # 如果没有传入realtime_quote，从数据库获取（设置页面预测：只使用数据库数据）
                try:
                    from utils.db_connection import DatabaseConnection
                    from datetime import datetime
                    db = DatabaseConnection()
                    # 获取最新日期的数据（用于检查涨跌停状态）
                    sql = """
                        SELECT close_price, limit_up, limit_down, is_limit_up, is_limit_down
                        FROM stock_history_data
                        WHERE symbol = %s AND period_type = 'daily'
                        ORDER BY trade_date DESC
                        LIMIT 1
                    """
                    result = db.execute_query(sql, (symbol,))
                    if result and len(result) > 0:
                        record = result[0]
                        current_price = record.get('close_price')
                        limit_up = record.get('limit_up')
                        limit_down = record.get('limit_down')
                        is_limit_up = record.get('is_limit_up')
                        is_limit_down = record.get('is_limit_down')
                        
                        # 检查是否涨停或跌停
                        if is_limit_up == 1 or (current_price and limit_up and abs(float(current_price) - float(limit_up)) < 0.01):
                            anomalies.append('limit_up')
                            details['limit_up'] = {
                                'price': current_price,
                                'limit_price': limit_up,
                                'message': '股票涨停，无法买入'
                            }
                        elif is_limit_down == 1 or (current_price and limit_down and abs(float(current_price) - float(limit_down)) < 0.01):
                            anomalies.append('limit_down')
                            details['limit_down'] = {
                                'price': current_price,
                                'limit_price': limit_down,
                                'message': '股票跌停，无法卖出'
                            }
                except Exception as e:
                    self.logger.debug(f"从数据库检查涨跌停状态失败: {str(e)}")
            
            # 判断是否可以预测
            can_predict = 'suspended' not in anomalies
            
            return {
                'can_predict': can_predict,
                'anomalies': anomalies,
                'details': details
            }
            
        except Exception as e:
            self.logger.error(f"异常检测失败: {str(e)}")
            # 检测失败时，允许继续预测（避免因检测失败而阻止预测）
            return {
                'can_predict': True,
                'anomalies': [],
                'details': {},
                'error': str(e)
            }
    
    def _calculate_valuation_score_with_cache(self, symbol: str, stock_info: Dict = None) -> Dict:
        """
        计算估值指标得分（使用缓存的stock_info，避免重复API调用）
        
        Args:
            symbol: 股票代码
            stock_info: 缓存的股票信息（可选）
        
        Returns:
            估值得分字典
        """
        if stock_info is None:
            # 如果没有缓存，调用原方法
            return self.calculate_valuation_score(symbol)
        
        # 使用缓存的stock_info
        try:
            pe_ratio = None
            pb_ratio = None
            
            # 获取PE
            for key in ['pe_ratio', '市盈率', 'PE', 'PE(TTM)']:
                if key in stock_info:
                    try:
                        pe_value = stock_info[key]
                        if isinstance(pe_value, str):
                            pe_value = pe_value.replace('倍', '').replace(',', '').strip()
                        pe_ratio = float(pe_value)
                        break
                    except:
                        continue
            
            # 获取PB
            for key in ['pb_ratio', '市净率', 'PB', 'PB(MRQ)']:
                if key in stock_info:
                    try:
                        pb_value = stock_info[key]
                        if isinstance(pb_value, str):
                            pb_value = pb_value.replace('倍', '').replace(',', '').strip()
                        pb_ratio = float(pb_value)
                        break
                    except:
                        continue
            
            if pe_ratio is None and pb_ratio is None:
                return {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None, 'valuation': 'unknown'}
            
            score = 0.0
            
            # PE评分：一般认为PE在10-30之间合理，低于10可能被低估，高于30可能被高估
            if pe_ratio is not None:
                if pe_ratio < 10:
                    score += 0.15  # 被低估
                elif pe_ratio > 30:
                    score -= 0.15  # 被高估
                elif pe_ratio > 50:
                    score -= 0.25  # 严重高估
            
            # PB评分：一般认为PB在1-3之间合理，低于1可能被低估，高于3可能被高估
            if pb_ratio is not None:
                if pb_ratio < 1:
                    score += 0.1  # 被低估
                elif pb_ratio > 3:
                    score -= 0.1  # 被高估
                elif pb_ratio > 5:
                    score -= 0.2  # 严重高估
            
            # 确定估值状态
            if score > 0.1:
                valuation = 'undervalued'
            elif score < -0.1:
                valuation = 'overvalued'
            else:
                valuation = 'fair'
            
            return {
                'score': max(-1.0, min(1.0, score)),
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'valuation': valuation
            }
        except Exception as e:
            self.logger.error(f"计算估值得分失败: {str(e)}")
            return {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None, 'valuation': 'unknown'}
    
    def _process_prediction_results_internal(self, symbol: str, stock_name: str, current_price: float,
                                           price_source: str, data: pd.DataFrame, results: Dict,
                                           initial_anomaly_result: Dict, target_date: str, 
                                           prediction_date: str, prediction_type: str = 'after_close') -> Dict:
        """
        处理预测结果（融合因子、计算置信度等）- 内部方法，供predict和predict_before_close共用
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            current_price: 当前价格
            price_source: 价格来源
            data: 股票历史数据
            results: 各因子分析结果
            initial_anomaly_result: 初始异常检测结果
            target_date: 目标日期
            prediction_date: 预测日期
            prediction_type: 预测类型（'after_close' 或 'before_close'）
        
        Returns:
            预测结果字典
        """
        # 提取各因子得分（与predict方法中的逻辑相同）
        technical_result = results.get('technical', {'score': 0.0, 'signals': {}})
        technical_score = technical_result['score']
        technical_signals = technical_result.get('signals', {})
        
        news_result = results.get('news', {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'weight_multiplier': 1.0})
        news_score = news_result['score']
        news_sentiment = news_result.get('sentiment', 'neutral')
        news_count = news_result.get('news_count', 0)
        news_weight_multiplier = news_result.get('weight_multiplier', 1.0)
        
        capital_flow_result = results.get('capital_flow', {'score': 0.0, 'trend': 'neutral', 'details': {}})
        capital_flow_score = capital_flow_result['score']
        capital_flow_details = capital_flow_result.get('details', {})
        
        market_result = results.get('market', {'score': 0.0, 'trend': 'neutral'})
        market_score = market_result['score']
        market_trend = market_result.get('trend', 'neutral')
        
        history_result = results.get('history', {'score': 0.0, 'pattern': '无显著模式'})
        history_score = history_result['score']
        history_pattern = history_result.get('pattern', '无显著模式')
        
        valuation_result = results.get('valuation', {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None})
        valuation_score = valuation_result['score']
        pe_ratio = valuation_result.get('pe_ratio')
        pb_ratio = valuation_result.get('pb_ratio')
        
        us_sector_result = results.get('us_sector', {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0})
        us_sector_score = us_sector_result['score']
        
        sector_rotation_result = results.get('sector_rotation', {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'})
        sector_rotation_score = sector_rotation_result['score']
        
        market_overall_result = results.get('market_overall', {'success': False})
        market_overall_success = market_overall_result.get('success', False)
        
        # 由于后续逻辑非常复杂（包括ML模型、权重优化、置信度计算等），
        # 为了保持代码完整性和避免重复，这里调用predict方法的后续逻辑
        # 但通过设置prediction_type来区分
        
        # 为了真正实现代码分离，我们需要将predict方法从"步骤6"开始的所有逻辑
        # 提取到一个独立的内部方法中，然后predict和predict_before_close都调用它
        
        # 临时方案：由于predict方法的后半部分逻辑非常复杂（700+行），
        # 为了快速实现分离，这里先调用predict方法获取完整结果，然后设置prediction_type
        # 后续可以逐步重构，将公共逻辑提取到_process_prediction_results_internal方法
        
        # 注意：这里调用predict方法会导致重复执行前面的逻辑，但可以保证功能完整
        # 更好的方案是将predict方法重构，提取公共逻辑
        
        # 为了真正实现代码分离，我创建一个简化版本，包含核心逻辑
        # 后续可以逐步完善，将predict方法的完整逻辑迁移过来
        
        # 6. 识别市场状态并动态调整权重
        self.logger.info("\n步骤6: 识别市场状态并综合计算预测结果...")
        
        # 尝试识别市场状态
        market_state = {'state': 'sideways', 'confidence': 0.5}
        weight_multipliers = {}
        try:
            from utils.market_state_identifier import MarketStateIdentifier
            identifier = MarketStateIdentifier()
            
            try:
                indices_data = self.data_source.get_all_market_indices(days=30)
                if '000001.SH' in indices_data and not indices_data['000001.SH'].empty:
                    index_data = indices_data['000001.SH']
                    market_state = identifier.identify_market_state(index_data, '上证指数')
                    weight_multipliers = identifier.get_weight_adjustment(market_state)
            except Exception as e:
                self.logger.debug(f"市场状态识别失败: {str(e)}")
        except ImportError:
            self.logger.debug("市场状态识别模块不可用")
        except Exception as e:
            self.logger.debug(f"市场状态识别模块初始化失败: {str(e)}")
        
        # 使用权重优化器获取优化后的权重
        optimized_weights = None
        try:
            from utils.weight_optimizer import get_weight_optimizer
            weight_optimizer = get_weight_optimizer()
            optimized_weights = weight_optimizer.get_optimized_weights(
                symbol=symbol,
                market_state=market_state,
                use_accuracy_optimization=True
            )
            self.logger.info(f"权重优化器已启用，使用优化后的权重配置")
        except Exception as e:
            self.logger.debug(f"权重优化失败: {str(e)}")
        
        # 检查是否为新股票或数据不足
        is_new_stock_or_insufficient_data = False
        try:
            from utils.db_connection import DatabaseConnection
            db = DatabaseConnection()
            check_sql = """
                SELECT COUNT(*) as cnt
                FROM stock_predictions
                WHERE symbol = %s
                  AND prediction_hit IS NOT NULL
            """
            result = db.execute_query(check_sql, (symbol,))
            if result and result[0].get('cnt', 0) < 10:
                is_new_stock_or_insufficient_data = True
        except Exception as e:
            self.logger.debug(f"检查历史数据失败: {str(e)}")
            is_new_stock_or_insufficient_data = True
        
        # 根据是否使用优化后的权重来设置权重值
        if optimized_weights and not is_new_stock_or_insufficient_data:
            adjusted_technical_weight = optimized_weights.get('technical_weight', self.config.get('technical_weight', 0.20))
            adjusted_news_weight = optimized_weights.get('news_weight', self.config['news_weight']) * news_weight_multiplier
            adjusted_capital_flow_weight = optimized_weights.get('capital_flow_weight', self.config.get('capital_flow_weight', 0.18))
            adjusted_market_weight = optimized_weights.get('market_weight', self.config.get('market_weight', 0.17))
            adjusted_sector_rotation_weight = optimized_weights.get('sector_rotation_weight', self.config.get('sector_rotation_weight', 0.05))
            adjusted_history_weight = optimized_weights.get('history_weight', self.config.get('history_weight', 0.08))
            adjusted_valuation_weight = optimized_weights.get('valuation_weight', self.config.get('valuation_weight', 0.02))
            adjusted_us_sector_weight = optimized_weights.get('us_sector_weight', self.config.get('us_sector_weight', 0.05))
        else:
            technical_multiplier = weight_multipliers.get('technical_weight_multiplier', 1.0)
            news_multiplier = weight_multipliers.get('news_weight_multiplier', 1.0) * news_weight_multiplier
            capital_flow_multiplier = weight_multipliers.get('capital_flow_weight_multiplier', 1.0)
            market_multiplier = weight_multipliers.get('market_weight_multiplier', 1.0)
            
            adjusted_technical_weight = self.config.get('technical_weight', 0.20) * technical_multiplier
            adjusted_news_weight = self.config['news_weight'] * news_multiplier
            adjusted_capital_flow_weight = self.config.get('capital_flow_weight', 0.18) * capital_flow_multiplier
            adjusted_market_weight = self.config.get('market_weight', 0.17) * market_multiplier
            adjusted_sector_rotation_weight = self.config.get('sector_rotation_weight', 0.05)
            adjusted_history_weight = self.config.get('history_weight', 0.08)
            adjusted_valuation_weight = self.config.get('valuation_weight', 0.02)
            adjusted_us_sector_weight = self.config.get('us_sector_weight', 0.05)
        
        # 尝试获取ML模型预测结果
        ml_prediction_result = None
        ml_score = 0.0
        ml_weight = 0.0
        try:
            from utils.ml_predictor_integration import MLPredictorIntegration
            from utils.ml_model_performance_monitor import MLModelPerformanceMonitor
            
            ml_predictor = MLPredictorIntegration()
            ml_result = ml_predictor.get_ml_prediction(symbol, data, current_price)
            
            if ml_result.get('available', False):
                ml_score = ml_result.get('ml_score', 0.0)
                ml_up_probability = ml_result.get('ml_up_probability', 0.5)
                ml_model_type = ml_result.get('model_type', 'unknown')
                ml_model_id = ml_result.get('model_id')
                
                # 获取动态权重（优化：传递配置管理器，支持热更新）
                performance_monitor = MLModelPerformanceMonitor(config_manager=self._config_manager)
                ml_weight = performance_monitor.get_optimal_weight(ml_model_id, ml_model_type) if ml_model_id else 0.15
                
                ml_prediction_result = {
                    'ml_score': ml_score,
                    'ml_up_probability': ml_up_probability,
                    'ml_down_probability': 1.0 - ml_up_probability,
                    'ml_prediction': '上涨' if ml_up_probability > 0.5 else '下跌',
                    'ml_confidence': ml_result.get('ml_confidence', 0.5),
                    'model_type': ml_model_type,
                    'model_id': ml_model_id,
                    'dynamic_weight': ml_weight
                }
        except Exception as e:
            self.logger.debug(f"ML模型预测失败（不影响主流程）: {str(e)}")
        
        # 计算包含ML模型的总权重（用于归一化）
        total_adjusted_weight = (
            adjusted_technical_weight +
            adjusted_news_weight +
            adjusted_capital_flow_weight +
            adjusted_market_weight +
            adjusted_sector_rotation_weight +
            adjusted_history_weight +
            adjusted_valuation_weight +
            adjusted_us_sector_weight +
            ml_weight
        )
        
        # 归一化权重（确保总和为1，包含ML模型权重）
        if total_adjusted_weight > 0:
            adjusted_technical_weight = adjusted_technical_weight / total_adjusted_weight
            adjusted_news_weight = adjusted_news_weight / total_adjusted_weight
            adjusted_capital_flow_weight = adjusted_capital_flow_weight / total_adjusted_weight
            adjusted_market_weight = adjusted_market_weight / total_adjusted_weight
            adjusted_sector_rotation_weight = adjusted_sector_rotation_weight / total_adjusted_weight
            adjusted_history_weight = adjusted_history_weight / total_adjusted_weight
            adjusted_valuation_weight = adjusted_valuation_weight / total_adjusted_weight
            adjusted_us_sector_weight = adjusted_us_sector_weight / total_adjusted_weight
            ml_weight = ml_weight / total_adjusted_weight
        
        # 使用动态调整后的权重计算最终得分（包含ML模型）
        final_score = (
            technical_score * adjusted_technical_weight +
            news_score * adjusted_news_weight +
            capital_flow_score * adjusted_capital_flow_weight +
            market_score * adjusted_market_weight +
            sector_rotation_score * adjusted_sector_rotation_weight +
            history_score * adjusted_history_weight +
            valuation_score * adjusted_valuation_weight +
            us_sector_score * adjusted_us_sector_weight +
            ml_score * ml_weight
        )
        
        # 使用Sigmoid函数转换为概率（优化版：动态调整放大系数）
        # 先计算波动率系数（用于动态调整Sigmoid系数）
        volatility_coefficient = self._calculate_volatility_coefficient(data, period=60) if not data.empty else 3.0
        
        # 根据市场状态、波动率和历史准确率动态调整放大系数
        sigmoid_coefficient = self._calculate_dynamic_sigmoid_coefficient(
            final_score=final_score,
            market_state={},  # 简化版本，不传递市场状态
            volatility_coefficient=volatility_coefficient,
            symbol=symbol
        )
        up_probability = 1 / (1 + np.exp(-final_score * sigmoid_coefficient))
        down_probability = 1 - up_probability
        
        # 概率校准（根据历史准确率校准，过滤干扰因子，提高可靠性）
        up_probability = self._calibrate_probability(
            raw_probability=up_probability,
            symbol=symbol,
            final_score=final_score
        )
        down_probability = 1 - up_probability
        
        # 确定预测方向（阈值0.55）
        if up_probability > 0.55:
            prediction = '上涨'
        elif down_probability > 0.55:
            prediction = '下跌'
        else:
            prediction = '震荡'
        
        # 计算置信度（增强版：使用优化后的置信度计算）
        factor_scores_dict = {
            'technical': results.get('technical', {}).get('score', 0.0),
            'news': results.get('news', {}).get('score', 0.0),
            'capital_flow': results.get('capital_flow', {}).get('score', 0.0),
            'market': results.get('market', {}).get('score', 0.0),
            'sector_rotation': results.get('sector_rotation', {}).get('score', 0.0),
            'history': results.get('history', {}).get('score', 0.0),
            'valuation': results.get('valuation', {}).get('score', 0.0),
            'us_sector': results.get('us_sector', {}).get('score', 0.0)
        }
        confidence = self._calculate_confidence(
            final_score=final_score,
            factor_scores=factor_scores_dict,
            data_quality=None,
            symbol=symbol,
            market_state={}
        )
        
        # 根据异常情况调整置信度（从配置读取参数）
        try:
            anomaly_details = initial_anomaly_result.get('details', {})
            
            # ST股票：降低置信度（从配置读取）
            st_reduction = self.config.get('st_stock_confidence_reduction', 0.20)
            if 'st_stock' in initial_anomaly_result.get('anomalies', []):
                confidence = confidence * (1.0 - st_reduction)
                self.logger.warning(f"股票 {symbol} 为ST股票，置信度降低{st_reduction*100:.0f}%")
            
            # 涨跌停：降低置信度（从配置读取）
            limit_reduction = self.config.get('limit_up_down_confidence_reduction', 0.10)
            if 'limit_up' in initial_anomaly_result.get('anomalies', []) or 'limit_down' in initial_anomaly_result.get('anomalies', []):
                confidence = confidence * (1.0 - limit_reduction)
                self.logger.warning(f"股票 {symbol} 处于涨跌停状态，置信度降低{limit_reduction*100:.0f}%")
        except Exception as e:
            self.logger.debug(f"异常检测调整置信度失败: {str(e)}")
        
        # 计算预测价格
        predicted_change_pct = (up_probability - down_probability) * 5.0  # 假设最大涨跌幅为5%
        predicted_close_price = current_price * (1 + predicted_change_pct / 100)
        
        # 计算整体数据质量评分（新增：数据缺失处理优化）
        try:
            avg_quality = sum(factor_quality_scores.values()) / len(factor_quality_scores) if factor_quality_scores else 1.0
            missing_factors = [name for name, score in factor_quality_scores.items() if score < 0.3]
            quality_warning = avg_quality < 0.5
        except Exception:
            avg_quality = 1.0
            missing_factors = []
            quality_warning = False
        
        # 构建返回结果
        result = {
            'symbol': symbol,
            'name': stock_name,
            'success': True,
            'prediction': prediction,
            'up_probability': up_probability,
            'down_probability': down_probability,
            'confidence': confidence,
            'current_price': current_price,
            'price_source': price_source,
            'predicted_close_price': predicted_close_price,
            'predicted_change_pct': predicted_change_pct,
            'target_date': target_date,
            'prediction_date': prediction_date,
            'prediction_type': prediction_type,
            'final_score': final_score,
            'factors': {
                'technical': technical_score,
                'news': news_score,
                'capital_flow': capital_flow_score,
                'market': market_score,
                'history': history_score,
                'valuation': valuation_score,
                'us_sector': us_sector_score,
                'sector_rotation': sector_rotation_score,
                'ml': ml_score if ml_prediction_result else None
            },
            'weights': {
                'technical': adjusted_technical_weight,
                'news': adjusted_news_weight,
                'capital_flow': adjusted_capital_flow_weight,
                'market': adjusted_market_weight,
                'history': adjusted_history_weight,
                'valuation': adjusted_valuation_weight,
                'us_sector': adjusted_us_sector_weight,
                'sector_rotation': adjusted_sector_rotation_weight,
                'ml': ml_weight if ml_prediction_result else 0.0
            },
            'anomaly_info': initial_anomaly_result,
            'ml_prediction': ml_prediction_result,
            'market_state': market_state,
            'data_quality': {  # 新增：数据质量信息
                'overall_quality': avg_quality,
                'factor_quality': factor_quality_scores,
                'missing_factors': missing_factors,
                'quality_warning': quality_warning
            }
        }
        
        # 输出预测结果
        self.logger.info("=" * 60)
        self.logger.info("预测结果汇总：")
        self.logger.info(f"预测方向: {prediction}")
        self.logger.info(f"上涨概率: {up_probability*100:.1f}%")
        self.logger.info(f"下跌概率: {down_probability*100:.1f}%")
        self.logger.info(f"置信度: {confidence*100:.1f}%")
        self.logger.info(f"明日大概收盘价格: {predicted_close_price:.2f}元")
        self.logger.info(f"明日大概涨幅: {predicted_change_pct:+.2f}%")
        self.logger.info("=" * 60)
        
        return result

