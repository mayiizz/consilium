import json
from contextlib import asynccontextmanager

from beanie import PydanticObjectId
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics.router import router as analytics_router
from app.api.auth.router import router as auth_router
from app.api.copilot.router import router as copilot_router
from app.api.documents.router import router as documents_router
from app.api.github.router import router as github_router
from app.api.health.router import router as health_router
from app.api.kanban.router import router as kanban_router
from app.api.meetings.router import router as meetings_router
from app.api.notifications.router import router as notifications_router
from app.api.research.router import router as research_router
from app.api.tasks.router import router as tasks_router
from app.api.workspaces.router import router as workspaces_router
from app.core.config import get_settings
from app.core.database import close_db, init_models
from app.core.logging import setup_logging
from app.core.redis import close_redis, connect_redis
from app.core.security import decode_access_token
from app.core.websocket_manager import ws_manager
from app.models.meeting import Meeting
from app.models.user import User
from app.services.meeting_service import meeting_service
from app.services.permissions import require_workspace_member


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    await init_models()
    try:
        await connect_redis()
    except Exception:
        pass
    yield
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(workspaces_router)
    app.include_router(meetings_router)
    app.include_router(tasks_router)
    app.include_router(github_router)
    app.include_router(copilot_router)
    app.include_router(documents_router)
    app.include_router(analytics_router)
    app.include_router(kanban_router)
    app.include_router(notifications_router)
    app.include_router(research_router)

    @app.websocket("/ws/meetings/{meeting_id}")
    async def meeting_websocket(
        websocket: WebSocket,
        meeting_id: str,
        token: str = Query(...),
        role: str = Query("subscriber"),
    ) -> None:
        await websocket.accept()

        payload = decode_access_token(token)
        if not payload or not payload.get("sub"):
            await websocket.close(code=4001, reason="Invalid or expired token")
            return
        try:
            user = await User.get(PydanticObjectId(payload["sub"]))
        except Exception:
            await websocket.close(code=4001, reason="Invalid user")
            return
        if not user or user.deleted_at:
            await websocket.close(code=4001, reason="User not found")
            return
        try:
            meeting_oid = PydanticObjectId(meeting_id)
        except Exception:
            await websocket.close(code=4004, reason="Invalid meeting id")
            return
        meeting = await Meeting.get(meeting_oid)
        if not meeting or meeting.deleted_at:
            await websocket.close(code=4004, reason="Meeting not found")
            return
        try:
            await require_workspace_member(str(meeting.workspace_id), user.id)
        except Exception:
            await websocket.close(code=4003, reason="Not a workspace member")
            return

        ws_manager.register(meeting_id, websocket)
        await meeting_service.register_ws_attendee(meeting, user.id)

        if role == "agent":
            went_live = await meeting_service.transition_to_live(meeting)
            meeting = await Meeting.get(PydanticObjectId(meeting_id))
            if went_live and meeting:
                await ws_manager.broadcast(
                    meeting_id,
                    {"type": "meeting_status", "status": "live"},
                )

        try:
            while True:
                raw = await websocket.receive_text()
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == "agent_connected":
                    went_live = await meeting_service.transition_to_live(meeting)
                    meeting = await Meeting.get(PydanticObjectId(meeting_id))
                    if went_live and meeting:
                        await ws_manager.broadcast(
                            meeting_id,
                            {"type": "meeting_status", "status": "live"},
                        )
                elif msg_type == "transcript_chunk":
                    chunk_data = dict(data.get("chunk", {}))
                    # Prefer authenticated user's name so every line is labeled.
                    if user and getattr(user, "name", None):
                        chunk_data["speaker"] = user.name
                    chunk, went_live = await meeting_service.append_transcript_chunk(
                        meeting_id, chunk_data
                    )
                    for payload in meeting_service.chunk_broadcast_payloads(chunk):
                        await ws_manager.broadcast(meeting_id, payload)
                    if went_live:
                        await ws_manager.broadcast(
                            meeting_id,
                            {"type": "meeting_status", "status": "live"},
                        )
                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
        except WebSocketDisconnect:
            ws_manager.disconnect(meeting_id, websocket)

    return app


app = create_app()
