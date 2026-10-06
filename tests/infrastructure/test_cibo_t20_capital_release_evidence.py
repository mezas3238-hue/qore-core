from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardOutcomeSeal,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    DurableT20CapitalReleaseStore,
    T20CapitalAuthorizationEvidence,
    T20CapitalReleaseSlice,
    build_t20_capital_release_evidence,
)

T0 = datetime(2026, 9, 29, 20, 0, tzinfo=UTC)


def _authorization() -> T20CapitalAuthorizationEvidence:
    return T20CapitalAuthorizationEvidence(
        evidence_id="t20-auth-001",
        decision_evidence_sha256="sha256:" + "1" * 64,
        signal_fingerprint="signal-a",
        position_id=7001,
        requested_at=T0,
        requested_margin_usd=Decimal("20"),
        requested_stop_risk_usd=Decimal("2"),
        risk_decision_id="risk-001",
        risk_disposition="REDUCE",
        risk_authorized_at=T0 + timedelta(seconds=1),
        risk_authorized_margin_usd=Decimal("15"),
        risk_authorized_stop_risk_usd=Decimal("1.5"),
        execution_evidence_id="execution-risk-001",
        execution_realized_at=T0 + timedelta(seconds=3),
        execution_realized_margin_usd=Decimal("12"),
        execution_realized_stop_risk_usd=Decimal("1.2"),
        capacity_deployed_at=T0 + timedelta(seconds=2),
        source_refs=(
            "cibo-request:001",
            "qore-risk:001",
            "execution-fill:001",
        ),
    )


def _settlement() -> CmaSettlementState:
    return CmaSettlementState(
        signal_fingerprint="signal-a",
        position_id=7001,
        records=(
            CmaSettlementRecord(
                event="CTRADER_DEMO_ENTRY_COST_SETTLEMENT",
                deal_id=8000,
                signal_fingerprint="signal-a",
                position_id=7001,
                net_profit_usd=Decimal("-0.10"),
                position_open_after=True,
            ),
            CmaSettlementRecord(
                event="CTRADER_DEMO_PARTIAL_SETTLEMENT",
                deal_id=8001,
                signal_fingerprint="signal-a",
                position_id=7001,
                net_profit_usd=Decimal("0.60"),
                position_open_after=True,
            ),
            CmaSettlementRecord(
                event="CTRADER_DEMO_EXIT_SETTLEMENT",
                deal_id=8002,
                signal_fingerprint="signal-a",
                position_id=7001,
                net_profit_usd=Decimal("1.50"),
                position_open_after=False,
            ),
        ),
        position_closed=True,
    )


def _outcome() -> Phase20ForwardOutcomeSeal:
    return Phase20ForwardOutcomeSeal(
        evidence_id="phase20-outcome-001",
        decision_evidence_sha256="sha256:" + "1" * 64,
        signal_fingerprint="signal-a",
        position_id=7001,
        execution_risk_evidence_id="execution-risk-001",
        settlement_deal_ids=(8000, 8001, 8002),
        fill_evidence_refs=("fill-001",),
        observed_at=T0 + timedelta(minutes=12),
        realized_net_pnl_usd=Decimal("2.00"),
        executed_initial_stop_risk_usd=Decimal("1.2"),
        realized_structural_outcome_r=Decimal("1.666666666666666666666666667"),
        capital_deployed_at=T0 + timedelta(seconds=2),
        capital_released_at=T0 + timedelta(minutes=10, seconds=2),
        capital_minutes=Decimal("10"),
    )


def _releases() -> tuple[T20CapitalReleaseSlice, ...]:
    return (
        T20CapitalReleaseSlice(
            settlement_deal_id=8001,
            released_at=T0 + timedelta(minutes=4, seconds=2),
            released_stop_risk_capacity_usd=Decimal("0.4"),
            released_margin_capacity_usd=Decimal("4"),
            source_ref="capital-ledger-release:8001",
            terminal=False,
        ),
        T20CapitalReleaseSlice(
            settlement_deal_id=8002,
            released_at=T0 + timedelta(minutes=10, seconds=2),
            released_stop_risk_capacity_usd=Decimal("0.8"),
            released_margin_capacity_usd=Decimal("8"),
            source_ref="capital-ledger-release:8002",
            terminal=True,
        ),
    )


def _evidence():
    return build_t20_capital_release_evidence(
        evidence_id="t20-release-001",
        authorization=_authorization(),
        outcome=_outcome(),
        settlement=_settlement(),
        releases=_releases(),
        observed_at=T0 + timedelta(minutes=12),
        source_refs=(
            "phase20-outcome:001",
            "cma-settlement:7001",
            "capital-return-ledger:7001",
        ),
    )


