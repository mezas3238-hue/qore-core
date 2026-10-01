from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_executive_memory import (
    CiboMemoryKind,
    CiboMemoryStore,
)
from qore.infrastructure.cibo_meta_capital_memory import (
    GENC13_POLICY_SHA256,
    Genc13CapitalEpisode,
    Genc13CapitalPhenotype,
    Genc13CounterfactualKind,
    Genc13CounterfactualStudy,
    Genc13PhenotypeEvidence,
    Genc13SkepticReport,
    build_genc13_memory_item,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)
from qore.kernel.result import Success

T0 = datetime(2026, 9, 30, 8, 20, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="genc13-memory",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _episode() -> Genc13CapitalEpisode:
    return Genc13CapitalEpisode(
        episode_id="episode-1",
        account_identity=_identity(),
        trader_id=TraderLineage.VT31_NAS100,
        decision_id="decision-1",
        decision_sha256="sha256:" + "1" * 64,
        decision_at=T0,
        outcome_at=T0 + timedelta(minutes=30),
        outcome_sha256="sha256:" + "2" * 64,
        capital_state_before_sha256="sha256:" + "3" * 64,
        capital_state_after_sha256="sha256:" + "4" * 64,
        action_code="ALLOCATE_MARGINAL_UNIT",
        allocated_capital_usd=Decimal("20"),
        peak_plausible_loss_usd=Decimal("1.5"),
        capital_minutes=Decimal("600"),
        realized_pnl_usd=Decimal("-1.5"),
    )


def _phenotype() -> Genc13PhenotypeEvidence:
    return Genc13PhenotypeEvidence(
        phenotype=Genc13CapitalPhenotype.PREMATURE_EXPANSION,
        evidence_sha256="sha256:" + "5" * 64,
        identified_at=T0 + timedelta(minutes=31),
    )


def _counterfactual() -> Genc13CounterfactualStudy:
    return Genc13CounterfactualStudy(
        study_id="cf-1",
        episode_id="episode-1",
        kind=Genc13CounterfactualKind.DEPLOY_LESS,
        created_at=T0 + timedelta(minutes=32),
        simulation_evidence_sha256="sha256:" + "6" * 64,
        counterfactual_decision_sha256="sha256:" + "7" * 64,
        ending_capital_delta_usd=Decimal("0.5"),
        max_drawdown_delta_usd=Decimal("-0.4"),
        optionality_delta_usd=Decimal("0.2"),
    )


def _report() -> Genc13SkepticReport:
    return Genc13SkepticReport(
        report_id="report-1",
        episode=_episode(),
        phenotypes=(_phenotype(),),
        counterfactuals=(_counterfactual(),),
        generated_at=T0 + timedelta(minutes=33),
        hypothesis_worth_preregistering=True,
    )


def test_genc13_policy_digest_is_frozen() -> None:
    assert GENC13_POLICY_SHA256 == (
        "sha256:237b3f87efa82570eab3155fa9f72cc1add404a019d4d101faae3467a32fc793"
    )


def test_genc13_episode_requires_frozen_pre_outcome_decision() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="provenance/governance drift",
    ):
        Genc13CapitalEpisode(
            episode_id="bad",
            account_identity=_identity(),
            trader_id=TraderLineage.VT31_NAS100,
            decision_id="decision",
            decision_sha256="sha256:" + "1" * 64,
            decision_at=T0,
            outcome_at=T0 + timedelta(minutes=1),
            outcome_sha256="sha256:" + "2" * 64,
            capital_state_before_sha256="sha256:" + "3" * 64,
            capital_state_after_sha256="sha256:" + "4" * 64,
            action_code="ALLOCATE",
            allocated_capital_usd=Decimal("10"),
            peak_plausible_loss_usd=Decimal("1"),
            capital_minutes=Decimal("60"),
            realized_pnl_usd=Decimal("-1"),
            decision_frozen_before_outcome=False,
        )


