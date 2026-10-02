from qore.infrastructure.cibo_arch2_ce2i_external_gate_terminalization import (
    COMPLETED,
    FALSIFIED,
    Ce2iExternalGateProvenance,
    terminalize_expansion,
    terminalize_t04_t10,
    terminalize_t09_t18,
    terminalize_t14_t15,
)
from qore.infrastructure.cibo_ce2i_t04_t10_economic_gate import (
    GATE_FROZEN_AT as T0410_FROZEN,
    GATE_ID as T0410_GATE_ID,
    GATE_SHA256 as T0410_SHA,
    Ce2iT04T10CandidateVerdict,
    Ce2iT04T10EconomicGateReport,
    Ce2iT04T10Status,
    Ce2iT04T10Tool,
)
from qore.infrastructure.cibo_expansion_utility_gate import (
    EXPANSION_UTILITY_GATE_ID,
    ExpansionUtilityGateReport,
    ExpansionUtilityGateRow,
    ExpansionUtilityKind,
    ExpansionUtilityStatus,
)
from qore.infrastructure.cibo_t09_t18_scarcity_safety_gate import (
    GATE_FROZEN_AT as T0918_FROZEN,
    GATE_ID as T0918_GATE_ID,
    GATE_SHA256 as T0918_SHA,
    T09T18ScarcityCandidateVerdict,
    T09T18ScarcityGateReport,
    T09T18ScarcityStatus,
    T09T18ScarcityTool,
)
from qore.infrastructure.cibo_t14_t15_utility_gate import (
    T14_T15_UTILITY_GATE_ID,
    T14T15UtilityGateReport,
    T14T15UtilityGateRow,
    T14T15UtilityKind,
    T14T15UtilityStatus,
)

SHA = "sha256:" + "1" * 64
FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _provenance() -> Ce2iExternalGateProvenance:
    return Ce2iExternalGateProvenance(
        evidence_id="fresh-provider-bound",
        source_receipt_sha256=SHA,
        fresh_post_freeze_oos=True,
        provider_bound=True,
        causal_control_treatment_bound=True,
        candidate_universe_frozen_complete=True,
    )


def _t0410_verdict(
    tool: Ce2iT04T10Tool,
    *,
    eligible: bool,
) -> tuple[Ce2iT04T10CandidateVerdict, Ce2iT04T10CandidateVerdict]:
    control = Ce2iT04T10CandidateVerdict(
        tool=tool,
        candidate_id=f"{tool.value}-control",
        status=Ce2iT04T10Status.CONTROL,
        passed_fold_ids=FOLDS,
        failed_fold_ids=(),
        failed_dimensions=(),
    )
    treatment = Ce2iT04T10CandidateVerdict(
        tool=tool,
        candidate_id=f"{tool.value}-treatment",
        status=(
            Ce2iT04T10Status.ELIGIBLE_FOR_FURTHER_RESEARCH
            if eligible
            else Ce2iT04T10Status.REJECTED_NOT_STRICT_4_OF_4
        ),
        passed_fold_ids=FOLDS if eligible else ("WF1", "WF2", "WF3"),
        failed_fold_ids=() if eligible else ("WF4",),
        failed_dimensions=() if eligible else ("WF4:NO_STRICT_IMPROVEMENT",),
    )
    return control, treatment


def test_t04_t10_terminalize_without_pooled_rescue() -> None:
    report = Ce2iT04T10EconomicGateReport(
        gate_id=T0410_GATE_ID,
        gate_sha256=T0410_SHA,
        gate_frozen_at=T0410_FROZEN,
        verdicts=(
            *_t0410_verdict(Ce2iT04T10Tool.T04, eligible=True),
            *_t0410_verdict(Ce2iT04T10Tool.T10, eligible=False),
        ),
    )

    t04, t10 = terminalize_t04_t10(
        report=report,
        provenance=_provenance(),
    )

    assert t04.terminal_recommendation == COMPLETED
    assert t10.terminal_recommendation == FALSIFIED
    assert t04.pooled_rescue_used is False
    assert t10.pooled_rescue_used is False


