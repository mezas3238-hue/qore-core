"""Derive conservative CE2I calibration evidence from burned Phase19 only."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

HOLDOUT_START = datetime(2017, 1, 1, tzinfo=UTC)
HOLDOUT_END = datetime(2017, 7, 1, tzinfo=UTC)


def _load(root: Path, name: str) -> dict[str, Any]:
    payload: object = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must contain a JSON object")
    return cast(dict[str, Any], payload)


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("calibration timestamps must be timezone-aware")
    return parsed


def _assert_no_holdout_overlap(start: str, end: str) -> None:
    left, right = _dt(start), _dt(end)
    if left < HOLDOUT_END and HOLDOUT_START < right:
        raise ValueError("fresh 2017H1 holdout cannot enter calibration")


def build_report(root: Path) -> dict[str, Any]:
    chronology = _load(root, "phase19-integrated-chronology-report.json")
    normalized = _load(root, "phase19-normalized-capital-mechanics.json")
    collisions = _load(root, "phase19-capital-collision-stress.json")
    wfo = _load(root, "phase19-causal-walk-forward.json")
    provider = _load(root, "phase19-provider-economics-inventory.json")

    common = chronology["common_window"]
    _assert_no_holdout_overlap(common["start"], common["end"])
    if chronology["total_common_window_rows"] != 855:
        raise ValueError("Phase19 population drift")
    if normalized["status"] != "NORMALIZED_CAPITAL_MECHANICS_BOUND_7_OF_7":
        raise ValueError("normalized capital mechanics not canonical")
    if normalized["capacity_breach_observed"] is not False:
        raise ValueError("capacity breach invalidates burned calibration")
    if int(normalized["accepted_opportunities"]) != 855:
        raise ValueError("normalized population coverage drift")
    if float(normalized["risk_capacity_minutes_ncu"]) <= 0:
        raise ValueError("capital-time evidence is required")
    if collisions["status"] != (
        "TRAIN_VALIDATION_CAPACITY_COLLISION_MEASURED_DESCRIPTIVE_ONLY"
    ):
        raise ValueError("collision train/validation evidence missing")
    for split in ("training", "validation"):
        scenarios = collisions[split]["capacity_scenarios"]
        if not scenarios:
            raise ValueError("capacity collision scenarios missing")
        if any(item["capacity_breach_observed"] for item in scenarios):
            raise ValueError("capacity breach in collision calibration")
    if wfo["status"] != "POST_FREEZE_FORWARD_VALIDATION_COMPLETE":
        raise ValueError("walk-forward evidence incomplete")
    if wfo["surviving_policy_count"] != 0:
        raise ValueError("unexpected policy-survival drift")
    if provider["status"] != "BLOCKED_PROVIDER_ECONOMICS":
        raise ValueError("Phase19 must not claim exact provider economics")

    promoted = {
        "T04": {
            "classification": "CALIBRATED_CAUSAL",
            "basis": (
                "train-only structural-R expectation per true structural "
                "stop-risk unit; USD risk-dollar economics excluded"
            ),
        },
        "T05": {
            "classification": "CALIBRATED_CAUSAL",
            "basis": (
                "burned chronological capital lifecycle proves release-before-"
                "reuse and forbids same-timestamp exit recycling without "
                "settlement evidence; incremental utility remains unvalidated"
            ),
        },
        "T06": {
            "classification": "CALIBRATED_CAUSAL",
            "basis": (
                "burned capital lifecycle plus settlement/source contracts "
                "freeze realized-profit-only expansion funding; multiplier "
                "and incremental utility remain unvalidated"
            ),
        },
        "T10": {
            "classification": "CALIBRATED_CAUSAL",
            "basis": (
                "train-only normalized capital-time with structural-R "
                "output; USD output per capital-hour excluded"
            ),
        },
        "T19": {
            "classification": "CALIBRATED_CAUSAL",
            "basis": (
                "burned concurrency plus durable reservation contracts prove "
                "reserve-before-deploy, source ownership and capacity "
                "conservation; incremental utility remains unvalidated"
            ),
        },
        "T20": {
            "classification": "CALIBRATED_CAUSAL",
            "basis": (
                "burned chronological lifecycle plus release contracts prove "
                "reconciled release-before-reuse and forbid premature release; "
                "incremental utility remains unvalidated"
            ),
        },
    }
    unavailable = {
        "T07": "verified protected economic floor unavailable",
        "T08": "dependence evidence remains descriptive/observational",
        "T09": "zero candidate policies survived both walk-forward folds",
        "T12": "temporal state evidence does not freeze regime boundaries",
        "T13": "zero reserve policies survived both walk-forward folds",
        "T14": (
            "no post-entry de-risk event population; capacity stress expresses "
            "entry rejection rather than open-position reduction"
        ),
        "T15": "optionality value not causally identified by this artifact",
        "T18": "zero allocation policies survived both walk-forward folds",
    }
    input_hashes = {}
    for name in (
        "phase19-integrated-chronology-report.json",
        "phase19-normalized-capital-mechanics.json",
        "phase19-capital-collision-stress.json",
        "phase19-causal-walk-forward.json",
        "phase19-provider-economics-inventory.json",
    ):
        input_hashes[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()

    return {
        "schema": "qore.cibo.phase19.burned_calibration.v1",
        "status": "BURNED_CAUSAL_CALIBRATION_COMPLETE",
        "calibration_source": "BURNED_PHASE19_ONLY",
        "holdout_2017h1_outcomes_used": False,
        "target_aware": False,
        "exact_usd_economics_claimed": False,
        "common_window": common,
        "population": {
            "opportunities": normalized["accepted_opportunities"],
            "risk_capacity_minutes_ncu": normalized["risk_capacity_minutes_ncu"],
            "max_drawdown_ncu": normalized["max_drawdown_ncu"],
            "capacity_breach_observed": normalized["capacity_breach_observed"],
        },
        "walk_forward": {
            "surviving_policy_count": wfo["surviving_policy_count"],
            "surviving_policy_ids": wfo["surviving_policy_ids"],
        },
        "promoted_tools": promoted,
        "calibration_unavailable": unavailable,
        "provider_economics_required": [
            "T01",
            "T03",
            "T04",
            "T07",
            "T10",
            "T11",
            "T16",
            "T17",
        ],
        "input_sha256": input_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase19-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.phase19_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
