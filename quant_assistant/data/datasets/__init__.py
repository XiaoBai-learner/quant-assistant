"""Normalized dataset facades built on top of providers."""

from quant_assistant.data.datasets.market import MarketDataset
from quant_assistant.data.datasets.signals import SignalDataset

__all__ = [
    "MarketDataset",
    "SignalDataset",
]
