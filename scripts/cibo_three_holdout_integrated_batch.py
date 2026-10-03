#!/usr/bin/env python3
"""Assemble one integrated seven-Trader 1Y research batch.

Per-Trader files are source preparation only. This assembler is the boundary
where the seven streams become one chronological portfolio before any CIBO
capital decision is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    REQUIRED_TRADERS,
    expected_windows,
)

TURTLE = {
    "R34_XAUUSD": "XAUUSD",
    "R38_EURUSD": "EURUSD",
    "R43_GBPUSD": "GBPUSD",
    "R38_GBPJPY": "GBPJPY",
    "R42_AUDJPY": "AUDJPY",
}


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _dec(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("decimal must be finite")
    return result


def _window(group_id: str) -> tuple[datetime, datetime]:
    for item in expected_windows():
        if item.group_id == group_id:
            return item.start_at, item.end_exclusive_at
    raise ValueError(group_id)


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _context(row: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in (
        "family",
        "target_route",
        "fragility_flag_count",
        "posture",
        "risk_ref_bucket",
        "entry_family",
        "h1_state",
        "h4_state",
        "confirmation_latency_bucket",
        "reclaim_age_bucket",
    ):
        value = row.get(key)
        if value is not None:
            out[key] = str(value)
    for prefix, field in (("ctx_", "setup_context"), ("reg_", "regime")):
        raw = row.get(field)
        if not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            name = str(key)
            if name.startswith("d1_"):
                continue
            if value is not None:
                out[prefix + name] = str(value)
    return dict(sorted(out.items()))


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _normalize(
    *,
    trader_id: str,
    symbol: str,
    source_sha: str,
    signal_at: datetime,
    entry_at: datetime,
    exit_at: datetime,
    side: str,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
    outcome_r: Decimal,
    exit_reason: str,
    context: dict[str, str],
) -> dict[str, Any]:
    if not signal_at <= entry_at < exit_at:
        raise ValueError(f"{trader_id}: chronology invalid")
    if side not in {"long", "short"}:
        raise ValueError(f"{trader_id}: side invalid")
    if side == "long" and not stop < entry < target:
        raise ValueError(f"{trader_id}: long geometry invalid")
    if side == "short" and not target < entry < stop:
        raise ValueError(f"{trader_id}: short geometry invalid")
    identity = {
        "trader_id": trader_id,
        "qore_symbol": symbol,
        "signal_at": signal_at.isoformat(),
        "entry_at": entry_at.isoformat(),
        "side": side,
        "entry": format(entry, "f"),
        "stop": format(stop, "f"),
        "target": format(target, "f"),
        "source_sha256": source_sha,
    }
    return {
        **identity,
        "signal_fingerprint": _fingerprint(identity),
        "exit_at": exit_at.isoformat(),
        "exit_reason": exit_reason,
        "gross_structural_outcome_r": format(outcome_r, "f"),
        "methodology_sha256": source_sha,
        "source_evidence_ids": [source_sha],
        "decision_context": context,
        "volume": None,
        "legacy_trader_sizing_used_for_cibo": False,
    }


def _turtle_rows(
    trader_id: str,
    symbol: str,
    path: Path,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    source_sha = _sha(path)
    result = []
    for row in _jsonl(path):
        signal_at = _dt(row["signal_at"])
        if not start <= signal_at < end:
            continue
        result.append(
            _normalize(
                trader_id=trader_id,
                symbol=symbol,
                source_sha=source_sha,
                signal_at=signal_at,
                entry_at=_dt(row["entry_at"]),
                exit_at=_dt(row["exit_at"]),
                side=str(row["side"]).lower(),
                entry=_dec(row["entry_price"]),
                stop=_dec(row["structural_stop"]),
                target=_dec(row["technical_target"]),
                outcome_r=_dec(row["raw_net_010_r"]),
                exit_reason=str(row["exit_reason"]),
                context=_context(row),
            )
        )
    return result


def _vt31_rows(path: Path, start: datetime, end: datetime) -> list[dict[str, Any]]:
    source_sha = _sha(path)
    result = []
    for row in _jsonl(path):
        signal_at = _dt(row["signal_at"])
        if not start <= signal_at < end:
            continue
        result.append(
            _normalize(
                trader_id="VT31_NAS100",
                symbol="NAS100",
                source_sha=source_sha,
                signal_at=signal_at,
                entry_at=_dt(row["entry_at"]),
                exit_at=_dt(row["exit_at"]),
                side=str(row["side"]).lower(),
                entry=_dec(row["entry_price"]),
                stop=_dec(row["structural_stop"]),
                target=_dec(row["technical_target"]),
                outcome_r=_dec(row["r_multiple"]),
                exit_reason=str(row["exit_reason"]),
                context=_context(row),
            )
        )
    return result


def _vt08_r(row: dict[str, Any]) -> Decimal:
    side = str(row["side"]).lower()
    entry = _dec(row["entry"])
    stop = _dec(row["stop"])
    exit_price = _dec(row["exit_price"])
    risk = entry - stop if side == "long" else stop - entry
    if risk <= 0:
        raise ValueError("VT08 structural risk invalid")
    pnl = exit_price - entry if side == "long" else entry - exit_price
    return pnl / risk


def _vt08_rows(path: Path, start: datetime, end: datetime) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "qore.cibo.trader-lab.vt08-1y-group-lane.v1":
        raise ValueError("VT08 source lane schema drift")
    source_sha = _sha(path)
    result = []
    for row in payload["trades"]:
        signal_at = _dt(row["signal_at"])
        if not start <= signal_at < end:
            continue
        result.append(
            _normalize(
                trader_id="VT08_FOREX",
                symbol=str(row["symbol"]),
                source_sha=source_sha,
                signal_at=signal_at,
                entry_at=signal_at,
                exit_at=_dt(row["exited_at"]),
                side=str(row["side"]).lower(),
                entry=_dec(row["entry"]),
                stop=_dec(row["stop"]),
                target=_dec(row["target"]),
                outcome_r=_vt08_r(row),
                exit_reason=str(row["exit_reason"]),
                context={"family": "VT08_B01_FROZEN"},
            )
        )
    return result


def _overlap(opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(opportunities, key=lambda row: row["entry_at"])
    cross = 0
    same = 0
    pair_counts: Counter[str] = Counter()
    max_concurrent = 0
    for index, left in enumerate(ordered):
        left_entry = _dt(left["entry_at"])
        left_exit = _dt(left["exit_at"])
        concurrent = 1
        for right in ordered[index + 1 :]:
            right_entry = _dt(right["entry_at"])
            if right_entry >= left_exit:
                break
            right_exit = _dt(right["exit_at"])
            if left_entry < right_exit and right_entry < left_exit:
                concurrent += 1
                if left["trader_id"] == right["trader_id"]:
                    same += 1
                else:
                    cross += 1
                    pair = "|".join(sorted((left["trader_id"], right["trader_id"])))
                    pair_counts[pair] += 1
        max_concurrent = max(max_concurrent, concurrent)

    by_day: dict[str, set[str]] = defaultdict(set)
    for row in opportunities:
        by_day[_dt(row["entry_at"]).date().isoformat()].add(row["trader_id"])
    return {
        "max_concurrent_positions_pre_cibo": max_concurrent,
        "cross_trader_overlap_pairs_pre_cibo": cross,
        "same_trader_overlap_pairs_pre_cibo": same,
        "multi_trader_entry_days": sum(len(value) >= 2 for value in by_day.values()),
        "cross_trader_pair_overlap_counts": dict(sorted(pair_counts.items())),
    }


def assemble(args: argparse.Namespace) -> dict[str, Any]:
    start, end = _window(args.group_id)
    paths = {
        "R34_XAUUSD": args.r34_xauusd,
        "R38_EURUSD": args.r38_eurusd,
        "R43_GBPUSD": args.r43_gbpusd,
        "R38_GBPJPY": args.r38_gbpjpy,
        "R42_AUDJPY": args.r42_audjpy,
    }
    by_trader: dict[str, list[dict[str, Any]]] = {
        trader_id: _turtle_rows(trader_id, TURTLE[trader_id], path, start, end)
        for trader_id, path in paths.items()
    }
    by_trader["VT31_NAS100"] = _vt31_rows(args.vt31, start, end)
    by_trader["VT08_FOREX"] = _vt08_rows(args.vt08, start, end)

    if set(by_trader) != set(REQUIRED_TRADERS):
        raise ValueError("exact seven-Trader surface required")
    empty = sorted(key for key, rows in by_trader.items() if not rows)
    if empty:
        raise ValueError(f"integrated group has empty Trader lanes: {empty}")

    opportunities = sorted(
        (row for rows in by_trader.values() for row in rows),
        key=lambda row: (
            row["signal_at"],
            row["trader_id"],
            row["signal_fingerprint"],
        ),
    )
    fps = [row["signal_fingerprint"] for row in opportunities]
    if len(fps) != len(set(fps)):
        raise ValueError("duplicate integrated signal fingerprint")

    payload = {
        "schema": "qore.cibo.trader-lab.1y-integrated-7trader-batch.v1",
        "group_id": args.group_id,
        "start_at": start.isoformat(),
        "end_exclusive_at": end.isoformat(),
        "execution_topology": "SINGLE_INTEGRATED_7_TRADER_PORTFOLIO",
        "traders": list(REQUIRED_TRADERS),
        "per_trader_results_source_only": True,
        "shared_initial_capital_usd": "60",
        "shared_cibo_state": True,
        "shared_qore_risk_state": True,
        "opportunity_count": len(opportunities),
        "opportunity_count_by_trader": {
            key: len(by_trader[key]) for key in REQUIRED_TRADERS
        },
        "opportunities": opportunities,
        "chronology": _overlap(opportunities),
        "cibo_execution_started": False,
        "ready_for_single_integrated_cibo_replay": True,
        "adaptive_research_only": True,
        "fresh_oos_claimed": False,
        "certification_claimed": False,
        "broker_mutation": False,
        "live": False,
        "production": False,
        "real_capital": False,
    }
    payload["batch_sha256"] = _fingerprint(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group-id", choices=("GROUP_1", "GROUP_2", "GROUP_3"), required=True)
    parser.add_argument("--vt08", type=Path, required=True)
    parser.add_argument("--vt31", type=Path, required=True)
    parser.add_argument("--r34-xauusd", dest="r34_xauusd", type=Path, required=True)
    parser.add_argument("--r38-eurusd", dest="r38_eurusd", type=Path, required=True)
    parser.add_argument("--r43-gbpusd", dest="r43_gbpusd", type=Path, required=True)
    parser.add_argument("--r38-gbpjpy", dest="r38_gbpjpy", type=Path, required=True)
    parser.add_argument("--r42-audjpy", dest="r42_audjpy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = assemble(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "group_id": payload["group_id"],
        "opportunity_count": payload["opportunity_count"],
        "opportunity_count_by_trader": payload["opportunity_count_by_trader"],
        "batch_sha256": payload["batch_sha256"],
        "execution_topology": payload["execution_topology"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
