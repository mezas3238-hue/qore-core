from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_a1_genc3_genc7_phase22_binding import (
    A1Genc6ExternalEngineReceipt,
    bind_genc3_to6_to_phase22,
    bind_genc7_to_phase22,
)
from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    MANIFEST_ID,
    A1Phase22PopulationFold,
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_genc3_genc6_economic_gate import (
    Genc3To6EconomicRole,
    Genc3To6FoldEconomicObservation,
    Genc3To6Workstream,
)
from qore.infrastructure.cibo_profit_preservation_economic_gate import (
    Genc7CausalEconomicObservation,
    Genc7EconomicRole,
)
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    genc7_policy_sha256,
)

BASE = datetime(2015, 10, 20, tzinfo=UTC)
FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _manifest() -> A1Phase22ScientificConsumptionManifest:
    folds = tuple(
        A1Phase22PopulationFold(
            fold_id=fold_id,
            decision_count=20,
            first_decision_at=BASE + timedelta(days=index * 20),
            last_decision_at=BASE + timedelta(days=(index + 1) * 20 - 1),
            population_sha256=_sha(f"population-{fold_id}"),
        )
        for index, fold_id in enumerate(FOLDS)
    )
    return A1Phase22ScientificConsumptionManifest(
        manifest_id=MANIFEST_ID,
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        code_sha="a" * 40,
        parameter_sha256=_sha("parameters"),
        amendment_sha256=_sha("amendment"),
        source_population_sha256=_sha("source-population"),
        policy_population_sha256=_sha("policy-population"),
        decision_count=80,
        policy_count=80,
        outcome_count=160,
        trader_ids=("R38_EURUSD", "VT31_NAS100"),
        folds=folds,
        exact_policy_coverage=True,
        historical_replay_only=True,
        folds_defined_without_outcomes=True,
    )


def _genc3_to6_observations(
    workstream: Genc3To6Workstream,
) -> tuple[Genc3To6FoldEconomicObservation, ...]:
    manifest = _manifest()
    result: list[Genc3To6FoldEconomicObservation] = []
    required = {
        Genc3To6Workstream.GENC3: "portfolio_cycle_complete",
        Genc3To6Workstream.GENC4: "marginal_unit_identified",
        Genc3To6Workstream.GENC5: "chronological_sequence_preserved",
        Genc3To6Workstream.GENC6: "true_scarcity_observed",
    }[workstream]
    for fold in manifest.folds:
        common = {
            "workstream": workstream,
            "fold_id": fold.fold_id,
            "population_sha256": fold.population_sha256,
            "provider_surface_sha256": _sha("provider"),
            "causal_horizon_sha256": _sha(f"horizon-{fold.fold_id}"),
            "protocol_binding_sha256": _sha("protocol"),
            "ending_realized_capital_usd": Decimal("70"),
            "maximum_drawdown_usd": Decimal("5"),
            "p99_drawdown_usd": Decimal("5"),
            "peak_plausible_loss_usd": Decimal("5"),
            "peak_margin_occupancy_usd": Decimal("5"),
            "provider_cost_usd": Decimal("1"),
            "capital_minutes": Decimal("10"),
            "minimum_liquid_reserve_usd": Decimal("10"),
            "minimum_optionality_usd": Decimal("10"),
            "p95_recovery_minutes": Decimal("5"),
            "causal_effect_identified": True,
            "treatment_preregistered_before_outcomes": True,
            "portfolio_cycle_complete": False,
            "marginal_unit_identified": False,
            "chronological_sequence_preserved": False,
            "true_scarcity_observed": False,
        }
        common[required] = True
        result.append(
            Genc3To6FoldEconomicObservation(
                candidate_id="control",
                workstream=workstream,
                role=Genc3To6EconomicRole.CONTROL,
                realized_net_delta_usd=Decimal("10"),
                capital_risk_time_productivity=Decimal("1"),
                **common,
            )
        )
        result.append(
            Genc3To6FoldEconomicObservation(
                candidate_id="treatment",
                workstream=workstream,
                role=Genc3To6EconomicRole.TREATMENT,
                realized_net_delta_usd=Decimal("11"),
                capital_risk_time_productivity=Decimal("2"),
                **common,
            )
        )
    return tuple(result)


