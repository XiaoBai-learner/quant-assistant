"""
WP4: Layout Manager - 图表布局管理
管理多个图表的排列和显示
"""
from typing import List, Dict, Any, Optional
import pandas as pd

from ..renderers.base_renderer import BaseRenderer
from ..renderers.ascii_renderer import ASCIIRenderer, SimpleTableRenderer
from ..indicators.engine import IndicatorEngine
from ..adapters.data_adapter import DataAdapter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChartLayout:
    """
    图表布局管理器
    
    整合数据适配、指标计算和图表渲染
    提供统一的图表展示接口
    """
    
    def __init__(self, renderer: BaseRenderer = None):
        """
        初始化布局管理器
        
        Args:
            renderer: 渲染器实例，默认使用ASCIIRenderer
        """
        self.data_adapter = DataAdapter()
        self.indicator_engine = IndicatorEngine()
        self.renderer = renderer or ASCIIRenderer()
        self.table_renderer = SimpleTableRenderer()
        
        logger.info("图表布局管理器初始化完成")
    
    def display(
        self,
        df: pd.DataFrame,
        symbol: str = "",
        period: str = "D",
        indicators: List[str] = None,
        show_table: bool = True,
        show_chart: bool = True
    ) -> str:
        """
        显示完整图表
        
        Args:
            df: 原始行情数据
            symbol: 股票代码
            period: 周期 'D'=日线, 'W'=周线
            indicators: 要显示的指标列表
            show_table: 是否显示数据表格
            show_chart: 是否显示K线图
            
        Returns:
            str: 渲染后的图表字符串
        """
        if df.empty:
            return "错误: 无数据"
        
        lines = []
        
        # 标题
        period_name = {'D': '日线', 'W': '周线', 'M': '月线'}.get(period, '日线')
        title = f"{symbol} {period_name}行情"
        lines.append(self._render_header(title))
        
        # 数据准备
        try:
            df_prepared = self.data_adapter.prepare_for_chart(df, period)
        except Exception as e:
            logger.error(f"数据准备失败: {e}")
            return f"错误: 数据准备失败 - {e}"
        
        # 计算指标
        indicator_results = {}
        if indicators:
            try:
                indicator_results = self.indicator_engine.calculate(
                    df_prepared, indicators
                )
            except Exception as e:
                logger.error(f"指标计算失败: {e}")
        
        # 数据表格
        if show_table:
            lines.append(self.table_renderer.render(df_prepared))
        
        # K线图
        if show_chart:
            lines.append(self.renderer.render_candlestick(df_prepared))
        
        # 指标显示
        if indicator_results:
            lines.append(self._render_separator())
            lines.append("技术指标:")
            for name, result in indicator_results.items():
                lines.append(self.renderer.render_indicator(result))
        
        # 数据摘要
        if not df_prepared.empty:
            lines.append(self._render_separator())
            lines.append(self.renderer.render_summary(df_prepared))
        
        return '\n'.join(lines)
    
    def display_with_ma(
        self,
        df: pd.DataFrame,
        symbol: str = "",
        period: str = "D",
        ma_periods: List[int] = None
    ) -> str:
        """
        显示K线 + 移动平均线
        
        Args:
            df: 行情数据
            symbol: 股票代码
            period: 周期
            ma_periods: MA周期列表，默认 [5, 10, 20]
            
        Returns:
            str: 渲染后的图表
        """
        ma_periods = ma_periods or [5, 10, 20]
        indicators = [f"MA{p}" for p in ma_periods]
        
        # 注册MA指标
        from ..indicators.moving_average import MAIndicator
        for p in ma_periods:
            self.indicator_engine.register(MAIndicator(period=p))
        
        return self.display(df, symbol, period, indicators)
    
    def display_with_macd(
        self,
        df: pd.DataFrame,
        symbol: str = "",
        period: str = "D"
    ) -> str:
        """
        显示K线 + MACD指标
        
        Args:
            df: 行情数据
            symbol: 股票代码
            period: 周期
            
        Returns:
            str: 渲染后的图表
        """
        return self.display(df, symbol, period, indicators=['MACD'])
    
    def _render_header(self, title: str) -> str:
        """渲染标题头"""
        width = 60
        lines = [
            "=" * width,
            f"{title:^{width}}",
            "=" * width,
        ]
        return '\n'.join(lines)
    
    def _render_separator(self) -> str:
        """渲染分隔线"""
        return "-" * 60
