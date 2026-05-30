# backtest/strategies/ultra_safe.py
from typing import List
import pandas as pd
from backtest.engine.risk import Order, OrderType, Side, Portfolio


class UltraSafeStrategy:
    """매우 안전형 — 1시간봉 추세 + 15분봉 확인 + 5분봉 진입
    
    - 1시간봉 MA20 상승 확인 (큰 추세)
    - 15분봉 RSI 과매도 확인 (중간 타이밍)
    - 5분봉 볼린저밴드 하단 터치 (정밀 진입)
    """

    POSITION_SIZE = 0.05
    STOP_LOSS = -0.02

    def __init__(self, symbol: str):
        self.symbol = symbol
        # 5분봉
        self._prices_5m = []
        self._volumes_5m = []
        self._candle_count = 0
        # 15분봉 (5분봉 3개 합산)
        self._prices_15m = []
        self._buffer_15m = []
        # 1시간봉 (5분봉 12개 합산)
        self._prices_1h = []
        self._buffer_1h = []

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

    def _bollinger(self, data: list, period: int = 20) -> tuple:
        if len(data) < period:
            return None, None, None
        d = data[-period:]
        mid = sum(d) / period
        std = (sum((x - mid) ** 2 for x in d) / period) ** 0.5
        return mid - 2 * std, mid, mid + 2 * std

    def _aggregate(self, close: float, buffer: list, history: list, n: int):
        """5분봉을 상위 타임프레임으로 합산"""
        buffer.append(close)
        if len(buffer) >= n:
            history.append(sum(buffer) / len(buffer))
            buffer.clear()

    def generate_orders(self, row: pd.Series, portfolio: Portfolio) -> List[Order]:
        close = float(row["close"])
        volume = int(row.get("volume", 0))

        self._prices_5m.append(close)
        self._volumes_5m.append(volume)
        self._candle_count += 1

        # 상위 타임프레임 합산
        self._aggregate(close, self._buffer_15m, self._prices_15m, 3)
        self._aggregate(close, self._buffer_1h, self._prices_1h, 12)

        orders = []

        # 최소 데이터: 1시간봉 20개 = 5분봉 240개
        if len(self._prices_1h) < 20:
            return orders

        # 1시간봉: MA20 상승 추세 확인
        ma20_1h = self._sma(self._prices_1h, 20)
        ma5_1h = self._sma(self._prices_1h, 5)
        trend_up = ma5_1h > ma20_1h if ma5_1h and ma20_1h else False

        # 15분봉: RSI 과매도
        rsi_15m = self._rsi(self._prices_15m, 14)

        # 5분봉: 볼린저밴드
        bb_lower, bb_mid, bb_upper = self._bollinger(self._prices_5m, 20)

        pos = portfolio.positions.get(self.symbol)
        current_qty = pos.qty if pos else 0

        # 매수: 1시간 상승추세 + 15분 RSI < 25 + 5분 BB 하단
        if trend_up and rsi_15m < 25 and bb_lower and close <= bb_lower and current_qty <= 0:
            qty = portfolio.equity * self.POSITION_SIZE / close
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.BUY, qty=qty, order_type=OrderType.MARKET
            ))

        # 매도: 5분 BB 상단 돌파 OR 15분 RSI > 65
        elif (bb_upper and close >= bb_upper or rsi_15m > 65) and current_qty > 0:
            orders.append(Order(
                ts=row.name, symbol=self.symbol,
                side=Side.SELL, qty=current_qty, order_type=OrderType.MARKET
            ))

        # 손절: -2%
        elif current_qty > 0 and pos:
            pnl = (close - pos.entry_price) / pos.entry_price
            if pnl <= self.STOP_LOSS:
                orders.append(Order(
                    ts=row.name, symbol=self.symbol,
                    side=Side.SELL, qty=current_qty, order_type=OrderType.MARKET
                ))

        return orders
    




    