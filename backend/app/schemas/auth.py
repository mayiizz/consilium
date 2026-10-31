from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBase


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(ORMBase):
    id: str
    email: str
    name: str
    avatar: Optional[str] = None
    skills: List[str] = []
    auth_provider: str
    created_at: datetime
