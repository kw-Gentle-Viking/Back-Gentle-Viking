# app/ai_client.py
import random
from app.routes_ai_webhook import realtime_predictions, SIGNAL_MAP


class AIClient:
    """AI 서버 클라이언트"""

    def predict(self, ticker: str) -> dict:
        """
        실시간 추론 결과가 있으면 사용, 없으면 더미
        """
        # AI 서버에서 push된 결과가 있으면 사용
        pred = realtime_predictions.get(ticker)
        if pred:
            return {
                "ticker": pred["ticker"],
                "signal": pred["signal"],
                "confidence": pred["confidence"],
            }

        # 더미 (AI 서버 미연결 시)
        signal = random.choice(["BUY", "HOLD", "SELL"])
        confidence = round(random.uniform(0.5, 0.95), 2)
        return {
            "ticker": ticker,
            "signal": signal,
            "confidence": confidence,
        }