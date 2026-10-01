"""Run Phase21 on the post-TRAIN part of the 9M historical shadow."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from cibo_phase19_causal_walk_forward import _bind_freeze
from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
)
from cibo_phase19_normalized_capital_mechanics import _parse_trade

from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    prior_digest_sha256,
)
from qore.infrastructure.cibo_ce2i_phase21_historical_shadow import (
    EXPECTED_ROWS_BY_TRADER,
    EXPECTED_VALIDATION_ROWS,
    VALIDATION_END,
    VALIDATION_START,
    evaluate_phase21_historical_shadow,
)


def build_report(
    *,
    paths: dict[str, Path],
) -> dict[str, object]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase21 shadow source set drift")

    parsed = []
    observed_counts = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} source row-count drift"
            )
        selected = []
        for row in rows:
            signal_at = datetime.fromisoformat(str(row["signal_at"]))
            exit_at = datetime.fromisoformat(str(row["exit_at"]))
            if signal_at < VALIDATION_START or exit_at > VALIDATION_END:
                continue
            selected.append(
                _bind_freeze(
                    _parse_trade(row, spec=spec),
                    frozen_at=VALIDATION_START,
                )
            )
        observed_counts[spec.trader_id.value] = len(selected)
        expected = EXPECTED_ROWS_BY_TRADER[spec.trader_id]
        if len(selected) != expected:
            raise ValueError(
                f"{spec.trader_id.value} Phase21 validation row drift"
            )
        parsed.extend(selected)

    if len(parsed) != EXPECTED_VALIDATION_ROWS:
        raise ValueError("Phase21 validation population drift")

    screen = evaluate_phase21_historical_shadow(tuple(parsed))
    payload: dict[str, object] = {
        "schema": "qore.cibo.phase21.historical-shadow-screen.v1",
        "status": "PASS" if screen.passed else "FAIL",
        "candidate_id": FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        "candidate_code_sha": FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        "candidate_parameter_sha256": (
            FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ),
        "train_prior_sha256": prior_digest_sha256(),
        "source_population": {
            "parent_shadow": (
                "CIBO_PHASE20D_HISTORICAL_SHADOW_HOLDOUT_1Y_V1"
            ),
            "parent_shadow_candidate_outcomes": 855,
            "post_train_validation_start": VALIDATION_START.isoformat(),
            "validation_end": VALIDATION_END.isoformat(),
            "rows_by_trader": observed_counts,
            "validation_rows": len(parsed),
            "historical_provider_usd_economics": False,
        },
        "screen": _jsonable(asdict(screen)),
        "interpretation": {
            "purpose": (
                "BURNED_SHADOW_PREFINAL_SCREEN_BEFORE_FRESH_2017H1"
            ),
            "four_fold_policy_delta_is_diagnostic_not_final_verdict": True,
            "aggregate_and_monte_carlo_hard_gates_enforced": True,
            "provider_stress_still_separate": True,
            "phase21_policy_freeze_still_separate": True,
        },
        "governance": {
            "shadow_outcomes_used_to_fit_train_prior": False,
            "policy_retuned_from_shadow_outcomes": False,
            "historical_evidence_relabelled_forward_observed": False,
            "historical_usd_claimed": False,
            "historical_provider_economics_claimed": False,
            "final_holdout_2017h1_read": False,
            "final_holdout_2017h1_status": "SEALED_UNTOUCHED",
            "broker_mutation_performed": False,
            "live_authorized": False,
            "real_capital_authorized": False,
        },
    }
    return payload


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        paths={key: getattr(args, key) for key in SOURCE_SPECS},
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
