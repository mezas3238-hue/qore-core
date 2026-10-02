from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FINAL_INTEGRATED_EXAM_ID,
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID
from qore.infrastructure.cibo_world_cup_maximum_capability_exam_evidence_controls import (
    WorldCupAsIsControlEvidence,
    WorldCupCausalAttributionEvidence,
    WorldCupDigitalTwinEvidence,
    WorldCupPathMonteCarloEvidence,
    WorldCupProviderEvidence,
    WorldCupStressEvidence,
    WorldCupSurvivalProductivityEvidence,
    WorldCupTemporalReplicationEvidence,
    build_world_cup_evidence_controls,
)

HEAD = "a" * 40
T0 = datetime(2026, 10, 1, 20, 30, tzinfo=UTC)
POP = "CIBO_WORLD_CUP_COMPETITION_POPULATION_V1"


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _final() -> FinalIntegratedExamReport:
    return FinalIntegratedExamReport(
        exam_id=FINAL_INTEGRATED_EXAM_ID,
        status=FinalIntegratedExamStatus.PASS,
        integrated_head_sha=HEAD,
        blockers=(),
    )


def _evidence():
    common = {
        "competition_population_id": POP,
        "evidence_sha256": _sha("population"),
        "observed_at": T0,
    }
    return (
        WorldCupProviderEvidence(
            **common,
            provider_adapter_sha256=_sha("provider-adapter"),
            provider_economics_sha256=_sha("provider-economics"),
            competition_provider_bound=True,
            provider_economics_complete=True,
        ),
        WorldCupDigitalTwinEvidence(
            **common,
            digital_twin_sha256=_sha("digital-twin"),
            capital_conservation_sha256=_sha("capital-conservation"),
            competition_digital_twin_bound=True,
            capital_conservation_proven=True,
        ),
        WorldCupAsIsControlEvidence(
            **common,
            as_is_control_sha256=_sha("as-is"),
            as_is_control_frozen=True,
        ),
        WorldCupCausalAttributionEvidence(
            **common,
            attribution_sha256=_sha("attribution"),
            causal_attribution_complete=True,
        ),
        WorldCupPathMonteCarloEvidence(
            **common,
            path_monte_carlo_sha256=_sha("mc"),
            path_structure_preserved=True,
        ),
        WorldCupStressEvidence(
            **common,
            stress_report_sha256=_sha("stress"),
            executed_stress_families=(
                "LOSSES_FIRST",
                "WINNER_DROUGHT",
                "LOSS_CLUSTERING",
                "CORRELATION_CONVERGENCE",
                "LIQUIDITY_SHOCK",
                "VOLATILITY_SHOCK",
                "MARGIN_HIKE",
                "SLIPPAGE_SHOCK",
                "GAP_THROUGH_STOP",
                "MULTIPLE_TRADERS_LOSE_TOGETHER",
                "PROFIT_GIVEBACK",
                "FAKE_DIVERSIFICATION",
                "CONVEX_STRUCTURES_FAIL_REPEATEDLY",
                "PROVIDER_DEGRADATION",
                "CAPITAL_LOCKUP",
                "OPPORTUNITY_SCARCITY",
            ),
            stress_noncompensatory_pass=True,
        ),
        WorldCupTemporalReplicationEvidence(
            **common,
            temporal_report_sha256=_sha("temporal"),
            fold_ids=("WF1", "WF2", "WF3", "WF4"),
            fold_passes=(True, True, True, True),
            four_fold_replication_pass=True,
        ),
        WorldCupSurvivalProductivityEvidence(
            **common,
            survival_productivity_sha256=_sha("survival-productivity"),
            survival_nonworse=True,
            tail_nonworse=True,
            plausible_loss_nonworse=True,
            capital_productivity_improved=True,
        ),
    )


def test_builds_wc03_wc10_only_from_complete_separate_population() -> None:
    controls = build_world_cup_evidence_controls(
        integrated_git_sha=HEAD,
        final_integrated_exam=_final(),
        provider=_evidence()[0],
        digital_twin=_evidence()[1],
        as_is=_evidence()[2],
        attribution=_evidence()[3],
        monte_carlo=_evidence()[4],
        stress=_evidence()[5],
        temporal=_evidence()[6],
        survival_productivity=_evidence()[7],
    )
    assert tuple(item.receipt_id for item in controls) == (
        "WC03_COMPETITION_PROVIDER_ADAPTER",
        "WC04_WORLD_CUP_DIGITAL_TWIN",
        "WC05_AS_IS_CONTROL",
        "WC06_AMPLIFICATION_CAUSAL_ATTRIBUTION",
        "WC07_PATH_DEPENDENT_MONTE_CARLO",
        "WC08_ADVERSARIAL_STRESS",
        "WC09_TEMPORAL_REPLICATION",
        "WC10_SURVIVAL_CAPITAL_PRODUCTIVITY",
    )


def test_rejects_phase22_v2_population_reuse() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot reuse a protected Phase22 holdout",
    ):
        replace(
            _evidence()[0],
            competition_population_id=(
                "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
            ),
        )




def test_rejects_phase22_v4_population_reuse() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot reuse a protected Phase22 holdout",
    ):
        WorldCupProviderEvidence(
            competition_population_id=V4_CANDIDATE_ID,
            evidence_sha256=_sha("v4-population"),
            observed_at=T0,
            provider_adapter_sha256=_sha("provider-adapter-v4"),
            provider_economics_sha256=_sha("provider-economics-v4"),
            competition_provider_bound=True,
            provider_economics_complete=True,
        )


def test_rejects_incomplete_stress_surface() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="stress family coverage drift",
    ):
        replace(
            _evidence()[5],
            executed_stress_families=("LOSSES_FIRST",),
        )


def test_rejects_population_identity_drift_across_controls() -> None:
    evidence = list(_evidence())
    evidence[4] = replace(
        evidence[4],
        competition_population_id="OTHER_WORLD_CUP_POPULATION",
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="one competition population identity",
    ):
        build_world_cup_evidence_controls(
            integrated_git_sha=HEAD,
            final_integrated_exam=_final(),
            provider=evidence[0],
            digital_twin=evidence[1],
            as_is=evidence[2],
            attribution=evidence[3],
            monte_carlo=evidence[4],
            stress=evidence[5],
            temporal=evidence[6],
            survival_productivity=evidence[7],
        )
