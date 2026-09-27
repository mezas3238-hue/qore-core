"""Recompute and verify frozen TRAIN-only Phase20 expectation priors.

Only the 523 Phase19 TRAIN opportunities are consumed. Phase19J validation is
not read for policy fitting, and no provider USD history is invented.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
)
from cibo_phase19_temporal_stability_validation import (
    EXPECTED_SPLIT_AT,
    EXPECTED_TRAINING_OPPORTUNITIES,
)

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    FROZEN_TRAIN_PRIORS,
    frozen_train_prior_for,
    prior_digest_sha256,
)

BLOCK_COUNT = 5


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _outcome(
    row: dict[str, Any],
    *,
    trader_id: TraderLineage,
) -> Decimal:
    if trader_id is TraderLineage.VT08_FOREX:
        value = row["raw_outcome_r"]
    elif trader_id is TraderLineage.VT31_NAS100:
        value = row["legacy_vt31_net_r_per_requested_r"]
    else:
        value = row["raw_net_010_r"]
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{trader_id.value} non-finite TRAIN outcome")
    return result


def _median_decimal(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise ValueError("TRAIN median population cannot be empty")
    if count % 2:
        return ordered[count // 2]
    with localcontext() as context:
        context.prec = 40
        return (
            ordered[count // 2 - 1] + ordered[count // 2]
        ) / Decimal(2)


def _chronological_block_means(
    rows: list[tuple[datetime, Decimal, Decimal]],
) -> tuple[Decimal, ...]:
    ordered = sorted(rows, key=lambda item: item[0])
    means: list[Decimal] = []
    for index in range(BLOCK_COUNT):
        start = index * len(ordered) // BLOCK_COUNT
        end = (index + 1) * len(ordered) // BLOCK_COUNT
        block = ordered[start:end]
        if not block:
            raise ValueError("TRAIN chronological block cannot be empty")
        with localcontext() as context:
            context.prec = 40
            means.append(
                sum((item[1] for item in block), Decimal(0))
                / Decimal(len(block))
            )
    return tuple(means)


def run(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("TRAIN prior source set drift")

    common_start = datetime.fromisoformat(EXPECTED_COMMON_START)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)
    split_at = datetime.fromisoformat(EXPECTED_SPLIT_AT)
    if not common_start < split_at < common_end:
        raise ValueError("TRAIN prior temporal split invalid")

    computed: dict[TraderLineage, dict[str, Any]] = {}
    total_rows = 0
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} source row-count drift"
            )

        selected: list[tuple[datetime, Decimal, Decimal]] = []
        common_count = 0
        for row in rows:
            entry_at = datetime.fromisoformat(str(row["entry_at"]))
            exit_at = datetime.fromisoformat(str(row["exit_at"]))
            if entry_at >= common_start and exit_at <= common_end:
                common_count += 1
            if entry_at >= common_start and exit_at <= split_at:
                with localcontext() as context:
                    context.prec = 40
                    duration_minutes = Decimal(
                        str((exit_at - entry_at).total_seconds())
                    ) / Decimal(60)
                if duration_minutes <= 0:
                    raise ValueError(
                        f"{spec.trader_id.value} non-positive duration"
                    )
                selected.append(
                    (
                        entry_at,
                        _outcome(row, trader_id=spec.trader_id),
                        duration_minutes,
                    )
                )
        if common_count != EXPECTED_COMMON_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} common-window row drift"
            )
        if not selected:
            raise ValueError(
                f"{spec.trader_id.value} TRAIN prior population empty"
            )

        blocks = _chronological_block_means(selected)
        block_median = _median_decimal(list(blocks))
        duration_median = _median_decimal(
            [item[2] for item in selected]
        )
        with localcontext() as context:
            context.prec = 40
            arithmetic_mean = (
                sum((item[1] for item in selected), Decimal(0))
                / Decimal(len(selected))
            )
        frozen = frozen_train_prior_for(spec.trader_id)
        if len(selected) != frozen.train_rows:
            raise ValueError(
                f"{spec.trader_id.value} TRAIN row-count prior drift"
            )
        if blocks != frozen.chronological_block_means_r:
            raise ValueError(
                f"{spec.trader_id.value} TRAIN block means drift"
            )
        if block_median != frozen.expected_structural_r:
            raise ValueError(
                f"{spec.trader_id.value} TRAIN MoM prior drift"
            )
        if duration_median != frozen.expected_capital_minutes:
            raise ValueError(
                f"{spec.trader_id.value} TRAIN duration prior drift"
            )
        if arithmetic_mean != frozen.arithmetic_mean_r_diagnostic:
            raise ValueError(
                f"{spec.trader_id.value} TRAIN arithmetic diagnostic drift"
            )

        total_rows += len(selected)
        computed[spec.trader_id] = {
            "train_rows": len(selected),
            "expected_structural_r": str(block_median),
            "expected_capital_minutes": str(duration_median),
            "chronological_block_means_r": [
                str(item) for item in blocks
            ],
            "arithmetic_mean_r_diagnostic": str(arithmetic_mean),
        }

    if total_rows != EXPECTED_TRAINING_OPPORTUNITIES:
        raise ValueError("Phase19 TRAIN prior total row-count drift")
    if len(FROZEN_TRAIN_PRIORS) != len(SOURCE_SPECS):
        raise ValueError("frozen TRAIN prior Trader coverage drift")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase20.train_expectation_prior.v1",
        "identity": "CIBO_PHASE20_TRAIN_PRIOR_V1",
        "status": "FROZEN_TRAIN_ONLY_CAUSAL_PRIOR",
        "estimator": {
            "expected_structural_r": (
                "CHRONOLOGICAL_MEDIAN_OF_MEANS_5"
            ),
            "expected_capital_minutes": "TRAIN_MEDIAN_MINUTES",
            "block_count": BLOCK_COUNT,
        },
        "training_window": {
            "start": EXPECTED_COMMON_START,
            "end": EXPECTED_SPLIT_AT,
        },
        "training_rows": total_rows,
        "prior_digest_sha256": prior_digest_sha256(),
        "rows": {
            trader_id.value: computed[trader_id]
            for trader_id in sorted(computed, key=lambda item: item.value)
        },
        "governance": {
            "phase19j_validation_rows_consumed_for_fit": 0,
            "phase19j_validation_reused": False,
            "historical_provider_usd_claimed": False,
            "outcome_aware_at_decision": False,
            "future_market_used_at_decision": False,
            "post_entry_path_used_at_decision": False,
            "research_only": True,
            "policy_certified": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        paths={
            key: getattr(args, key)
            for key in SOURCE_SPECS
        },
        output_path=args.output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
