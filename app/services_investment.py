def _score_to_grade(score: float) -> int:
    """100점 만점 점수 → 1~5등급 변환 (금융권 표준)"""
    if score <= 20:
        return 1  # 안정형
    elif score <= 40:
        return 2  # 안정추구형
    elif score <= 60:
        return 3  # 위험중립형
    elif score <= 80:
        return 4  # 적극투자형
    else:
        return 5  # 공격투자형


def calculate_risk_score(
    investment_goal: int,
    investment_period: int,
    risk_tolerance: int,
    investment_experience: int,
    volatility_preference: int,
) -> int:
    """
    항목별 가중치 부여 후 100점 환산 → 1~5등급 반환

    가중치:
    - risk_tolerance     : 30% (손실 감내 = 핵심)
    - volatility_preference: 25% (변동성 선호)
    - investment_goal    : 20% (투자 목적)
    - investment_experience: 15% (경험)
    - investment_period  : 10% (기간)
    """
    goal_score = (investment_goal - 1) / 3 * 100
    period_score = (investment_period - 1) / 3 * 100
    tolerance_score = (risk_tolerance - 1) / 3 * 100
    experience_score = (investment_experience - 1) / 3 * 100
    volatility_score = (volatility_preference - 1) / 2 * 100

    final_score = (
        goal_score * 0.20
        + period_score * 0.10
        + tolerance_score * 0.30
        + experience_score * 0.15
        + volatility_score * 0.25
    )

    # 안전장치: VERY_LOW면 최대 안정추구형(2)으로 제한
    if risk_tolerance == 1:
        return min(2, _score_to_grade(final_score))

    return _score_to_grade(final_score)