def _genc7_observations() -> tuple[Genc7CausalEconomicObservation, ...]:
    manifest = _manifest()
    common = {
        "policy_sha256": genc7_policy_sha256(),
        "population_sha256": manifest.source_population_sha256,
        "provider_surface_sha256": _sha("provider"),
        "fold_ids": FOLDS,
        "horizon_start": manifest.folds[0].first_decision_at,
        "horizon_end": manifest.folds[-1].last_decision_at + timedelta(days=1),
        "realized_capital_delta_usd": Decimal("10"),
        "realized_profit_delta_usd": Decimal("10"),
        "minimum_base_capital_usd": Decimal("60"),
        "minimum_compound_capital_usd": Decimal("10"),
        "maximum_drawdown_usd": Decimal("5"),
        "p99_drawdown_usd": Decimal("5"),
        "peak_plausible_loss_usd": Decimal("5"),
        "provider_cost_usd": Decimal("1"),
        "minimum_optionality_usd": Decimal("10"),
        "profit_retention_ratio": Decimal("0.8"),
        "giveback_usd": Decimal("2"),
        "capital_risk_time_productivity": Decimal("1"),
        "causal_effect_identified": True,
    }
    control = Genc7CausalEconomicObservation(
        candidate_id="control",
        role=Genc7EconomicRole.CONTROL,
        action=Genc7Action.HOLD_CURRENT_CAPITAL_STATE,
        ending_protected_floor_usd=Decimal("10"),
        **common,
    )
    treatment = Genc7CausalEconomicObservation(
        candidate_id="treatment",
        role=Genc7EconomicRole.TREATMENT,
        action=Genc7Action.PROTECT,
        ending_protected_floor_usd=Decimal("11"),
        **common,
    )
    return (control, treatment)


def test_genc3_gate_is_bound_to_exact_phase22_fold_populations() -> None:
    report = bind_genc3_to6_to_phase22(
        manifest=_manifest(),
        observations=_genc3_to6_observations(Genc3To6Workstream.GENC3),
    )

    assert report.exact_fold_population_binding is True
    assert report.bound_workstreams == (Genc3To6Workstream.GENC3,)
    assert report.genc6_external_receipt_sha256 is None


def test_genc3_binding_rejects_one_fold_population_drift() -> None:
    observations = list(
        _genc3_to6_observations(Genc3To6Workstream.GENC3)
    )
    observations[0] = replace(
        observations[0],
        population_sha256=_sha("wrong-population"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="differs from A1 Phase22 fold",
    ):
        bind_genc3_to6_to_phase22(
            manifest=_manifest(),
            observations=tuple(observations),
        )


def test_genc6_requires_read_only_a2_engine_receipt() -> None:
    observations = _genc3_to6_observations(Genc3To6Workstream.GENC6)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires A2 engine receipt",
    ):
        bind_genc3_to6_to_phase22(
            manifest=_manifest(),
            observations=observations,
        )

    receipt = A1Genc6ExternalEngineReceipt(
        source_workstream="INTERNAL_CAPITAL_MARKET",
        source_head="b" * 40,
        artifact_sha256=_sha("a2-engine"),
        source_population_sha256=_manifest().source_population_sha256,
        policy_identity="CIBO_GENC6_A2_ENGINE_V1",
        true_scarcity_bound=True,
        capital_conservation_proven=True,
    )
    report = bind_genc3_to6_to_phase22(
        manifest=_manifest(),
        observations=observations,
        genc6_external_receipt=receipt,
    )
    assert report.genc6_external_receipt_sha256 == receipt.fingerprint()
    assert report.a2_workstream_modified is False


def test_genc7_gate_is_bound_to_full_phase22_population_and_four_folds() -> None:
    report = bind_genc7_to_phase22(
        manifest=_manifest(),
        observations=_genc7_observations(),
    )

    assert report.full_population_bound is True
    assert report.canonical_four_folds_bound is True
    assert report.certification_ready is False


def test_genc7_binding_rejects_wrong_population() -> None:
    observations = list(_genc7_observations())
    observations[1] = replace(
        observations[1],
        population_sha256=_sha("wrong-population"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="differs from A1 Phase22 manifest",
    ):
        bind_genc7_to_phase22(
            manifest=_manifest(),
            observations=tuple(observations),
        )
