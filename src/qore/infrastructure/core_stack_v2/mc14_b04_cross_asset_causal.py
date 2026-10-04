"""MC-14 B04 cross-asset source-only causal feature contracts."""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Final, TypedDict

IDENTITY: Final = "QORE_SHARED_MC14_B04_CROSS_ASSET_FEATURES_001"
POST_SOURCE_MINUTES: Final = 15
EXPECTED_WINDOW_COUNT: Final = 2948
DISCOVERY_LOW_QUANTILE: Final = 0.45
DISCOVERY_HIGH_QUANTILE: Final = 0.55
MINIMUM_EFFECT_BPS: Final = 500
MINIMUM_GROUP_COUNT: Final = 250
MINIMUM_STRATUM_GROUP_COUNT: Final = 20
MINIMUM_STABILITY_BPS: Final = 8_000

FROZEN_FEATURES: Final = (
    "MID_RETURN_BPS",
    "ABS_MID_RETURN_BPS",
    "MEDIAN_SPREAD_BPS",
    "P90_SPREAD_BPS",
    "BID_TICK_RATE",
    "ASK_TICK_RATE",
    "QUOTE_SIDE_ACTIVITY_IMBALANCE_BPS",
)


class CausalMetricRow(TypedDict):
    source: int
    target_bps: int
    confounder_key: str
    regime_key: str


class CausalTargetRow(TypedDict):
    source_at: str
    target_bps: int
    confounder_key: str
    regime_key: str


