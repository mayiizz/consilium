import type { Meeting, MeetingPlatform } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { safeFormatDate } from "@/lib/safe-dates";
import { Copy, ExternalLink } from "lucide-react";
import { toast } from "sonner";

const PLATFORM_LABELS: Record<MeetingPlatform, string> = {
  google_meet: "Google Meet",
  zoom: "Zoom",
  teams: "Teams",
  jitsi: "Jitsi",
  custom: "Custom",
};

function fmt(dt?: Date) {
  return safeFormatDate(dt, "EEE, MMM d · HH:mm");
}

function fmtDuration(seconds?: number) {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function MeetingInfoPanel({ meeting }: { meeting: Meeting }) {
  const url = meeting.meetingUrl ?? meeting.jitsiUrl;

  const copyLink = () => {
    if (!url) return;
    navigator.clipboard.writeText(url);
    toast.success("Link copied");
  };

  return (
    <Card className="glass-card mb-6 p-5">
      <h3 className="mb-4 font-semibold">Meeting info</h3>
      <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <InfoRow label="Platform" value={meeting.platform ? PLATFORM_LABELS[meeting.platform] : "—"} />
        <InfoRow label="Status" value={<StatusBadge status={meeting.status} />} />
        <InfoRow label="Started at" value={fmt(meeting.startedAt)} />
        <InfoRow label="Ended at" value={fmt(meeting.endedAt)} />
        <InfoRow label="Duration" value={fmtDuration(meeting.duration)} />
        <InfoRow label="Participants" value={String(meeting.participants.length)} />
        <InfoRow label="Transcript count" value={`${meeting.transcriptCount ?? 0} chunks`} />
        <div className="sm:col-span-2">
          <div className="text-xs text-muted-foreground">Meeting link</div>
          <div className="mt-1 flex items-center gap-2">
            <span className="truncate text-sm">{url ?? "—"}</span>
            {url && (
              <>
                <Button size="icon" variant="ghost" className="h-7 w-7 shrink-0" onClick={copyLink}>
                  <Copy size={14} />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7 shrink-0"
                  onClick={() => window.open(url, "_blank", "noopener,noreferrer")}
                >
                  <ExternalLink size={14} />
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-0.5 font-medium">{value}</div>
    </div>
  );
}
