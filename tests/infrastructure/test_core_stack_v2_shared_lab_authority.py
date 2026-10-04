from qore.infrastructure.core_stack_v2.shared_lab_authority import (
    Authority,
    AuthorityIsolationReceipt,
    assess_authority_isolation,
)


def test_clean_lab_component_is_authority_free():
    receipt = AuthorityIsolationReceipt(
        component_id="shared-lab-core",
        requested_authorities=frozenset(),
        granted_authorities=frozenset(),
        read_only=True,
        research_only=True,
    )
    assert receipt.passed is True


def test_any_execution_authority_fails_lab_isolation():
    receipt = AuthorityIsolationReceipt(
        component_id="bad-component",
        requested_authorities=frozenset({Authority.EXECUTION}),
        granted_authorities=frozenset(),
        read_only=True,
        research_only=True,
    )
    result = assess_authority_isolation((receipt,))
    assert result.failed_component_ids == ("bad-component",)
    assert result.all_components_authority_free is False
