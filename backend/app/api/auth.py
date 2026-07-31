from fastapi import APIRouter, HTTPException, status #type:ignore
from pydantic import BaseModel

from app.core.security import create_access_token, get_password_hash, verify_password #type:ignore

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Hardcoded demo password hash ("password123") for Phase 2 testing
DEMO_USER_HASH = get_password_hash("password123")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    if credentials.username == "admin" and verify_password(credentials.password, DEMO_USER_HASH):
        access_token = create_access_token(data={"sub": credentials.username})
        return TokenResponse(access_token=access_token)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )