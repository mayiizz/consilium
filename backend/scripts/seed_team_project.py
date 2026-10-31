"""Seed a full demo project: manager, teammates, 20–30 min meetings with transcripts, Kanban tasks."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from app.core.database import close_db, init_models
from app.core.security import generate_task_key, hash_password
from app.models.meeting import (
    Meeting,
    MeetingAttendee,
    MeetingPlatform,
    MeetingStatus,
    TranscriptChunk,
)
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import AuthProvider, User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

DEFAULT_PASSWORD = "password123"
WORKSPACE_NAME = "PulseDesk"
WORKSPACE_SLUG = "pulsedesk"
INVITE_CODE = "PULSE01"

LEAD = ("priya@pulsedesk.demo", "Priya Shah", ["Product", "Facilitation", "Stakeholders"])

TEAM = [
    ("jordan@pulsedesk.demo", "Jordan Lee", ["React", "TypeScript", "Maps"]),
    ("amira@pulsedesk.demo", "Amira Hassan", ["FastAPI", "PostgreSQL", "Redis"]),
    ("kenji@pulsedesk.demo", "Kenji Sato", ["Swift", "QR", "Mobile"]),
    ("riley@pulsedesk.demo", "Riley Brooks", ["Figma", "QA", "Accessibility"]),
]

MEETINGS = [
    {
        "title": "Sprint 1 kickoff: PulseDesk desk-booking MVP",
        "description": "Align on PulseDesk MVP: map booking, conflict API, QR check-in, QA.",
        "days_ago": 5,
        "duration_min": 28,
        "lines": [
            ("Priya", "Welcome everyone. We have about half an hour. PulseDesk is a floor-map desk booking app for the downtown office. This sprint we ship the MVP: pick a desk on the map, book a slot, get a Slack ping, and check in with a QR on the plaque."),
            ("Priya", "Jordan owns the map UI, Amira the booking API, Kenji mobile QR check-in, Riley design plus QA. Third floor only. No waitlist. Let's go around with constraints and then lock decisions."),
            ("Jordan", "I'll render the third-floor SVG in React. Green is free, amber is held, grey is occupied. I need GET /desks with id, x, y, and status. Blocker for later: we still don't have Google Calendar OAuth, so the map cannot show external calendar holds."),
            ("Amira", "GET /desks is in my plan for today. POST /bookings will reject overlapping holds on the same desk. Slack notify on success is already drafted. I'll put inventory in Redis so the map does not hammer Postgres."),
            ("Kenji", "iOS will scan the plaque QR and call POST /check-in. Only the booking owner is marked present. I need Riley's scanner chrome sizes today so I don't guess padding on a small phone."),
            ("Riley", "Figma is almost ready: map, booking drawer, empty and error. I'll also write the accessibility checklist and a QA script that tries to double-book the same desk. I'll review Jordan's contrast before Friday."),
            ("Priya", "Calendar OAuth stays off the critical path. If Google review slips, the map only shows PulseDesk bookings. Jordan, do not block the map on that."),
            ("Jordan", "Understood. I'll mock occupied desks from Amira's status field. Question: do we zoom to a neighborhood or show the whole floor at once?"),
            ("Riley", "Whole floor at 100% for MVP. Pinch-zoom is nice-to-have. Color plus a text status in the drawer so we are not color-only."),
            ("Amira", "Booking slots are 30 minutes, 9 to 6. No overnight. If someone holds a desk past checkout we do not auto-kick them this sprint."),
            ("Kenji", "Check-in window is 15 minutes before the start through the end of the slot. Late scan still counts as present. No geofence."),
            ("Priya", "Good. Action items: Jordan ships map UI this week. Amira conflict API by Wednesday. Kenji QR by Thursday. Riley a11y pass before demo. I'll write the Friday demo script."),
            ("Amira", "I'll publish the OpenAPI snippet in Slack after this call so Jordan can type the Desk interface."),
            ("Jordan", "If the payload uses snake_case I'll map it once in the client. Don't mix camelCase mid-sprint."),
            ("Riley", "I'll attach the QR mock to the Figma page labeled 'plaque v1'. Kenji, use that asset, not a placeholder box."),
            ("Kenji", "Got it. I'll also need a staging token that does not expire every hour or check-in demos will fail."),
            ("Amira", "I'll mint a 7-day staging JWT after I land the auth route. I'll ping you in Slack."),
            ("Priya", "Any other blockers before we drop?"),
            ("Jordan", "Only Calendar OAuth, already parked."),
            ("Riley", "None. I'll send Figma in an hour."),
            ("Priya", "Decisions recap: third floor only, conflict-safe bookings, QR check-in not geofence, Calendar OAuth out of MVP. Thanks — see you at tomorrow's standup. We used the full slot."),
        ],
        "summary": "PulseDesk Sprint 1 kickoff (28 min). Third-floor-only MVP: map, conflict-safe bookings with Slack notify, QR check-in. Calendar OAuth is parked. Demo Friday.",
        "action_items": [
            "Jordan: third-floor map UI with live desk status.",
            "Amira: booking conflict API, Redis cache, Slack notify.",
            "Kenji: iOS QR check-in against POST /check-in.",
            "Riley: Figma states plus accessibility/QA checklist.",
            "Priya: keep Calendar OAuth off the critical path; draft demo script.",
        ],
        "key_decisions": [
            "MVP covers the third floor only; no waitlist.",
            "Bookings must reject overlapping holds on the same desk.",
            "Check-in is QR on the desk plaque, not geofence.",
            "Calendar OAuth is not required for Friday demo.",
        ],
    },
    {
        "title": "Day 2 standup: map wiring and booking API",
        "description": "Daily standup on map UI, desk inventory, and first booking conflicts.",
        "days_ago": 4,
        "duration_min": 22,
        "lines": [
            ("Priya", "Day 2 standup. We have about twenty minutes. Yesterday, what landed, what's today, what's blocked. Jordan first."),
            ("Jordan", "Map shell is in. SVG loads. Hover highlights a desk. I still mock status locally because GET /desks 404'd last night. Today I wire the live feed and the booking drawer."),
            ("Amira", "Sorry — I pushed the route this morning. GET /desks returns id, x, y, status. POST /bookings returns 409 on overlap. Redis cache is behind a flag; staging Redis is up."),
            ("Kenji", "Scanner chrome matches Riley's plaque mock. I can decode a static QR. POST /check-in still 501. I'll keep polishing the camera permission copy until Amira lands the route."),
            ("Riley", "Figma map, drawer, empty and error are in review. Contrast on green versus grey passed WCAG AA on my laptop; I still need to check Jordan's actual SVG fills."),
            ("Priya", "Jordan, once /desks is live, don't keep the mock. Amira, share a curl in Slack so we all hit the same staging host."),
            ("Amira", "I'll post the curl and a sample 409 body. Also Slack notify fired once on my machine; I'll confirm the webhook secret on staging."),
            ("Jordan", "If status is a string, I'll treat unknown as grey not green. We should not show a desk as free when the API is confused."),
            ("Riley", "Please. I'll add that to the QA script: unknown status, 409 on double book, empty floor."),
            ("Kenji", "For check-in I'll show a friendly error if the booking is not theirs instead of a raw 403. Riley, is that in the error set?"),
            ("Riley", "I'll add a 'not your booking' state this afternoon."),
            ("Priya", "Calendar OAuth still parked. Any new blockers?"),
            ("Amira", "Staging JWT TTL is 7 days as promised. Kenji you should be unblocked on tokens."),
            ("Kenji", "Token works. Only missing the check-in route."),
            ("Jordan", "I'll need CORS on the API origin. Vite is 5173 locally, staging frontend is another host."),
            ("Amira", "I'll allow both origins after this call."),
            ("Priya", "Today: Jordan live map, Amira CORS plus 409 docs, Kenji wait on check-in but finish camera UX, Riley contrast on the real SVG. See you mid-week."),
            ("Riley", "I'll sit with Jordan for ten minutes after this to eyedropper the fills."),
            ("Jordan", "I'll share a preview link."),
            ("Priya", "Thanks all. Standup closed at twenty-two minutes."),
        ],
        "summary": "Day 2 standup (22 min). Map shell exists; GET /desks just landed. Kenji waits on POST /check-in. CORS and unknown-status handling called out. Calendar OAuth still parked.",
        "action_items": [
            "Jordan: wire live GET /desks; unknown status renders grey.",
            "Amira: CORS for local and staging; document 409 body; confirm Slack webhook.",
            "Kenji: camera UX; wait on check-in route.",
            "Riley: contrast pass on real SVG; 'not your booking' error state.",
        ],
        "key_decisions": [
            "Unknown desk status is grey, never green.",
            "API CORS must include local Vite and staging frontend.",
        ],
    },
    {
        "title": "Mid-week review: conflicts, performance, and QA",
        "description": "Walk staging map, load-test bookings, and lock QA before feature freeze.",
        "days_ago": 3,
        "duration_min": 26,
        "lines": [
            ("Priya", "Mid-week review. About twenty-five minutes. Jordan, share staging."),
            ("Jordan", "Map is live. Status colors match Riley. Drawer shows desk id and next slot. Booking from the drawer hits POST /bookings. First book succeeds. Second book of the same slot returns 409 and I show Riley's error."),
            ("Riley", "Good. Contrast is better. Keyboard focus on desks is still weak — tab order jumps. I'll file that as a11y, not a visual bug."),
            ("Amira", "Conflict detection uses a unique index on desk_id plus slot start. Load test with 20 virtual users: p95 was 180ms with Redis on, 1.4s with Redis off. Keep the flag on for demo."),
            ("Kenji", "Still no POST /check-in in staging OpenAPI. I can demo the camera against a fixture, but judges will notice if check-in is fake."),
            ("Priya", "Amira, check-in is the next merge. Don't let it slip past Thursday."),
            ("Amira", "I'll land POST /check-in today. Body is booking_id plus plaque_token. 200 present, 409 already checked in, 403 not owner."),
            ("Riley", "I'll add those three codes to the QA script. Also overlapping booking from two browsers at once — I caught a race once yesterday."),
            ("Amira", "That race is why the unique index exists. If you still see a double book, send me the two request ids."),
            ("Jordan", "Map refreshes every 15 seconds. During demo I'll also refresh on window focus so we don't wait."),
            ("Priya", "Do that. Fifteen seconds looks idle on a projector."),
            ("Riley", "Skeleton on first load is in. Empty floor copy is in. I'll record a 2-minute QA video after Kenji has check-in."),
            ("Kenji", "Once the route exists I'll hit it from the device on office wifi. Staging cert must be trusted on my phone."),
            ("Amira", "I'll put the staging CA steps in README. Don't use Charles for the demo."),
            ("Priya", "Feature freeze Thursday 4pm. After that, bug fixes only. Demo path is map, book, Slack ping, QR check-in."),
            ("Jordan", "I'll freeze visual tweaks after freeze unless Riley finds a contrast fail."),
            ("Riley", "I'll sign off contrast by Thursday noon."),
            ("Amira", "I'll keep Redis on and add a /health that shows cache hit rate so we know if staging went cold."),
            ("Priya", "New board items: check-in API, keyboard tab order, health cache metric. Calendar OAuth still not on Friday's path."),
            ("Kenji", "I'll add a fallback screenshot in the deck if the phone camera fails in the room."),
            ("Priya", "Yes, one screenshot only — we still try live first. Thanks, that's twenty-six minutes."),
        ],
        "summary": "Mid-week review (26 min). Live map books with 409 on overlap. Redis stays on. POST /check-in due today. Feature freeze Thursday 4pm. Keyboard tab order and staging cert called out.",
        "action_items": [
            "Amira: land POST /check-in; keep Redis on; /health cache hit rate.",
            "Jordan: refresh map on window focus; freeze visuals after Thursday 4pm.",
            "Riley: keyboard tab order; contrast sign-off Thursday noon; extend QA script.",
            "Kenji: device check-in on office wifi; fallback screenshot in the deck.",
        ],
        "key_decisions": [
            "Feature freeze Thursday 16:00; bugs only after that.",
            "Demo path is map → book → Slack → QR check-in.",
            "Redis cache stays enabled for the demo.",
        ],
    },
    {
        "title": "QR check-in dry run on staging",
        "description": "Device check-in against POST /check-in, plaque tokens, and failure states.",
        "days_ago": 2,
        "duration_min": 24,
        "lines": [
            ("Priya", "Check-in dry run. Twenty to twenty-five minutes. Kenji has the phone, Amira is on staging logs."),
            ("Kenji", "Camera opens, plaque v1 QR decodes, we send booking_id and plaque_token. First scan returned 200 present. Second scan 409 already checked in. Good."),
            ("Amira", "Logs match. 403 when I used Jordan's token on Priya's booking. Error body is code plus message, not a stack trace."),
            ("Riley", "iOS copy for 403 and 409 matches Figma. 500 still shows a generic sorry — that's fine for MVP."),
            ("Jordan", "Map flipped the desk to occupied about four seconds after check-in because of the focus refresh. I'll also poll at 8 seconds during demo."),
            ("Priya", "Don't poll every second. Eight is enough."),
            ("Kenji", "Office wifi was fine. Cellular to staging failed once on a captive portal. Demo room should be on office wifi."),
            ("Priya", "I'll ask facilities for the guest SSID in the room. We will not rely on cellular."),
            ("Riley", "QA script now covers 200, 403, 409, and unknown QR. Unknown QR should not crash the camera session — Kenji, it relaunched on me once."),
            ("Kenji", "That's a AVFoundation teardown bug. I'll keep the session alive on decode failure. Fix today."),
            ("Amira", "plaque_token is a signed desk id, 24 hour TTL. I'll mint demo tokens Thursday morning so they don't expire mid-pitch."),
            ("Priya", "Put a calendar reminder. Expired tokens would kill the live scan."),
            ("Jordan", "Drawer now says 'Checked in' not just occupied. Riley, is that label ok?"),
            ("Riley", "Yes. Use sentence case. I'll tweak the Figma."),
            ("Amira", "Slack still fires on book, not on check-in. Do we want a second ping?"),
            ("Priya", "No. One Slack ping on book is enough. Check-in is visual on the map."),
            ("Kenji", "Fallback screenshot is in the deck slide 7 if the camera is blocked."),
            ("Riley", "I'll sit in the room tomorrow and tap through VoiceOver on the map for five minutes."),
            ("Priya", "Thank you. Dry run passed aside from the camera teardown. Twenty-four minutes. See you at rehearsal."),
            ("Amira", "I'll watch staging error rate after Kenji's camera fix lands."),
        ],
        "summary": "QR dry run (24 min). Check-in 200/403/409 work. Camera session must survive a bad QR. Demo tokens minted Thursday morning. Slack stays book-only. Use office wifi in the room.",
        "action_items": [
            "Kenji: keep camera session alive on decode failure.",
            "Amira: mint plaque tokens Thursday morning; watch error rate.",
            "Priya: confirm guest SSID in the demo room.",
            "Riley: VoiceOver pass on the map.",
            "Jordan: 8s poll during demo; Checked in label.",
        ],
        "key_decisions": [
            "No Slack ping on check-in; map state is enough.",
            "Demo uses office/guest wifi, not cellular.",
            "Plaque tokens are minted the morning of the demo.",
        ],
    },
    {
        "title": "Friday demo rehearsal",
        "description": "Timed dry-run of map booking, Slack ping, and QR check-in before stakeholders.",
        "days_ago": 1,
        "duration_min": 30,
        "lines": [
            ("Priya", "Rehearsal. We will run the real demo path at full length, about thirty minutes including buffer and Q and A practice."),
            ("Priya", "Script: I intro PulseDesk for two minutes. Jordan books a desk on the map. We wait for Slack. Kenji scans. Riley narrates a11y. Then questions."),
            ("Jordan", "I'll use desk 3F-12. It is free on staging. If it is taken I'll switch to 3F-18. I will not scroll wildly on the projector."),
            ("Amira", "Staging Redis is warm. /health shows hits. Slack webhook tested ten minutes ago. I am on the laptop in case we need a restart."),
            ("Kenji", "Phone is charged, camera fix is on TestFlight, tokens were minted this morning. Fallback screenshot is last resort."),
            ("Riley", "I'll stand left of the screen and only talk after check-in succeeds. Contrast and keyboard tab order are signed off."),
            ("Priya", "Let's time a full pass. Starting now. PulseDesk helps the downtown office book a desk on the third floor without a spreadsheet."),
            ("Jordan", "Selecting 3F-12, nine-thirty slot, confirm. Drawer says booked. Waiting for map refresh."),
            ("Amira", "Slack landed in #pulsedesk-demo. Booking id is on the screen if judges ask."),
            ("Kenji", "Scanning. Present. Map should show checked in."),
            ("Jordan", "Label updated. Polling worked."),
            ("Riley", "Keyboard can reach 3F-12 and the confirm button. Status is also in text, not only color."),
            ("Priya", "That's the happy path. Now a question we will get: what if two people book the same desk?"),
            ("Amira", "I'll answer: unique index, 409, UI error. We can show it if they insist, but we don't do it live unless asked."),
            ("Priya", "Calendar question: we do not have Google Calendar yet. Answer: parked, PulseDesk holds only, coming next sprint."),
            ("Kenji", "If camera fails I show slide 7 and describe the 200. I will not fumble Settings."),
            ("Jordan", "If the map is stale I'll click the window to force refresh. I practiced that twice."),
            ("Priya", "Run the failure line once: Kenji, scan a wrong QR."),
            ("Kenji", "Unknown QR, session stayed up, message is try another plaque. Good."),
            ("Riley", "VoiceOver still reads desk id and status. I'll be in the room early to set speaker volume."),
            ("Priya", "Rehearsal passed. Total time with Q and A practice is thirty minutes. Tomorrow we start on time, no new features. Thank you."),
            ("Amira", "I'll snapshot staging after this so overnight deploys don't surprise us."),
            ("Priya", "No deploys after 8pm. Feature freeze still holds. See you in the demo room."),
        ],
        "summary": "Friday rehearsal (30 min). Happy path timed: intro, book 3F-12, Slack, QR present, a11y note. Failure QR handled. Calendar answer is parked. No deploys after 8pm.",
        "action_items": [
            "Amira: snapshot staging; no deploys after 20:00.",
            "Jordan: use 3F-12 or 3F-18; window-focus refresh if stale.",
            "Kenji: TestFlight build; slide 7 only if camera fails.",
            "Riley: arrive early; VoiceOver and volume check.",
            "Priya: run the script; Calendar answer is next sprint.",
        ],
        "key_decisions": [
            "Demo desk is 3F-12 with 3F-18 backup.",
            "No production or staging deploys after 20:00 the night before.",
            "Do not live-demo double-book unless a judge asks.",
        ],
    },
]


async def _get_or_create_user(email: str, name: str, skills: list[str]) -> User:
    user = await User.find_one(User.email == email, User.deleted_at == None)
    if user:
        user.name = name
        user.skills = skills
        if not user.password_hash:
            user.password_hash = hash_password(DEFAULT_PASSWORD)
        await user.save()
        return user
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(DEFAULT_PASSWORD),
        auth_provider=AuthProvider.CREDENTIALS,
        skills=skills,
        created_by="seed",
    )
    await user.insert()
    print(f"Created user {name} <{email}>")
    return user


def _chunks(lines: list[tuple[str, str]], started: datetime, duration_min: int) -> list[TranscriptChunk]:
    n = max(len(lines), 1)
    span = max(duration_min, 20) * 60
    step = span / max(n - 1, 1)
    chunks: list[TranscriptChunk] = []
    for i, (speaker, text) in enumerate(lines):
        offset = int(i * step) if n > 1 else 0
        chunks.append(
            TranscriptChunk(
                chunk_id=str(uuid.uuid4()),
                speaker=speaker,
                text=f"{speaker}: {text}",
                timestamp=started + timedelta(seconds=offset),
                audio_offset_ms=offset * 1000,
                source="seed",
            )
        )
    return chunks


async def _upsert_meeting(
    *,
    ws: Workspace,
    lead: User,
    members: dict[str, User],
    spec: dict,
    now: datetime,
) -> Meeting:
    duration = int(spec["duration_min"])
    started = now - timedelta(days=int(spec["days_ago"]), hours=2)
    ended = started + timedelta(minutes=duration)
    attendees = [
        MeetingAttendee(
            user_id=u.id,
            speaker_label=u.name.split()[0],
            join_time=started,
            leave_time=ended,
        )
        for u in members.values()
    ]
    meeting = await Meeting.find_one(
        Meeting.workspace_id == ws.id,
        Meeting.title == spec["title"],
        Meeting.deleted_at == None,
    )
    fields = dict(
        description=spec["description"],
        platform=MeetingPlatform.JITSI,
        status=MeetingStatus.ENDED,
        scheduled_at=started,
        started_at=started,
        ended_at=ended,
        duration=duration,
        transcript_chunks=_chunks(spec["lines"], started, duration),
        summary=spec["summary"],
        action_items=spec["action_items"],
        key_decisions=spec["key_decisions"],
        attendees=attendees,
    )
    if meeting:
        for key, value in fields.items():
            setattr(meeting, key, value)
        await meeting.save()
        print(f"Updated meeting ({duration} min, {len(spec['lines'])} turns): {spec['title']}")
        return meeting
    meeting = Meeting(workspace_id=ws.id, title=spec["title"], created_by=str(lead.id), **fields)
    await meeting.insert()
    print(f"Created meeting ({duration} min, {len(spec['lines'])} turns): {spec['title']}")
    return meeting


async def seed() -> None:
    await init_models()
    now = datetime.now(timezone.utc)

    lead = await _get_or_create_user(*LEAD)
    members: dict[str, User] = {LEAD[0]: lead}
    for email, name, skills in TEAM:
        members[email] = await _get_or_create_user(email, name, skills)

    ws = await Workspace.find_one(Workspace.slug == WORKSPACE_SLUG, Workspace.deleted_at == None)
    if not ws:
        ws = Workspace(
            name=WORKSPACE_NAME,
            slug=WORKSPACE_SLUG,
            invite_code=hash_password(INVITE_CODE),
            invite_code_raw=INVITE_CODE,
            created_by=str(lead.id),
            members=[],
        )
        await ws.insert()
        print(f"Created workspace {WORKSPACE_NAME}")

    roster: list[WorkspaceMember] = [
        WorkspaceMember(user_id=lead.id, role=WorkspaceRole.LEAD, invited_by=lead.id),
    ]
    for email, _name, _skills in TEAM:
        roster.append(
            WorkspaceMember(
                user_id=members[email].id,
                role=WorkspaceRole.MEMBER,
                invited_by=lead.id,
            )
        )
    ws.name = WORKSPACE_NAME
    ws.members = roster
    await ws.save()

    meetings_by_title: dict[str, Meeting] = {}
    for spec in MEETINGS:
        meetings_by_title[spec["title"]] = await _upsert_meeting(
            ws=ws, lead=lead, members=members, spec=spec, now=now
        )

    kickoff = meetings_by_title[MEETINGS[0]["title"]]
    day2 = meetings_by_title[MEETINGS[1]["title"]]
    midweek = meetings_by_title[MEETINGS[2]["title"]]
    dry_run = meetings_by_title[MEETINGS[3]["title"]]
    rehearsal = meetings_by_title[MEETINGS[4]["title"]]

    demo_tasks = [
        {
            "title": "Third-floor map UI with live desk status",
            "description": "React SVG map; green = free, amber = held, grey = occupied. Uses GET /desks from the kickoff.",
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.HIGH,
            "email": "jordan@pulsedesk.demo",
            "due": now + timedelta(days=2),
            "evidence": "Jordan: I'll render the third-floor SVG in React.",
            "meeting": kickoff,
        },
        {
            "title": "Booking conflict detection API",
            "description": "POST /bookings must reject overlapping holds on the same desk for the MVP.",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.HIGH,
            "email": "amira@pulsedesk.demo",
            "due": now - timedelta(days=1),
            "evidence": "Amira: POST /bookings will reject overlapping holds on the same desk.",
            "meeting": kickoff,
        },
        {
            "title": "Slack notify on successful booking",
            "description": "Ping the booker and floor channel when a desk is confirmed.",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.MEDIUM,
            "email": "amira@pulsedesk.demo",
            "due": now - timedelta(days=1),
            "evidence": "Amira: Slack notify on success is already drafted.",
            "meeting": kickoff,
        },
        {
            "title": "iOS QR check-in against POST /check-in",
            "description": "Scan desk plaque QR; only the booking owner is marked present.",
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.HIGH,
            "email": "kenji@pulsedesk.demo",
            "due": now + timedelta(days=1),
            "evidence": "Kenji: iOS will scan the plaque QR and call POST /check-in.",
            "meeting": kickoff,
        },
        {
            "title": "Figma map + booking drawer states",
            "description": "Map, drawer, empty and error states for Jordan and Kenji.",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.MEDIUM,
            "email": "riley@pulsedesk.demo",
            "due": now - timedelta(days=2),
            "evidence": "Riley: Figma is almost ready: map, booking drawer, empty and error.",
            "meeting": kickoff,
        },
        {
            "title": "Unknown desk status renders grey",
            "description": "Never show a desk as free when GET /desks returns an unknown status.",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.MEDIUM,
            "email": "jordan@pulsedesk.demo",
            "due": now - timedelta(days=3),
            "evidence": "Jordan: If status is a string, I'll treat unknown as grey not green.",
            "meeting": day2,
        },
        {
            "title": "CORS for Vite and staging frontend",
            "description": "Allow local Vite and staging origin so the map can call the API.",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.HIGH,
            "email": "amira@pulsedesk.demo",
            "due": now - timedelta(days=3),
            "evidence": "Amira: I'll allow both origins after this call.",
            "meeting": day2,
        },
        {
            "title": "Accessibility and overlapping-booking QA script",
            "description": "Contrast pass on the map plus a script that double-books the same desk.",
            "status": TaskStatus.IN_REVIEW,
            "priority": TaskPriority.MEDIUM,
            "email": "riley@pulsedesk.demo",
            "due": now + timedelta(days=1),
            "evidence": "Riley: I'll add that to the QA script: unknown status, 409 on double book, empty floor.",
            "meeting": day2,
        },
        {
            "title": "Land POST /check-in on staging",
            "description": "200 present, 409 already checked in, 403 not owner.",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.URGENT,
            "email": "amira@pulsedesk.demo",
            "due": now - timedelta(days=2),
            "evidence": "Amira: I'll land POST /check-in today. Body is booking_id plus plaque_token.",
            "meeting": midweek,
        },
        {
            "title": "Keyboard tab order on the floor map",
            "description": "Desks and confirm must be reachable without a pointer.",
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.HIGH,
            "email": "riley@pulsedesk.demo",
            "due": now + timedelta(days=1),
            "evidence": "Riley: Keyboard focus on desks is still weak — tab order jumps.",
            "meeting": midweek,
        },
        {
            "title": "Keep camera session alive on bad QR",
            "description": "Unknown plaque must not tear down AVFoundation.",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.HIGH,
            "email": "kenji@pulsedesk.demo",
            "due": now - timedelta(days=1),
            "evidence": "Kenji: I'll keep the session alive on decode failure. Fix today.",
            "meeting": dry_run,
        },
        {
            "title": "Mint plaque tokens Thursday morning",
            "description": "24-hour signed desk tokens so the live scan does not expire mid-pitch.",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.HIGH,
            "email": "amira@pulsedesk.demo",
            "due": now + timedelta(days=1),
            "evidence": "Amira: I'll mint demo tokens Thursday morning so they don't expire mid-pitch.",
            "meeting": dry_run,
        },
        {
            "title": "Google Calendar OAuth for map conflicts",
            "description": "Blocked: Calendar OAuth is not approved; keep off the MVP critical path per Priya.",
            "status": TaskStatus.BLOCKERS,
            "priority": TaskPriority.URGENT,
            "email": "jordan@pulsedesk.demo",
            "due": now + timedelta(days=5),
            "evidence": "Priya: Calendar question: we do not have Google Calendar yet.",
            "blocker": "Calendar OAuth app review pending — map will show PulseDesk bookings only until then.",
            "meeting": rehearsal,
        },
        {
            "title": "Stakeholder demo script for Friday",
            "description": "Walk through map → book 3F-12 → Slack ping → QR check-in. Priya presents.",
            "status": TaskStatus.IN_REVIEW,
            "priority": TaskPriority.HIGH,
            "email": "priya@pulsedesk.demo",
            "due": now + timedelta(days=1),
            "evidence": "Priya: Script: I intro PulseDesk for two minutes. Jordan books a desk on the map.",
            "meeting": rehearsal,
        },
        {
            "title": "Snapshot staging; no deploys after 20:00",
            "description": "Freeze staging overnight so rehearsal state is what judges see.",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.HIGH,
            "email": "amira@pulsedesk.demo",
            "due": now + timedelta(hours=12),
            "evidence": "Amira: I'll snapshot staging after this so overnight deploys don't surprise us.",
            "meeting": rehearsal,
        },
    ]

    for spec in demo_tasks:
        existing = await Task.find_one(
            Task.workspace_id == ws.id,
            Task.title == spec["title"],
            Task.deleted_at == None,
        )
        meeting = spec["meeting"]
        user = members[spec["email"]]
        if existing:
            existing.meeting_id = meeting.id
            existing.source_meeting_id = meeting.id
            existing.status = spec["status"]
            existing.assignee = user.id
            existing.assignee_name = user.name
            existing.evidence = spec["evidence"]
            existing.blocker_reason = spec.get("blocker")
            existing.synced_from_meeting_ids = [str(meeting.id)]
            await existing.save()
            continue
        task = Task(
            workspace_id=ws.id,
            meeting_id=meeting.id,
            source_meeting_id=meeting.id,
            title=spec["title"],
            description=spec["description"],
            assignee=user.id,
            assignee_name=user.name,
            status=spec["status"],
            priority=spec["priority"],
            due_date=spec["due"],
            due_date_source="transcript",
            task_key=generate_task_key(),
            is_auto_generated=True,
            confidence=0.92,
            evidence=spec["evidence"],
            blocker_reason=spec.get("blocker"),
            synced_from_meeting_ids=[str(meeting.id)],
            last_activity_at=now,
            created_by=str(lead.id),
        )
        await task.insert()
        print(f"Created task [{spec['status'].value}] {spec['title']} → {user.name}")

    print("\nPulseDesk seed complete.")
    print(f"  {len(MEETINGS)} transcribed meetings (22–30 min each)")
    print(f"  Manager login: {LEAD[0]} / {DEFAULT_PASSWORD}")


async def main() -> None:
    try:
        await seed()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
