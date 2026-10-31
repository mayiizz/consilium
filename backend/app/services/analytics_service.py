from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from beanie import PydanticObjectId

from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.schemas.analytics import (
    AnalyticsResponse,
    BurndownPoint,
    DashboardMeeting,
    DashboardResponse,
    DashboardStats,
    MemberStats,
    RiskItem,
    RisksResponse,
    RoadmapMilestone,
    RoadmapPhase,
    RoadmapResponse,
)
from app.services.permissions import get_workspace_or_404, require_workspace_lead, require_workspace_member


def _avatar_url(seed: str) -> str:
    return f"https://api.dicebear.com/7.x/avataaars/svg?seed={seed}"


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _task_completed_at(task: Task) -> Optional[datetime]:
    """Best-effort completion timestamp from history, else updated_at when Done."""
    if task.status != TaskStatus.DONE:
        return None
    done_vals = {"Done", "done"}
    latest: Optional[datetime] = None
    for entry in task.history or []:
        if (entry.field or "").lower() in {"status", "task.status"} and (entry.new_value or "") in done_vals:
            at = _aware(entry.changed_at)
            if at and (latest is None or at > latest):
                latest = at
    if latest:
        return latest
    return _aware(task.updated_at or task.last_activity_at or task.created_at)


def _meeting_to_dashboard(m: Meeting, users: Dict[str, User]) -> DashboardMeeting:
    participants = []
    for a in m.attendees:
        if a.user_id:
            u = users.get(str(a.user_id))
            if u:
                participants.append(
                    {
                        "id": str(u.id),
                        "name": u.name,
                        "avatar": u.avatar or _avatar_url(u.name),
                    }
                )
    start = m.started_at or m.scheduled_at or m.created_at
    return DashboardMeeting(
        id=str(m.id),
        title=m.title,
        status=m.status.value,
        start_time=start,
        duration=m.duration or None,
        participants=participants,
        jitsi_url=m.video_link,
        summary=m.summary,
    )


