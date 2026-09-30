"""Canonical chronological path history for the CIBO Compound Cycle.

The history replays the existing causal event stream one event at a time and
captures an immutable state digest after each transition. It exposes raw path
facts and descriptive minima/giveback only; it does not claim causal utility,
market probability, policy quality or productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_cycle_audit import (
    compound_cycle_state_sha256,
)
from qore.infrastructure.cibo_compound_cycle_replay import (
    CompoundCycleEvent,
    replay_compound_cycle,
)
from qore.infrastructure.cibo_compound_cycle_state import CiboCompoundCycleState

COMPOUND_PATH_HISTORY_ID = "CIBO_COMPOUND_CHRONOLOGICAL_PATH_HISTORY_V1"


@dataclass(frozen=True, slots=True)
class CompoundPathSnapshot:
    sequence: int
    event_id: str
    observed_at: datetime
    state_sha256: str
    t19_ledger_sha256: str
    original_base_usd: Decimal
    compound_economic_value_usd: Decimal
    protected_floor_usd: Decimal
    closing_realized_capital_usd: Decimal
    strategic_reserve_usd: Decimal
    opportunity_reserve_usd: Decimal
    active_compound_capacity_usd: Decimal
    deployed_compound_capital_usd: Decimal
    remaining_stop_risk_capacity_usd: Decimal
    remaining_margin_capacity_usd: Decimal
    highest_generation: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence < 0
        ):
            raise CiboCompoundCapitalError(
                "compound path snapshot sequence invalid"
            )
        if not self.event_id:
            raise CiboCompoundCapitalError(
                "compound path snapshot event id required"
            )
        _aware(self.observed_at, "snapshot observed_at")
        _sha(self.state_sha256, "snapshot state_sha256")
        _sha(self.t19_ledger_sha256, "snapshot t19_ledger_sha256")
        for name in (
            "original_base_usd",
            "compound_economic_value_usd",
            "protected_floor_usd",
            "closing_realized_capital_usd",
            "strategic_reserve_usd",
            "opportunity_reserve_usd",
            "active_compound_capacity_usd",
            "deployed_compound_capital_usd",
            "remaining_stop_risk_capacity_usd",
            "remaining_margin_capacity_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"compound path snapshot {name} invalid"
                )
        if (
            not isinstance(self.highest_generation, int)
            or isinstance(self.highest_generation, bool)
            or self.highest_generation < 0
        ):
            raise CiboCompoundCapitalError(
                "compound path snapshot generation invalid"
            )


@dataclass(frozen=True, slots=True)
class CompoundPathDescriptiveSummary:
    minimum_original_base_usd: Decimal
    minimum_compound_economic_value_usd: Decimal
    minimum_protected_floor_usd: Decimal
    minimum_strategic_reserve_usd: Decimal
    minimum_opportunity_reserve_usd: Decimal
    minimum_active_compound_capacity_usd: Decimal
    minimum_remaining_stop_risk_capacity_usd: Decimal
    minimum_remaining_margin_capacity_usd: Decimal
    peak_closing_realized_capital_usd: Decimal
    terminal_closing_realized_capital_usd: Decimal
    maximum_realized_capital_giveback_usd: Decimal
    maximum_protected_floor_usd: Decimal
    highest_generation: int
    descriptive_only: bool = True
    causal_effect_identified: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        for name in (
            "minimum_original_base_usd",
            "minimum_compound_economic_value_usd",
            "minimum_protected_floor_usd",
            "minimum_strategic_reserve_usd",
            "minimum_opportunity_reserve_usd",
            "minimum_active_compound_capacity_usd",
            "minimum_remaining_stop_risk_capacity_usd",
            "minimum_remaining_margin_capacity_usd",
            "peak_closing_realized_capital_usd",
            "terminal_closing_realized_capital_usd",
            "maximum_realized_capital_giveback_usd",
            "maximum_protected_floor_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"compound path summary {name} invalid"
                )
        if self.maximum_realized_capital_giveback_usd > (
            self.peak_closing_realized_capital_usd
        ):
            raise CiboCompoundCapitalError(
                "compound path giveback exceeds path peak"
            )
        if (
            not isinstance(self.highest_generation, int)
            or isinstance(self.highest_generation, bool)
            or self.highest_generation < 0
        ):
            raise CiboCompoundCapitalError(
                "compound path summary generation invalid"
            )
        if (
            not self.descriptive_only
            or self.causal_effect_identified
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "compound path summary cannot claim causal/certification readiness"
            )


@dataclass(frozen=True, slots=True)
class CompoundPathHistory:
    history_id: str
    snapshots: tuple[CompoundPathSnapshot, ...]
    summary: CompoundPathDescriptiveSummary
    event_count: int
    chronological: bool = True
    future_leakage_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.history_id != COMPOUND_PATH_HISTORY_ID:
            raise CiboCompoundCapitalError(
                "compound path history identity drift"
            )
        if len(self.snapshots) != self.event_count + 1:
            raise CiboCompoundCapitalError(
                "compound path history snapshot/event count drift"
            )
        if not self.snapshots:
            raise CiboCompoundCapitalError(
                "compound path history snapshots required"
            )
        sequences = tuple(item.sequence for item in self.snapshots)
        if sequences != tuple(range(len(self.snapshots))):
            raise CiboCompoundCapitalError(
                "compound path snapshot sequence drift"
            )
        observed = tuple(item.observed_at for item in self.snapshots)
        if observed != tuple(sorted(observed)):
            raise CiboCompoundCapitalError(
                "compound path history chronology reversed"
            )
        if (
            not self.chronological
            or self.future_leakage_used
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "compound path history governance drift"
            )

    def fingerprint(self) -> str:
        payload = {
            "history_id": self.history_id,
            "snapshots": [_snapshot_json(item) for item in self.snapshots],
            "summary": _summary_json(self.summary),
            "event_count": self.event_count,
            "chronological": self.chronological,
            "future_leakage_used": self.future_leakage_used,
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def materialize_compound_path_history(
    *,
    initial_state: CiboCompoundCycleState,
    initial_observed_at: datetime,
    events: tuple[CompoundCycleEvent, ...],
) -> CompoundPathHistory:
    if not isinstance(initial_state, CiboCompoundCycleState):
        raise CiboCompoundCapitalError(
            "compound path history requires canonical initial state"
        )
    _aware(initial_observed_at, "initial_observed_at")
    if not isinstance(events, tuple) or not events:
        raise CiboCompoundCapitalError(
            "compound path history requires non-empty events"
        )
    if (
        initial_state.last_event_at is not None
        and initial_observed_at < initial_state.last_event_at
    ):
        raise CiboCompoundCapitalError(
            "compound path initial observation predates state history"
        )
    first_at = events[0].occurred_at
    if initial_observed_at > first_at:
        raise CiboCompoundCapitalError(
            "compound path initial observation postdates first event"
        )

    state = initial_state
    snapshots = [_snapshot(state, sequence=0, event_id="INITIAL_STATE", at=initial_observed_at)]
    for sequence, event in enumerate(events, start=1):
        result = replay_compound_cycle(
            initial_state=state,
            events=(event,),
        )
        state = result.final_state
        snapshots.append(
            _snapshot(
                state,
                sequence=sequence,
                event_id=event.event_id,
                at=event.occurred_at,
            )
        )

    snapshot_tuple = tuple(snapshots)
    return CompoundPathHistory(
        history_id=COMPOUND_PATH_HISTORY_ID,
        snapshots=snapshot_tuple,
        summary=_summarize(snapshot_tuple),
        event_count=len(events),
        chronological=True,
        future_leakage_used=False,
        productive_authority=False,
    )


def _snapshot(
    state: CiboCompoundCycleState,
    *,
    sequence: int,
    event_id: str,
    at: datetime,
) -> CompoundPathSnapshot:
    remaining = state.t19_ledger.remaining_budget()
    return CompoundPathSnapshot(
        sequence=sequence,
        event_id=event_id,
        observed_at=at,
        state_sha256=compound_cycle_state_sha256(state),
        t19_ledger_sha256=_t19_ledger_sha256(state),
        original_base_usd=state.current_original_base_usd,
        compound_economic_value_usd=(
            state.compound_ledger.current_economic_value_usd
        ),
        protected_floor_usd=state.floor_ledger.total_floor_usd,
        closing_realized_capital_usd=state.closing_realized_capital_usd,
        strategic_reserve_usd=state.compound_ledger.balance(
            CompoundCapitalState.STRATEGIC_RESERVE
        ),
        opportunity_reserve_usd=state.compound_ledger.balance(
            CompoundCapitalState.OPPORTUNITY_RESERVE
        ),
        active_compound_capacity_usd=state.compound_ledger.balance(
            CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY
        ),
        deployed_compound_capital_usd=state.compound_ledger.balance(
            CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL
        ),
        remaining_stop_risk_capacity_usd=remaining.stop_risk_headroom_usd,
        remaining_margin_capacity_usd=remaining.margin_headroom_usd,
        highest_generation=state.highest_generation,
    )


def _summarize(
    snapshots: tuple[CompoundPathSnapshot, ...],
) -> CompoundPathDescriptiveSummary:
    peak = Decimal(0)
    max_giveback = Decimal(0)
    for item in snapshots:
        peak = max(peak, item.closing_realized_capital_usd)
        max_giveback = max(
            max_giveback,
            peak - item.closing_realized_capital_usd,
        )
    return CompoundPathDescriptiveSummary(
        minimum_original_base_usd=min(item.original_base_usd for item in snapshots),
        minimum_compound_economic_value_usd=min(
            item.compound_economic_value_usd for item in snapshots
        ),
        minimum_protected_floor_usd=min(
            item.protected_floor_usd for item in snapshots
        ),
        minimum_strategic_reserve_usd=min(
            item.strategic_reserve_usd for item in snapshots
        ),
        minimum_opportunity_reserve_usd=min(
            item.opportunity_reserve_usd for item in snapshots
        ),
        minimum_active_compound_capacity_usd=min(
            item.active_compound_capacity_usd for item in snapshots
        ),
        minimum_remaining_stop_risk_capacity_usd=min(
            item.remaining_stop_risk_capacity_usd for item in snapshots
        ),
        minimum_remaining_margin_capacity_usd=min(
            item.remaining_margin_capacity_usd for item in snapshots
        ),
        peak_closing_realized_capital_usd=max(
            item.closing_realized_capital_usd for item in snapshots
        ),
        terminal_closing_realized_capital_usd=(
            snapshots[-1].closing_realized_capital_usd
        ),
        maximum_realized_capital_giveback_usd=max_giveback,
        maximum_protected_floor_usd=max(
            item.protected_floor_usd for item in snapshots
        ),
        highest_generation=max(item.highest_generation for item in snapshots),
        descriptive_only=True,
        causal_effect_identified=False,
        certification_ready=False,
    )


def _snapshot_json(item: CompoundPathSnapshot) -> dict[str, object]:
    payload = asdict(item)
    payload["observed_at"] = item.observed_at.isoformat()
    for name in (
        "original_base_usd",
        "compound_economic_value_usd",
        "protected_floor_usd",
        "closing_realized_capital_usd",
        "strategic_reserve_usd",
        "opportunity_reserve_usd",
        "active_compound_capacity_usd",
        "deployed_compound_capital_usd",
        "remaining_stop_risk_capacity_usd",
        "remaining_margin_capacity_usd",
    ):
        payload[name] = format(getattr(item, name), "f")
    return payload


def _t19_ledger_sha256(state: CiboCompoundCycleState) -> str:
    ledger = state.t19_ledger
    payload = {
        "total_stop_risk_capacity_usd": format(
            ledger.total_stop_risk_capacity_usd,
            "f",
        ),
        "total_margin_capacity_usd": format(
            ledger.total_margin_capacity_usd,
            "f",
        ),
        "concentration_limit_by_group": [
            [group, format(limit, "f")]
            for group, limit in sorted(ledger.concentration_limit_by_group)
        ],
        "reservations": [
            {
                "signal_fingerprint": item.signal_fingerprint,
                "trader_id": item.trader_id.value,
                "qore_symbol": item.qore_symbol,
                "stop_risk_usd": format(item.stop_risk_usd, "f"),
                "margin_usd": format(item.margin_usd, "f"),
                "concentration_group": item.concentration_group,
                "concentration_risk_usd": format(
                    item.concentration_risk_usd,
                    "f",
                ),
                "state": item.state.value,
            }
            for item in sorted(
                ledger.reservations,
                key=lambda row: (
                    row.signal_fingerprint,
                    row.trader_id.value,
                    row.qore_symbol,
                    row.state.value,
                ),
            )
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _summary_json(item: CompoundPathDescriptiveSummary) -> dict[str, object]:
    payload = asdict(item)
    for name, value in tuple(payload.items()):
        if isinstance(value, Decimal):
            payload[name] = format(value, "f")
    return payload


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"compound path {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCompoundCapitalError(
            f"compound path {name} must be timezone-aware"
        )
