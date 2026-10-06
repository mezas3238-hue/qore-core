"""VT31 NAS100 Comparator-011 Breaker Deep-Giveback composition V1.

Consumed development evidence only. Fresh Holdout remains sealed.

Frozen base:
    VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR

Single predeclared delta:
- for a Breaker still pre-DOL1, permit one next-M1 structural stop improvement
  only when the already-supported conservative Deep Giveback witness is true:
  observed MFE >= 1.50R, peak-close giveback >= 1.00R, current close <= +0.25R,
  recent closed-M1 path efficiency <= 0.10, a confirmed M1 protective swing
  exists, and maximum cognition is verified.

No threshold search is performed. No future outcome, fold/date identity, sizing,
leverage, compounding, portfolio, volume, equity or capital state may influence
an action.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_breaker_mixed_weak_efficiency_adverse_exit_v1 as weak
import vt31_nas100_bullish_h1_mid_confirmation_conflict_admission_v1 as mid
import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_live_cognitive_breaker_protection_frontier_v1 as live_cognition
import vt31_nas100_rapid_breaker_conflict_admission_frontier_v1 as rapid
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp011.breaker_deep_giveback_composition.v1"
BASE_COMPARATOR_ID = "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
VARIANT_ID = "VT31_AB_COMP011_BREAKER_DEEP_GIVEBACK_025"
# Frozen from the previously adjudicated DGR_CURRENT_CLOSE_MAX_0_25 witness.
# Keep these local: the historical DGR research module mutates global Decimal
# precision at import time, which would contaminate Comparator-009 exact
# development bindings in this final metric harness.
DGR_MIN_MFE_R = Decimal("1.5")
DGR_MIN_CLOSE_GIVEBACK_R = Decimal("1.0")
DGR_MAX_PATH_EFFICIENCY = Decimal("0.10")
DGR_CURRENT_CLOSE_MAX_R = Decimal("0.25")


def _d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite decimal")
    return result


def _r_from_price(
    price: Decimal,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    if side == "long":
        return (price - entry) / risk
    if side == "short":
        return (entry - price) / risk
    raise ValueError(side)


def _path_efficiency(
    bars: list[object],
    *,
    side: str,
) -> Decimal | None:
    if len(bars) < 2:
        return None
    closes = [_d(bar.close) for bar in bars]
    net = (
        closes[-1] - closes[0]
        if side == "long"
        else closes[0] - closes[-1]
    )
    gross = sum(
        (
            abs(right - left)
            for left, right in zip(closes, closes[1:], strict=False)
        ),
        Decimal(0),
    )
    return None if gross <= 0 else net / gross


def _dgr_features(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    observation_at: datetime,
) -> dict[str, Decimal | None]:
    side = str(executable.side.value)
    entry = _d(executable.entry_price)
    initial_stop = _d(executable.stop_price)
    risk = abs(entry - initial_stop)
    if risk <= 0:
        raise ValueError("invalid initial risk")

    fill_index = v2b._fill_index(day_bars, executable)
    if fill_index is None:
        raise ValueError("DGR observation requires a filled trade")

    eligible = tuple(
        bar
        for bar in day_bars[fill_index:]
        if specialist.baseline._local_minute(bar)
        < specialist.LIFECYCLE_MINUTE
    )
    # Match the established DGR path semantics: the fill bar establishes the
    # position; deterioration evidence begins with the following closed M1.
    observed = [
        bar
        for bar in eligible[1:]
        if cast(datetime, bar.closed_at) <= observation_at
    ]
    if not observed:
        return {
            "mfe_r": None,
            "current_close_r": None,
            "close_giveback_r": None,
            "path_efficiency": None,
        }

    close_rs = [
        _r_from_price(
            _d(bar.close),
            side=side,
            entry=entry,
            risk=risk,
        )
        for bar in observed
    ]
    current_close_r = close_rs[-1]
    peak_close_r = max(close_rs)
    favorable_prices = [
        _d(bar.high) if side == "long" else _d(bar.low)
        for bar in observed
    ]
    mfe_r = max(
        _r_from_price(
            price,
            side=side,
            entry=entry,
            risk=risk,
        )
        for price in favorable_prices
    )
    return {
        "mfe_r": mfe_r,
        "current_close_r": current_close_r,
        "close_giveback_r": max(
            Decimal(0),
            peak_close_r - current_close_r,
        ),
        "path_efficiency": _path_efficiency(
            observed[-5:],
            side=side,
        ),
    }


def _dgr_qualifies(
    features: dict[str, Decimal | None],
) -> bool:
    efficiency = features["path_efficiency"]
    return bool(
        features["mfe_r"] is not None
        and features["mfe_r"] >= DGR_MIN_MFE_R
        and features["close_giveback_r"] is not None
        and features["close_giveback_r"] >= DGR_MIN_CLOSE_GIVEBACK_R
        and features["current_close_r"] is not None
        and features["current_close_r"] <= DGR_CURRENT_CLOSE_MAX_R
        and efficiency is not None
        and efficiency <= DGR_MAX_PATH_EFFICIENCY
    )


def _simulate_candidate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
) -> dict[str, object]:
    cognitive_evaluations: list[dict[str, object]] = []
    dgr_evaluations: list[dict[str, object]] = []
    entry_family = str(executable.selected_family.value)
    reference_volatility_state = str(state["reference_volatility_state"])

    def exit_authorizer(
        bar: object,
        current_stop: Decimal,
    ) -> bool:
        observation_at = cast(datetime, bar.closed_at)
        _, diagnostic = live_cognition._live_cognitive_decision(
            day_bars=day_bars,
            executable=executable,
            state=state,
            observation_at=observation_at,
            current_stop=current_stop,
            candidate_stop=current_stop,
            confirmations=1,
            mode="WEAK_PATH",
        )
        base_allowed = adverse._exit_allowed(
            diagnostic,
            variant=rapid.POSITION_VARIANT,
            entry_family=entry_family,
            reference_volatility_state=reference_volatility_state,
        )
        weak_allowed = weak._extra_exit_allowed(
            diagnostic,
            entry_family=entry_family,
        )
        allowed = base_allowed or weak_allowed
        diagnostic["cognitive_exit_variant"] = VARIANT_ID
        diagnostic["cognitive_exit_authorized"] = allowed
        diagnostic["comp007_base_exit_authorized"] = base_allowed
        diagnostic["breaker_mixed_weak_efficiency_exit_authorized"] = (
            weak_allowed
        )
        cognitive_evaluations.append(diagnostic)
        return allowed

    def dgr_authorizer(
        bar: object,
        candidate_stop: Decimal,
        current_stop: Decimal,
    ) -> bool:
        observation_at = cast(datetime, bar.closed_at)
        features = _dgr_features(
            day_bars=day_bars,
            executable=executable,
            observation_at=observation_at,
        )
        _, diagnostic = live_cognition._live_cognitive_decision(
            day_bars=day_bars,
            executable=executable,
            state=state,
            observation_at=observation_at,
            current_stop=current_stop,
            candidate_stop=candidate_stop,
            confirmations=1,
            mode="WEAK_PATH",
        )
        maximum_cognition = (
            diagnostic.get("maximum_cognition_verified") is True
        )
        qualifies = (
            entry_family == "breaker"
            and maximum_cognition
            and _dgr_qualifies(features)
        )
        dgr_evaluations.append(
            {
                "observation_at": observation_at.isoformat(),
                "entry_family": entry_family,
                "maximum_cognition_verified": maximum_cognition,
                "candidate_stop": format(candidate_stop, "f"),
                "current_stop": format(current_stop, "f"),
                "mfe_r": (
                    None
                    if features["mfe_r"] is None
                    else format(cast(Decimal, features["mfe_r"]), "f")
                ),
                "current_close_r": (
                    None
                    if features["current_close_r"] is None
                    else format(
                        cast(Decimal, features["current_close_r"]),
                        "f",
                    )
                ),
                "close_giveback_r": (
                    None
                    if features["close_giveback_r"] is None
                    else format(
                        cast(Decimal, features["close_giveback_r"]),
                        "f",
                    )
                ),
                "recent_path_efficiency": (
                    None
                    if features["path_efficiency"] is None
                    else format(
                        cast(Decimal, features["path_efficiency"]),
                        "f",
                    )
                ),
                "dgr_authorized": qualifies,
            }
        )
        return qualifies

    outcome = composition._simulate_composite(
        day_bars,
        executable,
        state,
        window=adverse.WINDOW,
        pretarget_breaker_ps_confirmations=1,
        pretarget_breaker_ps_authorizer=dgr_authorizer,
        pretarget_cognitive_exit_authorizer=exit_authorizer,
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        outcome["cognitive_exit_variant"] = VARIANT_ID
        outcome["cognitive_exit_evaluations"] = cognitive_evaluations
        outcome["dgr_evaluations"] = dgr_evaluations
        outcome["dgr_qualification_count"] = sum(
            event["dgr_authorized"] is True
            for event in dgr_evaluations
        )
        outcome["dgr_committed"] = (
            outcome.get("pretarget_breaker_ps_committed") is True
        )
    return outcome


def _build_candidate_rows(
    evidence_path: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    original = specialist._simulate_selected_plan
    position_rows: list[dict[str, object]] = []

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        structural = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if structural.get("status") != "terminal":
            return structural

        outcome = _simulate_candidate(day_bars, executable, state)
        if outcome.get("status") != "terminal":
            raise AssertionError(
                "Comparator-011 changed sovereign terminal eligibility: "
                f"{outcome}"
            )
        position_rows.append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(
        list[dict[str, object]],
        base_payload["trades"],
    )
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    if [str(row["signal_at"]) for row in position_rows] != structural_ids:
        raise AssertionError(
            "Comparator-011 changed sovereign terminal trade identity"
        )

    comp007_rows = weak._apply_comp007_admission(position_rows)
    candidate = [row for row in comp007_rows if not mid._conflict(row)]
    return structural_rows, candidate


def _changed_trade_forensics(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> list[dict[str, object]]:
    baseline_map = {str(row["signal_at"]): row for row in baseline}
    candidate_map = {str(row["signal_at"]): row for row in candidate}
    if set(baseline_map) != set(candidate_map):
        raise AssertionError(
            "Comparator-011 changed Comparator-009 trade identity"
        )

    changed: list[dict[str, object]] = []
    for signal_at in sorted(baseline_map):
        left = baseline_map[signal_at]
        right = candidate_map[signal_at]
        left_r = _d(left["r_multiple"])
        right_r = _d(right["r_multiple"])
        if left_r == right_r and left.get("exit_reason") == right.get(
            "exit_reason"
        ):
            continue
        events = [
            event
            for event in cast(
                list[dict[str, object]],
                right.get("dgr_evaluations", []),
            )
            if event.get("dgr_authorized") is True
        ]
        changed.append(
            {
                "signal_at": signal_at,
                "local_date": right.get("local_date"),
                "entry_family": right.get("entry_family"),
                "side": right.get("side"),
                "baseline_r": format(left_r, "f"),
                "candidate_r": format(right_r, "f"),
                "delta_r": format(right_r - left_r, "f"),
                "baseline_exit_reason": left.get("exit_reason"),
                "candidate_exit_reason": right.get("exit_reason"),
                "dgr_committed": right.get("dgr_committed") is True,
                "dgr_authorization_events": events,
                "entry_context": right.get("entry_context", {}),
            }
        )
    return changed


def _halfyear_non_degrading(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> tuple[bool, list[dict[str, object]]]:
    left = specialist._block_metrics(baseline, halfyear=True)
    right = specialist._block_metrics(candidate, halfyear=True)
    if set(left) != set(right):
        return False, [{"reason": "HALFYEAR_IDENTITY_DRIFT"}]

    rows: list[dict[str, object]] = []
    passed = True
    for block in sorted(left):
        base = left[block]
        cand = right[block]
        mean_delta = _d(cand["mean_r"]) - _d(base["mean_r"])
        total_delta = _d(cand["total_r"]) - _d(base["total_r"])
        ok = mean_delta >= 0 and total_delta >= 0
        passed = passed and ok
        rows.append(
            {
                "halfyear": block,
                "mean_r_delta": format(mean_delta, "f"),
                "total_r_delta": format(total_delta, "f"),
                "non_degrading": ok,
            }
        )
    return passed, rows


def _partition_report(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    baseline = pack._candidate_rows(evidence_path)
    structural, candidate = _build_candidate_rows(evidence_path)

    baseline_ids = [str(row["signal_at"]) for row in baseline]
    candidate_ids = [str(row["signal_at"]) for row in candidate]
    if baseline_ids != candidate_ids:
        raise AssertionError(
            "Comparator-011 must preserve Comparator-009 admitted identity"
        )

    baseline_metrics = specialist._metrics(
        baseline,
        friction=pack.BASELINE_FRICTION_R,
    )
    if not pack._binding_matches(partition, baseline_metrics):
        raise AssertionError(
            f"Comparator-009 frozen binding drift in {partition}"
        )

    eligible_dates, evidence = pack._eligible_dates(evidence_path)
    daily = pack._daily_series(candidate, eligible_dates)
    metrics = specialist._metrics(
        candidate,
        friction=pack.BASELINE_FRICTION_R,
    )
    payoff = pack._payoff(candidate, pack.BASELINE_FRICTION_R)
    risk = pack._risk_adjusted(daily)
    mc = specialist._monte_carlo(candidate)
    stress = pack._cost_stress(candidate)
    years = pack._year_totals(candidate)
    winner = admission._winner_preservation(baseline, candidate)
    changed = _changed_trade_forensics(baseline, candidate)
    halfyear_ok, halfyear_deltas = _halfyear_non_degrading(
        baseline,
        candidate,
    )

    gates = {
        "baseline_binding_exact": True,
        "same_trade_identity_vs_comp009": baseline_ids == candidate_ids,
        "winner_count_preservation_at_least_0_80": (
            _d(winner["winner_count_preservation"]) >= Decimal("0.80")
        ),
        "winner_r_preservation_at_least_0_90": (
            _d(winner["winner_r_preservation"]) >= Decimal("0.90")
        ),
        "pf_nondegrade_vs_comp009": (
            _d(metrics["profit_factor"])
            >= _d(baseline_metrics["profit_factor"])
        ),
        "mean_nondegrade_vs_comp009": (
            _d(metrics["mean_r"]) >= _d(baseline_metrics["mean_r"])
        ),
        "dd_nondegrade_vs_comp009": (
            _d(metrics["max_drawdown_r"])
            <= _d(baseline_metrics["max_drawdown_r"])
        ),
        "all_halfyears_nondegrading": halfyear_ok,
        "era_pf_at_least_1_50": pack._pf_pass(
            metrics,
            pack.ERA_PF_MIN,
        ),
        "observed_dd_at_most_6r": (
            _d(metrics["max_drawdown_r"]) <= pack.OBSERVED_DD_MAX
        ),
    }

    return {
        "schema": SCHEMA,
        "mode": "partition",
        "partition": partition,
        "base_comparator_id": BASE_COMPARATOR_ID,
        "variant_id": VARIANT_ID,
        "policy_fingerprint_base": pack.policy_fingerprint(),
        "baseline_trade_count": len(baseline),
        "structural_trade_count": len(structural),
        "candidate_trade_count": len(candidate),
        "baseline_metrics": baseline_metrics,
        "metrics": metrics,
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "risk_adjusted": risk,
        "monte_carlo": mc,
        "cost_stress": stress,
        "year_total_r": years,
        "halfyear_stress": specialist._block_metrics(
            candidate,
            halfyear=True,
        ),
        "halfyear_deltas_vs_comp009": halfyear_deltas,
        "winner_preservation_vs_comp009": winner,
        "changed_trade_count": len(changed),
        "changed_trade_forensics": changed,
        "dgr_qualified_trade_count": sum(
            int(row.get("dgr_qualification_count", 0)) > 0
            for row in candidate
        ),
        "dgr_committed_trade_count": sum(
            row.get("dgr_committed") is True
            for row in candidate
        ),
        "eligible_dates": eligible_dates,
        "daily_series": daily,
        "candidate_rows": pack._minimal_rows(candidate),
        "reference_volatility_regimes": pack._regime_report(
            pack._minimal_rows(candidate)
        ),
        "evidence": evidence,
        "gates": gates,
        "partition_pass": all(gates.values()),
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "base_is_frozen_comp009": True,
            "same_comp009_admission": True,
            "same_comp009_target_stack": True,
            "breaker_only_dgr_scope": True,
            "maximum_cognition_required": True,
            "dgr_min_mfe_r_preexisting": format(DGR_MIN_MFE_R, "f"),
            "dgr_min_giveback_r_preexisting": format(
                DGR_MIN_CLOSE_GIVEBACK_R,
                "f",
            ),
            "dgr_max_efficiency_preexisting": format(
                DGR_MAX_PATH_EFFICIENCY,
                "f",
            ),
            "dgr_current_close_max_r_preexisting": format(
                DGR_CURRENT_CLOSE_MAX_R,
                "f",
            ),
            "confirmed_m1_protective_swing_required": True,
            "maximum_one_dgr_rescue_per_trade": True,
            "next_m1_activation": True,
            "existing_cognitive_exit_priority_preserved": True,
            "new_numeric_threshold_added": False,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def _aggregate(reports: list[dict[str, object]]) -> dict[str, object]:
    required = {"r5", "r6", "r8", "consumed"}
    by_partition = {
        str(report["partition"]): report
        for report in reports
    }
    if set(by_partition) != required:
        raise AssertionError(
            f"expected partitions {sorted(required)}, got {sorted(by_partition)}"
        )

    fingerprints = {
        str(report["policy_fingerprint_base"])
        for report in reports
    }
    if fingerprints != {pack.policy_fingerprint()}:
        raise AssertionError("Comparator-009 policy fingerprint drift")

    rows = [
        cast(dict[str, object], row)
        for partition in ("r5", "r6", "r8", "consumed")
        for row in cast(
            list[dict[str, object]],
            by_partition[partition]["candidate_rows"],
        )
    ]
    rows.sort(key=lambda row: str(row["signal_at"]))
    signal_ids = [str(row["signal_at"]) for row in rows]
    if len(signal_ids) != len(set(signal_ids)):
        raise AssertionError("candidate signal identities overlap across folds")

    daily = [
        cast(dict[str, str], item)
        for partition in ("r5", "r6", "r8", "consumed")
        for item in cast(
            list[dict[str, str]],
            by_partition[partition]["daily_series"],
        )
    ]
    daily.sort(key=lambda item: item["local_date"])
    daily_dates = [item["local_date"] for item in daily]
    if len(daily_dates) != len(set(daily_dates)):
        raise AssertionError("eligible session dates overlap across folds")

    metrics = specialist._metrics(
        rows,
        friction=pack.BASELINE_FRICTION_R,
    )
    payoff = pack._payoff(rows, pack.BASELINE_FRICTION_R)
    risk = pack._risk_adjusted(daily)
    mc = specialist._monte_carlo(rows)
    stress = pack._cost_stress(rows)
    years = pack._year_totals(rows)
    drawdown = pack._drawdown_episode(rows, pack.BASELINE_FRICTION_R)

    changed = [
        {
            "partition": partition,
            **cast(dict[str, object], item),
        }
        for partition in ("r5", "r6", "r8", "consumed")
        for item in cast(
            list[dict[str, object]],
            by_partition[partition]["changed_trade_forensics"],
        )
    ]

    gates = {
        "all_partition_gates_pass": all(
            bool(by_partition[name]["partition_pass"])
            for name in required
        ),
        "no_signal_overlap_across_folds": True,
        "no_eligible_session_overlap_across_folds": True,
        "all_fold_pf_at_least_1_50": all(
            pack._pf_pass(
                cast(dict[str, object], by_partition[name]["metrics"]),
                pack.ERA_PF_MIN,
            )
            for name in required
        ),
        "all_fold_observed_dd_at_most_6r": all(
            _d(
                cast(dict[str, object], by_partition[name]["metrics"])[
                    "max_drawdown_r"
                ]
            )
            <= pack.OBSERVED_DD_MAX
            for name in required
        ),
        "combined_pf_at_least_1_70": pack._pf_pass(
            metrics,
            pack.COMBINED_PF_MIN,
        ),
        "combined_expectancy_positive": _d(metrics["mean_r"]) > 0,
        "payoff_at_least_1_20": (
            payoff is not None and payoff >= pack.PAYOFF_MIN
        ),
        "stitched_observed_dd_at_most_6r": (
            _d(drawdown["max_drawdown_r"]) <= pack.OBSERVED_DD_MAX
        ),
        "annualized_sharpe_at_least_1_50": (
            risk["annualized_sharpe"] is not None
            and _d(risk["annualized_sharpe"]) >= pack.SHARPE_MIN
        ),
        "annualized_sortino_at_least_2_00": (
            risk["annualized_sortino"] is not None
            and _d(risk["annualized_sortino"]) >= pack.SORTINO_MIN
        ),
        "mc_positive_at_least_0_90": (
            _d(mc["positive_terminal_probability"])
            >= pack.MC_POSITIVE_MIN
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"]) <= pack.MC_P95_DD_MAX
        ),
        "degraded_0_10r_pf_gt_1": pack._pf_gt(
            stress["0.10"],
            Decimal(1),
        ),
    }

    return {
        "schema": SCHEMA,
        "mode": "aggregate",
        "base_comparator_id": BASE_COMPARATOR_ID,
        "variant_id": VARIANT_ID,
        "policy_fingerprint_base": pack.policy_fingerprint(),
        "partitions": {
            name: {
                "partition_pass": by_partition[name]["partition_pass"],
                "baseline_trade_count": by_partition[name][
                    "baseline_trade_count"
                ],
                "candidate_trade_count": by_partition[name][
                    "candidate_trade_count"
                ],
                "baseline_metrics": by_partition[name]["baseline_metrics"],
                "metrics": by_partition[name]["metrics"],
                "winner_preservation_vs_comp009": by_partition[name][
                    "winner_preservation_vs_comp009"
                ],
                "changed_trade_count": by_partition[name][
                    "changed_trade_count"
                ],
                "dgr_qualified_trade_count": by_partition[name][
                    "dgr_qualified_trade_count"
                ],
                "dgr_committed_trade_count": by_partition[name][
                    "dgr_committed_trade_count"
                ],
                "halfyear_deltas_vs_comp009": by_partition[name][
                    "halfyear_deltas_vs_comp009"
                ],
            }
            for name in ("r5", "r6", "r8", "consumed")
        },
        "combined": {
            "trade_count": len(rows),
            "metrics": metrics,
            "payoff_ratio": (
                None if payoff is None else format(payoff, "f")
            ),
            "risk_adjusted": risk,
            "monte_carlo": mc,
            "cost_stress": stress,
            "year_total_r": years,
            "drawdown_episode": drawdown,
            "reference_volatility_regimes": pack._regime_report(rows),
        },
        "changed_trade_count": len(changed),
        "changed_trade_forensics": changed,
        "gates": gates,
        "comparator011_survivor": all(gates.values()),
        "fresh_holdout_opened": False,
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "single_predeclared_composition": True,
            "conservative_dgr_witness_only": True,
            "new_numeric_threshold_added": False,
            "maximum_cognition_required": True,
            "confirmed_m1_protective_swing_required": True,
            "maximum_one_dgr_rescue_per_trade": True,
            "next_m1_activation": True,
            "existing_cognitive_exit_priority_preserved": True,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("partition")
    one.add_argument("evidence", type=Path)
    one.add_argument("--partition", required=True)
    one.add_argument("--output", required=True, type=Path)

    agg = sub.add_parser("aggregate")
    agg.add_argument("reports", nargs="+", type=Path)
    agg.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "partition":
        payload = _partition_report(
            args.evidence,
            partition=args.partition,
        )
    else:
        payload = _aggregate(
            [
                json.loads(path.read_text(encoding="utf-8"))
                for path in args.reports
            ]
        )
    _write(args.output, payload)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
