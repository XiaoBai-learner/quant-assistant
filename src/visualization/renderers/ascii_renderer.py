"""
ASCII 图表渲染器
在命令行中展示K线图和指标
"""
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from .base_renderer import BaseRenderer
from ..indicators.base import IndicatorResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ASCIIRenderer(BaseRenderer):
    """
    ASCII 图表渲染器
    
    使用 ASCII 字符在命令行中绘制图表
    """
    
    # ASCII 绘图字符
    CHARS = {
        'up': '▲',      # 上涨
        'down': '▼',    # 下跌
        'horizontal': '─',
        'vertical': '│',
        'cross': '┼',
        'top_left': '┌',
        'top_right': '┐',
        'bottom_left': '└',
        'bottom_right': '┘',
        'left_t': '├',
        'right_t': '┤',
        'top_t': '┬',
        'bottom_t': '┴',
        'block': '█',
        'half_block': '▄',
        'empty': ' ',
    }
    
    def __init__(self, width: int = 80, height: int = 15):
        super().__init__(width, height)
    
    def render(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, IndicatorResult] = None,
        title: str = ""
    ) -> str:
        """
        渲染完整图表 (K线 + 指标)
        """
        lines = []
        
        # 标题
        if title:
            lines.append(self._render_title(title))
        
        # K线图
        lines.append(self.render_candlestick(df))
        
        # 指标
        if indicators:
            lines.append(self._render_separator())
            for name, result in indicators.items():
                lines.append(self.render_indicator(result))
        
        return '\n'.join(lines)
    
    def render_candlestick(
        self,
        df: pd.DataFrame,
        title: str = ""
    ) -> str:
        """
        渲染ASCII K线图
        
        简化版: 使用折线图展示收盘价走势
        """
        if df.empty:
            return "无数据"
        
        # 取最近的数据点 (根据宽度调整)
        max_points = min(len(df), self.width - 10)
        df_plot = df.tail(max_points).reset_index(drop=True)
        
        # 计算价格范围
        high = df_plot['high'].max()
        low = df_plot['low'].min()
        price_range = high - low if high != low else 1
        
        # 构建图表
        lines = []
        
        # Y轴标签宽度
        label_width = 8
        chart_width = self.width - label_width - 2
        
        # 绘制标题
        if title:
            lines.append(f"{' ' * label_width}{title:^{chart_width}}")
        
        # 绘制Y轴和价格刻度
        for i in range(self.height):
            price = high - (i / (self.height - 1)) * price_range
            label = f"{price:7.2f} "
            
            # 绘制价格线
            line_chars = [' '] * chart_width
            
            for j, row in df_plot.iterrows():
                x = int((j / (len(df_plot) - 1)) * (chart_width - 1)) if len(df_plot) > 1 else 0
                
                # 计算该价格点在Y轴的位置
                price_normalized = (row['close'] - low) / price_range
                y_pos = int((1 - price_normalized) * (self.height - 1))
                
                if y_pos == i:
                    # 判断涨跌
                    if row['close'] >= row['open']:
                        line_chars[x] = self.CHARS['up']
                    else:
                        line_chars[x] = self.CHARS['down']
            
            line = label + self.CHARS['vertical'] + ''.join(line_chars)
            lines.append(line)
        
        # X轴
        x_axis = ' ' * label_width + self.CHARS['bottom_left'] + self.CHARS['horizontal'] * chart_width + self.CHARS['bottom_right']
        lines.append(x_axis)
        
        # 日期标签
        date_start = str(df_plot['trade_date'].iloc[0])[-5:]  # MM-DD
        date_end = str(df_plot['trade_date'].iloc[-1])[-5:]
        date_line = ' ' * label_width + f"{date_start:^{chart_width}}{date_end:>{0}}"
        lines.append(date_line)
        
        return '\n'.join(lines)
    
    def render_indicator(self, result: IndicatorResult, title: str = "") -> str:
        """渲染指标"""
        lines = []
        
        name = title or result.name
        values = result.values.dropna()
        
        if len(values) == 0:
            return f"{name}: 无数据"
        
        # 最新值
        latest = values.iloc[-1]
        prev = values.iloc[-2] if len(values) > 1 else latest
        change = latest - prev
        
        # 趋势箭头
        arrow = "▲" if change >= 0 else "▼"
        
        # 指标信息行
        lines.append(f"{name:8s}: {latest:8.3f} {arrow} ({change:+.3f})")
        
        # MACD 特殊处理
        if name == "MACD" and result.metadata:
            dif = result.metadata['DIF'].iloc[-1]
            dea = result.metadata['DEA'].iloc[-1]
            macd = result.metadata['MACD'].iloc[-1]
            
            lines.append(f"  DIF: {dif:8.3f}  DEA: {dea:8.3f}  MACD: {macd:8.3f}")
            
            # MACD柱状图
            bar_length = int(abs(macd) * 20)
            bar = self.CHARS['block'] * min(bar_length, 40)
            if macd >= 0:
                lines.append(f"  {bar} (+)")
            else:
                lines.append(f"  {bar} (-)")
        
        return '\n'.join(lines)
    
    def render_summary(self, df: pd.DataFrame) -> str:
        """渲染数据摘要"""
        if df.empty:
            return "无数据"
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        change = latest['close'] - prev['close']
        change_pct = (change / prev['close'] * 100) if prev['close'] != 0 else 0
        
        arrow = "▲" if change >= 0 else "▼"
        
        lines = [
            f"最新价: {latest['close']:.2f} {arrow} {change:+.2f} ({change_pct:+.2f}%)",
            f"最高: {latest['high']:.2f}  最低: {latest['low']:.2f}  开盘: {latest['open']:.2f}",
            f"成交量: {latest['volume']:,.0f}  成交额: {latest['amount']:,.0f}",
            f"日期: {latest['trade_date']}",
        ]
        
        return '\n'.join(lines)
    
    def _render_title(self, title: str) -> str:
        """渲染标题"""
        padding = (self.width - len(title) - 2) // 2
        return f"{'=' * padding} {title} {'=' * padding}"
    
    def _render_separator(self) -> str:
        """渲染分隔线"""
        return '-' * self.width


