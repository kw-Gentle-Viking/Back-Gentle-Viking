# app/strategy_factory.py
from backtest.strategies.ultra_safe import UltraSafeStrategy
from backtest.strategies.conservative import ConservativeStrategy
from backtest.strategies.balanced import BalancedStrategy
from backtest.strategies.aggressive import AggressiveStrategy

STRATEGY_CONFIG = {
    "ultra_safe": {
        "class": UltraSafeStrategy,
        "timeframe": "5m",
        "warmup": lambda p: 240,  # 1시간봉 20개 = 5분봉 240개
    },
    "conservative": {
        "class": ConservativeStrategy,
        "timeframe": "5m",
        "warmup": lambda p: 63,   # 15분봉 21개 = 5분봉 63개
    },
    "balanced": {
        "class": BalancedStrategy,
        "timeframe": "5m",
        "warmup": lambda p: 81,   # 15분봉 27개 = 5분봉 81개
    },
    "aggressive": {
        "class": AggressiveStrategy,
        "timeframe": "5m",
        "warmup": lambda p: 21,   # 5분봉 21개만
    },
}


def _get_strategy_config(strategy_id: str):
    return STRATEGY_CONFIG.get(strategy_id) or STRATEGY_CONFIG["conservative"]


def create_strategy(symbol: str, strategy_id: str, params: dict = None):
    cfg = _get_strategy_config(strategy_id)
    return cfg["class"](symbol=symbol)


def get_warmup_count(strategy_id: str, params: dict = None) -> int:
    cfg = _get_strategy_config(strategy_id)
    return cfg["warmup"](params or {})


def get_timeframe(strategy_id: str) -> str:
    cfg = _get_strategy_config(strategy_id)
    return cfg["timeframe"]

## multiframe 전략으로 진화 시킬 것 