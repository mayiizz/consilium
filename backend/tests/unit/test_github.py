import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient

from app.integrations.github_app import (
    parse_task_key_from_payload,
    parse_task_keys_from_payload,
    verify_github_signature,
)
from app.services.task_key import extract_task_keys, task_key_prefix


def test_github_signature_verification() -> None:
    secret = "test-secret"
    payload = b'{"action": "closed"}'
    sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_github_signature(payload, sig, secret)
    assert not verify_github_signature(payload, "sha256=bad", secret)


def test_parse_task_key() -> None:
    payload = {"pull_request": {"title": "Fix MM-ABCD1234", "body": ""}}
    assert parse_task_key_from_payload(payload) == "MM-ABCD1234"
    assert parse_task_keys_from_payload(payload, "pull_request") == ["MM-ABCD1234"]


def test_extract_task_keys_configurable_prefix() -> None:
    assert task_key_prefix() == "MM"
    keys = extract_task_keys("Refs MM-ABCD1234 and MM-ABCDEF01")
    assert "MM-ABCD1234" in keys
    assert "MM-ABCDEF01" in keys


@pytest.mark.asyncio
async def test_github_webhook_no_signature(client: AsyncClient) -> None:
    payload = {
        "action": "closed",
        "pull_request": {"merged": True, "title": "MM-TEST1234", "body": ""},
        "repository": {"full_name": "org/repo"},
    }
    body = json.dumps(payload).encode()
    secret = "mysupersecret123"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    resp = await client.post(
        "/github/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-1",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == 200
