"""
美股数据存储模块
用于存储美股历史数据到数据库
"""
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


class USStockStorage:
    """美股数据存储管理器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
    
    def save_stock_info(self, stock_info: Dict) -> bool:
        """
        保存股票基本信息
        
        Args:
            stock_info: 股票信息字典
        
        Returns:
            是否成功
        """
        try:
            sql = """
                INSERT INTO us_stock_info
                (symbol, name_en, name_cn, exchange, market_cap, sector_code, industry_code,
                 sub_industry_code, country, currency, ipo_date, description, website,
                 is_active, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name_en = VALUES(name_en),
                    name_cn = VALUES(name_cn),
                    exchange = VALUES(exchange),
                    market_cap = VALUES(market_cap),
                    sector_code = VALUES(sector_code),
                    industry_code = VALUES(industry_code),
                    sub_industry_code = VALUES(sub_industry_code),
                    description = VALUES(description),
                    website = VALUES(website),
                    updated_at = CURRENT_TIMESTAMP
            """
            
            params = (
                stock_info.get('symbol'),
                stock_info.get('name_en'),
                stock_info.get('name_cn'),
                stock_info.get('exchange'),
                stock_info.get('market_cap'),
                stock_info.get('sector_code'),
                stock_info.get('industry_code'),
                stock_info.get('sub_industry_code'),
                stock_info.get('country', 'US'),
                stock_info.get('currency', 'USD'),
                stock_info.get('ipo_date'),
                stock_info.get('description'),
                stock_info.get('website'),
                stock_info.get('is_active', 1),
                stock_info.get('data_source', 'yfinance')
            )
            
            self.db.execute_update(sql, params)
            self.logger.debug(f"保存股票信息成功: {stock_info.get('symbol')}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存股票信息失败 {stock_info.get('symbol')}: {str(e)}")
            return False
    
    def save_stock_history(self, symbol: str, trade_date: str, data: Dict) -> bool:
        """
        保存股票历史数据
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期（YYYY-MM-DD）
            data: 历史数据字典
        
        Returns:
            是否成功
        """
        try:
            sql = """
                INSERT INTO us_stock_history_data
                (symbol, name, trade_date, period_type, exchange,
                 open_price, close_price, high_price, low_price, adj_close_price,
                 pre_close, change_amount, change_pct,
                 volume, amount, turnover_rate, volume_ratio,
                 bid_price, ask_price, bid_volume, ask_volume,
                 bid_levels, ask_levels,
                 market_cap, enterprise_value, pe_ratio, forward_pe, pb_ratio, ps_ratio,
                 ev_ebitda, dividend_yield,
                 amplitude, price_range, volatility,
                 ma5, ma10, ma20, ma50, ma200,
                 rsi, macd, macd_signal, macd_hist, x2,
                 net_inflow, institutional_flow, retail_flow,
                 put_call_ratio, implied_volatility,
                 extra_data, data_source, data_quality_score, is_valid)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    period_type = VALUES(period_type),
                    exchange = VALUES(exchange),
                    open_price = VALUES(open_price),
                    close_price = VALUES(close_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    adj_close_price = VALUES(adj_close_price),
                    pre_close = VALUES(pre_close),
                    change_amount = VALUES(change_amount),
                    change_pct = VALUES(change_pct),
                    volume = VALUES(volume),
                    amount = VALUES(amount),
                    turnover_rate = VALUES(turnover_rate),
                    volume_ratio = VALUES(volume_ratio),
                    market_cap = VALUES(market_cap),
                    pe_ratio = VALUES(pe_ratio),
                    forward_pe = VALUES(forward_pe),
                    pb_ratio = VALUES(pb_ratio),
                    ps_ratio = VALUES(ps_ratio),
                    dividend_yield = VALUES(dividend_yield),
                    amplitude = VALUES(amplitude),
                    price_range = VALUES(price_range),
                    volatility = VALUES(volatility),
                    ma5 = VALUES(ma5),
                    ma10 = VALUES(ma10),
                    ma20 = VALUES(ma20),
                    ma50 = VALUES(ma50),
                    ma200 = VALUES(ma200),
                    rsi = VALUES(rsi),
                    x2 = VALUES(x2),
                    macd = VALUES(macd),
                    macd_signal = VALUES(macd_signal),
                    macd_hist = VALUES(macd_hist),
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 处理JSON字段
            bid_levels = json.dumps(data.get('bid_levels')) if data.get('bid_levels') else None
            ask_levels = json.dumps(data.get('ask_levels')) if data.get('ask_levels') else None
            extra_data = json.dumps(data.get('extra_data')) if data.get('extra_data') else None
            
            # 获取period_type，默认为'daily'
            period_type = data.get('period_type', 'daily')
            
            params = (
                symbol,
                data.get('name'),
                trade_date,
                period_type,
                data.get('exchange'),
                data.get('open_price'),
                data.get('close_price'),
                data.get('high_price'),
                data.get('low_price'),
                data.get('adj_close_price'),
                data.get('pre_close'),
                data.get('change_amount'),
                data.get('change_pct'),
                data.get('volume'),
                data.get('amount'),
                data.get('turnover_rate'),
                data.get('volume_ratio'),
                data.get('bid_price'),
                data.get('ask_price'),
                data.get('bid_volume'),
                data.get('ask_volume'),
                bid_levels,
                ask_levels,
                data.get('market_cap'),
                data.get('enterprise_value'),
                data.get('pe_ratio'),
                data.get('forward_pe'),
                data.get('pb_ratio'),
                data.get('ps_ratio'),
                data.get('ev_ebitda'),
                data.get('dividend_yield'),
                data.get('amplitude'),
                data.get('price_range'),
                data.get('volatility'),
                data.get('ma5'),
                data.get('ma10'),
                data.get('ma20'),
                data.get('ma50'),
                data.get('ma200'),
                data.get('rsi'),
                data.get('x2'),
                data.get('macd'),
                data.get('macd_signal'),
                data.get('macd_hist'),
                data.get('net_inflow'),
                data.get('institutional_flow'),
                data.get('retail_flow'),
                data.get('put_call_ratio'),
                data.get('implied_volatility'),
                extra_data,
                data.get('data_source', 'yfinance'),
                data.get('data_quality_score', 1.0),
                data.get('is_valid', 1)
            )
            
            self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            self.logger.error(f"保存股票历史数据失败 {symbol} {trade_date}: {str(e)}")
            return False
    
    def save_sector_info(self, sector_code: str, sector_name_en: str, 
                        sector_name_cn: str = None, description: str = None) -> bool:
        """保存板块信息"""
        try:
            sql = """
                INSERT INTO us_sectors
                (sector_code, sector_name_en, sector_name_cn, sector_description, gics_level)
                VALUES (%s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    sector_name_en = VALUES(sector_name_en),
                    sector_name_cn = VALUES(sector_name_cn),
                    sector_description = VALUES(sector_description),
                    updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute_update(sql, (sector_code, sector_name_en, sector_name_cn, description))
            return True
        except Exception as e:
            self.logger.error(f"保存板块信息失败 {sector_code}: {str(e)}")
            return False
    
    def save_industry_info(self, industry_code: str, industry_name_en: str,
                          sector_code: str = None, industry_name_cn: str = None,
                          description: str = None) -> bool:
        """保存行业信息"""
        try:
            sql = """
                INSERT INTO us_industries
                (industry_code, industry_name_en, industry_name_cn, sector_code, industry_description, gics_level)
                VALUES (%s, %s, %s, %s, %s, 3)
                ON DUPLICATE KEY UPDATE
                    industry_name_en = VALUES(industry_name_en),
                    industry_name_cn = VALUES(industry_name_cn),
                    sector_code = VALUES(sector_code),
                    industry_description = VALUES(industry_description),
                    updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute_update(sql, (industry_code, industry_name_en, industry_name_cn, sector_code, description))
            return True
        except Exception as e:
            self.logger.error(f"保存行业信息失败 {industry_code}: {str(e)}")
            return False
    
    def create_or_get_industry(self, industry_name: str, sector_code: str = None) -> Optional[str]:
        """
        创建或获取行业代码（基于行业名称）
        
        Args:
            industry_name: 行业名称
            sector_code: 所属板块代码
        
        Returns:
            行业代码，如果创建失败返回None
        """
        try:
            # 先查询是否已存在相同名称的行业
            sql = "SELECT industry_code FROM us_industries WHERE industry_name_en = %s LIMIT 1"
            results = self.db.execute_query(sql, (industry_name,))
            
            if results:
                return results[0]['industry_code']
            
            # 如果不存在，创建一个新的行业代码
            # 使用sector_code + 序号的方式生成临时代码
            if sector_code:
                # 查找该板块下已有的行业数量
                count_sql = "SELECT COUNT(*) as cnt FROM us_industries WHERE sector_code = %s"
                count_results = self.db.execute_query(count_sql, (sector_code,))
                count = count_results[0]['cnt'] if count_results else 0
                
                # 生成临时代码：sector_code + 3位序号（如：45001表示Technology板块下的第1个行业）
                industry_code = f"{sector_code}{str(count + 1).zfill(3)}"
            else:
                # 如果没有sector_code，使用999开头作为临时代码
                industry_code = f"999{hash(industry_name) % 10000:04d}"
            
            # 保存新行业
            if self.save_industry_info(
                industry_code=industry_code,
                industry_name_en=industry_name,
                sector_code=sector_code
            ):
                return industry_code
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"创建或获取行业失败 {industry_name}: {str(e)}")
            return None
    
    def save_sector_stock_map(self, symbol: str, sector_code: str, sector_name: str = None) -> bool:
        """
        保存板块股票映射关系
        
        Args:
            symbol: 股票代码
            sector_code: 板块代码
            sector_name: 板块名称（可选，用于记录）
        
        Returns:
            是否成功
        """
        try:
            sql = """
                INSERT INTO us_sector_stock_map
                (symbol, sector_code, is_primary)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    is_primary = VALUES(is_primary),
                    updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute_update(sql, (symbol, sector_code))
            
            # 如果板块不存在，先创建板块
            if sector_name:
                self.save_sector_info(
                    sector_code=sector_code,
                    sector_name_en=sector_name
                )
            
            return True
        except Exception as e:
            self.logger.error(f"保存板块股票映射失败 {symbol} -> {sector_code}: {str(e)}")
            return False
    
    def save_industry_stock_map(self, symbol: str, industry_code: str, industry_name: str = None) -> bool:
        """
        保存行业股票映射关系
        
        Args:
            symbol: 股票代码
            industry_code: 行业代码
            industry_name: 行业名称（可选，用于记录）
        
        Returns:
            是否成功
        """
        try:
            sql = """
                INSERT INTO us_industry_stock_map
                (symbol, industry_code, is_primary)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    is_primary = VALUES(is_primary),
                    updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute_update(sql, (symbol, industry_code))
            
            # 如果行业不存在，先创建行业
            if industry_name:
                # 需要获取sector_code
                sector_code_sql = "SELECT sector_code FROM us_industries WHERE industry_code = %s LIMIT 1"
                sector_results = self.db.execute_query(sector_code_sql, (industry_code,))
                sector_code = sector_results[0]['sector_code'] if sector_results else None
                
                if not sector_results:
                    # 行业不存在，需要创建（但这里缺少sector_code，所以先不创建）
                    self.logger.debug(f"行业 {industry_code} 不存在，但缺少sector_code信息，跳过创建")
            
            return True
        except Exception as e:
            self.logger.error(f"保存行业股票映射失败 {symbol} -> {industry_code}: {str(e)}")
            return False
    
    def update_stock_industry_code(self, symbol: str, industry_code: str) -> bool:
        """更新股票信息表中的industry_code"""
        try:
            sql = "UPDATE us_stock_info SET industry_code = %s WHERE symbol = %s"
            self.db.execute_update(sql, (industry_code, symbol))
            return True
        except Exception as e:
            self.logger.error(f"更新股票industry_code失败 {symbol}: {str(e)}")
            return False
    
    def get_existing_dates(self, symbol: str, start_date: str, end_date: str) -> List[str]:
        """
        获取已存在的日期列表（用于增量更新）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            已存在的日期列表
        """
        try:
            sql = """
                SELECT trade_date FROM us_stock_history_data
                WHERE symbol = %s AND trade_date >= %s AND trade_date <= %s
                ORDER BY trade_date
            """
            results = self.db.execute_query(sql, (symbol, start_date, end_date))
            return [str(r['trade_date']) for r in results]
        except Exception as e:
            self.logger.error(f"获取已存在日期失败 {symbol}: {str(e)}")
            return []
    
    def get_stock_sectors(self, symbol: str) -> List[Dict]:
        """
        获取股票所属的板块列表
        
        Args:
            symbol: 股票代码
        
        Returns:
            板块列表
        """
        try:
            sql = """
                SELECT s.sector_code, s.sector_name_en, s.sector_name_cn, m.is_primary
                FROM us_sector_stock_map m
                JOIN us_sectors s ON m.sector_code = s.sector_code
                WHERE m.symbol = %s
            """
            results = self.db.execute_query(sql, (symbol,))
            return results
        except Exception as e:
            self.logger.error(f"获取股票板块失败 {symbol}: {str(e)}")
            return []
    
    def get_stock_industries(self, symbol: str) -> List[Dict]:
        """
        获取股票所属的行业列表
        
        Args:
            symbol: 股票代码
        
        Returns:
            行业列表
        """
        try:
            sql = """
                SELECT i.industry_code, i.industry_name_en, i.industry_name_cn, m.is_primary
                FROM us_industry_stock_map m
                JOIN us_industries i ON m.industry_code = i.industry_code
                WHERE m.symbol = %s
            """
            results = self.db.execute_query(sql, (symbol,))
            return results
        except Exception as e:
            self.logger.error(f"获取股票行业失败 {symbol}: {str(e)}")
            return []
