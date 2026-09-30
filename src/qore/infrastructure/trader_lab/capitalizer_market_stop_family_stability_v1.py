"""Temporal stability audit for Capitalizer market-specific stop state families.

Compares the exact same pre-trade state-family IDs across consumed 5Y development and the
already-consumed 5Y holdout. This is descriptive falsification, not a fresh holdout claim.

The audit intentionally does not choose a buffer. It asks whether:
- state families recur through time;
- stop rates persist;
- post-stop target recovery persists;
- the amount of extra adverse excursion needed by recovered stops persists.

Missing pre-trade dimensions are recorded explicitly so unstable breathing is not disguised
as a tunable numeric problem.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

IDENTITY = "QORE_CAPITALIZER_MARKET_STOP_FAMILY_STABILITY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_FAMILY_STABILITY_MATRIX_V1"
FAMILY_IDENTITY = "QORE_CAPITALIZER_MARKET_STOP_STATE_FAMILY_LAB_V1"
DENSITY_GRID = (5, 10, 20)
MISSING_PRETRADE_DIMENSIONS = (
    "FRESH_REPEAT_STATE",
    "RECLAIM_STATE",
    "SPREAD_AT_ENTRY",
    "TICK_SIZE_NORMALIZED_SPREAD",
    "MARKET_VOLATILITY_STATE",
    "DISPLACEMENT_SPEED_STATE",
    "EXPANSION_SPEED_STATE",
)


@dataclass(frozen=True, slots=True)
class CapitalizerStopFamilyStabilitySlice:
    min_trades_each_window: int
    common_families: int
    stop_rate_correlation: str | None
    recovery_rate_correlation: str | None
    recovered_extra_r_correlation: str | None
    median_absolute_stop_rate_delta: str | None
    median_absolute_recovery_rate_delta: str | None
    median_absolute_recovered_extra_r_delta: str | None


@dataclass(frozen=True, slots=True)
class CapitalizerMarketStopFamilyStability:
    identity: str
    symbol: str
    session: str
    development_trades: int
    consumed_holdout_trades: int
    development_families: int
    consumed_holdout_families: int
    common_family_count: int
    development_common_trade_coverage: str
    consumed_holdout_common_trade_coverage: str
    slices: tuple[CapitalizerStopFamilyStabilitySlice, ...]
    missing_pretrade_dimensions: tuple[str, ...]
    family_key_uses_outcome: bool = False
    fresh_holdout_claimed: bool = False
    buffer_freeze_supported: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False


def _read_report(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-market-stop-state-families-v1.json"))
    if len(paths) != 1:
        raise ValueError(f"expected one state-family report, got {len(paths)}")
    raw = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("identity") != FAMILY_IDENTITY:
        raise ValueError("unexpected state-family report identity")
    if raw.get("family_key_uses_outcome") is not False:
        raise ValueError("stability audit requires outcome-free family keys")
    return raw


def _family_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    families = report.get("families")
    if not isinstance(families, list):
        raise ValueError("state-family report missing families")
    result: dict[str, dict[str, Any]] = {}
    for item in families:
        if not isinstance(item, dict):
            raise ValueError("state-family item must be object")
        key = str(item["state_family_id"])
        if key in result:
            raise ValueError("duplicate state_family_id")
        result[key] = item
    return result


def _pearson(xs: list[Decimal], ys: list[Decimal]) -> Decimal | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mean_x = sum(xs, Decimal("0")) / Decimal(len(xs))
    mean_y = sum(ys, Decimal("0")) / Decimal(len(ys))
    var_x = sum((value - mean_x) ** 2 for value in xs)
    var_y = sum((value - mean_y) ** 2 for value in ys)
    if var_x == 0 or var_y == 0:
        return None
    covariance = sum(
        (x_value - mean_x) * (y_value - mean_y)
        for x_value, y_value in zip(xs, ys, strict=True)
    )
    denominator = Decimal(str(math.sqrt(float(var_x * var_y))))
    if denominator == 0:
        return None
    return covariance / denominator


def _optional_decimal(row: dict[str, Any], key: str) -> Decimal | None:
    value = row.get(key)
    if value is None:
        return None
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{key} must be finite")
    return result


def _median_abs_delta(pairs: list[tuple[Decimal, Decimal]]) -> Decimal | None:
    if not pairs:
        return None
    return median(abs(left - right) for left, right in pairs)


def _slice(
    *,
    development: dict[str, dict[str, Any]],
    holdout: dict[str, dict[str, Any]],
    min_trades: int,
) -> CapitalizerStopFamilyStabilitySlice:
    keys = sorted(
        key
        for key in development.keys() & holdout.keys()
        if int(development[key]["trades"]) >= min_trades
        and int(holdout[key]["trades"]) >= min_trades
    )

    stop_pairs = [
        (
            Decimal(str(development[key]["stop_rate"])),
            Decimal(str(holdout[key]["stop_rate"])),
        )
        for key in keys
    ]
    recovery_pairs: list[tuple[Decimal, Decimal]] = []
    extra_pairs: list[tuple[Decimal, Decimal]] = []
    for key in keys:
        dev_recovery = _optional_decimal(
            development[key],
            "target_recovery_after_stop_rate",
        )
        hold_recovery = _optional_decimal(
            holdout[key],
            "target_recovery_after_stop_rate",
        )
        if dev_recovery is not None and hold_recovery is not None:
            recovery_pairs.append((dev_recovery, hold_recovery))

        dev_extra = _optional_decimal(
            development[key],
            "median_extra_stop_r_recovered",
        )
        hold_extra = _optional_decimal(
            holdout[key],
            "median_extra_stop_r_recovered",
        )
        if dev_extra is not None and hold_extra is not None:
            extra_pairs.append((dev_extra, hold_extra))

    def correlation(
        pairs: list[tuple[Decimal, Decimal]],
    ) -> str | None:
        value = _pearson(
            [left for left, _ in pairs],
            [right for _, right in pairs],
        )
        return None if value is None else str(value)

    def delta(
        pairs: list[tuple[Decimal, Decimal]],
    ) -> str | None:
        value = _median_abs_delta(pairs)
        return None if value is None else str(value)

    return CapitalizerStopFamilyStabilitySlice(
        min_trades_each_window=min_trades,
        common_families=len(keys),
        stop_rate_correlation=correlation(stop_pairs),
        recovery_rate_correlation=correlation(recovery_pairs),
        recovered_extra_r_correlation=correlation(extra_pairs),
        median_absolute_stop_rate_delta=delta(stop_pairs),
        median_absolute_recovery_rate_delta=delta(recovery_pairs),
        median_absolute_recovered_extra_r_delta=delta(extra_pairs),
    )


def build_market_stability(
    development_root: Path,
    holdout_root: Path,
) -> CapitalizerMarketStopFamilyStability:
    development_report = _read_report(development_root)
    holdout_report = _read_report(holdout_root)
    symbol = str(development_report["symbol"])
    session = str(development_report["session"])
    if symbol != str(holdout_report["symbol"]):
        raise ValueError("development/holdout symbol mismatch")
    if session != str(holdout_report["session"]):
        raise ValueError("development/holdout session mismatch")

    development = _family_index(development_report)
    holdout = _family_index(holdout_report)
    common = development.keys() & holdout.keys()
    dev_common_trades = sum(int(development[key]["trades"]) for key in common)
    hold_common_trades = sum(int(holdout[key]["trades"]) for key in common)
    dev_total = int(development_report["source_trade_count"])
    hold_total = int(holdout_report["source_trade_count"])

    return CapitalizerMarketStopFamilyStability(
        identity=IDENTITY,
        symbol=symbol,
        session=session,
        development_trades=dev_total,
        consumed_holdout_trades=hold_total,
        development_families=len(development),
        consumed_holdout_families=len(holdout),
        common_family_count=len(common),
        development_common_trade_coverage=str(
            Decimal(dev_common_trades) / Decimal(dev_total)
        ),
        consumed_holdout_common_trade_coverage=str(
            Decimal(hold_common_trades) / Decimal(hold_total)
        ),
        slices=tuple(
            _slice(
                development=development,
                holdout=holdout,
                min_trades=min_trades,
            )
            for min_trades in DENSITY_GRID
        ),
        missing_pretrade_dimensions=MISSING_PRETRADE_DIMENSIONS,
    )


def write_market_stability(
    report: CapitalizerMarketStopFamilyStability,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-{report.symbol.lower()}-market-stop-family-stability-v1.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-market-stop-family-stability-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"stability matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    expected = {
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "USDCAD",
        "USDJPY",
        "XAUUSD",
    }
    if {str(report["symbol"]) for report in reports} != expected:
        raise ValueError("stability matrix universe mismatch")
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "family_key_uses_outcome": False,
        "fresh_holdout_claimed": False,
        "buffer_freeze_supported": False,
        "missing_pretrade_dimensions": list(MISSING_PRETRADE_DIMENSIONS),
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-stop-family-stability-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("development_root", type=Path)
    market.add_argument("holdout_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        market_report = build_market_stability(
            args.development_root,
            args.holdout_root,
        )
        write_market_stability(market_report, args.output)
        print(
            json.dumps(
                {
                    "identity": market_report.identity,
                    "symbol": market_report.symbol,
                    "common_families": market_report.common_family_count,
                    "dev_coverage": market_report.development_common_trade_coverage,
                    "holdout_coverage": (
                        market_report.consumed_holdout_common_trade_coverage
                    ),
                    "buffer_freeze_supported": market_report.buffer_freeze_supported,
                },
                sort_keys=True,
            )
        )
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
