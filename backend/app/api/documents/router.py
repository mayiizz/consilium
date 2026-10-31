from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas import DocumentResponse, MessageResponse
from app.schemas.document import DocumentPreviewResponse
from app.services.document_service import document_service

router = APIRouter(tags=["documents"])


@router.post("/api/workspaces/{workspace_id}/documents", response_model=DocumentResponse)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    return await document_service.upload(workspace_id, user.id, file, doc_type)


@router.get("/api/workspaces/{workspace_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    workspace_id: str, user: User = Depends(get_current_user)
) -> List[DocumentResponse]:
    return await document_service.list(workspace_id, user.id)


@router.get("/api/documents/{document_id}")
async def get_document(
    document_id: str, user: User = Depends(get_current_user)
) -> Response:
    doc, content = await document_service.get(document_id, user.id)
    return Response(content=content, media_type=doc.mime_type)


@router.get("/api/documents/{document_id}/preview", response_model=DocumentPreviewResponse)
async def preview_document(
    document_id: str, user: User = Depends(get_current_user)
) -> DocumentPreviewResponse:
    return await document_service.preview(document_id, user.id)


@router.delete("/api/documents/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: str, user: User = Depends(get_current_user)
) -> MessageResponse:
    await document_service.delete(document_id, user.id)
    return MessageResponse(message="Document deleted")
