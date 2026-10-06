"""Causal pre-trade / in-trade Situation Model for VT31_NAS100.

This is not one of the trader's three persistent memories. It is the ephemeral
working representation of what the market is doing now, built only from
information observable no later than the as-of timestamp.

Unknown information stays explicit. No terminal PnL, future bar, post-outcome
journey label or date-level historical answer may enter this object.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Nas100SituationModel:
    # Identity / temporal
    as_of: str
    weekday: str
    session: str
    decision_minute_ny: int
    side: str
    setup_family: str
    confirmation_state: str

    # Market structure / regime
    prior_day_state: str
    h4_state: str
    h1_state: str
    premarket_state: str
    cash_open_state: str
    position_in_prior_day_range: str
    range_state: str
    volatility_state: str
    current_path_vs_previous: Decimal | None
    reference_width_vs_prior5: Decimal | None
    raid_depth_ref: Decimal | None
    recent_path_efficiency: Decimal | None
    recent_overlap_rate: Decimal | None

    # Liquidity / sequence
    first_breach_side: str
    double_sided_before_decision: bool
    reference_reclaimed: bool
    reference_reclaim_age_minutes: int | None
    last_structure_event_family: str
    last_structure_event_age_minutes: int | None
    recent_liquidity_event_count_10m: int | None

    # Displacement / entry
    displacement_state: str
    entry_evidence_family: str
    confirmation_latency_minutes: int | None
    entry_evidence_freshness: str

    # Structural risk / geometry
    stop_plan: str
    risk_ref: Decimal | None
    # Optional strategy-native R target. R may govern trader logic; sizing may
    # not be used to manufacture certification.
    planned_target_r: Decimal | None
    structural_destination: str
    destination_distance_ref: Decimal | None

    # Journey / target intelligence
    journey_stage: str
    dol1_state: str
    dol2_state: str
    dol3_state: str
    extension_capacity_state: str
    exhaustion_state: str

    # Cross-index context; never substitutes NAS100 memory.
    cross_index_state: str

    # Explicit M15 layer for maximum-intelligence certification. Existing
    # callers default to UNWIRED until causal M15 state is actually supplied.
    m15_state: str = "UNWIRED"

    # Causal live-position journey location in strategy-native R, normalized
    # by the frozen initial structural risk. None is valid before fill; a live
    # post-entry maximum-intelligence observation must supply it.
    current_open_r: Decimal | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.decision_minute_ny < 24 * 60:
            raise ValueError("decision_minute_ny out of range")
        if not self.m15_state:
            raise ValueError("m15_state cannot be empty")
        for age in (
            self.reference_reclaim_age_minutes,
            self.last_structure_event_age_minutes,
            self.confirmation_latency_minutes,
        ):
            if age is not None and age < 0:
                raise ValueError("situation ages/latencies cannot be negative")
        if (
            self.recent_liquidity_event_count_10m is not None
            and self.recent_liquidity_event_count_10m < 0
        ):
            raise ValueError("liquidity-event count cannot be negative")
        if self.planned_target_r is not None:
            if (
                not self.planned_target_r.is_finite()
                or self.planned_target_r <= 0
            ):
                raise ValueError(
                    "planned_target_r must be positive finite when supplied"
                )
        for value in (
            self.current_path_vs_previous,
            self.reference_width_vs_prior5,
            self.raid_depth_ref,
            self.recent_path_efficiency,
            self.recent_overlap_rate,
            self.risk_ref,
            self.destination_distance_ref,
            self.planned_target_r,
            self.current_open_r,
        ):
            if value is not None and not value.is_finite():
                raise ValueError("situation decimal values must be finite")

    def payload(self) -> dict[str, object]:
        raw = asdict(self)
        return {
            "schema": "qore.vt31.nas100.situation_model.v1",
            "memory_class": "EPHEMERAL_CAUSAL_SITUATION",
            "persistent_memory": False,
            "causal_as_of_only": True,
            "terminal_pnl_present": False,
            "historical_date_outcome_present": False,
            **{
                key: (
                    format(value, "f")
                    if isinstance(value, Decimal)
                    else value
                )
                for key, value in raw.items()
            },
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
