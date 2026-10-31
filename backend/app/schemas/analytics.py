from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    total_tasks: int = 0
    tasks_by_status: Dict[str, int] = Field(default_factory=dict)
    my_tasks: int = 0
    overdue_tasks: int = 0
    live_meetings: int = 0
    upcoming_meetings: int = 0
    recent_meetings: List[Dict[str, Any]] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    velocity: List[Dict[str, Any]] = Field(default_factory=list)
    burndown: List[Dict[str, Any]] = Field(default_factory=list)
    tasks_by_assignee: Dict[str, int] = Field(default_factory=dict)
    meeting_stats: Dict[str, Any] = Field(default_factory=dict)


class RoadmapMilestone(BaseModel):
    name: str
    status: str  # done | active | planned
    task_count: int = 0


class RoadmapPhase(BaseModel):
    id: str
    name: str
    status: str  # done | active | planned
    milestones: List[RoadmapMilestone] = Field(default_factory=list)
    q: str
    progress: int = 0


class RoadmapResponse(BaseModel):
    phases: List[RoadmapPhase] = Field(default_factory=list)


class RiskItem(BaseModel):
    id: str
    title: str
    severity: str  # high | medium | low
    owner: str
    impact: str


class RisksResponse(BaseModel):
    risks: List[RiskItem] = Field(default_factory=list)
    total: int = 0


class BurndownPoint(BaseModel):
    week: str
    planned: int = 0
    completed: int = 0
    remaining: int = 0


class MemberStats(BaseModel):
    id: str
    name: str
    email: str
    role: str
    avatar: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    tasks_assigned: int = 0
    tasks_completed: int = 0


class DashboardMeeting(BaseModel):
    id: str
    title: str
    status: str
    start_time: Optional[datetime] = None
    duration: Optional[int] = None
    participants: List[Dict[str, Any]] = Field(default_factory=list)
    jitsi_url: Optional[str] = None
    summary: Optional[str] = None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    live_meeting: Optional[DashboardMeeting] = None
    upcoming_meetings: List[DashboardMeeting] = Field(default_factory=list)
    recent_meetings: List[DashboardMeeting] = Field(default_factory=list)
    members: List[MemberStats] = Field(default_factory=list)
    team_score: int = 0
