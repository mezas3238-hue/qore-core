from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_adaptive_compound_speed_population import (
    Genc8PopulationStatus,
    describe_genc8_population,
)
from qore.infrastructure.cibo_adaptive_compound_speed_shadow import (
    GENC8_POLICY_FROZEN_AT,
    Genc8AdaptiveSpeedFact,
    Genc8FactKind,
    Genc8RegimeEvidence,
    Genc8Severity,
    Genc8SpeedPosture,
    evaluate_genc8_adaptive_compound_speed,
    genc8_policy_sha256,
)
from qore.infrastructure.cibo_adaptive_compound_speed_store import (
    DurableGenc8AdaptiveCompoundSpeedStore,
    VersionedGenc8ShadowBook,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimePosture,
    ProviderCondition,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    GENC5_SHADOW_POLICY_ID,
    SequentialCompoundPosture,
    SequentialCompoundShadowAction,
    genc5_shadow_policy_sha256,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    Genc5ShadowDecisionSeal,
)

T0 = datetime(2026, 9, 30, 0, 25, tzinfo=UTC)


def _genc5() -> Genc5ShadowDecisionSeal:
    return Genc5ShadowDecisionSeal(
        decision_sha256="sha256:" + "1" * 64,
        policy_sha256=genc5_shadow_policy_sha256(),
        decision_id="genc5-for-c8",
        decision_at=T0,
        sealed_at=T0 + timedelta(seconds=1),
        account_provider_key="ctrader",
        account_ref="genc8-test",
        source_lot_id="lot-1",
        source_lot_state=CompoundCapitalState.COMPOUNDABLE,
        source_lot_amount_usd=Decimal("20"),
        portfolio_sha256="sha256:" + "2" * 64,
        marginal_evidence_sha256="sha256:" + "3" * 64,
        policy_protected_floor_usd=Decimal("10"),
        candidate_compound_capacity_usd=Decimal("20"),
        control_posture=SequentialCompoundPosture.COMPOUND_PAUSED,
        control_action=SequentialCompoundShadowAction.HOLD_CURRENT_STATE,
        control_requested_risk_review_usd=Decimal("0"),
        treatment_posture=SequentialCompoundPosture.CAUTIOUS_COMPOUND,
        treatment_action=(
            SequentialCompoundShadowAction.REQUEST_DOWNSTREAM_RISK_REVIEW
        ),
        treatment_requested_risk_review_usd=Decimal("5"),
        blocker_codes=(),
        treatment_differs_from_control=True,
    )


def _regime(
    *,
    posture: CiboRegimePosture = CiboRegimePosture.STABLE,
    provider: ProviderCondition = ProviderCondition.HEALTHY,
    calibrated: bool = True,
    capital_eligible: bool = True,
) -> Genc8RegimeEvidence:
    return Genc8RegimeEvidence(
        evidence_id="genc8-regime",
        decision_at=T0,
        account_provider_key="ctrader",
        account_ref="genc8-test",
        regime_posture=posture,
        provider_condition=provider,
        evidence_sha256="sha256:" + "4" * 64,
        source="T12_CANONICAL_REGIME",
        policy_version="T12_FROZEN",
        calibrated=calibrated,
        capital_eligible=capital_eligible,
    )


def _facts(
    *,
    overrides: dict[Genc8FactKind, Genc8Severity] | None = None,
    ineligible: Genc8FactKind | None = None,
) -> tuple[Genc8AdaptiveSpeedFact, ...]:
    overrides = overrides or {}
    result = []
    for index, kind in enumerate(Genc8FactKind, start=1):
        result.append(
            Genc8AdaptiveSpeedFact(
                fact_id=f"fact-{kind.value}",
                decision_at=T0,
                account_provider_key="ctrader",
                account_ref="genc8-test",
                kind=kind,
                severity=overrides.get(kind, Genc8Severity.BENIGN),
                evidence_sha256=(
                    "sha256:" + format(index, "x").rjust(64, "0")
                ),
                source=f"CALIBRATED_{kind.value}",
                model_id=f"MODEL_{kind.value}_V1",
                calibrated=kind is not ineligible,
                capital_eligible=kind is not ineligible,
            )
        )
    return tuple(result)


def test_genc8_policy_digest_is_frozen() -> None:
    assert genc8_policy_sha256() == (
        "sha256:db6c06aee21bc89f7d9058334292e6f8"
        "c2f99ea46cc35560b46891b5bd8eb1bc"
    )
    assert GENC5_SHADOW_POLICY_ID.startswith("CIBO_GENC5_")


def test_genc8_all_benign_can_research_accelerated_without_deciding_amount() -> None:
    decision = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-benign",
        genc5=_genc5(),
        regime=_regime(),
        facts=_facts(),
    )

    assert decision.control_posture is Genc8SpeedPosture.CAUTIOUS
    assert decision.treatment_posture is Genc8SpeedPosture.ACCELERATED
    assert decision.binding_ceiling_posture is Genc8SpeedPosture.ACCELERATED
    assert decision.treatment_differs_from_control is True
    assert decision.amount_decided_usd is None
    assert decision.runtime_authority is False
    assert decision.sizing_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False


def test_genc8_watch_regime_caps_speed_without_rejecting() -> None:
    decision = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-watch",
        genc5=_genc5(),
        regime=_regime(posture=CiboRegimePosture.WATCH),
        facts=_facts(),
    )

    assert decision.treatment_posture is Genc8SpeedPosture.CAUTIOUS
    assert decision.binding_reason == "regime:WATCH"
    assert decision.blocker_codes == ()


