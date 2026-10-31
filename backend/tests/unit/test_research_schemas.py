from app.services.research_exports import extract_tables_from_markdown, job_csv_bytes, job_json_payload
from app.services.research_schemas import (
    COMPETITOR_SCHEMA,
    STUDENT_SCHEMA,
    build_competitor_pricing_table,
    collect_images_from_findings,
    follow_urls_from_extract,
    infer_source_type,
    is_pricing_url,
    schema_for_research_type,
    url_priority,
)


def test_schema_for_types():
    assert schema_for_research_type("competitor_analysis") is COMPETITOR_SCHEMA
    assert schema_for_research_type("student_project") is STUDENT_SCHEMA
    assert "pricing_plans" in COMPETITOR_SCHEMA["properties"]
    assert "github" in STUDENT_SCHEMA["properties"]


def test_infer_source_type():
    assert infer_source_type("https://github.com/org/repo") == "github"
    assert infer_source_type("https://arxiv.org/abs/123") == "paper"
    assert infer_source_type("https://example.com/pricing") == "pricing"
    assert infer_source_type("https://example.com", {"source_type": "dataset"}) == "dataset"


def test_extract_tables_from_markdown():
    md = """# Title

| A | B |
| --- | --- |
| 1 | 2 |
| 3 | 4 |
"""
    tables = extract_tables_from_markdown(md)
    assert len(tables) == 1
    assert tables[0]["headers"] == ["A", "B"]
    assert tables[0]["rows"][0] == ["1", "2"]


def test_pricing_url_priority_and_follow():
    assert is_pricing_url("https://acme.com/pricing")
    assert url_priority("https://acme.com/pricing") > url_priority("https://reddit.com/r/saas")
    follows = follow_urls_from_extract(
        "https://acme.com/",
        {
            "pricing_page_url": "https://acme.com/pricing",
            "related_urls": ["/features", "https://acme.com/product"],
        },
    )
    assert "https://acme.com/pricing" in follows
    assert any("/features" in u or u.endswith("/features") for u in follows)


def test_build_pricing_table_and_images():
    findings = [
        {
            "title": "Acme",
            "url": "https://acme.com/pricing",
            "extracted_data": {
                "company_name": "Acme",
                "pricing_plans": [
                    {
                        "plan_name": "Pro",
                        "price": "$29",
                        "billing_period": "monthly",
                        "currency": "USD",
                        "source_url": "https://acme.com/pricing",
                    }
                ],
                "image_urls": ["https://cdn.acme.com/hero.png"],
                "image_captions": ["Hero"],
            },
        }
    ]
    table = build_competitor_pricing_table(findings)
    assert table and table["rows"][0][0] == "Acme"
    assert table["rows"][0][2] == "$29"
    images = collect_images_from_findings(findings)
    assert images[0]["url"] == "https://cdn.acme.com/hero.png"


def test_job_exports_shape():
    class FakeJob:
        id = "abc"
        workspace_id = "ws"
        topic = "Desk booking"
        constraints = ""
        research_type = "competitor_analysis"
        status = type("S", (), {"value": "done"})()
        summary_preview = "Summary"
        findings = [{"title": "X", "url": "https://example.com"}]
        sources = [
            {
                "title": "X",
                "url": "https://example.com",
                "source_type": "website",
                "verification_status": "verified",
                "extracted_content": "hello",
            }
        ]
        tables = [{"title": "T", "headers": ["a"], "rows": [["1"]]}]
        plan_notes = "{}"
        report_markdown = "# Desk booking\n\nDone."

    payload = job_json_payload(FakeJob())  # type: ignore[arg-type]
    assert payload["research_type"] == "competitor_analysis"
    assert payload["sources"]
    csv_bytes = job_csv_bytes(FakeJob())  # type: ignore[arg-type]
    assert b"source" in csv_bytes
