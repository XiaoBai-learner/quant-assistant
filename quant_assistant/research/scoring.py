"""Weighted factor scoring."""
from typing import Dict

import pandas as pd


class FactorScorer:
    """Combine processed factor scores into one explainable score."""

    def __init__(self, factor_weights: Dict[str, float], min_valid_ratio: float = 0.6):
        self.factor_weights = dict(factor_weights)
        self.min_valid_ratio = min_valid_ratio

    def score(self, processed: pd.DataFrame) -> pd.DataFrame:
        """Add contribution columns and total score."""
        result = processed.copy()
        factor_names = list(self.factor_weights)
        denominator = sum(abs(weight) for weight in self.factor_weights.values()) or 1.0
        contribution_cols = []

        for name, weight in self.factor_weights.items():
            processed_col = f"{name}_processed"
            contribution_col = f"{name}_contribution"
            result[contribution_col] = result[processed_col].astype(float) * weight
            contribution_cols.append(contribution_col)

        valid_counts = result[[f"{name}_processed" for name in factor_names]].notna().sum(axis=1)
        min_valid = max(1, int(len(factor_names) * self.min_valid_ratio + 0.999999))
        result["valid_factor_count"] = valid_counts
        result["score"] = result[contribution_cols].sum(axis=1, skipna=True) / denominator
        result.loc[valid_counts < min_valid, "score"] = pd.NA
        return result
