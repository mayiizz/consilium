from app.services.kanban_automation import validate_transcript_evidence


def test_validate_transcript_evidence_verbatim() -> None:
    assert validate_transcript_evidence("hello world", "prefix hello world suffix") == "hello world"


def test_validate_transcript_evidence_whitespace_normalized() -> None:
    ev = "hello   world"
    chunk = "prefix hello world suffix"
    out = validate_transcript_evidence(ev, chunk)
    assert out == "hello world"


def test_validate_transcript_evidence_rejects_missing() -> None:
    assert validate_transcript_evidence("not present", "only this text") == ""
