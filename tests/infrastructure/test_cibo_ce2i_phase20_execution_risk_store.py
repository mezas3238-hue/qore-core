from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    DurablePhase20ExecutedRiskError,
    DurablePhase20ExecutedRiskStore,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)

NOW = datetime(2026, 9, 27, 18, 0, tzinfo=UTC)


def _evidence() -> Phase20ExecutedRiskEvidence:
    return Phase20ExecutedRiskEvidence(
        evidence_id="risk-evidence-1",
        decision_evidence_sha256="sha256:" + "a" * 64,
        signal_fingerprint="signal-1",
        qore_symbol="NAS100",
        provider_order_ref="70001",
        side="long",
        position_id=77,
        authorized_source_volume=Decimal("1"),
        filled_source_volume=Decimal("1"),
        weighted_fill_price=Decimal("100.15"),
        intended_entry_price=Decimal("100"),
        structural_stop_price=Decimal("99"),
        stop_risk_per_volume_at_intended_entry_usd=Decimal("10"),
        executed_initial_stop_risk_usd=Decimal("11.5"),
        observed_at=NOW,
        fill_evidence_refs=("fill-1", "fill-2"),
        fill_reconciled=True,
        mutation_outcome_known=True,
        capital_deployed_at=NOW - timedelta(seconds=1),
    )


def test_executed_risk_store_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "executed-risk.json"
    store = DurablePhase20ExecutedRiskStore(path)

    first = store.seal(_evidence(), expected_generation=0)
    restarted = DurablePhase20ExecutedRiskStore(path).load()

    assert first.generation == 1
    assert restarted == first
    assert restarted.risk_for(
        decision_evidence_sha256="sha256:" + "a" * 64,
        signal_fingerprint="signal-1",
        position_id=77,
    ) == _evidence()
    assert restarted.evidences[0].capital_deployed_at == (
        NOW - timedelta(seconds=1)
    )


def test_executed_risk_exact_duplicate_is_idempotent(
    tmp_path: Path,
) -> None:
    store = DurablePhase20ExecutedRiskStore(tmp_path / "risk.json")

    first = store.seal(_evidence(), expected_generation=0)
    second = store.seal(
        _evidence(),
        expected_generation=first.generation,
    )

    assert first == second
    assert second.generation == 1


def test_executed_risk_conflicting_denominator_fails_closed(
    tmp_path: Path,
) -> None:
    store = DurablePhase20ExecutedRiskStore(tmp_path / "risk.json")
    first = store.seal(_evidence(), expected_generation=0)
    conflicting = replace(
        _evidence(),
        evidence_id="risk-evidence-2",
        weighted_fill_price=Decimal("100.2"),
        executed_initial_stop_risk_usd=Decimal("12"),
    )

    with pytest.raises(
        DurablePhase20ExecutedRiskError,
        match="conflicting executed-risk decision/signal/position",
    ):
        store.seal(
            conflicting,
            expected_generation=first.generation,
        )

    assert store.load().generation == 1


def test_executed_risk_stale_generation_fails_closed(
    tmp_path: Path,
) -> None:
    store = DurablePhase20ExecutedRiskStore(tmp_path / "risk.json")
    store.seal(_evidence(), expected_generation=0)

    with pytest.raises(
        DurablePhase20ExecutedRiskError,
        match="stale executed-risk generation",
    ):
        store.seal(
            replace(
                _evidence(),
                evidence_id="other",
                signal_fingerprint="signal-2",
                position_id=78,
            ),
            expected_generation=0,
        )
