import os, secrets, hashlib
from datetime import datetime, timedelta, timezone
from jose import jwt


SECRET = os.getenv("JWT_SECRET", "dev-secret")
ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_MIN = int(os.getenv("JWT_ACCESS_EXPIRE_MIN", "30"))
REFRESH_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "14"))
PEPPER = os.getenv("REFRESH_TOKEN_PEPPER", "dev-pepper")



def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,               # 보통 user_id 또는 email
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_MIN)).timestamp()),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET, algorithm=ALG)

def new_refresh_token_pair(user_id: int, family_id: str | None = None) -> dict:
    jti = secrets.token_hex(16)  # 32 chars
    fam = family_id or secrets.token_hex(16)
    raw = secrets.token_urlsafe(48)  # 충분히 길게
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS)
    return {
        "raw": raw,
        "jti": jti,
        "family_id": fam,
        "expires_at": expires_at,
    }

def hash_refresh_token(raw: str) -> str :
    return hashlib.sha256((raw+ PEPPER).encode("utf-8")).hexdigest()

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=[ALG])