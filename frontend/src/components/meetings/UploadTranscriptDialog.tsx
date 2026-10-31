import { useRef, useState } from "react";
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
import { useMeetingMutations } from "@/lib/api/hooks/useMeetingMutations";
import { formatApiError } from "@/lib/api/client";
import { Loader2, Upload } from "lucide-react";
import { toast } from "sonner";

interface UploadTranscriptDialogProps {
  workspaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** When set, upload into this meeting instead of creating a new one. */
  meetingId?: string;
  meetingTitle?: string;
}

export function UploadTranscriptDialog({
  workspaceId,
  open,
  onOpenChange,
  meetingId,
  meetingTitle,
}: UploadTranscriptDialogProps) {
  const navigate = useNavigate();
  const { create, upload } = useMeetingMutations(workspaceId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState(meetingTitle ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const reset = () => {
    setTitle(meetingTitle ?? "");
    setFile(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const onSubmit = async () => {
    if (!file) {
      toast.error("Choose a file to upload");
      return;
    }
    const name = title.trim() || file.name.replace(/\.[^.]+$/, "") || "Uploaded meeting";
    setBusy(true);
    try {
      let targetId = meetingId;
      if (!targetId) {
        const meeting = await create.mutateAsync({
          title: name,
          description: `Uploaded: ${file.name}`,
          meeting_type: "instant",
          platform: "custom",
          generate_link: false,
        });
        targetId = meeting.id;
      }
      const result = await upload.mutateAsync({ meetingId: targetId, file });
      toast.success(
        "File processed — summary and Kanban automation are running. Check the board for new tasks.",
      );
      onOpenChange(false);
      reset();
      navigate({
        to: "/business/manager/workspaces/$workspaceId/meeting/$meetingId",
        params: { workspaceId, meetingId: result.id },
      });
    } catch (err) {
      toast.error(formatApiError(err, "Upload failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v);
        if (!v) reset();
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Upload meeting file</DialogTitle>
          <DialogDescription>
            Upload a text transcript (.txt, .md, .vtt, .srt), PDF, or DOCX. Live speech uses the
            browser Web Speech API (Chrome/Edge) when you Start a meeting — audio/video files are
            not transcribed with Whisper.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 pt-1">
          {!meetingId && (
            <div>
              <Label className="text-xs text-muted-foreground">Meeting title</Label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Sprint review notes"
                className="rounded-xl mt-1"
              />
            </div>
          )}
          <div>
            <Label className="text-xs text-muted-foreground">File</Label>
            <Input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.markdown,.csv,.vtt,.srt,.pdf,.docx,text/plain,application/pdf"
              className="rounded-xl mt-1 cursor-pointer"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file && (
              <p className="mt-1 text-xs text-muted-foreground">
                {file.name} · {(file.size / 1024).toFixed(1)} KB
              </p>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button className="gradient-primary" onClick={onSubmit} disabled={busy || !file}>
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            {busy ? "Processing…" : "Upload & automate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
