"""Incremental live decision policy for certified VT31 NAS100.

This module reuses the exact certified research primitives already frozen in
the repository. It only converts CLOSED M1 evidence available up to the current
decision into a durable virtual execution basket.

No terminal PnL, future bar, calendar-edge or fold identity is used.
"""
# ruff: noqa: B009
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

import vt31_nas100_causal_hybrid_rearm_v1 as rearm
import vt31_nas100_causal_hybrid_replay_v1 as hybrid
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_structural_rearm_density_frontier_v1 as frontier
import vt31_nas100_structural_rearm_quality_frontier_v1 as quality

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    structurally_rearmed,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)
from qore.infrastructure.vt31_nas100_state import (
    Vt31Nas100LiveState,
    Vt31VirtualBasketState,
    Vt31VirtualOrderState,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
)

STRATEGY_IDENTITY = "VT31_NAS100_STRUCTURAL_TARGET_V1"
CERTIFIED_STRATEGY_FINGERPRINT = (
    "089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08"
)
EXECUTION_BINDING_FINGERPRINT = (
    "604f8b06fbbb6d808da6389d9abf02a498612d7dc8a735de886eb174f54cab8c"
)
WAIT_RELEASE_MINUTE = 10 * 60 + 25
MONTHLY_ALT_BUDGET = Decimal("0.60")
ACTIVITY_L = corrective.ACTIVITY_L
REARM_RISK_MAP = corrective.REARM_RISK_MAP


