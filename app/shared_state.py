import asyncio

# AI 추론 결과 저장
realtime_predictions: dict[str, dict] = {}

# AI push 이벤트
ai_signal_event = asyncio.Event()

# 워밍업 완료 이벤트
warmup_events: dict[int, asyncio.Event] = {}

SIGNAL_MAP = {"매수": "BUY", "관망": "HOLD", "매도": "SELL"}