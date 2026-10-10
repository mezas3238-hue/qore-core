"""Decision-time causal forensics for SOURCE_FIRST-added MAX3 trades.

Joins the frozen V3/SOURCE_FIRST ledgers to the frozen CISD-boundary semantics census.
Only SOURCE_FIRST MAX3 trades whose causal closeback opportunity did not produce a V3
raw trade are analyzed.

The lab groups those trades using information available no later than entry:
- original V3 first blocker;
- frozen M5 directional state;
- SOURCE_FIRST relation vs V3 structural MSS;
- liquidity source, side, entry mode;
- sweep -> boundary, boundary -> MSS, closeback -> MSS timing;
- whether the persistent boundary was established before or after the M5 closeback;
- M3 confirmation minute band and calendar quarter.

It also repeats those diagnostics inside the exact SOURCE_FIRST max-drawdown episode.
Post-outcome cohort metrics are descriptive only and cannot promote a runtime rule.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_delta_drawdown_forensics_2y_v1 as delta,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_ADDED_CAUSAL_FORENSICS_2Y_V1"
EXPECTED_SOURCE_FIRST_MAX3 = 1118
EXPECTED_ADDED_SELECTED = 719
EXPECTED_DD_EPISODE_TRADES = 148
EXPECTED_DD_ADDED = 87


def _load_semantics_rows(root: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-cisd-boundary-semantics-census-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"causal forensics requires 9 semantics ledgers, got {len(paths)}")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("semantics row must be object")
                key = (
                    str(raw["symbol"]),
                    str(raw["side"]),
                    str(raw["closeback_at"]),
                )
                if key in result:
                    raise ValueError("duplicate semantics closeback key")
                result[key] = raw
    return result


def _meta_key(trade: v3.V3Trade) -> tuple[str, str, str]:
    return (trade.symbol, trade.side, trade.m5_closeback_at)


def _minutes(start: str, end: str) -> Decimal:
    delta_seconds = (
        datetime.fromisoformat(end) - datetime.fromisoformat(start)
    ).total_seconds()
    return Decimal(str(delta_seconds)) / Decimal("60")


def _band(
    value: Decimal,
    limits: tuple[tuple[Decimal, str], ...],
    tail: str,
) -> str:
    for maximum, label in limits:
        if value <= maximum:
            return label
    return tail


def _closeback_to_mss(row: dict[str, Any]) -> str:
    value = _minutes(str(row["closeback_at"]), str(row["source_first_mss_at"]))
    return _band(
        value,
        (
            (Decimal("15"), "00_15M"),
            (Decimal("30"), "15_30M"),
            (Decimal("45"), "30_45M"),
        ),
        "45M_PLUS",
    )


def _boundary_age(row: dict[str, Any]) -> str:
    started = row["source_first_boundary_started_at"]
    confirmed = row["source_first_mss_at"]
    if started is None or confirmed is None:
        raise ValueError("selected SOURCE_FIRST trade requires boundary/MSS timestamps")
    value = _minutes(str(started), str(confirmed))
    return _band(
        value,
        (
            (Decimal("15"), "00_15M"),
            (Decimal("30"), "15_30M"),
            (Decimal("45"), "30_45M"),
        ),
        "45M_PLUS",
    )


def _sweep_to_boundary(row: dict[str, Any]) -> str:
    started = row["source_first_boundary_started_at"]
    if started is None:
        raise ValueError("selected SOURCE_FIRST trade requires boundary timestamp")
    value = _minutes(str(row["sweep_at"]), str(started))
    return _band(
        value,
        (
            (Decimal("6"), "00_06M"),
            (Decimal("15"), "06_15M"),
            (Decimal("30"), "15_30M"),
        ),
        "30M_PLUS",
    )


def _boundary_phase(row: dict[str, Any]) -> str:
    started = row["source_first_boundary_started_at"]
    if started is None:
        raise ValueError("selected SOURCE_FIRST trade requires boundary timestamp")
    boundary_at = datetime.fromisoformat(str(started))
    closeback_at = datetime.fromisoformat(str(row["closeback_at"]))
    if boundary_at <= closeback_at:
        return "BOUNDARY_PRE_OR_AT_CLOSEBACK"
    return "BOUNDARY_POST_CLOSEBACK"


def _mss_minute_band(row: dict[str, Any]) -> str:
    confirmed = datetime.fromisoformat(str(row["source_first_mss_at"]))
    minute = confirmed.minute
    if minute <= 14:
        return "MINUTE_00_14"
    if minute <= 29:
        return "MINUTE_15_29"
    if minute <= 44:
        return "MINUTE_30_44"
    return "MINUTE_45_59"


def _quarter(trade: v3.V3Trade) -> str:
    value = datetime.fromisoformat(trade.entry_at)
    quarter = (value.month - 1) // 3 + 1
    return f"{value.year}-Q{quarter}"


def _body_ratio_band(trade: v3.V3Trade) -> str:
    value = Decimal(trade.m3_body_ratio)
    if value < Decimal("0.70"):
        return "BODY_60_70"
    if value < Decimal("0.80"):
        return "BODY_70_80"
    if value < Decimal("0.90"):
        return "BODY_80_90"
    return "BODY_90_100"


def _displacement_atr_band(trade: v3.V3Trade) -> str:
    atr = Decimal(trade.m3_atr14)
    if atr <= 0:
        raise ValueError("M3 ATR must be positive")
    ratio = Decimal(trade.m3_displacement_range) / atr
    if ratio < Decimal("1.50"):
        return "ATR_1_2_1_5"
    if ratio < Decimal("2.00"):
        return "ATR_1_5_2_0"
    return "ATR_2_0_PLUS"


def _mss_to_entry_band(trade: v3.V3Trade) -> str:
    value = _minutes(trade.m3_mss_at, trade.entry_at)
    return _band(
        value,
        (
            (Decimal("5"), "00_05M"),
            (Decimal("15"), "05_15M"),
            (Decimal("30"), "15_30M"),
        ),
        "30M_PLUS",
    )


def _entry_maturity(trade: v3.V3Trade) -> str:
    value = _minutes(trade.m3_mss_at, trade.entry_at)
    return "IMMEDIATE_LE_5M" if value <= Decimal("5") else "MATURE_GT_5M"


def _closeback_maturity(row: dict[str, Any]) -> str:
    value = _minutes(str(row["closeback_at"]), str(row["source_first_mss_at"]))
    return "EARLY_LE_15M" if value <= Decimal("15") else "MATURE_GT_15M"


def _mss_to_fvg_band(trade: v3.V3Trade) -> str:
    value = _minutes(trade.m3_mss_at, trade.m1_fvg_confirmed_at)
    return _band(
        value,
        (
            (Decimal("3"), "00_03M"),
            (Decimal("10"), "03_10M"),
            (Decimal("20"), "10_20M"),
        ),
        "20M_PLUS",
    )


def _metrics(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def _group(
    rows: tuple[tuple[v3.V3Trade, dict[str, Any]], ...],
    key_fn: Callable[[v3.V3Trade, dict[str, Any]], str],
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[v3.V3Trade]] = {}
    for trade, meta in rows:
        key = key_fn(trade, meta)
        buckets.setdefault(key, []).append(trade)
    result: dict[str, dict[str, Any]] = {}
    for key, values in sorted(buckets.items()):
        trades = tuple(values)
        result[key] = {
            "trades": len(trades),
            "metrics": _metrics(trades),
            "total_r": str(
                sum(
                    (Decimal(item.realized_gross_r) for item in trades),
                    Decimal("0"),
                )
            ),
        }
    return result


def build_report(
    v3_root: Path,
    source_first_root: Path,
    semantics_root: Path,
) -> dict[str, Any]:
    baseline_raw = delta._load_v3(v3_root)
    source_raw = delta._load_source_first(source_first_root)
    source_max3 = v3._portfolio_max3(source_raw)
    if len(source_max3) != EXPECTED_SOURCE_FIRST_MAX3:
        raise ValueError("SOURCE_FIRST MAX3 control mismatch")

    base_keys = {delta._key(item) for item in baseline_raw}
    added = tuple(
        item for item in source_max3 if delta._key(item) not in base_keys
    )
    if len(added) != EXPECTED_ADDED_SELECTED:
        raise ValueError("SOURCE_FIRST added-selected control mismatch")

    semantics = _load_semantics_rows(semantics_root)
    joined: list[tuple[v3.V3Trade, dict[str, Any]]] = []
    for trade in added:
        meta = semantics.get(_meta_key(trade))
        if meta is None:
            raise ValueError(f"missing semantics metadata for {_meta_key(trade)}")
        if str(meta["source_first_mss_at"]) != trade.m3_mss_at:
            raise ValueError("SOURCE_FIRST trade/census MSS mismatch")
        joined.append((trade, meta))
    joined_rows = tuple(joined)

    episode = delta._drawdown_episode(source_max3)
    episode_trades = tuple(episode["episode_trades"])
    if len(episode_trades) != EXPECTED_DD_EPISODE_TRADES:
        raise ValueError("SOURCE_FIRST DD episode control mismatch")
    episode_keys = {delta._key(item) for item in episode_trades}
    dd_added = tuple(
        row for row in joined_rows if delta._key(row[0]) in episode_keys
    )
    if len(dd_added) != EXPECTED_DD_ADDED:
        raise ValueError("SOURCE_FIRST DD-added control mismatch")

    dimensions: dict[str, Callable[[v3.V3Trade, dict[str, Any]], str]] = {
        "original_first_blocker": lambda _t, m: str(m["original_first_blocker"]),
        "m5_state": lambda _t, m: str(m["m5_state"]),
        "relation_vs_v3": lambda _t, m: str(m["source_first_relation_vs_v3"]),
        "liquidity_source": lambda t, _m: t.liquidity_source,
        "side": lambda t, _m: t.side,
        "entry_mode": lambda t, _m: t.entry_mode,
        "closeback_to_mss": lambda _t, m: _closeback_to_mss(m),
        "boundary_age": lambda _t, m: _boundary_age(m),
        "sweep_to_boundary": lambda _t, m: _sweep_to_boundary(m),
        "boundary_phase": lambda _t, m: _boundary_phase(m),
        "mss_minute_band": lambda _t, m: _mss_minute_band(m),
        "calendar_quarter": lambda t, _m: _quarter(t),
        "body_ratio_band": lambda t, _m: _body_ratio_band(t),
        "displacement_atr_band": lambda t, _m: _displacement_atr_band(t),
        "mss_to_entry": lambda t, _m: _mss_to_entry_band(t),
        "mss_to_fvg": lambda t, _m: _mss_to_fvg_band(t),
        "ob_fvg_overlap": lambda t, _m: (
            "OVERLAP" if t.m1_ob_fvg_overlap else "NO_OVERLAP"
        ),
        "market": lambda t, _m: t.symbol,
        "session": lambda t, _m: t.session,
    }

    overall_groups = {
        name: _group(joined_rows, fn)
        for name, fn in dimensions.items()
    }
    dd_groups = {
        name: _group(dd_added, fn)
        for name, fn in dimensions.items()
    }

    relation_strata: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    relation_subsets: dict[str, tuple[tuple[v3.V3Trade, dict[str, Any]], ...]] = {}
    for relation in (
        "PREEMPTS_V3_MSS",
        "RECOVERS_NO_V3_MSS",
    ):
        subset = tuple(
            row
            for row in joined_rows
            if str(row[1]["source_first_relation_vs_v3"]) == relation
        )
        relation_subsets[relation] = subset
        relation_strata[relation] = {
            name: _group(subset, fn)
            for name, fn in dimensions.items()
        }

    recovery_rows = relation_subsets["RECOVERS_NO_V3_MSS"]
    recovery_maturation_cube = _group(
        recovery_rows,
        lambda t, m: "|".join(
            (
                _boundary_phase(m),
                _entry_maturity(t),
                "OVERLAP" if t.m1_ob_fvg_overlap else "NO_OVERLAP",
            )
        ),
    )
    recovery_timing_cube = _group(
        recovery_rows,
        lambda t, m: "|".join(
            (
                _closeback_maturity(m),
                _entry_maturity(t),
                "OVERLAP" if t.m1_ob_fvg_overlap else "NO_OVERLAP",
            )
        ),
    )

    state_counts = Counter(str(meta["m5_state"]) for _, meta in joined_rows)
    relation_counts = Counter(
        str(meta["source_first_relation_vs_v3"])
        for _, meta in joined_rows
    )

    return {
        "identity": IDENTITY,
        "source_first_max3_trades": len(source_max3),
        "added_selected_trades": len(added),
        "metadata_rows_joined": len(joined_rows),
        "m5_state_counts": dict(sorted(state_counts.items())),
        "relation_vs_v3_counts": dict(sorted(relation_counts.items())),
        "overall_groups": overall_groups,
        "relation_strata": relation_strata,
        "recovery_maturation_cube": recovery_maturation_cube,
        "recovery_timing_cube": recovery_timing_cube,
        "joint_state_exploratory_only": True,
        "max_drawdown_episode": {
            "drawdown_r": episode["drawdown_r"],
            "peak_exit_at": episode["peak_exit_at"],
            "trough_exit_at": episode["trough_exit_at"],
            "trades_in_episode": len(episode_trades),
            "added_trades_in_episode": len(dd_added),
            "added_groups": dd_groups,
        },
        "timing_bands_predeclared": True,
        "decision_time_features_only": True,
        "post_outcome_metrics_descriptive_only": True,
        "outcome_used_for_admission": False,
        "rule_derived": False,
        "strategy_mutated": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "fresh_holdout_claimed": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-v3-source-first-added-causal-forensics-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("v3_root", type=Path)
    parser.add_argument("source_first_root", type=Path)
    parser.add_argument("semantics_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(
        args.v3_root,
        args.source_first_root,
        args.semantics_root,
    )
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
