"""
数据质量校验器
提供数据完整性、逻辑性、异常值检查
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class ValidationCheck:
    """单项校验结果"""
    name: str
    passed: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """校验结果"""
    checks: List[ValidationCheck]
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_valid(self) -> bool:
        """是否全部通过"""
        return all(check.passed for check in self.checks)
    
    @property
    def passed_count(self) -> int:
        """通过的检查数"""
        return sum(1 for check in self.checks if check.passed)
    
    @property
    def failed_count(self) -> int:
        """失败的检查数"""
        return sum(1 for check in self.checks if not check.passed)
    
    def get_failed_checks(self) -> List[ValidationCheck]:
        """获取失败的检查"""
        return [check for check in self.checks if not check.passed]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'is_valid': self.is_valid,
            'passed_count': self.passed_count,
            'failed_count': self.failed_count,
            'timestamp': self.timestamp.isoformat(),
            'checks': [
                {
                    'name': c.name,
                    'passed': c.passed,
                    'message': c.message,
                    'details': c.details
                }
                for c in self.checks
            ]
        }


class DataValidator:
    """数据校验器"""
    
    def __init__(self):
        self.price_tolerance = 0.5  # 价格异常容忍度（涨跌幅超过50%视为异常）
        self.volume_tolerance = 10  # 成交量异常容忍度（超过均值10倍视为异常）
    
    def validate_price_data(self, df: pd.DataFrame) -> ValidationResult:
        """
        校验价格数据
        
        检查项：
        1. 无缺失值
        2. 价格逻辑正确 (high >= low >= 0, high >= close >= low, high >= open >= low)
        3. 成交量为正
        4. 无重复数据
        5. 无异常值
        """
        checks = []
        
        # 1. 检查缺失值
        checks.append(self._check_missing_values(df))
        
        # 2. 检查价格逻辑
        checks.append(self._check_price_logic(df))
        
        # 3. 检查成交量
        checks.append(self._check_volume_positive(df))
        
        # 4. 检查重复数据
        checks.append(self._check_duplicates(df))
        
        # 5. 检查异常值
        checks.append(self._check_price_outliers(df))
        checks.append(self._check_volume_outliers(df))
        
        return ValidationResult(checks=checks)
    
    def _check_missing_values(self, df: pd.DataFrame) -> ValidationCheck:
        """检查缺失值"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = df[required_cols].isnull().sum().sum()
        
        if missing == 0:
            return ValidationCheck(
                name="缺失值检查",
                passed=True,
                message="无缺失值"
            )
        else:
            missing_cols = df[required_cols].isnull().sum()
            missing_cols = missing_cols[missing_cols > 0]
            return ValidationCheck(
                name="缺失值检查",
                passed=False,
                message=f"发现 {missing} 个缺失值",
                details={'missing_by_column': missing_cols.to_dict()}
            )
    
    def _check_price_logic(self, df: pd.DataFrame) -> ValidationCheck:
        """检查价格逻辑"""
        errors = []
        
        # high >= low
        invalid_hl = (df['high'] < df['low']).sum()
        if invalid_hl > 0:
            errors.append(f"{invalid_hl} 条数据 high < low")
        
        # high >= close >= low
        invalid_close = ((df['close'] > df['high']) | (df['close'] < df['low'])).sum()
        if invalid_close > 0:
            errors.append(f"{invalid_close} 条数据 close 不在 [low, high] 范围内")
        
        # high >= open >= low
        invalid_open = ((df['open'] > df['high']) | (df['open'] < df['low'])).sum()
        if invalid_open > 0:
            errors.append(f"{invalid_open} 条数据 open 不在 [low, high] 范围内")
        
        # 价格必须为正
        negative_prices = (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1).sum()
        if negative_prices > 0:
            errors.append(f"{negative_prices} 条数据包含非正价格")
        
        if not errors:
            return ValidationCheck(
                name="价格逻辑检查",
                passed=True,
                message="价格逻辑正确"
            )
        else:
            return ValidationCheck(
                name="价格逻辑检查",
                passed=False,
                message="; ".join(errors),
                details={'error_count': len(errors)}
            )
    
    def _check_volume_positive(self, df: pd.DataFrame) -> ValidationCheck:
        """检查成交量为正"""
        invalid_volume = (df['volume'] <= 0).sum()
        
        if invalid_volume == 0:
            return ValidationCheck(
                name="成交量检查",
                passed=True,
                message="成交量全部为正"
            )
        else:
            return ValidationCheck(
                name="成交量检查",
                passed=False,
                message=f"{invalid_volume} 条数据成交量非正"
            )
    
    def _check_duplicates(self, df: pd.DataFrame) -> ValidationCheck:
        """检查重复数据"""
        if 'symbol' in df.columns and 'trade_date' in df.columns:
            duplicates = df.duplicated(subset=['symbol', 'trade_date']).sum()
        elif 'trade_date' in df.columns:
            duplicates = df.duplicated(subset=['trade_date']).sum()
        else:
            duplicates = df.duplicated().sum()
        
        if duplicates == 0:
            return ValidationCheck(
                name="重复数据检查",
                passed=True,
                message="无重复数据"
            )
        else:
            return ValidationCheck(
                name="重复数据检查",
                passed=False,
                message=f"发现 {duplicates} 条重复数据"
            )
    
    def _check_price_outliers(self, df: pd.DataFrame) -> ValidationCheck:
        """检查价格异常值"""
        # 计算涨跌幅
        df_copy = df.copy()
        df_copy['change_pct'] = df_copy['close'].pct_change() * 100
        
        # 检查超过容忍度的涨跌幅
        outliers = (df_copy['change_pct'].abs() > self.price_tolerance * 100).sum()
        
        if outliers == 0:
            return ValidationCheck(
                name="价格异常值检查",
                passed=True,
                message="无价格异常值"
            )
        else:
            extreme_changes = df_copy[df_copy['change_pct'].abs() > self.price_tolerance * 100]['change_pct']
            return ValidationCheck(
                name="价格异常值检查",
                passed=False,
                message=f"发现 {outliers} 条价格异常数据",
                details={
                    'max_change_pct': float(extreme_changes.abs().max()),
                    'threshold': self.price_tolerance * 100
                }
            )
    
    def _check_volume_outliers(self, df: pd.DataFrame) -> ValidationCheck:
        """检查成交量异常值"""
        mean_volume = df['volume'].mean()
        outliers = (df['volume'] > mean_volume * self.volume_tolerance).sum()
        
        if outliers == 0:
            return ValidationCheck(
                name="成交量异常值检查",
                passed=True,
                message="无成交量异常值"
            )
        else:
            max_volume = df['volume'].max()
            return ValidationCheck(
                name="成交量异常值检查",
                passed=False,
                message=f"发现 {outliers} 条成交量异常数据",
                details={
                    'max_volume': int(max_volume),
                    'mean_volume': int(mean_volume),
                    'threshold': int(mean_volume * self.volume_tolerance)
                }
            )
    
    def validate_stock_list(self, df: pd.DataFrame) -> ValidationResult:
        """校验股票列表数据"""
        checks = []
        
        # 检查必要字段
        required_cols = ['symbol', 'name', 'exchange']
        missing_cols = [c for c in required_cols if c not in df.columns]
        
        if missing_cols:
            checks.append(ValidationCheck(
                name="必要字段检查",
                passed=False,
                message=f"缺少必要字段: {missing_cols}"
            ))
        else:
            checks.append(ValidationCheck(
                name="必要字段检查",
                passed=True,
                message="所有必要字段存在"
            ))
        
        # 检查代码格式
        if 'symbol' in df.columns:
            invalid_symbols = df[~df['symbol'].str.match(r'^\d{6}$', na=False)]
            if len(invalid_symbols) == 0:
                checks.append(ValidationCheck(
                    name="代码格式检查",
                    passed=True,
                    message="代码格式正确"
                ))
            else:
                checks.append(ValidationCheck(
                    name="代码格式检查",
                    passed=False,
                    message=f"{len(invalid_symbols)} 条代码格式不正确"
                ))
        
        return ValidationResult(checks=checks)
