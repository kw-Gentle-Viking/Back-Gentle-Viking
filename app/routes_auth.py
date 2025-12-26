from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, select
from pydantic import BaseModel, EmailStr

from app.db import get_db
from app.crud_users import get_user_by_email
from app.security import verify_password
from app.jwt import create_access_token, new_refresh_token_pair, hash_refresh_token
from app.google_oauth import verify_google_id_token
from app.models import User
from app.crud_refresh import create_refresh_token, find_by_hash, revoke_token, revoke_family
from app.schemas import TokenPair

from datetime import datetime, timezone

router = APIRouter(prefix="/auth",tags=["auth"])

class LoginReq(BaseModel):
    email: EmailStr
    password: str

class GoogleReq(BaseModel):
    id_token : str

@router.post("/login",response_model=TokenPair)
def login(payload: LoginReq, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(subject=str(user.id), extra={"email": user.email})

    # rt : refresh token bundle (raw token + metadata) 
    # claude에 내가 쓴 code 물어보니깐 refresh_token 써놨더니 혼남 .. raw token과 혼동 가능성
    rt = new_refresh_token_pair(user_id=user.id)
    rt_hash = hash_refresh_token(rt["raw"])

    create_refresh_token(
        db = db,
        user_id=user.id,
        jti = rt["jti"],
        family_id= rt["family_id"],
        token_hash=rt_hash,
        expires_at=rt["expires_at"],
        #user_agent=request.headers.get("user-agent"),
        #ip=request.client.host if request.client else None,
    )

    return TokenPair(access_token=access_token, refresh_token=rt["raw"])


class RefreshReq(BaseModel):
    refresh_token : str

# Refresh 
@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshReq, request: Request, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token) # refresh token hash
    stored = find_by_hash(db, token_hash) # hash 저장된거 찾기?

    # 없는 token이면 탈취/오류 가능성
    if not stored :
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # 만료 check 
    now = datetime.now
    if stored.expires_at <= now:
        revoke_token(db, stored)
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # 이미 revoke 된 token 재사용 -> 재사용 탐지 -> family 전체 revoke
    if stored.revoked_at is not None:
        revoke_family(db, stored.family_id)
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

    # rotate : 기존 토큰 revoke  + 새 token 발급
    new_rt = new_refresh_token_pair(user_id=stored.user_id, family_id=stored.family_id)
    stored.revoked_at = now
    stored.replaced_by_jti = new_rt["jti"]
    db.commit()

    # 새 토큰 저장
    new_rt_hash = hash_refresh_token(new_rt["raw"])

    create_refresh_token(
        db = db,
        user_id= stored.user_id,
        jti = new_rt["jti"],
        family_id=new_rt["family_id"],
        token_hash=new_rt_hash,
        expires_at=new_rt["expires_at"],

    )

    new_access_token = create_access_token(subject=str(stored.user_id))
    return TokenPair(access_token=new_access_token, refresh_token=new_rt["raw"])

#Logout
@router.post("/logout")
def logout(payload: RefreshReq, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = find_by_hash(db, token_hash)
    if stored and stored.revoked_at is None:
        revoke_token(db, stored)
    return {"ok": True}





# -- access_token만 -- 
@router.post("/google")
async def google_login(payload: GoogleReq, db: Session = Depends(get_db)):
    info = await verify_google_id_token(payload.id_token)

    email = info.get("email")
    sub = info.get("sub") # google 고유 id 
    if not email or not sub:
        raise HTTPException(status_code=401, detail="Google token missing fields")


    # 이메일 기준으로 찾고 없으면 생성 
    user = db.execute(select(User).where(User.email == email)).scalars().first()
    # scalars() method는 generator이기 때문에 추가적으로 사용하는 method가 있음

    if not user:
        user = User(
            email = email,
            password_hash = None,
            provider = "google",
            provider_sub = sub,
            emial_verified = (info.get("email_verified") == "true" ),
            name = info.get("name"),
            picture = info.get("picture"), 
        )
        db.add(user) # 추가 
        db.commit() 
        db.refresh(user)   
    else :
        # 기존 유저 update
        user.provider = "google"
        user.provider_sub = sub
        user.email_verified = (info.get("email_verified") == "true")
        user.name = info.get("name") or user.name
        user.picture = info.get("picture") or user.picture
        db.commit()
    
    token = create_access_token(subject= str(user.id), extra= {"email" : user.email})
    return {"access_token" : token, "token_type": "bearer"}




# --access token + refresh toekn 동시 관리
@router.post("/google",response_model=TokenPair)
async def google_login(payload: GoogleReq, db: Session = Depends(get_db)):
    info = await verify_google_id_token(payload.id_token)

    email = info.get("email")
    sub = info.get("sub") # google 고유 id 
    if not email or not sub:
        raise HTTPException(status_code=401, detail="Google token missing fields")


    # 이메일 기준으로 찾고 없으면 생성 
    user = db.execute(select(User).where(User.email == email)).scalars().first()
    # scalars() method는 generator이기 때문에 추가적으로 사용하는 method가 있음
    
    if not user:
        user = User(
            email = email,
            password_hash = None,
            provider = "google",
            provider_sub = sub,
            emial_verified = (info.get("email_verified") == "true" ),
            name = info.get("name"),
            picture = info.get("picture"), 
        )
        db.add(user) # 추가 
        db.commit() 
        db.refresh(user)   
    else :
        # 기존 유저 update
        user.provider = "google"
        user.provider_sub = sub
        user.email_verified = (info.get("email_verified") == "true")
        user.name = info.get("name") or user.name
        user.picture = info.get("picture") or user.picture
        db.commit()
    
    access_token = create_access_token(subject= str(user.id), extra= {"email" : user.email})
    
    rt = new_refresh_token_pair(user_id=user.id) 
    rt_hash = hash_refresh_token(rt["raw"])

    create_refresh_token(
        db= db,
        user_id= user.id,
        jti = rt["jti"],
        family_id= rt["family_id"],
        token_hash=rt_hash,
        expires_at=rt["expires_at"],
    )
    
    
    return TokenPair(access_token=access_token, refresh_token=rt["raw"])




