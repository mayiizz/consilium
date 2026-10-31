"""Seed Project0 demo data: team, upcoming meetings, tasks for analytics/risks."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from beanie import PydanticObjectId

from app.core.database import close_db, init_models
from app.core.security import generate_task_key, hash_password
from app.models.meeting import Meeting, MeetingPlatform, MeetingStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import AuthProvider, User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

PROJECT0_NAMES = ("Project0", "project0")
LEAD_EMAIL = "user1@gmail.com"

TEAM = [
    ("sam@sprint.demo", "Sam Chen", ["Product", "Scrum", "Stakeholders"]),
    ("aria@sprint.demo", "Aria Patel", ["Next.js", "TypeScript", "Figma"]),
    ("leo@sprint.demo", "Leo Martinez", ["FastAPI", "Python", "ML"]),
    ("maya@sprint.demo", "Maya Okonkwo", ["Docker", "CI/CD", "Load testing"]),
]

UPCOMING_MEETINGS = [
    ("Day 4: Feature Freeze & QA", "Final bug bash before code freeze. QA sign-off on prediction flow."),
    ("Day 5: Stakeholder Demo Rehearsal", "Dry run of the demo script with Sam presenting live staging."),
    ("Stakeholder Demo", "External demo for placement judges — live prediction + dashboard walkthrough."),
]

DEMO_TASKS = [
    ("Set up FastAPI boilerplate & health checks", TaskStatus.DONE, TaskPriority.MEDIUM, "leo@sprint.demo"),
    ("Initialize Next.js dashboard shell", TaskStatus.DONE, TaskPriority.MEDIUM, "aria@sprint.demo"),
    ("Configure Docker & GitHub Actions CI", TaskStatus.DONE, TaskPriority.HIGH, "maya@sprint.demo"),
    ("Convert analytics timestamps to Unix integers", TaskStatus.DONE, TaskPriority.HIGH, "leo@sprint.demo"),
    ("Integrate ML prediction pipeline", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, "leo@sprint.demo"),
    ("Build interactive data tables & search", TaskStatus.IN_PROGRESS, TaskPriority.MEDIUM, "aria@sprint.demo"),
    ("Add Redis cache for prediction endpoint", TaskStatus.IN_PROGRESS, TaskPriority.URGENT, "leo@sprint.demo"),
    ("Replace loading spinner with skeleton UI", TaskStatus.IN_REVIEW, TaskPriority.MEDIUM, "aria@sprint.demo"),
    ("Write integration test payloads script", TaskStatus.TODO, TaskPriority.MEDIUM, "maya@sprint.demo"),
    ("Update staging env for Redis container", TaskStatus.TODO, TaskPriority.HIGH, "maya@sprint.demo"),
    (
        "Prediction endpoint latency under load",
        TaskStatus.BLOCKERS,
        TaskPriority.URGENT,
        "leo@sprint.demo",
        "Heavy SQL on every request — 2.5s DB + 1.5s inference; load test hit 9s at 20 users.",
    ),
    (
        "Staging memory headroom for Redis",
        TaskStatus.BLOCKERS,
        TaskPriority.HIGH,
        "maya@sprint.demo",
        "Need to confirm Redis cache allocation before demo; monitor RAM after Leo's Redis deploy.",
    ),
]


async def _find_project0() -> Workspace | None:
    for ws in await Workspace.find(Workspace.deleted_at == None).to_list():
        if ws.name in PROJECT0_NAMES or ws.slug.lower().startswith("project0"):
            return ws
    return None


async def _get_or_create_user(email: str, name: str, skills: list[str]) -> User:
    user = await User.find_one(User.email == email, User.deleted_at == None)
    if user:
        user.name = name
        user.skills = skills
        await user.save()
        return user
    user = User(
        email=email,
        name=name,
        password_hash=hash_password("password123"),
        auth_provider=AuthProvider.CREDENTIALS,
        skills=skills,
        created_by="seed",
    )
    await user.insert()
    return user


async def seed() -> None:
    await init_models()
    ws = await _find_project0()
    if not ws:
        print("Project0 workspace not found — run seed_sprint_meetings.py first or create the workspace.")
        return

    lead = await User.find_one(User.email == LEAD_EMAIL)
    if not lead:
        print(f"Lead user {LEAD_EMAIL} not found.")
        return

    member_ids: dict[str, PydanticObjectId] = {LEAD_EMAIL: lead.id}
    for email, name, skills in TEAM:
        user = await _get_or_create_user(email, name, skills)
        member_ids[email] = user.id
        if not any(m.user_id == user.id for m in ws.members):
            ws.members.append(
                WorkspaceMember(
                    user_id=user.id,
                    role=WorkspaceRole.MEMBER,
                    invited_by=lead.id,
                )
            )
            print(f"Added team member: {name}")

    await ws.save()

    now = datetime.now(timezone.utc)
    for i, (title, desc) in enumerate(UPCOMING_MEETINGS):
        existing = await Meeting.find_one(
            Meeting.workspace_id == ws.id,
            Meeting.title == title,
            Meeting.deleted_at == None,
        )
        if existing:
            continue
        scheduled = now + timedelta(days=i + 1, hours=10)
        meeting = Meeting(
            workspace_id=ws.id,
            title=title,
            description=desc,
            platform=MeetingPlatform.JITSI,
            status=MeetingStatus.SCHEDULED,
            scheduled_at=scheduled,
            created_by=str(lead.id),
        )
        await meeting.insert()
        print(f"Scheduled meeting: {title}")

    users_by_email = {email: uid for email, uid in member_ids.items()}
    for spec in DEMO_TASKS:
        title = spec[0]
        status, priority, assignee_email = spec[1], spec[2], spec[3]
        blocker_reason = spec[4] if len(spec) > 4 else None

        existing = await Task.find_one(
            Task.workspace_id == ws.id,
            Task.title == title,
            Task.deleted_at == None,
        )
        if existing:
            continue

        assignee_id = users_by_email.get(assignee_email)
        assignee_user = await User.get(assignee_id) if assignee_id else None
        task = Task(
            workspace_id=ws.id,
            title=title,
            description=blocker_reason or "",
            assignee=assignee_id,
            assignee_name=assignee_user.name if assignee_user else None,
            status=status,
            priority=priority,
            task_key=generate_task_key(),
            is_auto_generated=False,
            blocker_reason=blocker_reason,
            last_activity_at=now,
            created_by=str(lead.id),
        )
        await task.insert()
        print(f"Created task: {title} [{status.value}]")

    print(f"\nProject0 demo seed complete — workspace '{ws.name}' ({ws.id})")


async def main() -> None:
    try:
        await seed()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
