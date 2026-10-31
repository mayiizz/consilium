import type { ReactNode } from "react";

/** Lightweight markdown → React for research / document previews (no extra deps). */
export function MarkdownPreview({ markdown }: { markdown: string }) {
  const lines = (markdown || "").replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;

  const inline = (text: string) => {
    const parts: ReactNode[] = [];
    const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) {
      if (m.index > last) parts.push(text.slice(last, m.index));
      const token = m[0];
      if (token.startsWith("**")) {
        parts.push(<strong key={`s${key++}`}>{token.slice(2, -2)}</strong>);
      } else if (token.startsWith("`")) {
        parts.push(
          <code key={`c${key++}`} className="rounded bg-muted px-1 py-0.5 text-[0.85em]">
            {token.slice(1, -1)}
          </code>,
        );
      } else {
        const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
        if (link) {
          parts.push(
            <a
              key={`a${key++}`}
              href={link[2]}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline underline-offset-2"
            >
              {link[1]}
            </a>,
          );
        }
      }
      last = m.index + token.length;
    }
    if (last < text.length) parts.push(text.slice(last));
    return parts;
  };

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    if (line.startsWith("### ")) {
      blocks.push(
        <h3 key={key++} className="mt-4 text-base font-semibold">
          {inline(line.slice(4))}
        </h3>,
      );
      i += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push(
        <h2 key={key++} className="mt-5 text-lg font-semibold tracking-tight">
          {inline(line.slice(3))}
        </h2>,
      );
      i += 1;
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push(
        <h1 key={key++} className="mt-2 text-xl font-bold tracking-tight">
          {inline(line.slice(2))}
        </h1>,
      );
      i += 1;
      continue;
    }
    if (/^[-*] /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*] /.test(lines[i])) {
        items.push(lines[i].replace(/^[-*] /, ""));
        i += 1;
      }
      blocks.push(
        <ul key={key++} className="my-2 list-disc space-y-1 pl-5 text-sm leading-relaxed">
          {items.map((it, idx) => (
            <li key={idx}>{inline(it)}</li>
          ))}
        </ul>,
      );
      continue;
    }
    if (/^\d+\. /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\. /, ""));
        i += 1;
      }
      blocks.push(
        <ol key={key++} className="my-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed">
          {items.map((it, idx) => (
            <li key={idx}>{inline(it)}</li>
          ))}
        </ol>,
      );
      continue;
    }
    const para: string[] = [line];
    i += 1;
    while (i < lines.length && lines[i].trim() && !/^#{1,3} /.test(lines[i]) && !/^[-*] /.test(lines[i]) && !/^\d+\. /.test(lines[i])) {
      para.push(lines[i]);
      i += 1;
    }
    blocks.push(
      <p key={key++} className="my-2 text-sm leading-relaxed text-foreground/90">
        {inline(para.join(" "))}
      </p>,
    );
  }

  return <div className="prose-sm max-w-none">{blocks.length ? blocks : <p className="text-sm text-muted-foreground">No content</p>}</div>;
}
