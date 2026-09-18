"""VT31 NAS100 five-year consumed validation for the R5-derived reference.

This validation stitches the three immutable NAS100 M1 development evidence
packages (R8/R6/R5), retains pre-window warmup context, and evaluates the
already-selected ACTIVITY_L + global risk scalar 0.60 policy over exactly five
calendar years:

    [2017-07-01, 2022-07-01)

No parameter is selected or tuned inside this script. The entire interval is
consumed development evidence and is not a fresh certification holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

# Environment must be set before importing the evaluated research module.
os.environ["QORE_DD6_FRONTIER_ONLY"] = "1"
os.environ["QORE_EVAL_START_DATE"] = "2017-07-01"
os.environ["QORE_EVAL_END_EXCLUSIVE_DATE"] = "2022-07-01"
os.environ["QORE_INCLUDE_TRADE_ROWS"] = "1"

import vt31_nas100_causal_hybrid_rearm_v1 as rearm  # noqa: E402

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (  # noqa: E402
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5_reference_5y_validation.v1"
IDENTITY = "VT31_NAS100_R5_REFERENCE_5Y_VALIDATION_V1"
REFERENCE_VARIANT = (
    "REARM_ADAPTIVE_ACTIVITY_L_SCORE_PROTECT_RISK_SCALAR_060"
)
START_DATE = date(2017, 7, 1)
END_EXCLUSIVE_DATE = date(2022, 7, 1)
YEAR_BLOCKS = tuple(
    (
        date(year, 7, 1),
        date(year + 1, 7, 1),
    )
    for year in range(2017, 2022)
)


def _source_record(path: Path) -> tuple[list[object], dict[str, object]]:
    (
        series,
        account,
        fingerprint,
        checked_at,
        software_sha,
        provider,
    ) = load_market_evidence(path)
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
        raise ValueError("5Y source evidence account fingerprints disagree")
    if len(providers) != 1:
        raise ValueError("5Y source evidence provider symbols disagree")

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
        raise ValueError("5Y stitched evidence is empty")

    first_opened = cast(datetime, getattr(deduped[0], "opened_at"))
    last_closed = cast(datetime, getattr(deduped[-1], "closed_at"))
    if first_opened.date() > date(2016, 5, 1):
        raise ValueError("5Y warmup coverage is insufficient")
    if last_closed.date() < END_EXCLUSIVE_DATE:
        raise ValueError("5Y evaluation end is not covered")

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
    composite_fingerprint = hashlib.sha256(
        json.dumps(
            composite_material,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    current_sha = os.environ.get("GITHUB_SHA", "")
    if len(current_sha) != 40:
        current_sha = cast(str, records[-1]["software_sha"])

    for record in records:
        record["stitch_duplicate_count_total"] = duplicate_count

    return (
        tuple(deduped),
        next(iter(accounts)),
        composite_fingerprint,
        max(checked_values),
        current_sha,
        next(iter(providers)),
        records,
    )


def _annual_blocks(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for index, (start, end) in enumerate(YEAR_BLOCKS, start=1):
        selected = [
            row
            for row in rows
            if start
            <= date.fromisoformat(cast(str, row["local_date"]))
            < end
        ]
        metrics = rearm._capital_metrics(selected)
        blocks.append(
            {
                "year_block": index,
                "start_date": start.isoformat(),
                "end_exclusive_date": end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": (
                    len(selected) > 0
                    and Decimal(cast(str, metrics["total_r"])) > 0
                    and Decimal(cast(str, metrics["mean_r"])) > 0
                ),
            }
        )
    return blocks


def validate(
    *,
    r8_path: Path,
    r6_path: Path,
    r5_path: Path,
) -> dict[str, object]:
    stitched = _stitch((r8_path, r6_path, r5_path))
    (
        series,
        account,
        fingerprint,
        checked_at,
        software_sha,
        provider,
        records,
    ) = stitched

    original_loader = rearm.load_market_evidence

    def stitched_loader(
        _path: Path,
    ) -> tuple[tuple[object, ...], str, str, datetime, str, str]:
        return (
            series,
            account,
            fingerprint,
            checked_at,
            software_sha,
            provider,
        )

    rearm.load_market_evidence = stitched_loader
    try:
        replay = rearm.replay(
            Path("STITCHED_IMMUTABLE_5Y_EVIDENCE"),
            partition="five_year_consumed",
        )
    finally:
        rearm.load_market_evidence = original_loader

    variants = cast(dict[str, dict[str, object]], replay["variants"])
    if REFERENCE_VARIANT not in variants:
        raise ValueError("frozen 5Y reference variant was not produced")
    reference = variants[REFERENCE_VARIANT]
    rows = cast(list[dict[str, object]], reference["trade_rows"])
    if not rows:
        raise ValueError("5Y reference emitted no trade rows")

    annual = _annual_blocks(rows)
    overall = cast(dict[str, object], reference["metrics"])
    mc = cast(dict[str, object], reference["monte_carlo"])
    trade_count = int(cast(int, reference["trade_count"]))

    gates = {
        "exact_five_calendar_year_window": (
            (END_EXCLUSIVE_DATE - START_DATE).days in {1825, 1826}
            and len(annual) == 5
        ),
        "trade_count_750_to_875": 750 <= trade_count <= 875,
        "profit_factor_at_least_2": (
            overall["profit_factor"] is not None
            and Decimal(cast(str, overall["profit_factor"]))
            >= Decimal("2")
        ),
        "observed_dd_at_most_6r": (
            Decimal(cast(str, overall["max_drawdown_r"]))
            <= Decimal("6")
        ),
        "all_five_year_blocks_positive": all(
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

    compact_reference = {
        key: value
        for key, value in reference.items()
        if key != "trade_rows"
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "NAS100",
        "reference_variant": REFERENCE_VARIANT,
        "window": {
            "start_date": START_DATE.isoformat(),
            "end_exclusive_date": END_EXCLUSIVE_DATE.isoformat(),
            "calendar_years": 5,
            "status": "CONSUMED_EXTENDED_VALIDATION",
            "fresh": False,
        },
        "source_evidence": records,
        "stitched_evidence": {
            "bar_count": len(series),
            "first_opened_at": cast(
                datetime, getattr(series[0], "opened_at")
            ).astimezone(UTC).isoformat(),
            "last_closed_at": cast(
                datetime, getattr(series[-1], "closed_at")
            ).astimezone(UTC).isoformat(),
            "fingerprint": fingerprint,
            "warmup_context_retained": True,
        },
        "five_year_result": compact_reference,
        "five_annual_blocks": annual,
        "gates": gates,
        "passes_all_5y_development_gates": all(gates.values()),
        "governance": {
            "parameters_retuned_inside_5y": False,
            "reference_variant_preselected": True,
            "source_evidence_consumed": True,
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
    parser.add_argument("--r8", required=True, type=Path)
    parser.add_argument("--r6", required=True, type=Path)
    parser.add_argument("--r5", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = validate(
        r8_path=args.r8,
        r6_path=args.r6,
        r5_path=args.r5,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    result = cast(dict[str, object], payload["five_year_result"])
    print(
        json.dumps(
            {
                "reference_variant": payload["reference_variant"],
                "window": payload["window"],
                "trade_count": result["trade_count"],
                "metrics": result["metrics"],
                "monte_carlo": result["monte_carlo"],
                "annual_blocks": payload["five_annual_blocks"],
                "gates": payload["gates"],
                "passes_all": payload["passes_all_5y_development_gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