class SimpleTableRenderer(BaseRenderer):
    """
    简单表格渲染器
    以表格形式展示数据
    """
    
    def render(self, df: pd.DataFrame, indicators: Dict[str, IndicatorResult] = None, title: str = "") -> str:
        """渲染数据表格"""
        if df.empty:
            return "无数据"
        
        lines = []
        
        if title:
            lines.append(f"\n{'=' * 60}")
            lines.append(f"  {title}")
            lines.append(f"{'=' * 60}\n")
        
        # 表头
        header = f"{'日期':<12} {'开盘':>8} {'最高':>8} {'最低':>8} {'收盘':>8} {'涨跌%':>8} {'成交量':>12}"
        lines.append(header)
        lines.append('-' * 80)
        
        # 数据行 (显示最近10条)
        for _, row in df.tail(10).iterrows():
            change_pct = row.get('pct_change', 0)
            line = (
                f"{str(row['trade_date']):<12} "
                f"{row['open']:>8.2f} "
                f"{row['high']:>8.2f} "
                f"{row['low']:>8.2f} "
                f"{row['close']:>8.2f} "
                f"{change_pct:>8.2f} "
                f"{row['volume']:>12,}"
            )
            lines.append(line)
        
        return '\n'.join(lines)
    
    def render_candlestick(self, df: pd.DataFrame, title: str = "") -> str:
        """表格形式渲染K线"""
        return self.render(df, title=title)
    
    def render_indicator(self, result: IndicatorResult, title: str = "") -> str:
        """渲染指标值"""
        lines = []
        name = title or result.name
        values = result.values.dropna()
        
        if len(values) > 0:
            lines.append(f"\n{name} 指标:")
            lines.append(f"  最新值: {values.iloc[-1]:.4f}")
            lines.append(f"  周期参数: {result.params}")
        
        return '\n'.join(lines)
