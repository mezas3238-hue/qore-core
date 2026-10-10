from qore.infrastructure.trader_lab.capitalizer_source_rule_ledger_v48 import (
    QORE_DIFFERENTIAL_MISMATCHES,
    SOURCE_RULES,
    V48DifferentialAuditState,
    V48EvidenceClass,
    V48MismatchStatus,
    V48SemanticRole,
)


def test_unresolved_interpretation_and_qore_rules_cannot_be_universal_hard_gates() -> None:
    forbidden = {
        V48EvidenceClass.INTERPRETATION,
        V48EvidenceClass.QORE_ENGINEERING_RULE,
        V48EvidenceClass.UNRESOLVED,
    }
    for rule in SOURCE_RULES:
        if rule.evidence_class in forbidden:
            assert rule.universal_hard_gate_supported is False


def test_source_explicit_alternative_routes_are_not_collapsed_into_universal_gates() -> None:
    alternative_rules = [
        rule
        for rule in SOURCE_RULES
        if rule.semantic_role
        in {
            V48SemanticRole.ALTERNATIVE_ROUTE,
            V48SemanticRole.EXECUTION_OPTION_FAMILY,
        }
    ]

    assert alternative_rules
    assert all(rule.universal_hard_gate_supported is False for rule in alternative_rules)


def test_v48_records_session_route_and_superintersection_mismatches() -> None:
    mismatches = {item.mismatch_id: item for item in QORE_DIFFERENTIAL_MISMATCHES}

    assert mismatches["UNIVERSAL_H1_M15_M1_SESSION_GRAMMAR"].status is (
        V48MismatchStatus.SOURCE_CONFLICT
    )
    assert mismatches["M1_PROMOTED_TO_SECOND_DECISION_SYSTEM"].status is (
        V48MismatchStatus.SOURCE_SUPPORT_NOT_ESTABLISHED
    )
    assert mismatches["DUAL_SOURCE_SUPERINTERSECTION_ALL_MANDATORY"].status is (
        V48MismatchStatus.SOURCE_SUPPORT_NOT_ESTABLISHED
    )


def test_v48_source_reconstruction_grants_no_economic_or_deployment_authority() -> None:
    state = V48DifferentialAuditState()

    assert state.economics_authorized is False
    assert state.fresh_holdout_authorized is False
    assert state.certification_authorized is False
    assert state.deployment_authorized is False
