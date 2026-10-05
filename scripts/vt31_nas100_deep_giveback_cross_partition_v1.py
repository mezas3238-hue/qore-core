"""Cross-partition adjudication for VT31 deep-giveback rescue.

Consumes only outputs of the consumed-evidence DGR frontier. The predeclared
research witness is the most conservative frontier member, current close
<= +0.25R. It is not a runtime policy and cannot open a holdout.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

SCHEMA = "qore.vt31.nas100.deep_giveback_rescue_adjudication.v1"
WITNESS = "DGR_CURRENT_CLOSE_MAX_0_25"
NEIGHBORS = (
    "DGR_CURRENT_CLOSE_MAX_0_50",
    "DGR_CURRENT_CLOSE_MAX_0_75",
    "DGR_CURRENT_CLOSE_MAX_1_00",
)
EXPECTED_PARTITIONS = ("r8_fresh", "r6", "r5")
MIN_WINNER_COUNT = Decimal("0.80")
MIN_WINNER_R = Decimal("0.90")


def _d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite metric")
    return result


def _pf(value: object) -> Decimal:
    return Decimal("Infinity") if value is None else _d(value)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != (
        "qore.vt31.nas100.deep_giveback_rescue_frontier.v1"
    ):
        raise ValueError("unexpected DGR frontier schema")
    governance = payload.get("governance", {})
    if governance.get("consumed_evidence_only") is not True:
        raise ValueError("DGR frontier must use consumed evidence only")
    if governance.get("opens_new_holdout") is not False:
        raise ValueError("DGR frontier cannot open holdout")
    return payload


def _halfyear_non_degradation(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[bool, list[dict[str, object]]]:
    base_blocks = baseline["halfyear_metrics"]
    cand_blocks = candidate["halfyear_metrics"]
    details: list[dict[str, object]] = []
    passed = True
    if set(base_blocks) != set(cand_blocks):
        return False, [{"reason": "HALFYEAR_IDENTITY_DRIFT"}]
    for block in sorted(base_blocks):
        base = base_blocks[block]
        cand = cand_blocks[block]
        mean_delta = _d(cand["mean_r"]) - _d(base["mean_r"])
        total_delta = _d(cand["total_r"]) - _d(base["total_r"])
        block_pass = mean_delta >= 0 and total_delta >= 0
        passed = passed and block_pass
        details.append(
            {
                "halfyear": block,
                "mean_r_delta": format(mean_delta, "f"),
                "total_r_delta": format(total_delta, "f"),
                "non_degrading": block_pass,
            }
        )
    return passed, details


def _adjudicate_variant(
    payload: dict[str, Any],
    variant: str,
) -> dict[str, object]:
    reports = payload["variant_reports"]
    baseline = reports["BASELINE"]
    candidate = reports[variant]
    b = baseline["metrics"]
    c = candidate["metrics"]
    preservation = candidate["winner_preservation"]

    pf_delta = _pf(c["profit_factor"]) - _pf(b["profit_factor"])
    mean_delta = _d(c["mean_r"]) - _d(b["mean_r"])
    dd_delta = (
        _d(c["max_drawdown_r"])
        - _d(b["max_drawdown_r"])
    )
    halfyear_pass, halfyears = _halfyear_non_degradation(
        baseline,
        candidate,
    )
    winner_count = _d(
        preservation["winner_count_preservation"]
    )
    winner_r = _d(
        preservation["winner_r_preservation"]
    )
    gates = {
        "same_terminal_sample": (
            int(c["sample"]) == int(b["sample"])
        ),
        "profit_factor_non_degrading": pf_delta >= 0,
        "mean_r_non_degrading": mean_delta >= 0,
        "drawdown_non_degrading": dd_delta <= 0,
        "winner_count_preservation": (
            winner_count >= MIN_WINNER_COUNT
        ),
        "winner_r_preservation": winner_r >= MIN_WINNER_R,
        "all_halfyears_non_degrading": halfyear_pass,
    }
    return {
        "partition": payload["partition"],
        "variant": variant,
        "armed_trade_count": candidate["armed_trade_count"],
        "pf_delta": format(pf_delta, "f"),
        "mean_r_delta": format(mean_delta, "f"),
        "max_drawdown_r_delta": format(dd_delta, "f"),
        "winner_count_preservation": format(
            winner_count,
            "f",
        ),
        "winner_r_preservation": format(winner_r, "f"),
        "halfyear_deltas": halfyears,
        "gates": gates,
        "passes": all(gates.values()),
    }


def adjudicate(paths: list[Path]) -> dict[str, object]:
    payloads = [_load(path) for path in paths]
    by_partition = {
        str(payload["partition"]): payload
        for payload in payloads
    }
    if set(by_partition) != set(EXPECTED_PARTITIONS):
        raise ValueError(
            "DGR adjudication requires exactly r8_fresh, r6, r5"
        )

    witness = {
        partition: _adjudicate_variant(
            by_partition[partition],
            WITNESS,
        )
        for partition in EXPECTED_PARTITIONS
    }
    neighborhood = {
        variant: {
            partition: _adjudicate_variant(
                by_partition[partition],
                variant,
            )
            for partition in EXPECTED_PARTITIONS
        }
        for variant in NEIGHBORS
    }

    witness_cross_partition = all(
        item["passes"]
        for item in witness.values()
    )
    strict_pf_improvement = all(
        _d(item["pf_delta"]) > 0
        for item in witness.values()
    )
    strict_mean_improvement = all(
        _d(item["mean_r_delta"]) > 0
        for item in witness.values()
    )
    perfect_winner_preservation = all(
        _d(item["winner_count_preservation"]) == 1
        and _d(item["winner_r_preservation"]) == 1
        for item in witness.values()
    )
    wider_frontier_failures = {
        variant: [
            partition
            for partition, item in results.items()
            if not item["passes"]
        ]
        for variant, results in neighborhood.items()
    }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "research_witness": WITNESS,
        "witness_partition_results": witness,
        "witness_cross_partition_non_degrading": (
            witness_cross_partition
        ),
        "witness_strict_pf_improvement_3_of_3": (
            strict_pf_improvement
        ),
        "witness_strict_mean_improvement_3_of_3": (
            strict_mean_improvement
        ),
        "witness_perfect_winner_preservation_3_of_3": (
            perfect_winner_preservation
        ),
        "neighbor_results": neighborhood,
        "wider_frontier_failure_partitions": (
            wider_frontier_failures
        ),
        "adjudication": (
            "SUPPORTED_CROSS_PARTITION_RESEARCH_WITNESS"
            if (
                witness_cross_partition
                and strict_pf_improvement
                and strict_mean_improvement
                and perfect_winner_preservation
            )
            else "NOT_SUPPORTED"
        ),
        "interpretation": (
            "deep giveback near entry is the supported mechanism; "
            "wider current-close thresholds are not assumed safe"
        ),
        "governance": {
            "consumed_evidence_only": True,
            "automatic_runtime_promotion": False,
            "entry_filter_created": False,
            "target_changed": False,
            "initial_stop_changed": False,
            "opens_new_holdout": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--partition-report",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = adjudicate(args.partition_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "adjudication": payload["adjudication"],
                "research_witness": payload["research_witness"],
                "witness_partition_results": payload[
                    "witness_partition_results"
                ],
                "wider_frontier_failure_partitions": payload[
                    "wider_frontier_failure_partitions"
                ],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
