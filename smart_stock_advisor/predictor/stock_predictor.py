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

spec = importlib.util.spec_from_file_location("config", 
    os.path.join(project_root, "config.py"))
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
PREDICTION_CONFIG = config_module.PREDICTION_CONFIG
INDICATOR_CONFIG = config_module.INDICATOR_CONFIG
NEWS_CONFIG = config_module.NEWS_CONFIG
# TuShare token（如果在config中配置，则用于新闻源）
TUSHARE_TOKEN = getattr(config_module, "TUSHARE_TOKEN", None)

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
    
    def __init__(self):
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
                # 传入 TuShare token，用于TuShare新闻源
                self.news_source = UnifiedNewsSource(tushare_token=TUSHARE_TOKEN)
                self.sentiment_analyzer = NewsSentimentAnalyzer()
                self.news_enabled = True
            except Exception as e:
                self.logger.warning(f"新闻模块初始化失败: {str(e)}")
                self.news_enabled = False
        else:
            self.news_enabled = False
        
        # 加载配置（支持从数据库动态加载）
        self.config = self._load_prediction_config()
        self.indicator_config = self._load_indicator_config()
    
    def _load_prediction_config(self) -> Dict:
        """加载预测配置（优先从数据库，否则使用config.py默认值）"""
        try:
            # 尝试从数据库加载激活的配置
            from utils.prediction_config_manager import PredictionConfigManager
            manager = PredictionConfigManager()
            active_config = manager.get_config()  # 获取激活的配置
            
            if active_config and active_config.get('prediction'):
                # 合并配置，确保所有必需的键都存在
                config = PREDICTION_CONFIG.copy()
                config.update(active_config['prediction'])
                self.logger.info("已从数据库加载预测配置")
                return config
        except Exception as e:
            self.logger.warning(f"从数据库加载配置失败，使用config.py默认值: {str(e)}")
        
        # 使用config.py中的默认配置
        return PREDICTION_CONFIG.copy()
    
    def _load_indicator_config(self) -> Dict:
        """加载技术指标配置（优先从数据库，否则使用config.py默认值）"""
        try:
            # 尝试从数据库加载激活的配置
            from utils.prediction_config_manager import PredictionConfigManager
            manager = PredictionConfigManager()
            active_config = manager.get_config()  # 获取激活的配置
            
            if active_config and active_config.get('indicator'):
                # 合并配置，确保所有必需的键都存在
                config = INDICATOR_CONFIG.copy()
                config.update(active_config['indicator'])
                self.logger.info("已从数据库加载技术指标配置")
                return config
        except Exception as e:
            self.logger.warning(f"从数据库加载配置失败，使用config.py默认值: {str(e)}")
        
        # 使用config.py中的默认配置
        return INDICATOR_CONFIG.copy()
    
    def refresh_config(self):
        """刷新配置（支持热更新）"""
        self.config = self._load_prediction_config()
        self.indicator_config = self._load_indicator_config()
        self.logger.info("配置已刷新")
    
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
            
            # 5.1. 换手率分析（新增）
            turnover_rate_score = 0.0
            try:
                # 尝试获取换手率数据
                stock_info = self.data_source.get_stock_info(symbol)
                turnover_rate = None
                
                # 查找换手率字段
                for key in ['换手率', 'turnover_rate', 'Turnover', 'turnover']:
                    if key in stock_info:
                        try:
                            val = stock_info[key]
                            if isinstance(val, str):
                                val = val.replace('%', '').replace(',', '').strip()
                            turnover_rate = float(val)
                            break
                        except:
                            continue
                
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
                    signals['换手率'] = '数据不足'
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
    
    def calculate_news_score(self, symbol: str) -> Dict:
        """
        计算新闻情感得分
        包括直接提到股票的新闻和行业/概念相关的新闻
        根据利空/利好动态调整权重
        
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
            # 获取股票行业信息
            industry_keywords = []
            industry_info = {'industry': '', 'concepts': [], 'industry_keywords': []}
            try:
                industry_info = self.data_source.get_stock_industry_info(symbol)
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
            
            # 优先从数据库获取当天新闻
            direct_news = []
            market_news = []
            use_database_news = False
            
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
                        self.logger.info(f"从数据库获取到 {symbol} 当天 {len(direct_news)} 条直接新闻")
                    
                    # 从数据库获取当天市场新闻
                    db_market_news = news_storage.get_today_market_news(
                        limit=NEWS_CONFIG['news_count'] * 3
                    )
                    
                    if db_market_news:
                        market_news = db_market_news
                        use_database_news = True
                        self.logger.info(f"从数据库获取到当天 {len(market_news)} 条市场新闻")
            except Exception as e:
                self.logger.debug(f"从数据库获取新闻失败，将使用API: {str(e)}")
            
            # 如果数据库没有新闻，从API获取
            if not use_database_news or not market_news:
                try:
                    # 获取更多市场新闻用于筛选
                    if not market_news:
                        market_news = self.news_source.get_market_news(NEWS_CONFIG['news_count'] * 3)
                    
                    # 获取直接提到股票的新闻
                    if not direct_news:
                        if hasattr(self.news_source, 'sources'):
                            for source_name, source in self.news_source.sources:
                                try:
                                    news = source.get_stock_news(symbol, NEWS_CONFIG['news_count'])
                                    for n in news:
                                        n['relevance'] = 'direct'
                                        n['relevance_score'] = 1.0  # 直接相关，相关性为1
                                    direct_news.extend(news)
                                except Exception as e:
                                    self.logger.debug(f"从 {source_name} 获取新闻失败: {str(e)}")
                except Exception as e:
                    self.logger.debug(f"从API获取新闻失败: {str(e)}")
            
            # 从市场新闻中筛选行业相关新闻（更智能的判断）
            industry_news = []
            for news in market_news:
                # 检查是否已经包含在直接新闻中（去重）
                if any(n.get('title') == news.get('title') for n in direct_news):
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
            
            # 分析情感
            sentiment_results = self.sentiment_analyzer.analyze_batch(news_list)
            aggregated = self.sentiment_analyzer.get_aggregated_sentiment(sentiment_results)
            
            # 统计利空/利好消息（包含政策新闻权重提升）
            positive_news = []
            negative_news = []
            neutral_news = []
            
            for i, news in enumerate(sentiment_results):
                sentiment = news.get('sentiment', {})
                sentiment_type = sentiment.get('sentiment', 'neutral')
                score = sentiment.get('score', 0.0)
                confidence = sentiment.get('confidence', 0.0)
                relevance_score = news.get('relevance_score', 0.5)
                is_policy = news_list[i].get('is_policy', False) if i < len(news_list) else False
                policy_type = news_list[i].get('policy_type') if i < len(news_list) else None
                
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
                        'news': news,
                        'score': adjusted_score,
                        'confidence': confidence,
                        'relevance': relevance_score
                    })
                elif sentiment_type == 'negative' and adjusted_score < -0.1:
                    negative_news.append({
                        'news': news,
                        'score': adjusted_score,
                        'confidence': confidence,
                        'relevance': relevance_score
                    })
                else:
                    neutral_news.append(news)
            
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
                'policy_classification': policy_classification  # 新增：政策新闻分类
            }
            
            # 保存新闻情感数据到CSV
            if self.data_storage:
                self.data_storage.save_news_sentiment(symbol, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"计算新闻得分失败: {str(e)}")
            return {'score': 0.0, 'sentiment': 'neutral', 'news_count': 0, 'confidence': 0.0, 'weight_multiplier': 1.0}
    
    def calculate_market_score(self, data: pd.DataFrame, symbol: str = None) -> Dict:
        """
        计算市场情绪得分（改进：包含大盘指数影响）
        
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
                # 获取主要指数数据
                indices_data = self.data_source.get_all_market_indices(days=20)
                
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
            try:
                if symbol:
                    industry_info = self.data_source.get_stock_industry_info(symbol)
                    industry = industry_info.get('industry', '')
                    
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
    
    def calculate_market_sentiment_index(self) -> Dict:
        """
        计算市场情绪指标（恐慌指数、贪婪指数）
        - 恐慌指数：基于下跌股票比例、跌停股票数量、成交量放大
        - 贪婪指数：基于上涨股票比例、涨停股票数量
        - 情绪化交易识别
        
        Returns:
            市场情绪指标字典，包含：
            - fear_index: 恐慌指数（0-100）
            - greed_index: 贪婪指数（0-100）
            - sentiment: 综合情绪（'fear'/'greed'/'neutral'）
            - suggestion: 建议
        """
        try:
            # 获取市场统计数据
            market_stats = self.data_source.get_market_statistics()
            
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
    
    def calculate_us_sector_score(self, symbol: str) -> Dict:
        """
        计算美股板块得分（根据股票所属行业，获取对应美股板块的走势）
        
        Returns:
            {
                'score': 美股板块得分 (-1到1),
                'sector': 对应的美股板块名称,
                'trend': 'up'/'down'/'neutral',
                'change_pct': 涨跌幅百分比
            }
        """
        try:
            # 获取股票的行业信息
            industry_info = self.data_source.get_stock_industry_info(symbol)
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
            us_data = self.data_source.get_us_sector_data(matched_sector if matched_sector != '整体市场' else None, days=5)
            
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
    
    def calculate_valuation_score(self, symbol: str) -> Dict:
        """
        计算估值指标得分（PE、PB）
        
        Returns:
            {
                'score': 估值得分 (-1到1),
                'pe_ratio': 市盈率,
                'pb_ratio': 市净率,
                'valuation': 'undervalued'/'overvalued'/'fair'
            }
        """
        try:
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
    
    def calculate_capital_flow_score(self, symbol: str) -> Dict:
        """
        计算资金流向得分
        包括：北向资金、融资融券、主力资金
        
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
                north_bound = self.data_source.get_north_bound_capital(days=5)
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
                margin_data = self.data_source.get_margin_trading_data(symbol, days=5)
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
                main_force = self.data_source.get_main_force_capital(symbol, days=5)
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
    
    def calculate_sector_rotation_score(self, symbol: str) -> Dict:
        """
        计算板块轮动得分
        分析股票所属板块的热度、资金流向和轮动趋势
        
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
            # 获取股票行业信息
            industry_info = self.data_source.get_stock_industry_info(symbol)
            industry = industry_info.get('industry', '')
            concepts = industry_info.get('concepts', [])
            
            # 获取板块表现数据
            sector_data = self.data_source.get_sector_performance(days=5)
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
    
    def calculate_trading_suggestions(self, data: pd.DataFrame, prediction_result: Dict) -> Dict:
        """
        计算交易建议（买入价、卖出价、竞价建议）
        结合市场整体行情，给出更激进的交易建议
        
        Returns:
            {
                'buy_price': 建议买入价,
                'sell_price': 建议卖出价,
                'auction_entry': 是否建议竞价进入,
                'auction_price': 竞价价格,
                'stop_loss': 止损价,
                'take_profit': 止盈价
            }
        """
        try:
            current_price = data['close'].iloc[-1]
            prediction = prediction_result['prediction']
            up_prob = prediction_result['up_probability']
            down_prob = prediction_result['down_probability']
            confidence = prediction_result['confidence']
            market_overall = prediction_result.get('market_overall', {})
            
            # 获取市场整体行情
            market_bullish = False
            market_up_prob = 0.5
            if market_overall.get('success', False):
                market_pred = market_overall.get('overall_prediction', '震荡')
                market_up_prob = market_overall.get('overall_up_probability', 0.5)
                market_bullish = (market_pred == '上涨' or market_up_prob > 0.55)
            
            # 计算最近波动幅度
            recent_high = data['high'].tail(10).max()
            recent_low = data['low'].tail(10).min()
            volatility = (recent_high - recent_low) / current_price
            
            # 计算技术指标强度（用于判断激进程度）
            ma5 = data['close'].tail(5).mean()
            ma10 = data['close'].tail(10).mean()
            ma20 = data['close'].tail(20).mean()
            tech_strength = 0
            if ma5 > ma10 > ma20:
                tech_strength = 1  # 强势
            elif ma5 < ma10 < ma20:
                tech_strength = -1  # 弱势
            
            suggestions = {}
            
            # 买入价建议（更激进）
            # 结合市场行情和技术面，给出更积极的买入价
            if prediction == '上涨' and up_prob > 0.5:
                # 看涨，结合市场情况调整
                base_multiplier = 0.3
                if market_bullish:
                    base_multiplier += 0.2  # 市场看涨，更激进
                if tech_strength > 0:
                    base_multiplier += 0.1  # 技术面强势，更激进
                if up_prob > 0.7:
                    base_multiplier += 0.2  # 预测很强，更激进
                
                buy_price = current_price * (1 + volatility * base_multiplier)
                # 确保不超过当前价的5%
                buy_price = min(buy_price, current_price * 1.05)
            elif prediction == '下跌' and down_prob > 0.55:
                # 看跌，但结合市场情况，如果市场整体看涨，可以稍微激进
                if market_bullish and market_up_prob > 0.6:
                    # 市场整体看涨，即使个股看跌，也可以考虑在较低位置买入
                    buy_price = current_price * (1 - volatility * 0.3)
                else:
                    buy_price = current_price * (1 - volatility * 0.5)
            else:
                # 震荡，结合市场情况
                if market_bullish:
                    # 市场看涨，可以稍微激进
                    buy_price = recent_low * 1.03
                else:
                    buy_price = recent_low * 1.02
            
            suggestions['buy_price'] = round(buy_price, 2)
            
            # 卖出价建议（更激进，设置更高的目标）
            if prediction == '上涨' and up_prob > 0.5:
                # 看涨，结合市场情况设置更高的卖出价
                base_multiplier = 1.5
                if market_bullish:
                    base_multiplier += 0.5  # 市场看涨，目标更高
                if tech_strength > 0:
                    base_multiplier += 0.3  # 技术面强势，目标更高
                if up_prob > 0.7:
                    base_multiplier += 0.5  # 预测很强，目标更高
                
                sell_price = current_price * (1 + volatility * base_multiplier)
            elif prediction == '下跌' and down_prob > 0.55:
                # 看跌，但如果市场整体看涨，可以设置稍高的卖出价
                if market_bullish and market_up_prob > 0.6:
                    sell_price = current_price * (1 - volatility * 0.1)
                else:
                    sell_price = current_price * (1 - volatility * 0.3)
            else:
                # 震荡，结合市场情况
                if market_bullish:
                    sell_price = recent_high * 1.02  # 市场看涨，可以稍微激进
                else:
                    sell_price = recent_high * 0.98
            
            suggestions['sell_price'] = round(sell_price, 2)
            
            # 竞价进入建议（改进逻辑，给出明确的竞价建议）
            # 综合考虑：个股预测、市场整体、置信度、技术面
            auction_entry = False
            auction_price = None
            auction_reason = ""
            
            # 情况1：强烈看涨（个股+市场都看涨）
            if prediction == '上涨' and up_prob > 0.6 and market_bullish and market_up_prob > 0.55:
                auction_entry = True
                if up_prob > 0.75 and market_up_prob > 0.6:
                    auction_price = round(current_price * 1.03, 2)  # 当前价+3%，激进
                    auction_reason = "强烈看涨（个股+市场双重利好）"
                elif up_prob > 0.65:
                    auction_price = round(current_price * 1.02, 2)  # 当前价+2%
                    auction_reason = "看涨（个股+市场利好）"
                else:
                    auction_price = round(current_price * 1.01, 2)  # 当前价+1%
                    auction_reason = "看涨（个股+市场利好）"
            
            # 情况2：个股强烈看涨，但市场一般
            elif prediction == '上涨' and up_prob > 0.7 and confidence > 0.65:
                auction_entry = True
                if up_prob > 0.8:
                    auction_price = round(current_price * 1.025, 2)  # 当前价+2.5%
                    auction_reason = "个股强烈看涨"
                else:
                    auction_price = round(current_price * 1.015, 2)  # 当前价+1.5%
                    auction_reason = "个股看涨"
            
            # 情况3：市场强烈看涨，个股中性或略涨
            elif market_bullish and market_up_prob > 0.65 and up_prob > 0.5:
                auction_entry = True
                auction_price = round(current_price * 1.01, 2)  # 当前价+1%
                auction_reason = "市场整体看涨"
            
            # 情况4：技术面强势，即使预测中性也可以考虑
            elif tech_strength > 0 and up_prob > 0.52 and confidence > 0.55:
                auction_entry = True
                auction_price = round(current_price * 1.005, 2)  # 当前价+0.5%
                auction_reason = "技术面强势"
            
            # 情况5：看跌，但市场强烈看涨，可以考虑低吸
            elif prediction == '下跌' and market_bullish and market_up_prob > 0.7:
                auction_entry = True
                auction_price = round(current_price * 0.98, 2)  # 当前价-2%，低吸
                auction_reason = "市场强烈看涨，低吸机会"
            
            # 如果以上都不满足，给出不竞价的明确理由
            if not auction_entry:
                if prediction == '下跌' and down_prob > 0.6:
                    auction_reason = "看跌，不建议竞价"
                elif confidence < 0.5:
                    auction_reason = "置信度较低，不建议竞价"
                elif not market_bullish and up_prob < 0.55:
                    auction_reason = "市场与个股均不乐观，不建议竞价"
                else:
                    auction_reason = "震荡行情，建议观察后决定"
            
            suggestions['auction_entry'] = auction_entry
            suggestions['auction_price'] = auction_price
            suggestions['auction_reason'] = auction_reason
            
            # 止损价（建议买入价的-5%）
            suggestions['stop_loss'] = round(buy_price * 0.95, 2)
            
            # 止盈价（建议买入价的+12%或卖出价，更激进）
            suggestions['take_profit'] = round(min(buy_price * 1.12, sell_price), 2)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"计算交易建议失败: {str(e)}")
            return {
                'buy_price': None,
                'sell_price': None,
                'auction_entry': False,
                'auction_price': None,
                'stop_loss': None,
                'take_profit': None
            }
    
    def predict_market_overall(self) -> Dict:
        """
        预测沪深股市整体行情
        
        Returns:
            市场整体行情预测结果
        """
        try:
            self.logger.info("\n步骤0: 分析市场整体行情...")
            
            # 获取主要指数数据
            indices_data = self.data_source.get_all_market_indices(days=60)
            
            if not indices_data:
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
                
                # 计算市场情绪得分
                market_result = self.calculate_market_score(index_data)
                market_score = market_result['score']
                
                # 综合得分（技术指标70%，市场情绪30%）
                index_score = tech_score * 0.7 + market_score * 0.3
                
                # 转换为涨跌概率
                up_prob = 1 / (1 + np.exp(-index_score * 3))
                down_prob = 1 - up_prob
                
                # 确定预测方向
                if up_prob > 0.6:
                    prediction = '上涨'
                elif down_prob > 0.6:
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
                return {
                    'success': False,
                    'message': '无法获取有效的市场指数数据'
                }
            
            # 计算整体市场得分
            overall_score = overall_score / index_count
            
            # 转换为整体涨跌概率
            overall_up_prob = 1 / (1 + np.exp(-overall_score * 3))
            overall_down_prob = 1 - overall_up_prob
            
            # 确定整体预测方向
            if overall_up_prob > 0.6:
                overall_prediction = '上涨'
            elif overall_down_prob > 0.6:
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
        # 1. 基础置信度（基于得分绝对值）
        base_confidence = min(abs(final_score) * 0.5 + 0.5, 1.0)
        
        # 2. 因子一致性（所有因子方向一致时提高置信度）
        factor_consistency = self._calculate_factor_consistency(final_score, factor_scores)
        
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
        
        # 计算基础置信度（加权平均）
        base_calculated_confidence = (
            base_confidence * 0.40 +      # 基础置信度权重40%
            factor_consistency * 0.30 +   # 因子一致性权重30%
            quality_score * 0.30          # 数据质量权重30%
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
    
    def _calculate_factor_consistency(self, final_score: float, factor_scores: Dict) -> float:
        """
        计算因子一致性
        
        Args:
            final_score: 最终得分
            factor_scores: 各因子得分字典
        
        Returns:
            一致性得分（0-1），越高表示因子方向越一致
        """
        if not factor_scores:
            return 0.5
        
        # 确定最终方向
        final_direction = 1 if final_score > 0 else -1 if final_score < 0 else 0
        
        if final_direction == 0:
            return 0.5  # 中性，一致性中等
        
        # 计算每个因子的方向一致性
        consistent_count = 0
        total_count = 0
        
        for factor_name, factor_score in factor_scores.items():
            if abs(factor_score) < 0.01:
                # 中性因子，不计入一致性计算
                continue
            
            factor_direction = 1 if factor_score > 0 else -1
            if factor_direction == final_direction:
                consistent_count += 1
            total_count += 1
        
        if total_count == 0:
            return 0.5
        
        # 一致性比例
        consistency_ratio = consistent_count / total_count
        
        # 转换为0-1得分（50%一致性对应0.5，100%一致性对应1.0）
        consistency_score = 0.5 + (consistency_ratio - 0.5) * 0.5
        
        return max(0.0, min(1.0, consistency_score))
    
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
    
    def predict(self, symbol: str) -> Dict:
        """
        预测股票明天的涨跌概率
        
        Args:
            symbol: 股票代码
            
        Returns:
            预测结果字典
        """
        self.logger.info("=" * 60)
        self.logger.info(f"开始分析股票: {symbol}")
        self.logger.info("=" * 60)
        
        # 根据时间判断预测日期
        target_date, date_desc = self.get_target_date()
        prediction_date = datetime.now().strftime('%Y-%m-%d')  # 预测日期（当前日期）
        self.logger.info(f"预测日期（{date_desc}）: {target_date}")
        
        # 1. 获取股票数据（必须先获取，其他分析依赖此数据）
        self.logger.info("步骤1: 获取股票数据...")
        # 优先从数据库获取历史数据（已优化）
        data = self.data_source.get_stock_data(symbol, days=self.config['lookback_days'])
        
        if data.empty:
            return {
                'symbol': symbol,
                'success': False,
                'message': '无法获取股票数据'
            }
        
        # 获取当前价格（优先使用实时数据，如果未收盘）
        current_price = data['close'].iloc[-1]
        
        # 尝试获取实时价格（如果市场未收盘）
        try:
            realtime_quote = self.data_source.get_realtime_quote(symbol)
            if realtime_quote and realtime_quote.get('current_price'):
                current_price = float(realtime_quote.get('current_price'))
                self.logger.info(f"使用实时价格: {current_price:.2f}元")
            else:
                self.logger.info(f"使用历史数据最新价格: {current_price:.2f}元")
        except Exception as e:
            self.logger.debug(f"获取实时价格失败，使用历史数据: {str(e)}")
        
        self.logger.info(f"当前价格: {current_price:.2f}元")
        
        # 获取股票名称
        stock_name = '未知'
        try:
            # 尝试从股票列表中获取名称
            stock_list = self.data_source.get_all_stock_list(limit=None, sort_by_turnover=False)
            if stock_list:
                for stock in stock_list:
                    if str(stock.get('symbol', '')).strip() == str(symbol).strip():
                        stock_name = stock.get('name', '未知')
                        break
            # 如果没找到，尝试通过其他方式获取
            if stock_name == '未知':
                stock_info = self.data_source.get_stock_info(symbol)
                stock_name = stock_info.get('name', stock_info.get('股票简称', stock_info.get('股票名称', '未知')))
                if not stock_name or stock_name == '':
                    stock_name = '未知'
        except Exception as e:
            self.logger.warning(f"获取股票名称失败: {str(e)}，使用默认值'未知'")
            stock_name = '未知'
        
        # 使用多线程并行执行独立分析任务（不需要股票历史数据的分析）
        self.logger.info("\n步骤2-5.7: 并行分析多个指标（使用多线程加速）...")
        
        # 定义需要并行执行的任务（独立分析，只需要symbol）
        independent_tasks = {
            'market_overall': lambda: self.predict_market_overall(),
            'news': lambda: self.calculate_news_score(symbol),
            'capital_flow': lambda: self.calculate_capital_flow_score(symbol),
            'valuation': lambda: self.calculate_valuation_score(symbol),
            'us_sector': lambda: self.calculate_us_sector_score(symbol),
            'sector_rotation': lambda: self.calculate_sector_rotation_score(symbol),
            'market_sentiment_index': lambda: self.calculate_market_sentiment_index(),  # 市场情绪指标（恐慌/贪婪指数）
        }
        
        # 定义依赖股票数据的任务（需要data）
        data_dependent_tasks = {
            'technical': lambda: self.calculate_technical_score(data, symbol),
            'market': lambda: self.calculate_market_score(data, symbol),
            'history': lambda: self.calculate_history_score(data),
        }
        
        # 存储结果的字典
        results = {}
        
        # 第一阶段：并行执行独立分析任务
        self.logger.info("  并行执行独立分析任务（市场整体、新闻、资金流向、估值、美股板块、板块轮动）...")
        
        # 尝试使用线程池，如果失败则使用单线程模式
        use_thread_pool = True
        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
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
                        elif task_name == 'valuation':
                            results[task_name] = {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None}
                        elif task_name == 'us_sector':
                            results[task_name] = {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0}
                        elif task_name == 'sector_rotation':
                            results[task_name] = {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'}
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
                    elif task_name == 'valuation':
                        results[task_name] = {'score': 0.0, 'pe_ratio': None, 'pb_ratio': None}
                    elif task_name == 'us_sector':
                        results[task_name] = {'score': 0.0, 'sector': 'unknown', 'change_pct': 0.0}
                    elif task_name == 'sector_rotation':
                        results[task_name] = {'score': 0.0, 'sector_name': 'unknown', 'trend': 'neutral'}
        
        # 第二阶段：并行执行依赖股票数据的分析任务
        self.logger.info("  并行执行依赖股票数据的分析任务（技术指标、市场情绪、历史模式）...")
        
        if use_thread_pool:
            try:
                with ThreadPoolExecutor(max_workers=3) as executor:
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
                    self.logger.warning(f"    ✗ {task_name} 分析失败: {str(e)}")
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
            adjusted_technical_weight = optimized_weights.get('technical_weight', self.config.get('technical_weight', 0.20))
            adjusted_news_weight = optimized_weights.get('news_weight', self.config['news_weight']) * news_weight_multiplier
            adjusted_capital_flow_weight = optimized_weights.get('capital_flow_weight', self.config.get('capital_flow_weight', 0.18))
            adjusted_market_weight = optimized_weights.get('market_weight', self.config.get('market_weight', 0.17))
            adjusted_sector_rotation_weight = optimized_weights.get('sector_rotation_weight', self.config.get('sector_rotation_weight', 0.05))
            adjusted_history_weight = optimized_weights.get('history_weight', self.config.get('history_weight', 0.08))
            adjusted_valuation_weight = optimized_weights.get('valuation_weight', self.config.get('valuation_weight', 0.02))
            adjusted_us_sector_weight = optimized_weights.get('us_sector_weight', self.config.get('us_sector_weight', 0.05))
            
            self.logger.info(f"权重优化结果: 技术指标={adjusted_technical_weight:.3f}, "
                           f"新闻={adjusted_news_weight:.3f}, "
                           f"资金流向={adjusted_capital_flow_weight:.3f}, "
                           f"市场={adjusted_market_weight:.3f}")
        else:
            # 如果是新股票或数据不足，使用保守的默认权重（不依赖历史优化）
            if is_new_stock_or_insufficient_data:
                self.logger.info(f"股票 {symbol} 数据不足，使用保守的默认权重配置")
            # 如果权重优化失败，回退到基于市场状态的调整
            technical_multiplier = weight_multipliers.get('technical_weight_multiplier', 1.0)
            news_multiplier = weight_multipliers.get('news_weight_multiplier', 1.0) * news_weight_multiplier
            capital_flow_multiplier = weight_multipliers.get('capital_flow_weight_multiplier', 1.0)
            market_multiplier = weight_multipliers.get('market_weight_multiplier', 1.0)
            
            # 调整后的权重
            adjusted_technical_weight = self.config.get('technical_weight', 0.20) * technical_multiplier
            adjusted_news_weight = self.config['news_weight'] * news_multiplier
            adjusted_capital_flow_weight = self.config.get('capital_flow_weight', 0.18) * capital_flow_multiplier
            adjusted_market_weight = self.config.get('market_weight', 0.17) * market_multiplier
            adjusted_sector_rotation_weight = self.config.get('sector_rotation_weight', 0.05)
            adjusted_history_weight = self.config.get('history_weight', 0.08)
            adjusted_valuation_weight = self.config.get('valuation_weight', 0.02)
            adjusted_us_sector_weight = self.config.get('us_sector_weight', 0.05)
        
        # 计算权重总和（用于归一化）
        total_adjusted_weight = (
            adjusted_technical_weight +
            adjusted_news_weight +
            adjusted_capital_flow_weight +
            adjusted_market_weight +
            adjusted_sector_rotation_weight +
            adjusted_history_weight +
            adjusted_valuation_weight +
            adjusted_us_sector_weight
        )
        
        # 归一化权重（确保总和为1）
        if total_adjusted_weight > 0:
            adjusted_technical_weight = adjusted_technical_weight / total_adjusted_weight
            adjusted_news_weight = adjusted_news_weight / total_adjusted_weight
            adjusted_capital_flow_weight = adjusted_capital_flow_weight / total_adjusted_weight
            adjusted_market_weight = adjusted_market_weight / total_adjusted_weight
            adjusted_sector_rotation_weight = adjusted_sector_rotation_weight / total_adjusted_weight
            adjusted_history_weight = adjusted_history_weight / total_adjusted_weight
            adjusted_valuation_weight = adjusted_valuation_weight / total_adjusted_weight
            adjusted_us_sector_weight = adjusted_us_sector_weight / total_adjusted_weight
        
        # 使用动态调整后的权重计算最终得分（使用优化后的权重）
        final_score = (
            technical_score * adjusted_technical_weight +
            news_score * adjusted_news_weight +
            capital_flow_score * adjusted_capital_flow_weight +
            market_score * adjusted_market_weight +
            sector_rotation_score * adjusted_sector_rotation_weight +
            history_score * adjusted_history_weight +
            valuation_score * adjusted_valuation_weight +
            us_sector_score * adjusted_us_sector_weight
        )
        
        # 转换为涨跌概率
        # 使用sigmoid函数将得分转换为概率
        up_probability = 1 / (1 + np.exp(-final_score * 3))  # 放大系数
        down_probability = 1 - up_probability
        
        # 计算置信度（增强版：考虑历史准确率、一致性、数据时效性、校准）
        # 如果是新股票或数据不足，降低置信度阈值
        min_confidence_threshold = self.config['min_confidence']
        if is_new_stock_or_insufficient_data:
            # 数据不足时，使用更保守的置信度阈值（降低20%）
            min_confidence_threshold = self.config['min_confidence'] * 0.8
            self.logger.debug(f"股票 {symbol} 数据不足，置信度阈值从 {self.config['min_confidence']:.2f} 降低到 {min_confidence_threshold:.2f}")
        
        confidence = self._calculate_confidence(
            final_score=final_score,
            factor_scores={
                'technical': technical_score,
                'news': news_score,
                'capital_flow': capital_flow_score,
                'market': market_score,
                'sector_rotation': sector_rotation_score,
                'history': history_score,
                'valuation': valuation_score,
                'us_sector': us_sector_score
            },
            data_quality=None,  # 可以从外部传入数据质量信息
            symbol=symbol,
            market_state=market_state  # 传递市场状态信息用于置信度计算
        )
        
        # 如果是新股票或数据不足，进一步降低置信度
        if is_new_stock_or_insufficient_data:
            # 数据不足时，置信度降低15%
            confidence = confidence * 0.85
            self.logger.debug(f"股票 {symbol} 数据不足，置信度从 {confidence / 0.85:.3f} 降低到 {confidence:.3f}")
        
        # 如果置信度太低，降低概率差异
        if confidence < min_confidence_threshold:
            up_probability = 0.5 + (up_probability - 0.5) * (confidence / min_confidence_threshold)
            down_probability = 1 - up_probability
        
        # 确定预测方向
        if up_probability > 0.6:
            prediction = '上涨'
        elif down_probability > 0.6:
            prediction = '下跌'
        else:
            prediction = '震荡'
        
        # 计算明日大概收盘价格和涨幅
        # 基于概率差异和置信度计算预期涨跌幅
        # 使用 sigmoid 函数将概率差异转换为涨跌幅，并考虑置信度
        probability_diff = up_probability - down_probability  # -1 到 1
        # 将概率差异映射到涨跌幅范围（-10% 到 +10%），并乘以置信度
        # 使用 tanh 函数平滑映射，最大涨跌幅为 10%
        max_change_pct = 10.0  # 最大涨跌幅 10%
        predicted_change_pct = np.tanh(probability_diff * 3) * max_change_pct * confidence
        # 计算预测收盘价格
        predicted_close_price = current_price * (1 + predicted_change_pct / 100.0)
        
        self.logger.info(f"预测价格计算: 当前价格={current_price:.2f}元, 预期涨跌幅={predicted_change_pct:.2f}%, 预测收盘价={predicted_close_price:.2f}元")
        
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
        
        summary_parts.append(
            f"综合技术指标、新闻情感、资金流向、市场情绪、板块轮动、历史走势、估值指标和美股板块行情，{market_info}模型认为 {target_date} {symbol} {date_desc}整体走势{direction_text}。"
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
        
        # 添加美股板块信息
        us_sector_info = ""
        if us_sector_name and us_sector_name != 'unknown':
            us_trend_text = '上涨' if us_sector_score > 0.1 else '下跌' if us_sector_score < -0.1 else '震荡'
            us_sector_info = f"对应美股板块（{us_sector_name}）{us_trend_text}（涨跌幅{us_sector_change:+.2f}%，得分{us_sector_score:.2f}），"
        
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
        
        # 添加板块轮动描述
        sector_rotation_desc = f"板块轮动得分 {sector_rotation_score:.2f}（板块：{sector_name}，趋势：{'热门' if sector_trend == 'hot' else '冷门' if sector_trend == 'cold' else '中性'}）"
        
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
        
        summary_parts.append(
            f"技术面得分 {technical_score:.2f}（{ '偏多' if technical_score > 0.1 else '偏空' if technical_score < -0.1 else '中性' }，趋势：{tech_trend}），"
            f"{news_desc}，{capital_flow_desc}，"
            f"市场情绪得分 {market_score:.2f}（趋势：{market_trend}），{sector_rotation_desc}，"
            f"历史模式得分 {history_score:.2f}（{history_pattern}），"
            f"{us_sector_info}估值指标得分 {valuation_score:.2f}{market_state_desc}。"
        )
        summary_parts.append(
            f"在当前参数下，上涨概率约为 {up_probability*100:.1f}%，下跌概率约为 {down_probability*100:.1f}%，综合置信度约为 {confidence*100:.1f}%。"
        )

        summary_text = " ".join(summary_parts)
        
        # 7. 计算交易建议
        self.logger.info("\n步骤7: 计算交易建议...")
        trading_suggestions = self.calculate_trading_suggestions(data, {
            'prediction': prediction,
            'up_probability': up_probability,
            'down_probability': down_probability,
            'confidence': confidence,
            'market_overall': market_overall
        })
        self.logger.info(f"买入建议价: {trading_suggestions['buy_price']}元")
        self.logger.info(f"卖出建议价: {trading_suggestions['sell_price']}元")
        auction_reason = trading_suggestions.get('auction_reason', '')
        if trading_suggestions['auction_entry']:
            self.logger.info(f"建议竞价进入，竞价价格: {trading_suggestions['auction_price']}元，理由: {auction_reason}")
        else:
            self.logger.info(f"竞价建议: {auction_reason}")

        # 保存预测因子数据到CSV（包含所有因子和最终结果）
        if self.data_storage:
            factors_for_storage = {
                'technical': {
                    'score': technical_score,
                    'weight': self.config.get('technical_weight', 0.20),
                    'trend': technical_result['trend']
                },
                'news': {
                    'score': news_score,
                    'weight': self.config.get('news_weight', 0.25),
                    'sentiment': news_result['sentiment']
                },
                'capital_flow': {
                    'score': capital_flow_score,
                    'weight': self.config.get('capital_flow_weight', 0.18),
                    'trend': capital_flow_result['trend']
                },
                'market': {
                    'score': market_score,
                    'weight': self.config.get('market_weight', 0.17),
                    'trend': market_result['trend']
                },
                'sector_rotation': {
                    'score': sector_rotation_score,
                    'weight': self.config.get('sector_rotation_weight', 0.05),
                    'trend': sector_rotation_result.get('trend', 'neutral')
                },
                'history': {
                    'score': history_score,
                    'weight': self.config.get('history_weight', 0.08),
                    'pattern': history_result['pattern']
                },
                'valuation': {
                    'score': valuation_score,
                    'weight': self.config.get('valuation_weight', 0.02),
                    'pe_ratio': pe_ratio,
                    'pb_ratio': pb_ratio
                },
                'us_sector': {
                    'score': us_sector_score,
                    'weight': self.config.get('us_sector_weight', 0.05),
                    'sector': us_sector_name
                },
                'final_score': final_score,
                'up_probability': up_probability,
                'down_probability': down_probability,
                'confidence': confidence
            }
            
            self.data_storage.save_prediction_factors(symbol, factors_for_storage, result)

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
            'prediction_date': prediction_date,  # 预测日期（当前日期）
            'success': True,
            'current_price': current_price,
            'prediction': prediction,
            'up_probability': up_probability,
            'down_probability': down_probability,
            'confidence': confidence,
            'final_score': final_score,
            'predicted_close_price': predicted_close_price,  # 明日大概收盘价格
            'predicted_change_pct': predicted_change_pct,  # 明日大概涨幅百分比
            'market_state': market_state,  # 市场状态信息（新增）
            'market_sentiment_index': market_sentiment_index,  # 市场情绪指标（恐慌/贪婪指数）
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
                    'negative_strength': news_result.get('negative_strength', 0.0)
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
                'sector_rotation': {
                    'score': sector_rotation_score,
                    'weight': self.config.get('sector_rotation_weight', 0.05),
                    'sector_name': sector_rotation_result.get('sector_name', 'unknown'),
                    'sector_type': sector_rotation_result.get('sector_type', 'unknown'),
                    'heat': sector_rotation_result.get('heat', 0.5),
                    'trend': sector_rotation_result.get('trend', 'neutral'),
                    'industry': sector_rotation_result.get('industry', ''),
                    'concepts': sector_rotation_result.get('concepts', [])
                },
                'market': {
                    'score': market_score,
                    'weight': self.config.get('market_weight', 0.17),
                    'trend': market_result['trend']
                },
                'history': {
                    'score': history_score,
                    'weight': self.config.get('history_weight', 0.08),
                    'pattern': history_result['pattern']
                },
                'us_sector': {
                    'score': us_sector_score,
                    'weight': self.config.get('us_sector_weight', 0.10),
                    'sector': us_sector_name,
                    'change_pct': us_sector_change,
                    'trend': us_sector_result.get('trend', 'neutral')
                },
                'valuation': {
                    'score': valuation_score,
                    'weight': self.config.get('valuation_weight', 0.05),
                    'pe_ratio': pe_ratio,
                    'pb_ratio': pb_ratio,
                    'valuation': valuation_result['valuation']
                }
            },
            'trading_suggestions': trading_suggestions,
            'timestamp': datetime.now(),
            'target_date': target_date,
            'date_desc': date_desc,
            'summary': summary_text,
            'market_overall': market_overall
        }
        
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

