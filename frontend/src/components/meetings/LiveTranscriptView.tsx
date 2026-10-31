import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { TranscriptLine } from "@/lib/types";

const SPEAKER_PALETTES = [
  "from-sky-500 to-cyan-600",
  "from-teal-500 to-emerald-600",
  "from-blue-500 to-indigo-600",
  "from-cyan-600 to-blue-600",
  "from-slate-500 to-slate-700",
  "from-amber-500 to-orange-600",
];

function speakerTone(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return SPEAKER_PALETTES[hash % SPEAKER_PALETTES.length];
}

function formatOffset(t: number): string {
  if (!Number.isFinite(t) || t < 0) return "";
  const total = Math.floor(t);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function LiveTranscriptView({
  lines,
  emptyLabel = "No transcript yet.",
  className,
}: {
  lines: TranscriptLine[];
  emptyLabel?: string;
  className?: string;
}) {
  const speakerColors = useMemo(() => {
    const map = new Map<string, string>();
    for (const line of lines) {
      const speaker = line.speaker?.trim();
      if (speaker && !map.has(speaker)) map.set(speaker, speakerTone(speaker));
    }
    return map;
  }, [lines]);

  if (!lines.length) {
    return (
      <div className="flex min-h-[180px] flex-col items-center justify-center gap-2 text-center">
        <div className="h-10 w-10 rounded-2xl bg-primary/10 grid place-items-center">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/50 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
          </span>
        </div>
        <p className="text-sm text-muted-foreground">{emptyLabel}</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {lines.map((line, i) => {
        const speaker = line.speaker?.trim();
        const tone = speaker ? speakerColors.get(speaker) : undefined;
        const time = formatOffset(line.t);
        return (
          <div
            key={`${line.t}-${i}-${line.text.slice(0, 24)}`}
            className="animate-slide-up flex gap-3 rounded-2xl border border-border/50 bg-card/70 px-3 py-2.5 shadow-card"
            style={{ animationDelay: `${Math.min(i, 8) * 30}ms` }}
          >
            <div
              className={cn(
                "mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br text-[11px] font-bold text-white",
                tone ?? "from-slate-400 to-slate-600",
              )}
            >
              {(speaker || "?")[0]?.toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="mb-0.5 flex items-baseline gap-2">
                {speaker ? (
                  <span className="text-xs font-semibold tracking-tight text-foreground">{speaker}</span>
                ) : (
                  <span className="text-xs font-medium text-muted-foreground">Unknown</span>
                )}
                {time ? <span className="font-mono text-[10px] text-muted-foreground/80">{time}</span> : null}
              </div>
              <p className="text-sm leading-relaxed text-foreground/90">{line.text}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
