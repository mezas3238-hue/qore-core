from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_t13_phase22_causal_lineage import (
    assess_phase22_t12_t13_causal_population,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    EXECUTION_ECONOMICS_KIND,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    Phase22HistoricalReplayOutcomeSeal,
    VersionedPhase22HistoricalReplayEvidenceBook,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    V2_SOURCE_BINDINGS,
    phase22_v2_holdout_source_receipt_sha256,
)

BASE = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)
CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"

SOURCE_COLLECTOR_GIT_SHAS = tuple(
    sorted({item.collector_git_sha for item in V2_SOURCE_BINDINGS})
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _payload(index: int, *, omit_last_trader: bool = False) -> dict[str, object]:
    at = BASE + timedelta(hours=index)
    traders = PHASE19_REQUIRED_TRADERS[:-1] if omit_last_trader else PHASE19_REQUIRED_TRADERS
    return {
        "evidence_kind": "HISTORICAL_REPLAY_OBSERVED",
        "population_slots": [
            {"trader_id": trader.value}
            for trader in traders
        ],
        "regime_state": {
            "liquidity": "NORMAL",
            "volatility": "NORMAL",
            "correlation": "NORMAL",
            "provider_condition": "HEALTHY",
            "risk_utilization": "0.25",
            "margin_utilization": "0.20",
            "drawdown_utilization": "0.10",
            "opportunity_count": 2,
            "position_path_adverse": False,
            "evidence_stale": False,
        },
        "capital_snapshot_id": f"capital-{index}",
        "capital_snapshot_observed_at": (at - timedelta(seconds=1)).isoformat(),
        "risk_snapshot_id": f"risk-{index}",
        "risk_snapshot_observed_at": (at - timedelta(seconds=1)).isoformat(),
        "hard_risk_headroom_usd": "10",
        "candidates": [
            {
                "candidate": {
                    "signal_fingerprint": f"signal-a-{index}",
                    "stop_risk_usd": "6",
                }
            },
            {
                "candidate": {
                    "signal_fingerprint": f"signal-b-{index}",
                    "stop_risk_usd": "6",
                }
            },
        ],
    }


def _decision(index: int, *, omit_last_trader: bool = False) -> Phase20ForwardDecisionSeal:
    at = BASE + timedelta(hours=index)
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256=_sha(f"decision-{index}"),
        decision_at=at,
        candidate_id=CANDIDATE_ID,
        code_sha="a" * 40,
        parameter_sha256=_sha("params"),
        signal_fingerprints=(f"signal-a-{index}", f"signal-b-{index}"),
        canonical_payload_json=json.dumps(
            _payload(index, omit_last_trader=omit_last_trader),
            sort_keys=True,
        ),
        sealed_at=datetime(2026, 10, 1, 20, 0, tzinfo=UTC)
        + timedelta(seconds=index),
        seal_deadline_at=datetime(2026, 10, 1, 20, 5, tzinfo=UTC)
        + timedelta(seconds=index),
    )


def _outcome(
    index: int,
    *,
    loss: bool = True,
    observed_shift_hours: int = 0,
) -> Phase22HistoricalReplayOutcomeSeal:
    decision_at = BASE + timedelta(hours=index)
    deployed = decision_at + timedelta(minutes=1)
    released = decision_at + timedelta(minutes=20)
    observed = decision_at + timedelta(minutes=30, hours=observed_shift_hours)
    gross_r = Decimal("-1") if loss else Decimal("1")
    pnl = Decimal("-5") if loss else Decimal("5")
    return Phase22HistoricalReplayOutcomeSeal(
        evidence_id=(
            "phase22-replay-outcome:"
            + hashlib.sha256(f"outcome-{index}-{observed_shift_hours}".encode()).hexdigest()
        ),
        decision_evidence_sha256=_sha(f"decision-{index}"),
        signal_fingerprint=f"signal-a-{index}",
        trader_id="VT31_NAS100",
        qore_symbol="NAS100",
        observed_at=observed,
        gross_structural_outcome_r=gross_r,
        provider_execution_adjustment_usd=Decimal("0"),
        decision_provider_cost_proxy_usd=Decimal("0"),
        realized_net_pnl_usd=pnl,
        executed_initial_stop_risk_usd=Decimal("5"),
        realized_structural_outcome_r=gross_r,
        capital_deployed_at=deployed,
        capital_released_at=released,
        capital_minutes=Decimal("19"),
        provider_calibration_sha256=_sha("calibration"),
        amendment_sha256=_sha("amendment"),
        execution_economics_kind=EXECUTION_ECONOMICS_KIND,
        counterfactual_historical_replay=True,
        historical_broker_fills_claimed=False,
        fabricated_execution_evidence_used=False,
        outcome_reconciled=True,
    )


