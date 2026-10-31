from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field

from app.models.base import AuditMixin, utcnow


class AuthProvider(str, Enum):
    CREDENTIALS = "credentials"
    GITHUB = "github"


class User(Document, AuditMixin):
    email: Indexed(EmailStr, unique=True)
    name: str
    password_hash: Optional[str] = None
    auth_provider: AuthProvider = AuthProvider.CREDENTIALS
    github_id: Optional[str] = None
    avatar: Optional[str] = None
    skills: List[str] = Field(default_factory=list)

    class Settings:
        name = "users"
