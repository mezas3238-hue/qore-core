from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_phase22_true_scarcity_lineage import (
    assess_phase22_t09_t18_true_scarcity_lineage,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    EXECUTION_ECONOMICS_KIND,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    V2_SOURCE_BINDINGS,
    phase22_v2_holdout_source_receipt_sha256,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    Phase22HistoricalReplayOutcomeSeal,
    VersionedPhase22HistoricalReplayEvidenceBook,
)

BASE = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)
CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"

SOURCE_COLLECTOR_GIT_SHAS = tuple(
    sorted({item.collector_git_sha for item in V2_SOURCE_BINDINGS})
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _decision(index: int, *, scarce: bool = True) -> Phase20ForwardDecisionSeal:
    signal_a = f"signal-a-{index:02d}"
    signal_b = f"signal-b-{index:02d}"
    at = BASE + timedelta(hours=index)
    payload = {
        "evidence_kind": "HISTORICAL_REPLAY_OBSERVED",
        "current_step": index,
        "horizon_steps": 2,
        "hard_risk_headroom_usd": "10" if scarce else "100",
        "margin_headroom_usd": "100",
        "concentration_limit_by_group": [],
        "candidates": [
            {
                "candidate": {
                    "signal_fingerprint": signal_a,
                    "trader_id": "VT31_NAS100",
                    "concentration_group": "INDEX",
                    "stop_risk_usd": "6",
                    "margin_usd": "1",
                    "concentration_risk_usd": "6",
                }
            },
            {
                "candidate": {
                    "signal_fingerprint": signal_b,
                    "trader_id": "R38_EURUSD",
                    "concentration_group": "FX",
                    "stop_risk_usd": "6",
                    "margin_usd": "1",
                    "concentration_risk_usd": "6",
                }
            },
        ],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index:02d}",
        decision_epoch_id=f"epoch-{index:02d}",
        evidence_sha256=_sha(f"decision-{index:02d}"),
        decision_at=at,
        candidate_id=CANDIDATE_ID,
        code_sha="a" * 40,
        parameter_sha256=_sha("parameters"),
        signal_fingerprints=(signal_a, signal_b),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        sealed_at=datetime(2026, 10, 1, 20, 0, tzinfo=UTC)
        + timedelta(seconds=index),
        seal_deadline_at=datetime(2026, 10, 1, 20, 5, tzinfo=UTC)
        + timedelta(seconds=index),
    )


def _policy(
    decision: Phase20ForwardDecisionSeal,
    *,
    selected: tuple[str, ...] | None = None,
) -> Phase20ForwardPolicyDecisionSeal:
    chosen = selected or (decision.signal_fingerprints[0],)
    record = {
        "evidence_sha256": decision.evidence_sha256,
        "selected_signal_fingerprints": list(chosen),
    }
    canonical = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    )
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=decision.evidence_sha256,
        policy_record_sha256="sha256:" + hashlib.sha256(
            canonical.encode()
        ).hexdigest(),
        allocator_disposition="ALLOCATE",
        selected_signal_fingerprints=chosen,
        canonical_record_json=canonical,
    )


def _outcome(
    decision: Phase20ForwardDecisionSeal,
    signal: str,
    *,
    ordinal: int,
) -> Phase22HistoricalReplayOutcomeSeal:
    deployed = decision.decision_at + timedelta(minutes=1)
    released = deployed + timedelta(minutes=10)
    observed = released + timedelta(minutes=1)
    return Phase22HistoricalReplayOutcomeSeal(
        evidence_id=(
            "phase22-replay-outcome:"
            + hashlib.sha256(
                f"{decision.evidence_sha256}:{signal}:{ordinal}".encode()
            ).hexdigest()
        ),
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=signal,
        trader_id=(
            "VT31_NAS100" if signal.startswith("signal-a") else "R38_EURUSD"
        ),
        qore_symbol="NAS100" if signal.startswith("signal-a") else "EURUSD",
        observed_at=observed,
        gross_structural_outcome_r=Decimal("1"),
        provider_execution_adjustment_usd=Decimal("0"),
        decision_provider_cost_proxy_usd=Decimal("0"),
        realized_net_pnl_usd=Decimal("5"),
        executed_initial_stop_risk_usd=Decimal("5"),
        realized_structural_outcome_r=Decimal("1"),
        capital_deployed_at=deployed,
        capital_released_at=released,
        capital_minutes=Decimal("10"),
        provider_calibration_sha256=_sha("calibration"),
        amendment_sha256=_sha("amendment"),
        execution_economics_kind=EXECUTION_ECONOMICS_KIND,
        counterfactual_historical_replay=True,
        historical_broker_fills_claimed=False,
        fabricated_execution_evidence_used=False,
        outcome_reconciled=True,
    )


