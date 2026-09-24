from __future__ import annotations

from datetime import UTC, datetime

import qore.infrastructure.fundednext_mt5_mutation_ledger as ledger_module
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    FundedNextMt5MutationRecord,
    FundedNextMt5MutationState,
    JsonFileFundedNextMt5MutationLedger,
)


_NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _record() -> FundedNextMt5MutationRecord:
    return FundedNextMt5MutationRecord(
        idempotency_key="mutation-ledger-test",
        receipt_id="receipt-ledger-test",
        submission_digest="sha256:" + "a" * 64,
        client_order_id="qore-ledger-test",
        state=FundedNextMt5MutationState.ATTEMPT_STARTED,
        transitioned_at=_NOW,
        risk_authorization_id="risk-ledger-test",
        risk_authorization_fingerprint="b" * 64,
        risk_reservation_id="risk-ledger-test",
    )


def test_json_ledger_atomic_commit_round_trips(tmp_path) -> None:
    path = tmp_path / "mt5-mutations.json"
    ledger = JsonFileFundedNextMt5MutationLedger(path)
    ledger.upsert(_record())

    recovered = JsonFileFundedNextMt5MutationLedger(path)
    assert recovered.records() == (_record(),)


def test_json_ledger_retries_transient_replace_failure(
    monkeypatch,
    tmp_path,
) -> None:
    real_replace = ledger_module.os.replace
    calls = 0

    def flaky_replace(source, destination) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("transient Windows file lock")
        real_replace(source, destination)

    monkeypatch.setattr(ledger_module.os, "replace", flaky_replace)

    path = tmp_path / "mt5-mutations.json"
    ledger = JsonFileFundedNextMt5MutationLedger(path)
    ledger.upsert(_record())

    assert calls == 2
    assert JsonFileFundedNextMt5MutationLedger(path).records() == (_record(),)
