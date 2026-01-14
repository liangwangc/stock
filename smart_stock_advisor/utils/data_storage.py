"""
数据存储模块
用于将各种指标数据保存到CSV文件或数据库，供后续学习和分析使用
支持数据库和CSV两种存储方式，根据配置自动选择
"""
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List, Any
from utils.logger import get_logger

# 尝试导入数据库配置
try:
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    from config_db import USE_DATABASE
    if USE_DATABASE:
        from utils.db_storage import DatabaseStorage
except ImportError:
    USE_DATABASE = False

logger = get_logger(__name__)

class DataStorage:
    """数据存储管理器（支持数据库和CSV两种方式）"""
    
    def __init__(self, base_dir: str = "data"):
        """
        初始化数据存储管理器
        
        Args:
            base_dir: 数据存储的基础目录（CSV模式使用）
        """
        self.base_dir = base_dir
        self.logger = logger
        self.use_database = USE_DATABASE
        
        # 如果使用数据库，初始化数据库存储
        if self.use_database:
            try:
                self.db_storage = DatabaseStorage()
                self.logger.info("数据存储模式：数据库")
            except Exception as e:
                self.logger.warning(f"数据库初始化失败，回退到CSV模式: {str(e)}")
                self.use_database = False
                self.db_storage = None
        else:
            self.db_storage = None
            self.logger.info("数据存储模式：CSV文件")
        
        # 确保基础目录存在（CSV模式）
        if not self.use_database:
            if not os.path.exists(self.base_dir):
                os.makedirs(self.base_dir)
                self.logger.info(f"创建数据存储目录: {self.base_dir}")
    
    def _get_file_path(self, data_type: str) -> str:
        """
        获取数据文件的路径
        
        Args:
            data_type: 数据类型（如 'north_bound', 'margin_trading' 等）
            
        Returns:
            文件路径
        """
        filename = f"{data_type}_data.csv"
        return os.path.join(self.base_dir, filename)
    
    def _ensure_file_exists(self, file_path: str, columns: List[str]):
        """
        确保CSV文件存在，如果不存在则创建
        
        Args:
            file_path: 文件路径
            columns: 列名列表
        """
        if not os.path.exists(file_path):
            df = pd.DataFrame(columns=columns)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.debug(f"创建数据文件: {file_path}")
    
    def save_north_bound_capital(self, data: Dict, timestamp: datetime = None):
        """
        保存北向资金数据
        
        Args:
            data: 北向资金数据字典
            timestamp: 时间戳，如果为None则使用当前时间
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                self.db_storage.save_north_bound_capital(data, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('north_bound_capital')
            columns = ['timestamp', 'date', 'today_net_inflow', 'avg_net_inflow_5d', 
                      'avg_net_inflow_10d', 'trend']
            
            self._ensure_file_exists(file_path, columns)
            
            new_record = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'today_net_inflow': data.get('today_net_inflow', 0.0),
                'avg_net_inflow_5d': data.get('avg_net_inflow_5d', 0.0),
                'avg_net_inflow_10d': data.get('avg_net_inflow_10d', 0.0),
                'trend': data.get('trend', 'neutral')
            }
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 检查是否已存在相同日期的记录
            existing = df[df['date'] == new_record['date']]
            if not existing.empty:
                # 更新现有记录
                df.loc[df['date'] == new_record['date'], new_record.keys()] = list(new_record.values())
                self.logger.debug(f"更新北向资金数据: {new_record['date']}")
            else:
                # 追加新记录
                new_df = pd.DataFrame([new_record])
                # 确保列顺序一致
                new_df = new_df.reindex(columns=df.columns, fill_value=None)
                df = pd.concat([df, new_df], ignore_index=True)
                self.logger.debug(f"保存北向资金数据: {new_record['date']}")
            
            # 保存到CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            self.logger.error(f"保存北向资金数据失败: {str(e)}")
    
    def save_margin_trading_data(self, symbol: str, data: Dict, timestamp: datetime = None):
        """
        保存融资融券数据
        
        Args:
            symbol: 股票代码
            data: 融资融券数据字典
            timestamp: 时间戳
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                self.db_storage.save_margin_trading_data(symbol, data, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('margin_trading')
            columns = ['timestamp', 'date', 'symbol', 'margin_balance', 'margin_change', 
                      'margin_change_pct', 'short_balance', 'trend']
            
            self._ensure_file_exists(file_path, columns)
            
            new_record = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'symbol': str(symbol).zfill(6),
                'margin_balance': data.get('margin_balance', 0.0),
                'margin_change': data.get('margin_change', 0.0),
                'margin_change_pct': data.get('margin_change_pct', 0.0),
                'short_balance': data.get('short_balance', 0.0),
                'trend': data.get('trend', 'stable')
            }
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 检查是否已存在相同日期和股票代码的记录
            existing = df[(df['date'] == new_record['date']) & (df['symbol'] == new_record['symbol'])]
            if not existing.empty:
                # 更新现有记录
                idx = existing.index[0]
                for key, value in new_record.items():
                    df.at[idx, key] = value
                self.logger.debug(f"更新融资融券数据: {symbol} - {new_record['date']}")
            else:
                # 追加新记录
                new_df = pd.DataFrame([new_record])
                # 确保列顺序一致
                new_df = new_df.reindex(columns=df.columns, fill_value=None)
                df = pd.concat([df, new_df], ignore_index=True)
                self.logger.debug(f"保存融资融券数据: {symbol} - {new_record['date']}")
            
            # 保存到CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            self.logger.error(f"保存融资融券数据失败: {str(e)}")
    
    def save_main_force_capital(self, symbol: str, data: Dict, timestamp: datetime = None):
        """
        保存主力资金数据
        
        Args:
            symbol: 股票代码
            data: 主力资金数据字典
            timestamp: 时间戳
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                self.db_storage.save_main_force_capital(symbol, data, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('main_force_capital')
            columns = ['timestamp', 'date', 'symbol', 'main_net_inflow', 
                      'main_net_inflow_pct', 'trend']
            
            self._ensure_file_exists(file_path, columns)
            
            new_record = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'symbol': str(symbol).zfill(6),
                'main_net_inflow': data.get('main_net_inflow', 0.0),
                'main_net_inflow_pct': data.get('main_net_inflow_pct', 0.0),
                'trend': data.get('trend', 'neutral')
            }
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 检查是否已存在相同日期和股票代码的记录
            existing = df[(df['date'] == new_record['date']) & (df['symbol'] == new_record['symbol'])]
            if not existing.empty:
                # 更新现有记录
                idx = existing.index[0]
                for key, value in new_record.items():
                    df.at[idx, key] = value
                self.logger.debug(f"更新主力资金数据: {symbol} - {new_record['date']}")
            else:
                # 追加新记录
                new_df = pd.DataFrame([new_record])
                # 确保列顺序一致
                new_df = new_df.reindex(columns=df.columns, fill_value=None)
                df = pd.concat([df, new_df], ignore_index=True)
                self.logger.debug(f"保存主力资金数据: {symbol} - {new_record['date']}")
            
            # 保存到CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            self.logger.error(f"保存主力资金数据失败: {str(e)}")
    
    def save_sector_rotation_data(self, data: Dict, timestamp: datetime = None):
        """
        保存板块轮动数据
        
        Args:
            data: 板块轮动数据字典
            timestamp: 时间戳
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                self.db_storage.save_sector_rotation_data(data, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('sector_rotation')
            columns = ['timestamp', 'date', 'sector_name', 'sector_type', 
                      'change_pct', 'capital_flow', 'heat', 'is_hot']
            
            self._ensure_file_exists(file_path, columns)
            
            date_str = timestamp.strftime('%Y-%m-%d')
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 删除当天的旧数据（如果有）
            df = df[df['date'] != date_str]
            
            # 处理行业板块数据
            industry_sectors = data.get('industry_sectors', {})
            concept_sectors = data.get('concept_sectors', {})
            hot_sectors = data.get('hot_sectors', [])
            
            new_records = []
            
            # 添加行业板块数据
            for sector_name, sector_info in industry_sectors.items():
                new_records.append({
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'date': date_str,
                    'sector_name': sector_name,
                    'sector_type': 'industry',
                    'change_pct': sector_info.get('change_pct', 0.0),
                    'capital_flow': sector_info.get('capital_flow', 0.0),
                    'heat': sector_info.get('heat', 0.5),
                    'is_hot': 1 if sector_name in hot_sectors else 0
                })
            
            # 添加概念板块数据
            for sector_name, sector_info in concept_sectors.items():
                new_records.append({
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'date': date_str,
                    'sector_name': sector_name,
                    'sector_type': 'concept',
                    'change_pct': sector_info.get('change_pct', 0.0),
                    'capital_flow': sector_info.get('capital_flow', 0.0),
                    'heat': sector_info.get('heat', 0.5),
                    'is_hot': 1 if sector_name in hot_sectors else 0
                })
            
            if new_records:
                # 追加新记录
                new_df = pd.DataFrame(new_records)
                df = pd.concat([df, new_df], ignore_index=True)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                self.logger.debug(f"保存板块轮动数据: {date_str} ({len(new_records)} 条记录)")
            
        except Exception as e:
            self.logger.error(f"保存板块轮动数据失败: {str(e)}")
    
    def save_cost_distribution(self, symbol: str, data: Dict, timestamp: datetime = None):
        """
        保存成本分布数据
        
        每个价位一行，方便后续做分布统计和学习分析。
        
        Args:
            symbol: 股票代码
            data: 成本分布数据字典，包含 levels 和可选 top_levels
            timestamp: 时间戳
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            levels = data.get('levels') or []
            if not levels:
                return
            
            file_path = self._get_file_path('cost_distribution')
            columns = ['timestamp', 'date', 'symbol', 'scope', 'price', 'volume', 'volume_pct', 'is_top_level']
            
            self._ensure_file_exists(file_path, columns)
            
            symbol_str = str(symbol).zfill(6)
            date_str = timestamp.strftime('%Y-%m-%d')
            
            # 顶部主要成本区，用于标记
            top_levels = data.get('top_levels') or []
            top_price_set = {float(lvl.get('price')) for lvl in top_levels if 'price' in lvl}
            scope = str(data.get('scope', 'history'))
            
            # 构造本次全部价位记录
            new_records = []
            for lvl in levels:
                price = float(lvl.get('price', 0.0))
                volume = float(lvl.get('volume', 0.0))
                volume_pct = float(lvl.get('volume_pct', 0.0))
                is_top = 1 if price in top_price_set else 0
                
                new_records.append({
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'date': date_str,
                    'symbol': symbol_str,
                    'scope': scope,
                    'price': price,
                    'volume': volume,
                    'volume_pct': volume_pct,
                    'is_top_level': is_top
                })
            
            if not new_records:
                return
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')

            # 兼容旧文件如果没有scope列，则补上默认值
            if 'scope' not in df.columns:
                df['scope'] = 'history'
            
            # 删除同一日期、同一股票、同一scope的旧记录，保留最新一版分布
            if not df.empty:
                mask = ~((df['date'] == date_str) & (df['symbol'] == symbol_str) & (df['scope'] == scope))
                df = df[mask]
            
            # 追加新记录
            new_df = pd.DataFrame(new_records)
            new_df = new_df.reindex(columns=df.columns if not df.empty else columns, fill_value=None)
            df = pd.concat([df, new_df], ignore_index=True)
            
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.debug(f"保存成本分布数据: {symbol_str} - {date_str} ({len(new_records)} 条价位记录)")
        
        except Exception as e:
            self.logger.error(f"保存成本分布数据失败: {str(e)}")
    
    def save_technical_indicators(self, symbol: str, data: Dict, timestamp: datetime = None):
        """
        保存技术指标数据
        
        Args:
            symbol: 股票代码
            data: 技术指标数据字典
            timestamp: 时间戳
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                self.db_storage.save_technical_indicators(symbol, data, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('technical_indicators')
            columns = ['timestamp', 'date', 'symbol', 'score', 'trend', 
                      'macd', 'rsi_14', 'rsi_6', 'rsi_12', 'kdj_k', 'kdj_d', 
                      'cci', 'ma_short', 'ma_long', 'ma60', 'turnover_rate']
            
            self._ensure_file_exists(file_path, columns)
            
            details = data.get('details', {})
            signals = data.get('signals', {})
            
            new_record = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'symbol': str(symbol).zfill(6),
                'score': data.get('score', 0.0),
                'trend': data.get('trend', 'neutral'),
                'macd': details.get('MACD', None),
                'rsi_14': details.get('RSI(14)', None),
                'rsi_6': details.get('RSI(6)', None),
                'rsi_12': details.get('RSI(12)', None),
                'kdj_k': details.get('KDJ_K', None),
                'kdj_d': details.get('KDJ_D', None),
                'cci': details.get('CCI', None),
                'ma_short': details.get('MA_short', None),
                'ma_long': details.get('MA_long', None),
                'ma60': details.get('MA60', None),
                'turnover_rate': signals.get('换手率', None)
            }
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 检查是否已存在相同日期和股票代码的记录
            existing = df[(df['date'] == new_record['date']) & (df['symbol'] == new_record['symbol'])]
            if not existing.empty:
                # 更新现有记录
                idx = existing.index[0]
                for key, value in new_record.items():
                    df.at[idx, key] = value
                self.logger.debug(f"更新技术指标数据: {symbol} - {new_record['date']}")
            else:
                # 追加新记录
                new_df = pd.DataFrame([new_record])
                # 确保列顺序一致
                new_df = new_df.reindex(columns=df.columns, fill_value=None)
                df = pd.concat([df, new_df], ignore_index=True)
                self.logger.debug(f"保存技术指标数据: {symbol} - {new_record['date']}")
            
            # 保存到CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            self.logger.error(f"保存技术指标数据失败: {str(e)}")
    
    def save_news_sentiment(self, symbol: str, data: Dict, timestamp: datetime = None):
        """
        保存新闻情感数据
        
        Args:
            symbol: 股票代码
            data: 新闻情感数据字典
            timestamp: 时间戳
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                self.db_storage.save_news_sentiment(symbol, data, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('news_sentiment')
            columns = ['timestamp', 'date', 'symbol', 'score', 'sentiment', 
                      'news_count', 'direct_news_count', 'industry_news_count', 
                      'policy_news_count', 'positive_count', 'negative_count', 
                      'positive_strength', 'negative_strength', 'weight_multiplier']
            
            self._ensure_file_exists(file_path, columns)
            
            new_record = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'symbol': str(symbol).zfill(6),
                'score': data.get('score', 0.0),
                'sentiment': data.get('sentiment', 'neutral'),
                'news_count': data.get('news_count', 0),
                'direct_news_count': data.get('direct_news_count', 0),
                'industry_news_count': data.get('industry_news_count', 0),
                'policy_news_count': data.get('policy_news_count', 0),
                'positive_count': data.get('positive_count', 0),
                'negative_count': data.get('negative_count', 0),
                'positive_strength': data.get('positive_strength', 0.0),
                'negative_strength': data.get('negative_strength', 0.0),
                'weight_multiplier': data.get('weight_multiplier', 1.0)
            }
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 检查是否已存在相同日期和股票代码的记录
            existing = df[(df['date'] == new_record['date']) & (df['symbol'] == new_record['symbol'])]
            if not existing.empty:
                # 更新现有记录
                idx = existing.index[0]
                for key, value in new_record.items():
                    df.at[idx, key] = value
                self.logger.debug(f"更新新闻情感数据: {symbol} - {new_record['date']}")
            else:
                # 追加新记录
                new_df = pd.DataFrame([new_record])
                # 确保列顺序一致
                new_df = new_df.reindex(columns=df.columns, fill_value=None)
                df = pd.concat([df, new_df], ignore_index=True)
                self.logger.debug(f"保存新闻情感数据: {symbol} - {new_record['date']}")
            
            # 保存到CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            self.logger.error(f"保存新闻情感数据失败: {str(e)}")
    
    def save_market_sentiment(self, data: Dict, timestamp: datetime = None):
        """
        保存市场情绪数据
        
        Args:
            data: 市场情绪数据字典
            timestamp: 时间戳
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                self.db_storage.save_market_sentiment(data, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('market_sentiment')
            columns = ['timestamp', 'date', 'score', 'trend', 'market_index_score', 
                      'stock_score', 'sector_score', 'up_days', 'down_days', 'avg_return']
            
            self._ensure_file_exists(file_path, columns)
            
            details = data.get('details', {})
            
            new_record = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'score': data.get('score', 0.0),
                'trend': data.get('trend', 'neutral'),
                'market_index_score': details.get('market_index_score', None),
                'stock_score': details.get('stock_score', None),
                'sector_score': details.get('sector_score', None),
                'up_days': details.get('up_days', None),
                'down_days': details.get('down_days', None),
                'avg_return': details.get('avg_return', None)
            }
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 检查是否已存在相同日期的记录
            existing = df[df['date'] == new_record['date']]
            if not existing.empty:
                # 更新现有记录
                idx = existing.index[0]
                for key, value in new_record.items():
                    df.at[idx, key] = value
                self.logger.debug(f"更新市场情绪数据: {new_record['date']}")
            else:
                # 追加新记录
                new_df = pd.DataFrame([new_record])
                # 确保列顺序一致
                new_df = new_df.reindex(columns=df.columns, fill_value=None)
                df = pd.concat([df, new_df], ignore_index=True)
                self.logger.debug(f"保存市场情绪数据: {new_record['date']}")
            
            # 保存到CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            self.logger.error(f"保存市场情绪数据失败: {str(e)}")
    
    def save_prediction_factors(self, symbol: str, factors: Dict, prediction_result: Dict = None, timestamp: datetime = None):
        """
        保存预测因子数据（所有因子的汇总）
        
        Args:
            symbol: 股票代码
            factors: 预测因子字典
            prediction_result: 预测结果字典（包含final_score等）
            timestamp: 时间戳
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                if prediction_result is None:
                    # 如果没有提供prediction_result，尝试从factors中获取
                    prediction_result = {
                        'final_score': factors.get('final_score', 0),
                        'up_probability': factors.get('up_probability', 0),
                        'down_probability': factors.get('down_probability', 0),
                        'confidence': factors.get('confidence', 0)
                    }
                self.db_storage.save_prediction_factors(symbol, factors, prediction_result, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('prediction_factors')
            columns = ['timestamp', 'date', 'symbol', 
                      'technical_score', 'technical_weight', 'technical_trend',
                      'news_score', 'news_weight', 'news_sentiment',
                      'capital_flow_score', 'capital_flow_weight', 'capital_flow_trend',
                      'market_score', 'market_weight', 'market_trend',
                      'sector_rotation_score', 'sector_rotation_weight', 'sector_rotation_trend',
                      'history_score', 'history_weight', 'history_pattern',
                      'valuation_score', 'valuation_weight', 'pe_ratio', 'pb_ratio',
                      'us_sector_score', 'us_sector_weight', 'us_sector_name',
                      'final_score', 'up_probability', 'down_probability', 'confidence']
            
            self._ensure_file_exists(file_path, columns)
            
            technical = factors.get('technical', {})
            news = factors.get('news', {})
            capital_flow = factors.get('capital_flow', {})
            market = factors.get('market', {})
            sector_rotation = factors.get('sector_rotation', {})
            history = factors.get('history', {})
            valuation = factors.get('valuation', {})
            us_sector = factors.get('us_sector', {})
            
            new_record = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'symbol': str(symbol).zfill(6),
                'technical_score': technical.get('score', 0.0),
                'technical_weight': technical.get('weight', 0.0),
                'technical_trend': technical.get('trend', 'neutral'),
                'news_score': news.get('score', 0.0),
                'news_weight': news.get('weight', 0.0),
                'news_sentiment': news.get('sentiment', 'neutral'),
                'capital_flow_score': capital_flow.get('score', 0.0),
                'capital_flow_weight': capital_flow.get('weight', 0.0),
                'capital_flow_trend': capital_flow.get('trend', 'neutral'),
                'market_score': market.get('score', 0.0),
                'market_weight': market.get('weight', 0.0),
                'market_trend': market.get('trend', 'neutral'),
                'sector_rotation_score': sector_rotation.get('score', 0.0),
                'sector_rotation_weight': sector_rotation.get('weight', 0.0),
                'sector_rotation_trend': sector_rotation.get('trend', 'neutral'),
                'history_score': history.get('score', 0.0),
                'history_weight': history.get('weight', 0.0),
                'history_pattern': history.get('pattern', ''),
                'valuation_score': valuation.get('score', 0.0),
                'valuation_weight': valuation.get('weight', 0.0),
                'pe_ratio': valuation.get('pe_ratio', None),
                'pb_ratio': valuation.get('pb_ratio', None),
                'us_sector_score': us_sector.get('score', 0.0),
                'us_sector_weight': us_sector.get('weight', 0.0),
                'us_sector_name': us_sector.get('sector', 'unknown'),
                'final_score': factors.get('final_score', 0.0),
                'up_probability': factors.get('up_probability', 0.0),
                'down_probability': factors.get('down_probability', 0.0),
                'confidence': factors.get('confidence', 0.0)
            }
            
            # 读取现有数据
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 检查是否已存在相同日期和股票代码的记录
            existing = df[(df['date'] == new_record['date']) & (df['symbol'] == new_record['symbol'])]
            if not existing.empty:
                # 更新现有记录
                idx = existing.index[0]
                for key, value in new_record.items():
                    df.at[idx, key] = value
                self.logger.debug(f"更新预测因子数据: {symbol} - {new_record['date']}")
            else:
                # 追加新记录
                new_df = pd.DataFrame([new_record])
                # 确保列顺序一致
                new_df = new_df.reindex(columns=df.columns, fill_value=None)
                df = pd.concat([df, new_df], ignore_index=True)
                self.logger.debug(f"保存预测因子数据: {symbol} - {new_record['date']}")
            
            # 保存到CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            self.logger.error(f"保存预测因子数据失败: {str(e)}")

    def save_realtime_trading_decision(self, data: Dict, timestamp: datetime = None):
        """
        保存实时交易决策数据（监控/实时模式下的每一次决策快照）
        
        Args:
            data: 实时决策完整结果字典（通常为 RealtimeTradingAdvisor.get_realtime_decision 的返回值）
            timestamp: 时间戳（可选，不传则使用当前时间）
        """
        # 优先使用数据库
        if self.use_database and self.db_storage:
            try:
                self.db_storage.save_realtime_trading_decision(data, timestamp)
                return
            except Exception as e:
                self.logger.warning(f"数据库保存失败，回退到CSV: {str(e)}")
        
        # CSV模式
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            file_path = self._get_file_path('realtime_trading_decisions')
            columns = [
                'timestamp', 'date', 'symbol', 'mode',
                'holding', 'cost_price',
                'current_price', 'change_pct',
                'up_probability', 'down_probability', 'confidence',
                'prediction_direction', 'target_date',
                'signal_strength',
                'action', 'action_cn', 'strength', 'strength_cn',
                'trading_session', 'trading_message',
                'main_net_inflow', 'total_net_inflow', 'flow_trend',
                'reasons', 'risk_warnings', 'position_advice'
            ]
            
            self._ensure_file_exists(file_path, columns)
            
            symbol = str(data.get('symbol', '')).zfill(6)
            mode = data.get('mode', 'single')
            quote = data.get('realtime_quote', {}) or {}
            prediction = data.get('prediction', {}) or {}
            decision = data.get('decision', {}) or {}
            trading_time = data.get('trading_time', {}) or {}
            capital_flow = data.get('capital_flow', {}) or {}
            
            reasons = decision.get('reasons', []) or []
            risk_warnings = decision.get('risk_warnings', []) or []
            
            new_record = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'symbol': symbol,
                'mode': mode,
                'holding': int(bool(decision.get('current_profit_pct') is not None)) if 'current_profit_pct' in decision else 0,
                'cost_price': data.get('cost_price', None),
                'current_price': quote.get('current_price', None),
                'change_pct': quote.get('change_pct', None),
                'up_probability': prediction.get('up_probability', None),
                'down_probability': prediction.get('down_probability', None),
                'confidence': prediction.get('confidence', None),
                'prediction_direction': prediction.get('direction', ''),
                'target_date': prediction.get('target_date', ''),
                'signal_strength': data.get('signal_strength', None),
                'action': decision.get('action', ''),
                'action_cn': decision.get('action_cn', ''),
                'strength': decision.get('strength', ''),
                'strength_cn': decision.get('strength_cn', ''),
                'trading_session': trading_time.get('session', ''),
                'trading_message': trading_time.get('message', ''),
                'main_net_inflow': capital_flow.get('main_net_inflow', None),
                'total_net_inflow': capital_flow.get('total_net_inflow', None),
                'flow_trend': capital_flow.get('flow_trend', ''),
                'reasons': ' | '.join(str(r) for r in reasons),
                'risk_warnings': ' | '.join(str(r) for r in risk_warnings),
                'position_advice': decision.get('position_advice', '')
            }
            
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            new_df = pd.DataFrame([new_record])
            # 确保列顺序一致
            new_df = new_df.reindex(columns=df.columns, fill_value=None)
            df = pd.concat([df, new_df], ignore_index=True)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.debug(f"保存实时交易决策数据: {symbol} - {new_record['timestamp']} ({mode})")
        
        except Exception as e:
            self.logger.error(f"保存实时交易决策数据失败: {str(e)}")

