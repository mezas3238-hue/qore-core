import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    CacheKey,
    LabScope,
    TaskResult,
    TaskState,
    ValidationSuite,
)
from qore.infrastructure.core_stack_v2.shared_lab_store import CacheStore, DatasetStore


def result(cache_key: str) -> TaskResult:
    return TaskResult(
        task_id="sensor",
        suite=ValidationSuite.SENSOR_REALITY,
        scope=LabScope.SENSOR,
        state=TaskState.PASS,
        worker_id="W01",
        started_at_ns=1,
        ended_at_ns=2,
        duration_ms=0.001,
        attempts=1,
        cache_hit=False,
        tests_total=1,
        tests_passed=1,
        tests_failed=0,
        stdout_path="stdout",
        stderr_path="stderr",
        artifact_hash="a" * 64,
        failure_reason=None,
        resource_limits_applied=True,
        cache_key=cache_key,
    )


def test_dataset_store_is_content_addressed_and_persistent(tmp_path: Path) -> None:
    store = DatasetStore(tmp_path / "datasets")
    first = store.put_bytes(dataset_id="ticks", version="1", payload=b"abc")
    second = store.resolve("ticks", "1")
    assert first == second
    assert first.content_hash != store.put_bytes(
        dataset_id="ticks",
        version="2",
        payload=b"abcd",
    ).content_hash


def test_cache_requires_exact_causal_key(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache")
    key = CacheKey("a", "b", "c", "d", "e", "f")
    store.put(key, result(key.fingerprint()))
    assert store.get(key) is not None
    changed = CacheKey("a", "changed", "c", "d", "e", "f")
    assert store.get(changed) is None


def test_task_evidence_contains_required_sections() -> None:
    payload = result("k").to_dict()
    assert payload["component"] == "sensor"
    assert "outputs" in payload
    assert "consumer_evidence" in payload
    assert "causal_evidence" in payload
    assert "regression_evidence" in payload
    assert "performance_metrics" in payload
    assert "replay_metrics" in payload
    json.dumps(payload)
