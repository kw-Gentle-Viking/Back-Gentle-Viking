# app/candle_aggregator.py
from datetime import datetime, timedelta
from collections import defaultdict


class CandleAggregator:
    """실시간 체결가 → 1분봉 → 5분봉 집계"""

    def __init__(self):
        # 1분봉 버퍼
        self.min1_buffer: dict[str, dict] = {}  # ticker -> 현재 1분봉
        self.min1_history: dict[str, list] = defaultdict(list)  # ticker -> 1분봉 리스트

        # 5분봉
        self.min5_buffer: dict[str, list] = defaultdict(list)  # ticker -> 1분봉 5개 모음
        self.min5_history: dict[str, list] = defaultdict(list)  # ticker -> 완성된 5분봉 리스트

    def _get_min1_slot(self, dt: datetime) -> datetime:
        """현재 시각의 1분봉 슬롯"""
        return dt.replace(second=0, microsecond=0)

    def _get_min5_slot(self, dt: datetime) -> datetime:
        """현재 시각의 5분봉 슬롯"""
        minute = (dt.minute // 5) * 5
        return dt.replace(minute=minute, second=0, microsecond=0)

    def on_tick(self, ticker: str, price: int, volume: int) -> dict:
        """
        체결가 수신 시 호출
        Returns: {"min1": 완성된 1분봉 or None, "min5": 완성된 5분봉 or None}
        """
        now = datetime.now()
        slot = self._get_min1_slot(now)
        result = {"min1": None, "min5": None}

        current = self.min1_buffer.get(ticker)

        # 새 1분봉 슬롯이면 기존 봉 완성
        if current and current["slot"] != slot:
            completed = {
                "open": current["open"],
                "high": current["high"],
                "low": current["low"],
                "close": current["close"],
                "volume": current["volume"],
                "datetime": current["slot"],
            }
            self.min1_history[ticker].append(completed)
            result["min1"] = completed

            # 5분봉 집계
            result["min5"] = self._aggregate_5min(ticker, completed)

            # 새 1분봉 시작
            self.min1_buffer[ticker] = {
                "slot": slot,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
        elif not current:
            # 첫 데이터
            self.min1_buffer[ticker] = {
                "slot": slot,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
        else:
            # 기존 1분봉 업데이트
            current["high"] = max(current["high"], price)
            current["low"] = min(current["low"], price)
            current["close"] = price
            current["volume"] += volume

        return result

    def _aggregate_5min(self, ticker: str, min1_candle: dict) -> dict:
        """1분봉 → 5분봉 합산"""
        self.min5_buffer[ticker].append(min1_candle)

        # 5개 모이면 5분봉 완성
        if len(self.min5_buffer[ticker]) >= 5:
            candles = self.min5_buffer[ticker]
            min5 = {
                "open": candles[0]["open"],
                "high": max(c["high"] for c in candles),
                "low": min(c["low"] for c in candles),
                "close": candles[-1]["close"],
                "volume": sum(c["volume"] for c in candles),
                "datetime": candles[0]["datetime"],
            }
            self.min5_history[ticker].append(min5)
            self.min5_buffer[ticker] = []  # 버퍼 초기화
            return min5

        return None