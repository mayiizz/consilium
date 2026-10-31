from datetime import datetime

from app.services.task_stale_detection import effective_last_activity, task_is_stale


def test_effective_last_activity_prefers_last_activity_at():
    t = datetime(2025, 1, 10, 12, 0, 0)
    u = datetime(2025, 1, 15, 12, 0, 0)
    doc = {"last_activity_at": t, "updated_at": u, "created_at": u}
    assert effective_last_activity(doc) == t


def test_effective_last_activity_falls_back_to_updated_at():
    u = datetime(2025, 1, 15, 12, 0, 0)
    doc = {"updated_at": u, "created_at": datetime(2025, 1, 1)}
    assert effective_last_activity(doc) == u


def test_task_is_stale_before_cutoff():
    doc = {"last_activity_at": datetime(2025, 1, 1)}
    cutoff = datetime(2025, 1, 10)
    assert task_is_stale(doc, cutoff) is True


def test_task_is_stale_after_cutoff():
    doc = {"last_activity_at": datetime(2025, 1, 20)}
    cutoff = datetime(2025, 1, 10)
    assert task_is_stale(doc, cutoff) is False
