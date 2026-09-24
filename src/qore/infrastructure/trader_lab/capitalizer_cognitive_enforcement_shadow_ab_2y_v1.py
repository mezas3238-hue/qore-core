"""Shadow A/B: force the frozen Capitalizer fast brain onto the frozen 1R trade set.

This probe changes no strategy, entry, stop, target, MAX3, cognition rule, or runtime.
It answers one narrow question: what happens if the current economic candidates must
receive an EXECUTE decision from the already-frozen top-level cognitive engine?

The gate sees pre-trade fields only. Terminal outcomes are attached after the decision
solely for counterfactual accounting. Missing cognitive evidence is not invented:
calibrated evidence remains UNKNOWN and unavailable execution evidence remains
DEGRADED, which exercises the existing fail-closed semantics exactly as written.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cognitive_engine import (
    evaluate_capitalizer,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerDecision,
    CapitalizerSession,
    EvidenceStrength,
    ExecutionQuality,
    MarketState,
)
from qore.infrastructure.trader_lab.capitalizer_governor import (
    CapitalizerPortfolioState,
)
from qore.infrastructure.trader_lab.capitalizer_max_recovery_target_sensitivity_2y_v1 import (
    TargetOutcome,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerExecutionState,
    CapitalizerSituationModel,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_ENFORCEMENT_SHADOW_AB_2Y_V1"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"
EXPECTED_CONTROL_TRADES = 948
TARGET_R = Decimal("1.00")


@dataclass(frozen=True, slots=True)
class PreTradeCandidate:
    symbol: str
    session: CapitalizerSession
    operating_date: str
    observed_at: datetime
    hypothesis_id: str
    source_event_id: str


@dataclass(frozen=True, slots=True)
class CognitiveShadowRow:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    decision: str
    reasons: tuple[str, ...]
    adversarial_findings: tuple[str, ...]
    original_exit_reason: str
    original_realized_gross_r: str
    original_provenance: str


def _load_target1(root: Path) -> tuple[TargetOutcome, ...]:
    paths = sorted(root.rglob(
        "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl"
    ))
    if len(paths) != 1:
        raise ValueError(f"cognitive shadow requires one frozen 1R ledger, got {len(paths)}")
    rows: list[TargetOutcome] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                item = TargetOutcome(**json.loads(line))
                if Decimal(item.target_r) != TARGET_R:
                    raise ValueError("cognitive shadow received non-1R outcome")
                rows.append(item)
    ordered = tuple(sorted(
        rows,
        key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
    ))
    if len(ordered) != EXPECTED_CONTROL_TRADES:
        raise ValueError("cognitive shadow control-trade count mismatch")
    return ordered


def _pretrade(item: TargetOutcome) -> PreTradeCandidate:
    observed_at = datetime.fromisoformat(item.entry_at)
    stable = (
        f"{item.symbol}:{item.session}:{item.operating_date}:"
        f"{item.h1_open}:{item.entry_at}:{item.provenance}"
    )
    return PreTradeCandidate(
        symbol=item.symbol,
        session=CapitalizerSession(item.session),
        operating_date=item.operating_date,
        observed_at=observed_at,
        hypothesis_id=f"H:{stable}",
        source_event_id=f"SRC:{stable}",
    )


def _situation(candidate: PreTradeCandidate) -> CapitalizerSituationModel:
    # Facts inherited from the already-admitted frozen strategy candidate:
    # trigger/displacement are present. No additional cognitive calibration,
    # execution-quality proof, destination intelligence, contradiction state,
    # correlation state, or failure fingerprint is fabricated here.
    return CapitalizerSituationModel(
        symbol=candidate.symbol,
        session=candidate.session,
        observed_at=candidate.observed_at,
        hypothesis_id=candidate.hypothesis_id,
        source_event_id=candidate.source_event_id,
        event_generation=1,
        market_state=MarketState.DISPLACEMENT,
        evidence_strength=EvidenceStrength.UNKNOWN,
        execution=CapitalizerExecutionState(
            spread_points=Decimal("0"),
            commission_cost_r=Decimal("0"),
            expected_slippage_r=Decimal("0"),
            quote_age_ms=0,
            observed_latency_ms=0,
            quality=ExecutionQuality.DEGRADED,
        ),
        strategy_trigger_ready=True,
        displacement_confirmed=True,
        destination_available=True,
        late_entry=False,
        correlated_exposure_blocked=False,
        contradictions=(),
        observations=(),
        failure_state_fingerprint=None,
    )


def _metrics(rows: tuple[CognitiveShadowRow, ...]) -> dict[str, Any]:
    values = tuple(Decimal(item.original_realized_gross_r) for item in rows)
    if not values:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "stops": 0,
            "total_r": "0",
            "profit_factor": None,
        }
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    return {
        "trades": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(item.original_exit_reason == "STOP" for item in rows),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
    }


def build_report(root: Path) -> tuple[dict[str, Any], tuple[CognitiveShadowRow, ...]]:
    control = _load_target1(root)
    ledgers: dict[tuple[str, CapitalizerSession], CapitalizerSessionLedger] = {}
    result: list[CognitiveShadowRow] = []

    for item in control:
        candidate = _pretrade(item)
        key = (candidate.operating_date, candidate.session)
        ledger = ledgers.setdefault(
            key,
            CapitalizerSessionLedger(candidate.session),
        )
        evaluation = evaluate_capitalizer(
            situation=_situation(candidate),
            ledger=ledger,
            loss_memory=CapitalizerLossMemory(),
            portfolio_state=CapitalizerPortfolioState(),
        )
        ledgers[key] = evaluation.ledger_after
        result.append(
            CognitiveShadowRow(
                symbol=item.symbol,
                session=item.session,
                operating_date=item.operating_date,
                entry_at=item.entry_at,
                decision=evaluation.final_decision.value,
                reasons=evaluation.reasoning.reasons,
                adversarial_findings=evaluation.reasoning.adversarial_findings,
                original_exit_reason=item.exit_reason,
                original_realized_gross_r=item.realized_gross_r,
                original_provenance=item.provenance,
            )
        )

    rows = tuple(result)
    decision_counts = Counter(item.decision for item in rows)
    execute = tuple(item for item in rows if item.decision == CapitalizerDecision.EXECUTE.value)
    wait = tuple(item for item in rows if item.decision == CapitalizerDecision.WAIT.value)
    abstain = tuple(item for item in rows if item.decision == CapitalizerDecision.ABSTAIN.value)

    by_reason: Counter[str] = Counter()
    for shadow_row in rows:
        by_reason.update(shadow_row.reasons)

    by_original_exit: dict[str, Counter[str]] = defaultdict(Counter)
    for shadow_row in rows:
        by_original_exit[shadow_row.original_exit_reason][shadow_row.decision] += 1

    report = {
        "identity": IDENTITY,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "control_trades": len(control),
        "target_r": str(TARGET_R),
        "decision_counts": dict(decision_counts),
        "reason_counts": dict(by_reason),
        "original_exit_by_cognitive_decision": {
            key: dict(value) for key, value in sorted(by_original_exit.items())
        },
        "control_metrics": _metrics(tuple(
            CognitiveShadowRow(
                symbol=item.symbol,
                session=item.session,
                operating_date=item.operating_date,
                entry_at=item.entry_at,
                decision="CONTROL",
                reasons=(),
                adversarial_findings=(),
                original_exit_reason=item.exit_reason,
                original_realized_gross_r=item.realized_gross_r,
                original_provenance=item.provenance,
            )
            for item in control
        )),
        "execute_metrics": _metrics(execute),
        "wait_counterfactual_metrics": _metrics(wait),
        "abstain_counterfactual_metrics": _metrics(abstain),
        "existing_cognitive_engine_used": True,
        "cognitive_rules_changed": False,
        "strategy_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "new_numeric_thresholds_added": False,
        "outcome_visible_to_gate": False,
        "missing_evidence_fabricated": False,
        "calibrated_evidence_bound": False,
        "execution_quality_evidence_bound": False,
        "loss_failure_fingerprint_bound": False,
        "cross_market_exposure_bound": False,
        "destination_intelligence_bound": False,
        "interpretation": (
            "CONNECTIVITY_PROBE_ONLY: measures current cognition when forced onto "
            "the frozen economic trade set without inventing missing cognitive evidence."
        ),
        "development_window_role": "CONSUMED_LABORATORY",
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[CognitiveShadowRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-enforcement-shadow-ab-2y-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / "capitalizer-cognitive-enforcement-shadow-ab-2y-v1-rows.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(args.input_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()