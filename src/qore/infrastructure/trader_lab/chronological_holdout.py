"""Chronological development/holdout partitioning for Trader Lab market evidence.

This module never evaluates Trader outcomes. It only partitions already collected,
read-only market evidence by time and records cryptographic provenance so that a
validation holdout cannot be consumed by development/backtest analytics accidentally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

_SCHEMA = "qore.trader_lab.chronological_holdout.v1"
_REQUIRED_PERIODS = ("M5", "M15", "H4")
_GAP_POLICY = (
    "raw closed-bar discontinuities; includes legitimate market closures and does not "
    "infer missing tradable candles"
)


class ChronologicalHoldoutError(ValueError):
    """Raised when evidence cannot be partitioned without weakening the holdout."""


def _timestamp(value: object, *, field_name: str) -> datetime:
    if type(value) is not str or not value:
        raise ChronologicalHoldoutError(f"{field_name} must be RFC3339 text")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ChronologicalHoldoutError(f"{field_name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ChronologicalHoldoutError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _rows(payload: dict[str, object], period: str) -> list[dict[str, object]]:
    periods = payload.get("periods")
    if type(periods) is not dict:
        raise ChronologicalHoldoutError("periods must be a JSON object")
    raw_rows = periods.get(period)
    if type(raw_rows) is not list:
        raise ChronologicalHoldoutError(f"period {period} must be a JSON array")
    rows: list[dict[str, object]] = []
    for item in raw_rows:
        if type(item) is not dict:
            raise ChronologicalHoldoutError(f"period {period} contains a non-object bar")
        row = cast(dict[str, object], item)
        _timestamp(row.get("opened_at"), field_name=f"{period}.opened_at")
        _timestamp(row.get("closed_at"), field_name=f"{period}.closed_at")
        rows.append(row)
    ordered = sorted(
        rows,
        key=lambda row: _timestamp(
            row["closed_at"], field_name=f"{period}.closed_at"
        ),
    )
    if rows != ordered:
        raise ChronologicalHoldoutError(f"period {period} is not chronological")
    identities = [
        (
            _timestamp(row["opened_at"], field_name=f"{period}.opened_at"),
            _timestamp(row["closed_at"], field_name=f"{period}.closed_at"),
        )
        for row in rows
    ]
    if len(set(identities)) != len(identities):
        raise ChronologicalHoldoutError(f"period {period} contains duplicate bars")
    return rows


def _coverage(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "bar_count": 0,
            "first_opened_at": None,
            "last_closed_at": None,
            "maximum_observed_gap_seconds": 0,
            "observed_gap_count": 0,
            "observed_gap_seconds": 0,
            "span_days": 0,
            "span_seconds": 0,
            "gap_policy": _GAP_POLICY,
        }
    first = _timestamp(rows[0]["opened_at"], field_name="bar.opened_at")
    last = _timestamp(rows[-1]["closed_at"], field_name="bar.closed_at")
    span_seconds = int((last - first).total_seconds())
    gaps: list[int] = []
    previous_closed = _timestamp(rows[0]["closed_at"], field_name="bar.closed_at")
    for row in rows[1:]:
        opened = _timestamp(row["opened_at"], field_name="bar.opened_at")
        gap = int((opened - previous_closed).total_seconds())
        if gap != 0:
            if gap < 0:
                raise ChronologicalHoldoutError("bar chronology overlaps")
            gaps.append(gap)
        previous_closed = _timestamp(row["closed_at"], field_name="bar.closed_at")
    return {
        "bar_count": len(rows),
        "first_opened_at": first.isoformat(timespec="microseconds"),
        "last_closed_at": last.isoformat(timespec="microseconds"),
        "maximum_observed_gap_seconds": max(gaps, default=0),
        "observed_gap_count": len(gaps),
        "observed_gap_seconds": sum(gaps),
        "span_days": span_seconds // 86_400,
        "span_seconds": span_seconds,
        "gap_policy": _GAP_POLICY,
    }


def _partition(
    raw: dict[str, object], *, cutoff: datetime, required_development_days: int
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ChronologicalHoldoutError("cutoff must be timezone-aware")
    cutoff = cutoff.astimezone(UTC)
    if type(required_development_days) is not int or required_development_days < 1:
        raise ChronologicalHoldoutError("required_development_days must be positive int")
    periods = raw.get("periods")
    if type(periods) is not dict or set(periods) != {"M1", "M5", "M15", "H4"}:
        raise ChronologicalHoldoutError("evidence must contain exactly M1/M5/M15/H4")

    development = deepcopy(raw)
    holdout = deepcopy(raw)
    dev_periods = cast(dict[str, object], development["periods"])
    hold_periods = cast(dict[str, object], holdout["periods"])
    dev_coverage: dict[str, object] = {}
    hold_coverage: dict[str, object] = {}
    boundary: dict[str, object] = {}

    for period in ("M1", "M5", "M15", "H4"):
        rows = _rows(raw, period)
        dev_rows = [
            row
            for row in rows
            if _timestamp(row["closed_at"], field_name=f"{period}.closed_at") <= cutoff
        ]
        hold_rows = [
            row
            for row in rows
            if _timestamp(row["closed_at"], field_name=f"{period}.closed_at") > cutoff
        ]
        if len(dev_rows) + len(hold_rows) != len(rows):
            raise ChronologicalHoldoutError("partition is not exhaustive")
        dev_periods[period] = dev_rows
        hold_periods[period] = hold_rows
        dev_coverage[period] = _coverage(dev_rows)
        hold_coverage[period] = _coverage(hold_rows)
        dev_period_coverage = cast(dict[str, object], dev_coverage[period])
        hold_period_coverage = cast(dict[str, object], hold_coverage[period])
        boundary[period] = {
            "development_last_closed_at": dev_period_coverage["last_closed_at"],
            "holdout_first_opened_at": hold_period_coverage["first_opened_at"],
            "development_bar_count": len(dev_rows),
            "holdout_bar_count": len(hold_rows),
        }

    minimum_seconds = required_development_days * 86_400
    for period in _REQUIRED_PERIODS:
        coverage = cast(dict[str, object], dev_coverage[period])
        span = coverage["span_seconds"]
        if type(span) is not int or span < minimum_seconds:
            raise ChronologicalHoldoutError(
                f"development partition {period} has less than "
                f"{required_development_days} calendar days"
            )
        hold_rows = cast(list[object], hold_periods[period])
        if not hold_rows:
            raise ChronologicalHoldoutError(f"holdout partition {period} is empty")

    development["coverage"] = dev_coverage
    development["partition_role"] = "DEVELOPMENT"
    development["holdout_cutoff"] = cutoff.isoformat(timespec="microseconds")
    development["holdout_consumption_prohibited"] = False
    development["required_coverage_days"] = required_development_days
    dev_span = min(
        cast(dict[str, object], dev_coverage[period])["span_seconds"]
        for period in _REQUIRED_PERIODS
    )
    development["requested_lookback_days"] = max(
        required_development_days,
        math.ceil(cast(int, dev_span) / 86_400),
    )

    holdout["coverage"] = hold_coverage
    holdout["partition_role"] = "UNTOUCHED_HOLDOUT"
    holdout["holdout_cutoff"] = cutoff.isoformat(timespec="microseconds")
    holdout["holdout_consumption_prohibited"] = True
    holdout["required_coverage_days"] = required_development_days

    policy_material = {
        "schema": _SCHEMA,
        "cutoff": cutoff.isoformat(timespec="microseconds"),
        "required_development_days": required_development_days,
        "boundary": boundary,
    }
    policy_fingerprint = _sha256(policy_material)
    development["holdout_policy_fingerprint"] = policy_fingerprint
    holdout["holdout_policy_fingerprint"] = policy_fingerprint
    manifest = {
        "schema": _SCHEMA,
        "cutoff": cutoff.isoformat(timespec="microseconds"),
        "required_development_days": required_development_days,
        "policy_fingerprint": policy_fingerprint,
        "boundary": boundary,
        "raw_evidence_sha256": _sha256(raw),
        "development_evidence_sha256": _sha256(development),
        "holdout_evidence_sha256": _sha256(holdout),
        "holdout_role": "UNTOUCHED_HOLDOUT",
        "development_may_consume_holdout": False,
        "holdout_may_be_opened_for_parameter_selection": False,
        "authority": {
            "research_only": True,
            "execution_authority": False,
            "demo_or_live_promotion": False,
        },
    }
    return development, holdout, manifest


def partition_tail_days(
    raw: dict[str, object], *, holdout_days: int, required_development_days: int = 730
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    if type(holdout_days) is not int or holdout_days < 1:
        raise ChronologicalHoldoutError("holdout_days must be positive int")
    anchors: list[datetime] = []
    for period in _REQUIRED_PERIODS:
        rows = _rows(raw, period)
        if not rows:
            raise ChronologicalHoldoutError(f"period {period} is empty")
        anchors.append(
            _timestamp(rows[-1]["closed_at"], field_name=f"{period}.closed_at")
        )
    anchor = min(anchors)
    cutoff = anchor - timedelta(days=holdout_days)
    development, holdout, manifest = _partition(
        raw,
        cutoff=cutoff,
        required_development_days=required_development_days,
    )
    manifest["reservation_mode"] = "HISTORICAL_TAIL_DAYS"
    manifest["holdout_days"] = holdout_days
    manifest["anchor"] = anchor.isoformat(timespec="microseconds")
    return development, holdout, manifest


def partition_at_cutoff(
    raw: dict[str, object], *, cutoff: datetime, required_development_days: int = 730
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    development, holdout, manifest = _partition(
        raw,
        cutoff=cutoff,
        required_development_days=required_development_days,
    )
    manifest["reservation_mode"] = "ABSOLUTE_CUTOFF"
    return development, holdout, manifest


def _load(path: Path) -> dict[str, object]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    if type(decoded) is not dict:
        raise ChronologicalHoldoutError("market evidence root must be object")
    return cast(dict[str, object], decoded)


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Partition Trader Lab evidence chronologically"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("development", type=Path)
    parser.add_argument("holdout", type=Path)
    parser.add_argument("manifest", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--holdout-days", type=int)
    group.add_argument("--cutoff")
    parser.add_argument("--required-development-days", type=int, default=730)
    args = parser.parse_args(argv)
    raw = _load(args.input)
    if args.holdout_days is not None:
        development, holdout, manifest = partition_tail_days(
            raw,
            holdout_days=args.holdout_days,
            required_development_days=args.required_development_days,
        )
    else:
        cutoff = _timestamp(args.cutoff, field_name="cutoff")
        development, holdout, manifest = partition_at_cutoff(
            raw,
            cutoff=cutoff,
            required_development_days=args.required_development_days,
        )
    _write(args.development, development)
    _write(args.holdout, holdout)
    _write(args.manifest, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
