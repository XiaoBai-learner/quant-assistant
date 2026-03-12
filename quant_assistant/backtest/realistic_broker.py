"""
真实撮合引擎
模拟订单簿和更真实的成交逻辑
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random

from src.backtest.broker import Broker, Order, Trade, OrderType, OrderSide, OrderStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PriceLevel:
    """价格档位"""
    price: float
    volume: int
    orders: List[Order] = field(default_factory=list)


@dataclass
class OrderBook:
    """订单簿"""
    symbol: str
    timestamp: datetime
    
    # 买盘（价格从高到低）
    bids: List[PriceLevel] = field(default_factory=list)
    # 卖盘（价格从低到高）
    asks: List[PriceLevel] = field(default_factory=list)
    
    def best_bid(self) -> Optional[PriceLevel]:
        """最优买价"""
        return self.bids[0] if self.bids else None
    
    def best_ask(self) -> Optional[PriceLevel]:
        """最优卖价"""
        return self.asks[0] if self.asks else None
    
    def mid_price(self) -> float:
        """中间价"""
        bid = self.best_bid()
        ask = self.best_ask()
        if bid and ask:
            return (bid.price + ask.price) / 2
        return bid.price if bid else (ask.price if ask else 0)
    
    def spread(self) -> float:
        """买卖价差"""
        bid = self.best_bid()
        ask = self.best_ask()
        if bid and ask:
            return ask.price - bid.price
        return 0


class RealisticBroker(Broker):
    """
    真实撮合引擎
    
    特性：
    1. 订单簿模拟
    2. 市价单按订单簿成交
    3. 限价单挂盘等待
    4. 市场冲击模型
    5. 部分成交支持
    """
    
    def __init__(self, config, market_impact: float = 0.0001):
        """
        初始化真实撮合引擎
        
        Args:
            config: 回测配置
            market_impact: 市场冲击系数
        """
        super().__init__(config)
        self.market_impact = market_impact
        self.order_books: Dict[str, OrderBook] = {}
        self.pending_orders: Dict[str, List[Order]] = {}
    
    def update_order_book(self, symbol: str, bar, timestamp: datetime):
        """
        更新订单簿
        
        基于OHLC数据生成模拟订单簿
        """
        # 生成订单簿深度
        spread = (bar.high - bar.low) * 0.001  # 假设价差为范围的0.1%
        mid = bar.close
        
        # 买盘档位（5档）
        bids = []
        for i in range(5):
            price = mid - spread * (i + 1) - random.uniform(0, spread * 0.5)
            volume = int(random.uniform(1000, 10000) * (1 - i * 0.15))
            bids.append(PriceLevel(price=price, volume=volume))
        
        # 卖盘档位（5档）
        asks = []
        for i in range(5):
            price = mid + spread * (i + 1) + random.uniform(0, spread * 0.5)
            volume = int(random.uniform(1000, 10000) * (1 - i * 0.15))
            asks.append(PriceLevel(price=price, volume=volume))
        
        self.order_books[symbol] = OrderBook(
            symbol=symbol,
            timestamp=timestamp,
            bids=bids,
            asks=asks
        )
    
    def execute_order(self, order: Order, bar, timestamp: datetime = None) -> List[Trade]:
        """
        执行订单撮合
        
        Args:
            order: 订单
            bar: K线数据
            timestamp: 时间戳
            
        Returns:
            成交列表
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 更新订单簿
        self.update_order_book(order.symbol, bar, timestamp)
        
        # 根据订单类型执行
        if order.order_type == OrderType.MARKET:
            return self._match_market_order(order, bar)
        elif order.order_type == OrderType.LIMIT:
            return self._match_limit_order(order, bar)
        else:
            logger.warning(f"不支持的订单类型: {order.order_type}")
            return []
    
    def _match_market_order(self, order: Order, bar) -> List[Trade]:
        """
        撮合市价单
        
        按订单簿最优价格成交，考虑市场冲击
        """
        trades = []
        book = self.order_books.get(order.symbol)
        
        if not book:
            # 无订单簿，按简单逻辑成交
            return self._simple_match(order, bar)
        
        remaining = order.remaining_volume()
        
        if order.side == OrderSide.BUY:
            # 买入：从卖盘成交
            for level in book.asks:
                if remaining <= 0:
                    break
                
                # 考虑市场冲击
                impact_price = level.price * (1 + self.market_impact)
                
                # 计算可成交量
                fill_volume = min(remaining, level.volume)
                
                # 创建成交
                trade = Trade(
                    symbol=order.symbol,
                    side=order.side,
                    volume=fill_volume,
                    price=impact_price,
                    amount=fill_volume * impact_price,
                    timestamp=datetime.now(),
                    order_id=order.order_id
                )
                trades.append(trade)
                
                # 更新订单状态
                order.filled_volume += fill_volume
                order.filled_amount += fill_volume * impact_price
                remaining -= fill_volume
                
                if order.filled_volume >= order.volume:
                    order.status = OrderStatus.FILLED
                    break
        
        else:  # SELL
            # 卖出：从买盘成交
            for level in book.bids:
                if remaining <= 0:
                    break
                
                # 考虑市场冲击
                impact_price = level.price * (1 - self.market_impact)
                
                # 计算可成交量
                fill_volume = min(remaining, level.volume)
                
                # 创建成交
                trade = Trade(
                    symbol=order.symbol,
                    side=order.side,
                    volume=fill_volume,
                    price=impact_price,
                    amount=fill_volume * impact_price,
                    timestamp=datetime.now(),
                    order_id=order.order_id
                )
                trades.append(trade)
                
                # 更新订单状态
                order.filled_volume += fill_volume
                order.filled_amount += fill_volume * impact_price
                remaining -= fill_volume
                
                if order.filled_volume >= order.volume:
                    order.status = OrderStatus.FILLED
                    break
        
        # 更新订单状态
        if order.filled_volume > 0 and order.filled_volume < order.volume:
            order.status = OrderStatus.PARTIAL_FILLED
        
        return trades
    
    def _match_limit_order(self, order: Order, bar) -> List[Trade]:
        """
        撮合限价单
        
        如果价格触及限价，则成交；否则挂入订单簿等待
        """
        trades = []
        book = self.order_books.get(order.symbol)
        
        if not book:
            # 无订单簿，挂起订单
            self._add_to_pending(order)
            return trades
        
        # 检查是否可以立即成交
        if order.side == OrderSide.BUY:
            # 买入：如果最优卖价 <= 限价
            best_ask = book.best_ask()
            if best_ask and best_ask.price <= order.limit_price:
                # 可以成交
                trades = self._match_market_order(order, bar)
            else:
                # 挂起订单
                self._add_to_pending(order)
        
        else:  # SELL
            # 卖出：如果最优买价 >= 限价
            best_bid = book.best_bid()
            if best_bid and best_bid.price >= order.limit_price:
                # 可以成交
                trades = self._match_market_order(order, bar)
            else:
                # 挂起订单
                self._add_to_pending(order)
        
        return trades
    
    def _simple_match(self, order: Order, bar) -> List[Trade]:
        """简单撮合（无订单簿时回退）"""
        # 使用父类的简单撮合逻辑
        return super().execute_order(order, bar)
    
    def _add_to_pending(self, order: Order):
        """添加订单到挂单列表"""
        if order.symbol not in self.pending_orders:
            self.pending_orders[order.symbol] = []
        self.pending_orders[order.symbol].append(order)
        order.status = OrderStatus.PENDING
        logger.debug(f"订单挂起: {order.order_id}, 限价: {order.limit_price}")
    
    def check_pending_orders(self, symbol: str, bar, timestamp: datetime = None):
        """
        检查挂单是否可以成交
        
        在每个bar结束时调用
        """
        if symbol not in self.pending_orders:
            return
        
        # 更新订单簿
        self.update_order_book(symbol, bar, timestamp)
        book = self.order_books.get(symbol)
        
        if not book:
            return
        
        # 检查每个挂单
        filled_orders = []
        for order in self.pending_orders[symbol]:
            if order.order_type != OrderType.LIMIT:
                continue
            
            can_fill = False
            
            if order.side == OrderSide.BUY:
                # 买入：最优卖价 <= 限价
                best_ask = book.best_ask()
                if best_ask and best_ask.price <= order.limit_price:
                    can_fill = True
            else:
                # 卖出：最优买价 >= 限价
                best_bid = book.best_bid()
                if best_bid and best_bid.price >= order.limit_price:
                    can_fill = True
            
            if can_fill:
                # 执行成交
                trades = self._match_market_order(order, bar)
                filled_orders.append(order)
                
                # 添加成交记录
                self.trades.extend(trades)
        
        # 移除已成交订单
        for order in filled_orders:
            self.pending_orders[symbol].remove(order)
    
    def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """获取订单簿"""
        return self.order_books.get(symbol)
    
    def get_market_depth(self, symbol: str) -> Dict[str, List]:
        """
        获取市场深度
        
        Returns:
            {'bids': [[price, volume], ...], 'asks': [[price, volume], ...]}
        """
        book = self.order_books.get(symbol)
        if not book:
            return {'bids': [], 'asks': []}
        
        return {
            'bids': [[level.price, level.volume] for level in book.bids],
            'asks': [[level.price, level.volume] for level in book.asks]
        }
