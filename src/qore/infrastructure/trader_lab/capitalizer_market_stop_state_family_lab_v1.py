"""Exact pre-trade state-family lab for Capitalizer Market Stop Cognition V1.

This lab partitions consumed native-M1 forensic trades by decision-time categorical facts only.
It measures stop/recovery behavior inside those families but does not choose or freeze a buffer.

Family key:
- market/session;
- side;
- source event signature;
- New York entry hour;
- exact validated Order Block candle count;
- immediate retest (delay == 0) vs later retest (delay > 0).

No outcome is used to create the family key. Outcomes are measured only after grouping.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

IDENTITY = "QORE_CAPITALIZER_MARKET_STOP_STATE_FAMILY_LAB_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_STATE_FAMILY_MATRIX_V1"
FORENSIC_IDENTITY = "QORE_CAPITALIZER_M1_LOSS_CAUSAL_FORENSICS_V1"
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class CapitalizerStopStateFamilyObservation:
    state_family_id: str
    symbol: str
    session: str
    side: str
    source_event_signature: str
    ny_entry_hour: int
    order_block_candle_count: int
    retest_phase: str
    trades: int
    stops: int
    losses: int
    target_recovered_after_stop: int
    stop_rate: str
    target_recovery_after_stop_rate: str | None
    median_extra_stop_r_recovered: str | None
    p75_extra_stop_r_recovered: str | None
    p90_extra_stop_r_recovered: str | None
    median_setup_age_minutes: str
    median_retest_delay_minutes: str
    median_planned_reward_r: str
    median_fvg_width_r: str
    median_order_block_width_r: str
    median_distance_ob_to_mss_r: str
    median_entry_adverse_excursion_r: str
    buffer_candidate_frozen: bool = False
    rule_promotion_allowed: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerMarketStopStateFamilyReport:
    identity: str
    symbol: str
    session: str
    source_trade_count: int
    family_count: int
    families: tuple[CapitalizerStopStateFamilyObservation, ...]
    family_key_uses_outcome: bool = False
    exact_state_families_built: bool = True
    buffer_candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False


def _quantile(values: list[Decimal], fraction: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    scaled = Decimal(len(ordered) - 1) * fraction
    index = int(scaled)
    return ordered[index]


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("state-family timestamps must be timezone-aware")
    return parsed


def _decimal(row: dict[str, Any], key: str) -> Decimal:
    value = row.get(key)
    if value is None:
        raise ValueError(f"state-family row missing {key}")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"state-family {key} must be finite")
    return result


def _event_signature(row: dict[str, Any]) -> str:
    labels = row.get("source_event_labels")
    if not isinstance(labels, list) or not labels:
        return "NO_SOURCE_EVENT_LABEL"
    if not all(isinstance(label, str) and label for label in labels):
        raise ValueError("source_event_labels must contain non-empty strings")
    return "+".join(sorted(labels))


def _family_key(row: dict[str, Any]) -> tuple[str, str, str, str, int, int, str]:
    symbol = str(row["symbol"])
    session = str(row["session"])
    side = str(row["side"])
    signature = _event_signature(row)
    ny_hour = _aware(str(row["entry_at"])).astimezone(NEW_YORK).hour
    ob_count = int(row["order_block_candle_count"])
    if ob_count <= 0:
        raise ValueError("accepted M1 trade requires positive Order Block candle count")
    delay = int(row["retest_delay_minutes"])
    if delay < 0:
        raise ValueError("retest delay cannot be negative")
    phase = "IMMEDIATE_RETEST" if delay == 0 else "LATER_RETEST"
    return symbol, session, side, signature, ny_hour, ob_count, phase


def _state_family_id(key: tuple[str, str, str, str, int, int, str]) -> str:
    symbol, session, side, signature, ny_hour, ob_count, phase = key
    return (
        f"{symbol}:{session}:{side}:EVENT={signature}:NYH={ny_hour}:"
        f"OBN={ob_count}:{phase}"
    )


def _metrics(rows: list[dict[str, Any]]) -> CapitalizerStopStateFamilyObservation:
    if not rows:
        raise ValueError("state-family metrics require rows")
    key = _family_key(rows[0])
    if any(_family_key(row) != key for row in rows):
        raise ValueError("state-family rows must share exact pre-trade key")

    stops = [row for row in rows if str(row["exit_reason"]) == "STOP"]
    losses = [row for row in rows if _decimal(row, "realized_gross_r") < 0]
    recovered = [
        row
        for row in stops
        if bool(row.get("target_reached_after_stop_same_session"))
    ]
    extra = [
        _decimal(row, "extra_stop_r_needed_for_same_session_target_recovery")
        for row in recovered
        if row.get("extra_stop_r_needed_for_same_session_target_recovery") is not None
    ]
    symbol, session, side, signature, ny_hour, ob_count, phase = key

    med_extra = None if not extra else median(extra)
    p75 = _quantile(extra, Decimal("0.75"))
    p90 = _quantile(extra, Decimal("0.90"))
    stop_rate = Decimal(len(stops)) / Decimal(len(rows))
    recovery_rate = (
        None
        if not stops
        else Decimal(len(recovered)) / Decimal(len(stops))
    )

    def med(key_name: str) -> str:
        return str(median(_decimal(row, key_name) for row in rows))

    return CapitalizerStopStateFamilyObservation(
        state_family_id=_state_family_id(key),
        symbol=symbol,
        session=session,
        side=side,
        source_event_signature=signature,
        ny_entry_hour=ny_hour,
        order_block_candle_count=ob_count,
        retest_phase=phase,
        trades=len(rows),
        stops=len(stops),
        losses=len(losses),
        target_recovered_after_stop=len(recovered),
        stop_rate=str(stop_rate),
        target_recovery_after_stop_rate=(
            None if recovery_rate is None else str(recovery_rate)
        ),
        median_extra_stop_r_recovered=(
            None if med_extra is None else str(med_extra)
        ),
        p75_extra_stop_r_recovered=None if p75 is None else str(p75),
        p90_extra_stop_r_recovered=None if p90 is None else str(p90),
        median_setup_age_minutes=med("setup_age_minutes"),
        median_retest_delay_minutes=med("retest_delay_minutes"),
        median_planned_reward_r=med("planned_reward_r"),
        median_fvg_width_r=med("fvg_width_r"),
        median_order_block_width_r=med("order_block_width_r"),
        median_distance_ob_to_mss_r=med("distance_ob_to_mss_r"),
        median_entry_adverse_excursion_r=med(
            "entry_adverse_excursion_upper_bound_r"
        ),
    )


def _one_report(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-m1-loss-causal-forensics-v1.json"))
    if len(paths) != 1:
        raise ValueError(f"expected one forensic report, got {len(paths)}")
    raw = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("identity") != FORENSIC_IDENTITY:
        raise ValueError("unexpected forensic report identity")
    return raw


def _one_ledger(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-m1-loss-causal-forensics-v1-ledger.jsonl")
    )
    if len(paths) != 1:
        raise ValueError(f"expected one forensic ledger, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("forensic ledger row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("state-family lab rejects outcome-selected rows")
            rows.append(raw)
    if not rows:
        raise ValueError("state-family lab requires forensic rows")
    return rows


def build_market_report(root: Path) -> CapitalizerMarketStopStateFamilyReport:
    source = _one_report(root)
    rows = _one_ledger(root)
    symbol = str(source["symbol"])
    session = str(source["session"])
    if len(rows) != int(source["source_trade_count"]):
        raise ValueError("forensic report/ledger trade count mismatch")
    if any(str(row["symbol"]) != symbol for row in rows):
        raise ValueError("state-family ledger symbol mismatch")
    if any(str(row["session"]) != session for row in rows):
        raise ValueError("state-family ledger session mismatch")

    grouped: dict[
        tuple[str, str, str, str, int, int, str],
        list[dict[str, Any]],
    ] = defaultdict(list)
    for row in rows:
        grouped[_family_key(row)].append(row)

    families = tuple(
        sorted(
            (_metrics(group) for group in grouped.values()),
            key=lambda item: (-item.trades, item.state_family_id),
        )
    )
    return CapitalizerMarketStopStateFamilyReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session,
        source_trade_count=len(rows),
        family_count=len(families),
        families=families,
    )


def write_market_report(
    report: CapitalizerMarketStopStateFamilyReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-{report.symbol.lower()}-market-stop-state-families-v1.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(
        root.rglob("capitalizer-*-market-stop-state-families-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"state-family matrix requires 9 reports, got {len(paths)}")
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
        raise ValueError("state-family matrix universe mismatch")
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "total_trades": sum(int(report["source_trade_count"]) for report in reports),
        "total_families": sum(int(report["family_count"]) for report in reports),
        "markets": [
            {
                "symbol": report["symbol"],
                "session": report["session"],
                "source_trade_count": report["source_trade_count"],
                "family_count": report["family_count"],
                "largest_families": report["families"][:20],
            }
            for report in sorted(reports, key=lambda item: str(item["symbol"]))
        ],
        "family_key_uses_outcome": False,
        "buffer_candidate_frozen": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-stop-state-family-matrix-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("forensic_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        market_report = build_market_report(args.forensic_root)
        write_market_report(market_report, args.output)
        print(
            json.dumps(
                {
                    "identity": market_report.identity,
                    "symbol": market_report.symbol,
                    "trades": market_report.source_trade_count,
                    "families": market_report.family_count,
                    "buffer_candidate_frozen": (
                        market_report.buffer_candidate_frozen
                    ),
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
