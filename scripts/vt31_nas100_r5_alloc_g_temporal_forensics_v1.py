"""Temporal and component diagnostics for VT31 NAS100 ALLOC_G.

Consumed-evidence research only. Replays the unchanged R5 trade authorization,
entry, stop, target, lifecycle, ACTIVITY_L structural rearm and applies the
already-tested ALLOC_G_CORE_FAMILY_050 capital policy. The script then measures
where expectancy is concentrated in time and by trade component.

No fresh evidence is opened. No policy is promoted by this diagnostic.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.alloc_g_temporal_forensics.v1"
MARKET = "NAS100"
PROFILE_NAME = "ALLOC_G_CORE_FAMILY_050"
NY = ZoneInfo("America/New_York")

HOLDOUT_BLOCKS: dict[str, tuple[date, date]] = {
    "Y1_2022-07-18_2023-07-18": (
        date(2022, 7, 18),
        date(2023, 7, 18),
    ),
    "Y2_2023-07-18_2024-07-18": (
        date(2023, 7, 18),
        date(2024, 7, 18),
    ),
    "H1_2022-07-18_2023-01-18": (
        date(2022, 7, 18),
        date(2023, 1, 18),
    ),
    "H2_2023-01-18_2023-07-18": (
        date(2023, 1, 18),
        date(2023, 7, 18),
    ),
    "H3_2023-07-18_2024-01-18": (
        date(2023, 7, 18),
        date(2024, 1, 18),
    ),
    "H4_2024-01-18_2024-07-18": (
        date(2024, 1, 18),
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
    return sorted(rows, key=lambda row: str(row["signal_at"]))


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return engine._capital_metrics(_sorted(rows))


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


def _period_metrics(
    rows: list[dict[str, object]],
    key_fn: Callable[[date], str],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = key_fn(_signal_date(row))
        grouped[key].append(row)
    return {
        key: _metrics(items)
        for key, items in sorted(grouped.items())
    }


def _calendar_year(local_day: date) -> str:
    return str(local_day.year)


def _calendar_half(local_day: date) -> str:
    half = 1 if local_day.month <= 6 else 2
    return f"{local_day.year}-H{half}"


def _calendar_quarter(local_day: date) -> str:
    quarter = (local_day.month - 1) // 3 + 1
    return f"{local_day.year}-Q{quarter}"


def _block_rows(
    rows: list[dict[str, object]],
    start: date,
    end_exclusive: date,
) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if start <= _signal_date(row) < end_exclusive
    ]


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
        raise ValueError("ALLOC_G temporal forensics requires NAS100")

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
    profile = allocation.PROFILES[PROFILE_NAME]
    adjusted = allocation._apply_profile(nominal, profile=profile)

    owner_blocks = {
        name: {
            "start": start.isoformat(),
            "end_exclusive": end.isoformat(),
            "metrics": _metrics(block_rows),
            "by_tier": _group_metrics(block_rows, ("tier",)),
            "by_tier_family": _group_metrics(
                block_rows,
                ("tier", "entry_family"),
            ),
        }
        for name, (start, end) in HOLDOUT_BLOCKS.items()
        if (
            block_rows := _block_rows(adjusted, start, end)
        )
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "profile": PROFILE_NAME,
        "profile_parameters": {
            key: format(value, "f")
            for key, value in profile.items()
        },
        "trade_count": len(adjusted),
        "overall": _metrics(adjusted),
        "calendar_year": _period_metrics(
            adjusted,
            _calendar_year,
        ),
        "calendar_half": _period_metrics(
            adjusted,
            _calendar_half,
        ),
        "calendar_quarter": _period_metrics(
            adjusted,
            _calendar_quarter,
        ),
        "by_tier": _group_metrics(adjusted, ("tier",)),
        "by_tier_family": _group_metrics(
            adjusted,
            ("tier", "entry_family"),
        ),
        "by_side": _group_metrics(adjusted, ("side",)),
        "by_tier_side": _group_metrics(
            adjusted,
            ("tier", "side"),
        ),
        "owner_holdout_blocks": owner_blocks,
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
            "allocation_profile_fixed_before_temporal_analysis": True,
            "trade_authorization_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_admission_changed": False,
            "terminal_pnl_used_only_for_evaluation": True,
            "uses_fold_identity_at_runtime": False,
            "diagnostic_only": True,
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
