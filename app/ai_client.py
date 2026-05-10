# ai_client.py (더미)
import random

class AIClient:
    """AI 서버 클라이언트 (더미 구현)"""
    
    # TODO: 실제 AI 서버 연동 시 교체
    def predict(self, ticker: str) -> dict:
        """
        Returns:
            {
                "ticker": "005930",
                "signal": "BUY",       # BUY | HOLD | SELL
                "confidence": 0.82,     # 0.0 ~ 1.0
            }
        """
        signal = random.choice(["BUY", "HOLD", "SELL"])
        confidence = round(random.uniform(0.5, 0.95), 2)
        
        return {
            "ticker": ticker,
            "signal": signal,
            "confidence": confidence,
        }