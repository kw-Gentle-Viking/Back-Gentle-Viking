from typing import List
import pandas as pd

from backtest.engine.risk import Order, OrderType, Side, Portfolio


class MACrossStrategy:
    """이동평균 크로스 전략"""

    def __init__(self, symbol: str, fast_period: int = 10, slow_period: int = 30):
        self.symbol = symbol
        self.fast_period = fast_period
        self.slow_period = slow_period
        # self.sr = None  # Support/Resistance detector (optional)

        # 내부 상태
        self._prices = []
        self._position = 0

    def generate_orders(self, row: pd.Series, portfolio: Portfolio) -> List[Order]:
        """주문 생성"""
        orders = []

        close = float(row["close"])
        self._prices.append(close)

        # 충분한 데이터가 없으면 패스
        if len(self._prices) < self.slow_period:
            return orders

        # 이동평균 계산
        fast_ma = sum(self._prices[-self.fast_period :]) / self.fast_period
        slow_ma = sum(self._prices[-self.slow_period :]) / self.slow_period

        # 현재 포지션
        pos = portfolio.positions.get(self.symbol)
        current_qty = pos.qty if pos else 0

        # 포지션 크기 계산 (자본의 10%)
        position_size = int(portfolio.equity * 0.1 / close)  # 주식이니깐 int

        # 골든 크로스 (매수 신호)
        if fast_ma > slow_ma and current_qty <= 0:
            # 숏 청산 + 롱 진입
            if current_qty < 0:
                orders.append(
                    Order(
                        ts=row.name,
                        symbol=self.symbol,
                        side=Side.BUY,
                        qty=abs(current_qty),
                        order_type=OrderType.MARKET,
                    )
                )
            orders.append(
                Order(
                    ts=row.name,
                    symbol=self.symbol,
                    side=Side.BUY,
                    qty=position_size,
                    order_type=OrderType.MARKET,
                )
            )

        # 데드 크로스 (매도 신호)
        elif fast_ma < slow_ma and current_qty >= 0:
            # 롱 청산 + 숏 진입
            if current_qty > 0:
                orders.append(
                    Order(
                        ts=row.name,
                        symbol=self.symbol,
                        side=Side.SELL,
                        qty=current_qty,
                        order_type=OrderType.MARKET,
                    )
                )
            orders.append(
                Order(
                    ts=row.name,
                    symbol=self.symbol,
                    side=Side.SELL,
                    qty=position_size,
                    order_type=OrderType.MARKET,
                )
            )

        return orders
