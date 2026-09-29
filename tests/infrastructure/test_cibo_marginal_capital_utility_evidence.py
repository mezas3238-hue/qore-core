from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
    SharedCapitalFactKind,
    SharedCapitalIntelligenceFact,
    SharedToCiboCapitalIntelligenceSnapshot,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 29, 17, 30, tzinfo=UTC)
SHA = "sha256:" + "a" * 64


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="marginal-capital-demo",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _fact(
    *,
    eligible: bool,
    observed_at: datetime | None = None,
    valid_until: datetime | None = None,
) -> SharedCapitalIntelligenceFact:
    return SharedCapitalIntelligenceFact(
        fact_id="shared-failure-hazard",
        kind=SharedCapitalFactKind.FAILURE_HAZARD,
        normalized_value=Decimal("0.20"),
        value_semantics="calibrated probability-like hazard score",
        observed_at=observed_at or (T0 - timedelta(seconds=1)),
        valid_until=valid_until or (T0 + timedelta(seconds=1)),
        producer_identity="QORE_SHARED_RESEARCH",
        producer_git_sha="b" * 40,
        evidence_sha256=SHA,
        calibration_artifact_sha256=(SHA if eligible else None),
        calibrated=eligible,
        fresh_oos_validated=eligible,
        temporal_stability_validated=eligible,
        economic_utility_validated=eligible,
        eligible_for_capital_use=eligible,
    )


def _snapshot(
    fact: SharedCapitalIntelligenceFact,
) -> SharedToCiboCapitalIntelligenceSnapshot:
    return SharedToCiboCapitalIntelligenceSnapshot(
        snapshot_id="shared-snapshot",
        decision_at=T0,
        facts=(fact,),
        snapshot_sha256="sha256:" + "c" * 64,
    )


def _marginal(
    *,
    shared_snapshot: SharedToCiboCapitalIntelligenceSnapshot | None = None,
    shared_fact_ids_used: tuple[str, ...] = (),
    requested: str = "5",
    capacity: str = "10",
) -> MarginalCapitalUtilityEvidence:
    return MarginalCapitalUtilityEvidence(
        evidence_id="marginal-1",
        decision_at=T0,
        account_identity=_identity(),
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="signal-1",
        source_opportunity_decision_sha256="sha256:" + "7" * 64,
        source_baseline_policy_record_sha256="sha256:" + "8" * 64,
        current_compound_capacity_usd=Decimal(capacity),
        requested_incremental_capital_usd=Decimal(requested),
        expected_incremental_return_usd=Decimal("1.2"),
        incremental_stop_risk_usd=Decimal("0.8"),
        incremental_margin_usd=Decimal("4"),
        incremental_execution_cost_usd=Decimal("0.1"),
        incremental_concentration_risk_usd=Decimal("0.5"),
        incremental_drawdown_risk_proxy_usd=Decimal("0.4"),
        incremental_optionality_consumed_usd=Decimal("1"),
        expected_capital_minutes=Decimal("45"),
        epistemic_uncertainty=Decimal("0.25"),
        provider_evidence_sha256="sha256:" + "1" * 64,
        expectation_evidence_sha256="sha256:" + "2" * 64,
        factor_evidence_sha256="sha256:" + "3" * 64,
        duration_evidence_sha256="sha256:" + "4" * 64,
        execution_evidence_sha256="sha256:" + "5" * 64,
        optionality_evidence_sha256="sha256:" + "6" * 64,
        shared_snapshot=shared_snapshot,
        shared_fact_ids_used=shared_fact_ids_used,
    )


def test_shared_fact_never_transfers_capital_authority() -> None:
    fact = _fact(eligible=True)

    assert fact.read_only is True
    assert fact.sizing_authority is False
    assert fact.capital_authority is False
    assert fact.risk_authority is False
    assert fact.execution_authority is False

    with pytest.raises(
        CiboCompoundCapitalError,
        match="read-only/no-authority",
    ):
        SharedCapitalIntelligenceFact(
            fact_id="bad-authority",
            kind=SharedCapitalFactKind.OPPORTUNITY_QUALITY,
            normalized_value=Decimal("0.8"),
            value_semantics="test",
            observed_at=T0,
            valid_until=T0 + timedelta(seconds=1),
            producer_identity="QORE_SHARED_RESEARCH",
            producer_git_sha="b" * 40,
            evidence_sha256=SHA,
            capital_authority=True,
        )


def test_unvalidated_shared_fact_cannot_influence_capital() -> None:
    snapshot = _snapshot(_fact(eligible=False))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="unvalidated Shared fact",
    ):
        _marginal(
            shared_snapshot=snapshot,
            shared_fact_ids_used=("shared-failure-hazard",),
        )


def test_validated_shared_fact_may_be_bound_as_read_only_evidence() -> None:
    snapshot = _snapshot(_fact(eligible=True))
    evidence = _marginal(
        shared_snapshot=snapshot,
        shared_fact_ids_used=("shared-failure-hazard",),
    )

    assert evidence.shared_snapshot == snapshot
    assert evidence.utility_score_computed is False
    assert evidence.capital_authority is False
    assert evidence.outcome_present is False


def test_shared_snapshot_rejects_future_or_stale_fact() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot arrive from the future",
    ):
        _snapshot(
            _fact(
                eligible=False,
                observed_at=T0 + timedelta(milliseconds=1),
            )
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="stale at decision time",
    ):
        _snapshot(
            _fact(
                eligible=False,
                valid_until=T0 - timedelta(milliseconds=1),
            )
        )


def test_marginal_evidence_cannot_request_more_than_current_capacity() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="exceeds current compound capacity",
    ):
        _marginal(requested="11", capacity="10")


def test_gen_c4_evidence_cannot_contain_outcome_or_utility_score() -> None:
    base = _marginal()
    values = {
        field: getattr(base, field)
        for field in base.__dataclass_fields__
    }
    values["outcome_present"] = True

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot contain outcomes",
    ):
        MarginalCapitalUtilityEvidence(**values)