def evaluate_live_basket(
    *,
    closed_m1: tuple[OhlcSnapshot, ...],
    evidence_fingerprint: str,
    live_state: Vt31Nas100LiveState,
) -> tuple[Vt31VirtualBasketState | None, str]:
    """Return the currently authorized basket from evidence available now."""
    if not closed_m1:
        return None, "NO_CLOSED_M1"
    latest = closed_m1[-1]
    local_day = _day(latest.opened_at)
    by_day = _by_day(closed_m1)
    day_bars = by_day.get(local_day, ())
    reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
    session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
    if len(reference) != 60:
        return None, "REFERENCE_INCOMPLETE"
    if not session:
        return None, "SESSION_NOT_STARTED"

    current_local_minute = (
        latest.closed_at.astimezone(
            __import__("zoneinfo").ZoneInfo("America/New_York")
        ).hour
        * 60
        + latest.closed_at.astimezone(
            __import__("zoneinfo").ZoneInfo("America/New_York")
        ).minute
    )
    if current_local_minute > 11 * 60:
        return None, "SESSION_CLOSED"

    # If the first position already existed today, only a structurally fresh
    # rearm may be authorized.
    if local_day.isoformat() in live_state.first_trade_dates:
        return _evaluate_rearm(
            reference=reference,
            session=session,
            day_bars=day_bars,
            by_day=by_day,
            evidence_fingerprint=evidence_fingerprint,
            live_state=live_state,
            local_day=local_day,
        )

    context_by_day = specialist._context_map(by_day)
    if local_day not in context_by_day:
        return None, "CONTEXT_UNAVAILABLE"
    (
        previous_path_range,
        prior_ref_median,
        prior_admitted_day_bars,
    ) = context_by_day[local_day]

    policy = Vt31R22ExecutionPolicy()
    prefix: list[object] = list(reference)
    saw_wait = False
    authorization_at: datetime | None = None
    authorization_source: Vt31R22SourceSetup | None = None
    tier: str | None = None
    reason: str | None = None
    core_setup: Vt31R22ExecutableSetup | None = None
    core_state: dict[str, object] | None = None

    for bar in session:
        prefix.append(bar)
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=closed_at,
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence_fingerprint,
        )
        if evaluation.setup is None:
            if saw_wait and evaluation.both_sides_swept:
                return None, "SOURCE_INVALIDATED_AFTER_WAIT"
            continue

        executable, _ = make_executable_setup(evaluation.setup, policy)
        if executable is None:
            authorization_at = closed_at
            authorization_source = evaluation.setup
            tier = "SECONDARY"
            reason = "CORE_SOURCE_NOT_SINGLE_ROUTE_EXECUTABLE"
            break

        session_prefix = tuple(
            item
            for item in prefix
            if (10, 0, 0)
            <= _wall(getattr(item, "opened_at"))
            < (11, 0, 0)
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            evaluation.setup,
            executable,
            closed_at,
        )
        action = cast(str, state["action"])
        if action == "WAIT":
            saw_wait = True
            if specialist.baseline._local_minute(bar) >= WAIT_RELEASE_MINUTE:
                authorization_at = closed_at
                authorization_source = evaluation.setup
                tier = "SCOUT"
                reason = "CORE_PERSISTENT_WAIT_625"
                break
            continue
        if action == "ABSTAIN":
            authorization_at = closed_at
            authorization_source = evaluation.setup
            tier = "SECONDARY"
            reason = "CORE_CAUSAL_ABSTAIN"
            break
        if action != "EXECUTE":
            raise ValueError(f"VT31 unsupported reasoning action={action}")

        core_setup = hybrid._activation_setup(executable, closed_at)
        core_state = state
        authorization_at = closed_at
        authorization_source = evaluation.setup
        tier = "CORE"
        reason = "CORE_EXECUTE"
        break

    if authorization_at is None or authorization_source is None or tier is None or reason is None:
        return None, "NO_AUTHORIZATION"

    month = local_day.isoformat()[:7]
    if tier in {"SECONDARY", "SCOUT"}:
        remaining = Decimal(
            live_state.alt_budget_map().get(month, format(MONTHLY_ALT_BUDGET, "f"))
        )
        nominal = (
            hybrid.SECONDARY_RISK if tier == "SECONDARY" else Decimal("0.02")
        )
        if nominal > remaining:
            return None, "ALT_MONTHLY_BUDGET_EXHAUSTED"

    if tier == "CORE":
        assert core_setup is not None and core_state is not None
        order = _virtual_order(
            setup=core_setup,
            tier=tier,
            reason=reason,
            state=core_state,
            local_day=local_day,
            nominal_risk=Decimal("1.00"),
            rearm_quality=None,
        )
        return (
            Vt31VirtualBasketState(
                basket_id=_basket_id(
                    local_day=local_day,
                    tier=tier,
                    reason=reason,
                    authorization_at=authorization_at,
                    source=authorization_source,
                ),
                local_date=local_day.isoformat(),
                tier=tier,
                authorization_reason=reason,
                authorized_at=authorization_at.isoformat(),
                candidates=(order,),
            ),
            "AUTHORIZED_CORE",
        )

    # SECONDARY/SCOUT OCO: authorization is fixed at the first causal release,
    # but candidate families may continue to form afterward. Rebuild only the
    # same source event through the latest closed M1.
    source, invalidated = _source_through_now(
        reference=reference,
        session=session,
        evidence_fingerprint=evidence_fingerprint,
        source_key=_source_key(authorization_source),
    )
    if invalidated:
        return None, "SOURCE_INVALIDATED_BEFORE_FILL"
    if source is None:
        source = authorization_source

    state_for_family: dict[str, dict[str, object]] = {}
    orders: list[Vt31VirtualOrderState] = []
    nominal = hybrid.SECONDARY_RISK if tier == "SECONDARY" else Decimal("0.02")
    for evidence in source.candidates:
        raw_setup = oco._candidate_order(source, evidence, policy)
        if raw_setup is None:
            continue
        setup = hybrid._activation_setup(raw_setup, authorization_at)
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at")) <= setup.decision_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            source,
            setup,
            setup.decision_at,
        )
        state_for_family[setup.selected_family.value] = state
        orders.append(
            _virtual_order(
                setup=setup,
                tier=tier,
                reason=reason,
                state=state,
                local_day=local_day,
                nominal_risk=nominal,
                rearm_quality=None,
            )
        )
    if not orders:
        return None, "NO_EXECUTABLE_OCO_CANDIDATE"
    return (
        Vt31VirtualBasketState(
            basket_id=_basket_id(
                local_day=local_day,
                tier=tier,
                reason=reason,
                authorization_at=authorization_at,
                source=source,
            ),
            local_date=local_day.isoformat(),
            tier=tier,
            authorization_reason=reason,
            authorized_at=authorization_at.isoformat(),
            candidates=tuple(
                sorted(
                    orders,
                    key=lambda item: (
                        item.formed_at,
                        item.family,
                        item.entry_price,
                    ),
                )
            ),
        ),
        f"AUTHORIZED_{tier}",
    )


