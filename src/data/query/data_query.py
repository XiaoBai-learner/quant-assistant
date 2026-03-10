"""
数据查询接口 - 提供统一的数据访问
"""
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union

from src.storage.mysql_storage import MySQLStorage
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataQueryEngine:
    """数据查询引擎"""
    
    def __init__(self):
        self.storage = MySQLStorage()
        self._cache = {}
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息"""
        df = self.storage.get_stock_list()
        stock = df[df['symbol'] == symbol]
        
        if stock.empty:
            return None
        
        return stock.iloc[0].to_dict()
    
    def get_price_data(
        self,
        symbol: str,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        fields: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """获取价格数据"""
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        df = self.storage.get_daily_quotes(symbol, start_date, end_date)
        
        if df.empty:
            logger.warning(f"未找到 {symbol} 的价格数据")
            return pd.DataFrame()
        
        if fields:
            available_fields = ['symbol', 'trade_date'] + fields
            df = df[[col for col in available_fields if col in df.columns]]
        
        return df
    
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取最新价格"""
        df = self.get_price_data(symbol)
        
        if df.empty:
            return None
        
        latest = df.iloc[-1]
        return {
            'symbol': symbol,
            'date': latest['trade_date'],
            'close': latest['close'],
            'change_pct': latest['pct_change'],
            'volume': latest['volume'],
            'turnover': latest['turnover']
        }
    
    def get_multiple_stocks(
        self,
        symbols: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, pd.DataFrame]:
        """批量获取多只股票数据"""
        result = {}
        for symbol in symbols:
            df = self.get_price_data(symbol, start_date, end_date)
            if not df.empty:
                result[symbol] = df
        return result
    
    def calculate_returns(
        self,
        symbol: str,
        periods: List[int] = [1, 5, 20, 60]
    ) -> pd.DataFrame:
        """计算收益率"""
        df = self.get_price_data(symbol)
        
        if df.empty:
            return pd.DataFrame()
        
        df = df.sort_values('trade_date')
        
        for period in periods:
            df[f'return_{period}d'] = df['close'].pct_change(period) * 100
        
        return df
    
    def get_trading_days(
        self,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """获取交易日列表"""
        days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                days.append(current)
            current += timedelta(days=1)
        return days
    
    def resample_data(
        self,
        df: pd.DataFrame,
        rule: str = 'W',
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """重采样数据"""
        if df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        })
        
        resampled.reset_index(inplace=True)
        return resampled
