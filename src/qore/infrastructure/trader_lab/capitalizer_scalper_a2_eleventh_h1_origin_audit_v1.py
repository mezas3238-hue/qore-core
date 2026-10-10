"""Eleventh audit: classify V49 H1 bias provenance without turning C3 share into fidelity.

This post-hoc origin census reads immutable source opportunities; it creates
zero orders and does not use outcomes. C2 is explicitly permitted by TTrades.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)

IDENTITY = "QORE_SCALPER_A2_ELEVENTH_H1_BASIS_ORIGIN_AUDIT_V1"


def classify_basis(basis: str) -> tuple[str, bool]:
    """Session inherited is a lifetime marker, NOT another source closure."""

    inherited = basis.startswith("SESSION_INHERITED:")
    actual = basis.removeprefix("SESSION_INHERITED:")
    if actual.startswith("CANDLE2_REVERSAL:"):
        return "CANDLE2_REVERSAL", inherited
    if actual.startswith("CANDLE3_CONFIRMATION:"):
        return "CANDLE3_CONFIRMATION", inherited
    return "UNRESOLVED_SOURCE_BASIS", inherited


def inspect_market(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    files = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(files) != 1:
        raise ValueError("expected precisely one frozen V49 source book")
    sources = tuple(V49Opportunity(**row) for row in _jsonl(files[0]))
    if not sources:
        raise ValueError("V49 source book is empty")
    symbol = sources[0].symbol
    if any(s.symbol != symbol for s in sources):
        raise ValueError("different symbols in one V49 book")
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for source in sources:
        sid = source_id(source)
        if sid in seen:
            raise ValueError("duplicate frozen opportunity identity")
        seen.add(sid)
        kind, inherited = classify_basis(source.h1_state_basis)
        counts[kind] += 1
        counts["SESSION_INHERITED" if inherited else "STATE_BEGAN_AT_H1_EVENT"] += 1
        rows.append({
            "source_opportunity_id": sid,
            "symbol": symbol,
            "h1_state_basis": source.h1_state_basis,
            "h1_state_from": source.h1_state_from,
            "h1_source_closure_kind": kind,
            "session_inherited": inherited,
            "h1_poi_provenance_independently_attested": False,
            "author_fidelity_certified": False,
            "admission_changed": False,
        })
    return {
        "identity": IDENTITY, "symbol": symbol, "sources": len(sources),
        "basis_counts": dict(sorted(counts.items())),
        "author_fidelity_certified": False, "admission_changed": 0,
        "paper_replay": False,
    }, tuple(rows)


def aggregate(root: Path) -> dict[str, Any]:
    reports = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(root.rglob("scalper-eleventh-h1-market.json"))
    ]
    if len(reports) != 9 or len({r["symbol"] for r in reports}) != 9:
        raise ValueError("requires nine distinct source markets")
    rows = [
        row for file in sorted(root.rglob("scalper-eleventh-h1-ids.jsonl"))
        for row in _jsonl(file)
    ]
    if len(rows) != 2876 or len({r["source_opportunity_id"] for r in rows}) != 2876:
        raise ValueError("frozen V49 source IDs not conserved")
    counts: Counter[str] = Counter(row["h1_source_closure_kind"] for row in rows)
    inherited = sum(bool(row["session_inherited"]) for row in rows)
    if sum(counts.values()) != 2876 or any(r["admission_changed"] for r in rows):
        raise ValueError("invalid census accounting or trade-authority leakage")
    return {
        "identity": IDENTITY, "sources": 2876, "markets": 9,
        "closure_basis_counts": dict(sorted(counts.items())),
        "session_inherited_sources": inherited,
        "not_inherited_sources": 2876-inherited,
        "december_c3_only_fraction_is_not_author_fidelity": True,
        "requires_poi_and_h1_m15_m1_causal_attestation": True,
        "admissions_changed": 0, "profit_factor": None,
        "certification": "NOT_CERTIFIED",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("original", type=Path)
    m.add_argument("output", type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("inputs", type=Path)
    a.add_argument("output", type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.mode == "market":
        report, rows = inspect_market(args.original)
        (args.output/"scalper-eleventh-h1-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8"
        )
        with (args.output/"scalper-eleventh-h1-ids.jsonl").open(
            "w", encoding="utf-8"
        ) as out:
            for row in rows:
                out.write(json.dumps(row, sort_keys=True)+"\n")
    else:
        report = aggregate(args.inputs)
        (args.output/"scalper-eleventh-h1-nine-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8"
        )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
