# app/ai_client.py
import os
import random
from app.shared_state import realtime_predictions


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
                "prob_buy": pred.get("prob_buy", 0.0),
                "prob_hold": pred.get("prob_hold", 0.0),
                "prob_sell": pred.get("prob_sell", 0.0),
                "trade_datetime": pred.get("trade_datetime"),
                "model_version": pred.get("model_version"),
            }

        if os.getenv("AI_ALLOW_DUMMY_PREDICTIONS", "false").lower() not in {
            "1",
            "true",
            "yes",
            "y",
        }:
            return {
                "ticker": ticker,
                "signal": "HOLD",
                "confidence": 0.0,
                "prob_buy": 0.0,
                "prob_hold": 1.0,
                "prob_sell": 0.0,
            }

        # 더미 (AI 서버 미연결 시)
        signal = random.choice(["BUY", "HOLD", "SELL"])
        confidence = round(random.uniform(0.5, 0.95), 2)
        return {
            "ticker": ticker,
            "signal": signal,
            "confidence": confidence,
            "prob_buy": confidence if signal == "BUY" else 0.0,
            "prob_hold": confidence if signal == "HOLD" else 0.0,
            "prob_sell": confidence if signal == "SELL" else 0.0,
        }