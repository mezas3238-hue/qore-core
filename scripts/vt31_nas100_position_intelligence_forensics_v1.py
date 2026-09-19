"""VT31_NAS100 structural position-intelligence forensics.

Research-only counterfactuals over consumed NAS100 evidence.

For each executed VT31 opportunity this lab observes causal protection events:
- confirmed protective M1 swings, actionable from the next bar;
- conquered DOL levels, actionable from the next bar.

Each event is judged by structural journey preservation rather than by PnL:
- PROTECTED_FAILED_JOURNEY: the counterfactual stop would exit before the
  original methodological invalidation and the untouched journey would not
  subsequently conquer a deeper DOL;
- PREMATURE_CUT_DEEPER_JOURNEY: the counterfactual stop would exit, but the
  untouched journey later conquered a deeper DOL before invalidation/lifecycle;
- NO_EXIT_EFFECT: the proposed protection was never revisited.

The lab does not select SUPPORTIVE/MIXED/CAUTIOUS thresholds and does not open
fresh holdout evidence.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

IDENTITY = "VT31_NAS100_POSITION_INTELLIGENCE_FORENSICS_V1"
LIFECYCLE_MINUTE = 16 * 60


@dataclass(frozen=True, slots=True)
class ProtectionEvent:
    event_type: str
    observed_at: datetime
    effective_at: datetime
    level: Decimal
    confirmations: int
    dol_rank_when_observed: int


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _rate(n: int, d: int) -> str | None:
    return None if d == 0 else format(Decimal(n) / Decimal(d), "f")


def _median(values: list[int]) -> str | None:
    return None if not values else str(median(values))


def _dol_ladder(
    setup: Vt31R22ExecutableSetup,
) -> tuple[tuple[str, Decimal], ...]:
    side = setup.side.value
    boundary = setup.target_price
    width = (
        setup.source_setup.reference.high
        - setup.source_setup.reference.low
    )
    direction = Decimal(1) if side == "long" else Decimal(-1)
    return (
        ("DOL1_BOUNDARY", boundary),
        (
            "DOL2_PLUS_0_25_REF",
            boundary + direction * width * Decimal("0.25"),
        ),
        (
            "DOL3_PLUS_0_50_REF",
            boundary + direction * width * Decimal("0.50"),
        ),
        (
            "DOL4_PLUS_1_00_REF",
            boundary + direction * width,
        ),
        (
            "DOL5_PLUS_1_50_REF",
            boundary + direction * width * Decimal("1.50"),
        ),
        (
            "DOL6_PLUS_2_00_REF",
            boundary + direction * width * Decimal("2.00"),
        ),
    )


def _touches_level(bar: object, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _touches_stop(bar: object, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= level
    return _d(getattr(bar, "high")) >= level


def _improves(
    *,
    side: str,
    current_stop: Decimal,
    candidate: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return current_stop < candidate < target
    return target < candidate < current_stop


def _rank_through(
    bars: tuple[object, ...],
    *,
    side: str,
    ladder: tuple[tuple[str, Decimal], ...],
    end_index: int,
) -> int:
    rank = 0
    for bar in bars[: end_index + 1]:
        for candidate_rank, (_, level) in enumerate(ladder, start=1):
            if _touches_level(bar, side, level):
                rank = max(rank, candidate_rank)
    return rank


def _protective_swings(
    bars: tuple[object, ...],
    *,
    side: str,
    initial_stop: Decimal,
    research_destination: Decimal,
    ladder: tuple[tuple[str, Decimal], ...],
) -> list[ProtectionEvent]:
    events: list[ProtectionEvent] = []
    confirmations = 0
    for right_index in range(2, len(bars) - 1):
        left = bars[right_index - 2]
        middle = bars[right_index - 1]
        right = bars[right_index]
        level: Decimal | None = None
        if side == "long":
            middle_low = _d(getattr(middle, "low"))
            if (
                middle_low < _d(getattr(left, "low"))
                and middle_low < _d(getattr(right, "low"))
            ):
                level = middle_low
        else:
            middle_high = _d(getattr(middle, "high"))
            if (
                middle_high > _d(getattr(left, "high"))
                and middle_high > _d(getattr(right, "high"))
            ):
                level = middle_high
        if level is None or not _improves(
            side=side,
            current_stop=initial_stop,
            candidate=level,
            target=research_destination,
        ):
            continue
        confirmations += 1
        effective_index = right_index + 1
        if effective_index >= len(bars):
            continue
        events.append(
            ProtectionEvent(
                event_type="CONFIRMED_PROTECTIVE_SWING",
                observed_at=cast(datetime, getattr(right, "closed_at")),
                effective_at=cast(
                    datetime,
                    getattr(bars[effective_index], "opened_at"),
                ),
                level=level,
                confirmations=confirmations,
                dol_rank_when_observed=_rank_through(
                    bars,
                    side=side,
                    ladder=ladder,
                    end_index=right_index,
                ),
            )
        )
    return events


def _dol_lock_events(
    bars: tuple[object, ...],
    *,
    side: str,
    initial_stop: Decimal,
    research_destination: Decimal,
    ladder: tuple[tuple[str, Decimal], ...],
) -> list[ProtectionEvent]:
    events: list[ProtectionEvent] = []
    conquered: set[int] = set()
    for index, bar in enumerate(bars[:-1]):
        for rank, (_, level) in enumerate(ladder[:-1], start=1):
            if rank in conquered or not _touches_level(bar, side, level):
                continue
            conquered.add(rank)
            if not _improves(
                side=side,
                current_stop=initial_stop,
                candidate=level,
                target=research_destination,
            ):
                continue
            events.append(
                ProtectionEvent(
                    event_type="CONQUERED_DOL_LOCK",
                    observed_at=cast(datetime, getattr(bar, "closed_at")),
                    effective_at=cast(
                        datetime,
                        getattr(bars[index + 1], "opened_at"),
                    ),
                    level=level,
                    confirmations=1,
                    dol_rank_when_observed=rank,
                )
            )
    return events


def _original_end_index(
    bars: tuple[object, ...],
    *,
    side: str,
    initial_stop: Decimal,
) -> tuple[int, str]:
    for index, bar in enumerate(bars):
        if _touches_stop(bar, side, initial_stop):
            return index, "METHODOLOGICAL_INVALIDATION"
    return len(bars) - 1, "LIFECYCLE"


def _classify_event(
    event: ProtectionEvent,
    bars: tuple[object, ...],
    *,
    side: str,
    ladder: tuple[tuple[str, Decimal], ...],
    original_end_index: int,
    original_end_reason: str,
) -> dict[str, object]:
    effective_index = next(
        (
            index
            for index, bar in enumerate(bars)
            if getattr(bar, "opened_at") >= event.effective_at
        ),
        None,
    )
    if effective_index is None or effective_index > original_end_index:
        return {"classification": "NO_EFFECTIVE_PATH"}

    stop_touch_index = next(
        (
            index
            for index in range(effective_index, original_end_index + 1)
            if _touches_stop(bars[index], side, event.level)
        ),
        None,
    )
    if stop_touch_index is None:
        return {
            "classification": "NO_EXIT_EFFECT",
            "stop_touch_at": None,
            "deeper_rank_after_counterfactual_exit": False,
        }

    stop_bar = bars[stop_touch_index]
    same_bar_rank = max(
        (
            rank
            for rank, (_, level) in enumerate(ladder, start=1)
            if _touches_level(stop_bar, side, level)
        ),
        default=0,
    )
    later_bars = bars[stop_touch_index + 1 : original_end_index + 1]
    later_rank = (
        _rank_through(
            later_bars,
            side=side,
            ladder=ladder,
            end_index=len(later_bars) - 1,
        )
        if later_bars
        else 0
    )
    deeper_later = later_rank > event.dol_rank_when_observed
    same_bar_deeper = same_bar_rank > event.dol_rank_when_observed

    if deeper_later:
        classification = "PREMATURE_CUT_DEEPER_JOURNEY"
    elif same_bar_deeper:
        classification = "CENSORED_SAME_BAR_PROTECTION_DOL"
    elif original_end_reason == "METHODOLOGICAL_INVALIDATION":
        classification = "PROTECTED_FAILED_JOURNEY"
    else:
        classification = "EARLY_EXIT_NO_DEEPER_DOL"

    return {
        "classification": classification,
        "stop_touch_at": cast(
            datetime,
            getattr(stop_bar, "closed_at"),
        )
        .astimezone(UTC)
        .isoformat(),
        "same_bar_max_dol_rank": same_bar_rank,
        "later_max_dol_rank": later_rank,
        "deeper_rank_after_counterfactual_exit": deeper_later,
        "same_bar_deeper_dol_ambiguous": same_bar_deeper,
    }


def _selected_setup(
    day_bars: tuple[object, ...],
    *,
    evidence_fingerprint: str,
    setup_formed_at: datetime,
    intelligence_decision_at: datetime,
) -> Vt31R22ExecutableSetup | None:
    reference = tuple(
        bar
        for bar in day_bars
        if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
    )
    session = tuple(
        bar
        for bar in day_bars
        if (10, 0, 0) <= _wall(getattr(bar, "opened_at")) < (11, 0, 0)
    )
    if len(reference) != 60 or len(session) != 60:
        return None
    policy = Vt31R22ExecutionPolicy()
    prefix = list(reference)
    for bar in session:
        prefix.append(bar)
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=getattr(bar, "closed_at"),
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence_fingerprint,
        )
        if evaluation.setup is None:
            continue
        executable, _ = make_executable_setup(evaluation.setup, policy)
        if executable is None:
            return None
        if executable.decision_at == setup_formed_at:
            if intelligence_decision_at < setup_formed_at:
                raise ValueError("intelligence decision cannot predate setup")
            return Vt31R22ExecutableSetup(
                side=executable.side,
                entry_price=executable.entry_price,
                stop_price=executable.stop_price,
                target_price=executable.target_price,
                three_r_price=executable.three_r_price,
                selected_family=executable.selected_family,
                candidate_families=executable.candidate_families,
                decision_at=intelligence_decision_at,
                pending_expires_at=executable.pending_expires_at,
                source_setup=executable.source_setup,
                execution_policy_fingerprint=(
                    executable.execution_policy_fingerprint
                ),
            )
    return None


def _trace_for_signal(
    replay: dict[str, Any],
    signal_at: str,
) -> dict[str, Any] | None:
    for row in cast(list[dict[str, Any]], replay["reasoning_trace"]):
        if (
            row.get("decision_at") == signal_at
            and row.get("action") == "EXECUTE"
        ):
            return row
    return None


def _context_from_trace(row: dict[str, Any]) -> dict[str, object]:
    return {
        key: row.get(key)
        for key in (
            "prior_day_state",
            "h4_state",
            "h1_state",
            "premarket_state",
            "cash_open_state",
            "position_in_prior_day_range",
            "reference_volatility_state",
            "last_structure_event_family",
            "current_path_vs_previous",
            "raid_depth_ref",
            "recent_path_efficiency",
            "recent_overlap_rate",
        )
    }


def build(
    evidence_path: Path,
    replay_path: Path,
) -> dict[str, object]:
    replay = cast(
        dict[str, Any],
        json.loads(replay_path.read_text(encoding="utf-8")),
    )
    if replay.get("research_only") is not True:
        raise ValueError("position forensics requires research replay")
    if replay.get("opens_new_holdout") is not False:
        raise ValueError("fresh holdout must remain sealed")

    series, _, evidence, _, _, _ = load_market_evidence(evidence_path)
    raw_by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw_by_day[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(rows, key=lambda bar: getattr(bar, "opened_at")))
        for day, rows in raw_by_day.items()
    }

    opportunities = cast(
        list[dict[str, Any]],
        replay.get("journey_capacity_observations", []),
    )
    observations: list[dict[str, object]] = []
    reconstruction_failures = 0

    for opportunity in opportunities:
        signal_at = datetime.fromisoformat(str(opportunity["signal_at"]))
        local_day = _day(signal_at)
        day_bars = by_day.get(local_day)
        if day_bars is None:
            reconstruction_failures += 1
            continue
        trace_row = _trace_for_signal(
            replay,
            signal_at.astimezone(UTC).isoformat(),
        )
        if trace_row is None:
            reconstruction_failures += 1
            continue
        setup_formed_raw = trace_row.get("setup_formed_at")
        if not isinstance(setup_formed_raw, str):
            reconstruction_failures += 1
            continue
        setup = _selected_setup(
            day_bars,
            evidence_fingerprint=evidence,
            setup_formed_at=datetime.fromisoformat(setup_formed_raw),
            intelligence_decision_at=signal_at,
        )
        if setup is None:
            reconstruction_failures += 1
            continue
        fill_index = v2b._fill_index(day_bars, setup)
        if fill_index is None:
            continue
        path = tuple(
            bar
            for bar in day_bars[fill_index:]
            if specialist.baseline._local_minute(bar) < LIFECYCLE_MINUTE
        )
        if not path:
            continue

        side = setup.side.value
        ladder = _dol_ladder(setup)
        original_end, original_reason = _original_end_index(
            path,
            side=side,
            initial_stop=setup.stop_price,
        )
        causal_path = path[: original_end + 1]
        research_destination = ladder[-1][1]
        events = [
            *_protective_swings(
                causal_path,
                side=side,
                initial_stop=setup.stop_price,
                research_destination=research_destination,
                ladder=ladder,
            ),
            *_dol_lock_events(
                causal_path,
                side=side,
                initial_stop=setup.stop_price,
                research_destination=research_destination,
                ladder=ladder,
            ),
        ]
        context = _context_from_trace(trace_row)
        for event in sorted(events, key=lambda item: item.effective_at):
            classification = _classify_event(
                event,
                causal_path,
                side=side,
                ladder=ladder,
                original_end_index=len(causal_path) - 1,
                original_end_reason=original_reason,
            )
            observations.append(
                {
                    "local_date": local_day.isoformat(),
                    "signal_at": signal_at.astimezone(UTC).isoformat(),
                    "side": side,
                    "event_type": event.event_type,
                    "observed_at": event.observed_at.astimezone(UTC).isoformat(),
                    "effective_at": event.effective_at.astimezone(UTC).isoformat(),
                    "candidate_stop": format(event.level, "f"),
                    "confirmations": event.confirmations,
                    "dol_rank_when_observed": event.dol_rank_when_observed,
                    "original_journey_end_reason": original_reason,
                    "research_extension_destination": format(
                        research_destination,
                        "f",
                    ),
                    **classification,
                    "pre_entry_context": context,
                    "timing_class": "POST_ENTRY_COUNTERFACTUAL_RESEARCH",
                    "used_for_runtime_decision": False,
                }
            )

    classes = Counter(
        str(row["classification"]) for row in observations
    )
    by_type: dict[str, object] = {}
    for event_type in sorted(
        {str(row["event_type"]) for row in observations}
    ):
        rows = [
            row for row in observations if row["event_type"] == event_type
        ]
        row_classes = Counter(str(row["classification"]) for row in rows)
        by_type[event_type] = {
            "n": len(rows),
            "classification_counts": dict(sorted(row_classes.items())),
            "premature_cut_rate": _rate(
                row_classes["PREMATURE_CUT_DEEPER_JOURNEY"],
                len(rows),
            ),
            "protected_failed_journey_rate": _rate(
                row_classes["PROTECTED_FAILED_JOURNEY"],
                len(rows),
            ),
        }

    return {
        "identity": IDENTITY,
        "candidate_id": replay["candidate_id"],
        "contract_fingerprint": replay["contract_fingerprint"],
        "market": "NAS100",
        "opportunities_assessed": len(opportunities),
        "reconstruction_failures": reconstruction_failures,
        "protection_events": len(observations),
        "classification_counts": dict(sorted(classes.items())),
        "by_event_type": by_type,
        "observations": observations,
        "governance": {
            "structural_labels_not_direct_pnl_optimization": True,
            "xauusd_thresholds_copied": False,
            "deepest_dol_used_only_as_counterfactual_research_destination": True,
            "contextual_policy_selection_allowed": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build(args.evidence, args.replay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "opportunities_assessed": payload["opportunities_assessed"],
                "reconstruction_failures": payload["reconstruction_failures"],
                "protection_events": payload["protection_events"],
                "classification_counts": payload["classification_counts"],
                "by_event_type": payload["by_event_type"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
