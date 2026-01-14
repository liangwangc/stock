"""
获取美股股票列表脚本
从S&P 500、NASDAQ 100等指数获取股票列表
"""
import os
import sys
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance未安装")


def get_sp500_stocks_from_wikipedia():
    """从Wikipedia获取S&P 500成分股列表"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # 方法1: 尝试使用pandas直接读取HTML表格
            try:
                dfs = pd.read_html(url)
                if dfs:
                    df = dfs[0]
                    if 'Symbol' in df.columns:
                        symbols = df['Symbol'].tolist()
                        # 清理符号（移除可能的后缀，如.BR）
                        symbols = [s.split('.')[0].split()[0] for s in symbols if pd.notna(s)]
                        logger.info(f"从Wikipedia获取S&P 500成分股，共 {len(symbols)} 只")
                        return symbols
            except Exception as e1:
                logger.debug(f"pandas读取HTML失败: {str(e1)}")
            
            # 方法2: 使用BeautifulSoup解析
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'id': 'constituents'})
            
            if table:
                df = pd.read_html(str(table))[0]
                if 'Symbol' in df.columns:
                    symbols = df['Symbol'].tolist()
                    symbols = [s.split('.')[0].split()[0] for s in symbols if pd.notna(s)]
                    logger.info(f"从Wikipedia获取S&P 500成分股，共 {len(symbols)} 只")
                    return symbols
        
        return []
    except Exception as e:
        logger.warning(f"从Wikipedia获取S&P 500列表失败: {str(e)}")
        return []


def get_nasdaq100_stocks_from_wikipedia():
    """从Wikipedia获取NASDAQ 100成分股列表"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://en.wikipedia.org/wiki/NASDAQ-100"
        response = requests.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table', {'class': 'wikitable'})
            
            for table in tables:
                try:
                    df = pd.read_html(str(table))[0]
                    if 'Ticker' in df.columns:
                        symbols = df['Ticker'].tolist()
                        logger.info(f"从Wikipedia获取NASDAQ 100成分股，共 {len(symbols)} 只")
                        return symbols
                except:
                    continue
        
        return []
    except Exception as e:
        logger.warning(f"从Wikipedia获取NASDAQ 100列表失败: {str(e)}")
        return []


def get_sp500_stocks_from_yfinance():
    """使用yfinance尝试获取S&P 500成分股"""
    if not YFINANCE_AVAILABLE:
        return []
    
    try:
        # 尝试从SPY ETF获取持仓
        spy = yf.Ticker("SPY")
        holdings = spy.get_holdings()
        
        if holdings is not None and not holdings.empty:
            symbols = holdings.index.tolist()
            logger.info(f"从SPY ETF获取成分股，共 {len(symbols)} 只")
            return symbols
    except:
        pass
    
    return []


def get_stock_list_by_index(index_name: str = 'sp500') -> list:
    """
    根据指数名称获取股票列表
    
    Args:
        index_name: 指数名称（'sp500'/'nasdaq100'/'dow'）
    
    Returns:
        股票代码列表
    """
    if index_name.lower() == 'sp500':
        # 优先从Wikipedia获取
        symbols = get_sp500_stocks_from_wikipedia()
        if not symbols:
            symbols = get_sp500_stocks_from_yfinance()
        return symbols
    elif index_name.lower() == 'nasdaq100':
        return get_nasdaq100_stocks_from_wikipedia()
    else:
        logger.warning(f"不支持的指数: {index_name}")
        return []


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='获取美股股票列表')
    parser.add_argument('--index', choices=['sp500', 'nasdaq100'], default='sp500',
                       help='指数名称')
    parser.add_argument('--output', help='输出文件路径（CSV格式）')
    
    args = parser.parse_args()
    
    logger.info(f"正在获取 {args.index.upper()} 成分股列表...")
    symbols = get_stock_list_by_index(args.index)
    
    if symbols:
        logger.info(f"成功获取 {len(symbols)} 只股票")
        
        if args.output:
            df = pd.DataFrame({'symbol': symbols})
            df.to_csv(args.output, index=False, encoding='utf-8-sig')
            logger.info(f"已保存到 {args.output}")
        else:
            print(f"\n{args.index.upper()} 成分股列表（共 {len(symbols)} 只）：")
            print("=" * 60)
            for i, symbol in enumerate(symbols, 1):
                print(f"{i:4d}. {symbol}")
                if i % 20 == 0:
                    print()  # 每20只换行
    else:
        logger.error("未能获取股票列表，可能是网络问题或依赖未安装")
        logger.info("提示：请确保已安装 requests, beautifulsoup4, lxml")
        logger.info("安装命令：pip install requests beautifulsoup4 lxml")
