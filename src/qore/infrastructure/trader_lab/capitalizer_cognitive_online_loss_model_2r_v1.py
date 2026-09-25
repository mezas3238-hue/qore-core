"""Online loss-risk model layered on the causal position-mode learner.

The model is deliberately prequential:
- features are available at entry;
- labels are incorporated only after an accepted trade has closed;
- blocked trades never reveal their labels to the learner;
- the current trade's outcome and unchosen mode outcomes remain hidden.

A deterministic hashed logistic learner estimates loss risk.  The prediction can
route the trade to stronger causal M3 protection and, in explicit variants, can
abstain only when the predicted loss risk is high and the already-realized path
is WATCH/DEFENSIVE.

This is consumed-window research. Threshold variants are fixed hypotheses, not
retrospectively optimized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_online_causal_memory_2r_v1 as causal_memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_position_mode_bandit_2r_v1 as bandit,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_stability_intelligence_2r_v1 as stability,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_m3_stop_protection_true_2r_v2 as m3,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_ONLINE_LOSS_MODEL_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_M3_RUN_ID = 36177149363
SOURCE_M3_SHA = "2d3cb599a9a6eb5566a7374e17317a43d4d6a6b0"
EXPECTED_TRADES = 948
HASH_DIM = 4096
BASE_LR = 0.08
L2 = 0.0005
MIN_TRAINED = 60

POLICIES = (
    "MODEL_MODE_ONLY",
    "BANDIT_MODEL_ROUTE",
    "BANDIT_GATE_075_GLOBAL",
    "BANDIT_GATE_070_WATCH",
    "BANDIT_GATE_065_DEFENSIVE",
)


@dataclass(frozen=True, slots=True)
class ModelDecision:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    policy: str
    stability_state: str
    predicted_loss_probability: str
    trained_examples: int
    bandit_mode: str
    selected_mode: str
    accepted: bool
    reason: str
    current_outcome_visible_to_decision: bool = False
    blocked_outcome_visible_to_model: bool = False
    unchosen_counterfactual_visible_to_model: bool = False


class OnlineLogistic:
    def __init__(self) -> None:
        self.weights = [0.0] * HASH_DIM
        self.bias = 0.0
        self.updates = 0

    @staticmethod
    def _index(token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % HASH_DIM

    def predict(self, tokens: tuple[str, ...]) -> float:
        score = self.bias
        for token in tokens:
            score += self.weights[self._index(token)]
        score = max(-20.0, min(20.0, score))
        return 1.0 / (1.0 + math.exp(-score))

    def update(self, tokens: tuple[str, ...], *, label: float) -> None:
        prediction = self.predict(tokens)
        error = prediction - label
        lr = BASE_LR / math.sqrt(1.0 + self.updates / 50.0)
        self.bias -= lr * error
        for token in tokens:
            index = self._index(token)
            weight = self.weights[index]
            gradient = error + L2 * weight
            self.weights[index] = weight - lr * gradient
        self.updates += 1


def _model_tokens(row: dict[str, Any]) -> tuple[str, ...]:
    base = sorted(causal_memory._features(row))
    symbol = str(row["symbol"])
    session = str(row["session"])
    interactions: list[str] = []
    for token in base:
        if token.startswith(("MICRO=", "SLOT=", "PRIOR_REALIZED_SIGN=", "ACTIVE_POS=")):
            interactions.append(f"SYMBOL_X:{symbol}|{token}")
        if token.startswith(("MICRO=", "PRIOR_REALIZED_SIGN=", "PRIOR_CLOSED=")):
            interactions.append(f"SESSION_X:{session}|{token}")
    return tuple(("BIAS_FEATURE", *base, *sorted(interactions)))


def _loss_label(outcome: stability.TradeOutcome) -> float:
    return 1.0 if Decimal(outcome.realized_gross_r) < 0 else 0.0


def _route_mode(
    *,
    policy: str,
    prediction: float,
    bandit_mode: str,
) -> str:
    if policy == "MODEL_MODE_ONLY":
        if prediction >= 0.65:
            return m3.ProtectionMode.M3_SWING_IMPROVE.value
        if prediction >= 0.55:
            return m3.ProtectionMode.M3_PROFITABLE_SWING_LOCK.value
        return m3.ProtectionMode.ORIGINAL.value

    if prediction >= 0.65:
        return m3.ProtectionMode.M3_SWING_IMPROVE.value
    if prediction >= 0.55 and bandit_mode == m3.ProtectionMode.ORIGINAL.value:
        return m3.ProtectionMode.M3_PROFITABLE_SWING_LOCK.value
    return bandit_mode


def _admit(
    *,
    policy: str,
    prediction: float,
    trained: int,
    state: stability.StabilityState,
) -> tuple[bool, str]:
    if trained < MIN_TRAINED:
        return True, "MODEL_WARMUP"
    if policy == "BANDIT_GATE_075_GLOBAL" and prediction >= 0.75:
        return False, "PREDICTED_LOSS_GE_075"
    if (
        policy == "BANDIT_GATE_070_WATCH"
        and state is not stability.StabilityState.STABLE
        and prediction >= 0.70
    ):
        return False, "WATCH_DEFENSIVE_PREDICTED_LOSS_GE_070"
    if (
        policy == "BANDIT_GATE_065_DEFENSIVE"
        and state is stability.StabilityState.DEFENSIVE
        and prediction >= 0.65
    ):
        return False, "DEFENSIVE_PREDICTED_LOSS_GE_065"
    return True, "ALLOW"


def _simulate(
    *,
    policy: str,
    rows: tuple[dict[str, Any], ...],
    mode_ledgers: dict[str, tuple[stability.TradeOutcome, ...]],
) -> tuple[dict[str, Any], tuple[ModelDecision, ...]]:
    by_mode = {
        mode: {(item.symbol, item.entry_at): item for item in ledger}
        for mode, ledger in mode_ledgers.items()
    }
    row_by_key = {bandit._join_key(row): row for row in rows}
    if any(set(index) != set(row_by_key) for index in by_mode.values()):
        raise ValueError("online loss model rebase/mode identities differ")

    ordered_rows = tuple(
        sorted(
            rows,
            key=lambda row: (
                stability._aware(row["entry_at"], field="entry_at"),
                str(row["symbol"]),
            ),
        )
    )

    model = OnlineLogistic()
    accepted: list[stability.TradeOutcome] = []
    blocked_original: list[stability.TradeOutcome] = []
    updated: set[tuple[str, str]] = set()
    feature_by_key = {
        bandit._join_key(row): _model_tokens(row)
        for row in rows
    }
    selection_counts: Counter[tuple[str, str]] = Counter()
    decisions: list[ModelDecision] = []

    for row in ordered_rows:
        key = bandit._join_key(row)
        entry_at = stability._aware(row["entry_at"], field="entry_at")

        for prior in accepted:
            prior_key = (prior.symbol, prior.entry_at)
            if prior_key in updated:
                continue
            if stability._aware(prior.exit_at, field="exit_at") <= entry_at:
                model.update(
                    feature_by_key[prior_key],
                    label=_loss_label(prior),
                )
                updated.add(prior_key)

        closed_history = tuple(
            sorted(
                (
                    item
                    for item in accepted
                    if stability._aware(item.exit_at, field="exit_at") <= entry_at
                ),
                key=lambda item: (
                    stability._aware(item.exit_at, field="exit_at"),
                    item.symbol,
                ),
            )
        )
        state, _dd, _recent5, _loss_streak, _stop_streak = stability._state(
            closed_history
        )
        prediction = model.predict(feature_by_key[key])

        bandit_policy = (
            "SYMBOL_GREEDY_MEAN"
            if policy != "MODEL_MODE_ONLY"
            else "ORIGINAL_ONLY"
        )
        base_mode, _reason, _state2, _pressure, _means, _stops, _counts = (
            bandit._choose_mode(
                policy=bandit_policy,
                row=row,
                history=closed_history,
                selection_counts=selection_counts,
            )
        )
        selected_mode = _route_mode(
            policy=policy,
            prediction=prediction,
            bandit_mode=base_mode,
        )
        allow, reason = _admit(
            policy=policy,
            prediction=prediction,
            trained=model.updates,
            state=state,
        )

        if allow:
            outcome = by_mode[selected_mode][key]
            accepted.append(outcome)
            selection_counts[(str(row["symbol"]), selected_mode)] += 1
        else:
            blocked_original.append(by_mode[m3.ProtectionMode.ORIGINAL.value][key])

        decisions.append(
            ModelDecision(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=str(row["operating_date"]),
                entry_at=str(row["entry_at"]),
                policy=policy,
                stability_state=state.value,
                predicted_loss_probability=str(Decimal(str(prediction))),
                trained_examples=model.updates,
                bandit_mode=base_mode,
                selected_mode=selected_mode,
                accepted=allow,
                reason=reason,
            )
        )

    kept = tuple(accepted)
    blocked = tuple(blocked_original)
    control = mode_ledgers[m3.ProtectionMode.ORIGINAL.value]
    metrics = stability._metrics(kept)
    control_metrics = stability._metrics(control)
    blocked_metrics = stability._metrics(blocked)

    return {
        "policy": policy,
        "control_trades": len(control),
        "kept_trades": len(kept),
        "blocked_trades": len(blocked),
        "density_retention": str(Decimal(len(kept)) / Decimal(len(control))),
        "metrics": metrics,
        "control_metrics": control_metrics,
        "blocked_original_metrics": blocked_metrics,
        "blocked_stops": int(blocked_metrics["stops"]),
        "blocked_wins": int(blocked_metrics["wins"]),
        "trained_examples_final": model.updates,
        "mean_predicted_loss_probability": str(
            sum(
                (Decimal(item.predicted_loss_probability) for item in decisions),
                Decimal("0"),
            )
            / Decimal(len(decisions))
        ),
        "pf_at_least_control": (
            metrics["profit_factor"] is not None
            and control_metrics["profit_factor"] is not None
            and Decimal(str(metrics["profit_factor"]))
            >= Decimal(str(control_metrics["profit_factor"]))
        ),
        "total_r_at_least_control": (
            Decimal(str(metrics["total_r"]))
            >= Decimal(str(control_metrics["total_r"]))
        ),
        "dd_below_control": (
            Decimal(str(metrics["max_drawdown_r"]))
            < Decimal(str(control_metrics["max_drawdown_r"]))
        ),
        "current_outcome_visible_to_decision": False,
        "blocked_outcomes_visible_to_model": False,
        "unchosen_counterfactual_visible_to_model": False,
    }, tuple(decisions)


def build_report(
    rebase_root: Path,
    m3_root: Path,
) -> tuple[dict[str, Any], tuple[ModelDecision, ...]]:
    rebase_report, rows = stability._load_rebase(rebase_root)
    modes = {
        mode.value: stability._load_mode(m3_root, mode=mode.value)
        for mode in m3.ProtectionMode
    }

    results: list[dict[str, Any]] = []
    decisions: list[ModelDecision] = []
    for policy in POLICIES:
        result, audit = _simulate(
            policy=policy,
            rows=rows,
            mode_ledgers=modes,
        )
        results.append(result)
        decisions.extend(audit)

    pareto = tuple(
        row
        for row in results
        if row["pf_at_least_control"]
        and row["total_r_at_least_control"]
        and row["dd_below_control"]
    )
    dd6 = tuple(
        row
        for row in results
        if Decimal(str(row["metrics"]["max_drawdown_r"])) <= Decimal("6")
        and Decimal(str(row["density_retention"])) >= Decimal("0.90")
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_m3_run_id": SOURCE_M3_RUN_ID,
        "source_m3_sha": SOURCE_M3_SHA,
        "development_window_role": "PREQUENTIAL_CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(rows),
        "policy_count": len(POLICIES),
        "results": results,
        "pareto_improving_policy_count": len(pareto),
        "dd6_high_density_policy_count": len(dd6),
        "features_known_by_entry": True,
        "labels_revealed_only_after_accepted_trade_close": True,
        "blocked_outcomes_hidden_from_model": True,
        "unchosen_counterfactuals_hidden_from_model": True,
        "current_trade_outcome_visible_to_decision": False,
        "threshold_variants_outcome_tuned": False,
        "automatic_policy_selection": False,
        "runtime_rule_selected": False,
        "fresh_holdout_required_after_candidate_selection": True,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(rows)
        ),
        "strategy_rules_changed": False,
        "entry_geometry_changed": False,
        "original_stop_geometry_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FRESH_HOLDOUT_ONLINE_LOSS_MODEL"
            if pareto
            else "ADD_DESTINATION_AND_REGIME_FEATURE_BINDING_TO_MODEL"
        ),
    }, tuple(decisions)


def write_report(
    report: dict[str, Any],
    decisions: tuple[ModelDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-online-loss-model-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-online-loss-model-2r-v1-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in decisions:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("m3_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, decisions = build_report(args.rebase_root, args.m3_root)
    write_report(report, decisions, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
