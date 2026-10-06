from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ceiling_discovery_assembly import (
    assemble_ceiling_discovery,
)


SHA = "sha256:" + "a" * 64


def _preflight(**overrides):
    value = {
        "schema": "qore.cibo.native-max-intelligence-preflight.v1",
        "source_manifest_sha256": SHA,
        "decision_count": 3368,
        "native_max_pass_count": 3368,
        "native_max_blocked_count": 0,
        "maximum_intelligence_ready": True,
        "external_ai_call_count": 0,
    }
    value.update(overrides)
    return value


def _run(**overrides):
    value = {
        "schema": "qore.cibo.single-account-sovereign-ceiling-run.v1",
        "source_manifest_sha256": SHA,
        "decision_count": 3368,
        "sovereign_runtime_evaluation_count": 3368,
        "full_semantic_decision_count": 3368,
        "external_ai_call_count": 0,
        "account_reset_count": 0,
        "economic_era_reset_count": 0,
        "initial_capital_usd": "60",
        "ending_capital_usd": "50000",
        "peak_capital_usd": "52000",
        "maximum_drawdown_usd": "2000",
        "native_sovereign_runtime_used": True,
        "qore_risk_sovereign": True,
        "outcome_used_for_predecision": False,
        "target_capital_used_for_tuning": False,
        "population_exhausted": False,
        "growth_capacity_remaining_at_population_end": False,
        "intrinsic_ceiling_claimed": True,
        "observed_lower_bound_only": False,
        "limiting_factor": "MARGIN",
        "ablations": {
            "sizing": {"executed": True},
            "adaptive_leverage": {"executed": True},
            "cibo_compound": {"executed": True},
            "compound_portfolio": {"executed": True},
            "cognition": {"executed": True},
        },
    }
    value.update(overrides)
    return value


def _frontier():
    return {
        "frontier_role": "DIAGNOSTIC_FRONTIER_ONLY",
        "ceiling_discovery_closure_eligible": False,
        "fingerprint": "sha256:" + "b" * 64,
    }


def test_assembly_closes_only_on_full_sovereign_intrinsic_ceiling() -> None:
    result = assemble_ceiling_discovery(
        native_preflight=_preflight(),
        sovereign_run=_run(),
        diagnostic_frontier=_frontier(),
    )

    assert result["classification"] == "INTRINSIC_CEILING"
    assert result["ceiling_discovery_ready_to_close"] is True
    assert Decimal(result["capital_multiple"]) * Decimal("60") == Decimal(
        "50000"
    )
    assert result["governance"]["diagnostic_frontier_authoritative"] is False
    assert result["governance"]["native_sovereign_run_authoritative"] is True


def test_assembly_rejects_partial_native_max_coverage() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="complete Native MAX preflight",
    ):
        assemble_ceiling_discovery(
            native_preflight=_preflight(
                native_max_pass_count=2722,
                native_max_blocked_count=646,
                maximum_intelligence_ready=False,
            ),
            sovereign_run=_run(),
        )


def test_assembly_rejects_different_manifest_between_labs() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="source manifest lineage drift",
    ):
        assemble_ceiling_discovery(
            native_preflight=_preflight(),
            sovereign_run=_run(
                source_manifest_sha256="sha256:" + "c" * 64
            ),
        )


def test_assembly_rejects_missing_mandatory_ablation() -> None:
    ablations = dict(_run()["ablations"])
    ablations["adaptive_leverage"] = {"executed": False}

    with pytest.raises(
        CiboCapitalManagementError,
        match="mandatory ablation missing: adaptive_leverage",
    ):
        assemble_ceiling_discovery(
            native_preflight=_preflight(),
            sovereign_run=_run(ablations=ablations),
        )


def test_population_exhaustion_is_lower_bound_and_keeps_stage_open() -> None:
    result = assemble_ceiling_discovery(
        native_preflight=_preflight(),
        sovereign_run=_run(
            population_exhausted=True,
            growth_capacity_remaining_at_population_end=True,
            intrinsic_ceiling_claimed=False,
            observed_lower_bound_only=True,
            limiting_factor="OPPORTUNITY_POPULATION_EXHAUSTED",
        ),
        diagnostic_frontier=_frontier(),
    )

    assert result["classification"] == "OBSERVED_LOWER_BOUND"
    assert result["ceiling_discovery_ready_to_close"] is False


def test_diagnostic_frontier_cannot_claim_closure_authority() -> None:
    bad = dict(_frontier())
    bad["ceiling_discovery_closure_eligible"] = True

    with pytest.raises(
        CiboCapitalManagementError,
        match="diagnostic frontier cannot be closure-eligible",
    ):
        assemble_ceiling_discovery(
            native_preflight=_preflight(),
            sovereign_run=_run(),
            diagnostic_frontier=bad,
        )


def test_assembly_rejects_runner_that_did_not_use_native_sovereign_runtime() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="diagnostic frontier cannot substitute",
    ):
        assemble_ceiling_discovery(
            native_preflight=_preflight(),
            sovereign_run=_run(native_sovereign_runtime_used=False),
        )
