from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_enforcement_shadow_ab_2y_v1 as shadow,
)


def test_cognitive_shadow_contract_changes_no_rules() -> None:
    assert shadow.IDENTITY == (
        "QORE_CAPITALIZER_COGNITIVE_ENFORCEMENT_SHADOW_AB_2Y_V1"
    )
    assert shadow.EXPECTED_CONTROL_TRADES == 948
    assert str(shadow.TARGET_R) == "1.00"
