"""Build research download payloads (JSON, CSV, Markdown, PDF)."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Dict, List, Tuple

from app.models.notification import ResearchJob


def job_json_payload(job: ResearchJob) -> Dict[str, Any]:
    return {
        "research_id": str(job.id),
        "project_id": str(job.workspace_id),
        "objective": job.topic,
        "constraints": job.constraints or "",
        "research_type": job.research_type or "general",
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "summary": job.summary_preview or "",
        "findings": list(job.findings or []),
        "sources": list(job.sources or []),
        "tables": list(job.tables or []),
        "plan_notes": job.plan_notes or "",
    }


def job_markdown(job: ResearchJob) -> str:
    if (job.report_markdown or "").strip():
        return job.report_markdown
    lines = [f"# Research: {job.topic}", "", job.summary_preview or ""]
    if job.findings:
        lines.extend(["", "## Findings"])
        for f in job.findings:
            title = f.get("title") or f.get("url") or "Finding"
            lines.append(f"- {title}")
    if job.sources:
        lines.extend(["", "## Sources"])
        for s in job.sources:
            url = s.get("url") or ""
            title = s.get("title") or url
            if url:
                lines.append(f"- [{title}]({url})")
    return "\n".join(lines).strip() + "\n"


def job_csv_bytes(job: ResearchJob) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["kind", "title", "url", "source_type", "verification", "snippet"])
    for s in job.sources or []:
        writer.writerow(
            [
                "source",
                s.get("title") or "",
                s.get("url") or "",
                s.get("source_type") or "",
                s.get("verification_status") or "",
                (s.get("extracted_content") or "")[:500],
            ]
        )
    for f in job.findings or []:
        writer.writerow(
            [
                "finding",
                f.get("title") or "",
                f.get("url") or "",
                f.get("source_type") or "",
                f.get("verification_status") or "",
                json.dumps(f.get("extracted_data") or f.get("content") or "")[:500],
            ]
        )
    for table in job.tables or []:
        headers = table.get("headers") or []
        rows = table.get("rows") or []
        writer.writerow(["table", table.get("title") or "", "", "", "", "|".join(map(str, headers))])
        for row in rows:
            writer.writerow(["table_row", "", "", "", "", "|".join(map(str, row))])
    return buf.getvalue().encode("utf-8")


def markdown_to_pdf_bytes(markdown: str, title: str = "Research report") -> bytes:
    """Minimal text PDF without heavy native deps (fpdf2)."""
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError("fpdf2 is required for PDF export. pip install fpdf2") from exc

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, _safe_pdf_text(title)[:200])
    pdf.ln(4)
    pdf.set_font("Helvetica", size=10)
    for line in markdown.splitlines():
        text = _safe_pdf_text(line)
        if not text.strip():
            pdf.ln(4)
            continue
        if text.startswith("#"):
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 6, text.lstrip("# ").strip())
            pdf.set_font("Helvetica", size=10)
        else:
            pdf.multi_cell(0, 5, text)
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1", errors="replace")


def _safe_pdf_text(text: str) -> str:
    # Helvetica core fonts are Latin-1
    return (text or "").encode("latin-1", errors="replace").decode("latin-1")


def extract_tables_from_markdown(markdown: str) -> List[Dict[str, Any]]:
    """Parse simple GitHub-flavored markdown tables into structured rows."""
    tables: List[Dict[str, Any]] = []
    lines = (markdown or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            headers = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows: List[List[str]] = []
            while i < len(lines) and "|" in lines[i]:
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if row and not re.match(r"^:?-{3,}$", row[0] or ""):
                    rows.append(row)
                i += 1
            tables.append({"title": f"Table {len(tables) + 1}", "headers": headers, "rows": rows})
            continue
        i += 1
    return tables


def safe_filename(topic: str, ext: str) -> str:
    base = re.sub(r"[^\w\-]+", "_", (topic or "research").strip())[:60] or "research"
    return f"{base}.{ext}"


def content_type_for(fmt: str) -> Tuple[str, str]:
    mapping = {
        "json": ("application/json", "json"),
        "csv": ("text/csv", "csv"),
        "md": ("text/markdown", "md"),
        "markdown": ("text/markdown", "md"),
        "pdf": ("application/pdf", "pdf"),
    }
    return mapping.get(fmt.lower(), ("application/octet-stream", fmt))
