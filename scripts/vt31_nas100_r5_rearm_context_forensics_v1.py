"""Cross-period causal rearm context forensics for VT31_NAS100.

Consumed-evidence diagnostics only. Replays the frozen first-position routing,
then the ACTIVITY_L / SCORE_PROTECT structural rearm layer and attributes rearm
economics to decision-time state. No fresh evidence is opened.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.rearm_context_forensics.v1"


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return engine._capital_metrics(
        engine._scale_capital_rows(
            rows,
            scalar=Decimal("0.60"),
        )
    )


def _groups(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(f"{field}={row.get(field)}" for field in fields)
        grouped[key].append(row)
    return {
        key: _metrics(items)
        for key, items in sorted(grouped.items())
    }


def analyze(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    first_rows, first_diag = corrective._first_rows(
        by_day,
        context_by_day,
        evidence=evidence,
        alt_partial_r=None,
        secondary_route_policy="ORIGINAL",
    )
    rearm_rows, rearm_diag = corrective._rearm_rows(
        by_day,
        context_by_day,
        first_rows,
        evidence=evidence,
        rearm_partial_r=None,
    )

    specs = {
        "score": ("rearm_quality_score",),
        "risk_class": ("rearm_risk_class",),
        "family": ("entry_family",),
        "side": ("side",),
        "family_x_side": ("entry_family", "side"),
        "score_x_family": ("rearm_quality_score", "entry_family"),
        "score_x_side": ("rearm_quality_score", "side"),
        "family_x_h1": ("entry_family", "h1_state"),
        "family_x_ref": (
            "entry_family",
            "reference_volatility_state",
        ),
        "family_x_structure": (
            "entry_family",
            "last_structure_event_family",
        ),
        "side_x_ref": ("side", "reference_volatility_state"),
        "first_tier_x_family": ("first_tier", "entry_family"),
        "first_tier_x_score": ("first_tier", "rearm_quality_score"),
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "rearm_trade_count": len(rearm_rows),
        "rearm_metrics": _metrics(rearm_rows),
        "interactions": {
            name: _groups(rearm_rows, fields)
            for name, fields in specs.items()
        },
        "first_diagnostics": first_diag,
        "rearm_diagnostics": rearm_diag,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "decision_time_context_only": True,
            "diagnostic_only": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "policy_promoted": False,
            "opens_new_holdout": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = analyze(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
