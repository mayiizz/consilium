import { useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { MarkdownPreview } from "@/components/documents/MarkdownPreview";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DOCUMENT_TYPE_LABELS } from "@/lib/constants";
import { useDocuments } from "@/lib/api/hooks/useAnalytics";
import { uploadDocument } from "@/lib/api/services/analytics";
import { previewDocument } from "@/lib/api/services/research";
import { API_BASE, formatApiError, getAccessToken } from "@/lib/api/client";
import { FileText, Download, Eye, Search, Upload, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import type { Document } from "@/lib/types";

export function DocumentsPage({
  workspaceId,
  role,
}: {
  workspaceId: string;
  role: "manager" | "member";
}) {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const { data: allDocs = [], isLoading } = useDocuments(workspaceId);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
  const [previewText, setPreviewText] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);

  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(workspaceId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", workspaceId] });
      toast.success("Document uploaded — text is available for RAG / Kanban context");
    },
    onError: (err) => toast.error(formatApiError(err, "Upload failed")),
  });

  const docs = useMemo(() => {
    const q = query.toLowerCase().trim();
    if (!q) return allDocs;
    return allDocs.filter((d) => d.title.toLowerCase().includes(q) || d.author.toLowerCase().includes(q));
  }, [query, allDocs]);

  const downloadDocument = (id: string) => {
    const token = getAccessToken();
    void (async () => {
      try {
        const res = await fetch(`${API_BASE}/documents/${id}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error("Download failed");
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        window.open(objectUrl, "_blank", "noopener,noreferrer");
        setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
      } catch {
        toast.error("Could not download document");
      }
    })();
  };

  const openPreview = async (doc: Document) => {
    setPreviewDoc(doc);
    setPreviewOpen(true);
    setPreviewText("");
    setPreviewLoading(true);
    try {
      const preview = await previewDocument(doc.id);
      if (preview.text.trim()) {
        setPreviewText(preview.text);
      } else {
        // Fallback: open raw download for binary docs
        setPreviewOpen(false);
        downloadDocument(doc.id);
      }
    } catch {
      setPreviewOpen(false);
      downloadDocument(doc.id);
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <DashboardLayout role={role} workspaceId={workspaceId}>
      <PageHeader
        title="Documents"
        description="Shared specs and notes (any format). Extracted text feeds RAG when automating the Kanban board."
        actions={
          <>
            <input
              ref={fileRef}
              type="file"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload.mutate(file);
                e.target.value = "";
              }}
            />
            <Button
              size="sm"
              className="gradient-primary rounded-xl"
              disabled={upload.isPending}
              onClick={() => fileRef.current?.click()}
            >
              {upload.isPending ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
              {upload.isPending ? "Uploading…" : "Upload document"}
            </Button>
          </>
        }
      />
      <div className="mb-6 relative max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search documents…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="rounded-xl pl-9"
        />
      </div>
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading documents…</p>
      ) : docs.length === 0 ? (
        <Card className="glass-card p-12 text-center">
          <p className="text-muted-foreground">No documents yet. Upload a .txt or .md file to get started.</p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {docs.map((d) => (
            <Card key={d.id} className="glass-card hover-lift p-5">
              <div className="flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl gradient-primary">
                  <FileText className="text-white" size={18} />
                </div>
                <Badge variant="outline" className="rounded-full text-[10px]">
                  {DOCUMENT_TYPE_LABELS[d.type] ?? d.type}
                </Badge>
              </div>
              <h3 className="mt-3 font-semibold">{d.title}</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                {d.author} · {d.size} · {formatDistanceToNow(d.updatedAt, { addSuffix: true })}
              </p>
              <div className="mt-4 flex gap-2">
                <Button size="sm" variant="outline" className="flex-1 rounded-xl" onClick={() => openPreview(d)}>
                  <Eye size={14} /> Preview
                </Button>
                <Button size="sm" variant="ghost" className="rounded-xl" onClick={() => downloadDocument(d.id)}>
                  <Download size={14} />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{previewDoc?.title ?? "Document"}</DialogTitle>
          </DialogHeader>
          {previewLoading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 size={16} className="animate-spin" /> Loading…
            </div>
          ) : previewDoc?.type === "research" ||
            previewDoc?.title.toLowerCase().endsWith(".md") ||
            previewText.includes("\n## ") ? (
            <MarkdownPreview markdown={previewText} />
          ) : (
            <pre className="whitespace-pre-wrap break-words rounded-xl bg-muted/40 p-4 text-sm leading-relaxed">
              {previewText || "No text preview available."}
            </pre>
          )}
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
}
