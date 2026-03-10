"""
AKShare 数据获取实现
"""
import akshare as ak
import pandas as pd
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import time

from src.fetcher.base_fetcher import BaseDataFetcher
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AKShareFetcher(BaseDataFetcher):
    """AKShare 数据获取器"""
    
    def __init__(self):
        self.name = "AKShare"
        self.rate_limit_delay = 0.5
    
    def _rate_limit(self):
        """速率限制"""
        time.sleep(self.rate_limit_delay)
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取A股股票列表"""
        try:
            logger.info("获取A股股票列表...")
            df = ak.stock_zh_a_spot_em()
            
            df = df.rename(columns={
                '代码': 'symbol',
                '名称': 'name',
            })
            
            df['exchange'] = df['symbol'].apply(self._get_exchange)
            result = df[['symbol', 'name', 'exchange']].copy()
            
            logger.info(f"获取到 {len(result)} 只股票")
            return result
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """获取日线行情数据"""
        try:
            self._rate_limit()
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = '20200101'
            
            start = start_date.replace('-', '')
            end = end_date.replace('-', '')
            
            logger.info(f"获取 {symbol} 日线数据: {start_date} ~ {end_date}")
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="qfq"
            )
            
            if df.empty:
                logger.warning(f"{symbol} 在指定日期范围内无数据")
                return pd.DataFrame()
            
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change_amount',
                '换手率': 'turnover',
            })
            
            df['symbol'] = symbol
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            
            logger.info(f"获取到 {len(df)} 条日线数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 日线数据失败: {e}")
            raise
    
    def get_financial_indicators(self, symbol: str) -> pd.DataFrame:
        """获取财务指标数据"""
        try:
            self._rate_limit()
            logger.info(f"获取 {symbol} 财务指标...")
            
            df = ak.stock_financial_report_sina(
                stock=symbol,
                symbol="主要财务指标"
            )
            
            if df.empty:
                return pd.DataFrame()
            
            df['symbol'] = symbol
            logger.info(f"获取到 {len(df)} 条财务指标")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 财务指标失败: {e}")
            return pd.DataFrame()
    
    def _get_exchange(self, symbol: str) -> str:
        """根据股票代码判断交易所"""
        if symbol.startswith(('600', '601', '603', '605', '688')):
            return 'SH'
        elif symbol.startswith(('000', '001', '002', '003', '300')):
            return 'SZ'
        elif symbol.startswith(('8', '4')):
            return 'BJ'
        else:
            return 'UNKNOWN'