def test_genc8_critical_risk_headroom_forces_pause_noncompensatory() -> None:
    decision = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-critical-risk",
        genc5=_genc5(),
        regime=_regime(),
        facts=_facts(
            overrides={
                Genc8FactKind.RISK_HEADROOM: Genc8Severity.CRITICAL,
            }
        ),
    )

    assert decision.treatment_posture is Genc8SpeedPosture.PAUSE
    assert decision.binding_reason == "RISK_HEADROOM:CRITICAL"


def test_genc8_loss_deterioration_never_creates_more_speed() -> None:
    benign = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-loss-benign",
        genc5=_genc5(),
        regime=_regime(),
        facts=_facts(),
    )
    adverse = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-loss-adverse",
        genc5=_genc5(),
        regime=_regime(),
        facts=_facts(
            overrides={
                Genc8FactKind.LOSS_CLUSTER: Genc8Severity.ADVERSE,
            }
        ),
    )

    assert benign.treatment_posture is Genc8SpeedPosture.ACCELERATED
    assert adverse.treatment_posture is Genc8SpeedPosture.DEFENSIVE


def test_genc8_ineligible_fact_fails_closed_without_score() -> None:
    decision = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-ineligible",
        genc5=_genc5(),
        regime=_regime(),
        facts=_facts(ineligible=Genc8FactKind.SHARED_UNCERTAINTY),
    )

    assert decision.treatment_posture is Genc8SpeedPosture.PAUSE
    assert decision.blocker_codes == (
        "FACT_NOT_CAPITAL_ELIGIBLE:SHARED_UNCERTAINTY",
    )
    assert decision.amount_decided_usd is None


def test_genc8_requires_exact_mandatory_fact_set() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="mandatory adaptive fact set incomplete",
    ):
        evaluate_genc8_adaptive_compound_speed(
            decision_id="genc8-missing-fact",
            genc5=_genc5(),
            regime=_regime(),
            facts=_facts()[:-1],
        )


def test_genc8_frozen_policy_accepts_historical_genc5_decision() -> None:
    historical_at = GENC8_POLICY_FROZEN_AT - timedelta(days=365 * 5)
    genc5 = replace(
        _genc5(),
        decision_at=historical_at,
        sealed_at=historical_at + timedelta(seconds=1),
    )
    regime = replace(
        _regime(),
        decision_at=genc5.decision_at,
    )
    facts = tuple(
        replace(item, decision_at=genc5.decision_at)
        for item in _facts()
    )

    decision = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-historical",
        genc5=genc5,
        regime=regime,
        facts=facts,
    )

    assert decision.decision_at == historical_at
    assert decision.policy_frozen_at == GENC8_POLICY_FROZEN_AT
    assert decision.treatment_posture is Genc8SpeedPosture.ACCELERATED
    assert decision.outcome_present_at_seal is False


def test_genc8_store_is_restart_cas_and_conflict_safe(tmp_path) -> None:
    decision = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-store",
        genc5=_genc5(),
        regime=_regime(),
        facts=_facts(),
    )
    path = tmp_path / "genc8-store.json"
    store = DurableGenc8AdaptiveCompoundSpeedStore(path)
    sealed_at = T0 + timedelta(seconds=2)

    first = store.seal(
        decision,
        sealed_at=sealed_at,
        expected_generation=0,
    )
    assert first.generation == 1
    assert first.chain_sha256.startswith("sha256:")

    restarted = DurableGenc8AdaptiveCompoundSpeedStore(path)
    assert restarted.load() == first

    idempotent = restarted.seal(
        decision,
        sealed_at=sealed_at,
        expected_generation=1,
    )
    assert idempotent == first

    with pytest.raises(
        CiboCompoundCapitalError,
        match="generation conflict",
    ):
        restarted.seal(
            decision,
            sealed_at=sealed_at,
            expected_generation=0,
        )

    changed = replace(
        decision,
        binding_reason="different-but-post-outcome-illegal-rewrite",
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="conflicting decision rewrite",
    ):
        restarted.seal(
            changed,
            sealed_at=sealed_at,
            expected_generation=1,
        )


def test_genc8_population_is_descriptive_only(tmp_path) -> None:
    decision = evaluate_genc8_adaptive_compound_speed(
        decision_id="genc8-population",
        genc5=_genc5(),
        regime=_regime(),
        facts=_facts(),
    )
    store = DurableGenc8AdaptiveCompoundSpeedStore(
        tmp_path / "genc8-population.json"
    )
    book = store.seal(
        decision,
        sealed_at=T0 + timedelta(seconds=2),
        expected_generation=0,
    )

    report = describe_genc8_population(book=book)

    assert report.status is Genc8PopulationStatus.COLLECTING
    assert report.decision_count == 1
    assert report.accelerated_count == 1
    assert report.treatment_control_divergence_count == 1
    assert report.account_keys == ("ctrader:genc8-test",)
    assert report.descriptive_only is True
    assert report.real_outcome_binding_complete is False
    assert report.economic_utility_ready is False
    assert report.stress_pass is False
    assert report.temporal_replication_pass is False
    assert report.certification_ready is False


def test_genc8_empty_population_claims_nothing() -> None:
    report = describe_genc8_population(
        book=VersionedGenc8ShadowBook(generation=0)
    )

    assert report.status is Genc8PopulationStatus.EMPTY
    assert report.decision_count == 0
    assert report.economic_utility_ready is False
    assert report.certification_ready is False
