import type { Meeting } from "@/lib/types";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { safeFormatDate } from "@/lib/safe-dates";

function AttendeeRow({ p, status }: { p: Meeting["participants"][0]; status: "present" | "left" }) {
  return (
    <div className="flex items-center gap-3">
      <Avatar className="h-7 w-7">
        <AvatarImage src={p.avatar} />
        <AvatarFallback>{p.name[0]}</AvatarFallback>
      </Avatar>
      <div>
        <div className="text-sm font-medium">{p.name}</div>
        <div className="text-xs text-muted-foreground">
          {p.joinTime ? `Joined ${safeFormatDate(p.joinTime, "HH:mm:ss")}` : "Not joined"}
          {status === "left" && p.leaveTime
            ? ` · Left ${safeFormatDate(p.leaveTime, "HH:mm:ss")}`
            : status === "present" && p.joinTime
              ? " · Present"
              : ""}
        </div>
      </div>
    </div>
  );
}

export function MeetingAttendanceTab({ meeting }: { meeting: Meeting }) {
  const present = meeting.participants.filter((p) => p.joinTime && !p.leaveTime);
  const left = meeting.participants.filter((p) => p.leaveTime);

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Tracks workspace members viewing this page — not external meeting guests.
      </p>
      {present.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Present</h4>
          <div className="space-y-3">
            {present.map((p) => (
              <AttendeeRow key={p.id} p={p} status="present" />
            ))}
          </div>
        </div>
      )}
      {left.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Left</h4>
          <div className="space-y-3">
            {left.map((p) => (
              <AttendeeRow key={p.id} p={p} status="left" />
            ))}
          </div>
        </div>
      )}
      {present.length === 0 && left.length === 0 && (
        <p className="text-sm text-muted-foreground">No attendees recorded.</p>
      )}
    </div>
  );
}