class AnalyticsService:
    async def dashboard(self, workspace_id: str, user_id: PydanticObjectId) -> DashboardResponse:
        ws = await get_workspace_or_404(workspace_id)
        member = await require_workspace_member(workspace_id, user_id)
        is_lead = member.role == WorkspaceRole.LEAD

        tasks_query = Task.find(
            Task.workspace_id == PydanticObjectId(workspace_id),
            Task.deleted_at == None,
        )
        if not is_lead:
            tasks_query = tasks_query.find(Task.assignee == user_id)
        tasks = await tasks_query.to_list()

        by_status: Dict[str, int] = {}
        for t in tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

        now = datetime.now(timezone.utc)
        overdue = sum(
            1
            for t in tasks
            if t.due_date
            and (t.due_date.replace(tzinfo=timezone.utc) if t.due_date.tzinfo is None else t.due_date) < now
            and t.status != TaskStatus.DONE
        )
        my_tasks = len(tasks) if not is_lead else sum(1 for t in tasks if t.assignee == user_id)

        meetings = await Meeting.find(
            Meeting.workspace_id == PydanticObjectId(workspace_id),
            Meeting.deleted_at == None,
        ).to_list()

        user_ids = {str(m.user_id) for m in ws.members}
        users: Dict[str, User] = {}
        for uid in user_ids:
            u = await User.get(PydanticObjectId(uid))
            if u:
                users[uid] = u

        live_meeting = next((m for m in meetings if m.status == MeetingStatus.LIVE), None)
        upcoming = sorted(
            [m for m in meetings if m.status == MeetingStatus.SCHEDULED],
            key=lambda m: m.scheduled_at or m.created_at,
        )[:3]
        recent = sorted(
            [m for m in meetings if m.status == MeetingStatus.ENDED],
            key=lambda m: m.ended_at or m.created_at,
            reverse=True,
        )[:3]

        members_stats: List[MemberStats] = []
        all_tasks = await Task.find(
            Task.workspace_id == PydanticObjectId(workspace_id),
            Task.deleted_at == None,
        ).to_list()
        for m in ws.members:
            u = users.get(str(m.user_id))
            if not u:
                continue
            assigned = sum(1 for t in all_tasks if t.assignee == m.user_id)
            completed = sum(
                1 for t in all_tasks if t.assignee == m.user_id and t.status == TaskStatus.DONE
            )
            members_stats.append(
                MemberStats(
                    id=str(u.id),
                    name=u.name,
                    email=u.email,
                    role="manager" if m.role == WorkspaceRole.LEAD else "member",
                    avatar=u.avatar or _avatar_url(u.name),
                    skills=u.skills,
                    tasks_assigned=assigned,
                    tasks_completed=completed,
                )
            )

        done_count = sum(1 for t in all_tasks if t.status == TaskStatus.DONE)
        total_count = len(all_tasks) or 1
        team_score = min(100, round((done_count / total_count) * 100)) if all_tasks else 0

        stats = DashboardStats(
            total_tasks=len(tasks),
            tasks_by_status=by_status,
            my_tasks=my_tasks,
            overdue_tasks=overdue,
            live_meetings=1 if live_meeting else 0,
            upcoming_meetings=len(upcoming),
            recent_meetings=[
                {"id": str(m.id), "title": m.title, "status": m.status.value}
                for m in recent
            ],
        )

        return DashboardResponse(
            stats=stats,
            live_meeting=_meeting_to_dashboard(live_meeting, users) if live_meeting else None,
            upcoming_meetings=[_meeting_to_dashboard(m, users) for m in upcoming],
            recent_meetings=[_meeting_to_dashboard(m, users) for m in recent],
            members=members_stats[:5] if is_lead else [],
            team_score=team_score,
        )

    async def analytics(self, workspace_id: str, user_id: PydanticObjectId) -> AnalyticsResponse:
        await require_workspace_lead(workspace_id, user_id)
        tasks = await Task.find(
            Task.workspace_id == PydanticObjectId(workspace_id),
            Task.deleted_at == None,
        ).to_list()

        by_assignee: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        completions: List[Tuple[datetime, Task]] = []
        for t in tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            name = (t.assignee_name or "").strip() or "Unassigned"
            if t.assignee and name in {"", "Unassigned"}:
                u = await User.get(t.assignee)
                name = u.name if u else "Unknown"
            by_assignee[name] = by_assignee.get(name, 0) + 1
            completed_at = _task_completed_at(t)
            if completed_at:
                completions.append((completed_at, t))

        planned = len(tasks)
        now = datetime.now(timezone.utc)
        days = 14
        start_day = (now - timedelta(days=days - 1)).date()
        burndown: List[BurndownPoint] = []
        for i in range(days):
            day = start_day + timedelta(days=i)
            if day == now.date():
                completed = sum(1 for at, _ in completions if at <= now)
            else:
                day_end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc)
                completed = sum(1 for at, _ in completions if at <= day_end)
            remaining = max(0, planned - completed)
            burndown.append(
                BurndownPoint(
                    week=day.strftime("%b %d"),
                    planned=planned,
                    completed=completed,
                    remaining=remaining,
                )
            )

        week_counts: Dict[str, int] = {}
        for at, _ in completions:
            iso = at.isocalendar()
            key = f"{iso.year}-W{iso.week:02d}"
            week_counts[key] = week_counts.get(key, 0) + 1
        for i in range(7, -1, -1):
            d = now - timedelta(weeks=i)
            iso = d.isocalendar()
            key = f"{iso.year}-W{iso.week:02d}"
            week_counts.setdefault(key, 0)
        velocity = [{"week": k, "completed": week_counts[k]} for k in sorted(week_counts.keys())][-8:]

        meetings = await Meeting.find(
            Meeting.workspace_id == PydanticObjectId(workspace_id),
            Meeting.deleted_at == None,
        ).to_list()
        meeting_stats = {
            "total": len(meetings),
            "scheduled": sum(1 for m in meetings if m.status == MeetingStatus.SCHEDULED),
            "live": sum(1 for m in meetings if m.status == MeetingStatus.LIVE),
            "ended": sum(1 for m in meetings if m.status == MeetingStatus.ENDED),
            "cancelled": sum(1 for m in meetings if m.status == MeetingStatus.CANCELLED),
            "tasks_by_status": by_status,
            "tasks_total": planned,
            "tasks_done": sum(1 for t in tasks if t.status == TaskStatus.DONE),
        }

        return AnalyticsResponse(
            velocity=velocity,
            burndown=[b.model_dump() for b in burndown],
            tasks_by_assignee=by_assignee,
            meeting_stats=meeting_stats,
        )

    async def roadmap(self, workspace_id: str, user_id: PydanticObjectId) -> RoadmapResponse:
        await require_workspace_lead(workspace_id, user_id)
        tasks = await Task.find(
            Task.workspace_id == PydanticObjectId(workspace_id),
            Task.deleted_at == None,
        ).to_list()

        phases = []
        quarters = ["Q1", "Q2", "Q3", "Q4"]
        for i, phase_status in enumerate(["done", "active", "planned", "planned"]):
            if i == 0:
                group_tasks = [t for t in tasks if t.status == TaskStatus.DONE]
            elif i == 1:
                group_tasks = [t for t in tasks if t.status in (TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW)]
            else:
                group_tasks = [t for t in tasks if t.status in (TaskStatus.TODO, TaskStatus.BLOCKERS)]

            milestones = []
            by_title: Dict[str, List[Task]] = {}
            for t in group_tasks:
                by_title.setdefault(t.status.value, []).append(t)
            for name, ts in by_title.items():
                milestones.append(
                    RoadmapMilestone(
                        name=name,
                        status=(
                            "done"
                            if phase_status == "done"
                            else ("active" if phase_status == "active" else "planned")
                        ),
                        task_count=len(ts),
                    )
                )
            if not milestones and group_tasks:
                milestones = [RoadmapMilestone(name="Tasks", status=phase_status, task_count=len(group_tasks))]

            progress = 0
            if group_tasks:
                if phase_status == "done":
                    progress = 100
                elif phase_status == "active":
                    progress = round(
                        (
                            sum(
                                1
                                for t in group_tasks
                                if t.status in (TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE)
                            )
                            / len(group_tasks)
                        )
                        * 100
                    )
                else:
                    done_in = sum(1 for t in group_tasks if t.status == TaskStatus.DONE)
                    progress = round((done_in / len(group_tasks)) * 100)

            phases.append(
                RoadmapPhase(
                    id=f"p{i + 1}",
                    name=f"Phase {i + 1}",
                    status=phase_status if i < 3 else "planned",
                    milestones=milestones,
                    q=quarters[i % 4],
                    progress=progress,
                )
            )

        if not phases:
            phases = [
                RoadmapPhase(
                    id="p1",
                    name="Phase 1",
                    status="planned",
                    q="Q1",
                    progress=0,
                    milestones=[RoadmapMilestone(name="Getting started", status="planned", task_count=0)],
                )
            ]
        return RoadmapResponse(phases=phases)

    async def risks(self, workspace_id: str, user_id: PydanticObjectId) -> RisksResponse:
        await require_workspace_member(workspace_id, user_id)
        blockers = await Task.find(
            Task.workspace_id == PydanticObjectId(workspace_id),
            Task.status == TaskStatus.BLOCKERS,
            Task.deleted_at == None,
        ).to_list()
        risks = []
        for t in blockers:
            owner = "Unassigned"
            if t.assignee:
                u = await User.get(t.assignee)
                owner = u.name if u else "Unknown"
            elif t.assignee_name:
                owner = t.assignee_name
            severity = "high" if t.priority.value in ("high", "urgent") else "medium"
            risks.append(
                RiskItem(
                    id=str(t.id),
                    title=t.title,
                    severity=severity,
                    owner=owner,
                    impact=t.blocker_reason or t.description or "Blocked task requiring attention.",
                )
            )
        return RisksResponse(risks=risks, total=len(risks))


analytics_service = AnalyticsService()