class PartitionMetrics(TypedDict):
    effect_bps: int | None
    exposed_count: int
    control_count: int
    conditional_sign_stability_bps: int
    cross_regime_stability_bps: int
    material_same_sign: bool
    insufficient: bool
    insufficient_reason: str | None


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("MC14 B04 timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


def _rounded_ratio(numerator: int, denominator: int) -> int:
    if denominator == 0:
        raise ValueError("MC14 B04 ratio denominator cannot be zero")
    sign = -1 if numerator * denominator < 0 else 1
    numerator_abs = abs(numerator)
    denominator_abs = abs(denominator)
    return sign * (
        (numerator_abs + denominator_abs // 2) // denominator_abs
    )


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        raise ValueError("MC14 B04 percentile requires values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    weight_million = int(round((position - left) * 1_000_000))
    return _rounded_ratio(
        ordered[left] * (1_000_000 - weight_million)
        + ordered[right] * weight_million,
        1_000_000,
    )


def freeze_source_thresholds(values: list[int]) -> tuple[int, int]:
    """Freeze broad source-only tails before any future target is consulted."""

    low = _percentile(values, DISCOVERY_LOW_QUANTILE)
    high = _percentile(values, DISCOVERY_HIGH_QUANTILE)
    if low >= high:
        distinct = sorted(set(values))
        if len(distinct) < 2:
            raise ValueError(
                "MC14 B04 source feature lacks threshold diversity"
            )
        pivot = len(distinct) // 2
        low = distinct[max(0, pivot - 1)]
        high = distinct[min(len(distinct) - 1, pivot)]
    if low >= high:
        raise ValueError("MC14 B04 source thresholds are not strict")
    return low, high


@dataclass(frozen=True, slots=True)
class B04WindowFeatures:
    window_index: int
    source_at: datetime
    request_from_at: datetime
    request_to_at: datetime
    bid_tick_count: int
    ask_tick_count: int
    values: tuple[tuple[str, int], ...]
    complete: bool

    def feature(self, name: str) -> int:
        return dict(self.values)[name]


def _shards_by_window(root: Path) -> dict[int, list[Path]]:
    grouped: dict[int, list[Path]] = defaultdict(list)
    for path in sorted(root.rglob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            first = handle.readline()
        if not first:
            continue
        header = json.loads(first).get("header")
        if not isinstance(header, dict):
            raise ValueError(f"MC14 B04 shard missing header: {path}")
        grouped[int(header["window_index"])].append(path)
    return dict(grouped)


def _window_bounds(paths: list[Path]) -> tuple[datetime, datetime]:
    starts: list[datetime] = []
    ends: list[datetime] = []
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            header = json.loads(handle.readline())["header"]
        starts.append(_utc(str(header["request_from_at"])))
        ends.append(_utc(str(header["request_to_at"])))
    return min(starts), max(ends)


def _read_pre_source_ticks(
    paths: list[Path],
    *,
    source_at: datetime,
) -> tuple[list[tuple[datetime, str, int]], int, int]:
    ticks: list[tuple[datetime, str, int]] = []
    bid_count = 0
    ask_count = 0
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            header = json.loads(handle.readline())["header"]
            side = str(header["quote_side"]).lower()
            if side not in {"bid", "ask"}:
                raise ValueError("MC14 B04 quote side must be bid or ask")
            for line in handle:
                payload = json.loads(line).get("tick")
                if not isinstance(payload, dict):
                    continue
                observed_at = _utc(str(payload["provider_event_at"]))
                if observed_at > source_at:
                    continue
                price = int(payload["relative_price"])
                ticks.append((observed_at, side, price))
                if side == "bid":
                    bid_count += 1
                else:
                    ask_count += 1
    ticks.sort(key=lambda item: item[0])
    return ticks, bid_count, ask_count


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("MC14 B04 median requires values")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return _rounded_ratio(ordered[middle - 1] + ordered[middle], 2)


def _p90(values: list[int]) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("MC14 B04 p90 requires values")
    index = max(0, (9 * len(ordered) + 9) // 10 - 1)
    return ordered[min(index, len(ordered) - 1)]


def extract_window_features(
    *,
    root: Path,
    expected_window_count: int = EXPECTED_WINDOW_COUNT,
) -> tuple[B04WindowFeatures, ...]:
    """Extract preregistered features while cutting every window at source."""

    grouped = _shards_by_window(root)
    rows: list[B04WindowFeatures] = []
    for window_index in range(expected_window_count):
        paths = grouped.get(window_index, [])
        if not paths:
            rows.append(
                B04WindowFeatures(
                    window_index=window_index,
                    source_at=datetime.min.replace(tzinfo=UTC),
                    request_from_at=datetime.min.replace(tzinfo=UTC),
                    request_to_at=datetime.min.replace(tzinfo=UTC),
                    bid_tick_count=0,
                    ask_tick_count=0,
                    values=(),
                    complete=False,
                )
            )
            continue

        request_from_at, request_to_at = _window_bounds(paths)
        source_at = request_to_at - timedelta(minutes=POST_SOURCE_MINUTES)
        if source_at <= request_from_at:
            raise ValueError(
                "MC14 B04 source cutoff precedes acquisition window"
            )

        ticks, bid_count, ask_count = _read_pre_source_ticks(
            paths,
            source_at=source_at,
        )
        latest_bid: int | None = None
        latest_ask: int | None = None
        mids2: list[int] = []
        spreads_bps: list[int] = []
        updates_by_time: dict[datetime, dict[str, int]] = defaultdict(dict)
        for observed_at, side, price in ticks:
            updates_by_time[observed_at][side] = price

        for observed_at in sorted(updates_by_time):
            updates = updates_by_time[observed_at]
            if "bid" in updates:
                latest_bid = updates["bid"]
            if "ask" in updates:
                latest_ask = updates["ask"]
            if latest_bid is None or latest_ask is None:
                continue
            if latest_ask < latest_bid:
                continue
            mid2 = latest_bid + latest_ask
            if mid2 <= 0:
                continue
            mids2.append(mid2)
            spreads_bps.append(
                _rounded_ratio(
                    (latest_ask - latest_bid) * 20_000,
                    mid2,
                )
            )

        complete = bool(bid_count and ask_count and len(mids2) >= 2)
        if not complete:
            rows.append(
                B04WindowFeatures(
                    window_index=window_index,
                    source_at=source_at,
                    request_from_at=request_from_at,
                    request_to_at=request_to_at,
                    bid_tick_count=bid_count,
                    ask_tick_count=ask_count,
                    values=(),
                    complete=False,
                )
            )
            continue

        duration_seconds = int(
            (source_at - request_from_at).total_seconds()
        )
        if duration_seconds <= 0:
            raise ValueError("MC14 B04 source window duration invalid")
        mid_return_bps = _rounded_ratio(
            (mids2[-1] - mids2[0]) * 10_000,
            mids2[0],
        )
        values = {
            "MID_RETURN_BPS": mid_return_bps,
            "ABS_MID_RETURN_BPS": abs(mid_return_bps),
            "MEDIAN_SPREAD_BPS": _median(spreads_bps),
            "P90_SPREAD_BPS": _p90(spreads_bps),
            "BID_TICK_RATE": _rounded_ratio(
                bid_count * 60_000,
                duration_seconds,
            ),
            "ASK_TICK_RATE": _rounded_ratio(
                ask_count * 60_000,
                duration_seconds,
            ),
            "QUOTE_SIDE_ACTIVITY_IMBALANCE_BPS": _rounded_ratio(
                (bid_count - ask_count) * 10_000,
                bid_count + ask_count,
            ),
        }
        rows.append(
            B04WindowFeatures(
                window_index=window_index,
                source_at=source_at,
                request_from_at=request_from_at,
                request_to_at=request_to_at,
                bid_tick_count=bid_count,
                ask_tick_count=ask_count,
                values=tuple(sorted(values.items())),
                complete=True,
            )
        )
    return tuple(rows)


def _sign(value: int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def partition_metrics(
    rows: list[CausalMetricRow],
    *,
    low: int,
    high: int,
    reference_sign: int | None = None,
) -> PartitionMetrics:
    exposed = [
        int(row["target_bps"])
        for row in rows
        if int(row["source"]) >= high
    ]
    controls = [
        int(row["target_bps"])
        for row in rows
        if int(row["source"]) <= low
    ]
    if (
        len(exposed) < MINIMUM_GROUP_COUNT
        or len(controls) < MINIMUM_GROUP_COUNT
    ):
        return {
            "effect_bps": None,
            "exposed_count": len(exposed),
            "control_count": len(controls),
            "conditional_sign_stability_bps": 0,
            "cross_regime_stability_bps": 0,
            "material_same_sign": False,
            "insufficient": True,
            "insufficient_reason": "MINIMUM_GROUP_COUNT_NOT_MET",
        }

    effect = int(round(mean(exposed) - mean(controls)))

    def stability(group_key: str) -> int:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[str(row[group_key])].append(row)
        effects: list[int] = []
        for group in grouped.values():
            group_exposed = [
                int(row["target_bps"])
                for row in group
                if int(row["source"]) >= high
            ]
            group_controls = [
                int(row["target_bps"])
                for row in group
                if int(row["source"]) <= low
            ]
            if (
                len(group_exposed) < MINIMUM_STRATUM_GROUP_COUNT
                or len(group_controls) < MINIMUM_STRATUM_GROUP_COUNT
            ):
                continue
            effects.append(
                int(round(mean(group_exposed) - mean(group_controls)))
            )
        if not effects:
            return 0
        consistent = sum(
            abs(value) >= MINIMUM_EFFECT_BPS
            and _sign(value) == _sign(effect)
            for value in effects
        )
        return consistent * 10_000 // len(effects)

    conditional = stability("confounder_key")
    regimes = stability("regime_key")
    material = (
        abs(effect) >= MINIMUM_EFFECT_BPS
        and (
            reference_sign is None
            or _sign(effect) == reference_sign
        )
        and conditional >= MINIMUM_STABILITY_BPS
        and regimes >= MINIMUM_STABILITY_BPS
    )
    return {
        "effect_bps": effect,
        "exposed_count": len(exposed),
        "control_count": len(controls),
        "conditional_sign_stability_bps": conditional,
        "cross_regime_stability_bps": regimes,
        "material_same_sign": material,
        "insufficient": False,
        "insufficient_reason": None,
    }
