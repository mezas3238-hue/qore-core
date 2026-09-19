"""Robustness validation for VT31 NAS100 ALLOC_G.

Consumed evidence only. The ALLOC_G capital policy is frozen before this
validation. This script can evaluate either one immutable evidence package or a
stitched set of the immutable R8/R6/R5 NAS100 packages. It does not open fresh
evidence, retune parameters, change authorization, or promote a candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.alloc_g_robustness_validation.v1"
PROFILE_NAME = "ALLOC_G_CORE_FAMILY_050"
MARKET = "NAS100"


def _source_record(path: Path) -> tuple[list[object], dict[str, object]]:
    series, account, fingerprint, checked_at, software_sha, provider = (
        load_market_evidence(path)
    )
    return list(series), {
        "path_name": path.name,
        "account_fingerprint": account,
        "evidence_fingerprint": fingerprint,
        "checked_at": checked_at.astimezone(UTC).isoformat(),
        "software_sha": software_sha,
        "provider_symbol_name": provider,
        "bar_count": len(series),
        "first_opened_at": series[0].opened_at.astimezone(UTC).isoformat(),
        "last_closed_at": series[-1].closed_at.astimezone(UTC).isoformat(),
    }


def _stitch(paths: tuple[Path, ...]) -> tuple[
    tuple[object, ...],
    str,
    str,
    datetime,
    str,
    str,
    list[dict[str, object]],
]:
    all_bars: list[object] = []
    records: list[dict[str, object]] = []
    accounts: set[str] = set()
    providers: set[str] = set()
    checked_values: list[datetime] = []

    for path in paths:
        bars, record = _source_record(path)
        all_bars.extend(bars)
        records.append(record)
        accounts.add(cast(str, record["account_fingerprint"]))
        providers.add(cast(str, record["provider_symbol_name"]))
        checked_values.append(
            datetime.fromisoformat(cast(str, record["checked_at"]))
        )

    if len(accounts) != 1:
        raise ValueError("stitched evidence account fingerprints disagree")
    if len(providers) != 1:
        raise ValueError("stitched evidence provider symbols disagree")

    all_bars.sort(
        key=lambda bar: (
            getattr(bar, "opened_at"),
            getattr(bar, "closed_at"),
        )
    )
    deduped: list[object] = []
    duplicate_count = 0
    for bar in all_bars:
        if deduped:
            previous = deduped[-1]
            same_identity = (
                getattr(previous, "opened_at") == getattr(bar, "opened_at")
                and getattr(previous, "closed_at") == getattr(bar, "closed_at")
            )
            if same_identity:
                if previous != bar:
                    raise ValueError(
                        "overlapping immutable evidence contradicts on M1 bar"
                    )
                duplicate_count += 1
                continue
        deduped.append(bar)

    if not deduped:
        raise ValueError("stitched evidence is empty")

    first_opened = cast(datetime, getattr(deduped[0], "opened_at"))
    last_closed = cast(datetime, getattr(deduped[-1], "closed_at"))
    composite_material = {
        "schema": SCHEMA,
        "source_fingerprints": sorted(
            cast(str, record["evidence_fingerprint"])
            for record in records
        ),
        "first_opened_at": first_opened.astimezone(UTC).isoformat(),
        "last_closed_at": last_closed.astimezone(UTC).isoformat(),
        "deduped_bar_count": len(deduped),
        "duplicate_count": duplicate_count,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            composite_material,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    software_sha = os.environ.get("GITHUB_SHA", "")
    if len(software_sha) != 40:
        software_sha = cast(str, records[-1]["software_sha"])

    for record in records:
        record["stitch_duplicate_count_total"] = duplicate_count

    return (
        tuple(deduped),
        next(iter(accounts)),
        fingerprint,
        max(checked_values),
        software_sha,
        next(iter(providers)),
        records,
    )


def _sorted(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(rows, key=lambda row: cast(str, row["signal_at"]))


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


def _annual_blocks(
    rows: list[dict[str, object]],
    *,
    start: date,
    years: int,
) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for index in range(years):
        block_start = date(start.year + index, start.month, start.day)
        block_end = date(start.year + index + 1, start.month, start.day)
        selected = [
            row
            for row in rows
            if block_start
            <= date.fromisoformat(cast(str, row["local_date"]))
            < block_end
        ]
        metrics = _metrics(selected)
        blocks.append(
            {
                "year_block": index + 1,
                "start_date": block_start.isoformat(),
                "end_exclusive_date": block_end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": (
                    bool(selected)
                    and Decimal(cast(str, metrics["total_r"])) > 0
                    and Decimal(cast(str, metrics["mean_r"])) > 0
                ),
            }
        )
    return blocks


def _build_rows(
    series: tuple[object, ...],
    *,
    evidence_fingerprint: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    if not series:
        raise ValueError("evidence is empty")
    symbol = getattr(getattr(series[0], "instrument"), "symbol")
    if symbol != MARKET:
        raise ValueError("ALLOC_G robustness validation requires NAS100")

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
        evidence=evidence_fingerprint,
        alt_partial_r=None,
        secondary_route_policy="ORIGINAL",
    )
    rearm_rows, rearm_diag = corrective._rearm_rows(
        by_day,
        context_by_day,
        first_rows,
        evidence=evidence_fingerprint,
        rearm_partial_r=None,
    )
    nominal = _sorted([*first_rows, *rearm_rows])
    profile = allocation.PROFILES[PROFILE_NAME]
    adjusted = allocation._apply_profile(nominal, profile=profile)
    return adjusted, {
        "first": first_diag,
        "rearm": rearm_diag,
        "nominal_trade_count": len(nominal),
        "first_trade_count": len(first_rows),
        "rearm_trade_count": len(rearm_rows),
    }


def validate(
    *,
    series: tuple[object, ...],
    account: str,
    evidence_fingerprint: str,
    checked_at: datetime,
    software_sha: str,
    provider: str,
    source_records: list[dict[str, object]],
    window_label: str,
    start: date,
    end_exclusive: date,
    annual_years: int,
    density_min: int,
    density_max: int,
    pf_min: Decimal,
) -> dict[str, object]:
    rows, diagnostics = _build_rows(
        series,
        evidence_fingerprint=evidence_fingerprint,
    )
    selected = [
        row
        for row in rows
        if start
        <= date.fromisoformat(cast(str, row["local_date"]))
        < end_exclusive
    ]
    metrics = _metrics(selected)
    mc = engine._monte_carlo(
        selected,
        variant=f"ALLOC_G_ROBUSTNESS:{window_label}",
    )
    annual = _annual_blocks(selected, start=start, years=annual_years)

    trade_count = len(selected)
    gates = {
        "density_in_owner_range": density_min <= trade_count <= density_max,
        "profit_factor_at_least_threshold": (
            metrics["profit_factor"] is not None
            and Decimal(cast(str, metrics["profit_factor"])) >= pf_min
        ),
        "observed_dd_at_most_6r": (
            Decimal(cast(str, metrics["max_drawdown_r"])) <= Decimal("6")
        ),
        "all_annual_blocks_positive": all(
            bool(block["positive"]) for block in annual
        ),
        "mc_positive_at_least_0_90": (
            Decimal(cast(str, mc["positive_terminal_probability"]))
            >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_15r": (
            Decimal(cast(str, mc["p95_max_drawdown_r"]))
            <= Decimal("15")
        ),
    }

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "profile": PROFILE_NAME,
        "window": {
            "label": window_label,
            "start_date": start.isoformat(),
            "end_exclusive_date": end_exclusive.isoformat(),
            "status": "CONSUMED_VALIDATION",
            "fresh": False,
        },
        "profile_parameters": {
            key: format(value, "f")
            for key, value in allocation.PROFILES[PROFILE_NAME].items()
        },
        "trade_count": trade_count,
        "metrics": metrics,
        "monte_carlo": mc,
        "annual_blocks": annual,
        "by_tier": _group_metrics(selected, ("tier",)),
        "by_tier_family": _group_metrics(
            selected,
            ("tier", "entry_family"),
        ),
        "by_side": _group_metrics(selected, ("side",)),
        "gates": gates,
        "passes_all_robustness_gates": all(gates.values()),
        "diagnostics": diagnostics,
        "source_evidence": source_records,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence_fingerprint,
            "checked_at": checked_at.astimezone(UTC).isoformat(),
            "software_sha": software_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "profile_frozen_before_validation": True,
            "parameters_retuned_inside_validation": False,
            "trade_authorization_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_admission_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_time_as_runtime_rule": False,
            "opens_new_holdout": False,
            "may_be_called_fresh": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--r8", type=Path)
    parser.add_argument("--r6", type=Path)
    parser.add_argument("--r5", type=Path)
    parser.add_argument("--window-label", required=True)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end-exclusive", required=True, type=date.fromisoformat)
    parser.add_argument("--annual-years", required=True, type=int)
    parser.add_argument("--density-min", required=True, type=int)
    parser.add_argument("--density-max", required=True, type=int)
    parser.add_argument("--pf-min", required=True, type=Decimal)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    stitched_requested = all((args.r8, args.r6, args.r5))
    single_requested = args.evidence is not None
    if stitched_requested == single_requested:
        raise ValueError(
            "provide either --evidence or all of --r8/--r6/--r5"
        )

    if single_requested:
        series, account, fingerprint, checked_at, software_sha, provider = (
            load_market_evidence(cast(Path, args.evidence))
        )
        source_records = [
            {
                "path_name": cast(Path, args.evidence).name,
                "evidence_fingerprint": fingerprint,
                "bar_count": len(series),
            }
        ]
    else:
        (
            series,
            account,
            fingerprint,
            checked_at,
            software_sha,
            provider,
            source_records,
        ) = _stitch(
            (
                cast(Path, args.r8),
                cast(Path, args.r6),
                cast(Path, args.r5),
            )
        )

    payload = validate(
        series=tuple(series),
        account=account,
        evidence_fingerprint=fingerprint,
        checked_at=checked_at,
        software_sha=software_sha,
        provider=provider,
        source_records=source_records,
        window_label=args.window_label,
        start=args.start,
        end_exclusive=args.end_exclusive,
        annual_years=args.annual_years,
        density_min=args.density_min,
        density_max=args.density_max,
        pf_min=args.pf_min,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "window": payload["window"],
                "trade_count": payload["trade_count"],
                "metrics": payload["metrics"],
                "monte_carlo": payload["monte_carlo"],
                "annual_blocks": payload["annual_blocks"],
                "gates": payload["gates"],
                "passes_all": payload["passes_all_robustness_gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
