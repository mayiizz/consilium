import io
from datetime import datetime, timezone
from typing import List

from beanie import PydanticObjectId
from fastapi import HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.core.database import get_db
from app.models.document import DocumentType, ProjectDocument
from app.schemas import DocumentResponse
from app.schemas.document import DocumentPreviewResponse
from app.services.permissions import require_workspace_lead, require_workspace_member


def _doc_response(doc: ProjectDocument) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        workspace_id=str(doc.workspace_id),
        name=doc.name,
        type=doc.type.value,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        uploaded_by=str(doc.uploaded_by),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        has_text=bool((doc.extracted_text or "").strip()),
    )


class DocumentService:
    async def upload(
        self,
        workspace_id: str,
        user_id: PydanticObjectId,
        file: UploadFile,
        doc_type: str = "other",
    ) -> DocumentResponse:
        await require_workspace_member(workspace_id, user_id)
        content = await file.read()
        db = get_db()
        bucket = AsyncIOMotorGridFSBucket(db)
        file_id = await bucket.upload_from_stream(
            file.filename or "document",
            io.BytesIO(content),
            metadata={"workspace_id": workspace_id, "mime_type": file.content_type},
        )
        extracted = ""
        try:
            from app.services.file_text_extractor import extract_text_from_upload

            extracted, _kind = await extract_text_from_upload(
                content,
                filename=file.filename,
                content_type=file.content_type,
            )
        except Exception:
            # Still store the file even if text extraction fails
            extracted = ""
        dtype = DocumentType.OTHER
        try:
            dtype = DocumentType(doc_type)
        except ValueError:
            pass
        doc = ProjectDocument(
            workspace_id=PydanticObjectId(workspace_id),
            name=file.filename or "document",
            type=dtype,
            file_id=str(file_id),
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            extracted_text=extracted or None,
            uploaded_by=user_id,
            created_by=str(user_id),
        )
        await doc.insert()
        return _doc_response(doc)

    async def list(self, workspace_id: str, user_id: PydanticObjectId) -> List[DocumentResponse]:
        await require_workspace_member(workspace_id, user_id)
        docs = await ProjectDocument.find(
            ProjectDocument.workspace_id == PydanticObjectId(workspace_id),
            ProjectDocument.deleted_at == None,
        ).to_list()
        return [_doc_response(d) for d in docs]

    async def list_extracted_texts(self, workspace_id: str, max_chars: int = 6000) -> str:
        """Concatenate extracted document text for RAG / kanban context."""
        docs = await ProjectDocument.find(
            ProjectDocument.workspace_id == PydanticObjectId(workspace_id),
            ProjectDocument.deleted_at == None,
        ).to_list()
        parts: list[str] = []
        total = 0
        for doc in docs:
            text = (doc.extracted_text or "").strip()
            if not text:
                continue
            block = f"=== Document: {doc.name} ===\n{text}"
            if total + len(block) > max_chars:
                remain = max_chars - total
                if remain > 200:
                    parts.append(block[:remain] + "…")
                break
            parts.append(block)
            total += len(block) + 2
        return "\n\n".join(parts)

    async def get(self, document_id: str, user_id: PydanticObjectId) -> tuple[ProjectDocument, bytes]:
        doc = await self._get_doc(document_id)
        await require_workspace_member(str(doc.workspace_id), user_id)
        db = get_db()
        bucket = AsyncIOMotorGridFSBucket(db)
        stream = await bucket.open_download_stream(PydanticObjectId(doc.file_id))
        content = await stream.read()
        return doc, content

    async def preview(self, document_id: str, user_id: PydanticObjectId) -> DocumentPreviewResponse:
        doc = await self._get_doc(document_id)
        await require_workspace_member(str(doc.workspace_id), user_id)
        text = (doc.extracted_text or "").strip()
        if not text:
            _, content = await self.get(document_id, user_id)
            mime = (doc.mime_type or "").lower()
            name = (doc.name or "").lower()
            if (
                mime.startswith("text/")
                or mime in {"application/json", "application/markdown"}
                or name.endswith((".md", ".txt", ".markdown", ".json", ".csv"))
            ):
                try:
                    text = content.decode("utf-8", errors="replace")
                except Exception:
                    text = ""
        return DocumentPreviewResponse(
            id=str(doc.id),
            name=doc.name,
            type=doc.type.value,
            mime_type=doc.mime_type,
            text=text,
        )

    async def delete(self, document_id: str, user_id: PydanticObjectId) -> None:
        doc = await self._get_doc(document_id)
        await require_workspace_lead(str(doc.workspace_id), user_id)
        doc.soft_delete()
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()

    async def _get_doc(self, document_id: str) -> ProjectDocument:
        doc = await ProjectDocument.get(PydanticObjectId(document_id))
        if not doc or doc.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc


document_service = DocumentService()
