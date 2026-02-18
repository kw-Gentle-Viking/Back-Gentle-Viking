from typing import List
import pandas as pd

from backtest.engine.risk import Order, OrderType, Side, Portfolio


class RSIReversalStrategy:
    """RSI 반전 전략"""
    
    def __init__(
        self, 
        symbol: str, 
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0
    ):
        self.symbol = symbol
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        #self.sr = None
        
        # 내부 상태
        self._prices = []
        self._gains = []
        self._losses = []
    
    def _calc_rsi(self) -> float:
        """RSI 계산"""
        if len(self._prices) < self.period + 1:
            return 50.0  # 중립
        
        # 최근 변화량
        changes = []
        for i in range(1, min(len(self._prices), self.period + 1)):
            changes.append(self._prices[-i] - self._prices[-i-1])
        
        gains = [c for c in changes if c > 0]
        losses = [-c for c in changes if c < 0]
        
        avg_gain = sum(gains) / self.period if gains else 0
        avg_loss = sum(losses) / self.period if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def generate_orders(self, row: pd.Series, portfolio: Portfolio) -> List[Order]:
        """주문 생성"""
        orders = []
        
        close = float(row["close"])
        self._prices.append(close)
        
        # 충분한 데이터가 없으면 패스
        if len(self._prices) < self.period + 1:
            return orders
        
        rsi = self._calc_rsi()
        
        # 현재 포지션
        pos = portfolio.positions.get(self.symbol)
        current_qty = pos.qty if pos else 0
        
        # 포지션 크기
        position_size = portfolio.equity * 0.1 / close
        
        # 과매도 -> 매수
        if rsi < self.oversold and current_qty <= 0:
            if current_qty < 0:
                orders.append(Order(
                    ts=row.name,
                    symbol=self.symbol,
                    side=Side.BUY,
                    qty=abs(current_qty),
                    order_type=OrderType.MARKET
                ))
            orders.append(Order(
                ts=row.name,
                symbol=self.symbol,
                side=Side.BUY,
                qty=position_size,
                order_type=OrderType.MARKET
            ))
        
        # 과매수 -> 매도
        elif rsi > self.overbought and current_qty >= 0:
            if current_qty > 0:
                orders.append(Order(
                    ts=row.name,
                    symbol=self.symbol,
                    side=Side.SELL,
                    qty=current_qty,
                    order_type=OrderType.MARKET
                ))
            orders.append(Order(
                ts=row.name,
                symbol=self.symbol,
                side=Side.SELL,
                qty=position_size,
                order_type=OrderType.MARKET
            ))
        
        return orders