def test_genc13_counterfactual_cannot_claim_causal_effect() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="counterfactual governance drift",
    ):
        Genc13CounterfactualStudy(
            study_id="oracle-cf",
            episode_id="episode-1",
            kind=Genc13CounterfactualKind.DEPLOY_LESS,
            created_at=T0 + timedelta(minutes=31),
            simulation_evidence_sha256="sha256:" + "6" * 64,
            counterfactual_decision_sha256="sha256:" + "7" * 64,
            ending_capital_delta_usd=Decimal("1"),
            max_drawdown_delta_usd=Decimal("-1"),
            optionality_delta_usd=Decimal("1"),
            causal_effect_identified=True,
        )


def test_genc13_report_cannot_select_winning_counterfactual() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot select/promote/mutate",
    ):
        Genc13SkepticReport(
            report_id="winner",
            episode=_episode(),
            phenotypes=(_phenotype(),),
            counterfactuals=(_counterfactual(),),
            generated_at=T0 + timedelta(minutes=33),
            hypothesis_worth_preregistering=True,
            winning_counterfactual_id="cf-1",
        )


def test_genc13_exports_into_existing_governed_memory() -> None:
    report = _report()
    item = build_genc13_memory_item(
        report=report,
        recorded_at=T0 + timedelta(minutes=34),
    )
    original = CiboMemoryStore()
    result = original.record(item)

    assert original.items == ()
    assert item.kind is CiboMemoryKind.FAILURE_LESSON
    assert item.subject_code == "meta-capital"
    assert item.provenance.effective_at == report.episode.outcome_at
    assert len(item.evidence_refs) == 3
    assert not hasattr(item, "config")
    assert not hasattr(item, "promotion")
    assert isinstance(result, Success)
    assert result.value.items == (item,)


def test_genc13_memory_export_is_deterministic() -> None:
    report = _report()
    first = build_genc13_memory_item(
        report=report,
        recorded_at=T0 + timedelta(minutes=34),
    )
    second = build_genc13_memory_item(
        report=report,
        recorded_at=T0 + timedelta(minutes=34),
    )
    assert first.item_id == second.item_id
    assert first.logical_values() == second.logical_values()


def test_genc13_report_requires_post_outcome_counterfactuals() -> None:
    early = Genc13CounterfactualStudy(
        study_id="early",
        episode_id="episode-1",
        kind=Genc13CounterfactualKind.RESERVE_INSTEAD,
        created_at=T0 + timedelta(minutes=29),
        simulation_evidence_sha256="sha256:" + "8" * 64,
        counterfactual_decision_sha256="sha256:" + "9" * 64,
        ending_capital_delta_usd=Decimal("0"),
        max_drawdown_delta_usd=Decimal("0"),
        optionality_delta_usd=Decimal("0"),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="post-outcome episode",
    ):
        Genc13SkepticReport(
            report_id="early-report",
            episode=_episode(),
            phenotypes=(),
            counterfactuals=(early,),
            generated_at=T0 + timedelta(minutes=33),
            hypothesis_worth_preregistering=False,
        )

def test_genc13_episode_rejects_non_bool_provenance_flag() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="decision_frozen_before_outcome must be bool",
    ):
        replace(_episode(), decision_frozen_before_outcome=1)


def test_genc13_report_rejects_non_bool_governance_flag() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="automatic_promotion must be bool",
    ):
        replace(_report(), automatic_promotion=1)



def test_genc13_report_cannot_contain_future_phenotype_evidence() -> None:
    future = replace(
        _phenotype(),
        identified_at=T0 + timedelta(minutes=34),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="future phenotype evidence",
    ):
        Genc13SkepticReport(
            report_id="future-phenotype",
            episode=_episode(),
            phenotypes=(future,),
            counterfactuals=(),
            generated_at=T0 + timedelta(minutes=33),
            hypothesis_worth_preregistering=False,
        )


def test_genc13_report_cannot_contain_future_counterfactual_evidence() -> None:
    future = replace(
        _counterfactual(),
        created_at=T0 + timedelta(minutes=34),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="future counterfactual evidence",
    ):
        Genc13SkepticReport(
            report_id="future-counterfactual",
            episode=_episode(),
            phenotypes=(),
            counterfactuals=(future,),
            generated_at=T0 + timedelta(minutes=33),
            hypothesis_worth_preregistering=False,
        )
