"""R2-CI R2F-to-R2G exact-source identity; prevents double-counting already-tested ideas.

Research only. docs/research/VT08-CRT-PURE-R2CI-THREE-LEDGER-IDENTITY-FREEZE-001.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_crt_pure_r2ch_archived_source_novelty as r2ch

IDENTITY = "VT08_CRT_PURE_R2CI_THREE_LEDGER_SOURCE_EQUIVALENCE_001"
R2G_IDENTITY = "VT08_CRT_PURE_R2G_MODEL1_COMPETITION_FAMILY_001"
CURRENT_NEWEST = "NEWEST_SUPERSEDES_CONFIRMATION_FIRST"
R2CH_EXPECTED = {"AUDUSD": 43, "USDJPY": 32}
R2F_RUN, R2G_RUN = 35811162435, 35811391351


def _exact(
    market: str, parent_c3: str, source: str, refs: list[str] | tuple[str, ...]
) -> tuple[str, str, str, tuple[str, ...]]:
    if len(set(refs)) != len(refs):
        raise ValueError("Duplicate reference IDs in source event")
    return (*r2ch._key(market, parent_c3, source), tuple(sorted(refs)))


def _verify_r2g(
    market: str, rows: tuple[dict[str, Any], ...], report: dict[str, Any]
) -> None:
    if report["market"] != market or report["identity"] != R2G_IDENTITY:
        raise ValueError("Wrong frozen R2-G identity or market")
    if report["one_trade_attempt_max_per_parent"] is not True:
        raise ValueError("R2-G original did not bound same-parent competition")
    if CURRENT_NEWEST not in report["policy_family"]:
        raise ValueError("No current NEWEST hypothesis policy in original R2-G")
    by_policy: Counter[str] = Counter()
    unique_parent_policy: set[tuple[str, str]] = set()
    for row in rows:
        policy = row["competition_policy"]
        if row["market"] != market or policy not in report["policy_family"]:
            raise ValueError("Wrong R2-G trade market/competition policy")
        c3 = datetime.fromisoformat(row["c3_opened_at"])
        if c3.tzinfo is None or not r2ch.BEGIN <= c3 < r2ch.END:
            raise ValueError("R2-G selected trade outside original frozen 2Y")
        key = (policy, r2ch._key(market, row["c3_opened_at"], row["source_opened_at"])[1])
        if key in unique_parent_policy:
            raise ValueError("R2-G more than one selected trade per parent/policy")
        unique_parent_policy.add(key)
        by_policy[policy] += 1
    for policy in report["policy_family"]:
        if by_policy[policy] != report["policies"][policy]["full_2y"]["trades"]:
            raise ValueError(f"Frozen R2-G policy {policy} trade-count drift")


def _reconcile_three(
    market: str,
    r2f: tuple[dict[str, Any], ...],
    r2g: tuple[dict[str, Any], ...],
    originals: dict[tuple[str, str, str], int],
) -> dict[str, Any]:
    r2f_ids: dict[tuple[str, str, str, tuple[str, ...]], dict[str, Any]] = {}
    structural_ids: set[tuple[str, str, str]] = set()
    for row in r2f:
        key = _exact(
            market, row["parent_c3_opened_at"], row["source_opened_at"],
            tuple(row["source_reference_ids"]),
        )
        if key in r2f_ids:
            raise ValueError("Ambiguous duplicate R2-F exact source identity")
        r2f_ids[key] = row
        structural_ids.add(key[:3])

    selected_by: dict[tuple[str, str, str, tuple[str, ...]], set[str]] = defaultdict(set)
    selected_structural: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    missing_r2g: Counter[str] = Counter()
    for row in r2g:
        key = _exact(
            market, row["c3_opened_at"], row["source_opened_at"],
            tuple(row["reference_ids"]),
        )
        policy = row["competition_policy"]
        selected_structural[key[:3]].add(policy)
        if key not in r2f_ids:
            if key[:3] in structural_ids:
                missing_r2g["STRUCTURAL_MATCH_REFERENCE_ID_DIFFERENCE"] += 1
            else:
                missing_r2g["NO_R2F_STRUCTURAL_MATCH"] += 1
            continue
        selected_by[key].add(policy)

    selected_counts: Counter[str] = Counter()
    selected_newest_later: Counter[str] = Counter()
    all_later_unmatched = 0
    selected_parents: dict[str, set[str]] = defaultdict(set)
    for key, row in r2f_ids.items():
        if (
            int(row["event_generation"]) <= 1
            or row["state_at_c3_close"] != r2ch.CONFIRMED_SLOT
            or key[:3] in originals
        ):
            continue
        all_later_unmatched += 1
        chosen = selected_by.get(key, set())
        if CURRENT_NEWEST in chosen:
            status = "ALREADY_EVALUATED_NEWEST"
        elif chosen:
            status = "EVALUATED_OTHER_R2G_POLICY_ONLY"
        elif key[:3] in selected_structural:
            status = "PARTIAL_R2G_REFERENCE_ID_MISMATCH"
        else:
            status = "NOT_SELECTED_IN_ARCHIVED_R2G_POLICIES"
        selected_counts[status] += 1
        selected_parents[status].add(key[1])
        selected_newest_later[str(row["event_generation"]) + ":" + status] += 1
    # Strict R2-CH reproduction requires no ambiguous timestamp-only join.
    if all_later_unmatched != R2CH_EXPECTED[market]:
        raise ValueError(
            f"{market}: strict R2-CH novelty frontier changed: "
            f"{all_later_unmatched} != {R2CH_EXPECTED[market]}"
        )
    if sum(selected_counts.values()) != all_later_unmatched:
        raise ValueError("R2-CI category partition failed")
    return {
        "r2ch_structurally_unmatched_later_confirmed_reproduced": all_later_unmatched,
        "R2G_selection_overlap_classification": dict(selected_counts),
        "parents_by_selection_class": {
            k: len(v) for k, v in sorted(selected_parents.items())
        },
        "generation_by_class": dict(sorted(selected_newest_later.items())),
        "R2G_trade_to_R2F_exact_identity_unmatched": dict(missing_r2g),
        "R2G_exact_matchable_trade_rows": sum(len(v) for v in selected_by.values()),
        "exact_match_is_causal_source_identity_not_an_entry_authorization": True,
    }


def run_market(
    market: str, *, r2f_ledger: Path, r2f_report: Path,
    r2g_ledger: Path, r2g_report: Path, frozen_control: Path,
) -> dict[str, Any]:
    if market not in R2CH_EXPECTED:
        raise ValueError("Unsupported market, BTCUSD frozen")
    rf = r2ch._read_jsonl(r2f_ledger)
    rg = r2ch._read_jsonl(r2g_ledger)
    rf_report: dict[str, Any] = json.loads(r2f_report.read_text(encoding="utf-8"))
    rg_report: dict[str, Any] = json.loads(r2g_report.read_text(encoding="utf-8"))
    r2ch._check_original_r2f(market, rf, rf_report)
    _verify_r2g(market, rg, rg_report)
    originals, original_diag = r2ch._scope_original_keys(market, frozen_control)
    comparison = _reconcile_three(market, rf, rg, originals)
    return {
        "identity": IDENTITY,
        "market": market,
        "evidence_window": {
            "start": r2ch.BEGIN.isoformat(),
            "end_exclusive": r2ch.END.isoformat(),
        },
        "source_runs": {"R2F": R2F_RUN, "R2G": R2G_RUN},
        "input_sha256": {
            "r2f_ledger": hashlib.sha256(r2f_ledger.read_bytes()).hexdigest(),
            "r2g_ledger": hashlib.sha256(r2g_ledger.read_bytes()).hexdigest(),
            "r2g_report": hashlib.sha256(r2g_report.read_bytes()).hexdigest(),
            "control_ledger": hashlib.sha256(frozen_control.read_bytes()).hexdigest(),
        },
        "original_scoped_selection": original_diag,
        "R2G_frozen_newest_report_historical_only": rg_report["policies"][CURRENT_NEWEST],
        "R2G_original_policy_trade_counts_verified": True,
        "R2F_original_source_counts_verified": True,
        "three_ledger_source_equivalence": comparison,
        "capacity_not_trades": True,
        "pnl_replayed": False,
        "fresh_holdout_used": False,
        "candidate_certified": False,
        "trader_sizing_volume_forbidden": True,
        "no_trade_execution": True,
        "no_merge": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("--market", required=True, choices=tuple(R2CH_EXPECTED))
    p.add_argument("--r2f-ledger", required=True, type=Path)
    p.add_argument("--r2f-report", required=True, type=Path)
    p.add_argument("--r2g-ledger", required=True, type=Path)
    p.add_argument("--r2g-report", required=True, type=Path)
    p.add_argument("--frozen-control", required=True, type=Path)
    a = p.parse_args()
    out = run_market(
        a.market, r2f_ledger=a.r2f_ledger, r2f_report=a.r2f_report,
        r2g_ledger=a.r2g_ledger, r2g_report=a.r2g_report,
        frozen_control=a.frozen_control,
    )
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "report.json").write_text(
        json.dumps(out, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print("VT08_R2CI_SOURCE_OVERLAP=" + json.dumps({
        k: out[k] for k in (
            "market", "three_ledger_source_equivalence",
            "R2G_original_policy_trade_counts_verified",
            "R2G_frozen_newest_report_historical_only",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
