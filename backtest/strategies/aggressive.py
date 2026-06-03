# backtest/strategies/aggressive.py
from typing import List
import pandas as pd
from backtest.engine.risk import Order, OrderType, Side, Portfolio


class AggressiveStrategy:
    """공격형 — 5분봉 모멘텀 돌파 + 거래량 급증
    
    - 5분봉 신고가 돌파 + 거래량 2배 + 골든크로스
    - 상위 타임프레임 안 봄 (속도 우선)
    - 물타기 허용
    """

    POSITION_SIZE = 0.15
    STOP_LOSS = -0.07

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._prices = []
        self._volumes = []

    def _sma(self, data: list, period: int) -> float:
        if len(data) < period:
            return None
        return sum(data[-period:]) / period

    def _rsi(self, period: int = 9) -> float:
        if len(self._prices) < period + 1:
            return 50.0
        changes = [self._prices[-i] - self._prices[-i-1] for i in range(1, period + 1)]
        gains = [c for c in changes if c > 0]
        losses = [-c for c in changes if c < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def generate_orders(self, row: pd.Series, portfolio: Portfolio) -> List[Order]:
        close = float(row["close"])
        volume = int(row.get("volume", 0))
        self._prices.append(close)
        self._volumes.append(volume)

        orders = []
        if len(self._prices) < 21:
            return orders

        rsi = self._rsi(9)
        ma5 = self._sma(self._prices, 5)
        ma10 = self._sma(self._prices, 10)
        vol_avg = self._sma(self._volumes, 20)
        vol_ratio = volume / vol_avg if vol_avg and vol_avg > 0 else 1.0
        recent_high = max(self._prices[-20:])

        pos = portfolio.positions.get(self.symbol)
        current_qty = pos.qty if pos else 0

        # 매수: 신고가 + 거래량 2배 + 골든크로스
        if (close >= recent_high and vol_ratio >= 2.0 and
                ma5 > ma10 and current_qty <= 0):
            qty = portfolio.equity * self.POSITION_SIZE / close
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.BUY, qty=qty, order_type=OrderType.MARKET
            ))

        # 추가 매수: 보유 중 + RSI < 40 + 거래량 1.5배
        elif rsi < 40 and current_qty > 0 and vol_ratio >= 1.5:
            qty = portfolio.equity * 0.05 / close
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.BUY, qty=qty, order_type=OrderType.MARKET
            ))

        # 매도: 데드크로스 OR RSI > 80
        elif (ma5 < ma10 or rsi > 80) and current_qty > 0:
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.SELL, qty=current_qty, order_type=OrderType.MARKET
            ))

        # 손절: -7%
        elif current_qty > 0 and pos:
            pnl = (close - pos.entry_price) / pos.entry_price
            if pnl <= self.STOP_LOSS:
                orders.append(Order(
                    ts=row.name, symbol=self.symbol,
                    side=Side.SELL, qty=current_qty, order_type=OrderType.MARKET
                ))

        return orders