from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId

from app.models.base import AuditMixin


class DocumentType(str, Enum):
    REQUIREMENTS = "requirements"
    USER_STORY = "user_story"
    ARCHITECTURE = "architecture"
    RESEARCH = "research"
    OTHER = "other"


class ProjectDocument(Document, AuditMixin):
    workspace_id: PydanticObjectId
    name: str
    type: DocumentType = DocumentType.OTHER
    file_id: str
    file_size: int
    mime_type: str
    extracted_text: Optional[str] = None
    uploaded_by: PydanticObjectId

    class Settings:
        name = "documents"
