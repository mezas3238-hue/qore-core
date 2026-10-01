"""Immutable Architect-2 receipt for bounded T16 DEMO execution evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

RUN_ID = 36934306276
RUN_HEAD_SHA = "8cc3794feb645710952859fe40e20223e1c59093"
ARTIFACT_ID = 11197137857
ARTIFACT_DIGEST = (
    "sha256:96ad9cc8a8ac5bdafc2f35cac556bf54a6250cff62abd65ff09db7bd8922434b"
)
PAYLOAD_SHA256 = (
    "sha256:c783f5c9a78780a398e117efa2feb3df7095b1813b216e4e4d148c9dace005af"
)


@dataclass(frozen=True, slots=True)
class T16DemoExecutionReceipt:
    provider_key: str
    environment: str
    account_fingerprint_sha256: str
    provider_catalog_sha256: str
    required_hedges: tuple[str, ...]
    round_trip_count: int
    minimum_volume_only: bool
    both_sides_covered: bool
    created_positions_closed: bool
    realized_slippage_coverage_complete: bool
    realized_execution_coverage_complete: bool
    full_hedge_cost_model_ready: bool
    max_round_trip_cost_bps: tuple[tuple[str, Decimal], ...]
    holdout_outcomes_used: bool
    holdout_market_data_read: bool
    historical_provider_economics_claimed: bool
    fundednext_touched: bool
    vps_touched: bool
    live_authorized: bool
    real_capital_authorized: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError("T16 receipt provider drift")
        if self.required_hedges != ("US30", "US500"):
            raise CiboCapitalManagementError("T16 receipt hedge universe drift")
        if self.round_trip_count != 4:
            raise CiboCapitalManagementError("T16 receipt round-trip count drift")
        required_true = (
            self.minimum_volume_only,
            self.both_sides_covered,
            self.created_positions_closed,
            self.realized_slippage_coverage_complete,
            self.realized_execution_coverage_complete,
            self.full_hedge_cost_model_ready,
        )
        if not all(required_true):
            raise CiboCapitalManagementError("T16 receipt readiness incomplete")
        costs = dict(self.max_round_trip_cost_bps)
        if tuple(costs) != self.required_hedges:
            raise CiboCapitalManagementError("T16 receipt cost surface drift")
        if any(
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value < 0
            for value in costs.values()
        ):
            raise CiboCapitalManagementError("T16 receipt cost invalid")
        prohibited = (
            self.holdout_outcomes_used,
            self.holdout_market_data_read,
            self.historical_provider_economics_claimed,
            self.fundednext_touched,
            self.vps_touched,
            self.live_authorized,
            self.real_capital_authorized,
            self.productive_authority,
        )
        if any(prohibited):
            raise CiboCapitalManagementError("T16 receipt governance contamination")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["max_round_trip_cost_bps"] = [
            [symbol, format(value, "f")]
            for symbol, value in self.max_round_trip_cost_bps
        ]
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


T16_DEMO_EXECUTION_RECEIPT = T16DemoExecutionReceipt(
    provider_key="ctrader-demo",
    environment="demo",
    account_fingerprint_sha256=(
        "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
    ),
    provider_catalog_sha256=(
        "sha256:47ddbd42c083d7709f1c7b9922c4ef6826219f91c25aff9c894513a480fcbcf1"
    ),
    required_hedges=("US30", "US500"),
    round_trip_count=4,
    minimum_volume_only=True,
    both_sides_covered=True,
    created_positions_closed=True,
    realized_slippage_coverage_complete=True,
    realized_execution_coverage_complete=True,
    full_hedge_cost_model_ready=True,
    max_round_trip_cost_bps=(
        ("US30", Decimal("0.5302387754902352402683240905")),
        ("US500", Decimal("1.043090220589766601999332790")),
    ),
    holdout_outcomes_used=False,
    holdout_market_data_read=False,
    historical_provider_economics_claimed=False,
    fundednext_touched=False,
    vps_touched=False,
    live_authorized=False,
    real_capital_authorized=False,
    productive_authority=False,
)
