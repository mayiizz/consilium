import { useState } from "react";
import { Sparkles, X, Send, ThumbsUp, ThumbsDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { sendCopilotMessage, sendCopilotFeedback, getCopilotHistory } from "@/lib/api/services/copilot";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function Copilot({ workspaceId }: { workspaceId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: "user" | "ai"; text: string; id?: string }>>([
    { role: "ai", text: "Hi! I'm Consilium Copilot. Ask me about meetings, tasks, or risks." },
  ]);

  useEffect(() => {
    if (open && workspaceId) {
      getCopilotHistory(workspaceId).then((history) => {
        if (history.length > 0) {
          setMessages(history.map((m) => ({
            role: m.role === "assistant" ? "ai" as const : "user" as const,
            text: m.content,
            id: m.message_id,
          })));
        }
      }).catch(() => {});
    }
  }, [open, workspaceId]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input;
    setMessages((m) => [...m, { role: "user", text: userMsg }]);
    setInput("");
    setLoading(true);
    try {
      const res = await sendCopilotMessage(workspaceId, userMsg);
      if (res.kanban_refresh) {
        qc.invalidateQueries({ queryKey: ["tasks", workspaceId] });
        qc.invalidateQueries({ queryKey: ["kanban-review", workspaceId] });
      }
      setMessages((m) => [...m, { role: "ai", text: res.content, id: res.message_id }]);
    } catch {
      setMessages((m) => [...m, { role: "ai", text: "Sorry, I couldn't process that request. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const feedback = async (messageId: string, up: boolean) => {
    try {
      await sendCopilotFeedback(workspaceId, messageId, up ? "up" : "down");
    } catch {}
  };

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full gradient-primary shadow-glow transition-transform hover:scale-110",
          open && "scale-90"
        )}
        aria-label="Open Copilot"
      >
        {open ? <X className="text-white" /> : <Sparkles className="text-white" />}
      </button>
      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[480px] w-[380px] flex-col overflow-hidden rounded-3xl glass-card shadow-elevated animate-scale-in">
          <div className="flex items-center gap-2 border-b border-border/60 p-4">
            <div className="h-8 w-8 gradient-primary rounded-lg flex items-center justify-center">
              <Sparkles size={16} className="text-white" />
            </div>
            <div>
              <div className="text-sm font-semibold">Copilot</div>
              <div className="text-[11px] text-muted-foreground">Powered by Consilium AI</div>
            </div>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((m, i) => (
              <div key={i} className={cn("flex flex-col", m.role === "user" ? "items-end" : "items-start")}>
                <div
                  className={cn(
                    "max-w-[80%] rounded-2xl px-3 py-2 text-sm",
                    m.role === "user" ? "gradient-primary text-white" : "bg-muted text-foreground"
                  )}
                >
                  {m.text}
                </div>
                {m.role === "ai" && m.id && (
                  <div className="mt-1 flex gap-1">
                    <button onClick={() => feedback(m.id!, true)} className="p-1 text-muted-foreground hover:text-foreground"><ThumbsUp size={12} /></button>
                    <button onClick={() => feedback(m.id!, false)} className="p-1 text-muted-foreground hover:text-foreground"><ThumbsDown size={12} /></button>
                  </div>
                )}
              </div>
            ))}
            {loading && <div className="text-xs text-muted-foreground">Thinking…</div>}
          </div>
          <div className="flex gap-2 border-t border-border/60 p-3">
            <Input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask anything…" className="rounded-xl" />
            <Button size="icon" className="gradient-primary rounded-xl" onClick={send} disabled={loading}><Send size={14} /></Button>
          </div>
        </div>
      )}
    </>
  );
}
