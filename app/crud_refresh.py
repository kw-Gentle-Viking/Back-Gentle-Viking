from sqlalchemy.orm import Session
from sqlalchemy import select

from datetime import datetime, timezone
from app.models import RefreshToken

from typing import Optional

def create_refresh_token(
    db: Session,
    user_id: int,
    jti: str,
    family_id: str,
    token_hash: str,
    expires_at,
    #user_agent: str | None = None,
    #ip: str | None = None,
) -> RefreshToken:
    obj = RefreshToken(
        user_id=user_id,
        jti=jti,
        family_id=family_id,
        token_hash=token_hash,
        expires_at=expires_at,
        #user_agent=user_agent,
        #ip=ip,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def find_by_hash(db: Session, token_hash: str) -> Optional[RefreshToken] :
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    return db.execute(stmt).scalars().first()

def revoke_token(db: Session, token: RefreshToken):
    token.revoked_at = datetime.now(timezone.utc)
    db.commit()

def revoke_family(db: Session, family_id: str):
    now = datetime.now(timezone.utc)
    stmt = select(RefreshToken).where(RefreshToken.family_id == family_id).where(RefreshToken.revoked_at.is_(None))
    for t in db.execute(stmt).scalars().all():
        t.revoked_at = now
    db.commit()
