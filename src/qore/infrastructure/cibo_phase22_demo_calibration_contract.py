"""Governance contract for Phase22 cTrader DEMO execution calibration.

This lane is deliberately disjoint from the historical holdout. It may create
bounded DEMO-only calibration orders, but it may not inspect Phase22 holdout
outcomes or claim that current provider fills occurred in 2015-2016.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

CALIBRATION_AUTHORIZATION_TOKEN = (
    "CIBO_PHASE22_DEMO_EXECUTION_CALIBRATION_AUTHORIZED"
)
CALIBRATION_LABEL_PREFIX = "QORE:CIBO-CAL:"
REQUIRED_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)
MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL = 8
MAXIMUM_ROUND_TRIPS_PER_MANUAL_DISPATCH = 6
MANUAL_DISPATCH_EVENT = "workflow_dispatch"
OWNER_GITHUB_LOGIN = "mezas3238-hue"
DEMO_ONLY_CONFIRMATION = "DEMO_ONLY_NO_LIVE_NO_FUNDEDNEXT"


@dataclass(frozen=True, slots=True)
class Phase22DemoCalibrationGovernance:
    environment: str = "demo"
    endpoint_host: str = "demo.ctraderapi.com"
    account_must_be_non_live: bool = True
    minimum_volume_only: bool = True
    close_created_position_only: bool = True
    holdout_outcomes_allowed: bool = False
    fundednext_allowed: bool = False
    live_allowed: bool = False
    real_capital_allowed: bool = False
    vps_required: bool = False

    def __post_init__(self) -> None:
        if self.environment != "demo":
            raise ValueError("Phase22 calibration must remain DEMO-only")
        if self.endpoint_host != "demo.ctraderapi.com":
            raise ValueError("Phase22 calibration endpoint drift")
        required_true = (
            self.account_must_be_non_live,
            self.minimum_volume_only,
            self.close_created_position_only,
        )
        if not all(required_true):
            raise ValueError("Phase22 calibration safety guard weakened")
        prohibited = (
            self.holdout_outcomes_allowed,
            self.fundednext_allowed,
            self.live_allowed,
            self.real_capital_allowed,
            self.vps_required,
        )
        if any(prohibited):
            raise ValueError("Phase22 calibration authority widened")


PHASE22_DEMO_CALIBRATION_GOVERNANCE = Phase22DemoCalibrationGovernance()


@dataclass(frozen=True, slots=True)
class Phase22DemoCalibrationInvocation:
    """Closed authority envelope for one manually dispatched calibration run."""

    event_name: str
    actor: str
    run_id: str
    run_attempt: int
    owner_authorization: str
    demo_only_confirmation: str
    requested_round_trips: int

    def __post_init__(self) -> None:
        if self.event_name != MANUAL_DISPATCH_EVENT:
            raise ValueError("broker mutation requires workflow_dispatch")
        if self.actor != OWNER_GITHUB_LOGIN:
            raise ValueError("broker mutation requires the explicit Owner actor")
        if self.owner_authorization != CALIBRATION_AUTHORIZATION_TOKEN:
            raise ValueError("broker mutation Owner authorization is invalid")
        if self.demo_only_confirmation != DEMO_ONLY_CONFIRMATION:
            raise ValueError("DEMO-only mutation confirmation is invalid")
        if not self.run_id.isdigit() or int(self.run_id) <= 0:
            raise ValueError("GitHub run identity must be a positive integer")
        if type(self.run_attempt) is not int or self.run_attempt <= 0:
            raise ValueError("GitHub run attempt must be a positive integer")
        if (
            type(self.requested_round_trips) is not int
            or not 1
            <= self.requested_round_trips
            <= MAXIMUM_ROUND_TRIPS_PER_MANUAL_DISPATCH
        ):
            raise ValueError("manual calibration round-trip limit is invalid")

    @property
    def mutation_budget(self) -> int:
        """A GitHub retry is reconciliation-only and can never mutate again."""
        if self.run_attempt != 1:
            return 0
        return self.requested_round_trips


def plan_missing_execution_slots(
    execution_order_counts: Mapping[str, int],
    *,
    invocation: Phase22DemoCalibrationInvocation,
) -> tuple[tuple[str, int], ...]:
    """Plan from broker-executed entry orders, never causal reconstruction."""
    if set(execution_order_counts) != set(REQUIRED_SYMBOLS):
        raise ValueError("broker execution population symbol surface is incomplete")
    for symbol, count in execution_order_counts.items():
        if type(count) is not int or count < 0:
            raise ValueError(f"broker execution count is invalid for {symbol}")

    budget = invocation.mutation_budget
    if budget == 0:
        return ()
    if all(
        execution_order_counts[symbol]
        >= MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
        for symbol in REQUIRED_SYMBOLS
    ):
        return ()

    planned: list[tuple[str, int]] = []
    for symbol in REQUIRED_SYMBOLS:
        current = execution_order_counts[symbol]
        for ordinal in range(
            current + 1,
            MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL + 1,
        ):
            if len(planned) >= budget:
                return tuple(planned)
            planned.append((symbol, ordinal))
    return tuple(planned)
