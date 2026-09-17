"""Higher-context causal state laboratory for VT31_NAS100.

Extends immutable Market State V2 rows with only information that was already
known at each decision:
- previous completed NY market day (00:00-16:00),
- rolling prior reference-width context,
- 08:00-09:00 premarket,
- frozen 09:00-10:00 reference,
- 09:30-10:00 cash-open segment,
- current-day path only through the decision timestamp.

The laboratory is descriptive research.  It selects no trading policy and
opens no holdout.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

import vt31_nas100_r1_candidate as baseline

SCHEMA = "qore.vt31.nas100.market_context_lab.v3"
SOURCE_SCHEMA = "qore.vt31.nas100.market_state_lab.v2"
MARKET = "NAS100"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _interval(
    bars: tuple[object, ...],
) -> dict[str, Decimal] | None:
    if not bars:
        return None
    return {
        "open": _d(getattr(bars[0], "open")),
        "high": max(_d(getattr(bar, "high")) for bar in bars),
        "low": min(_d(getattr(bar, "low")) for bar in bars),
        "close": _d(getattr(bars[-1], "close")),
    }


def _range(interval: dict[str, Decimal] | None) -> Decimal | None:
    if interval is None:
        return None
    return interval["high"] - interval["low"]


def _body_fraction(interval: dict[str, Decimal] | None) -> Decimal | None:
    width = _range(interval)
    if interval is None or width is None or width <= 0:
        return None
    return abs(interval["close"] - interval["open"]) / width


def _direction(interval: dict[str, Decimal] | None) -> str:
    if interval is None:
        return "unavailable"
    if interval["close"] > interval["open"]:
        return "up"
    if interval["close"] < interval["open"]:
        return "down"
    return "flat"


def _alignment(direction: str, side: str) -> str:
    if direction in {"unavailable", "flat"}:
        return direction
    wanted = "up" if side == "long" else "down"
    return "aligned" if direction == wanted else "opposed"


def _strength(value: Decimal | None) -> str:
    if value is None:
        return "unavailable"
    if value < Decimal("0.25"):
        return "balanced"
    if value < Decimal("0.60"):
        return "directional"
    return "strong-directional"


def _relative_state(value: Decimal | None) -> str:
    if value is None:
        return "unavailable"
    if value < Decimal("0.75"):
        return "compressed"
    if value <= Decimal("1.25"):
        return "normal"
    return "expanded"


def _position_in_previous_range(
    price: Decimal,
    previous: dict[str, Decimal] | None,
) -> tuple[str, Decimal | None]:
    if previous is None:
        return "unavailable", None
    width = previous["high"] - previous["low"]
    if width <= 0:
        return "unavailable", None
    normalized = (price - previous["low"]) / width
    if normalized < 0:
        label = "below"
    elif normalized < Decimal("0.33"):
        label = "inside-lower"
    elif normalized <= Decimal("0.67"):
        label = "inside-middle"
    elif normalized <= 1:
        label = "inside-upper"
    else:
        label = "above"
    return label, normalized


def _ratio(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _market_day_bars(day_bars: tuple[object, ...]) -> tuple[object, ...]:
    return tuple(
        bar
        for bar in day_bars
        if (0, 0, 0) <= baseline._wall(getattr(bar, "opened_at")) < (16, 0, 0)
    )


def _slice(
    day_bars: tuple[object, ...],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
) -> tuple[object, ...]:
    return tuple(
        bar
        for bar in day_bars
        if start <= baseline._wall(getattr(bar, "opened_at")) < end
    )


def _context_for_row(
    row: dict[str, Any],
    current_day: tuple[object, ...],
    previous_day: tuple[object, ...] | None,
    prior_reference_widths: list[Decimal],
) -> dict[str, object]:
    side = cast(str, row["side"])
    decision_at = datetime.fromisoformat(cast(str, row["signal_at"]))
    causal_current = tuple(
        bar
        for bar in current_day
        if cast(datetime, getattr(bar, "closed_at")) <= decision_at
    )

    previous = _interval(_market_day_bars(previous_day or ()))
    previous_width = _range(previous)
    previous_body_fraction = _body_fraction(previous)
    previous_direction = _direction(previous)

    premarket = _interval(_slice(causal_current, (8, 0, 0), (9, 0, 0)))
    reference = _interval(_slice(causal_current, (9, 0, 0), (10, 0, 0)))
    cash_open = _interval(_slice(causal_current, (9, 30, 0), (10, 0, 0)))
    current_path = _interval(_market_day_bars(causal_current))

    reference_width = _range(reference)
    current_path_width = _range(current_path)
    rolling_reference_median = (
        median(prior_reference_widths[-5:])
        if prior_reference_widths
        else None
    )
    ref_vs_prior5 = _ratio(reference_width, rolling_reference_median)
    current_vs_previous = _ratio(current_path_width, previous_width)

    reference_direction = _direction(reference)
    premarket_direction = _direction(premarket)
    cash_open_direction = _direction(cash_open)

    decision_close = (
        _d(getattr(causal_current[-1], "close")) if causal_current else Decimal(0)
    )
    previous_position, previous_position_value = _position_in_previous_range(
        decision_close,
        previous,
    )

    gap_vs_previous = None
    if previous is not None and reference is not None and previous_width:
        gap_vs_previous = (reference["open"] - previous["close"]) / previous_width

    reference_location_vs_previous = None
    if previous is not None and reference is not None and previous_width:
        reference_mid = (reference["high"] + reference["low"]) / Decimal(2)
        reference_location_vs_previous = (
            reference_mid - previous["low"]
        ) / previous_width

    return {
        "previous_day_direction": previous_direction,
        "previous_day_body_fraction": _fmt(previous_body_fraction),
        "previous_day_strength": _strength(previous_body_fraction),
        "previous_day_trade_alignment": _alignment(previous_direction, side),
        "previous_day_range": _fmt(previous_width),
        "premarket_direction": premarket_direction,
        "premarket_body_fraction": _fmt(_body_fraction(premarket)),
        "premarket_strength": _strength(_body_fraction(premarket)),
        "premarket_trade_alignment": _alignment(premarket_direction, side),
        "reference_direction": reference_direction,
        "reference_body_fraction": _fmt(_body_fraction(reference)),
        "reference_strength": _strength(_body_fraction(reference)),
        "reference_trade_alignment": _alignment(reference_direction, side),
        "cash_open_direction": cash_open_direction,
        "cash_open_body_fraction": _fmt(_body_fraction(cash_open)),
        "cash_open_strength": _strength(_body_fraction(cash_open)),
        "cash_open_trade_alignment": _alignment(cash_open_direction, side),
        "reference_width": _fmt(reference_width),
        "prior5_reference_width_median": _fmt(rolling_reference_median),
        "reference_width_vs_prior5_median": _fmt(ref_vs_prior5),
        "reference_volatility_state": _relative_state(ref_vs_prior5),
        "current_path_range_vs_previous_day": _fmt(current_vs_previous),
        "current_path_volatility_state": _relative_state(current_vs_previous),
        "decision_position_in_previous_range": previous_position,
        "decision_position_normalized_previous_range": _fmt(
            previous_position_value
        ),
        "reference_mid_position_previous_range": _fmt(
            reference_location_vs_previous
        ),
        "reference_open_gap_vs_previous_range": _fmt(gap_vs_previous),
    }


def run(
    market_state_path: Path,
    evidence_path: Path,
) -> dict[str, object]:
    state = json.loads(market_state_path.read_text())
    if state.get("schema") != SOURCE_SCHEMA:
        raise ValueError("unexpected Market State source schema")
    contract = cast(dict[str, object], state["causal_contract"])
    if contract.get("runtime_features_are_predecision_only") is not True:
        raise ValueError("source causal contract mismatch")

    series, account, evidence, checked, evidence_sha, provider = (
        baseline.load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("Market Context V3 requires NAS100 evidence")

    by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        by_day[baseline._day(getattr(bar, "opened_at"))].append(bar)
    days = sorted(by_day)
    eligible_context_days: list[date] = []
    reference_width_by_day: dict[date, Decimal] = {}
    for day in days:
        day_tuple = tuple(by_day[day])
        reference_bars = _slice(day_tuple, (9, 0, 0), (10, 0, 0))
        session_bars = _slice(day_tuple, (10, 0, 0), (11, 0, 0))
        if len(reference_bars) != 60 or len(session_bars) != 60:
            continue
        reference = _interval(reference_bars)
        width = _range(reference)
        if width is None or width <= 0:
            continue
        eligible_context_days.append(day)
        reference_width_by_day[day] = width

    prior_day_map: dict[date, date | None] = {}
    for day in days:
        prior = [candidate for candidate in eligible_context_days if candidate < day]
        prior_day_map[day] = prior[-1] if prior else None

    enriched: list[dict[str, object]] = []
    missing_previous = 0
    for row in cast(list[dict[str, Any]], state["state_matrix"]):
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        previous_date = prior_day_map.get(local_day)
        if previous_date is None:
            missing_previous += 1
        prior_widths = [
            reference_width_by_day[day]
            for day in days
            if day < local_day and day in reference_width_by_day
        ]
        context = _context_for_row(
            row,
            tuple(by_day.get(local_day, ())),
            tuple(by_day[previous_date]) if previous_date is not None else None,
            prior_widths,
        )
        enriched.append({**row, **context})

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "partition": state["partition"],
        "research_only": True,
        "runtime_policy_selected": False,
        "candidate_frozen": False,
        "opens_new_holdout": False,
        "live_authorized": False,
        "production_authorized": False,
        "causal_contract": {
            "all_added_features_known_at_decision": True,
            "current_day_bars_cut_at_decision": True,
            "previous_day_is_completed_before_decision": True,
            "previous_day_uses_same_reference_session_admission": True,
            "rolling_context_uses_prior_days_only": True,
            "date_level_outcome_lookup": False,
            "future_bar_lookup_for_runtime_features": False,
        },
        "context_definitions": {
            "previous_market_day": (
                "last prior NY date admitted by complete 09:00-10:00 and "
                "10:00-11:00 M1 windows; context path uses that date 00:00-16:00"
            ),
            "premarket": "08:00-09:00 NY",
            "reference": "09:00-10:00 NY frozen",
            "cash_open_segment": "09:30-10:00 NY",
            "current_path": "00:00 NY through decision close only",
            "relative_state_bins": {
                "compressed": "<0.75",
                "normal": "0.75-1.25",
                "expanded": ">1.25",
            },
            "body_strength_bins": {
                "balanced": "<0.25",
                "directional": "0.25-0.60",
                "strong-directional": ">=0.60",
            },
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "source_rows": len(enriched),
        "rows_missing_previous_day": missing_previous,
        "state_matrix": enriched,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-state", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.market_state, args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "source_rows": payload["source_rows"],
                "rows_missing_previous_day": payload[
                    "rows_missing_previous_day"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
