"""Consume the owner-authorized one-year Phase20D historical shadow."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_historical_shadow import (
    EVIDENCE_KIND,
    POLICY_ID,
    SHADOW_CANDIDATE_ID,
    HistoricalShadowObservation,
    evaluate_historical_shadow_population,
    policy_invariants,
)
from scripts.cibo_phase19_integrated_chronology_replay import (
    PHASE19_REQUIRED_TRADERS,
    SOURCE_SPECS,
    _jsonl,
    _parse_row,
)
from scripts.cibo_phase19_integrated_chronology_replay import (
    replay as phase19_replay,
)


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _sha256(value: object) -> str:
    raw = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def consume(
    *,
    paths: dict[str, Path],
    chronology_output: Path,
    output: Path,
) -> dict[str, object]:
    chronology = phase19_replay(
        paths=paths,
        output_path=chronology_output,
    )
    common = chronology["common_window"]
    common_start = datetime.fromisoformat(str(common["start"]))
    common_end = datetime.fromisoformat(str(common["end"]))

    observations: list[HistoricalShadowObservation] = []
    for key, spec in SOURCE_SPECS.items():
        for row in _jsonl(paths[key]):
            parsed = _parse_row(row, spec=spec).opportunity
            if parsed.entry_at >= common_start and parsed.exit_at <= common_end:
                observations.append(
                    HistoricalShadowObservation(
                        trader_id=parsed.trader_id,
                        signal_fingerprint=parsed.signal_fingerprint,
                        entry_at=parsed.entry_at,
                        exit_at=parsed.exit_at,
                    )
                )

    qualification = evaluate_historical_shadow_population(
        tuple(observations)
    )
    if {item.trader_id for item in observations} != set(
        PHASE19_REQUIRED_TRADERS
    ):
        raise ValueError("historical shadow lineage population drift")

    payload: dict[str, object] = {
        "schema": "qore.cibo.phase20d.historical-shadow-1y.v1",
        "policy_id": POLICY_ID,
        "shadow_candidate_id": SHADOW_CANDIDATE_ID,
        "evidence_kind": EVIDENCE_KIND,
        "status": "PASS" if qualification.passed else "FAIL",
        "qualification": _canonical(asdict(qualification)),
        "chronology": {
            "phase19_report_sha256": _sha256(chronology),
            "common_window": common,
            "total_common_window_rows": chronology[
                "total_common_window_rows"
            ],
            "max_concurrent_positions": chronology[
                "max_concurrent_positions"
            ],
            "cross_trader_overlapping_pairs": chronology[
                "cross_trader_overlapping_pairs"
            ],
            "multi_trader_entry_days": chronology[
                "multi_trader_entry_days"
            ],
        },
        "source_evidence": {
            key: {
                "trader_id": spec.trader_id.value,
                "artifact_id": spec.artifact_id,
                "artifact_digest": spec.artifact_digest,
            }
            for key, spec in SOURCE_SPECS.items()
        },
        "policy_invariants": policy_invariants(),
        "phase20d_population_gate": {
            "status": "PASS" if qualification.passed else "FAIL",
            "physical_28_day_wait_satisfied_by_shadow": qualification.passed,
            "eligible_to_continue_to_provider_aware_phase21_gates": (
                qualification.passed
            ),
            "selected_usd_economic_outcomes_deferred": True,
            "provider_execution_economics_deferred": True,
        },
        "final_holdout": {
            "candidate_id": "CIBO_USD60_6M_HOLDOUT_2017H1_V1",
            "outcomes_inspected": False,
            "market_data_read": False,
            "status": "SEALED_UNTOUCHED",
        },
        "governance": {
            "historical_shadow_consumed": True,
            "burned_research_reuse_authorized": True,
            "evidence_relabelled_forward_observed": False,
            "provider_economics_fabricated": False,
            "outcome_aware_refit_performed": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--chronology-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {key: getattr(args, key) for key in SOURCE_SPECS}
    report = consume(
        paths=paths,
        chronology_output=args.chronology_output,
        output=args.output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