def _evaluate_rearm(
    *,
    reference: tuple[object, ...],
    session: tuple[object, ...],
    day_bars: tuple[object, ...],
    by_day: dict[date, tuple[object, ...]],
    evidence_fingerprint: str,
    live_state: Vt31Nas100LiveState,
    local_day: date,
) -> tuple[Vt31VirtualBasketState | None, str]:
    if local_day.isoformat() in live_state.rearm_used_dates:
        return None, "REARM_ALREADY_USED"
    if live_state.last_exit_at is None:
        return None, "REARM_NO_PRIOR_EXIT"
    after_at = datetime.fromisoformat(live_state.last_exit_at)
    if _day(after_at) != local_day:
        return None, "REARM_EXIT_NOT_TODAY"
    if _wall(after_at) >= (11, 0, 0):
        return None, "REARM_EXIT_AFTER_SESSION"

    policy = Vt31R22ExecutionPolicy()
    selected = frontier._next_executable_after(
        reference=reference,
        session=session,
        after_at=after_at,
        evidence=evidence_fingerprint,
        policy=policy,
    )
    if selected is None:
        return None, "REARM_NO_NEW_EVENT"
    source, setup = selected
    if not structurally_rearmed(
        protected_exit_at_epoch=int(after_at.timestamp()),
        new_raid_at_epoch=int(source.structure.raid_at.timestamp()),
        new_confirmation_at_epoch=int(source.structure.confirmation_at.timestamp()),
        new_decision_at_epoch=int(setup.decision_at.timestamp()),
    ):
        return None, "REARM_STRUCTURE_INVARIANT_FAILED"

    context = specialist._context_map(by_day)
    if local_day not in context:
        return None, "REARM_CONTEXT_UNAVAILABLE"
    prev_range, prior_ref, prior_bars = context[local_day]
    session_prefix = tuple(
        bar
        for bar in session
        if cast(datetime, getattr(bar, "closed_at")) <= setup.decision_at
    )
    state = specialist._state_snapshot(
        day_bars,
        prev_range,
        prior_ref,
        prior_bars,
        session_prefix,
        source,
        setup,
        setup.decision_at,
    )
    score, _reasons = quality._quality_score(state, setup)
    risk_class = rearm._risk_class(score)
    nominal = REARM_RISK_MAP[risk_class]
    month = local_day.isoformat()[:7]
    remaining = Decimal(
        live_state.rearm_budget_map().get(
            month,
            format(_rearm_opening_budget(live_state, month), "f"),
        )
    )
    if nominal > remaining:
        return None, "REARM_MONTHLY_BUDGET_EXHAUSTED"

    order = _virtual_order(
        setup=setup,
        tier="REARM",
        reason="NEW_RAID_CONFIRMATION_DECISION_AFTER_TERMINAL_EXIT",
        state=state,
        local_day=local_day,
        nominal_risk=nominal,
        rearm_quality=risk_class,
    )
    return (
        Vt31VirtualBasketState(
            basket_id=_basket_id(
                local_day=local_day,
                tier="REARM",
                reason="NEW_RAID_CONFIRMATION_DECISION_AFTER_TERMINAL_EXIT",
                authorization_at=setup.decision_at,
                source=source,
            ),
            local_date=local_day.isoformat(),
            tier="REARM",
            authorization_reason=(
                "NEW_RAID_CONFIRMATION_DECISION_AFTER_TERMINAL_EXIT"
            ),
            authorized_at=setup.decision_at.isoformat(),
            candidates=(order,),
        ),
        f"AUTHORIZED_REARM_{risk_class}",
    )


def _source_through_now(
    *,
    reference: tuple[object, ...],
    session: tuple[object, ...],
    evidence_fingerprint: str,
    source_key: tuple[str, ...],
) -> tuple[Vt31R22SourceSetup | None, bool]:
    prefix: list[object] = list(reference)
    current: Vt31R22SourceSetup | None = None
    for bar in session:
        prefix.append(bar)
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=closed_at,
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence_fingerprint,
        )
        if evaluation.both_sides_swept:
            if current is not None:
                return current, True
            continue
        if evaluation.setup is None:
            continue
        if _source_key(evaluation.setup) != source_key:
            return current, True
        current = evaluation.setup
    return current, False


