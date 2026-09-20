from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_dual_source_entry_acceptance_v1 import (
    CURRENT_ENTRY_COVERAGE_AUDIT,
    IDENTITY,
    CapitalizerDualSourceEntryFacts,
    CapitalizerEntryAcceptanceState,
    assess_dual_source_entry,
)


def _facts(**overrides: object) -> CapitalizerDualSourceEntryFacts:
    values: dict[str, object] = {
        "cognitive_gate_decision": CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
        "source_session_resolved": True,
        "source_session_eligible": True,
        "higher_timeframe_bias_confirmed_aligned": True,
        "structural_target_intact": True,
        "structural_stop_geometry_valid": True,
        "ict_liquidity_reference_defined": True,
        "ict_liquidity_raid_observed": True,
        "ict_market_structure_shift_confirmed": True,
        "ict_displacement_significant": True,
        "ict_fvg_present_in_displacement": True,
        "ict_entry_retrace_into_valid_pd_array": True,
        "ict_entry_not_chasing": True,
        "ttrades_htf_closure_at_poi_confirmed": True,
        "ttrades_ltf_cisd_confirmed": True,
        "ttrades_protected_swing_confirmed": True,
        "ttrades_continuation_confirmed": True,
        "ttrades_wick_formation_confirmed": True,
        "contradictions": (),
    }
    values.update(overrides)
    return CapitalizerDualSourceEntryFacts(**values)  # type: ignore[arg-type]


def test_entry_is_acceptable_only_when_every_source_condition_passes() -> None:
    result = assess_dual_source_entry(_facts())

    assert result.identity == IDENTITY
    assert result.state is CapitalizerEntryAcceptanceState.ACCEPTABLE_FOR_QORE_RISK
    assert result.all_mandatory_conditions_confirmed is True
    assert result.passes_to_qore_risk is True
    assert result.numeric_score_used is False
    assert result.outcome_aware is False
    assert result.executes_trade is False
    assert result.grants_capital_authority is False


def test_missing_ict_fvg_means_no_acceptable_entry() -> None:
    result = assess_dual_source_entry(_facts(ict_fvg_present_in_displacement=False))

    assert result.state is CapitalizerEntryAcceptanceState.WAIT
    assert result.passes_to_qore_risk is False
    assert result.reasons == ("ICT_FVG_NOT_PRESENT_IN_DISPLACEMENT",)


def test_missing_ttrades_cisd_means_no_acceptable_entry() -> None:
    result = assess_dual_source_entry(_facts(ttrades_ltf_cisd_confirmed=False))

    assert result.state is CapitalizerEntryAcceptanceState.WAIT
    assert result.passes_to_qore_risk is False
    assert result.reasons == ("TTRADES_LTF_CISD_NOT_CONFIRMED",)


def test_chasing_after_favorable_area_is_rejected() -> None:
    result = assess_dual_source_entry(_facts(ict_entry_not_chasing=False))

    assert result.state is CapitalizerEntryAcceptanceState.REJECT
    assert result.passes_to_qore_risk is False
    assert result.reasons == ("ICT_ENTRY_IS_CHASING_AFTER_FAVORABLE_AREA",)


def test_misaligned_htf_bias_is_rejected() -> None:
    result = assess_dual_source_entry(
        _facts(higher_timeframe_bias_confirmed_aligned=False)
    )

    assert result.state is CapitalizerEntryAcceptanceState.REJECT
    assert result.passes_to_qore_risk is False
    assert result.reasons == ("HTF_BIAS_NOT_CONFIRMED_ALIGNED",)


def test_current_engine_audit_exposes_missing_explicit_entry_conditions() -> None:
    audit = CURRENT_ENTRY_COVERAGE_AUDIT

    assert audit.current_engine_explicitly_requires_source_session is True
    assert audit.current_engine_explicitly_requires_htf_bias is True
    assert audit.current_engine_explicitly_requires_ttrades_ltf_cisd is True
    assert audit.current_engine_explicitly_requires_protected_swing is True

    assert audit.current_engine_explicitly_requires_ict_liquidity_raid is False
    assert audit.current_engine_explicitly_requires_ict_significant_displacement is False
    assert audit.current_engine_explicitly_requires_ict_fvg_in_displacement is False
    assert audit.current_engine_explicitly_requires_ict_fvg_retrace_entry is False
    assert audit.current_engine_explicitly_rejects_entry_chasing is False
    assert audit.current_engine_explicitly_requires_wick_formed_before_body is False
    assert audit.current_next_bar_open_is_universally_dual_source_entry is False
    assert audit.current_engine_may_claim_full_entry_fidelity is False
    assert audit.integration_required_before_entry_acceptance is True
