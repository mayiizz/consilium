"""Typed TinyFish extraction schemas by research objective (one agent, many plans)."""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

RESEARCH_TYPES = (
    "student_project",
    "academic",
    "technical",
    "competitor_analysis",
    "general",
)

GENERIC_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": {"type": "string"}},
        "source_url": {"type": "string"},
        "image_urls": {"type": "array", "items": {"type": "string"}},
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string"},
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
        "source_type": {"type": "string"},
    },
}

STUDENT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "source_type": {
            "type": "string",
            "description": "github | paper | dataset | documentation | website",
        },
        "github": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "url": {"type": "string"},
                "description": {"type": "string"},
                "language": {"type": "string"},
                "stars": {"type": "string"},
                "last_updated": {"type": "string"},
                "license": {"type": "string"},
                "technologies": {"type": "array", "items": {"type": "string"}},
                "relevance": {"type": "string"},
            },
        },
        "paper": {
            "type": "object",
            "properties": {
                "paper_title": {"type": "string"},
                "authors": {"type": "string"},
                "year": {"type": "string"},
                "venue": {"type": "string"},
                "url": {"type": "string"},
                "doi": {"type": "string"},
                "methodology": {"type": "string"},
                "dataset": {"type": "string"},
                "results": {"type": "string"},
                "limitations": {"type": "string"},
                "relevance": {"type": "string"},
            },
        },
        "dataset": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "url": {"type": "string"},
                "description": {"type": "string"},
                "format": {"type": "string"},
                "size": {"type": "string"},
                "license": {"type": "string"},
                "access": {"type": "string"},
                "relevance": {"type": "string"},
            },
        },
        "findings": {"type": "array", "items": {"type": "string"}},
        "image_urls": {"type": "array", "items": {"type": "string"}},
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string"},
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
        "source_url": {"type": "string"},
    },
}

COMPETITOR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "source_type": {
            "type": "string",
            "description": "pricing | product | website | documentation",
        },
        "company_name": {"type": "string"},
        "product_name": {"type": "string"},
        "website": {"type": "string"},
        "pricing_page_url": {
            "type": "string",
            "description": "Absolute URL of the official pricing page if found or linked",
        },
        "related_urls": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Same-site product/features/docs links worth visiting",
        },
        "target_customers": {"type": "string"},
        "positioning": {"type": "string"},
        "pricing_plans": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "plan_name": {"type": "string"},
                    "price": {"type": "string"},
                    "billing_period": {"type": "string"},
                    "currency": {"type": "string"},
                    "per_user": {"type": "string"},
                    "usage_limits": {"type": "string"},
                    "features": {"type": "array", "items": {"type": "string"}},
                    "free_trial": {"type": "string"},
                    "source_url": {"type": "string"},
                },
            },
        },
        "features": {"type": "array", "items": {"type": "string"}},
        "integrations": {"type": "array", "items": {"type": "string"}},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "findings": {"type": "array", "items": {"type": "string"}},
        "image_urls": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Absolute HTTPS URLs of product screenshots/logos visible on the page",
        },
        "image_captions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Captions or alt text aligned with image_urls when available",
        },
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string"},
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "description": "Pricing or feature tables as shown on the page",
        },
        "source_url": {"type": "string"},
        "notes": {
            "type": "string",
            "description": "Use when pricing is not publicly disclosed",
        },
    },
}


def schema_for_research_type(research_type: str) -> Dict[str, Any]:
    if research_type == "competitor_analysis":
        return COMPETITOR_SCHEMA
    if research_type in ("student_project", "academic", "technical"):
        return STUDENT_SCHEMA
    return GENERIC_SCHEMA


def infer_source_type(url: str, extracted: Dict[str, Any] | None = None) -> str:
    if extracted and isinstance(extracted.get("source_type"), str) and extracted["source_type"].strip():
        return str(extracted["source_type"]).strip().lower()
    host = (url or "").lower()
    path = urlparse(url or "").path.lower()
    if "github.com" in host:
        return "github"
    if any(x in host for x in ("arxiv.org", "pubmed", "semanticscholar", "ieee.org", "doi.org")):
        return "paper"
    if "pricing" in host or "/pricing" in path or path.rstrip("/").endswith("/plans"):
        return "pricing"
    return "website"


def is_pricing_url(url: str) -> bool:
    u = (url or "").lower()
    path = urlparse(url or "").path.lower()
    return any(
        token in u or token in path
        for token in ("/pricing", "/plans", "/price", "pricing?", "billing")
    )


def url_priority(url: str, title: str = "") -> int:
    """Higher = prefer earlier for competitor research."""
    blob = f"{url} {title}".lower()
    score = 0
    if is_pricing_url(url):
        score += 100
    if any(x in blob for x in ("official", "product", "features", "compare")):
        score += 20
    if any(x in blob for x in ("reddit", "medium.com", "youtube", "wikipedia", " Quora".lower())):
        score -= 50
    if any(x in blob for x in ("g2.com", "capterra", "producthunt", "trustradius")):
        score += 5  # directory ok but prefer official
    return score


def competitor_search_queries(topic: str, constraints: str = "") -> List[str]:
    focus = f" {constraints}" if constraints else ""
    return [
        f"{topic}{focus} official website",
        f"{topic}{focus} pricing plans",
        f"{topic}{focus} competitors alternatives pricing",
        f"best {topic} tools comparison pricing",
    ]


