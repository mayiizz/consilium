from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class DocumentResponse(ORMBase):
    id: str
    workspace_id: str
    name: str
    type: str
    file_size: int
    mime_type: str
    uploaded_by: str
    created_at: datetime
    updated_at: datetime
    has_text: bool = False


class DocumentPreviewResponse(BaseModel):
    id: str
    name: str
    type: str
    mime_type: str
    text: str = ""
