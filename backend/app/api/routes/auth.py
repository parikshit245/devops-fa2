from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import AuthResponse, LoginRequest, RegisterRequest, UserRead

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
def normalized(email: str) -> str: return email.strip().lower()

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    email = normalized(payload.email)
    if await db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password))
    db.add(user); await db.commit(); await db.refresh(user)
    response.set_cookie("access_token", create_access_token(user.id), httponly=True, secure=get_settings().cookie_secure, samesite="lax", max_age=get_settings().jwt_expire_minutes * 60)
    return {"user": user}

@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == normalized(payload.email)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    response.set_cookie("access_token", create_access_token(user.id), httponly=True, secure=get_settings().cookie_secure, samesite="lax", max_age=get_settings().jwt_expire_minutes * 60)
    return {"user": user}

@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(current_user)): return user

@router.post("/logout", status_code=204)
async def logout(response: Response): response.delete_cookie("access_token")
