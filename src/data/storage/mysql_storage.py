"""
MySQL 数据存储实现
"""
import pandas as pd
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from sqlalchemy import insert, update, delete
from sqlalchemy.dialects.mysql import insert as mysql_insert

from src.storage.base_storage import BaseStorage
from src.database.connection import db_manager
from src.database.models import (
    Stock, DailyQuote, FinancialIndicator, UpdateLog, Base
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MySQLStorage(BaseStorage):
    """MySQL 数据存储实现"""
    
    def __init__(self):
        self.db = db_manager
        self._ensure_tables()
    
    def _ensure_tables(self):
        """确保数据库表已创建"""
        Base.metadata.create_all(self.db.engine)
        logger.info("数据库表结构已确认")
    
    def save_stocks(self, df: pd.DataFrame) -> int:
        """保存股票列表"""
        if df.empty:
            return 0
        
        records = df.to_dict('records')
        count = 0
        
        with self.db.session() as session:
            for record in records:
                stmt = mysql_insert(Stock).values(**record)
                stmt = stmt.on_duplicate_key_update(
                    name=stmt.inserted.name,
                    exchange=stmt.inserted.exchange,
                    updated_at=datetime.now()
                )
                session.execute(stmt)
                count += 1
        
        logger.info(f"保存/更新 {count} 只股票信息")
        self._log_update('stocks', None, None, None, count, 'success')
        return count
    
    def save_daily_quotes(self, df: pd.DataFrame) -> int:
        """保存日线行情数据"""
        if df.empty:
            return 0
        
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
        records = df.to_dict('records')
        count = 0
        symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else None
        
        with self.db.session() as session:
            for record in records:
                stmt = mysql_insert(DailyQuote).values(**record)
                stmt = stmt.on_duplicate_key_update(
                    open=stmt.inserted.open,
                    high=stmt.inserted.high,
                    low=stmt.inserted.low,
                    close=stmt.inserted.close,
                    volume=stmt.inserted.volume,
                    amount=stmt.inserted.amount,
                    amplitude=stmt.inserted.amplitude,
                    pct_change=stmt.inserted.pct_change,
                    change_amount=stmt.inserted.change_amount,
                    turnover=stmt.inserted.turnover,
                )
                session.execute(stmt)
                count += 1
        
        start_date = df['trade_date'].min()
        end_date = df['trade_date'].max()
        
        logger.info(f"保存 {count} 条日线数据 [{symbol}: {start_date} ~ {end_date}]")
        self._log_update('daily_quotes', symbol, start_date, end_date, count, 'success')
        return count
    
    def save_financial_indicators(self, df: pd.DataFrame) -> int:
        """保存财务指标"""
        if df.empty:
            return 0
        
        records = df.to_dict('records')
        count = 0
        
        with self.db.session() as session:
            for record in records:
                stmt = mysql_insert(FinancialIndicator).values(**record)
                stmt = stmt.on_duplicate_key_update(**record)
                session.execute(stmt)
                count += 1
        
        logger.info(f"保存 {count} 条财务指标")
        self._log_update('financial_indicators', None, None, None, count, 'success')
        return count
    
    def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """查询日线数据"""
        from sqlalchemy import select, and_
        
        stmt = select(DailyQuote).where(DailyQuote.symbol == symbol)
        
        if start_date:
            stmt = stmt.where(DailyQuote.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(DailyQuote.trade_date <= end_date)
        
        stmt = stmt.order_by(DailyQuote.trade_date)
        
        with self.db.session() as session:
            result = session.execute(stmt)
            rows = result.scalars().all()
            
            if not rows:
                return pd.DataFrame()
            
            data = [{
                'symbol': r.symbol,
                'trade_date': r.trade_date,
                'open': float(r.open) if r.open else None,
                'high': float(r.high) if r.high else None,
                'low': float(r.low) if r.low else None,
                'close': float(r.close) if r.close else None,
                'volume': r.volume,
                'amount': float(r.amount) if r.amount else None,
                'amplitude': float(r.amplitude) if r.amplitude else None,
                'pct_change': float(r.pct_change) if r.pct_change else None,
                'change_amount': float(r.change_amount) if r.change_amount else None,
                'turnover': float(r.turnover) if r.turnover else None,
            } for r in rows]
            
            return pd.DataFrame(data)
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        from sqlalchemy import select
        
        stmt = select(Stock).where(Stock.status == 1)
        
        with self.db.session() as session:
            result = session.execute(stmt)
            rows = result.scalars().all()
            
            data = [{
                'symbol': r.symbol,
                'name': r.name,
                'exchange': r.exchange,
                'industry': r.industry,
            } for r in rows]
            
            return pd.DataFrame(data)
    
    def get_last_update_date(self, symbol: str, table: str = 'daily_quotes') -> Optional[date]:
        """获取某只股票的最后更新日期"""
        from sqlalchemy import select, func
        
        if table == 'daily_quotes':
            stmt = select(func.max(DailyQuote.trade_date)).where(
                DailyQuote.symbol == symbol
            )
        else:
            return None
        
        with self.db.session() as session:
            result = session.execute(stmt)
            last_date = result.scalar()
            return last_date
    
    def _log_update(
        self,
        table_name: str,
        symbol: Optional[str],
        start_date: Optional[date],
        end_date: Optional[date],
        record_count: int,
        status: str,
        message: str = ''
    ):
        """记录更新日志"""
        log = UpdateLog(
            table_name=table_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            record_count=record_count,
            status=status,
            message=message
        )
        
        with self.db.session() as session:
            session.add(log)