def default_goals(research_type: str, topic: str, constraints: str) -> str:
    focus = f" Focus: {constraints}." if constraints else ""
    if research_type == "competitor_analysis":
        return (
            f"Competitor analysis for: {topic}.{focus} "
            "This page is a competitor's OWN website (homepage, product, or pricing). "
            "1) Identify company_name, product_name, website, target customers, positioning. "
            "2) If this is NOT the pricing page, find and return pricing_page_url (absolute https link to /pricing or Plans). "
            "Also list related_urls for Features/Product pages on the SAME domain. "
            "3) On pricing pages: extract EVERY visible plan into pricing_plans with exact price text, "
            "currency, billing_period (monthly/annual), per-user if shown, usage limits, included features, free trial. "
            "NEVER invent or estimate prices — if not shown, set notes accordingly. "
            "4) Extract any HTML or visual pricing/feature TABLES into tables (headers + rows as displayed). "
            "5) Collect absolute image_urls for product screenshots, hero images, and logos visible on the page "
            "(https only), with image_captions/alt when available. "
            "6) List features, integrations, strengths, weaknesses from the page only."
        )
    if research_type in ("student_project", "academic", "technical"):
        return (
            f"Student/engineering research for: {topic}.{focus} "
            "If this is a GitHub repo, extract name, description, language, stars, license, tech stack. "
            "If a paper page, extract title, authors, year, venue, DOI, methods, datasets, results. "
            "If a dataset page, extract name, format, license, access, size. "
            "Never invent URLs, star counts, or paper titles."
        )
    return (
        f"Extract key facts, claims, numbers, and caveats about: {topic}.{focus} "
        "Preserve source URLs. Do not invent information."
    )


def synthesize_sections(research_type: str) -> List[str]:
    base = [
        "## Executive summary",
        "## Key findings",
        "## Comparison tables (markdown tables when data supports them)",
        "## Sources (clickable markdown links only from extracts)",
        "## Recommendations (label as analysis, not verified fact)",
        "## Open questions",
        "## Confidence notes",
    ]
    if research_type == "competitor_analysis":
        return [
            "## Executive summary",
            "## Competitor overview (one subsection per competitor website)",
            "## Pricing comparison (exact prices/currency/billing from pricing pages only)",
            "## Feature comparison table",
            "## Product visuals (markdown image links only from extracted image_urls)",
            "## Market and positioning",
            "## Strategic recommendations (analysis — label clearly)",
            "## Sources (official and pricing URLs)",
            "## Confidence notes",
        ]
    if research_type in ("student_project", "academic", "technical"):
        return [
            "## Executive summary",
            "## Related GitHub projects",
            "## Research papers",
            "## Datasets",
            "## Technologies and tools",
            "## Implementation guidance",
            "## Sources",
            "## Recommendations (analysis)",
            "## Confidence notes",
        ]
    return base


def follow_urls_from_extract(base_url: str, extracted: Dict[str, Any] | None) -> List[str]:
    """Collect same-site pricing / related links discovered during browse."""
    if not extracted:
        return []
    out: List[str] = []
    for key in ("pricing_page_url", "website", "source_url"):
        val = extracted.get(key)
        if isinstance(val, str) and val.strip():
            out.append(val.strip())
    related = extracted.get("related_urls")
    if isinstance(related, list):
        for item in related:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
    plans = extracted.get("pricing_plans")
    if isinstance(plans, list):
        for plan in plans:
            if isinstance(plan, dict):
                src = plan.get("source_url")
                if isinstance(src, str) and src.strip():
                    out.append(src.strip())

    base_host = (urlparse(base_url).hostname or "").lower()
    resolved: List[str] = []
    for raw in out:
        abs_url = urljoin(base_url, raw)
        host = (urlparse(abs_url).hostname or "").lower()
        # Prefer same-site follow links for competitor deep dive
        if base_host and host and host != base_host and host != f"www.{base_host}" and base_host != f"www.{host}":
            # still allow explicit pricing_page_url even if host differs slightly
            if not is_pricing_url(abs_url):
                continue
        if abs_url.startswith("https://"):
            resolved.append(abs_url)
    return resolved


def build_competitor_pricing_table(findings: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Build a cross-competitor pricing table from structured extracts."""
    headers = ["Competitor", "Plan", "Price", "Billing", "Currency", "Source"]
    rows: List[List[str]] = []
    for f in findings:
        data = f.get("extracted_data") if isinstance(f.get("extracted_data"), dict) else {}
        company = str(data.get("company_name") or data.get("product_name") or f.get("title") or "")[:80]
        plans = data.get("pricing_plans") if isinstance(data.get("pricing_plans"), list) else []
        source = str(data.get("pricing_page_url") or f.get("url") or "")
        for plan in plans:
            if not isinstance(plan, dict):
                continue
            rows.append(
                [
                    company,
                    str(plan.get("plan_name") or ""),
                    str(plan.get("price") or ""),
                    str(plan.get("billing_period") or ""),
                    str(plan.get("currency") or ""),
                    str(plan.get("source_url") or source),
                ]
            )
    if not rows:
        return None
    return {"title": "Competitor pricing (from official pages)", "headers": headers, "rows": rows}


def collect_images_from_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    images: List[Dict[str, str]] = []
    seen: set[str] = set()
    for f in findings:
        data = f.get("extracted_data") if isinstance(f.get("extracted_data"), dict) else {}
        urls = data.get("image_urls") if isinstance(data.get("image_urls"), list) else []
        captions = data.get("image_captions") if isinstance(data.get("image_captions"), list) else []
        for i, raw in enumerate(urls):
            if not isinstance(raw, str):
                continue
            url = raw.strip()
            if not url.startswith("https://") or url in seen:
                continue
            seen.add(url)
            cap = ""
            if i < len(captions) and isinstance(captions[i], str):
                cap = captions[i]
            images.append(
                {
                    "url": url,
                    "caption": cap or str(f.get("title") or ""),
                    "source_url": str(f.get("url") or ""),
                }
            )
    return images
