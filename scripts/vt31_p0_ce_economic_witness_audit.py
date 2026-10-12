#!/usr/bin/env python3
"""VT31 P0: executable-economics *identifiability* from frozen source ledger.

Does NOT estimate profit, synthesize fills, modify trades, or use fresh holdout.
An OHLC same-minute path witness is a mathematical counterexample only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SOURCE_EVENTS = 2140
SOURCE_M1 = 1059784
SESSIONS = {"VT31_LONDON": 766, "VT31_NY_AM": 721, "VT31_NY_PM": 653}
STOP_FIELDS = (
    "stop_loss_price", "initial_stop_price", "protected_stop_price",
    "attached_stop_loss", "source_stop_price", "m1_stop_loss",
)
EXIT_FIELDS = (
    "exit_policy_id", "exit_decision_at", "position_exit_at",
    "exit_execution_ack", "exit_broker_execution_id", "closed_trade_pnl",
)
FILL_FIELDS = ("broker_execution_ack", "entry_broker_execution_id", "fill_ack")
FEE_FIELDS = ("commission", "swap", "slippage", "broker_fee", "fee_currency")
NY = ZoneInfo("America/New_York")


def _dt(text: str) -> datetime:
    at = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return at.astimezone(UTC)


def _positive(value: object) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as err:
        raise ValueError("invalid finite positive price") from err
    if not d.is_finite() or d <= 0:
        raise ValueError("invalid finite positive price")
    return d


def _populated(record: dict[str, object], fields: tuple[str, ...]) -> bool:
    # A field's mere presence does not authenticate provenance. This is
    # necessary but NEVER sufficient for a real economic claim.
    return any(record.get(field) is not None for field in fields)


def audit(ledger: dict[str, Any], *, sha256: str) -> dict[str, Any]:
    if len(sha256) != 64 or any(x not in "0123456789abcdef" for x in sha256):
        raise ValueError("real 64-char sha256 required")
    if ledger.get("trader_id") != "VT31" or ledger.get("market_m1_count") != SOURCE_M1:
        raise ValueError("wrong frozen source identity or M1 count")
    if (ledger.get("source_fvg_hypothesis_count") != SOURCE_EVENTS or
            ledger.get("candidate_count_by_window") != SESSIONS):
        raise ValueError("2,140 original candidate IDs and sessions required")
    if ledger.get("broker_execution_ack_count") != 0 or (
        ledger.get("live_fills_proven") != 0 or ledger.get("paper_fills_proven") != 0
    ):
        raise ValueError("source ledger must contain zero authenticated executions")
    rows = ledger.get("events")
    if not isinstance(rows, list) or len(rows) != SOURCE_EVENTS:
        raise ValueError("frozen source ledger events missing")
    seen: set[str] = set()
    sess_counts: Counter[str] = Counter()
    geometry = 0
    populated = Counter()
    event_fields: set[str] = set()
    terminal = Counter()
    with_revocation = 0
    reported_m1_touch = 0
    same_close_revocation_overlap = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("source event is not an object")
        event_fields.update(row)
        client_id = row.get("client_order_id")
        if not isinstance(client_id, str) or not client_id or client_id in seen:
            raise ValueError("missing/duplicate source client ID")
        seen.add(client_id)
        sess = row.get("session_window")
        if sess not in SESSIONS or row.get("trader_id") != "VT31":
            raise ValueError("unknown session/trader")
        sess_counts[sess] += 1
        formed, first = _dt(row["formed_at"]), _dt(row["source_first_m1_open"])
        if formed - first != timedelta(minutes=3):
            raise ValueError("inconsistent 3-closed-M1 FVG source geometry")
        ny = formed.astimezone(NY)
        if ny.hour != {"VT31_LONDON":3,"VT31_NY_AM":10,"VT31_NY_PM":14}[sess]:
            raise ValueError("candidate formed outside original source hour")
        if not 0 < ny.minute <= 59:
            raise ValueError("source must have formed before hour boundary")
        ce, target = _positive(row["m1_ce_research_limit"]), _positive(row["draw_target"])
        side = row["side"]
        if (side == "LONG" and target <= ce) or (
            side == "SHORT" and target >= ce
        ):
            raise ValueError("target must lie in direction of CE position")
        if side not in ("LONG", "SHORT"):
            raise ValueError("unknown direction")
        geometry += 1
        for label, fields in (
            ("explicit_stop", STOP_FIELDS),
            ("complete_exit_policy_or_ack", EXIT_FIELDS),
            ("authenticated_entry_ack", FILL_FIELDS),
            ("broker_fees", FEE_FIELDS),
        ):
            if _populated(row, fields):
                populated[label] += 1
        if row.get("broker_execution_ack") is not None or row.get("paper_fill_count") != 0 or (
            row.get("live_fill_count") != 0 or row.get("actual_broker_order_submitted") is not False
        ):
            raise ValueError("source research ledger should not contain fills or orders")
        terminal[str(row.get("final_source_phase"))] += 1
        with_revocation += row.get("cognition_lost_or_source_invalidated_at") is not None
        reported_m1_touch += row.get("m1_touch_observed_at_not_fill") is not None
        same_close_revocation_overlap += row.get(
            "m1_ce_overlap_same_m1_as_source_revocation"
        ) is not None
    if dict(sess_counts) != SESSIONS:
        raise ValueError("session denominator drift")
    return {
        "schema": "qore.vt31.p0.ce_economic_evidence_completeness.v1",
        "source_ledger_sha256": sha256,
        "source_ledger_artifact_id": 11657461650,
        "trader_id": "VT31",
        "historical_3y_m1_count_reported_not_rehashed": SOURCE_M1,
        "source_candidates": len(rows),
        "session_source_candidates": dict(sorted(sess_counts.items())),
        "valid_directional_ce_target_geometry": geometry,
        "source_m1_price_touch_not_fill": reported_m1_touch,
        "same_close_ce_and_revocation_unknown": same_close_revocation_overlap,
        "source_cognitive_revocation_timestamps_populated": with_revocation,
        "source_final_states": dict(sorted(terminal.items())),
        "field_presence_is_not_provenance": True,
        "explicit_stop_price_present": populated["explicit_stop"],
        "explicit_stop_price_missing": len(rows) - populated["explicit_stop"],
        "exit_policy_or_exit_ack_present": populated["complete_exit_policy_or_ack"],
        "exit_policy_or_exit_ack_missing": len(rows)-populated["complete_exit_policy_or_ack"],
        "entry_execution_ack_present": populated["authenticated_entry_ack"],
        "broker_fees_present": populated["broker_fees"],
        "source_event_fields": sorted(event_fields),
        "global_source_broker_ack_count": ledger["broker_execution_ack_count"],
        "real_historical_quote_ticks_provided": False,
        "source_symbol_NAS100_matches_user_NDX100_verified": False,
        "can_calculate_true_net_profit_factor": False,
        "can_calculate_true_net_expectancy": False,
        "can_calculate_true_position_drawdown": False,
        "economic_gate": "BLOCKED_SOURCE_ORDER_STOP_EXIT_QUOTES_ACK_FEES",
        "sealed_fresh_holdout_preserved": True,
        "does_not_infer_broker_fills": True,
        "production_changes": False,
    }


def synthetic_ohlc_path_witness() -> dict[str, Any]:
    """Construct same OHLC and constant spread but opposite theoretical exits.

    **NOT** actual VT31 source events or proven broker trades. This proves
    OHLC+spread alone cannot distinguish intraminute ordering after CE.
    """
    spread = Decimal("1.60")
    half = spread/2
    ce, stop, target = Decimal("100"), Decimal("98"), Decimal("103")
    sequences = {
        "target_after_CE": ("102", "99", "106", "96", "101"),
        "stop_after_CE": ("102", "106", "99", "96", "101"),
    }

    def theoretical_path(prices: tuple[str, ...]) -> str:
        entered = False
        for price_text in prices:
            mid = Decimal(price_text)
            ask, bid = mid + half, mid - half
            if not entered:
                if ask <= ce:
                    entered = True
                continue  # cannot exit on the same synthetic observation
            if bid >= target:
                return "TARGET_REACHABLE_AFTER_CE_SYNTHETIC"
            if bid <= stop:
                return "STOP_REACHABLE_AFTER_CE_SYNTHETIC"
        return "UNRESOLVED_SYNTHETIC"

    checked = {k: theoretical_path(v) for k,v in sequences.items()}
    assert checked["target_after_CE"] == "TARGET_REACHABLE_AFTER_CE_SYNTHETIC"
    assert checked["stop_after_CE"] == "STOP_REACHABLE_AFTER_CE_SYNTHETIC"
    candles = {
        k: (v[0], str(max(map(Decimal, v))), str(min(map(Decimal, v))), v[-1])
        for k,v in sequences.items()
    }
    if len(set(candles.values())) != 1:
        raise AssertionError("two paths must have IDENTICAL OHLC")
    return {
        "case": "SYNTHETIC_MATHEMATICAL_WITNESS_NOT_MARKET_OR_BROKER",
        "side": "LONG",
        "CE_limit": str(ce), "stop_hypothetical": str(stop),
        "target_hypothetical": str(target), "constant_spread": str(spread),
        "identical_mid_OHLC": next(iter(candles.values())),
        "intraminute_mid_sequences": sequences,
        "alternative_theoretical_path_outcomes": checked,
        "broker_orders_placed": 0,
        "broker_fills_proven": 0,
        "real_VT31_trades": 0,
        "not_an_empirical_strategy_result": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    witness = synthetic_ohlc_path_witness()
    if args.self_test:
        print(json.dumps(witness, sort_keys=True))
        return
    if args.ledger is None or args.output is None:
        parser.error("--ledger and --output required")
    raw = args.ledger.read_bytes()
    report = audit(json.loads(raw), sha256=hashlib.sha256(raw).hexdigest())
    report["intraminute_identifiability_counterexample"] = witness
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in (
        "source_event_fields", "source_final_states",
        "intraminute_identifiability_counterexample",
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
