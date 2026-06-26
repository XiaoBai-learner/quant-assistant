"""Cross-sectional factor preprocessing."""
from typing import Dict, List

import pandas as pd

from .factors import FactorDefinition


class FactorPreprocessor:
    """Transform raw factor values into comparable cross-sectional scores."""

    def __init__(self, definitions: Dict[str, FactorDefinition], min_coverage: float = 0.5):
        self.definitions = definitions
        self.min_coverage = min_coverage
        self.disabled_factors: Dict[pd.Timestamp, List[str]] = {}

    def transform(self, factor_data: pd.DataFrame, factor_names: List[str]) -> pd.DataFrame:
        """Winsorize, z-score, and apply factor direction by rebalance date."""
        output = factor_data.copy()
        output["trade_date"] = pd.to_datetime(output["trade_date"])

        for trade_date, idx in output.groupby("trade_date").groups.items():
            disabled = []
            for name in factor_names:
                values = output.loc[idx, name].astype(float)
                coverage = values.notna().mean() if len(values) else 0.0
                processed_col = f"{name}_processed"
                valid_col = f"{name}_valid"
                if coverage < self.min_coverage:
                    output.loc[idx, processed_col] = pd.NA
                    output.loc[idx, valid_col] = False
                    disabled.append(name)
                    continue

                clipped = self._winsorize(values)
                zscore = self._zscore(clipped)
                direction = self.definitions[name].direction
                if direction == "negative":
                    zscore = -zscore
                output.loc[idx, processed_col] = zscore.clip(-3, 3)
                output.loc[idx, valid_col] = values.notna()
            if disabled:
                self.disabled_factors[pd.Timestamp(trade_date)] = disabled
        return output

    @staticmethod
    def _winsorize(values: pd.Series) -> pd.Series:
        valid = values.dropna()
        if valid.empty:
            return values
        lower = valid.quantile(0.01)
        upper = valid.quantile(0.99)
        return values.clip(lower, upper)

    @staticmethod
    def _zscore(values: pd.Series) -> pd.Series:
        mean = values.mean(skipna=True)
        std = values.std(skipna=True)
        if pd.isna(std) or std == 0:
            return values.where(values.isna(), 0.0)
        return (values - mean) / std
