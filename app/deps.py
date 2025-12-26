from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.jwt import decode_token

bearer = HTTPBearer(auto_error=False)

def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    if not creds:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = decode_token(creds.credentials)
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# 