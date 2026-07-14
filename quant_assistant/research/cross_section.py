"""Cross-sectional factor processing for stock-pool research.

The missing "工序" that makes single-stock time-series factors comparable
across the whole market on the same day: outlier trimming (winsorize),
standardization (z-score / rank), and neutralization (remove industry and
size beta). All operations run strictly within one ``trade_date`` slice, so
they never leak information across days.

Honest boundaries:
- Size neutralization uses ``amount`` as a proxy for float market cap because
  real share-count data is not cached. This removes a liquidity/size beta but
  is not identical to true market-cap neutralization.
- A too-small daily cross-section is pure noise, so days with fewer than
  ``min_samples`` valid observations are returned as NaN rather than
  standardized.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


def winsorize(
    series: pd.Series,
    lower: float = 0.01,
    upper: float = 0.99,
    method: str = "quantile",
    mad_scale: float = 3.0,
) -> pd.Series:
    """Clip extreme values.

    ``method="quantile"`` clips to the [lower, upper] empirical quantiles.
    ``method="mad"`` clips to median +/- ``mad_scale`` * (1.4826 * MAD).
    """
    values = pd.to_numeric(series, errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return values
    if method == "mad":
        median = valid.median()
        mad = (valid - median).abs().median()
        scaled = 1.4826 * mad
        if scaled == 0:
            return values
        low = median - mad_scale * scaled
        high = median + mad_scale * scaled
    elif method == "quantile":
        low = valid.quantile(lower)
        high = valid.quantile(upper)
    else:
        raise ValueError("method 必须是 quantile 或 mad")
    return values.clip(lower=low, upper=high)


def zscore(series: pd.Series) -> pd.Series:
    """Standardize to mean 0 / std 1. Zero-variance slices return 0."""
    values = pd.to_numeric(series, errors="coerce")
    mean = values.mean(skipna=True)
    std = values.std(skipna=True)
    if pd.isna(std) or std == 0:
        return values.where(values.isna(), 0.0)
    return (values - mean) / std


def rank_normalize(series: pd.Series, feature_range: tuple = (-1.0, 1.0)) -> pd.Series:
    """Map values to their cross-sectional rank scaled into ``feature_range``."""
    values = pd.to_numeric(series, errors="coerce")
    ranks = values.rank(method="average")
    count = ranks.notna().sum()
    if count <= 1:
        return values.where(values.isna(), 0.0)
    # ranks in [1, count] -> [0, 1]
    unit = (ranks - 1) / (count - 1)
    low, high = feature_range
    return unit * (high - low) + low


def neutralize(
    series: pd.Series,
    groups: Optional[pd.Series] = None,
    size: Optional[pd.Series] = None,
) -> pd.Series:
    """Remove industry (group-demean) and size (log-size regression) beta.

    Returns residuals aligned to ``series.index``. ``groups`` demeans within
    each industry bucket; ``size`` regresses the (already group-demeaned)
    factor on ``log(size)`` and keeps the residual. Rows with non-positive
    size are excluded from the fit and pass through their group-demeaned value.
    """
    result = pd.to_numeric(series, errors="coerce").astype(float)

    if groups is not None:
        group_mean = result.groupby(groups).transform("mean")
        result = result - group_mean

    if size is not None:
        size_values = pd.to_numeric(size, errors="coerce")
        log_size = np.log(size_values.where(size_values > 0))
        fit_mask = result.notna() & log_size.notna()
        if fit_mask.sum() >= 2:
            x = log_size[fit_mask].to_numpy()
            y = result[fit_mask].to_numpy()
            if np.ptp(x) > 0:
                slope, intercept = np.polyfit(x, y, 1)
                predicted = intercept + slope * log_size
                residual = result - predicted
                result = residual.where(fit_mask, result)
    return result


@dataclass
class CrossSectionProcessor:
    """Configurable per-day cross-sectional pipeline for factor columns."""

    winsorize: bool = True
    winsorize_lower: float = 0.01
    winsorize_upper: float = 0.99
    winsorize_method: str = "quantile"
    standardize: str = "zscore"  # "zscore", "rank", or "none"
    neutralize: bool = False
    min_samples: int = 5

    def process(
        self,
        panel: pd.DataFrame,
        factor_cols: list[str],
        industry_col: Optional[str] = None,
        size_col: Optional[str] = "amount",
    ) -> pd.DataFrame:
        """Return ``panel`` with ``factor_cols`` replaced by processed values.

        Processing is per ``trade_date``: winsorize -> (optional) neutralize
        -> standardize. Non-factor columns are preserved unchanged.
        """
        required = {"trade_date", *factor_cols}
        missing = required - set(panel.columns)
        if missing:
            raise ValueError(f"横截面处理缺少字段: {', '.join(sorted(missing))}")

        if self.neutralize and industry_col is not None and industry_col not in panel.columns:
            warnings.warn(f"行业列 {industry_col} 不存在，跳过行业中性化", stacklevel=2)
            industry_col = None
        if self.neutralize and size_col is not None and size_col not in panel.columns:
            warnings.warn(f"市值代理列 {size_col} 不存在，跳过市值中性化", stacklevel=2)
            size_col = None

        result = panel.copy()
        for factor in factor_cols:
            result[factor] = pd.to_numeric(result[factor], errors="coerce")

        processed_parts = []
        for _, day in result.groupby("trade_date", sort=False):
            processed_parts.append(
                self._process_day(day, factor_cols, industry_col, size_col)
            )
        if not processed_parts:
            return result
        return pd.concat(processed_parts).sort_index()

    def _process_day(
        self,
        day: pd.DataFrame,
        factor_cols: list[str],
        industry_col: Optional[str],
        size_col: Optional[str],
    ) -> pd.DataFrame:
        out = day.copy()
        groups = day[industry_col] if (self.neutralize and industry_col) else None
        size = day[size_col] if (self.neutralize and size_col) else None

        for factor in factor_cols:
            series = out[factor]
            valid_count = series.notna().sum()
            if valid_count < self.min_samples:
                out[factor] = np.nan
                continue
            if self.winsorize:
                series = winsorize(
                    series,
                    lower=self.winsorize_lower,
                    upper=self.winsorize_upper,
                    method=self.winsorize_method,
                )
            if self.neutralize and (groups is not None or size is not None):
                series = neutralize(series, groups=groups, size=size)
            out[factor] = self._standardize(series)
        return out

    def _standardize(self, series: pd.Series) -> pd.Series:
        if self.standardize == "zscore":
            return zscore(series)
        if self.standardize == "rank":
            return rank_normalize(series)
        if self.standardize == "none":
            return pd.to_numeric(series, errors="coerce")
        raise ValueError("standardize 必须是 zscore、rank 或 none")
