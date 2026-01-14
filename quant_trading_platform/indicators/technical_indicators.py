"""
技术指标计算
"""
import pandas as pd
import numpy as np

def SMA(data: pd.Series, period: int) -> pd.Series:
    """简单移动平均线"""
    return data.rolling(window=period).mean()

def EMA(data: pd.Series, period: int) -> pd.Series:
    """指数移动平均线"""
    return data.ewm(span=period, adjust=False).mean()

def MACD(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    MACD指标
    
    Returns:
        DataFrame with columns: macd, signal, histogram
    """
    ema_fast = EMA(data, fast)
    ema_slow = EMA(data, slow)
    macd = ema_fast - ema_slow
    signal_line = EMA(macd, signal)
    histogram = macd - signal_line
    
    result = pd.DataFrame({
        'macd': macd,
        'signal': signal_line,
        'histogram': histogram
    })
    return result

def RSI(data: pd.Series, period: int = 14) -> pd.Series:
    """相对强弱指标"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def BollingerBands(data: pd.Series, period: int = 20, num_std: float = 2) -> pd.DataFrame:
    """
    布林带指标
    
    Returns:
        DataFrame with columns: upper, middle, lower
    """
    middle = SMA(data, period)
    std = data.rolling(window=period).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    result = pd.DataFrame({
        'upper': upper,
        'middle': middle,
        'lower': lower
    })
    return result

