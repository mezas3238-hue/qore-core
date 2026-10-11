"""GitHub Actions only: reconcile nine pinned Audit14/V49 sources into safe A1 JSONL.

Does not invoke cognition, change a trade, or read hypothetical R as signals.
CLI: market <V49-control-root> <A2-audit14-root> <output>
     aggregate <nine-market-results-root> <output>
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_a1_audit14_online_predecision_bridge_v1 import (
    A1FirstOnlinePredecisionWitness,
    IDENTITY,
    reconcile_audit14_online_witnesses,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)


def _jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip())


def market(
    original_root: Path, audit14_root: Path, output: Path,
) -> dict[str, Any]:
    original_files = tuple(original_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    audit_files = tuple(audit14_root.rglob("scalper-audit14-ids.jsonl"))
    if len(original_files) != 1 or len(audit_files) != 1:
        raise ValueError("one frozen V49 source and one pinned Audit14 ledger required")
    originals = tuple(V49Opportunity(**row) for row in _jsonl(original_files[0]))
    observations, summary = reconcile_audit14_online_witnesses(
        originals=originals, rows=_jsonl(audit_files[0]), full_nine_market=False,
    )
    if not observations or len({item.symbol for item in observations}) != 1:
        raise ValueError("source market missing or mixed")
    output.mkdir(parents=True, exist_ok=True)
    (output/"a1-audit14-predecision-market.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )
    with (output/"a1-audit14-predecision-witnesses.jsonl").open(
        "w", encoding="utf-8"
    ) as file:
        for item in observations:
            file.write(json.dumps(asdict(item),sort_keys=True)+"\n")
    return summary


def aggregate(root: Path, output: Path) -> dict[str, Any]:
    summary_paths = tuple(sorted(root.rglob("a1-audit14-predecision-market.json")))
    witness_paths = tuple(sorted(root.rglob("a1-audit14-predecision-witnesses.jsonl")))
    if len(summary_paths) != 9 or len(witness_paths) != 9:
        raise ValueError("all nine genuine market artifacts required")
    summaries = [json.loads(path.read_text(encoding="utf-8"))
                 for path in summary_paths]
    if any(item["identity"] != IDENTITY for item in summaries):
        raise ValueError("mixed or obsolete A1 interface")
    rows = tuple(A1FirstOnlinePredecisionWitness(**raw)
                 for path in witness_paths for raw in _jsonl(path))
    ids = {row.source_opportunity_id for row in rows}
    symbols = {row.symbol for row in rows}
    if len(rows) != 2876 or len(ids) != 2876 or len(symbols) != 9:
        raise ValueError("real nine-market original source population changed")
    if sum(s["source_ids_reconciled"] for s in summaries) != len(rows):
        raise ValueError("market source counts do not reconcile")
    statuses = Counter(item.status for item in rows)
    online_changed = sum(item.differs_from_v49 for item in rows)
    frozen_381 = sum(item.frozen_381_cohort for item in rows)
    if (
        sum(s["online_differs_from_v49"] for s in summaries) != online_changed
        or sum(s["static_cisd_381_cohort"] for s in summaries) != frozen_381
        or any(s["paper_trades_executed"] != 0
               or s["ex_post_outcomes_forwarded"] is not False for s in summaries)
    ):
        raise ValueError("market receipt has inconsistent or unsafe cognitive claims")
    result: dict[str, Any] = {
        "identity": IDENTITY, "markets": 9, "source_ids_reconciled": len(rows),
        "first_online_changed_from_v49": online_changed,
        "static_381_cohort": frozen_381,
        "pre_max3_statuses": dict(sorted(statuses.items())),
        "historical_v49_source_anchored": True,
        "H1_M15_new_universe_generated": False,
        "physical_bid_ask_costs": False,
        "master_frame_historical_run": False,
        "economic_trades_replayed_here": 0,
        "winner_outcomes_or_mfe_forwarded": False,
        "scalper_certified": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output/"a1-audit14-predecision-nine-market.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    p_market = sub.add_parser("market")
    p_market.add_argument("original", type=Path)
    p_market.add_argument("audit14", type=Path)
    p_market.add_argument("output", type=Path)
    p_aggregate = sub.add_parser("aggregate")
    p_aggregate.add_argument("root", type=Path)
    p_aggregate.add_argument("output", type=Path)
    args = parser.parse_args()
    result = (
        market(args.original, args.audit14, args.output)
        if args.mode == "market"
        else aggregate(args.root, args.output)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
