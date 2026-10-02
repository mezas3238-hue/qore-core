"""Fail-closed readiness audit for the Architect-2 T11 DEMO runner.

This module never executes a broker request.  It inspects the runner source and
answers whether the executable surface still implements every pre-evidence
scientific control frozen for the market-impact experiment.

A runner that merely lints, types, or has credentials is not execution-ready.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    T11_NONLINEAR_INPUT_FREEZE,
)

READY = "RUNNER_CONTRACT_READY"
BLOCKED = "RUNNER_CONTRACT_BLOCKED"

_REQUIRED_SOURCE_MARKERS = (
    "T11_NONLINEAR_INPUT_FREEZE",
    "def source_minimum_volume",
    "def pair_plan",
    "all children are open before any close begins",
    "realized_settlement_cost_total_usd=",
    'deposit_asset="USD"',
    "level_order_position=",
    '"two_x_children_open_before_close": True',
    '"balanced_long_short_pairs": True',
    '"alternating_level_order": True',
    '"metric": "ADVERSE_REALIZED_ALL_IN_SETTLEMENT_COST_USD"',
)


@dataclass(frozen=True, slots=True)
class T11RunnerReadiness:
    status: str
    missing_markers: tuple[str, ...]
    freeze_requires_realized_settlement: bool
    freeze_requires_usd_deposit_asset: bool
    freeze_requires_balanced_sides: bool
    freeze_requires_alternating_level_order: bool
    freeze_requires_minimum_volume_children: bool
    execution_authorized: bool = False
    broker_mutation_performed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        expected_status = READY if not self.missing_markers else BLOCKED
        if self.status != expected_status:
            raise ValueError("T11 runner readiness/status drift")
        required = (
            self.freeze_requires_realized_settlement,
            self.freeze_requires_usd_deposit_asset,
            self.freeze_requires_balanced_sides,
            self.freeze_requires_alternating_level_order,
            self.freeze_requires_minimum_volume_children,
        )
        if not all(required):
            raise ValueError("T11 frozen scientific controls weakened")
        if (
            self.execution_authorized
            or self.broker_mutation_performed
            or self.productive_authority
        ):
            raise ValueError("T11 readiness audit cannot grant execution authority")


def assess_t11_runner_source(source: str) -> T11RunnerReadiness:
    if not isinstance(source, str) or not source:
        raise ValueError("T11 runner source is required")

    freeze = T11_NONLINEAR_INPUT_FREEZE.market_impact
    missing = tuple(
        marker for marker in _REQUIRED_SOURCE_MARKERS if marker not in source
    )
    return T11RunnerReadiness(
        status=READY if not missing else BLOCKED,
        missing_markers=missing,
        freeze_requires_realized_settlement=(
            freeze.realized_settlement_cost_required
        ),
        freeze_requires_usd_deposit_asset=freeze.deposit_asset_usd_required,
        freeze_requires_balanced_sides=freeze.balanced_long_short_pairs_required,
        freeze_requires_alternating_level_order=(
            freeze.alternating_level_order_required
        ),
        freeze_requires_minimum_volume_children=(
            freeze.each_child_order_minimum_volume_required
        ),
        execution_authorized=False,
        broker_mutation_performed=False,
        productive_authority=False,
    )
