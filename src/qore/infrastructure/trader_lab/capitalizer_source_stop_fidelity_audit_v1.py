"""Source-fidelity audit for QORE Capitalizer initial stop placement.

This audit compares the frozen Capitalizer contracts against the reviewed TTrades
primary-source semantics. It is intentionally diagnostic: discovering a fidelity gap
does not itself choose a numeric buffer, widen stops, promote a rule, or certify execution.

Primary sources re-verified 2026-09-20:
- https://ttrades.com/protected-swings-understanding-trends-and-invalidations/
- https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/

Source semantics:
- the confirmed protected swing is the structural invalidation anchor;
- scalp stops use logical protected swings;
- the stop is described as beyond / right above (bearish example) the protected swing;
- the source does not define a universal numeric outward padding.

Current QORE distinctions:
- source-faithful trade plan currently maps initial_stop_price exactly to protected_swing_price;
- M5 economic replay uses SOURCE_M5_DIRECTIONAL_EXTREME and is explicitly a geometry proxy,
  not the source-faithful M1 protected-swing stop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

IDENTITY = "QORE_CAPITALIZER_SOURCE_STOP_FIDELITY_AUDIT_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerSourceStopFidelityAudit:
    identity: str = IDENTITY
    source_invalidation_anchor: str = "CONFIRMED_LOGICAL_PROTECTED_SWING"
    source_stop_relation: str = "BEYOND_PROTECTED_SWING"
    source_universal_numeric_padding_defined: bool = False
    source_lower_timeframe_refinement_supported: bool = True
    current_trade_plan_relation: str = "EXACTLY_AT_PROTECTED_SWING"
    current_trade_plan_source_faithful: bool = False
    current_m5_replay_stop: str = "SOURCE_M5_DIRECTIONAL_EXTREME"
    current_m5_replay_source_faithful_stop: bool = False
    m1_protected_swing_required_for_source_replay: bool = True
    native_m1_evidence_present: bool = False
    exact_outward_stop_distance_resolved: bool = False
    fidelity_gap: str = "STOP_PRICE_EQUALS_INVALIDATION_LEVEL_INSTEAD_OF_BEING_BEYOND_IT"
    source_strategy_status: str = "REOPEN_STOP_PLACEMENT_FIDELITY"
    numeric_buffer_selected: bool = False
    stop_widening_authorized: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False


def build_source_stop_fidelity_audit() -> CapitalizerSourceStopFidelityAudit:
    return CapitalizerSourceStopFidelityAudit()


def payload() -> dict[str, object]:
    return asdict(build_source_stop_fidelity_audit())
