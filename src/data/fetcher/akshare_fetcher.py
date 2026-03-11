"""
AKShare 数据获取实现
"""
import akshare as ak
import pandas as pd
from datetime import datetime, date, timedelta
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
    
    def get_daily_quotes_incremental(
        self,
        symbol: str,
        last_date: Optional[date] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        增量获取日线数据
        
        Args:
            symbol: 股票代码
            last_date: 数据库中最新日期，None表示获取全部历史
            end_date: 结束日期，默认昨天
            
        Returns:
            DataFrame: 新增的数据
        """
        # 确定起始日期
        if last_date is None:
            # 获取全部历史
            start_date = '20200101'
        else:
            # 从最新日期的下一天开始
            next_date = last_date + timedelta(days=1)
            start_date = next_date.strftime('%Y-%m-%d')
        
        # 确定结束日期
        if end_date is None:
            yesterday = date.today() - timedelta(days=1)
            end_date = yesterday.strftime('%Y-%m-%d')
        
        # 检查是否需要更新
        if last_date and last_date >= date.today() - timedelta(days=1):
            logger.info(f"[{symbol}] 数据已是最新，无需更新")
            return pd.DataFrame()
        
        logger.info(f"[{symbol}] 增量更新: {start_date} ~ {end_date}")
        return self.get_daily_quotes(symbol, start_date, end_date)
    
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
