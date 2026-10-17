"""Causal source-multiplicity census for VT08 CRT PURE R2-C WAIT parents.

This census does not create entries and never evaluates PnL. It measures whether
R2-C's engineering control "first aligned Model #1 source only" suppresses later,
independent direction-aligned source events inside the same parent C3.

A later source is counted only when it is emitted by the existing causal
close-unmitigated breach builder. Exact reference evidence IDs are compared so
the census can prove whether a later event reuses the first source reference.

Research only. No methodology mutation and no deployment/capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    FOLD_1_END,
    ReplayBar,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    BreachGroup,
    M15Bar,
    ParentCrt,
    ReferenceKind,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
    first_r2c_trade,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2E_SOURCE_MULTIPLICITY_CENSUS_001"
SCHEMA = "qore.vt08.crt_pure.r2e_source_multiplicity_census.v1"
WAIT_REASON = "FIRST_CLOSE_UNMITIGATED_SOURCE_NOT_CONFIRMED"


class ConfirmationState(StrEnum):
    NO_BODY_CONFIRMATION = "NO_BODY_CONFIRMATION"
    BODY_CONFIRMED_NO_NEXT_BAR = "BODY_CONFIRMED_NO_NEXT_BAR"
    BODY_CONFIRMED_NO_CONTIGUOUS_NEXT_BAR = (
        "BODY_CONFIRMED_NO_CONTIGUOUS_NEXT_BAR"
    )
    EXECUTABLE_CONFIRMATION = "EXECUTABLE_CONFIRMATION"


@dataclass(frozen=True, slots=True)
class SourceObservation:
    group: BreachGroup
    source_index: int
    confirmation_state: ConfirmationState
    confirmation_opened_at: datetime | None

    @property
    def reference_ids(self) -> frozenset[str]:
        return frozenset(item.evidence_id for item in self.group.references)


def _c3_m15(
    parent: ParentCrt,
    m15_by_time: dict[datetime, M15Bar],
) -> tuple[M15Bar, ...]:
    return tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if parent.c3_opened_at <= opened_at < parent.c3_closed_at
    )


def _confirmation_state(
    *,
    source: M15Bar,
    subsequent: tuple[M15Bar, ...],
    direction: CrtPureCandidateDirection,
) -> tuple[ConfirmationState, datetime | None]:
    for index, bar in enumerate(subsequent):
        confirmed = (
            bar.close_price > source.open_price
            if direction is CrtPureCandidateDirection.BULLISH
            else bar.close_price < source.open_price
        )
        if not confirmed:
            continue
        if index + 1 >= len(subsequent):
            return ConfirmationState.BODY_CONFIRMED_NO_NEXT_BAR, bar.opened_at
        next_bar = subsequent[index + 1]
        if next_bar.opened_at != bar.closed_at:
            return (
                ConfirmationState.BODY_CONFIRMED_NO_CONTIGUOUS_NEXT_BAR,
                bar.opened_at,
            )
        return ConfirmationState.EXECUTABLE_CONFIRMATION, bar.opened_at
    return ConfirmationState.NO_BODY_CONFIRMATION, None


def _aligned_sources(
    *,
    parent: ParentCrt,
    c3_m15: tuple[M15Bar, ...],
    breaches: dict[datetime, tuple[BreachGroup, ...]],
) -> tuple[SourceObservation, ...]:
    expected_kind = (
        ReferenceKind.OLD_LOW
        if parent.direction is CrtPureCandidateDirection.BULLISH
        else ReferenceKind.OLD_HIGH
    )
    result: list[SourceObservation] = []
    for index, source in enumerate(c3_m15):
        for group in breaches.get(source.opened_at, ()):
            if group.kind is not expected_kind:
                continue
            state, confirmed_at = _confirmation_state(
                source=source,
                subsequent=c3_m15[index + 1 :],
                direction=parent.direction,
            )
            result.append(
                SourceObservation(
                    group=group,
                    source_index=index,
                    confirmation_state=state,
                    confirmation_opened_at=confirmed_at,
                )
            )
    return tuple(result)


def _count_wait_parent(
    *,
    observations: tuple[SourceObservation, ...],
    counter: Counter[str],
) -> None:
    counter["wait_parent_count"] += 1
    counter[f"source_multiplicity_{len(observations)}"] += 1
    if not observations:
        counter["invariant_wait_without_first_source"] += 1
        return

    first = observations[0]
    counter[f"first_state_{first.confirmation_state.value}"] += 1
    later = observations[1:]
    counter["later_source_event_count"] += len(later)
    if not later:
        counter["wait_without_later_aligned_source"] += 1
        return

    counter["wait_with_later_aligned_source"] += 1
    if len(later) >= 2:
        counter["wait_with_two_or_more_later_sources"] += 1

    first_refs = first.reference_ids
    later_reuses_first = False
    has_later_body_confirmation = False
    has_later_executable = False
    for item in later:
        counter[f"later_state_{item.confirmation_state.value}"] += 1
        if item.reference_ids & first_refs:
            later_reuses_first = True
        if item.confirmation_state is not ConfirmationState.NO_BODY_CONFIRMATION:
            has_later_body_confirmation = True
        if item.confirmation_state is ConfirmationState.EXECUTABLE_CONFIRMATION:
            has_later_executable = True

    if later_reuses_first:
        counter["wait_with_later_reference_reuse"] += 1
    if has_later_body_confirmation:
        counter["wait_with_later_body_confirmation"] += 1
    if has_later_executable:
        counter["wait_with_later_executable_confirmation"] += 1


def run_census(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> dict[str, Any]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    full: Counter[str] = Counter()
    year_1: Counter[str] = Counter()
    year_2: Counter[str] = Counter()

    for parent in parents:
        trade, reason = first_r2c_trade(
            parent=parent,
            m15_by_time=m15_by_time,
            breaches=breaches,
        )
        if trade is not None or reason != WAIT_REASON:
            continue

        observations = _aligned_sources(
            parent=parent,
            c3_m15=_c3_m15(parent, m15_by_time),
            breaches=breaches,
        )
        _count_wait_parent(observations=observations, counter=full)
        fold_counter = year_1 if parent.c3_opened_at < FOLD_1_END else year_2
        _count_wait_parent(
            observations=observations,
            counter=fold_counter,
        )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "parent_crt_count": len(parents),
        "population": WAIT_REASON,
        "full_2y": dict(full),
        "year_1": dict(year_1),
        "year_2": dict(year_2),
        "methodology_mutated": False,
        "trades_created": 0,
        "pnl_evaluated": False,
        "single_source_control_under_test": True,
        "later_source_is_not_auto_entry": True,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    report = run_census(market, load_two_year_m5(market))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print("CRT_R2E_SOURCE_MULTIPLICITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
