"""Governance contract for Phase22 cTrader DEMO execution calibration.

This lane is deliberately disjoint from the historical holdout. It may create
bounded DEMO-only calibration orders, but it may not inspect Phase22 holdout
outcomes or claim that current provider fills occurred in 2015-2016.
"""

from __future__ import annotations

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
