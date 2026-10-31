import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useMeetingMutations } from "@/lib/api/hooks/useMeetingMutations";
import { formatApiError } from "@/lib/api/client";
import type { MeetingPlatform } from "@/lib/types";
import { toast } from "sonner";

const PLATFORMS: { value: MeetingPlatform; label: string }[] = [
  { value: "jitsi", label: "Jitsi" },
  { value: "google_meet", label: "Google Meet" },
  { value: "zoom", label: "Zoom" },
  { value: "teams", label: "Teams" },
  { value: "custom", label: "Custom" },
];

interface NewMeetingDialogProps {
  workspaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: "instant" | "scheduled";
}

export function NewMeetingDialog({
  workspaceId,
  open,
  onOpenChange,
  defaultTab = "instant",
}: NewMeetingDialogProps) {
  const navigate = useNavigate();
  const { create } = useMeetingMutations(workspaceId);
  const [tab, setTab] = useState<"instant" | "scheduled">(defaultTab);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [platform, setPlatform] = useState<MeetingPlatform>("jitsi");
  const [meetingLink, setMeetingLink] = useState("");
  const [useOwnLink, setUseOwnLink] = useState(false);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");

  const reset = () => {
    setTitle("");
    setDescription("");
    setPlatform("jitsi");
    setMeetingLink("");
    setUseOwnLink(false);
    setDate("");
    setTime("");
  };

  const onSubmit = async () => {
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    if (tab === "scheduled" && (!date || !time)) {
      toast.error("Date and time are required for scheduled meetings");
      return;
    }
    if (useOwnLink && !meetingLink.trim()) {
      toast.error("Meeting link is required");
      return;
    }

    let scheduled_at: string | undefined;
    if (tab === "scheduled") {
      scheduled_at = new Date(`${date}T${time}`).toISOString();
    }

    const generate_link = platform === "jitsi" && !useOwnLink;
    const video_link = useOwnLink ? meetingLink.trim() : undefined;

    try {
      const meeting = await create.mutateAsync({
        title: title.trim(),
        description: description.trim() || undefined,
        platform,
        meeting_type: tab,
        video_link,
        scheduled_at,
        generate_link,
      });
      toast.success("Meeting created");
      onOpenChange(false);
      reset();
      navigate({
        to: "/business/manager/workspaces/$workspaceId/meeting/$meetingId",
        params: { workspaceId, meetingId: meeting.id },
      });
    } catch (err) {
      toast.error(formatApiError(err, "Could not create meeting"));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>New meeting</DialogTitle>
          <DialogDescription>Start instantly or schedule for later.</DialogDescription>
        </DialogHeader>
        <Tabs value={tab} onValueChange={(v) => setTab(v as "instant" | "scheduled")}>
          <TabsList className="w-full">
            <TabsTrigger value="instant" className="flex-1">Instant</TabsTrigger>
            <TabsTrigger value="scheduled" className="flex-1">Scheduled</TabsTrigger>
          </TabsList>
          <TabsContent value="instant" className="space-y-4 pt-2">
            <Field label="Title" value={title} onChange={setTitle} placeholder="Sprint planning" />
            <Field label="Description" value={description} onChange={setDescription} placeholder="Optional" />
            <PlatformFields
              platform={platform}
              setPlatform={setPlatform}
              useOwnLink={useOwnLink}
              setUseOwnLink={setUseOwnLink}
              meetingLink={meetingLink}
              setMeetingLink={setMeetingLink}
            />
          </TabsContent>
          <TabsContent value="scheduled" className="space-y-4 pt-2">
            <Field label="Title" value={title} onChange={setTitle} placeholder="Weekly sync" />
            <Field label="Description" value={description} onChange={setDescription} placeholder="Optional" />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground">Date</Label>
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="rounded-xl mt-1" />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Time</Label>
                <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="rounded-xl mt-1" />
              </div>
            </div>
            <PlatformFields
              platform={platform}
              setPlatform={setPlatform}
              useOwnLink={useOwnLink}
              setUseOwnLink={setUseOwnLink}
              meetingLink={meetingLink}
              setMeetingLink={setMeetingLink}
            />
          </TabsContent>
        </Tabs>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="gradient-primary" onClick={onSubmit} disabled={create.isPending}>
            {tab === "instant" ? "Create & open" : "Schedule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-xl mt-1"
      />
    </div>
  );
}

function PlatformFields({
  platform,
  setPlatform,
  useOwnLink,
  setUseOwnLink,
  meetingLink,
  setMeetingLink,
}: {
  platform: MeetingPlatform;
  setPlatform: (p: MeetingPlatform) => void;
  useOwnLink: boolean;
  setUseOwnLink: (v: boolean) => void;
  meetingLink: string;
  setMeetingLink: (v: string) => void;
}) {
  return (
    <>
      <div>
        <Label className="text-xs text-muted-foreground">Platform</Label>
        <Select value={platform} onValueChange={(v) => setPlatform(v as MeetingPlatform)}>
          <SelectTrigger className="rounded-xl mt-1">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PLATFORMS.map((p) => (
              <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {platform === "jitsi" ? (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={useOwnLink} onChange={(e) => setUseOwnLink(e.target.checked)} />
          I have my own meeting link
        </label>
      ) : (
        <Field
          label="Meeting link"
          value={meetingLink}
          onChange={setMeetingLink}
          placeholder="https://meet.google.com/..."
        />
      )}
      {platform === "jitsi" && useOwnLink && (
        <Field
          label="Meeting link"
          value={meetingLink}
          onChange={setMeetingLink}
          placeholder="https://meet.jit.si/..."
        />
      )}
      {platform === "jitsi" && !useOwnLink && (
        <p className="text-xs text-muted-foreground">A Jitsi room will be auto-generated.</p>
      )}
    </>
  );
}
