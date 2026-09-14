"""Cross-market adjudication for VT-31 R2.5 predeclared research variants."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    MARKETS,
    SCHEMA,
    VARIANTS,
    Vt31R25ResearchError,
    _metrics,
    _quartiles,
)

ADJUDICATION_SCHEMA = "qore.trader_lab.vt31_r2_5_adjudication.v1"


def _read(path: Path) -> dict[str, object]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt31R25ResearchError(f"cannot read {path.name}") from error
    if type(value) is not dict:
        raise Vt31R25ResearchError("research report must be an object")
    report = cast(dict[str, object], value)
    if report.get("schema") != SCHEMA:
        raise Vt31R25ResearchError("unexpected research report schema")
    if report.get("environment") != "demo" or report.get("read_only") is not True:
        raise Vt31R25ResearchError("adjudication requires read-only DEMO evidence")
    return report


def _variant(report: dict[str, object], variant_id: str) -> dict[str, object]:
    variants = report.get("variants")
    if type(variants) is not dict:
        raise Vt31R25ResearchError("variants must be an object")
    result = cast(dict[str, object], variants).get(variant_id)
    if type(result) is not dict:
        raise Vt31R25ResearchError(f"missing variant {variant_id}")
    return cast(dict[str, object], result)


def _trades(variant: dict[str, object]) -> list[dict[str, object]]:
    value = variant.get("trades")
    if type(value) is not list or any(type(item) is not dict for item in value):
        raise Vt31R25ResearchError("variant trades must be an object array")
    return cast(list[dict[str, object]], value)


def adjudicate(paths: tuple[Path, ...]) -> dict[str, object]:
    reports = tuple(_read(path) for path in paths)
    by_market = {cast(str, item["market"]): item for item in reports}
    if set(by_market) != MARKETS:
        raise Vt31R25ResearchError("exact NAS100/SP500/US30 reports are required")
    accounts = {cast(str, item["account_fingerprint"]) for item in reports}
    software = {cast(str, item["software_sha"]) for item in reports}
    if len(accounts) != 1 or len(software) != 1:
        raise Vt31R25ResearchError("market evidence must share account and software SHA")
    results: dict[str, object] = {}
    survivors: list[str] = []
    for configured in VARIANTS:
        variant_id = configured.variant_id
        market_variants = {
            market: _variant(report, variant_id) for market, report in by_market.items()
        }
        combined = sorted(
            [
                {**trade, "market": market}
                for market, variant in market_variants.items()
                for trade in _trades(variant)
            ],
            key=lambda item: (cast(str, item["signal_at"]), cast(str, item["market"])),
        )
        aggregate = _metrics(combined)
        stressed = _metrics(combined, friction=Decimal("0.05"))
        market_stress = {
            market: cast(dict[str, object], variant["stress_0_05r"])
            for market, variant in market_variants.items()
        }
        side_stress = {
            side: _metrics(
                [item for item in combined if item["side"] == side],
                friction=Decimal("0.05"),
            )
            for side in ("long", "short")
        }
        quartiles = _quartiles(combined)
        positive_quartiles = sum(
            Decimal(cast(str, item["mean_r"])) > 0 for item in quartiles
        )
        temporal = {
            f"{market}:{year}": cast(dict[str, object], metrics)
            for market, variant in market_variants.items()
            for year, metrics in cast(dict[str, object], variant["by_year"]).items()
        }
        positive_temporal = sum(
            Decimal(cast(str, item["mean_r"])) > 0
            for item in temporal.values()
            if cast(int, item["sample"]) >= 10
        )
        eligible_temporal = sum(
            cast(int, item["sample"]) >= 10 for item in temporal.values()
        )
        gates = {
            "aggregate_sample_at_least_150": cast(int, stressed["sample"]) >= 150,
            "each_market_sample_at_least_30": all(
                cast(int, item["sample"]) >= 30 for item in market_stress.values()
            ),
            "aggregate_stressed_mean_positive": Decimal(
                cast(str, stressed["mean_r"])
            )
            > 0,
            "aggregate_stressed_pf_at_least_1_10": (
                stressed["profit_factor"] is not None
                and Decimal(cast(str, stressed["profit_factor"])) >= Decimal("1.10")
            ),
            "aggregate_stressed_dd_at_most_20r": Decimal(
                cast(str, stressed["max_drawdown_r"])
            )
            <= Decimal(20),
            "every_market_stressed_mean_positive": all(
                Decimal(cast(str, item["mean_r"])) > 0
                for item in market_stress.values()
            ),
            "both_sides_stressed_mean_positive": all(
                Decimal(cast(str, item["mean_r"])) > 0
                for item in side_stress.values()
            ),
            "three_of_four_quartiles_positive": positive_quartiles >= 3,
            "two_thirds_eligible_temporal_blocks_positive": (
                eligible_temporal > 0 and positive_temporal * 3 >= eligible_temporal * 2
            ),
        }
        passed = all(gates.values())
        if passed:
            survivors.append(variant_id)
        results[variant_id] = {
            "fingerprint": configured.fingerprint(),
            "aggregate": aggregate,
            "stress_0_05r": stressed,
            "market_stress": market_stress,
            "side_stress": side_stress,
            "quartiles": quartiles,
            "temporal_blocks": temporal,
            "gates": gates,
            "candidate_grade_research_survivor": passed,
        }
    return {
        "schema": ADJUDICATION_SCHEMA,
        "research_only": True,
        "software_sha": next(iter(software)),
        "account_fingerprint": next(iter(accounts)),
        "markets": sorted(MARKETS),
        "same_configuration_across_markets": True,
        "hypothesis_count": len(VARIANTS),
        "survivors": survivors,
        "adjudication": (
            "CANDIDATE_JUSTIFIED_FOR_SEPARATE_FREEZE"
            if len(survivors) == 1
            else "V4_CANDIDATE_NOT_JUSTIFIED"
        ),
        "ambiguous_multiple_survivors": len(survivors) > 1,
        "candidate_frozen": False,
        "fresh_validation": "NOT_RUN_RESEARCH_STAGE",
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "variants": results,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        print("usage: vt31-r2-5-adjudication NAS100.json SP500.json US30.json")
        return 2
    try:
        payload = adjudicate(tuple(Path(item) for item in args))
    except Vt31R25ResearchError as error:
        print(f"VT-31 R2.5 adjudication failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
