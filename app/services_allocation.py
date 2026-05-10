# app/services_allocation.py

def allocate_portfolio(
    predictions: list[dict],
    persona_id: int,
    total_capital: int,
    max_weight: float = 0.30,  # 한 종목 최대 30%
    cash_reserve: float = 0.10,  # 현금 보유 10%
) -> list[dict]:
    """
    predictions: [{"ticker": "005930", "signal": "BUY", "confidence": 0.85}, ...]
    """

    # 1. BUY 시그널만 필터
    buys = [p for p in predictions if p["signal"] == "BUY" and p["confidence"] >= 0.6]

    if not buys:
        return []

    # 2. 페르소나별 confidence 보정
    PERSONA_MULTIPLIER = {
        1: {"large_cap": 1.3, "default": 0.7},   # 안정형: 대형주 선호
        2: {"large_cap": 1.2, "default": 0.8},   # 안정추구형
        3: {"large_cap": 1.0, "default": 1.0},   # 위험중립형: 보정 없음
        4: {"large_cap": 0.8, "default": 1.2},   # 적극투자형: 중소형 선호
        5: {"large_cap": 0.7, "default": 1.3},   # 공격투자형: 테마주 선호
    }
    multiplier = PERSONA_MULTIPLIER.get(persona_id, PERSONA_MULTIPLIER[3])

    for b in buys:
        # TODO: 실제로는 ticker로 대형주 여부 판단 (시가총액 기준)
        cap_type = b.get("cap_type", "default")
        b["adj_confidence"] = b["confidence"] * multiplier.get(cap_type, 1.0)

    # 3. 가중 분배 (보정된 confidence 기준)
    total_conf = sum(b["adj_confidence"] for b in buys)
    investable = total_capital * (1 - cash_reserve)

    for b in buys:
        raw_weight = b["adj_confidence"] / total_conf

        # 4. 최대 비중 제한
        b["weight"] = min(raw_weight, max_weight)

    # 비중 재정규화 (max_weight로 잘린 만큼 재분배)
    total_weight = sum(b["weight"] for b in buys)
    for b in buys:
        b["weight"] = b["weight"] / total_weight

    # 5. 실제 금액/수량 계산
    result = []
    for b in buys:
        amount = int(investable * b["weight"])
        result.append({
            "ticker": b["ticker"],
            "signal": b["signal"],
            "confidence": b["confidence"],
            "adj_confidence": round(b["adj_confidence"], 3),
            "weight": round(b["weight"], 3),
            "amount": amount,
            # TODO: 현재가로 나눠서 수량 계산
            # "qty": amount // current_price,
        })

    return result