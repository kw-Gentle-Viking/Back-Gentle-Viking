# backtest/strategies/balanced.py
from typing import List
import pandas as pd
from backtest.engine.risk import Order, OrderType, Side, Portfolio


class BalancedStrategy:
    """중립형 — 15분봉 MACD 추세 + 5분봉 RSI 진입
    
    - 15분봉 MACD > 0 (상승 모멘텀 확인)
    - 5분봉 RSI < 45 (과매수 아님)
    """

    POSITION_SIZE = 0.10
    STOP_LOSS = -0.05

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._prices_5m = []
        self._prices_15m = []
        self._buffer_15m = []

    def _ema(self, data: list, period: int) -> float:
        if len(data) < period:
            return None
        k = 2 / (period + 1)
        ema = data[-period]
        for p in data[-period+1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def _macd(self, data: list) -> float:
        ema12 = self._ema(data, 12)
        ema26 = self._ema(data, 26)
        if ema12 is None or ema26 is None:
            return None
        return ema12 - ema26

    def _rsi(self, data: list, period: int = 14) -> float:
        if len(data) < period + 1:
            return 50.0
        changes = [data[-i] - data[-i-1] for i in range(1, period + 1)]
        gains = [c for c in changes if c > 0]
        losses = [-c for c in changes if c < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _aggregate(self, close: float, buffer: list, history: list, n: int):
        buffer.append(close)
        if len(buffer) >= n:
            history.append(sum(buffer) / len(buffer))
            buffer.clear()

    def generate_orders(self, row: pd.Series, portfolio: Portfolio) -> List[Order]:
        close = float(row["close"])
        self._prices_5m.append(close)
        self._aggregate(close, self._buffer_15m, self._prices_15m, 3)

        orders = []
        if len(self._prices_15m) < 27:
            return orders

        # 15분봉: MACD
        macd_15m = self._macd(self._prices_15m)

        # 5분봉: RSI
        rsi_5m = self._rsi(self._prices_5m, 14)

        pos = portfolio.positions.get(self.symbol)
        current_qty = pos.qty if pos else 0

        # 매수: 15분 MACD > 0 + 5분 RSI < 45
        if macd_15m and macd_15m > 0 and rsi_5m < 45 and current_qty <= 0:
            qty = portfolio.equity * self.POSITION_SIZE / close
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.BUY, qty=qty, order_type=OrderType.MARKET
            ))

        # 매도: 15분 MACD < 0 OR 5분 RSI > 70
        elif ((macd_15m and macd_15m < 0) or rsi_5m > 70) and current_qty > 0:
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.SELL, qty=current_qty, order_type=OrderType.MARKET
            ))

        # 손절: -5%
        elif current_qty > 0 and pos:
            pnl = (close - pos.entry_price) / pos.entry_price
            if pnl <= self.STOP_LOSS:
                orders.append(Order(
                    ts=row.name, symbol=self.symbol,
                    side=Side.SELL, qty=current_qty, order_type=OrderType.MARKET
                ))

        return orders