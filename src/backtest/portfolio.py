"""
投资组合模块
管理持仓和资金
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import date

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    """持仓"""
    symbol: str
    volume: int = 0
    avg_cost: float = 0.0
    market_value: float = 0.0
    
    def update(self, volume_change: int, price: float, cost: float = 0):
        """更新持仓"""
        if volume_change > 0:
            # 买入
            total_cost = self.avg_cost * self.volume + price * volume_change + cost
            self.volume += volume_change
            self.avg_cost = total_cost / self.volume if self.volume > 0 else 0
        else:
            # 卖出
            self.volume += volume_change  # volume_change为负
            if self.volume == 0:
                self.avg_cost = 0
        
        self.market_value = self.volume * price
    
    def unrealized_pnl(self, current_price: float) -> float:
        """浮动盈亏"""
        return (current_price - self.avg_cost) * self.volume if self.volume > 0 else 0
    
    def realized_pnl(self, sell_price: float, volume: int) -> float:
        """实现盈亏"""
        return (sell_price - self.avg_cost) * volume


class Portfolio:
    """
    投资组合
    
    管理资金和持仓
    """
    
    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.total_commission = 0.0
        self.total_slippage = 0.0
    
    def update_position(
        self,
        symbol: str,
        volume: int,
        price: float,
        cost: float = 0
    ):
        """
        更新持仓
        
        Args:
            symbol: 股票代码
            volume: 数量 (正为买入，负为卖出)
            price: 价格
            cost: 交易成本
        """
        # 检查资金
        if volume > 0:  # 买入
            amount = price * volume + cost
            if amount > self.cash:
                logger.warning(f"资金不足: 需要{amount}, 可用{self.cash}")
                return
            self.cash -= amount
        else:  # 卖出
            if symbol not in self.positions or self.positions[symbol].volume < abs(volume):
                logger.warning(f"持仓不足: {symbol}")
                return
            amount = price * abs(volume) - cost
            self.cash += amount
        
        # 更新持仓
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        
        self.positions[symbol].update(volume, price, cost)
        
        # 清理空仓
        if self.positions[symbol].volume == 0:
            del self.positions[symbol]
        
        # 记录成本
        self.total_commission += cost
        
        logger.debug(f"更新持仓: {symbol}, 数量{volume}, 价格{price}, 成本{cost}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions
    
    def total_value(self, data: Dict, current_date: date) -> float:
        """
        计算总资产
        
        Args:
            data: 市场数据
            current_date: 当前日期
            
        Returns:
            float: 总资产
        """
        market_value = 0.0
        
        for symbol, position in self.positions.items():
            if symbol in data:
                # 获取最新价格
                day_data = data[symbol][data[symbol].index.date == current_date]
                if not day_data.empty:
                    latest_price = day_data['close'].iloc[-1]
                    market_value += position.volume * latest_price
        
        return self.cash + market_value
    
    def total_pnl(self, data: Dict, current_date: date) -> float:
        """计算总盈亏"""
        total_value = self.total_value(data, current_date)
        return total_value - self.initial_cash
    
    def total_return(self, data: Dict, current_date: date) -> float:
        """计算总收益率"""
        pnl = self.total_pnl(data, current_date)
        return pnl / self.initial_cash if self.initial_cash > 0 else 0
    
    def get_position_ratio(self, data: Dict, current_date: date) -> float:
        """计算仓位比例"""
        total_value = self.total_value(data, current_date)
        market_value = total_value - self.cash
        return market_value / total_value if total_value > 0 else 0
