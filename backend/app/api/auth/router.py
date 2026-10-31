from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest) -> TokenResponse:
    return await auth_service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest) -> TokenResponse:
    return await auth_service.login(data)


@router.post("/logout", response_model=MessageResponse)
async def logout(data: RefreshRequest) -> MessageResponse:
    await auth_service.logout(data.refresh_token)
    return MessageResponse(message="Logged out")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest) -> TokenResponse:
    return await auth_service.refresh(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return await auth_service.me(user)