def _book(
    *,
    omit_last_trader: bool = False,
    include_outcomes: bool = True,
    future_only_outcomes: bool = False,
) -> VersionedPhase22HistoricalReplayEvidenceBook:
    decisions = tuple(
        _decision(index, omit_last_trader=omit_last_trader)
        for index in range(80)
    )
    if not include_outcomes:
        outcomes = ()
    elif future_only_outcomes:
        outcomes = tuple(
            _outcome(index, observed_shift_hours=200)
            for index in range(80)
        )
    else:
        outcomes = tuple(
            _outcome(index, loss=index < 12)
            for index in range(80)
        )
    return VersionedPhase22HistoricalReplayEvidenceBook(
        generation=1,
        amendment_sha256=_sha("amendment"),
        source_receipt_sha256=phase22_v2_holdout_source_receipt_sha256(),
        source_collector_git_shas=SOURCE_COLLECTOR_GIT_SHAS,
        decisions=decisions,
        outcomes=outcomes,
    )


def test_phase22_t12_t13_lineage_is_ready_on_causal_complete_population() -> None:
    report = assess_phase22_t12_t13_causal_population(_book())

    assert report.t12.schema_7_of_7 is True
    assert report.t12.lineage_complete is True
    assert report.t12.outcomes_read is False
    assert report.t13.decision_threshold_met is True
    assert report.t13.settled_history_epochs > 0
    assert report.t13.reserve_pressure_epochs > 0
    assert report.t13.pressure_and_scarcity_epochs > 0
    assert report.t13.lineage_complete is True
    assert report.t13.future_outcome_used is False
    assert report.t13.scientific_blockers == (
        "T13_RESERVE_POLICY_NOT_IDENTIFIED",
        "T13_CAUSAL_UTILITY_AND_WF1_WF4_REPLICATION_REQUIRED",
    )


def test_phase22_t12_detects_missing_seventh_trader_lineage() -> None:
    report = assess_phase22_t12_t13_causal_population(
        _book(omit_last_trader=True)
    )

    assert report.t12.schema_7_of_7 is False
    assert report.t12.lineage_complete is False
    assert "T12_PHASE22_REQUIRED_LINEAGES_NOT_ALL_REPRESENTED" in (
        report.t12.lineage_blockers
    )


def test_phase22_t13_requires_settled_predecision_history() -> None:
    report = assess_phase22_t12_t13_causal_population(
        _book(include_outcomes=False)
    )

    assert report.t13.lineage_complete is False
    assert "T13_PHASE22_NO_SETTLED_CAUSAL_HISTORY" in report.t13.lineage_blockers
    assert "T13_PHASE22_NO_RESERVE_PRESSURE_EPOCHS" in report.t13.lineage_blockers


def test_phase22_t13_ignores_outcomes_observed_only_after_all_decisions() -> None:
    report = assess_phase22_t12_t13_causal_population(
        _book(future_only_outcomes=True)
    )

    assert report.t13.settled_history_epochs == 0
    assert report.t13.maximum_loss_cluster == 0
    assert report.t13.maximum_settlement_drawdown_usd == Decimal("0")
    assert report.t13.future_outcome_used is False


def test_phase22_t12_rejects_stale_snapshot_binding() -> None:
    book = _book()
    first = book.decisions[0]
    payload = json.loads(first.canonical_payload_json)
    payload["capital_snapshot_observed_at"] = (
        first.decision_at - timedelta(seconds=3)
    ).isoformat()
    modified = replace(
        first,
        canonical_payload_json=json.dumps(payload, sort_keys=True),
    )
    report = assess_phase22_t12_t13_causal_population(
        VersionedPhase22HistoricalReplayEvidenceBook(
            generation=book.generation,
            amendment_sha256=book.amendment_sha256,
            source_receipt_sha256=book.source_receipt_sha256,
            source_collector_git_shas=book.source_collector_git_shas,
            decisions=(modified,) + book.decisions[1:],
            outcomes=book.outcomes,
        )
    )

    assert report.t12.lineage_complete is False
    assert "T12_PHASE22_CANONICAL_REGIME_COVERAGE_INCOMPLETE" in (
        report.t12.lineage_blockers
    )
