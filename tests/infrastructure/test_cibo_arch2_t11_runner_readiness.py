from qore.infrastructure.cibo_arch2_t11_runner_readiness import (
    BLOCKED,
    READY,
    assess_t11_runner_source,
)


def _compliant_source() -> str:
    return """
T11_NONLINEAR_INPUT_FREEZE
def source_minimum_volume
def pair_plan
all children are open before any close begins
realized_settlement_cost_total_usd=
deposit_asset="USD"
level_order_position=
"two_x_children_open_before_close": True
"balanced_long_short_pairs": True
"alternating_level_order": True
"metric": "ADVERSE_REALIZED_ALL_IN_SETTLEMENT_COST_USD"
"""


def test_t11_runner_readiness_accepts_complete_frozen_contract() -> None:
    result = assess_t11_runner_source(_compliant_source())

    assert result.status == READY
    assert result.missing_markers == ()
    assert result.freeze_requires_realized_settlement is True
    assert result.freeze_requires_usd_deposit_asset is True
    assert result.freeze_requires_balanced_sides is True
    assert result.freeze_requires_alternating_level_order is True
    assert result.freeze_requires_minimum_volume_children is True
    assert result.execution_authorized is False
    assert result.broker_mutation_performed is False
    assert result.productive_authority is False


def test_t11_runner_readiness_fails_closed_on_sequential_surface() -> None:
    source = _compliant_source().replace(
        "all children are open before any close begins",
        "each child is closed before the next child opens",
    )

    result = assess_t11_runner_source(source)

    assert result.status == BLOCKED
    assert "all children are open before any close begins" in result.missing_markers
    assert result.execution_authorized is False
