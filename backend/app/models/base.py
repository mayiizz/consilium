from datetime import datetime, timezone
from typing import Optional

from pydantic import Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditMixin:
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    created_by: Optional[str] = None
    deleted_at: Optional[datetime] = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = utcnow()
        self.updated_at = utcnow()
