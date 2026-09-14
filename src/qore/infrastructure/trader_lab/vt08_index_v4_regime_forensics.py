"""Consumed-evidence regime/context forensics for VT-08 Index V4 research.

This module does not define or freeze a V4 trading candidate. It reproduces the
rejected V3 mechanics across three already-consumed evidence windows and builds
a structural census for falsification work.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import (
    ClosurePolicy,
    SwingPolicy,
    _closure,
    _signal,
)
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import _load_candidate_market
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    CANDIDATE_ID as V3_CANDIDATE_ID,
)
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    RULE_FINGERPRINT as V3_RULE_FINGERPRINT,
)
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    STRESS_COST_R,
    _geometry,
    build_v3_candidate_report,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    AUTHORIZED_MARKETS,
    Vt08IndexC2R1Bar,
    _latest_complete_source_days,
    _window_bars,
    protected_swings_in_candle2,
)
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_v4_regime_forensics.v1"
RESEARCH_ID = "VT08_INDEX_V4_REGIME_FORENSICS_001"
V2_FRESH_SHA = "58dd289646de8814449f836ad617a51342eba0da"
V3_FRESH_SHA = "106a34282fe8eac2f8c466bcc8502d4ec8d73855"
DEVELOPMENT_SHA = "a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0"
_NY = ZoneInfo("America/New_York")


class Vt08IndexV4ForensicsError(InfrastructureError):
    __slots__ = ()


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _max_drawdown(values: Iterable[Decimal]) -> Decimal:
    equity = Decimal()
    peak = Decimal()
    maximum = Decimal()
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _metrics(rows: Iterable[dict[str, object]]) -> dict[str, object]:
    ordered = tuple(
        sorted(rows, key=lambda row: (str(row["signal_at"]), str(row["symbol"])))
    )
    values = tuple(_decimal(row["r_multiple"]) for row in ordered)
    gross_win = sum((value for value in values if value > 0), Decimal())
    gross_loss = -sum((value for value in values if value < 0), Decimal())
    total = sum(values, Decimal())
    sample = len(values)
    return {
        "sample": sample,
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / sample) if sample else "0",
        "profit_factor": str(gross_win / gross_loss) if gross_loss else None,
        "max_drawdown_r": str(_max_drawdown(values)),
        "stressed_mean_r": (
            str((total - STRESS_COST_R * sample) / sample) if sample else "0"
        ),
    }


def _body_aligned(bar: Vt08IndexC2R1Bar, side: DemoTradingSetupSide) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return bar.close > bar.open
    return bar.close < bar.open


def _bias_family(previous_day: Vt08IndexC2R1Bar, current_day: Vt08IndexC2R1Bar) -> str:
    if current_day.close > previous_day.high or current_day.close < previous_day.low:
        return "breakout"
    return "reversal"


def _load_indexed(
    path: Path,
    *,
    symbol: str,
    expected_sha: str,
    minimum_days: int,
) -> dict[datetime, Vt08IndexC2R1Bar]:
    _, _, _, bars = _load_candidate_market(
        path,
        expected_symbol=symbol,
        expected_software_sha=expected_sha,
        minimum_evidence_days=minimum_days,
    )
    return {bar.opened_at.astimezone(UTC): bar for bar in bars}


def _feature_row(
    trade: dict[str, object],
    *,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
) -> dict[str, object]:
    symbol = str(trade["symbol"])
    decision = datetime.fromisoformat(str(trade["signal_at"]))
    signal = _signal(
        symbol=symbol,
        bars_by_open=indexed,
        decision_at=decision,
        closure=ClosurePolicy.C2_OR_C3_BODY_CLOSE,
        swing=SwingPolicy.FARTHEST_STRUCTURAL,
    )
    if signal is None:
        raise Vt08IndexV4ForensicsError("official V3 trade no longer resolves")
    resolved = _closure(
        policy=ClosurePolicy.C2_OR_C3_BODY_CLOSE,
        bars_by_open=indexed,
        decision_at=decision,
        side=signal.side,
    )
    source_days = _latest_complete_source_days(
        indexed,
        before_local=decision.astimezone(_NY),
    )
    geometry = _geometry(signal, bars_by_open=indexed)
    if resolved is None or source_days is None or geometry is None:
        raise Vt08IndexV4ForensicsError("feature reconstruction drifted")
    reference, closure_bar, closure_kind = resolved
    m15 = _window_bars(indexed, opened_at=closure_bar.opened_at, count=16)
    if m15 is None:
        raise Vt08IndexV4ForensicsError("closure M15 window is incomplete")
    important = (
        reference.low if signal.side is DemoTradingSetupSide.LONG else reference.high
    )
    swings = protected_swings_in_candle2(
        m15,
        side=signal.side,
        important_level=important,
    )
    if not swings:
        raise Vt08IndexV4ForensicsError("protected-swing set drifted")
    previous_day, current_day = source_days
    selected = signal.protected_swing
    if not any(
        item.price == selected.price and item.cisd_level == selected.cisd_level
        for item in swings
    ):
        raise Vt08IndexV4ForensicsError("selected swing left reconstructed set")
    elapsed = int(
        (selected.confirmed_at - selected.opposing_series_opened_at).total_seconds()
        // 900
    )
    return {
        "symbol": symbol,
        "signal_at": decision.astimezone(UTC).isoformat(),
        "anchor": signal.anchor,
        "side": signal.side.value,
        "r_multiple": str(trade["r_multiple"]),
        "closure_kind": closure_kind,
        "bias_family": _bias_family(previous_day, current_day),
        "protected_swing_count": len(swings),
        "selected_opposing_series_bars": max(0, elapsed - 1),
        "previous_source_day_body_aligned": _body_aligned(previous_day, signal.side),
        "current_source_day_body_aligned": _body_aligned(current_day, signal.side),
        "risk_fraction": str(geometry["risk_fraction"]),
        "closure_reference_range_ratio": str(
            geometry["closure_reference_range_ratio"]
        ),
    }


def _feature_rows(
    report: dict[str, object],
    *,
    paths: dict[str, Path],
    expected_sha: str,
    minimum_days: int,
) -> list[dict[str, object]]:
    raw = report.get("trades")
    if not isinstance(raw, list):
        raise Vt08IndexV4ForensicsError("V3 report trades are malformed")
    indexed = {
        symbol: _load_indexed(
            paths[symbol],
            symbol=symbol,
            expected_sha=expected_sha,
            minimum_days=minimum_days,
        )
        for symbol in AUTHORIZED_MARKETS
    }
    rows: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise Vt08IndexV4ForensicsError("V3 trade payload is malformed")
        symbol = str(item["symbol"])
        rows.append(_feature_row(item, indexed=indexed[symbol]))
    return rows


def _replay(
    *,
    paths: dict[str, Path],
    start: date,
    end_exclusive: date,
    expected_sha: str,
    minimum_days: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    report = build_v3_candidate_report(
        nas100=paths["NAS100"],
        sp500=paths["SP500"],
        us30=paths["US30"],
        start_date=start,
        end_date_exclusive=end_exclusive,
        expected_software_sha=expected_sha,
        minimum_evidence_days=minimum_days,
    )
    rows = _feature_rows(
        report,
        paths=paths,
        expected_sha=expected_sha,
        minimum_days=minimum_days,
    )
    return report, rows


def _condition_report(
    rows: list[dict[str, object]],
    *,
    predicate: Callable[[dict[str, object]], bool],
) -> dict[str, Any]:
    retained = [row for row in rows if predicate(row)]
    markets = {
        market: _metrics([row for row in retained if row["symbol"] == market])
        for market in AUTHORIZED_MARKETS
    }
    sides = {
        side: _metrics([row for row in retained if row["side"] == side])
        for side in ("long", "short")
    }
    return {"metrics": _metrics(retained), "by_market": markets, "by_side": sides}


def _load_json(path: Path) -> dict[str, object]:
    decoded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise Vt08IndexV4ForensicsError("expected JSON object")
    return decoded


def build_report(
    *,
    v3_decision_root: Path,
    v2_decision_root: Path,
    development_paths: dict[str, Path],
) -> dict[str, object]:
    v3_paths = {
        symbol: v3_decision_root / "truncated" / f"{symbol}.json"
        for symbol in AUTHORIZED_MARKETS
    }
    v2_paths = {
        symbol: v2_decision_root / "truncated" / f"{symbol}.json"
        for symbol in AUTHORIZED_MARKETS
    }
    official_v3 = _load_json(v3_decision_root / "candidate-full.json")
    replay_22, rows_22 = _replay(
        paths=v3_paths,
        start=date(2022, 9, 15),
        end_exclusive=date(2023, 9, 15),
        expected_sha=V3_FRESH_SHA,
        minimum_days=350,
    )
    if replay_22["candidate_id"] != V3_CANDIDATE_ID:
        raise Vt08IndexV4ForensicsError("V3 candidate identity drifted")
    if replay_22["rule_fingerprint"] != V3_RULE_FINGERPRINT:
        raise Vt08IndexV4ForensicsError("V3 fingerprint drifted")
    if replay_22["trades"] != official_v3.get("trades"):
        raise Vt08IndexV4ForensicsError("official V3 fresh replay is not reproducible")

    replay_23, rows_23 = _replay(
        paths=v2_paths,
        start=date(2023, 9, 15),
        end_exclusive=date(2024, 8, 13),
        expected_sha=V2_FRESH_SHA,
        minimum_days=300,
    )
    replay_24, rows_24 = _replay(
        paths=development_paths,
        start=date(2024, 8, 13),
        end_exclusive=date(2026, 9, 12),
        expected_sha=DEVELOPMENT_SHA,
        minimum_days=700,
    )
    windows = {
        "2022_23": rows_22,
        "2023_24": rows_23,
        "2024_26": rows_24,
    }
    conditions: dict[str, Callable[[dict[str, object]], bool]] = {
        "protected_swing_count_eq_2": (
            lambda row: row["protected_swing_count"] == 2
        ),
        "previous_source_day_body_opposed": (
            lambda row: row["previous_source_day_body_aligned"] is False
        ),
        "swing_count_eq_2_and_bias_reversal": (
            lambda row: row["protected_swing_count"] == 2
            and row["bias_family"] == "reversal"
        ),
    }
    condition_reports = {
        name: {
            window: _condition_report(rows, predicate=predicate)
            for window, rows in windows.items()
        }
        for name, predicate in conditions.items()
    }
    swing_dev = _decimal(
        condition_reports["protected_swing_count_eq_2"]["2024_26"]["metrics"]["mean_r"]
    )
    opposed = condition_reports["previous_source_day_body_opposed"]
    opposed_means = [_decimal(opposed[name]["metrics"]["mean_r"]) for name in windows]
    opposed_stress = [
        _decimal(opposed[name]["metrics"]["stressed_mean_r"]) for name in windows
    ]
    findings = {
        "official_v3_fresh_reproduction": "pass",
        "protected_swing_count_eq_2": (
            "falsified_as_standalone_three_window_rule"
            if swing_dev <= 0
            else "survives_three_window_aggregate_screen"
        ),
        "previous_source_day_body_opposed": (
            "survives_three_window_aggregate_screen_only"
            if all(value > 0 for value in opposed_means)
            and all(value > 0 for value in opposed_stress)
            else "fails_three_window_aggregate_screen"
        ),
        "candidate_freeze_recommended": False,
    }
    return {
        "schema": SCHEMA,
        "research_id": RESEARCH_ID,
        "v3_candidate_id": V3_CANDIDATE_ID,
        "v3_rule_fingerprint": V3_RULE_FINGERPRINT,
        "windows": {
            "2022_23": replay_22["metrics"],
            "2023_24": replay_23["metrics"],
            "2024_26": replay_24["metrics"],
        },
        "condition_reports": condition_reports,
        "findings": findings,
        "governance": {
            "consumed_evidence_only": True,
            "v4_candidate_frozen": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3-decision-root", type=Path, required=True)
    parser.add_argument("--v2-decision-root", type=Path, required=True)
    parser.add_argument("--development-nas100", type=Path, required=True)
    parser.add_argument("--development-sp500", type=Path, required=True)
    parser.add_argument("--development-us30", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        v3_decision_root=args.v3_decision_root,
        v2_decision_root=args.v2_decision_root,
        development_paths={
            "NAS100": args.development_nas100,
            "SP500": args.development_sp500,
            "US30": args.development_us30,
        },
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["findings"], sort_keys=True))


if __name__ == "__main__":
    main()
