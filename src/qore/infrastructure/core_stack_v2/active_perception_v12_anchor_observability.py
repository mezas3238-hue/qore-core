"""Source-only anchor observability and staleness freeze for WP-05 V12."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Final

ANCHOR_OBSERVABILITY_IDENTITY: Final = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ANCHOR_OBSERVABILITY_001"
)
STALENESS_CANDIDATES_MS: Final = (
    250,
    500,
    1_000,
    2_000,
    5_000,
    10_000,
    30_000,
    60_000,
)
MIN_USABLE_COVERAGE_BPS: Final = 9_500
FROZEN_MICROSTRUCTURE_WINDOWS_MS: Final = (1_000, 5_000, 15_000, 60_000)


@dataclass(frozen=True, slots=True)
class V12AnchorQuoteState:
    evaluation_at: datetime
    bid_age_ms: int | None
    ask_age_ms: int | None
    bid_relative_price: int | None
    ask_relative_price: int | None

    def __post_init__(self) -> None:
        if self.evaluation_at.tzinfo is None or self.evaluation_at.utcoffset() is None:
            raise ValueError("evaluation_at must be timezone-aware")
        for age in (self.bid_age_ms, self.ask_age_ms):
            if age is not None and (type(age) is not int or age < 0):
                raise ValueError("quote age must be non-negative int")
        if (self.bid_age_ms is None) != (self.bid_relative_price is None):
            raise ValueError("BID age/price availability mismatch")
        if (self.ask_age_ms is None) != (self.ask_relative_price is None):
            raise ValueError("ASK age/price availability mismatch")
        for price in (self.bid_relative_price, self.ask_relative_price):
            if price is not None and (type(price) is not int or price <= 0):
                raise ValueError("relative price must be positive int")


def _summary(values: list[int]) -> dict[str, int] | None:
    if not values:
        return None
    ordered = sorted(values)

    def percentile(percent: int) -> int:
        return ordered[((len(ordered) - 1) * percent) // 100]

    return {
        "min": ordered[0],
        "p50": percentile(50),
        "p95": percentile(95),
        "p99": percentile(99),
        "max": ordered[-1],
    }


def summarize_v12_anchor_observability(
    states: tuple[V12AnchorQuoteState, ...],
) -> dict[str, object]:
    """Freeze staleness using source-only causal quote availability."""

    if not states:
        raise ValueError("anchor observability requires states")
    evaluation_times = tuple(item.evaluation_at for item in states)
    if evaluation_times != tuple(sorted(evaluation_times)):
        raise ValueError("anchor quote states must be chronological")
    if len(evaluation_times) != len(set(evaluation_times)):
        raise ValueError("anchor quote states must be unique")

    total = len(states)
    bid_ages = [item.bid_age_ms for item in states if item.bid_age_ms is not None]
    ask_ages = [item.ask_age_ms for item in states if item.ask_age_ms is not None]
    both = [
        item
        for item in states
        if item.bid_age_ms is not None
        and item.ask_age_ms is not None
        and item.bid_relative_price is not None
        and item.ask_relative_price is not None
    ]
    max_side_ages = [
        max(item.bid_age_ms, item.ask_age_ms)
        for item in both
        if item.bid_age_ms is not None and item.ask_age_ms is not None
    ]
    side_age_skews = [
        abs(item.bid_age_ms - item.ask_age_ms)
        for item in both
        if item.bid_age_ms is not None and item.ask_age_ms is not None
    ]
    crossed_before_staleness = sum(
        1
        for item in both
        if item.ask_relative_price is not None
        and item.bid_relative_price is not None
        and item.ask_relative_price < item.bid_relative_price
    )

    threshold_reports: list[dict[str, int]] = []
    selected: int | None = None
    for threshold in STALENESS_CANDIDATES_MS:
        fresh = [
            item
            for item in both
            if item.bid_age_ms is not None
            and item.ask_age_ms is not None
            and item.bid_age_ms <= threshold
            and item.ask_age_ms <= threshold
        ]
        crossed = sum(
            1
            for item in fresh
            if item.ask_relative_price is not None
            and item.bid_relative_price is not None
            and item.ask_relative_price < item.bid_relative_price
        )
        usable = len(fresh) - crossed
        coverage_bps = usable * 10_000 // total
        threshold_reports.append(
            {
                "threshold_ms": threshold,
                "both_side_fresh_count": len(fresh),
                "crossed_count": crossed,
                "usable_count": usable,
                "usable_coverage_bps": coverage_bps,
            }
        )
        if selected is None and coverage_bps >= MIN_USABLE_COVERAGE_BPS:
            selected = threshold

    return {
        "identity": ANCHOR_OBSERVABILITY_IDENTITY,
        "status": "frozen" if selected is not None else "rejected",
        "anchor_count": total,
        "no_prior_bid_count": total - len(bid_ages),
        "no_prior_ask_count": total - len(ask_ages),
        "bid_age_ms": _summary([int(value) for value in bid_ages]),
        "ask_age_ms": _summary([int(value) for value in ask_ages]),
        "max_side_age_ms": _summary(max_side_ages),
        "absolute_side_age_skew_ms": _summary(side_age_skews),
        "crossed_causal_quote_count": crossed_before_staleness,
        "threshold_reports": threshold_reports,
        "selected_staleness_limit_ms": selected,
        "minimum_usable_coverage_bps": MIN_USABLE_COVERAGE_BPS,
        "microstructure_windows_ms": list(FROZEN_MICROSTRUCTURE_WINDOWS_MS),
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


def v12_anchor_observability_digest(report: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
