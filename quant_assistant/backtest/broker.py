"""
券商模拟模块
处理订单和撮合
"""
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.utils.logger import get_logger

logger = get_logger(__name__)


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"       # 市价单
    LIMIT = "limit"         # 限价单
    STOP = "stop"           # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"         # 待提交
    SUBMITTED = "submitted"     # 已提交
    PARTIAL_FILLED = "partial_filled"  # 部分成交
    FILLED = "filled"           # 全部成交
    CANCELLED = "cancelled"     # 已撤销
    REJECTED = "rejected"       # 已拒绝


@dataclass
class Order:
    """订单"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    volume: int
    price: float = 0.0
    
    # 可选参数
    stop_price: float = None      # 止损价
    limit_price: float = None     # 限价
    
    # 状态
    order_id: str = field(default_factory=lambda: str(id(datetime.now())))
    status: OrderStatus = OrderStatus.PENDING
    filled_volume: int = 0
    filled_amount: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def remaining_volume(self) -> int:
        """剩余未成交数量"""
        return self.volume - self.filled_volume
    
    def is_filled(self) -> bool:
        """是否全部成交"""
        return self.filled_volume >= self.volume


@dataclass
class Trade:
    """成交记录"""
    symbol: str
    side: OrderSide
    volume: int
    price: float
    amount: float
    timestamp: datetime
    order_id: str = ""
    trade_id: str = field(default_factory=lambda: str(id(datetime.now())))


class Broker:
    """
    券商模拟
    
    处理订单撮合
    """
    
    def __init__(self, config):
        self.config = config
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
    
    def submit_order(self, order: Order) -> bool:
        """提交订单"""
        order.status = OrderStatus.SUBMITTED
        self.orders.append(order)
        logger.debug(f"提交订单: {order.order_id}, {order.symbol}, {order.side.value}, {order.volume}")
        return True
    
    def execute_order(self, order: Order, bar) -> List[Trade]:
        """
        执行订单
        
        Args:
            order: 订单
            bar: 当前K线数据
            
        Returns:
            List[Trade]: 成交记录
        """
        trades = []
        
        if order.order_type == OrderType.MARKET:
            # 市价单：以当前价格成交
            trade_price = bar.close
            trade_volume = order.volume
            
            trade = Trade(
                symbol=order.symbol,
                side=order.side,
                volume=trade_volume,
                price=trade_price,
                amount=trade_price * trade_volume,
                timestamp=bar.timestamp,
                order_id=order.order_id
            )
            
            trades.append(trade)
            
            # 更新订单状态
            order.filled_volume += trade_volume
            order.filled_amount += trade.amount
            order.status = OrderStatus.FILLED
            
            self.trades.append(trade)
        
        elif order.order_type == OrderType.LIMIT:
            # 限价单
            if order.side == OrderSide.BUY and bar.low <= order.limit_price:
                # 买入限价单：价格低于等于限价时成交
                trade_price = min(order.limit_price, bar.close)
                trade_volume = order.volume
                
                trade = Trade(
                    symbol=order.symbol,
                    side=order.side,
                    volume=trade_volume,
                    price=trade_price,
                    amount=trade_price * trade_volume,
                    timestamp=bar.timestamp,
                    order_id=order.order_id
                )
                
                trades.append(trade)
                order.status = OrderStatus.FILLED
                self.trades.append(trade)
            
            elif order.side == OrderSide.SELL and bar.high >= order.limit_price:
                # 卖出限价单：价格高于等于限价时成交
                trade_price = max(order.limit_price, bar.close)
                trade_volume = order.volume
                
                trade = Trade(
                    symbol=order.symbol,
                    side=order.side,
                    volume=trade_volume,
                    price=trade_price,
                    amount=trade_price * trade_volume,
                    timestamp=bar.timestamp,
                    order_id=order.order_id
                )
                
                trades.append(trade)
                order.status = OrderStatus.FILLED
                self.trades.append(trade)
        
        return trades
    
    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        for order in self.orders:
            if order.order_id == order_id:
                if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                    order.status = OrderStatus.CANCELLED
                    logger.debug(f"撤销订单: {order_id}")
                    return True
        return False
    
    def get_open_orders(self) -> List[Order]:
        """获取未成交订单"""
        return [o for o in self.orders if o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]]
    
    def get_trades(self, symbol: str = None) -> List[Trade]:
        """获取成交记录"""
        if symbol:
            return [t for t in self.trades if t.symbol == symbol]
        return self.trades
