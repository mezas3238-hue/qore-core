"""Phase-2 CE2I sizing-path reconstruction.

This module reconstructs the economic provenance of a cTrader DEMO sizing
decision from passive sink telemetry. It does not calculate or alter broker
orders. Historical rows that predate the richer CE2I telemetry remain readable
and are explicitly marked PARTIAL instead of being silently completed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from collections.abc import Mapping


class SizingReconstructionError(ValueError):
    """Invalid passive sizing evidence."""


class ReconstructionStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True, slots=True)
class SizingPathContract:
    trader: str
    symbol: str
    sizing_path: str
    budget_model: str
    base_risk_model: str
    strategy_scaler_model: str
    broker_sizing_model: str


SIZING_PATH_CONTRACTS: dict[str, SizingPathContract] = {
    "VT08_FOREX": SizingPathContract(
        trader="VT08_FOREX",
        symbol="MULTI",
        sizing_path="VT08_CIBO_AUTHORIZATION_PLUS_DEMO_NATIVE_RISK_SIZING",
        budget_model="SYMBOL_BPS_X_ASSIGNED_CAPITAL",
        base_risk_model="AUDJPY_25BPS_GBPUSD_25BPS_GBPJPY_20BPS",
        strategy_scaler_model="VT08_CIBO_ALLOW_DENY_POSTURE_NO_EXTRA_VOLUME_SCALER",
        broker_sizing_model="SIZE_VOLUME_FOR_RISK",
    ),
    "R34_XAUUSD": SizingPathContract(
        trader="R34_XAUUSD",
        symbol="XAUUSD",
        sizing_path="R34_BASE_RISK_X_GOVERNOR_SCALE_THEN_DEMO_NATIVE_VOLUME",
        budget_model="BASE_RISK_X_GOVERNOR_SCALE",
        base_risk_model="ASSIGNED_CAPITAL_X_0.002",
        strategy_scaler_model="R34_STATE_RISK_SCALE",
        broker_sizing_model="SIZE_VOLUME_FOR_RISK",
    ),
    "R38_EURUSD": SizingPathContract(
        trader="R38_EURUSD",
        symbol="EURUSD",
        sizing_path="R38_EURUSD_BASE_RISK_X_COGNITIVE_SCALE_THEN_DEMO_NATIVE_VOLUME",
        budget_model="BASE_RISK_X_FRAGILITY_X_STRUCTURAL_OVERLAY",
        base_risk_model="ASSIGNED_CAPITAL_X_0.002",
        strategy_scaler_model="FRAGILITY_SCALE_X_F5_SHORT_X_UNSTABLE_LONG_ROUTE",
        broker_sizing_model="SIZE_VOLUME_FOR_RISK",
    ),
    "R43_GBPUSD": SizingPathContract(
        trader="R43_GBPUSD",
        symbol="GBPUSD",
        sizing_path="R43_GBPUSD_BASE_RISK_X_COGNITIVE_SCALE_THEN_DEMO_NATIVE_VOLUME",
        budget_model="BASE_RISK_X_STRUCTURAL_X_OVERLAY_X_DRAWDOWN",
        base_risk_model="ASSIGNED_CAPITAL_X_0.002",
        strategy_scaler_model="STRUCTURAL_X_MIN_SIDE_RANK_X_DRAWDOWN",
        broker_sizing_model="SIZE_VOLUME_FOR_RISK",
    ),
    "R38_GBPJPY": SizingPathContract(
        trader="R38_GBPJPY",
        symbol="GBPJPY",
        sizing_path="R38_GBPJPY_BASE_RISK_X_COGNITIVE_SCALE_THEN_DEMO_NATIVE_VOLUME",
        budget_model="BASE_RISK_X_POLICY_X_FRAGILITY_OVERLAY",
        base_risk_model="ASSIGNED_CAPITAL_X_0.002",
        strategy_scaler_model="SELECTED_POLICY_X_FRAGILITY_OVERLAY",
        broker_sizing_model="SIZE_VOLUME_FOR_RISK",
    ),
    "R42_AUDJPY": SizingPathContract(
        trader="R42_AUDJPY",
        symbol="AUDJPY",
        sizing_path="R42_AUDJPY_BASE_RISK_X_COGNITIVE_SCALE_THEN_DEMO_NATIVE_VOLUME",
        budget_model="BASE_RISK_X_AUTHORITY_X_TWO_FRAGILITY_LAYERS",
        base_risk_model="ASSIGNED_CAPITAL_X_0.002",
        strategy_scaler_model="AUTHORITY_SCALE_X_FIRST_OVERLAY_X_SECOND_OVERLAY",
        broker_sizing_model="SIZE_VOLUME_FOR_RISK",
    ),
    "VT31_NAS100": SizingPathContract(
        trader="VT31_NAS100",
        symbol="NAS100",
        sizing_path="VT31_CERTIFIED_RISK_RESOLUTION_THEN_DEMO_NATIVE_VOLUME",
        budget_model="ONE_R_X_CERTIFIED_RISK_RESOLUTION",
        base_risk_model="ASSIGNED_CAPITAL_X_0.002",
        strategy_scaler_model=(
            "NOMINAL_TIER_X_ALLOCATION_X_0.60_X_STATE_X_LOSS_CLUSTER_X_BREAKER"
        ),
        broker_sizing_model="SIZE_VOLUME_FOR_RISK_WITH_4_LEG_MINIMUM",
    ),
}


@dataclass(frozen=True, slots=True)
class SizingDecisionReconstruction:
    trader: str
    symbol: str
    sizing_path: str
    sizing_path_observed: bool
    status: ReconstructionStatus
    requested_volume: Decimal
    assigned_capital: Decimal
    requested_stop_risk: Decimal
    strategy_requested_risk_usd: Decimal | None
    stop_loss_per_volume: Decimal | None
    requested_margin: Decimal | None
    margin_per_volume: Decimal | None
    volume_step: Decimal | None
    minimum_volume: Decimal | None
    minimum_volume_uplifted: bool | None
    risk_budget_utilization: Decimal | None
    unused_strategy_risk_usd: Decimal | None
    margin_fraction_of_assigned_capital: Decimal | None
    missing_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.trader not in SIZING_PATH_CONTRACTS:
            raise SizingReconstructionError("unknown CE2I trader")
        if self.requested_volume <= 0:
            raise SizingReconstructionError("requested_volume must be positive")
        if self.assigned_capital <= 0:
            raise SizingReconstructionError("assigned_capital must be positive")
        if self.requested_stop_risk <= 0:
            raise SizingReconstructionError("requested_stop_risk must be positive")
        expected = SIZING_PATH_CONTRACTS[self.trader].sizing_path
        if self.sizing_path != expected:
            raise SizingReconstructionError("sizing_path differs from frozen source contract")
        if type(self.sizing_path_observed) is not bool:
            raise SizingReconstructionError("sizing_path_observed must be bool")
        if self.status is ReconstructionStatus.COMPLETE and self.missing_fields:
            raise SizingReconstructionError("complete reconstruction cannot have missing fields")
        if self.status is ReconstructionStatus.PARTIAL and not self.missing_fields:
            raise SizingReconstructionError("partial reconstruction requires missing fields")


_REQUIRED_COMPLETE_FIELDS = (
    "strategy_requested_risk_usd",
    "stop_loss_per_volume",
    "requested_margin",
    "margin_per_volume",
    "volume_step",
    "minimum_volume",
    "minimum_volume_uplifted",
)


def reconstruct_sizing_decision(
    event: Mapping[str, object],
) -> SizingDecisionReconstruction:
    """Reconstruct one CTRADER_DEMO_FREE_SUBMIT passive telemetry row."""

    if not isinstance(event, Mapping):
        raise SizingReconstructionError("event must be a mapping")
    if str(event.get("event", "")) != "CTRADER_DEMO_FREE_SUBMIT":
        raise SizingReconstructionError("event is not a DEMO free submit row")

    trader = _required_text(event, "trader")
    symbol = _required_text(event, "symbol")
    contract = SIZING_PATH_CONTRACTS.get(trader)
    if contract is None:
        raise SizingReconstructionError("trader is outside CE2I reconstruction scope")
    raw_sizing_path = event.get("sizing_path")
    if raw_sizing_path is None or raw_sizing_path == "":
        sizing_path = contract.sizing_path
        sizing_path_observed = False
    else:
        sizing_path = _required_text(event, "sizing_path")
        sizing_path_observed = True

    requested_volume = _required_decimal(event, "requested_volume")
    assigned_capital = _required_decimal(event, "assigned_capital")
    requested_stop_risk = _required_decimal(event, "requested_stop_risk")

    optional_decimals = {
        name: _optional_decimal(event, name)
        for name in (
            "strategy_requested_risk_usd",
            "stop_loss_per_volume",
            "requested_margin",
            "margin_per_volume",
            "volume_step",
            "minimum_volume",
        )
    }
    uplift = _optional_bool(event, "minimum_volume_uplifted")

    missing_items: list[str] = []
    if not sizing_path_observed:
        missing_items.append("sizing_path")
    missing_items.extend(
        name
        for name in _REQUIRED_COMPLETE_FIELDS
        if (
            uplift is None
            if name == "minimum_volume_uplifted"
            else optional_decimals[name] is None
        )
    )
    missing = tuple(missing_items)
    status = (
        ReconstructionStatus.COMPLETE
        if not missing
        else ReconstructionStatus.PARTIAL
    )

    strategy_risk = optional_decimals["strategy_requested_risk_usd"]
    requested_margin = optional_decimals["requested_margin"]

    risk_utilization = (
        requested_stop_risk / strategy_risk
        if strategy_risk is not None and strategy_risk > 0
        else None
    )
    unused_risk = (
        max(Decimal(0), strategy_risk - requested_stop_risk)
        if strategy_risk is not None
        else None
    )
    margin_fraction = (
        requested_margin / assigned_capital
        if requested_margin is not None
        else None
    )

    return SizingDecisionReconstruction(
        trader=trader,
        symbol=symbol,
        sizing_path=sizing_path,
        sizing_path_observed=sizing_path_observed,
        status=status,
        requested_volume=requested_volume,
        assigned_capital=assigned_capital,
        requested_stop_risk=requested_stop_risk,
        strategy_requested_risk_usd=strategy_risk,
        stop_loss_per_volume=optional_decimals["stop_loss_per_volume"],
        requested_margin=requested_margin,
        margin_per_volume=optional_decimals["margin_per_volume"],
        volume_step=optional_decimals["volume_step"],
        minimum_volume=optional_decimals["minimum_volume"],
        minimum_volume_uplifted=uplift,
        risk_budget_utilization=risk_utilization,
        unused_strategy_risk_usd=unused_risk,
        margin_fraction_of_assigned_capital=margin_fraction,
        missing_fields=missing,
    )


def reconstruct_sizing_ledger(
    events: tuple[Mapping[str, object], ...],
) -> tuple[SizingDecisionReconstruction, ...]:
    """Reconstruct every in-scope sizing row in input chronology."""

    if not isinstance(events, tuple):
        raise SizingReconstructionError("events must be a tuple")
    rows: list[SizingDecisionReconstruction] = []
    for event in events:
        if str(event.get("event", "")) != "CTRADER_DEMO_FREE_SUBMIT":
            continue
        rows.append(reconstruct_sizing_decision(event))
    return tuple(rows)


def _required_text(event: Mapping[str, object], field: str) -> str:
    value = event.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SizingReconstructionError(f"{field} must be non-empty text")
    return value


def _required_decimal(event: Mapping[str, object], field: str) -> Decimal:
    value = _optional_decimal(event, field)
    if value is None or value <= 0:
        raise SizingReconstructionError(f"{field} must be positive decimal")
    return value


def _optional_decimal(
    event: Mapping[str, object],
    field: str,
) -> Decimal | None:
    value = event.get(field)
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise SizingReconstructionError(f"{field} is not decimal") from error
    if not parsed.is_finite() or parsed < 0:
        raise SizingReconstructionError(f"{field} must be finite non-negative")
    return parsed


def _optional_bool(
    event: Mapping[str, object],
    field: str,
) -> bool | None:
    value = event.get(field)
    if value is None:
        return None
    if type(value) is not bool:
        raise SizingReconstructionError(f"{field} must be bool/null")
    return value
