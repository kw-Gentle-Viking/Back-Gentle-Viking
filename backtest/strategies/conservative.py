# backtest/strategies/conservative.py
from typing import List
import pandas as pd
from backtest.engine.risk import Order, OrderType, Side, Portfolio


class ConservativeStrategy:
    """안전형 — 15분봉 추세 + 5분봉 RSI 진입
    
    - 15분봉 MA20 위에서만 매수 (추세 확인)
    - 5분봉 RSI 과매도 시 진입
    """

    POSITION_SIZE = 0.08
    STOP_LOSS = -0.03

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._prices_5m = []
        self._prices_15m = []
        self._buffer_15m = []

    def _sma(self, data: list, period: int) -> float:
        if len(data) < period:
            return None
        return sum(data[-period:]) / period

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
        if len(self._prices_15m) < 21:
            return orders

        # 15분봉: MA20 추세
        ma20_15m = self._sma(self._prices_15m, 20)
        trend_up = close > ma20_15m if ma20_15m else False

        # 5분봉: RSI
        rsi_5m = self._rsi(self._prices_5m, 14)

        pos = portfolio.positions.get(self.symbol)
        current_qty = pos.qty if pos else 0

        # 매수: 15분 MA20 위 + 5분 RSI < 30
        if trend_up and rsi_5m < 30 and current_qty <= 0:
            qty = portfolio.equity * self.POSITION_SIZE / close
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.BUY, qty=qty, order_type=OrderType.MARKET
            ))

        # 매도: 5분 RSI > 70 OR 15분 MA20 아래로 이탈
        elif (rsi_5m > 70 or not trend_up) and current_qty > 0:
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.SELL, qty=current_qty, order_type=OrderType.MARKET
            ))

        # 손절: -3%
        elif current_qty > 0 and pos:
            pnl = (close - pos.entry_price) / pos.entry_price
            if pnl <= self.STOP_LOSS:
                orders.append(Order(
                    ts=row.name, symbol=self.symbol,
                    side=Side.SELL, qty=current_qty, order_type=OrderType.MARKET
                ))

        return orders
    