def test_t20_distinguishes_requested_authorized_realized_and_returned() -> None:
    evidence = _evidence()

    assert evidence.authorization.requested_margin_usd == Decimal("20")
    assert evidence.authorization.risk_authorized_margin_usd == Decimal("15")
    assert evidence.authorization.execution_realized_margin_usd == Decimal("12")
    assert evidence.total_released_stop_risk_capacity_usd == Decimal("1.2")
    assert evidence.total_released_margin_capacity_usd == Decimal("12")
    assert evidence.release_latency_minutes == Decimal("10")
    assert len(evidence.releases) == 2
    assert evidence.releases[0].terminal is False
    assert evidence.releases[1].terminal is True
    assert evidence.inferred_from_position_close_only is False
    assert evidence.terminal_capacity_reconciled is True
    assert evidence.productive_authority is False
    assert evidence.fingerprint().startswith("sha256:")


def test_t20_rejects_terminal_close_without_release_evidence() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="refuses terminal-close-only release inference",
    ):
        build_t20_capital_release_evidence(
            evidence_id="t20-no-release",
            authorization=_authorization(),
            outcome=_outcome(),
            settlement=_settlement(),
            releases=(),
            observed_at=T0 + timedelta(minutes=12),
            source_refs=("terminal-close-only",),
        )


def test_t20_rejects_unreconciled_returned_capacity() -> None:
    bad_releases = (
        T20CapitalReleaseSlice(
            settlement_deal_id=8002,
            released_at=T0 + timedelta(minutes=10, seconds=2),
            released_stop_risk_capacity_usd=Decimal("1.2"),
            released_margin_capacity_usd=Decimal("11"),
            source_ref="bad-return-ledger",
            terminal=True,
        ),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="must restore all realized margin capacity",
    ):
        build_t20_capital_release_evidence(
            evidence_id="t20-bad-return",
            authorization=_authorization(),
            outcome=_outcome(),
            settlement=_settlement(),
            releases=bad_releases,
            observed_at=T0 + timedelta(minutes=12),
            source_refs=("bad-return",),
        )


def test_t20_rejects_execution_above_risk_authorization() -> None:
    auth = _authorization()
    with pytest.raises(
        CiboCompoundCapitalError,
        match="Execution cannot realize more margin capacity than Risk authorized",
    ):
        T20CapitalAuthorizationEvidence(
            evidence_id=auth.evidence_id,
            decision_evidence_sha256=auth.decision_evidence_sha256,
            signal_fingerprint=auth.signal_fingerprint,
            position_id=auth.position_id,
            requested_at=auth.requested_at,
            requested_margin_usd=auth.requested_margin_usd,
            requested_stop_risk_usd=auth.requested_stop_risk_usd,
            risk_decision_id=auth.risk_decision_id,
            risk_disposition=auth.risk_disposition,
            risk_authorized_at=auth.risk_authorized_at,
            risk_authorized_margin_usd=Decimal("10"),
            risk_authorized_stop_risk_usd=auth.risk_authorized_stop_risk_usd,
            execution_evidence_id=auth.execution_evidence_id,
            execution_realized_at=auth.execution_realized_at,
            execution_realized_margin_usd=Decimal("12"),
            execution_realized_stop_risk_usd=auth.execution_realized_stop_risk_usd,
            capacity_deployed_at=auth.capacity_deployed_at,
            source_refs=auth.source_refs,
        )


def test_t20_store_is_hash_chained_restart_safe_and_conflict_safe(tmp_path) -> None:
    store = DurableT20CapitalReleaseStore(tmp_path / "t20-release.json")
    evidence = _evidence()

    first = store.seal(
        evidence,
        sealed_at=T0 + timedelta(minutes=13),
        expected_generation=0,
    )
    assert first.generation == 1
    assert first.records[0].chain_sha256.startswith("sha256:")

    restarted = DurableT20CapitalReleaseStore(tmp_path / "t20-release.json")
    assert restarted.load() == first

    idempotent = restarted.seal(
        evidence,
        sealed_at=T0 + timedelta(minutes=13),
        expected_generation=1,
    )
    assert idempotent == first

    with pytest.raises(
        CiboCompoundCapitalError,
        match="generation conflict",
    ):
        restarted.seal(
            evidence,
            sealed_at=T0 + timedelta(minutes=13),
            expected_generation=0,
        )

    changed = build_t20_capital_release_evidence(
        evidence_id="t20-release-conflict",
        authorization=_authorization(),
        outcome=_outcome(),
        settlement=_settlement(),
        releases=_releases(),
        observed_at=T0 + timedelta(minutes=13),
        source_refs=(
            "phase20-outcome:001",
            "cma-settlement:7001",
            "capital-return-ledger:DIFFERENT",
        ),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="conflicting release evidence rewrite",
    ):
        restarted.seal(
            changed,
            sealed_at=T0 + timedelta(minutes=14),
            expected_generation=1,
        )
