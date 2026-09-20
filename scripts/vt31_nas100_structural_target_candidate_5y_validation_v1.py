"""Five-year consumed validation for VT31 NAS100 Structural Target V1.

The candidate is preselected and frozen before this validation. This script
stitches the immutable R8/R6/R5 M1 evidence packages and evaluates exactly:

    [2017-07-01, 2022-07-01)

No parameter selection or retuning is permitted inside the five-year window.
The entire interval is consumed extended validation evidence, never fresh.

Required gates:
- 800-900 trades;
- PF >= 1.50;
- total R > 0;
- observed DD <= 6R;
- every Jul-1 to Jul-1 annual block positive;
- MC positive terminal >= 0.90;
- MC p95 DD <= 15R.
"""
# ruff: noqa: E402
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

os.environ["QORE_DD6_FRONTIER_ONLY"] = "1"
os.environ["QORE_EVAL_START_DATE"] = "2017-07-01"
os.environ["QORE_EVAL_END_EXCLUSIVE_DATE"] = "2022-07-01"
os.environ["QORE_INCLUDE_TRADE_ROWS"] = "1"

import vt31_nas100_capacity_selective_target_ladder_v1 as frontier
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_structural_target_candidate_v1 as candidate

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.structural_target_candidate_5y_validation.v1"
IDENTITY = "VT31_NAS100_STRUCTURAL_TARGET_V1_5Y"
START_DATE = date(2017, 7, 1)
END_EXCLUSIVE_DATE = date(2022, 7, 1)
YEAR_BLOCKS = tuple(
    (date(year, 7, 1), date(year + 1, 7, 1))
    for year in range(2017, 2022)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


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


def _stitch(
    paths: tuple[Path, ...],
) -> tuple[
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
        raise ValueError("5Y evidence account fingerprints disagree")
    if len(providers) != 1:
        raise ValueError("5Y evidence provider symbols disagree")

    all_bars.sort(
        key=lambda bar: (
            cast(datetime, getattr(bar, "opened_at")),
            cast(datetime, getattr(bar, "closed_at")),
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
                        "overlapping immutable evidence contradicts on M1"
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

    material = {
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
            material,
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
        fingerprint,
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
        metrics = residual._metrics(selected)
        blocks.append(
            {
                "year_block": index,
                "start_date": start.isoformat(),
                "end_exclusive_date": end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": (
                    bool(selected)
                    and _d(metrics["total_r"]) > 0
                    and _d(metrics["mean_r"]) > 0
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
    (
        series,
        account,
        evidence_fingerprint,
        checked_at,
        software_sha,
        provider,
        records,
    ) = _stitch((r8_path, r6_path, r5_path))

    def stitched_loader(
        _path: Path,
    ) -> tuple[tuple[object, ...], str, str, datetime, str, str]:
        return (
            series,
            account,
            evidence_fingerprint,
            checked_at,
            software_sha,
            provider,
        )

    original_residual_loader = residual.load_market_evidence
    original_frontier_loader = frontier.load_market_evidence
    residual.load_market_evidence = stitched_loader
    frontier.load_market_evidence = stitched_loader
    try:
        evaluation = candidate.evaluate(
            Path("STITCHED_IMMUTABLE_5Y_EVIDENCE"),
            partition="five_year_consumed",
            include_rows=True,
        )
    finally:
        residual.load_market_evidence = original_residual_loader
        frontier.load_market_evidence = original_frontier_loader

    if (
        evaluation["contract_fingerprint"]
        != candidate.contract_fingerprint()
    ):
        raise AssertionError("candidate fingerprint changed inside 5Y")

    rows = cast(list[dict[str, object]], evaluation.pop("trade_rows"))
    annual = _annual_blocks(rows)
    metrics = cast(dict[str, object], evaluation["metrics"])
    mc = cast(dict[str, object], evaluation["monte_carlo"])
    trade_count = int(cast(int, evaluation["trade_count"]))

    gates = {
        "exact_five_calendar_year_window": (
            (END_EXCLUSIVE_DATE - START_DATE).days in {1825, 1826}
            and len(annual) == 5
        ),
        "trade_count_800_to_900": 800 <= trade_count <= 900,
        "profit_factor_at_least_1_50": (
            metrics["profit_factor"] is not None
            and _d(metrics["profit_factor"]) >= Decimal("1.50")
        ),
        "total_r_positive": _d(metrics["total_r"]) > 0,
        "observed_dd_at_most_6r": (
            _d(metrics["max_drawdown_r"]) <= Decimal("6")
        ),
        "all_five_year_blocks_positive": all(
            bool(block["positive"]) for block in annual
        ),
        "mc_positive_at_least_0_90": (
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
        ),
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_id": candidate.CANDIDATE_ID,
        "selected_variant": candidate.SELECTED_VARIANT,
        "contract_fingerprint": candidate.contract_fingerprint(),
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
                datetime,
                getattr(series[0], "opened_at"),
            ).astimezone(UTC).isoformat(),
            "last_closed_at": cast(
                datetime,
                getattr(series[-1], "closed_at"),
            ).astimezone(UTC).isoformat(),
            "fingerprint": evidence_fingerprint,
            "warmup_context_retained": True,
        },
        "five_year_result": evaluation,
        "five_annual_blocks": annual,
        "gates": gates,
        "passes_all_5y_development_gates": all(gates.values()),
        "governance": {
            "parameters_retuned_inside_5y": False,
            "candidate_preselected_and_frozen": True,
            "contract_fingerprint_unchanged": True,
            "source_evidence_consumed": True,
            "opens_new_holdout": False,
            "may_be_called_fresh": False,
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
                "candidate_id": payload["candidate_id"],
                "contract_fingerprint": payload[
                    "contract_fingerprint"
                ],
                "window": payload["window"],
                "trade_count": result["trade_count"],
                "metrics": result["metrics"],
                "monte_carlo": result["monte_carlo"],
                "annual_blocks": payload["five_annual_blocks"],
                "gates": payload["gates"],
                "passes_all": payload[
                    "passes_all_5y_development_gates"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
