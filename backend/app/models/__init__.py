from app.models.copilot_conversation import CopilotConversation
from app.models.document import ProjectDocument
from app.models.github_webhook_event import GitHubWebhookEvent
from app.models.kanban_review import KanbanTaskReviewQueue
from app.models.meeting import Meeting
from app.models.notification import Notification, ResearchJob
from app.models.research_conversation import ResearchConversation
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace

ALL_MODELS = [
    User,
    Workspace,
    Meeting,
    Task,
    ProjectDocument,
    GitHubWebhookEvent,
    CopilotConversation,
    ResearchConversation,
    KanbanTaskReviewQueue,
    Notification,
    ResearchJob,
]

__all__ = [
    "User",
    "Workspace",
    "Meeting",
    "Task",
    "ProjectDocument",
    "GitHubWebhookEvent",
    "CopilotConversation",
    "ResearchConversation",
    "KanbanTaskReviewQueue",
    "Notification",
    "ResearchJob",
    "ALL_MODELS",
]