def test_expansion_terminalizes_frozen_candidate_universe() -> None:
    report = ExpansionUtilityGateReport(
        gate_id=EXPANSION_UTILITY_GATE_ID,
        kind=ExpansionUtilityKind.T06_PROFIT_FUNDED,
        control_candidate_id="control",
        population_sha256=SHA,
        provider_economics_sha256=SHA,
        rows=(
            ExpansionUtilityGateRow(
                candidate_id="control",
                status=ExpansionUtilityStatus.CONTROL,
                safety_no_worse=True,
                strict_economic_improvement=False,
                failed_dimensions=(),
            ),
            ExpansionUtilityGateRow(
                candidate_id="treatment",
                status=ExpansionUtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
                safety_no_worse=True,
                strict_economic_improvement=True,
                failed_dimensions=(),
            ),
        ),
    )

    result = terminalize_expansion(
        report=report,
        provenance=_provenance(),
    )

    assert result.workstream_id == "T06"
    assert result.terminal_recommendation == COMPLETED


def _scarcity_verdict(
    tool: T09T18ScarcityTool,
) -> tuple[T09T18ScarcityCandidateVerdict, T09T18ScarcityCandidateVerdict]:
    return (
        T09T18ScarcityCandidateVerdict(
            tool=tool,
            candidate_id=f"{tool.value}-control",
            status=T09T18ScarcityStatus.CONTROL,
            passed_fold_ids=FOLDS,
            failed_fold_ids=(),
            failed_dimensions=(),
        ),
        T09T18ScarcityCandidateVerdict(
            tool=tool,
            candidate_id=f"{tool.value}-treatment",
            status=T09T18ScarcityStatus.REJECTED_NOT_STRICT_4_OF_4,
            passed_fold_ids=("WF1", "WF2", "WF3"),
            failed_fold_ids=("WF4",),
            failed_dimensions=("WF4:NO_STRICT_IMPROVEMENT",),
        ),
    )


def test_t09_t18_all_rejected_is_terminal_falsification() -> None:
    report = T09T18ScarcityGateReport(
        gate_id=T0918_GATE_ID,
        gate_sha256=T0918_SHA,
        gate_frozen_at=T0918_FROZEN,
        verdicts=(
            *_scarcity_verdict(T09T18ScarcityTool.T09),
            *_scarcity_verdict(T09T18ScarcityTool.T18),
        ),
    )

    t09, t18 = terminalize_t09_t18(
        report=report,
        provenance=_provenance(),
    )

    assert t09.terminal_recommendation == FALSIFIED
    assert t18.terminal_recommendation == FALSIFIED


def test_t14_terminalizes_strict_utility_pass() -> None:
    report = T14T15UtilityGateReport(
        gate_id=T14_T15_UTILITY_GATE_ID,
        kind=T14T15UtilityKind.T14_DYNAMIC_DERISKING,
        control_candidate_id="control",
        population_sha256=SHA,
        provider_economics_sha256=SHA,
        causal_horizon_sha256=SHA,
        rows=(
            T14T15UtilityGateRow(
                candidate_id="control",
                status=T14T15UtilityStatus.CONTROL,
                causal_identification_pass=True,
                governance_pass=True,
                pareto_no_worse=True,
                strict_utility_improvement=False,
                failed_dimensions=(),
            ),
            T14T15UtilityGateRow(
                candidate_id="treatment",
                status=T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
                causal_identification_pass=True,
                governance_pass=True,
                pareto_no_worse=True,
                strict_utility_improvement=True,
                failed_dimensions=(),
            ),
        ),
    )

    result = terminalize_t14_t15(
        report=report,
        provenance=_provenance(),
    )

    assert result.workstream_id == "T14"
    assert result.terminal_recommendation == COMPLETED
    assert result.winner_selected is False
