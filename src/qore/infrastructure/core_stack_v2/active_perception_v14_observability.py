"""Outcome-blind cross-peer observability and staleness freeze for WP-05 V14."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    V14PeerFamily,
)

V14_OBSERVABILITY_IDENTITY: Final = (
    "QORE_SHARED_WP05_V14_CROSS_MARKET_OBSERVABILITY_001"
)
V14_CHECKPOINTS_MINUTES: Final = (0, 3, 5, 10, 15)
V14_STALENESS_CANDIDATES_MS: Final = (5_000, 10_000, 30_000, 60_000, 120_000)
V14_MIN_PEER_CHECKPOINT_COVERAGE_BPS: Final = 9_500
V14_EXPECTED_SOURCE_COUNT: Final = 6_804
V14_EXPECTED_SOURCE_ANCHOR_SHA256: Final = (
    "d5dda96fbaab9506e77bd803cf8b542250288e7d46091db1630f1fd8fb91839e"
)


@dataclass(frozen=True, slots=True)
class V14PeerCheckpointQuoteState:
    peer: V14PeerFamily
    source_index: int
    checkpoint_minutes: int
    evaluation_at: datetime
    bid_age_ms: int | None
    ask_age_ms: int | None
    bid_relative_price: int | None
    ask_relative_price: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.peer, V14PeerFamily):
            raise ValueError("V14 quote state peer invalid")
        if type(self.source_index) is not int or self.source_index < 0:
            raise ValueError("V14 source index invalid")
        if self.checkpoint_minutes not in V14_CHECKPOINTS_MINUTES:
            raise ValueError("V14 checkpoint outside frozen schedule")
        if self.evaluation_at.tzinfo is None or self.evaluation_at.utcoffset() is None:
            raise ValueError("V14 evaluation_at must be timezone-aware")
        for age in (self.bid_age_ms, self.ask_age_ms):
            if age is not None and (type(age) is not int or age < 0):
                raise ValueError("V14 quote age invalid")
        if (self.bid_age_ms is None) != (self.bid_relative_price is None):
            raise ValueError("V14 BID availability mismatch")
        if (self.ask_age_ms is None) != (self.ask_relative_price is None):
            raise ValueError("V14 ASK availability mismatch")
        for price in (self.bid_relative_price, self.ask_relative_price):
            if price is not None and (type(price) is not int or price <= 0):
                raise ValueError("V14 relative price invalid")


def _summary(values: list[int]) -> dict[str, int] | None:
    if not values:
        return None
    ordered = sorted(values)

    def pct(value: int) -> int:
        return ordered[((len(ordered) - 1) * value) // 100]

    return {
        "min": ordered[0],
        "p50": pct(50),
        "p95": pct(95),
        "p99": pct(99),
        "max": ordered[-1],
    }


def summarize_v14_cross_peer_observability(
    states: tuple[V14PeerCheckpointQuoteState, ...],
) -> dict[str, object]:
    """Select one shared staleness threshold from source-only causal coverage."""

    expected = (
        len(V14PeerFamily)
        * V14_EXPECTED_SOURCE_COUNT
        * len(V14_CHECKPOINTS_MINUTES)
    )
    if len(states) != expected:
        raise ValueError("V14 observability population cardinality drift")

    by_key: dict[
        tuple[V14PeerFamily, int],
        list[V14PeerCheckpointQuoteState],
    ] = {}
    for peer in V14PeerFamily:
        for checkpoint in V14_CHECKPOINTS_MINUTES:
            subset = [
                item
                for item in states
                if item.peer is peer and item.checkpoint_minutes == checkpoint
            ]
            if len(subset) != V14_EXPECTED_SOURCE_COUNT:
                raise ValueError("V14 peer/checkpoint population drift")
            ordered_indices = [item.source_index for item in subset]
            if sorted(ordered_indices) != list(range(V14_EXPECTED_SOURCE_COUNT)):
                raise ValueError("V14 source identity drift")
            by_key[(peer, checkpoint)] = subset

    threshold_reports: list[dict[str, object]] = []
    selected: int | None = None
    for threshold in V14_STALENESS_CANDIDATES_MS:
        peer_checkpoint: list[dict[str, object]] = []
        all_pass = True
        for peer in V14PeerFamily:
            for checkpoint in V14_CHECKPOINTS_MINUTES:
                subset = by_key[(peer, checkpoint)]
                both_present = [
                    item
                    for item in subset
                    if item.bid_age_ms is not None
                    and item.ask_age_ms is not None
                    and item.bid_relative_price is not None
                    and item.ask_relative_price is not None
                ]
                fresh = [
                    item
                    for item in both_present
                    if item.bid_age_ms is not None
                    and item.ask_age_ms is not None
                    and item.bid_age_ms <= threshold
                    and item.ask_age_ms <= threshold
                ]
                crossed = sum(
                    1
                    for item in fresh
                    if item.bid_relative_price is not None
                    and item.ask_relative_price is not None
                    and item.ask_relative_price < item.bid_relative_price
                )
                usable = len(fresh) - crossed
                coverage = usable * 10_000 // V14_EXPECTED_SOURCE_COUNT
                passed = coverage >= V14_MIN_PEER_CHECKPOINT_COVERAGE_BPS
                all_pass = all_pass and passed
                peer_checkpoint.append(
                    {
                        "peer": peer.value,
                        "checkpoint_minutes": checkpoint,
                        "both_side_present_count": len(both_present),
                        "both_side_fresh_count": len(fresh),
                        "crossed_count": crossed,
                        "usable_count": usable,
                        "usable_coverage_bps": coverage,
                        "gate_pass": passed,
                    }
                )
        threshold_reports.append(
            {
                "threshold_ms": threshold,
                "all_peer_checkpoint_gates_pass": all_pass,
                "peer_checkpoint": peer_checkpoint,
            }
        )
        if selected is None and all_pass:
            selected = threshold

    age_diagnostics: dict[str, dict[str, object]] = {}
    for peer in V14PeerFamily:
        peer_states = [item for item in states if item.peer is peer]
        bid_ages = [item.bid_age_ms for item in peer_states if item.bid_age_ms is not None]
        ask_ages = [item.ask_age_ms for item in peer_states if item.ask_age_ms is not None]
        max_ages = [
            max(item.bid_age_ms, item.ask_age_ms)
            for item in peer_states
            if item.bid_age_ms is not None and item.ask_age_ms is not None
        ]
        age_diagnostics[peer.value] = {
            "bid_age_ms": _summary([int(value) for value in bid_ages]),
            "ask_age_ms": _summary([int(value) for value in ask_ages]),
            "max_side_age_ms": _summary(max_ages),
            "no_prior_bid_count": len(peer_states) - len(bid_ages),
            "no_prior_ask_count": len(peer_states) - len(ask_ages),
        }

    return {
        "identity": V14_OBSERVABILITY_IDENTITY,
        "status": "source_only_frozen" if selected is not None else "source_only_rejected",
        "source_count": V14_EXPECTED_SOURCE_COUNT,
        "checkpoints_minutes": list(V14_CHECKPOINTS_MINUTES),
        "peer_families": [peer.value for peer in V14PeerFamily],
        "staleness_candidates_ms": list(V14_STALENESS_CANDIDATES_MS),
        "minimum_peer_checkpoint_coverage_bps": (
            V14_MIN_PEER_CHECKPOINT_COVERAGE_BPS
        ),
        "selected_staleness_limit_ms": selected,
        "threshold_reports": threshold_reports,
        "age_diagnostics": age_diagnostics,
        "source_anchor_sha256": V14_EXPECTED_SOURCE_ANCHOR_SHA256,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v14_outcomes_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


def v14_observability_digest(report: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
