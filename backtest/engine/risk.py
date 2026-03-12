from __future__ import annotations
from collections import deque
from typing import Dict, Optional
import dataclasses as dc
import enum
import pandas as pd


class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class Side(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


@dc.dataclass
class Order:
    ts: pd.Timestamp  # 체결시간
    symbol: str
    side: Side
    qty: int  # 소수점 거래 못하게
    order_type: OrderType
    limit_price: Optional[int] = None
    id: Optional[int] = None


@dc.dataclass
class Fill:
    ts: pd.Timestamp
    order_id: int
    symbol: str
    side: Side
    qty: int
    price: int
    fee: int
    is_maker: bool


@dc.dataclass
class Position:
    symbol: str
    qty: int = 0
    entry_price: int = 0


@dc.dataclass
class Portfolio:
    cash: int = 0
    equity: int = 0
    positions: Dict[str, Position] = dc.field(default_factory=dict)

    def ensure_pos(self, symbol: str) -> Position:
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        return self.positions[symbol]


@dc.dataclass
class RiskLimits:
    max_gross_exposure: float = 2.0
    max_symbol_weight: float = 1.0
    intraday_dd_limit: float = 0.08
    cool_down_minutes: int = 5
    per_order_notional_cap: float = 0.3


class RiskManager:
    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self._halt_until: Optional[pd.Timestamp] = None
        self._equity_history = deque()

    def is_halted(self, ts: pd.Timestamp) -> bool:
        return self._halt_until is not None and ts < self._halt_until

    def _halt(self, ts: pd.Timestamp):
        self._halt_until = ts + pd.Timedelta(minutes=self.limits.cool_down_minutes)

    def check_pretrade(
        self, ts: pd.Timestamp, portfolio: Portfolio, symbol: str, order_notional: float
    ) -> bool:
        if self.is_halted(ts):
            return False

        total_pos_notional = sum(
            abs(p.qty) * (p.entry_price or 0.0) for p in portfolio.positions.values()
        )

        gross = total_pos_notional / max(portfolio.equity, 1e-9)
        if gross > self.limits.max_gross_exposure:
            return False

        if order_notional > self.limits.per_order_notional_cap * portfolio.equity:
            return False

        sym_pos = portfolio.positions.get(symbol, Position(symbol))
        sym_exp = abs(sym_pos.qty) * (sym_pos.entry_price or 0.0)

        if sym_exp + order_notional > self.limits.max_symbol_weight * portfolio.equity:
            return False

        return True

    def check_intraday_dd(self, ts: pd.Timestamp, equity: float):
        if equity > 1e12:
            equity = 1e12

        if not isinstance(ts, pd.Timestamp):
            try:
                ts = pd.Timestamp(ts)
            except Exception:
                ts = pd.Timestamp(ts, unit="ms")

        lookback = pd.Timedelta(hours=24)
        self._equity_history.append((ts, equity))

        while self._equity_history and ts - self._equity_history[0][0] > lookback:
            self._equity_history.popleft()

        max_equity = max(eq for _, eq in self._equity_history)

        if equity < (1 - self.limits.intraday_dd_limit) * max_equity:
            self._halt(ts)
