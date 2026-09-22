"""Root-cause regime diagnostics for VT31 NAS100 ALLOC_G.

Consumed evidence only. Replays the unchanged ALLOC_G policy and measures
decision-time market state across R5/R6/R8 and the consumed 2022-2024 interval.

Calendar blocks are used only to diagnose temporal instability. Dates, fold
identity, and terminal outcomes are never runtime authorization inputs.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.alloc_g_regime_root_cause_forensics.v1"
MARKET = "NAS100"
PROFILE_NAME = "ALLOC_G_CORE_FAMILY_050"
NY = ZoneInfo("America/New_York")

CONSUMED_BLOCKS = {
    "Y1_WEAK_2022-07-18_2023-07-18": (
        date(2022, 7, 18),
        date(2023, 7, 18),
    ),
    "Y2_RECOVERY_2023-07-18_2024-07-18": (
        date(2023, 7, 18),
        date(2024, 7, 18),
    ),
}


def _signal_date(row: dict[str, object]) -> date:
    raw = str(row["signal_at"]).replace("Z", "+00:00")
    timestamp = datetime.fromisoformat(raw)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(NY).date()


def _sorted(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(rows, key=lambda row: cast(str, row["signal_at"]))


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return engine._capital_metrics(_sorted(rows))


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _bucket_reclaim_age(value: object) -> str:
    if value is None:
        return "missing"
    age = int(value)
    if age <= 4:
        return "0_4m"
    if age <= 9:
        return "5_9m"
    if age <= 19:
        return "10_19m"
    return "20m_plus"


def _bucket_confirmation_latency(value: object) -> str:
    if value is None:
        return "missing"
    latency = int(value)
    if latency <= 2:
        return "0_2m"
    if latency <= 5:
        return "3_5m"
    if latency <= 10:
        return "6_10m"
    return "11m_plus"


def _bucket_ratio(
    value: object,
    *,
    low: Decimal,
    high: Decimal,
) -> str:
    number = _decimal(value)
    if number is None:
        return "missing"
    if number < low:
        return "low"
    if number <= high:
        return "mid"
    return "high"


def _decorate(row: dict[str, object]) -> dict[str, object]:
    updated = dict(row)
    updated["reclaim_age_bucket"] = _bucket_reclaim_age(
        row.get("reference_reclaim_age_minutes")
    )
    updated["confirmation_latency_bucket"] = _bucket_confirmation_latency(
        row.get("confirmation_latency_minutes")
    )
    updated["current_path_bucket"] = _bucket_ratio(
        row.get("current_path_vs_previous"),
        low=Decimal("0.75"),
        high=Decimal("1.25"),
    )
    updated["risk_ref_bucket"] = _bucket_ratio(
        row.get("risk_ref"),
        low=Decimal("0.30"),
        high=Decimal("0.70"),
    )
    return updated


def _group_metrics(
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


def _interaction_specs() -> dict[str, tuple[str, ...]]:
    return {
        "tier_x_family": ("tier", "entry_family"),
        "tier_x_side": ("tier", "side"),
        "tier_x_h1": ("tier", "h1_state"),
        "tier_x_h4": ("tier", "h4_state"),
        "tier_x_reference_volatility": (
            "tier",
            "reference_volatility_state",
        ),
        "tier_x_current_path": ("tier", "current_path_bucket"),
        "tier_x_prior_day": ("tier", "prior_day_state"),
        "tier_x_premarket": ("tier", "premarket_state"),
        "tier_x_cash_open": ("tier", "cash_open_state"),
        "tier_x_last_structure": ("tier", "last_structure_event_family"),
        "tier_x_reclaim_age": ("tier", "reclaim_age_bucket"),
        "tier_x_confirmation_latency": (
            "tier",
            "confirmation_latency_bucket",
        ),
        "tier_x_risk_ref": ("tier", "risk_ref_bucket"),
        "family_x_h1": ("entry_family", "h1_state"),
        "family_x_reference_volatility": (
            "entry_family",
            "reference_volatility_state",
        ),
        "family_x_current_path": (
            "entry_family",
            "current_path_bucket",
        ),
        "family_x_prior_day": ("entry_family", "prior_day_state"),
        "family_x_premarket": ("entry_family", "premarket_state"),
        "family_x_cash_open": ("entry_family", "cash_open_state"),
        "family_x_last_structure": (
            "entry_family",
            "last_structure_event_family",
        ),
        "family_x_reclaim_age": (
            "entry_family",
            "reclaim_age_bucket",
        ),
        "family_x_confirmation_latency": (
            "entry_family",
            "confirmation_latency_bucket",
        ),
        "family_x_risk_ref": ("entry_family", "risk_ref_bucket"),
        "tier_x_family_x_h1": ("tier", "entry_family", "h1_state"),
        "tier_x_family_x_reference_volatility": (
            "tier",
            "entry_family",
            "reference_volatility_state",
        ),
        "tier_x_family_x_current_path": (
            "tier",
            "entry_family",
            "current_path_bucket",
        ),
        "tier_x_family_x_cash_open": (
            "tier",
            "entry_family",
            "cash_open_state",
        ),
        "tier_x_family_x_confirmation_latency": (
            "tier",
            "entry_family",
            "confirmation_latency_bucket",
        ),
    }


def _analyze_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    specs = _interaction_specs()
    return {
        "trade_count": len(rows),
        "metrics": _metrics(rows),
        "interactions": {
            name: _group_metrics(rows, fields)
            for name, fields in specs.items()
        },
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("regime root-cause forensics requires NAS100")

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
    rearm_rows, rearm_diag = corrective._rearm_rows(
        by_day,
        context_by_day,
        first_rows,
        evidence=evidence,
        rearm_partial_r=None,
    )
    nominal = _sorted([*first_rows, *rearm_rows])
    adjusted = [
        _decorate(row)
        for row in allocation._apply_profile(
            nominal,
            profile=allocation.PROFILES[PROFILE_NAME],
        )
    ]

    blocks: dict[str, object] = {}
    if partition == "consumed_holdout":
        for name, (start, end) in CONSUMED_BLOCKS.items():
            selected = [
                row
                for row in adjusted
                if start <= _signal_date(row) < end
            ]
            blocks[name] = {
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                **_analyze_rows(selected),
            }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "allocation_profile": PROFILE_NAME,
        "overall": _analyze_rows(adjusted),
        "consumed_blocks": blocks,
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "decision_time_state_only": True,
            "calendar_blocks_diagnostic_only": True,
            "calendar_blocks_used_at_runtime": False,
            "trade_authorization_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "allocation_profile_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "policy_promoted": False,
            "opens_new_holdout": False,
            "candidate_certified": False,
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
    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "overall": payload["overall"],
                "consumed_blocks": payload["consumed_blocks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
