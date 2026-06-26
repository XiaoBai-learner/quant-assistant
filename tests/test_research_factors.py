import pandas as pd
from quant_assistant.research.factors import FactorCalculator, FactorDefinition


def make_panel():
    dates = pd.date_range("2024-01-01", periods=70, freq="B")
    rows = []
    for symbol, base in [("000001", 10), ("600000", 20)]:
        for i, trade_date in enumerate(dates):
            close = base + i
            rows.append({
                "symbol": symbol,
                "trade_date": trade_date,
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 1000 + i,
                "amount": (1000 + i) * close,
            })
    return pd.DataFrame(rows)


def test_factor_calculator_computes_builtin_factors_without_future_data():
    calculator = FactorCalculator()
    factors = calculator.calculate(make_panel(), ["momentum_20", "volatility_20"])

    latest = factors[factors["trade_date"] == factors["trade_date"].max()]

    assert set(latest["symbol"]) == {"000001", "600000"}
    assert "momentum_20" in latest.columns
    assert "volatility_20" in latest.columns
    assert latest["momentum_20"].notna().all()


def test_factor_calculator_accepts_user_defined_factor_function():
    def close_to_open(df):
        return df["close"] / df["open"] - 1

    calculator = FactorCalculator()
    calculator.register_factor(FactorDefinition(
        name="close_to_open",
        direction="positive",
        min_periods=1,
        dependencies=["close", "open"],
        compute=close_to_open,
    ))

    factors = calculator.calculate(make_panel(), ["close_to_open"])

    assert "close_to_open" in factors.columns
    assert factors["close_to_open"].notna().all()
