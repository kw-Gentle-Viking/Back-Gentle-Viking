import os
from datetime import date

from sqlalchemy.orm import Session

from app.models import Persona, User


def demo_mode_enabled() -> bool:
    return os.getenv("LOCAL_DEMO_MODE", "false").lower() in {"1", "true", "yes", "y"}


def demo_autotrade_loop_enabled() -> bool:
    return os.getenv("LOCAL_DEMO_AUTOTRADE_LOOP", "false").lower() in {"1", "true", "yes", "y"}


def ensure_demo_personas(db: Session) -> None:
    personas = [
        (1, "안정형", "원금을 중시하는 보수적인 투자자"),
        (2, "안정추구형", "안정적인 성장을 추구하는 투자자"),
        (3, "위험중립형", "실적과 추세를 균형 있게 보는 투자자"),
        (4, "적극투자형", "주도주와 모멘텀을 선호하는 투자자"),
        (5, "공격투자형", "높은 변동성을 감수하는 공격적인 투자자"),
    ]
    changed = False
    for persona_id, name, gemini_persona in personas:
        if db.get(Persona, persona_id):
            continue
        db.add(
            Persona(
                id=persona_id,
                name=name,
                gemini_persona=gemini_persona,
                criteria="로컬 데모 기본 투자성향입니다.",
                weights={
                    "가치_저평가": 2.0,
                    "실적_펀다맨탈": 5.0,
                    "호재_모맨텀": 3.0,
                    "악재_리스크": -5.0,
                    "섹터_트렌드": 3.0,
                },
                use_value_scout=False,
            )
        )
        changed = True
    if changed:
        db.commit()


def ensure_demo_user(db: Session) -> User:
    ensure_demo_personas(db)
    email = os.getenv("LOCAL_DEMO_USER_EMAIL", "demo@example.com")
    legacy_user = db.query(User).filter(User.provider == "local-demo").first()
    if legacy_user and legacy_user.email != email:
        legacy_user.email = email
        if not legacy_user.nickname:
            legacy_user.nickname = "demo-user"
        db.commit()
        db.refresh(legacy_user)
    user = db.query(User).filter(User.email == email).first()
    if user:
        if user.risk_score is None:
            user.risk_score = 3
            db.commit()
            db.refresh(user)
        return user

    user = User(
        email=email,
        password_hash=None,
        provider="local-demo",
        provider_sub="local-demo",
        email_verified=True,
        name="데모 사용자",
        nickname="demo-user",
        phone="01000000000",
        birth_date=date(1999, 1, 1),
        investment_goal=3,
        investment_period=3,
        risk_tolerance=3,
        investment_experience=3,
        volatility_preference=2,
        risk_score=3,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
