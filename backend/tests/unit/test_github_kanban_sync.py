from app.services.github_kanban_sync import extract_keys_from_payload


def test_extract_keys_from_workflow_pr() -> None:
    pr = {"title": "Ship MM-DEADBEEF", "body": "closes task"}
    keys = extract_keys_from_payload({}, "workflow_run", resolved_pr=pr)
    assert keys == ["MM-DEADBEEF"]
