from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import AuthProvider, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar=user.avatar,
        skills=user.skills,
        auth_provider=user.auth_provider.value,
        created_at=user.created_at,
    )


class AuthService:
    async def register(self, data: RegisterRequest) -> TokenResponse:
        existing = await User.find_one(User.email == data.email, User.deleted_at == None)
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
        user = User(
            email=data.email,
            name=data.name,
            password_hash=hash_password(data.password),
            auth_provider=AuthProvider.CREDENTIALS,
        )
        await user.insert()
        return await self._issue_tokens(user)

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await User.find_one(User.email == data.email, User.deleted_at == None)
        if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return await self._issue_tokens(user)

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(str(user.id), {"email": user.email})
        refresh = create_refresh_token(str(user.id))
        try:
            redis = get_redis()
            payload = decode_refresh_token(refresh)
            jti = payload.get("jti") if payload else None
            if jti:
                await redis.setex(f"refresh:{jti}", 7 * 86400, str(user.id))
        except RuntimeError:
            pass
        return TokenResponse(access_token=access, refresh_token=refresh)

    async def logout(self, refresh_token: Optional[str]) -> None:
        if not refresh_token:
            return
        payload = decode_refresh_token(refresh_token)
        if payload and payload.get("jti"):
            await get_redis().delete(f"refresh:{payload['jti']}")

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_refresh_token(refresh_token)
        if not payload or not payload.get("sub") or not payload.get("jti"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        redis = get_redis()
        stored = await redis.get(f"refresh:{payload['jti']}")
        if not stored or stored != payload["sub"]:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
        user = await User.get(PydanticObjectId(payload["sub"]))
        if not user or user.deleted_at:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found")
        await redis.delete(f"refresh:{payload['jti']}")
        return await self._issue_tokens(user)

    async def me(self, user: User) -> UserResponse:
        return _user_response(user)


auth_service = AuthService()
