import asyncio

# AI 추론 결과 저장
realtime_predictions: dict[str, dict] = {}

# AI push 이벤트
ai_signal_event = asyncio.Event()

# 워밍업 완료 이벤트 및 종목별 수신 상태
warmup_events: dict[int, asyncio.Event] = {}
warmup_requirements: dict[int, dict[str, int]] = {}
warmup_received: dict[int, dict[str, int]] = {}

SIGNAL_MAP = {
    "0": "BUY",
    "1": "HOLD",
    "2": "SELL",
    "BUY": "BUY",
    "HOLD": "HOLD",
    "SELL": "SELL",
    "buy": "BUY",
    "hold": "HOLD",
    "sell": "SELL",
    "매수": "BUY",
    "관망": "HOLD",
    "매도": "SELL",
}