def _virtual_order(
    *,
    setup: Vt31R22ExecutableSetup,
    tier: str,
    reason: str,
    state: dict[str, object],
    local_day: date,
    nominal_risk: Decimal,
    rearm_quality: str | None,
) -> Vt31VirtualOrderState:
    reference = setup.source_setup.reference
    material = {
        "strategy": STRATEGY_IDENTITY,
        "certified_strategy_fingerprint": CERTIFIED_STRATEGY_FINGERPRINT,
        "execution_binding_fingerprint": EXECUTION_BINDING_FINGERPRINT,
        "date": local_day.isoformat(),
        "tier": tier,
        "reason": reason,
        "family": setup.selected_family.value,
        "side": setup.side.value,
        "decision_at": setup.decision_at.isoformat(),
        "entry": format(setup.entry_price, "f"),
        "stop": format(setup.stop_price, "f"),
        "dol1": format(setup.target_price, "f"),
    }
    fingerprint = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return Vt31VirtualOrderState(
        candidate_id=f"vt31-{fingerprint[:24]}",
        signal_fingerprint=fingerprint,
        local_date=local_day.isoformat(),
        tier=tier,
        authorization_reason=reason,
        family=setup.selected_family.value,
        side=setup.side.value,
        formed_at=setup.decision_at.isoformat(),
        decision_at=setup.decision_at.isoformat(),
        expires_at=setup.pending_expires_at.isoformat(),
        entry_price=format(setup.entry_price, "f"),
        stop_loss=format(setup.stop_price, "f"),
        dol1=format(setup.target_price, "f"),
        three_r=format(setup.three_r_price, "f"),
        nominal_risk_r=format(nominal_risk, "f"),
        reference_high=format(reference.high, "f"),
        reference_low=format(reference.low, "f"),
        reference_volatility_state=str(
            state.get("reference_volatility_state", "unavailable")
        ),
        h1_state=str(state.get("h1_state", "unavailable")),
        premarket_state=str(state.get("premarket_state", "unavailable")),
        cash_open_state=str(state.get("cash_open_state", "unavailable")),
        confirmation_latency_minutes=(
            None
            if state.get("confirmation_latency_minutes") is None
            else int(cast(int, state["confirmation_latency_minutes"]))
        ),
        risk_ref=(
            None if state.get("risk_ref") is None else str(state["risk_ref"])
        ),
        current_path_vs_previous=(
            None
            if state.get("current_path_vs_previous") is None
            else str(state["current_path_vs_previous"])
        ),
        rearm_quality=rearm_quality,
    )


def _by_day(
    bars: tuple[OhlcSnapshot, ...],
) -> dict[date, tuple[OhlcSnapshot, ...]]:
    raw: dict[date, list[OhlcSnapshot]] = defaultdict(list)
    for bar in bars:
        raw[_day(bar.opened_at)].append(bar)
    return {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }


def _source_key(source: Vt31R22SourceSetup) -> tuple[str, ...]:
    return (
        source.side.value,
        source.structure.raid_at.isoformat(),
        source.structure.confirmation_at.isoformat(),
        format(source.structure.swing_extreme, "f"),
        format(source.target_price, "f"),
    )


def _basket_id(
    *,
    local_day: date,
    tier: str,
    reason: str,
    authorization_at: datetime,
    source: Vt31R22SourceSetup,
) -> str:
    material = {
        "date": local_day.isoformat(),
        "tier": tier,
        "reason": reason,
        "authorization_at": authorization_at.isoformat(),
        "source": _source_key(source),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _previous_month(month: str) -> str:
    year_text, month_text = month.split("-")
    year = int(year_text)
    value = int(month_text)
    if value == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{value - 1:02d}"


def _rearm_opening_budget(
    live_state: Vt31Nas100LiveState,
    month: str,
) -> Decimal:
    prior = _previous_month(month)
    prior_count = sum(
        1 for item in live_state.first_trade_dates if item.startswith(prior)
    )
    sparse_max = int(cast(int, ACTIVITY_L["sparse_max"]))
    balanced_max = int(cast(int, ACTIVITY_L["balanced_max"]))
    if prior_count <= sparse_max:
        return cast(Decimal, ACTIVITY_L["sparse_budget"])
    if prior_count <= balanced_max:
        return cast(Decimal, ACTIVITY_L["balanced_budget"])
    return cast(Decimal, ACTIVITY_L["dense_budget"])
