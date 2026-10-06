"""Generic scientific adjudication for normalized Trader Lab replay reports."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def d(value: object) -> Decimal:
    return Decimal(str(value))


def pf(metrics: dict[str, Any]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is not None:
        return d(value)
    wins = int(metrics.get("wins", 0))
    losses = int(metrics.get("losses", 0))
    if wins > 0 and losses == 0:
        return Decimal("Infinity")
    return Decimal("-Infinity")


def temporal_nondegrade(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    left = baseline.get("temporal_blocks", {})
    right = candidate.get("temporal_blocks", {})
    common = sorted(set(left) & set(right))
    details: dict[str, Any] = {}
    all_ok = bool(common)
    for key in common:
        bm = left[key]
        cm = right[key]
        mean_delta = d(cm["mean_r"]) - d(bm["mean_r"])
        dd_ok = d(cm["max_drawdown_r"]) <= d(bm["max_drawdown_r"])
        ok = mean_delta >= 0 and dd_ok
        all_ok &= ok
        details[key] = {
            "mean_r_delta": format(mean_delta, "f"),
            "dd_nondegrade": dd_ok,
            "nondegrade": ok,
        }
    return all_ok, details


def evaluate(
    profile: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    science = profile["science"]
    control = str(science["control"])
    primary_lane = str(science["primary_lane"])
    lanes = tuple(profile["lanes"].keys())
    if primary_lane not in lanes:
        raise ValueError("primary_lane is not a configured lane")

    variant_names = tuple(payloads[lanes[0]]["variants"])
    if control not in variant_names:
        raise ValueError(f"control {control!r} missing")
    for lane in lanes:
        if tuple(payloads[lane]["variants"]) != variant_names:
            raise ValueError("variant identity differs across lanes")

    min_density = d(science["min_density"])
    min_winner_count = d(science["min_winner_count_preservation"])
    min_winner_r = d(science["min_winner_r_preservation"])
    all_lane_pf_floor = d(science["all_lane_pf_floor"])
    hard_dd = d(science["hard_dd_max_r"])
    primary_pf_floor = d(science["primary_pf_floor"])
    primary_mean_floor = d(science["primary_mean_r_floor"])
    mc_paths_min = int(science["mc_paths_min"])
    mc_positive_floor = d(science["mc_positive_floor"])
    mc_p95_dd_max = d(science["mc_p95_dd_max_r"])
    require_temporal = bool(science.get("require_temporal_nondegrade", True))

    variants: dict[str, Any] = {}
    for variant in variant_names:
        per_lane: dict[str, Any] = {}
        pf_non_count = 0
        mean_non_count = 0
        dd_non_count = 0
        density_count = 0
        winner_all = True
        temporal_all = True
        mc_all = True

        for lane in lanes:
            base = payloads[lane]["variants"][control]
            cand = payloads[lane]["variants"][variant]
            bm = base["metrics"]
            cm = cand["metrics"]
            winner = cand["winner_preservation"]
            mc = cand["monte_carlo"]

            pf_non = pf(cm) >= pf(bm)
            mean_non = d(cm["mean_r"]) >= d(bm["mean_r"])
            dd_non = d(cm["max_drawdown_r"]) <= d(bm["max_drawdown_r"])
            density_ok = d(cand["relative_density_vs_control"]) >= min_density
            winner_ok = (
                d(winner["count"]) >= min_winner_count
                and d(winner["r"]) >= min_winner_r
            )
            temporal_ok, temporal = temporal_nondegrade(base, cand)
            if not require_temporal:
                temporal_ok = True
            mc_ok = (
                int(mc["paths"]) >= mc_paths_min
                and mc.get("positive_terminal_probability") is not None
                and mc.get("p95_max_drawdown_r") is not None
            )

            pf_non_count += int(pf_non)
            mean_non_count += int(mean_non)
            dd_non_count += int(dd_non)
            density_count += int(density_ok)
            winner_all &= winner_ok
            temporal_all &= temporal_ok
            mc_all &= mc_ok

            per_lane[lane] = {
                "metrics": cm,
                "pf_nondegrade": pf_non,
                "mean_nondegrade": mean_non,
                "dd_nondegrade": dd_non,
                "density_floor_pass": density_ok,
                "winner_floor_pass": winner_ok,
                "temporal_nondegrade": temporal_ok,
                "temporal_blocks": temporal,
                "monte_carlo_complete": mc_ok,
            }

        primary = payloads[primary_lane]["variants"][variant]
        pm = primary["metrics"]
        pmc = primary["monte_carlo"]
        owner = {
            "pf_floor": pf(pm) >= primary_pf_floor,
            "mean_r_floor": d(pm["mean_r"]) >= primary_mean_floor,
            "observed_dd_hard_gate": d(pm["max_drawdown_r"]) <= hard_dd,
            "mc_positive_floor": d(pmc["positive_terminal_probability"])
            >= mc_positive_floor,
            "mc_p95_dd_gate": d(pmc["p95_max_drawdown_r"]) <= mc_p95_dd_max,
        }
        all_lane_pf = all(
            pf(payloads[lane]["variants"][variant]["metrics"]) >= all_lane_pf_floor
            for lane in lanes
        )
        all_lane_dd = all(
            d(payloads[lane]["variants"][variant]["metrics"]["max_drawdown_r"])
            <= hard_dd
            for lane in lanes
        )
        development_survivor = (
            pf_non_count == len(lanes)
            and mean_non_count == len(lanes)
            and dd_non_count == len(lanes)
            and density_count == len(lanes)
            and winner_all
            and temporal_all
            and mc_all
        )
        scientific_pass = (
            development_survivor
            and all_lane_pf
            and all_lane_dd
            and all(owner.values())
        )
        variants[variant] = {
            "lanes": per_lane,
            "pf_nondegrade_lanes": pf_non_count,
            "mean_nondegrade_lanes": mean_non_count,
            "dd_nondegrade_lanes": dd_non_count,
            "density_floor_lanes": density_count,
            "winner_preservation_all_lanes": winner_all,
            "temporal_nondegrade_all_lanes": temporal_all,
            "monte_carlo_complete_all_lanes": mc_all,
            "all_lane_pf_floor_pass": all_lane_pf,
            "all_lane_dd_hard_gate_pass": all_lane_dd,
            "primary_lane_gates": owner,
            "development_survivor": development_survivor,
            "scientific_pass": scientific_pass,
            "promotion_authorized": False,
            "certification_authorized": False,
        }

    return {
        "schema": "qore.github-trader-lab.scientific-battery.v1",
        "profile_id": profile["profile_id"],
        "subject": profile["subject"],
        "lanes": list(lanes),
        "control": control,
        "battery_layers": [
            "MULTI_LANE_REPLAY",
            "FIXED_FRICTION_FROM_SUBJECT_REPLAY",
            "PF_MEAN_DD_NONDEGRADE",
            "DENSITY_FLOOR",
            "WINNER_COUNT_AND_R_PRESERVATION",
            "TEMPORAL_BLOCK_STRESS",
            "DETERMINISTIC_MONTE_CARLO",
            "CROSS_LANE_PF_FLOOR",
            "OBSERVED_DD_HARD_GATE",
            "PRIMARY_LANE_DIRECTION_GATES",
        ],
        "variants": variants,
        "development_survivors": [
            name for name, row in variants.items() if row["development_survivor"]
        ],
        "hard_dd_survivors": [
            name
            for name, row in variants.items()
            if row["development_survivor"] and row["all_lane_dd_hard_gate_pass"]
        ],
        "scientific_passes": [
            name for name, row in variants.items() if row["scientific_pass"]
        ],
        "governance": {
            "independent_trader_lab": True,
            "research_only": True,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
            "promotion_authorized": False,
            "sovereign_workflow_modified": False,
            "broker_mutation": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
