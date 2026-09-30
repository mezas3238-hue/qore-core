"""Prequential cognitive-memory laboratory for V50 High-Frequency Scalper.

The purpose is to test whether Capitalizer cognition can improve V49 opportunity competition
without seeing the current/future outcome.

At each candidate:
1. reveal only causal V50 feature-atlas state;
2. update memory only with ACCEPTED trades whose exit time is already <= current entry;
3. apply one fixed cognitive policy;
4. if accepted and the session/day still has a MAX3 slot, consume one slot;
5. blocked outcomes remain invisible forever to the runtime memory.

The full outcomes are used only after simulation to score each policy. No winner is promoted
automatically and no holdout/certification claim is made.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_feature_atlas import (
    IDENTITY as ATLAS_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_feature_atlas import (
    V50CognitiveFeatureRow,
)

IDENTITY = "QORE_CAPITALIZER_V50_PREQUENTIAL_COGNITIVE_MEMORY"
POLICIES = (
    "BASELINE_FIRST3",
    "STRUCTURAL_COGNITION",
    "MEMORY_CONSENSUS_2",
    "MEMORY_CONSENSUS_3",
    "KNN_NEGATIVE",
    "STRUCTURAL_PLUS_HYBRID",
)

MIN_GLOBAL_HISTORY = 24
MIN_CELL_HISTORY = 10
PRIOR_STRENGTH = Decimal("12")
NEGATIVE_STOP_EDGE = Decimal("0.05")
KNN_MIN_HISTORY = 8
KNN_TOP_K = 15
KNN_MIN_SIMILARITY = Decimal("0.40")


@dataclass(frozen=True, slots=True)
class V50CognitiveDecisionAudit:
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    accepted: bool
    reason: str
    execution_slot: int | None
    closed_history: int
    mature_feature_count: int
    negative_feature_count: int
    knn_neighbors: int
    knn_mean_r: str | None
    knn_stop_rate: str | None
    structural_disposition: str
    current_outcome_visible_to_decision: bool = False
    blocked_outcome_visible_to_memory: bool = False

    def __post_init__(self) -> None:
        if self.current_outcome_visible_to_decision:
            raise ValueError("V50 prequential decision leaked current outcome")
        if self.blocked_outcome_visible_to_memory:
            raise ValueError("V50 prequential memory learned blocked outcome")


@dataclass(frozen=True, slots=True)
class V50RuntimeOutcome:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    exit_at: str
    realized_gross_r: Decimal
    exit_reason: str


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("V50 prequential timestamps must be timezone-aware")
    return parsed


def _load_rows(root: Path) -> tuple[V50CognitiveFeatureRow, ...]:
    paths = sorted(root.rglob("capitalizer-*-v50-cognitive-feature-atlas-rows.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V50 prequential lab requires 9 feature ledgers, got {len(paths)}")
    rows: list[V50CognitiveFeatureRow] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = V50CognitiveFeatureRow(**json.loads(line))
                if row.identity != ATLAS_IDENTITY:
                    raise ValueError("unexpected V50 feature atlas identity")
                rows.append(row)
    return tuple(
        sorted(
            rows,
            key=lambda row: (_aware(row.entry_at), row.symbol, row.trigger_family),
        )
    )


def _count_bucket(value: int) -> str:
    if value <= 1:
        return "1"
    if value == 2:
        return "2"
    if value == 3:
        return "3"
    if value <= 6:
        return "4_6"
    return "7_PLUS"


def _ratio_bucket(value: str | None) -> str:
    if value is None:
        return "UNAVAILABLE"
    ratio = Decimal(value)
    if ratio < Decimal("0.25"):
        return "LT_025"
    if ratio < Decimal("0.50"):
        return "025_050"
    if ratio < Decimal("0.75"):
        return "050_075"
    return "GE_075"


def _features(
    row: V50CognitiveFeatureRow,
    *,
    execution_slot: int,
) -> frozenset[str]:
    base = {
        token
        for token in row.observation_tokens
        if not token.startswith("SLOT=")
    }
    base.update(
        {
            f"EXECUTION_SLOT={execution_slot}",
            (
                "RAW_CANDIDATE_ORDINAL="
                f"{_count_bucket(row.candidate_ordinal_in_session_day)}"
            ),
            f"STRUCTURAL_DISPOSITION={row.structural_disposition}",
            (
                "TARGET_COUNT="
                f"{_count_bucket(row.target_candidate_count)}"
            ),
            f"TARGET_HAS_1R={row.target_has_one_r}",
            f"TARGET_HAS_2R={row.target_has_two_r}",
            f"EXEC_STOP_AVAILABLE={row.execution_stop_available}",
            (
                "EXEC_VS_THESIS="
                f"{_ratio_bucket(row.execution_vs_thesis_ratio)}"
            ),
        }
    )
    return frozenset(base)


def _runtime_outcome(row: V50CognitiveFeatureRow) -> V50RuntimeOutcome:
    return V50RuntimeOutcome(
        symbol=row.symbol,
        session=row.session,
        operating_date=row.operating_date,
        entry_at=row.entry_at,
        exit_at=row.exit_at,
        realized_gross_r=Decimal(row.realized_gross_r),
        exit_reason=row.exit_reason,
    )


def _history_stats(history: tuple[V50RuntimeOutcome, ...]) -> tuple[Decimal, Decimal]:
    values = tuple(item.realized_gross_r for item in history)
    mean_r = sum(values, Decimal("0")) / Decimal(len(values))
    stop_rate = Decimal(sum(item.exit_reason == "STOP" for item in history)) / Decimal(
        len(history)
    )
    return mean_r, stop_rate


def _feature_cells(
    *,
    features: frozenset[str],
    history: tuple[V50RuntimeOutcome, ...],
    feature_by_key: dict[tuple[str, str], frozenset[str]],
    global_mean: Decimal,
    global_stop: Decimal,
) -> tuple[tuple[Decimal, Decimal, int, str], ...]:
    result: list[tuple[Decimal, Decimal, int, str]] = []
    for feature in sorted(features):
        selected = tuple(
            item
            for item in history
            if feature in feature_by_key[(item.symbol, item.entry_at)]
        )
        if len(selected) < MIN_CELL_HISTORY:
            continue
        values = tuple(item.realized_gross_r for item in selected)
        stops = sum(item.exit_reason == "STOP" for item in selected)
        denominator = PRIOR_STRENGTH + Decimal(len(selected))
        posterior_mean = (
            PRIOR_STRENGTH * global_mean + sum(values, Decimal("0"))
        ) / denominator
        posterior_stop = (
            PRIOR_STRENGTH * global_stop + Decimal(stops)
        ) / denominator
        result.append((posterior_mean, posterior_stop, len(selected), feature))
    return tuple(result)


def _knn(
    *,
    current: frozenset[str],
    history: tuple[V50RuntimeOutcome, ...],
    feature_by_key: dict[tuple[str, str], frozenset[str]],
) -> tuple[int, Decimal | None, Decimal | None]:
    neighbors: list[tuple[Decimal, V50RuntimeOutcome]] = []
    for item in history:
        prior = feature_by_key[(item.symbol, item.entry_at)]
        union = len(current | prior)
        if union == 0:
            continue
        similarity = Decimal(len(current & prior)) / Decimal(union)
        if similarity >= KNN_MIN_SIMILARITY:
            neighbors.append((similarity, item))
    neighbors.sort(
        key=lambda pair: (pair[0], _aware(pair[1].exit_at)),
        reverse=True,
    )
    chosen = tuple(item for _, item in neighbors[:KNN_TOP_K])
    if len(chosen) < KNN_MIN_HISTORY:
        return len(chosen), None, None
    return len(chosen), *_history_stats(chosen)


def _metrics(rows: tuple[V50RuntimeOutcome, ...]) -> dict[str, Any]:
    ordered = tuple(
        sorted(rows, key=lambda row: (_aware(row.exit_at), _aware(row.entry_at), row.symbol))
    )
    values = tuple(row.realized_gross_r for row in ordered)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    losing = 0
    max_losing = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            losing += 1
            max_losing = max(max_losing, losing)
        else:
            losing = 0
    total = sum(values, Decimal("0"))
    return {
        "trades": len(rows),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(row.exit_reason == "STOP" for row in rows),
        "targets": sum(row.exit_reason == "TARGET" for row in rows),
        "total_r": str(total),
        "expectancy_r": None if not rows else str(total / Decimal(len(rows))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_losing,
    }


def _simulate(
    *,
    policy: str,
    rows: tuple[V50CognitiveFeatureRow, ...],
) -> tuple[dict[str, Any], tuple[V50CognitiveDecisionAudit, ...]]:
    accepted: list[V50RuntimeOutcome] = []
    blocked_for_diagnostics: list[V50RuntimeOutcome] = []
    feature_by_key: dict[tuple[str, str], frozenset[str]] = {}
    slots: Counter[tuple[str, str]] = Counter()
    decisions: list[V50CognitiveDecisionAudit] = []

    for row in rows:
        key_session = (row.session, row.operating_date)
        execution_slot = slots[key_session] + 1
        if execution_slot > 3:
            blocked_for_diagnostics.append(_runtime_outcome(row))
            decisions.append(
                V50CognitiveDecisionAudit(
                    policy=policy,
                    symbol=row.symbol,
                    session=row.session,
                    operating_date=row.operating_date,
                    entry_at=row.entry_at,
                    accepted=False,
                    reason="MAX3_SESSION_BUDGET_EXHAUSTED",
                    execution_slot=None,
                    closed_history=0,
                    mature_feature_count=0,
                    negative_feature_count=0,
                    knn_neighbors=0,
                    knn_mean_r=None,
                    knn_stop_rate=None,
                    structural_disposition=row.structural_disposition,
                )
            )
            continue

        entry_at = _aware(row.entry_at)
        closed_history = tuple(
            item for item in accepted if _aware(item.exit_at) <= entry_at
        )
        features = _features(row, execution_slot=execution_slot)

        # Candidate features may enter memory only if the candidate is accepted.
        global_mean: Decimal | None = None
        global_stop: Decimal | None = None
        cells: tuple[tuple[Decimal, Decimal, int, str], ...] = ()
        negative: tuple[tuple[Decimal, Decimal, int, str], ...] = ()
        knn_n = 0
        knn_mean: Decimal | None = None
        knn_stop: Decimal | None = None
        if len(closed_history) >= MIN_GLOBAL_HISTORY:
            global_mean, global_stop = _history_stats(closed_history)
            cells = _feature_cells(
                features=features,
                history=closed_history,
                feature_by_key=feature_by_key,
                global_mean=global_mean,
                global_stop=global_stop,
            )
            negative = tuple(
                cell
                for cell in cells
                if cell[0] < 0
                and cell[1] >= global_stop + NEGATIVE_STOP_EDGE
            )
            knn_n, knn_mean, knn_stop = _knn(
                current=features,
                history=closed_history,
                feature_by_key=feature_by_key,
            )

        knn_negative = (
            knn_n >= KNN_MIN_HISTORY
            and knn_mean is not None
            and knn_stop is not None
            and global_stop is not None
            and knn_mean < 0
            and knn_stop >= global_stop + NEGATIVE_STOP_EDGE
        )

        allow = True
        reason = "COGNITIVE_ALLOW"
        structural_pass = row.structural_disposition == "PASS_TO_COMPETITION"
        if policy == "STRUCTURAL_COGNITION":
            allow = structural_pass
            reason = "STRUCTURAL_PASS" if allow else "STRUCTURAL_NOT_READY"
        elif policy == "MEMORY_CONSENSUS_2":
            allow = len(negative) < 2
            reason = "NEGATIVE_MEMORY_CONSENSUS_2" if not allow else reason
        elif policy == "MEMORY_CONSENSUS_3":
            allow = len(negative) < 3
            reason = "NEGATIVE_MEMORY_CONSENSUS_3" if not allow else reason
        elif policy == "KNN_NEGATIVE":
            allow = not knn_negative
            reason = "KNN_NEGATIVE_MEMORY" if not allow else reason
        elif policy == "STRUCTURAL_PLUS_HYBRID":
            allow = structural_pass and not (len(negative) >= 3 and knn_negative)
            if not structural_pass:
                reason = "STRUCTURAL_NOT_READY"
            elif not allow:
                reason = "STRUCTURAL_PLUS_NEGATIVE_MEMORY"
        elif policy != "BASELINE_FIRST3":
            raise ValueError(f"unknown V50 cognitive policy: {policy}")

        outcome = _runtime_outcome(row)
        if allow:
            accepted.append(outcome)
            feature_by_key[(outcome.symbol, outcome.entry_at)] = features
            slots[key_session] += 1
        else:
            blocked_for_diagnostics.append(outcome)

        decisions.append(
            V50CognitiveDecisionAudit(
                policy=policy,
                symbol=row.symbol,
                session=row.session,
                operating_date=row.operating_date,
                entry_at=row.entry_at,
                accepted=allow,
                reason=reason,
                execution_slot=execution_slot if allow else None,
                closed_history=len(closed_history),
                mature_feature_count=len(cells),
                negative_feature_count=len(negative),
                knn_neighbors=knn_n,
                knn_mean_r=None if knn_mean is None else str(knn_mean),
                knn_stop_rate=None if knn_stop is None else str(knn_stop),
                structural_disposition=row.structural_disposition,
            )
        )

    kept = tuple(accepted)
    blocked = tuple(blocked_for_diagnostics)
    return {
        "policy": policy,
        "kept_metrics": _metrics(kept),
        "blocked_diagnostic_metrics": _metrics(blocked) if blocked else None,
        "candidate_count": len(rows),
        "kept_trades": len(kept),
        "density_retention_vs_candidates": str(Decimal(len(kept)) / Decimal(len(rows))),
        "session_days_used": len({(item.session, item.operating_date) for item in kept}),
        "current_outcome_visible_to_decision": False,
        "blocked_outcomes_visible_to_runtime_memory": False,
        "automatic_rule_promotion": False,
    }, tuple(decisions)


def build_report(
    root: Path,
) -> tuple[dict[str, Any], tuple[V50CognitiveDecisionAudit, ...]]:
    rows = _load_rows(root)
    results: list[dict[str, Any]] = []
    audits: list[V50CognitiveDecisionAudit] = []
    for policy in POLICIES:
        result, decision_rows = _simulate(policy=policy, rows=rows)
        results.append(result)
        audits.extend(decision_rows)

    baseline = next(row for row in results if row["policy"] == "BASELINE_FIRST3")
    baseline_pf = baseline["kept_metrics"]["profit_factor"]
    baseline_total = Decimal(str(baseline["kept_metrics"]["total_r"]))
    baseline_dd = Decimal(str(baseline["kept_metrics"]["max_drawdown_r"]))

    improving = tuple(
        row
        for row in results
        if row["policy"] != "BASELINE_FIRST3"
        and row["kept_metrics"]["profit_factor"] is not None
        and baseline_pf is not None
        and Decimal(str(row["kept_metrics"]["profit_factor"])) > Decimal(str(baseline_pf))
        and Decimal(str(row["kept_metrics"]["total_r"])) > baseline_total
        and Decimal(str(row["kept_metrics"]["max_drawdown_r"])) < baseline_dd
    )

    return {
        "identity": IDENTITY,
        "development_role": "CONSUMED_PREQUENTIAL_LABORATORY",
        "candidate_rows": len(rows),
        "policy_count": len(POLICIES),
        "policies": results,
        "baseline_policy": "BASELINE_FIRST3",
        "multi_axis_improving_policy_count": len(improving),
        "multi_axis_improving_policies": [row["policy"] for row in improving],
        "features_known_by_entry": True,
        "labels_revealed_only_after_accepted_trade_close": True,
        "current_trade_outcome_visible_to_decision": False,
        "blocked_outcomes_visible_to_runtime_memory": False,
        "reserved_holdout_reopened": False,
        "fresh_holdout_used": False,
        "automatic_policy_selection": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[V50CognitiveDecisionAudit, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-v50-prequential-cognitive-memory.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / "capitalizer-v50-prequential-cognitive-memory-decisions.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(args.input_root)
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
