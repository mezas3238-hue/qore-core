"""R2-CH archived R2-F source novelty cross-census; no PnL, rule or sizing.

Frozen prior to results:
docs/research/VT08-CRT-PURE-R2CH-ARCHIVED-SOURCE-NOVELTY-CENSUS-FREEZE-001.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_crt_pure_r2ce_wait_cohort_alignment as r2ce

IDENTITY = "VT08_CRT_PURE_R2CH_ARCHIVED_SOURCE_NOVELTY_CENSUS_001"
R2F_IDENTITY = "VT08_CRT_PURE_R2F_MODEL1_HYPOTHESIS_IDENTITY_LEDGER_001"
BEGIN = datetime(2024, 9, 21, tzinfo=UTC)
END = datetime(2026, 9, 21, tzinfo=UTC)
CONFIRMED_SLOT = "CONFIRMED_ENTRY_SLOT_AVAILABLE"
SOURCE_RUN = 35811162435
ALLOWED_MARKETS = ("AUDUSD", "USDJPY")


def _key(market: str, parent_c3: str, source: str) -> tuple[str, str, str]:
    # Timestamps remain timezone-aware; UTC-normalized for source format differences.
    c3_time, source_time = datetime.fromisoformat(parent_c3), datetime.fromisoformat(source)
    if c3_time.tzinfo is None or source_time.tzinfo is None:
        raise ValueError("Source identity timestamps must be timezone-aware")
    return (
        market,
        c3_time.astimezone(UTC).isoformat(),
        source_time.astimezone(UTC).isoformat(),
    )


def _read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            item: Any = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"Non-object JSONL record at line {line_no}")
            rows.append(item)
    if not rows:
        raise ValueError("Empty immutable source ledger")
    return tuple(rows)


def _check_original_r2f(
    market: str,
    rows: tuple[dict[str, Any], ...],
    report: dict[str, Any],
) -> None:
    if report["identity"] != R2F_IDENTITY or report["market"] != market:
        raise ValueError("Wrong original R2-F research identity/market")
    if len(rows) != int(report["ledger_rows"]):
        raise ValueError("Original R2-F JSONL length vs report mismatch")
    if len({row["source_event_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate original source_event_id")
    if len({row["hypothesis_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate original hypothesis_id")
    later = sum(int(row["event_generation"] > 1) for row in rows)
    confirmed = sum(row["state_at_c3_close"] == CONFIRMED_SLOT for row in rows)
    original = report["full_2y"]
    if (
        len(rows) != original["source_event_count"]
        or later != original["later_source_event_count"]
        or confirmed != original["confirmed_entry_slot_event_count"]
    ):
        raise ValueError("Original R2-F event state/count reconciliation failed")
    for row in rows:
        if row["market"] != market:
            raise ValueError("Wrong market in original R2-F source ledger")
        if row.get("grants_entry_authority") is not False:
            raise ValueError("Unexpected old R2-F granted entry authority")
        c3 = datetime.fromisoformat(row["parent_c3_opened_at"])
        if c3.tzinfo is None or c3.astimezone(UTC) < BEGIN or c3.astimezone(UTC) >= END:
            raise ValueError("R2-F record outside the frozen 2-year window")


def _scope_original_keys(
    market: str,
    frozen_ledger: Path,
) -> tuple[dict[tuple[str, str, str], int], dict[str, int]]:
    orig = r2ce._load_frozen_delayed(market, frozen_ledger)
    keys: Counter[tuple[str, str, str]] = Counter()
    all_records = 0
    scoped = 0
    for item in orig:
        all_records += 1
        trade = item.source.trade
        parent = datetime.fromisoformat(trade.c3_opened_at)
        if parent.tzinfo is None:
            raise ValueError("Original control C3 timezone missing")
        if not (BEGIN <= parent.astimezone(UTC) < END):
            continue
        scoped += 1
        keys[_key(market, trade.c3_opened_at, trade.source_opened_at)] += 1
    return dict(keys), {
        "source_original_records_all_history": all_records,
        "source_original_records_scope_2y": scoped,
        "unique_source_structural_keys_scope_2y": len(keys),
        "duplicate_structural_control_keys_scope_2y": sum(
            count - 1 for count in keys.values() if count > 1
        ),
    }


def _classify(
    market: str,
    r2f: tuple[dict[str, Any], ...],
    original_keys: dict[tuple[str, str, str], int],
) -> dict[str, Any]:
    structural_r2f: Counter[tuple[str, str, str]] = Counter(
        _key(market, row["parent_c3_opened_at"], row["source_opened_at"])
        for row in r2f
    )
    counters: Counter[str] = Counter()
    by_generation: dict[str, Counter[str]] = defaultdict(Counter)
    by_calendar_year: dict[str, Counter[str]] = defaultdict(Counter)
    unmatched_parent_ids: set[str] = set()
    matched_parent_ids: set[str] = set()
    ambiguous_parent_ids: set[str] = set()
    unmatched_later_confirmed: set[str] = set()
    for row in r2f:
        key = _key(market, row["parent_c3_opened_at"], row["source_opened_at"])
        parent = key[1]
        generation = int(row["event_generation"])
        if generation < 1:
            raise ValueError("Invalid event generation")
        later = generation > 1
        confirmed = row["state_at_c3_close"] == CONFIRMED_SLOT
        duplicate = structural_r2f[key] > 1 or original_keys.get(key, 0) > 1
        classification = (
            "AMBIGUOUS_KEY" if duplicate else
            "STRUCTURALLY_MATCHED_ORIGINAL" if key in original_keys
            else "STRUCTURALLY_UNMATCHED_ORIGINAL"
        )
        counters[classification] += 1
        if later:
            counters["LATER_EVENT_ALL"] += 1
        if confirmed:
            counters["BODY_CONFIRMED_NEXT_SLOT_ALL"] += 1
        if later and confirmed:
            counters["LATER_CONFIRMED_SLOT_ALL"] += 1
            counters[f"LATER_CONFIRMED_SLOT_{classification}"] += 1
        by_generation[str(generation)][classification] += 1
        by_calendar_year[str(datetime.fromisoformat(parent).year)][classification] += 1
        if classification == "AMBIGUOUS_KEY":
            ambiguous_parent_ids.add(parent)
        elif classification == "STRUCTURALLY_MATCHED_ORIGINAL":
            matched_parent_ids.add(parent)
        else:
            unmatched_parent_ids.add(parent)
            if later and confirmed:
                unmatched_later_confirmed.add(parent)
    if sum(counters[x] for x in (
        "AMBIGUOUS_KEY", "STRUCTURALLY_MATCHED_ORIGINAL",
        "STRUCTURALLY_UNMATCHED_ORIGINAL",
    )) != len(r2f):
        raise ValueError("Unreconciled source key classification")
    return {
        "event_counts": dict(sorted(counters.items())),
        "generation_by_match_status": {
            k: dict(v) for k, v in sorted(by_generation.items())
        },
        "calendar_year_not_annualized": {
            k: dict(v) for k, v in sorted(by_calendar_year.items())
        },
        "parent_c3_with_any_unmatched_source": len(unmatched_parent_ids),
        "parent_c3_with_any_matched_source": len(matched_parent_ids),
        "parent_c3_with_ambiguous_reference_key": len(ambiguous_parent_ids),
        "parent_c3_with_later_confirmed_unmatched_source": len(
            unmatched_later_confirmed
        ),
        "not_a_trade_capacity_or_alpha_estimate": True,
    }


def run_market(
    market: str, *, r2f_ledger: Path, r2f_report: Path, frozen_control: Path
) -> dict[str, Any]:
    if market not in ALLOWED_MARKETS:
        raise ValueError(f"Unsupported market {market}; BTCUSD remains frozen")
    rows = _read_jsonl(r2f_ledger)
    original_report: dict[str, Any] = json.loads(
        r2f_report.read_text(encoding="utf-8")
    )
    _check_original_r2f(market, rows, original_report)
    control_keys, control_diagnostics = _scope_original_keys(market, frozen_control)
    comparison = _classify(market, rows, control_keys)
    return {
        "identity": IDENTITY, "market": market, "r2f_run": SOURCE_RUN,
        "window_start": BEGIN.isoformat(), "window_end_exclusive": END.isoformat(),
        "r2f_original_exact_counts_verified": True,
        "r2f_source_rows": len(rows),
        "r2f_reference_report": original_report["full_2y"],
        "source_input_sha256": {
            "r2f_hypotheses_jsonl": hashlib.sha256(r2f_ledger.read_bytes()).hexdigest(),
            "r2f_report": hashlib.sha256(r2f_report.read_bytes()).hexdigest(),
            "control_delayed_ledger": hashlib.sha256(frozen_control.read_bytes()).hexdigest(),
        },
        "scoped_original_control": control_diagnostics,
        "structural_comparison": comparison,
        "join_semantics": "C3_SOURCE_TIMESTAMP_ONLY_NOT_REFERENCE_IDENTITY",
        "ambiguous_reference_keys_fail_closed": True,
        "independent_source_event_does_not_imply_independent_trade": True,
        "competition_authority": "OPEN",
        "no_cross_period_extrapolation": True,
        "pnl_evaluated": False, "fresh_holdout_used": False,
        "candidate_certified": False, "automatic_promotion": False,
        "research_only": True, "sizing_volume_forbidden": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("--market", choices=ALLOWED_MARKETS, required=True)
    p.add_argument("--r2f-ledger", type=Path, required=True)
    p.add_argument("--r2f-report", type=Path, required=True)
    p.add_argument("--frozen-control", type=Path, required=True)
    args = p.parse_args()
    result = run_market(
        args.market, r2f_ledger=args.r2f_ledger,
        r2f_report=args.r2f_report, frozen_control=args.frozen_control,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("VT08_R2CH_SOURCE_NOVELTY=" + json.dumps({
        key: result[key] for key in (
            "market", "r2f_source_rows", "r2f_original_exact_counts_verified",
            "scoped_original_control", "structural_comparison",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
