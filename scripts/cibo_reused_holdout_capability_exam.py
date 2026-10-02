"""CLI for the repeatable reused-holdout CIBO infrastructure exam."""

from __future__ import annotations

import argparse
import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_phase22_v4_execution_inputs import (
    load_phase22_sealed_fresh_batch,
    load_phase22_sealed_provider_numeric,
)
from qore.infrastructure.cibo_phase22_v4_historical_regime import (
    PHASE22_REGIME_SYMBOLS,
    load_phase22_historical_regime_corpora,
)
from qore.infrastructure.cibo_reused_holdout_capability_exam import (
    run_reused_holdout_infrastructure_exam,
)
from qore.infrastructure.cibo_usd60_capability_certification import (
    assess_cibo_capability_economic_certification,
    build_cibo_usd60_capability_certification_receipt,
)
from qore.infrastructure.cibo_usd60_dual_objective_exam import (
    assess_cibo_usd60_dual_objective_exam,
)


def _json_object(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw


def _source_roots(values: list[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        symbol, sep, raw_path = value.partition("=")
        if not sep or not symbol or not raw_path:
            raise ValueError("source root must be SYMBOL=PATH")
        if symbol in parsed:
            raise ValueError(f"duplicate source root: {symbol}")
        parsed[symbol] = Path(raw_path)
    if set(parsed) != set(PHASE22_REGIME_SYMBOLS):
        raise ValueError("exact five regime source roots required")
    return parsed


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--provider-numeric", type=Path, required=True)
    parser.add_argument("--provider-numeric-freeze-sha256", required=True)
    parser.add_argument("--source-root", action="append", required=True)
    parser.add_argument("--replay-started-at", required=True)
    parser.add_argument("--integrated-git-sha", required=True)
    parser.add_argument("--workflow-run-id", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    batch_raw = _json_object(args.batch)
    if batch_raw.get("validation_mode") != "NON_CERTIFYING_REUSED_HOLDOUT":
        raise ValueError("capability exam requires reused-holdout validation batch")
    if batch_raw.get("scientific_freshness_claimed") is not False:
        raise ValueError("capability exam cannot claim scientific freshness")

    fresh = load_phase22_sealed_fresh_batch(batch_raw)
    provider = load_phase22_sealed_provider_numeric(
        _json_object(args.provider_numeric)
    )
    corpora = load_phase22_historical_regime_corpora(
        _source_roots(args.source_root)
    )
    report, execution = run_reused_holdout_infrastructure_exam(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=(
            args.provider_numeric_freeze_sha256
        ),
        corpora=corpora,
        replay_started_at=datetime.fromisoformat(args.replay_started_at),
    )
    dual_objective = assess_cibo_usd60_dual_objective_exam(report)
    capability_receipt = build_cibo_usd60_capability_certification_receipt(
        report=report,
        integrated_git_sha=args.integrated_git_sha,
        workflow_run_id=args.workflow_run_id,
        qualified_at=datetime.now().astimezone(),
    )
    economic_decision = assess_cibo_capability_economic_certification(
        capability_receipt
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "capability-exam-report.json").write_text(
        json.dumps(report.payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "execution-report.json").write_text(
        json.dumps(_canonical(execution), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "tool-audit.json").write_text(
        json.dumps(
            [_canonical(item) for item in report.tool_audit],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "usd60-dual-objective-exam.json").write_text(
        json.dumps(
            _canonical(dual_objective),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "usd60-capability-certification-receipt.json").write_text(
        json.dumps(capability_receipt.payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "usd60-capability-economic-certification.json").write_text(
        json.dumps(economic_decision.payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "exam_sha256": report.fingerprint(),
                "infrastructure_certified": report.infrastructure_certified,
                "usd60_survival_passed": dual_objective.survival.passed,
                "maximum_capability_passed": (
                    dual_objective.maximum_capability.passed
                ),
                "dual_objective_status": dual_objective.status.value,
                "survival_blockers": list(dual_objective.survival.blockers),
                "maximum_capability_blockers": list(
                    dual_objective.maximum_capability.blockers
                ),
                "baseline_ending_capital_usd": format(
                    report.minimal_seed_baseline.ending_capital_usd, "f"
                ),
                "full_cibo_ending_capital_usd": format(
                    report.full_cibo.ending_capital_usd, "f"
                ),
                "not_integrated_tools": [
                    item.tool_code
                    for item in report.tool_audit
                    if item.status.value == "NOT_INTEGRATED"
                ],
                "scientific_freshness_claimed": False,
                "capability_certification_receipt_sha256": (
                    capability_receipt.fingerprint()
                ),
                "capability_economic_certification": (
                    economic_decision.status.value
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
