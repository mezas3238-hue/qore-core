"""Deep cross-period CORE context forensics for VT31_NAS100_R5.

Consumed-evidence diagnostics only. Replays the unchanged first-position
architecture and studies only CORE-authorized trades using state known at or
before decision time. No fresh evidence is opened and no policy is promoted.
"""
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

SCHEMA = "qore.vt31.nas100.r5.core_context_forensics.v2"
MARKET = "NAS100"
GLOBAL_SCALAR = Decimal("0.60")


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return engine._capital_metrics(
        engine._scale_capital_rows(rows, scalar=GLOBAL_SCALAR)
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
    (
        series,
        account,
        evidence,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("CORE context forensics requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
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
    core_rows = [
        dict(row)
        for row in first_rows
        if str(row.get("tier")) == "CORE"
    ]
    for row in core_rows:
        row["core_family_bucket"] = (
            "BREAKER"
            if str(row.get("entry_family")) == "breaker"
            else "NON_BREAKER"
        )

    specs = {
        "core_family_bucket": ("core_family_bucket",),
        "core_family_bucket_x_side": ("core_family_bucket", "side"),
        "core_family_bucket_x_h1": ("core_family_bucket", "h1_state"),
        "core_family_bucket_x_reference_volatility": (
            "core_family_bucket",
            "reference_volatility_state",
        ),
        "core_family_bucket_x_cash_open": (
            "core_family_bucket",
            "cash_open_state",
        ),
        "core_family_bucket_x_last_structure": (
            "core_family_bucket",
            "last_structure_event_family",
        ),
        "family": ("entry_family",),
        "side": ("side",),
        "family_x_side": ("entry_family", "side"),
        "family_x_h1": ("entry_family", "h1_state"),
        "family_x_h4": ("entry_family", "h4_state"),
        "family_x_reference_volatility": (
            "entry_family",
            "reference_volatility_state",
        ),
        "family_x_current_path": (
            "entry_family",
            "current_path_vs_previous",
        ),
        "family_x_prior_day": ("entry_family", "prior_day_state"),
        "family_x_premarket": ("entry_family", "premarket_state"),
        "family_x_cash_open": ("entry_family", "cash_open_state"),
        "family_x_last_structure": (
            "entry_family",
            "last_structure_event_family",
        ),
        "side_x_h1": ("side", "h1_state"),
        "side_x_reference_volatility": (
            "side",
            "reference_volatility_state",
        ),
        "side_x_cash_open": ("side", "cash_open_state"),
        "family_x_side_x_h1": (
            "entry_family",
            "side",
            "h1_state",
        ),
        "family_x_side_x_reference_volatility": (
            "entry_family",
            "side",
            "reference_volatility_state",
        ),
        "family_x_side_x_cash_open": (
            "entry_family",
            "side",
            "cash_open_state",
        ),
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "core_trade_count": len(core_rows),
        "core_metrics": _metrics(core_rows),
        "interactions": {
            name: _groups(core_rows, fields)
            for name, fields in specs.items()
        },
        "first_diagnostics": first_diag,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "core_only": True,
            "decision_time_context_only": True,
            "diagnostic_only": True,
            "global_risk_scalar": "0.60",
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "policy_promoted": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "production_authorized": False,
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
