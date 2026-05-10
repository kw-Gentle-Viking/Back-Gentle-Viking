# app/strategy_factory.py
from backtest.strategies.rsi_reversal import RSIReversalStrategy
from backtest.strategies.ma_cross import MACrossStrategy


STRATEGY_DEFAULTS = {
    "rsi_reversal": {"period": 14, "oversold": 30.0, "overbought": 70.0},
    "ma_cross": {"fast_period": 5, "slow_period": 20},
}


def create_strategy(symbol: str, strategy_id: str, params: dict = None):
    """전략 인스턴스 생성"""
    defaults = STRATEGY_DEFAULTS.get(strategy_id, {})
    merged = {**defaults, **(params or {})}

    if strategy_id == "rsi_reversal":
        return RSIReversalStrategy(
            symbol=symbol,
            period=merged["period"],
            oversold=merged["oversold"],
            overbought=merged["overbought"],
        )
    elif strategy_id == "ma_cross":
        return MACrossStrategy(
            symbol=symbol,
            fast_period=merged["fast_period"],
            slow_period=merged["slow_period"],
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy_id}")