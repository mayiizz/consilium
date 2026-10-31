"""Seed Day 1–3 sprint planning meeting transcripts for user1@gmail.com."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from beanie import PydanticObjectId

from app.core.database import close_db, init_models
from app.core.security import hash_password
from app.models.meeting import Meeting, MeetingAttendee, MeetingStatus, TranscriptChunk
from app.models.user import AuthProvider, User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.utils.helpers import slugify

USER_EMAIL = "user1@gmail.com"
USER_NAME = "User One"
DEFAULT_PASSWORD = "password123"
WORKSPACE_NAME = "Sprint Demo Workspace"

MEETINGS = [
    {
        "title": "Day 1: Sprint Planning & Architecture Alignment",
        "lines": [
            ("Sam", "Good morning, team. Welcome to Day 1 of our intensive sprint. We have exactly 5 days to turn our project proposal into a high-fidelity, working deployment for the upcoming stakeholder demo. Our goal today is to map out the exact technical architecture, establish our API contracts, and divide the tasks so no one is stepping on anyone else's toes. Aria, let's start with the visual layout and client-side expectations."),
            ("Aria", "Morning everyone. I finalized the Figma workspace last night. The core layout relies on a modern, high-contrast dashboard framework. The main view contains three primary widgets: a real-time analytics data stream, a complex search interface with multi-tier filtering, and a predictive visualization panel. For the tech stack, I'm initializing a Next.js 14 repository using App Router, TypeScript, and Tailwind CSS. Leo, we need to finalize the data structure for the predictive panel because I want to map the TypeScript interfaces today."),
            ("Leo", "Looks clean, Aria. For the backend, I'm building a RESTful API using FastAPI since we need high performance to handle our data-driven prediction pipeline. Our machine learning model—which processes user input data and runs a real-time inference—takes about 4 distinct parameters. I'll make sure the API returns a structured JSON payload. It's going to look something like a nested object: a status code, an array of prediction probabilities, and a timestamp."),
            ("Maya", "Hold on a second, Leo. If the model is running real-time inference on every request, what happens if the database gets hit with a high volume of concurrent traffic? Are we handling the prediction queue asynchronously, or are we going to let the connection pool block?"),
            ("Leo", "Good point, Maya. For the MVP, to keep it simple, it's a synchronous block, but I am implementing connection pooling via SQLAlchemy to manage database threads. If we notice latency spikes during your load testing on Wednesday, I can quickly set up a Celery worker queue with Redis."),
            ("Maya", "Let's plan for the worst-case scenario. I don't want the server crashing during our live demo. Today, my primary task is creating our cloud environment infrastructure. I'm writing a docker-compose.yml file to containerize the FastAPI app and the PostgreSQL database locally. By this afternoon, I'll have our GitHub Actions CI/CD pipeline built so that every time Aria or Leo pushes to the main or dev branches, it automatically builds and runs a linting check."),
            ("Sam", "Perfect. Let's look at the breakdown of our Jira tickets for Day 1: Aria will initialize Next.js project, configure global Tailwind styles, build responsive sidebar/navigation components, and define global TypeScript interfaces. Leo will set up FastAPI boilerplate, configure PostgreSQL database connections, write the initial database migration schemas, and expose the basic health-check endpoints. Maya will configure Docker environments, write GitHub Actions workflows, and provision the staging server environment."),
            ("Sam", "Are there any immediate resource constraints or blockers before we drop off to code?"),
            ("Aria", "I just need Leo to drop the exact JSON schema example into our shared documentation page within the next hour so I can mock my frontend fetch states accurately."),
            ("Leo", "I'm typing it out right now, Aria. You'll have it in 10 minutes."),
            ("Sam", "Awesome. Let's put our heads down and execute. See you all tomorrow for the standup."),
        ],
    },
    {
        "title": "Day 2: Daily Standup & API Integration Hurdle",
        "lines": [
            ("Sam", "Morning team! Welcome to Day 2. Let's keep this brief and focused. Standard format: What did you do, what are you doing today, and what is blocking you? Aria, kick us off."),
            ("Aria", "Yesterday I successfully bootstrapped the Next.js app and built out the shell of the dashboard. The responsiveness is fully dialed in. Today, I started building the interactive data tables and the search component. However, I've run into a blocker regarding Leo's API structure."),
            ("Sam", "What's the issue?"),
            ("Aria", "Leo, the JSON mock you gave me returns the historical data timestamps as a raw string format from the database, but the client-side charting library I chose requires an explicit Unix timestamp integer to map the X-axis correctly. If I try to parse strings on the frontend for 10,000 data rows, the browser UI lags visibly."),
            ("Leo", "Ah, I see what you mean. On my end yesterday, I got the PostgreSQL database fully mapped and wrote the endpoints for user authentication and data retrieval. I can easily modify the backend serializer to convert the database datetime objects into Unix timestamps before sending the response. It's much more efficient to handle that data serialization on the server side anyway. I'll push an update to the /api/v1/analytics endpoint by noon."),
            ("Sam", "Great adjustment, Leo. What else is on your plate for today?"),
            ("Leo", "Once I update that serializer for Aria, my main focus today is integrating our core predictive ML pipeline into the FastAPI route handlers. I need to ensure the data inputted by the user is correctly validated using Pydantic schemas before it hits the model."),
            ("Maya", "That brings me to my update. Yesterday I completed the Docker setups and verified the CI/CD pipeline is working flawlessly—every commit is building cleanly. Today, I'm going to start writing automation scripts for integration testing. Leo, once you finish those Pydantic validation schemas, let me know. I'm going to write a script that purposely injects malformed, empty, or massive string payloads into your endpoints to see if we can break the backend validation layer."),
            ("Sam", "Excellent proactive testing, Maya. So, to summarize the plan for today: Leo updates the timestamp payload formats to unblock Aria, then moves to ML model routing. Aria integrates the updated API feed into her frontend state management system using React's useEffect or SWR. Maya builds out the security and validation test suites. We are moving fast, team. Let's keep communication fluid on Slack."),
        ],
    },
    {
        "title": "Day 3: Mid-Week Sync & Core Performance Bottlenecks",
        "lines": [
            ("Sam", "Happy Wednesday, team. We are at the midpoint of our project sprint. We have a semi-functional integrated app running on our staging environment right now. Let's do a live review. Aria, do you want to share your screen and show us what the staging link looks like?"),
            ("Aria", "Sure thing. So, as you can see, the Next.js frontend is pulling live data from Leo's FastAPI staging server. The navigation works, and the data tables render perfectly now that the timestamps are coming through as integers. But watch what happens when I click the Generate Prediction Report button. A loading spinner spins for 4 solid seconds before rendering data."),
            ("Sam", "Oof. That's a pretty noticeable delay for an online web app. What's causing that lag?"),
            ("Leo", "That's my department. The prediction model itself runs complex calculations, and right now, the endpoint is executing a heavy SQL query to pull historical reference points from the database every single time the user clicks that button. The database query is taking 2.5 seconds, and the model inference takes another 1.5 seconds."),
            ("Maya", "I ran an automated load test on that specific endpoint an hour ago with just 20 virtual users, and the response time scaled up to 9 seconds. If two people try to use this platform simultaneously during our placement presentation or hackathon judging, the application will completely time out."),
            ("Sam", "Okay, this is a critical bottleneck. We can't present a lagging app. What are our options to optimize this before tomorrow's feature freeze?"),
            ("Leo", "Since the historical reference data in the database only changes once a day, there is absolutely no reason to query the database on every single request. I can introduce a Redis caching layer this afternoon. When a user requests a prediction, the app will check if the historical summary is already in the Redis cache. If it is, retrieval takes 5 milliseconds instead of 2.5 seconds."),
            ("Aria", "From a frontend perspective, even if Leo gets the backend down to 1.5 seconds, a static loading spinner feels boring and makes the app feel slower than it actually is. Today, I'll replace that generic spinner with an animated skeleton loader screen that mimics the data structure. Psychologically, it makes the user feel like the app is working faster."),
            ("Maya", "I agree with both approaches. Leo, if you spin up a Redis container, make sure to update the docker-compose configuration and update the staging environment variables so the pipeline doesn't break. I will monitor the staging memory usage to make sure the Redis cache doesn't run out of allocated RAM."),
            ("Sam", "This is exactly why we do mid-week reviews. Excellent pivot plan. Leo handles Redis integration. Aria implements skeleton loading states and polishes the dashboard UI interactions. Maya monitors infrastructure updates and prepares for the final stress tests. Let's execute!"),
        ],
    },
]


def _chunks_from_lines(lines: list[tuple[str, str]], base_time: datetime) -> list[TranscriptChunk]:
    chunks: list[TranscriptChunk] = []
    for i, (speaker, text) in enumerate(lines):
        chunks.append(
            TranscriptChunk(
                chunk_id=str(uuid.uuid4()),
                speaker=speaker,
                text=f"{speaker}: {text}",
                timestamp=base_time + timedelta(seconds=i * 30),
                source="seed",
            )
        )
    return chunks


async def _get_or_create_user() -> User:
    user = await User.find_one(User.email == USER_EMAIL, User.deleted_at == None)
    if user:
        return user
    user = User(
        email=USER_EMAIL,
        name=USER_NAME,
        password_hash=hash_password(DEFAULT_PASSWORD),
        auth_provider=AuthProvider.CREDENTIALS,
        created_by="seed",
    )
    await user.insert()
    print(f"Created user {USER_EMAIL}")
    return user


async def _get_or_create_workspace(user: User) -> Workspace:
    for ws in await Workspace.find(Workspace.deleted_at == None).to_list():
        if any(m.user_id == user.id for m in ws.members):
            return ws

    slug_base = slugify(WORKSPACE_NAME)
    ws = Workspace(
        name=WORKSPACE_NAME,
        slug=slug_base,
        invite_code=hash_password("SPRINT01"),
        invite_code_raw="SPRINT01",
        created_by=str(user.id),
        members=[WorkspaceMember(user_id=user.id, role=WorkspaceRole.LEAD, invited_by=user.id)],
    )
    await ws.insert()
    print(f"Created workspace {WORKSPACE_NAME}")
    return ws


async def seed() -> None:
    await init_models()
    user = await _get_or_create_user()
    workspace = await _get_or_create_workspace(user)

    base_day = datetime(2026, 6, 9, 9, 0, tzinfo=timezone.utc)
    created = 0
    skipped = 0

    for day_index, spec in enumerate(MEETINGS):
        existing = await Meeting.find_one(
            Meeting.workspace_id == workspace.id,
            Meeting.title == spec["title"],
            Meeting.deleted_at == None,
        )
        if existing:
            print(f"Skip (exists): {spec['title']}")
            skipped += 1
            continue

        started = base_day + timedelta(days=day_index)
        ended = started + timedelta(hours=1)
        chunks = _chunks_from_lines(spec["lines"], started)

        meeting = Meeting(
            workspace_id=workspace.id,
            title=spec["title"],
            description="Sprint planning standup (seeded transcript)",
            status=MeetingStatus.ENDED,
            started_at=started,
            ended_at=ended,
            duration=3600,
            transcript_chunks=chunks,
            attendees=[
                MeetingAttendee(user_id=user.id, speaker_label=user.name, join_time=started, leave_time=ended),
            ],
            created_by=str(user.id),
        )
        await meeting.insert()
        created += 1
        print(f"Created meeting: {spec['title']} ({len(chunks)} chunks)")

    print(
        f"\nDone for {USER_EMAIL} — workspace '{workspace.name}' ({workspace.id}): "
        f"{created} created, {skipped} skipped"
    )


async def main() -> None:
    try:
        await seed()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