def _books(
    *,
    scarce: bool = True,
) -> tuple[
    VersionedPhase22HistoricalReplayEvidenceBook,
    VersionedPhase20ForwardPolicyBook,
]:
    decisions = tuple(_decision(index, scarce=scarce) for index in range(32))
    policies = tuple(_policy(decision) for decision in decisions)
    outcomes = tuple(
        _outcome(decision, signal, ordinal=ordinal)
        for ordinal, decision in enumerate(decisions)
        for signal in decision.signal_fingerprints
    )
    return (
        VersionedPhase22HistoricalReplayEvidenceBook(
        source_receipt_sha256=phase22_v2_holdout_source_receipt_sha256(),
        source_collector_git_shas=SOURCE_COLLECTOR_GIT_SHAS,
            generation=1,
            amendment_sha256=_sha("amendment"),
            decisions=decisions,
            outcomes=outcomes,
        ),
        VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=policies,
        ),
    )


def test_phase22_true_scarcity_lineage_readies_t09_and_t18() -> None:
    evidence, policies = _books()

    report = assess_phase22_t09_t18_true_scarcity_lineage(
        evidence_book=evidence,
        policy_book=policies,
    )

    assert report.exact_competition_epochs == 32
    assert report.scarce_competition_epochs == 32
    assert report.cross_trader_scarce_epochs == 32
    assert report.t09_ready_for_utility is True
    assert report.t18_ready_for_utility is True
    assert report.t09_blockers == ()
    assert report.t18_blockers == ()
    assert tuple(item.fold_id for item in report.t09_folds) == (
        "WF1",
        "WF2",
        "WF3",
        "WF4",
    )
    assert report.pnl_magnitudes_read is False
    assert report.counterfactual_effect_identified is False


def test_phase22_true_scarcity_does_not_relabel_abundance_as_scarcity() -> None:
    evidence, policies = _books(scarce=False)

    report = assess_phase22_t09_t18_true_scarcity_lineage(
        evidence_book=evidence,
        policy_book=policies,
    )

    assert report.exact_competition_epochs == 32
    assert report.scarce_competition_epochs == 0
    assert report.cross_trader_scarce_epochs == 0
    assert report.t09_ready_for_utility is False
    assert report.t18_ready_for_utility is False


def test_phase22_true_scarcity_rejects_policy_selection_outside_candidate_set() -> None:
    evidence, policies = _books()
    first = evidence.decisions[0]
    invalid = _policy(first, selected=("not-a-sealed-candidate",))
    policy_rows = (invalid,) + policies.decisions[1:]

    with pytest.raises(
        CiboCapitalManagementError,
        match="selected outside candidate set",
    ):
        assess_phase22_t09_t18_true_scarcity_lineage(
            evidence_book=evidence,
            policy_book=VersionedPhase20ForwardPolicyBook(
                generation=1,
                decisions=policy_rows,
            ),
        )


def test_phase22_true_scarcity_requires_digest_valid_policy() -> None:
    evidence, policies = _books()
    first = policies.decisions[0]
    corrupted = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=first.evidence_sha256,
        policy_record_sha256=_sha("wrong"),
        allocator_disposition=first.allocator_disposition,
        selected_signal_fingerprints=first.selected_signal_fingerprints,
        canonical_record_json=first.canonical_record_json,
    )

    with pytest.raises(CiboCapitalManagementError, match="policy digest drift"):
        assess_phase22_t09_t18_true_scarcity_lineage(
            evidence_book=evidence,
            policy_book=VersionedPhase20ForwardPolicyBook(
                generation=1,
                decisions=(corrupted,) + policies.decisions[1:],
            ),
        )
