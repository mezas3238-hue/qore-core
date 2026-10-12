"""G2 availability test: W3 original 33 event times versus sparse signed 29 quotes.

This checks ONLY timestamp intersection. No quote prices, outcomes, PnL,
future 2026 tick data, source-side execution assertions, or broker calls.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_native_market33_source_census_v1 import (
    FAMILIES,
)
from qore.research.alpha2_g2_29_real_bidask_reuse import (
    ID as QUOTE_SOURCE_ID,
    SOURCE_29,
    WINDOWS,
)
from qore.research.alpha2_intermarket import MARKETS, sha256_file
from qore.research.alpha2_w3_cmtrl_native_m5 import (
    IDENTITY as W3_SOURCE_ID,
    SOURCE33_SHA,
)

W3_HEAD = "e7ec0e4d1cfb8b80effb9e2c1eea23524d6e716c"
SOURCE29_HEAD = "bffb5e8ff5bb9ce12e515bb2558d12001472d9a3"
IDENTITY = "QORE_ALPHA2_G2_W3_33_MARKET_REAL_QUOTE_WINDOW_COVERAGE_SOURCE_ONLY"
EXPECTED_SIGNALS = 24487
EXPECTED_PAIRED = 24399
EMBARGO = datetime(2024, 9, 17, tzinfo=UTC)
FIXED_WINDOWS = tuple(
    (datetime.fromisoformat(left), datetime.fromisoformat(right))
    for left, right in WINDOWS[:2]
)


def _date(value: Any) -> datetime:
    if type(value) is not str:
        raise ValueError("original event timestamp missing")
    at = datetime.fromisoformat(value)
    if at.tzinfo is None or at.utcoffset() != UTC.utcoffset(at):
        raise ValueError("original event not exact UTC")
    return at


def in_same_quote_window(
    entry: datetime, exit_at: datetime | None, *, has_source: bool,
) -> tuple[bool, bool]:
    """Entry overlap and completed path overlap only; never stitch windows."""
    if not has_source:
        return False, False
    for begin, end in FIXED_WINDOWS:
        if begin <= entry < end:
            return True, bool(exit_at is not None and entry <= exit_at < end)
    return False, False


def inspect_events(
    symbol: str, events: list[dict[str, Any]], *,
    has_source: bool,
) -> dict:
    count = Counter()
    era_totals: dict[str, Counter[str]] = {
        "DEVELOPMENT": Counter(),
        "DIAGNOSTIC": Counter(),
    }
    seen_days: set[str] = set()
    for event in events:
        if event.get("symbol") != symbol or event.get("era") not in era_totals:
            raise ValueError("worker symbol/era provenance mismatch")
        day = event.get("utc_day")
        if type(day) is not str or day in seen_days:
            raise ValueError("worker original day duplicate/missing")
        seen_days.add(day)
        plan = event.get("plan")
        if not isinstance(plan, dict):
            raise ValueError("worker plan not original causal decision")
        entry = _date(plan["entry_utc"])
        deadline = _date(plan["exit_deadline_utc"])
        decision = _date(plan["decision_utc"])
        if (not decision < entry < deadline
                or deadline > EMBARGO or day != decision.date().isoformat()):
            raise ValueError("event chronology or reserved holdout violation")
        paired = event.get("paired")
        if type(paired) is not bool:
            raise ValueError("missing original pair status")
        strategy = event.get("strategy")
        control = event.get("control")
        if not isinstance(strategy, dict) or not isinstance(control, dict):
            raise ValueError("frozen W3 original arm metadata missing")
        entry_in, _ = in_same_quote_window(entry, None, has_source=has_source)
        arm_ok = []
        for arm in (strategy, control):
            if arm.get("status") == "COMPLETE_GROSS_PROXY":
                at = _date(arm["exit_utc"])
                if not entry <= at <= deadline:
                    raise ValueError("W3 original completed exit beyond causal horizon")
                _, covered = in_same_quote_window(entry, at, has_source=has_source)
                arm_ok.append(covered)
            else:
                arm_ok.append(False)
        if paired != (
            strategy.get("status") == control.get("status") == "COMPLETE_GROSS_PROXY"
        ):
            raise ValueError("original paired status drift")
        update = {
            "original_signals": 1,
            "original_paired": int(paired),
            "entry_in_quote_window": int(entry_in),
            "strategy_entry_and_exit_same_window": int(arm_ok[0]),
            "control_entry_and_exit_same_window": int(arm_ok[1]),
            "both_arms_entry_and_exit_same_window": int(all(arm_ok)),
        }
        count.update(update)
        era_totals[event["era"]].update(update)
    return {
        "symbol":symbol,
        "quote_source_in_29":has_source,
        "data_source_classification":(
            "29_DEMO_QUOTE_SOURCE_ORIGINAL_WINDOWS"
            if has_source else "OUTSIDE_29_SOURCE_SCOPE"
        ),
        "counts":dict(count),
        "by_era":{era:dict(vals) for era, vals in era_totals.items()},
        "executable_broker_net_paths":0,
    }


def _worker_records(root: Path) -> dict[str, list[dict[str, Any]]]:
    rows = sorted(root.rglob("alpha2-w3-cmtrl-gross-*.json"))
    if len(rows) != 33:
        raise ValueError("all 33 original W3 market workers required")
    records = {}
    for file in rows:
        name=file.name
        sha_line=(file.parent/(name+".sha256")).read_text(encoding="utf-8").strip()
        if sha_line != f"{sha256_file(file)}  {name}":
            raise ValueError("signed W3 worker SHA mismatch")
        if (file.parent/"exact-code-head-sha.txt").read_text(
            encoding="utf-8"
        ).strip()!=W3_HEAD:
            raise ValueError("W3 worker code-head not original")
        doc=json.loads(file.read_text(encoding="utf-8"))
        sym=doc.get("symbol")
        if (sym not in MARKETS or sym in records or
                doc.get("identity")!=W3_SOURCE_ID or
                doc.get("source_33_manifest_sha256")!=SOURCE33_SHA or
                doc.get("full_native_source_SHA_verified_before_OHLC") is not True or
                doc.get("after_2024_09_17_price_unread") is not True or
                doc.get("UTC001_certified") is not False or
                doc.get("broker_costs_verified") is not False or
                doc.get("original_signal_count")!=len(doc.get("opportunities",[]))):
            raise ValueError("frozen W3 worker source identity invalid")
        records[sym]=doc["opportunities"]
    if set(records)!=set(MARKETS):
        raise ValueError("frozen 33 market universe incomplete")
    return records


def _quote_index(root: Path) -> dict:
    filename="alpha2-g2-real29-two-past-windows-source-index.json"
    target=root/filename
    sha_witness=root/"OUTPUT_SHA256SUMS.txt"
    expected={}
    for line in sha_witness.read_text(encoding="utf-8").splitlines():
        parts=line.split()
        if len(parts)!=2 or parts[1] in expected:
            raise ValueError("original Alpha2 source29 checksum format invalid")
        expected[parts[1]]=parts[0]
    if set(expected)!={filename,"exact-code-head-sha.txt"}:
        raise ValueError("source29 original signed file set changed")
    for path, sha in expected.items():
        if sha256_file(root/path)!=sha:
            raise ValueError("source29 original checksum mismatch")
    if (root/"exact-code-head-sha.txt").read_text(
        encoding="utf-8"
    ).strip()!=SOURCE29_HEAD:
        raise ValueError("source29 verified exact HEAD mismatch")
    d=json.loads(target.read_text(encoding="utf-8"))
    if (d.get("identity")!=QUOTE_SOURCE_ID or
            d.get("status")!="SOURCE29_TWO_PAST_WINDOWS_SHA_VERIFIED_NOT_NET" or
            d.get("market_count")!=29 or
            set(d.get("all_29",{}))!=SOURCE_29 or
            d.get("holdout_2026_quote_values_unread") is not True or
            d.get("net_costs_history_complete") is not False):
        raise ValueError("source29 already attested quote index drift")
    return d


def audit_coverage(worker33: Path, source29: Path) -> dict:
    frozen_quotes=_quote_index(source29)
    worker=_worker_records(worker33)
    per_market={}
    combined=Counter()
    family={}
    for group,members in FAMILIES.items():
        family[group]=Counter()
        for symbol in sorted(members):
            item=inspect_events(
                symbol,worker[symbol],has_source=symbol in SOURCE_29,
            )
            per_market[symbol]=item
            combined.update(item["counts"])
            family[group].update(item["counts"])
    if (set(per_market)!=set(MARKETS) or
            combined["original_signals"]!=EXPECTED_SIGNALS or
            combined["original_paired"]!=EXPECTED_PAIRED):
        raise ValueError("W3 exact fixed original economic event count changed")
    for name in (
        "strategy_entry_and_exit_same_window",
        "control_entry_and_exit_same_window",
        "both_arms_entry_and_exit_same_window",
    ):
        if combined[name]>combined["entry_in_quote_window"]:
            raise ValueError("source quote window coverage impossible")
    return {
        "identity":IDENTITY, "status":"W3_EVENT_TIME_WINDOW_COVERAGE_ONLY_NOT_NET",
        "original_w3_code_head":W3_HEAD,
        "original_29_quote_source_code_head":SOURCE29_HEAD,
        "source29_index_sha256":frozen_quotes["source_root_sha256"],
        "markets_total":33,
        "markets_with_two_short_quote_windows":29,
        "markets_outside_current_quote_source":sorted(set(MARKETS)-SOURCE_29),
        "fixed_windows":WINDOWS[:2],
        "global":dict(combined),
        "by_family":{n:dict(c) for n,c in family.items()},
        "per_market_all33":per_market,
        "source_tick_price_values_read":False,
        "2026_tick_price_values_unread":True,
        "gross_outcomes_recalculated":False,
        "trade_or_capital_executed":False,
        "full_entry_exit_quote_coverage_verified":False,
        "historical_quote_receipt_time_verified":False,
        "cost_contract_and_macro_PIT_verified":False,
        "executable_net_paths_certified":0,
        "UTC001_certified":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("original_w3_worker33",type=Path)
    p.add_argument("original_29_quote_source_index",type=Path)
    p.add_argument("out",type=Path)
    args=p.parse_args()
    d=audit_coverage(args.original_w3_worker33,args.original_29_quote_source_index)
    args.out.mkdir(parents=True,exist_ok=True)
    target=args.out/"alpha2-g2-w3-33-original-event-source-window-coverage.json"
    target.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "markets":33,
        "signals":d["global"]["original_signals"],
        "paired":d["global"]["original_paired"],
        "entry_in_two_source_windows":d["global"]["entry_in_quote_window"],
        "both_arms_complete_in_same_window":d["global"][
            "both_arms_entry_and_exit_same_window"],
        "executable_net_paths_certified":0,
    },sort_keys=True))


if __name__=="__main__":
    main()
