import os
import httpx
from fastapi import HTTPException

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

async def verify_google_id_token(id_token : str) -> dict:

    # Google이 제공하는 검증 엔드포인트 간단하고 안정적이다
    url = "https://oauth2.googleapis.com/tokeninfo"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url,params={"id_token": id_token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    data = r.json()

    # 우리 app token이 맞는지 검사
    if GOOGLE_CLIENT_ID and data.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code= 401 , detail= "Google token audience mismatch")

    data.get("email_verified") == "true"
    
    return data






