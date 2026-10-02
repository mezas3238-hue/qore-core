from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.ctrader_demo_runtime_state import CTraderDemoRuntimeState

_STARTED = datetime(2026, 10, 2, 7, 0, tzinfo=UTC)
_OLD_SHA = "1" * 40
_NEW_SHA = "2" * 40
_FINGERPRINT = "a" * 64


def test_canonical_redeploy_advances_sha_without_erasing_runtime_history() -> None:
    old = CTraderDemoRuntimeState(
        git_sha=_OLD_SHA,
        account_identity_fingerprint=_FINGERPRINT,
        balance="100000",
        equity="100125",
        processed_anchors=("A", "B"),
        heartbeat_at=_STARTED,
        last_reconciliation_at=_STARTED,
        service_started_at=_STARTED,
    )
    restarted_at = _STARTED + timedelta(hours=1)

    redeployed = old.restarted_at(restarted_at, git_sha=_NEW_SHA)

    assert redeployed.git_sha == _NEW_SHA
    assert redeployed.account_identity_fingerprint == _FINGERPRINT
    assert redeployed.balance == "100000"
    assert redeployed.equity == "100125"
    assert redeployed.processed_anchors == ("A", "B")
    assert redeployed.heartbeat_at == restarted_at
    assert redeployed.last_reconciliation_at == restarted_at
    assert redeployed.service_started_at == restarted_at


def test_plain_restart_retains_current_sha() -> None:
    old = CTraderDemoRuntimeState(
        git_sha=_OLD_SHA,
        account_identity_fingerprint=_FINGERPRINT,
        balance="100000",
        equity="100125",
        processed_anchors=(),
        heartbeat_at=_STARTED,
        last_reconciliation_at=_STARTED,
        service_started_at=_STARTED,
    )

    restarted = old.restarted_at(_STARTED + timedelta(minutes=1))

    assert restarted.git_sha == _OLD_SHA
