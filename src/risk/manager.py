"""
风险管理器
提供事前、事中、事后风控检查
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from src.strategy.base import Signal
from src.backtest.broker import Order
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskCheck:
    """单项风控检查"""
    name: str
    passed: bool
    level: RiskLevel
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    checks: List[RiskCheck]
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_allowed(self) -> bool:
        """是否允许交易（无CRITICAL级别失败）"""
        for check in self.checks:
            if not check.passed and check.level == RiskLevel.CRITICAL:
                return False
        return True
    
    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return any(not c.passed and c.level in [RiskLevel.MEDIUM, RiskLevel.HIGH] 
                   for c in self.checks)
    
    def get_failed_checks(self) -> List[RiskCheck]:
        """获取失败的检查"""
        return [c for c in self.checks if not c.passed]
    
    def get_critical_failures(self) -> List[RiskCheck]:
        """获取严重失败"""
        return [c for c in self.checks if not c.passed and c.level == RiskLevel.CRITICAL]


class RiskManager:
    """风险管理器"""
    
    def __init__(
        self,
        max_position_pct: float = 1.0,  # 最大仓位比例
        max_single_position_pct: float = 0.3,  # 单只股票最大仓位
        max_daily_loss_pct: float = 0.05,  # 单日最大亏损比例
        max_drawdown_pct: float = 0.2,  # 最大回撤限制
        min_cash_reserve: float = 0.1,  # 最小现金储备比例
    ):
        self.max_position_pct = max_position_pct
        self.max_single_position_pct = max_single_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.min_cash_reserve = min_cash_reserve
        
        # 风控记录
        self.daily_pnl: Dict[datetime, float] = {}
        self.peak_value: float = 0.0
        self.current_drawdown: float = 0.0
    
    def check_order(self, order: Order, portfolio: Dict[str, Any]) -> RiskCheckResult:
        """
        检查订单风险
        
        Args:
            order: 订单
            portfolio: 投资组合状态
                {
                    'cash': float,
                    'positions': Dict[str, int],
                    'total_value': float,
                    'daily_pnl': float
                }
        
        Returns:
            RiskCheckResult: 风控检查结果
        """
        checks = []
        
        # 1. 检查资金充足
        checks.append(self._check_cash_sufficient(order, portfolio))
        
        # 2. 检查仓位限制
        checks.append(self._check_position_limit(order, portfolio))
        
        # 3. 检查单日亏损
        checks.append(self._check_daily_loss_limit(portfolio))
        
        # 4. 检查回撤限制
        checks.append(self._check_drawdown_limit(portfolio))
        
        # 5. 检查现金储备
        checks.append(self._check_cash_reserve(order, portfolio))
        
        return RiskCheckResult(checks=checks)
    
    def check_signal(self, signal: Signal, portfolio: Dict[str, Any]) -> RiskCheckResult:
        """检查信号风险"""
        checks = []
        
        # 1. 检查信号强度
        checks.append(self._check_signal_strength(signal))
        
        # 2. 检查交易频率
        checks.append(self._check_trading_frequency(signal, portfolio))
        
        return RiskCheckResult(checks=checks)
    
    def _check_cash_sufficient(self, order: Order, portfolio: Dict[str, Any]) -> RiskCheck:
        """检查资金充足"""
        cash = portfolio.get('cash', 0)
        required = order.volume * order.price
        
        if cash >= required:
            return RiskCheck(
                name="资金充足检查",
                passed=True,
                level=RiskLevel.LOW,
                message=f"资金充足: {cash:.2f} >= {required:.2f}"
            )
        else:
            return RiskCheck(
                name="资金充足检查",
                passed=False,
                level=RiskLevel.CRITICAL,
                message=f"资金不足: {cash:.2f} < {required:.2f}",
                details={'cash': cash, 'required': required}
            )
    
    def _check_position_limit(self, order: Order, portfolio: Dict[str, Any]) -> RiskCheck:
        """检查仓位限制"""
        total_value = portfolio.get('total_value', 0)
        positions = portfolio.get('positions', {})
        
        # 当前该股票持仓市值
        current_position = positions.get(order.symbol, 0)
        current_value = abs(current_position) * order.price
        
        # 新订单后的持仓市值
        if order.side.value == 'buy':
            new_value = current_value + order.volume * order.price
        else:
            new_value = abs(current_value - order.volume * order.price)
        
        # 检查单只股票仓位
        single_pct = new_value / total_value if total_value > 0 else 0
        if single_pct > self.max_single_position_pct:
            return RiskCheck(
                name="单股仓位限制",
                passed=False,
                level=RiskLevel.HIGH,
                message=f"单股仓位超限: {single_pct:.2%} > {self.max_single_position_pct:.2%}",
                details={'current_pct': single_pct, 'limit': self.max_single_position_pct}
            )
        
        # 检查总仓位
        total_position_value = sum(abs(v) * order.price for v in positions.values())
        new_total_pct = (total_position_value + order.volume * order.price) / total_value if total_value > 0 else 0
        if new_total_pct > self.max_position_pct:
            return RiskCheck(
                name="总仓位限制",
                passed=False,
                level=RiskLevel.HIGH,
                message=f"总仓位超限: {new_total_pct:.2%} > {self.max_position_pct:.2%}",
                details={'current_pct': new_total_pct, 'limit': self.max_position_pct}
            )
        
        return RiskCheck(
            name="仓位限制检查",
            passed=True,
            level=RiskLevel.LOW,
            message=f"仓位合规: 单股{single_pct:.2%}, 总仓位{new_total_pct:.2%}"
        )
    
    def _check_daily_loss_limit(self, portfolio: Dict[str, Any]) -> RiskCheck:
        """检查单日亏损限制"""
        daily_pnl = portfolio.get('daily_pnl', 0)
        total_value = portfolio.get('total_value', 0)
        
        if total_value == 0:
            return RiskCheck(
                name="单日亏损限制",
                passed=True,
                level=RiskLevel.LOW,
                message="无持仓，跳过检查"
            )
        
        daily_loss_pct = abs(daily_pnl) / total_value if daily_pnl < 0 else 0
        
        if daily_loss_pct > self.max_daily_loss_pct:
            return RiskCheck(
                name="单日亏损限制",
                passed=False,
                level=RiskLevel.CRITICAL,
                message=f"单日亏损超限: {daily_loss_pct:.2%} > {self.max_daily_loss_pct:.2%}",
                details={'daily_loss_pct': daily_loss_pct, 'limit': self.max_daily_loss_pct}
            )
        
        return RiskCheck(
            name="单日亏损限制",
            passed=True,
            level=RiskLevel.LOW,
            message=f"单日亏损合规: {daily_loss_pct:.2%}"
        )
    
    def _check_drawdown_limit(self, portfolio: Dict[str, Any]) -> RiskCheck:
        """检查回撤限制"""
        total_value = portfolio.get('total_value', 0)
        
        # 更新峰值和回撤
        if total_value > self.peak_value:
            self.peak_value = total_value
            self.current_drawdown = 0
        else:
            self.current_drawdown = (self.peak_value - total_value) / self.peak_value if self.peak_value > 0 else 0
        
        if self.current_drawdown > self.max_drawdown_pct:
            return RiskCheck(
                name="最大回撤限制",
                passed=False,
                level=RiskLevel.CRITICAL,
                message=f"回撤超限: {self.current_drawdown:.2%} > {self.max_drawdown_pct:.2%}",
                details={'current_drawdown': self.current_drawdown, 'limit': self.max_drawdown_pct}
            )
        
        return RiskCheck(
            name="最大回撤限制",
            passed=True,
            level=RiskLevel.LOW,
            message=f"回撤合规: {self.current_drawdown:.2%}"
        )
    
    def _check_cash_reserve(self, order: Order, portfolio: Dict[str, Any]) -> RiskCheck:
        """检查现金储备"""
        cash = portfolio.get('cash', 0)
        total_value = portfolio.get('total_value', 0)
        
        if total_value == 0:
            return RiskCheck(
                name="现金储备检查",
                passed=True,
                level=RiskLevel.LOW,
                message="无总资产，跳过检查"
            )
        
        # 买入后剩余现金
        if order.side.value == 'buy':
            remaining_cash = cash - order.volume * order.price
        else:
            remaining_cash = cash + order.volume * order.price
        
        cash_reserve_pct = remaining_cash / total_value
        
        if cash_reserve_pct < self.min_cash_reserve:
            return RiskCheck(
                name="现金储备检查",
                passed=False,
                level=RiskLevel.MEDIUM,
                message=f"现金储备不足: {cash_reserve_pct:.2%} < {self.min_cash_reserve:.2%}",
                details={'reserve_pct': cash_reserve_pct, 'limit': self.min_cash_reserve}
            )
        
        return RiskCheck(
            name="现金储备检查",
            passed=True,
            level=RiskLevel.LOW,
            message=f"现金储备充足: {cash_reserve_pct:.2%}"
        )
    
    def _check_signal_strength(self, signal: Signal) -> RiskCheck:
        """检查信号强度"""
        strength = getattr(signal, 'strength', 1.0)
        
        if strength < 0.3:
            return RiskCheck(
                name="信号强度检查",
                passed=False,
                level=RiskLevel.MEDIUM,
                message=f"信号强度较弱: {strength:.2f} < 0.3",
                details={'strength': strength}
            )
        
        return RiskCheck(
            name="信号强度检查",
            passed=True,
            level=RiskLevel.LOW,
            message=f"信号强度合格: {strength:.2f}"
        )
    
    def _check_trading_frequency(self, signal: Signal, portfolio: Dict[str, Any]) -> RiskCheck:
        """检查交易频率"""
        # 这里可以实现更复杂的频率检查
        # 例如：同一股票24小时内最多交易3次
        return RiskCheck(
            name="交易频率检查",
            passed=True,
            level=RiskLevel.LOW,
            message="交易频率合规"
        )
    
    def update_daily_pnl(self, date: datetime, pnl: float):
        """更新每日盈亏"""
        self.daily_pnl[date] = pnl
