import json
from datetime import UTC, datetime, timedelta

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_regime_population import (
    assess_phase20_t12_regime_population,
)

BASE = datetime(2026, 9, 29, 4, 0, tzinfo=UTC)
M5_LINEAGES = (
    TraderLineage.R34_XAUUSD,
    TraderLineage.R38_EURUSD,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R38_GBPJPY,
    TraderLineage.R42_AUDJPY,
)


def _decision(
    index: int,
    lineages: tuple[TraderLineage, ...],
    *,
    stale_snapshot: bool = False,
) -> Phase20ForwardDecisionSeal:
    decision_at = BASE + timedelta(minutes=index * 5)
    observed_at = decision_at - timedelta(
        seconds=3 if stale_snapshot else 1
    )
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "capital_snapshot_id": f"capital-{index}",
        "capital_snapshot_observed_at": observed_at.isoformat(),
        "risk_snapshot_id": f"risk-{index}",
        "risk_snapshot_observed_at": observed_at.isoformat(),
        "regime_state": {
            "liquidity": "NORMAL",
            "volatility": "NORMAL",
            "correlation": "NORMAL",
            "provider_condition": "HEALTHY",
            "risk_utilization": "0.10",
            "margin_utilization": "0.20",
            "drawdown_utilization": "0.05",
            "opportunity_count": 0,
            "position_path_adverse": False,
            "evidence_stale": False,
        },
        "population_slots": [
            {
                "slot_id": f"{trader.value}|slot",
                "trader_id": trader.value,
                "qore_symbol": trader.value,
                "observed_at": observed_at.isoformat(),
                "disposition": "ABSTAIN",
                "reason": "CAUSAL_ABSTAIN",
                "signal_fingerprint": None,
            }
            for trader in lineages
        ],
        "candidates": [],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256="sha256:" + f"{index + 1:064x}",
        decision_at=decision_at,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=(),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=decision_at + timedelta(milliseconds=200),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def test_t12_forward_regime_schema_covers_seven_lineages() -> None:
    book = VersionedPhase20ForwardEvidenceBook(
        generation=3,
        decisions=(
            _decision(0, M5_LINEAGES),
            _decision(1, (TraderLineage.VT31_NAS100,)),
            _decision(2, (TraderLineage.VT08_FOREX,)),
        ),
    )

    audit = assess_phase20_t12_regime_population(book)

    assert audit.usable_forward_epochs == 3
    assert audit.canonical_regime_epochs == 3
    assert audit.account_risk_snapshot_bound_epochs == 3
    assert audit.provider_condition_bound_epochs == 3
    assert len(audit.represented_lineages) == 7
    assert len(audit.canonical_lineages) == 7
    assert audit.noncanonical_lineages == ()
    assert audit.missing_lineages == ()
    assert audit.forward_schema_7_of_7 is True
    assert audit.burned_phase19_reinterpreted is False
    assert audit.fresh_oos_generalization_demonstrated is False
    assert audit.blockers == (
        "FRESH_OOS_T12_REGIME_GENERALIZATION_REQUIRED",
    )


def test_t12_forward_regime_audit_keeps_missing_lineage_visible() -> None:
    book = VersionedPhase20ForwardEvidenceBook(
        generation=2,
        decisions=(
            _decision(0, M5_LINEAGES),
            _decision(1, (TraderLineage.VT31_NAS100,)),
        ),
    )

    audit = assess_phase20_t12_regime_population(book)

    assert audit.forward_schema_7_of_7 is False
    assert audit.missing_lineages == (TraderLineage.VT08_FOREX,)
    assert (
        "FORWARD_T12_REQUIRED_LINEAGES_NOT_ALL_REPRESENTED"
        in audit.blockers
    )


def test_t12_forward_regime_audit_rejects_stale_snapshot_binding() -> None:
    book = VersionedPhase20ForwardEvidenceBook(
        generation=3,
        decisions=(
            _decision(0, M5_LINEAGES),
            _decision(
                1,
                (TraderLineage.VT31_NAS100,),
                stale_snapshot=True,
            ),
            _decision(2, (TraderLineage.VT08_FOREX,)),
        ),
    )

    audit = assess_phase20_t12_regime_population(book)

    assert audit.forward_schema_7_of_7 is False
    assert audit.noncanonical_lineages == (TraderLineage.VT31_NAS100,)
    assert (
        "FORWARD_T12_ACCOUNT_RISK_SNAPSHOT_BINDING_INCOMPLETE"
        in audit.blockers
    )
