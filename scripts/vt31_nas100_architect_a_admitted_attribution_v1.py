"""VT31 NAS100 Architect A admitted-state attribution V1.

Consumed/burned evidence development only.

The current Architect A admission engine already rejects most source states.
This lab explains the terminal population it still admits under a common source
structural exit. It searches predeclared causal conjunctions for:

- stable positive classes across all four consumed folds;
- stable negative classes across all four consumed folds;
- regime-flip classes that are positive in R5/R6/R8 but weak or negative in
  the recent consumed block.

No class is promoted to a runtime rule by this script.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_architect_a_entry_edge_baseline_v1 as entry_baseline
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.architect_a_admitted_attribution.v1"
MIN_GROUP_SAMPLE = 2


def _d(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _bucket(
    value: object,
    cuts: tuple[tuple[Decimal, str], ...],
    tail: str,
) -> str:
    current = _d(value)
    if current is None:
        return "unavailable"
    for upper, label in cuts:
        if current < upper:
            return label
    return tail


def _minutes_bucket(value: object) -> str:
    if value is None:
        return "unavailable"
    minute = int(value)
    if minute <= 2:
        return "0_2m"
    if minute <= 5:
        return "3_5m"
    if minute <= 10:
        return "6_10m"
    return "11m_plus"


def _reclaim_bucket(value: object) -> str:
    if value is None:
        return "unavailable"
    minute = int(value)
    if minute <= 3:
        return "0_3m"
    if minute <= 7:
        return "4_7m"
    if minute <= 14:
        return "8_14m"
    return "15m_plus"


def _decision_bucket(value: object) -> str:
    minute = int(value)
    if minute < 10 * 60 + 10:
        return "10_00_10_09"
    if minute < 10 * 60 + 20:
        return "10_10_10_19"
    if minute < 10 * 60 + 30:
        return "10_20_10_29"
    return "10_30_plus"


def _features(
    trace: dict[str, object],
    trade: dict[str, object],
) -> dict[str, str]:
    family = str(trace["entry_family"])
    side = str(trace["side"])
    h1 = str(trace["h1_state"])
    h4 = str(trace["h4_state"])
    volatility = str(trace["reference_volatility_state"])
    last_structure = str(trace["last_structure_event_family"])
    cash_open = str(trace["cash_open_state"])
    premarket = str(trace["premarket_state"])
    prior_day = str(trace["prior_day_state"])
    prior_location = str(trace["position_in_prior_day_range"])
    path = (
        "compressed"
        if trace["current_path_compressed"] is True
        else "not_compressed"
    )
    risk = _bucket(
        trace["risk_ref"],
        (
            (Decimal("0.50"), "lt_0_50"),
            (Decimal("0.75"), "0_50_0_75"),
            (Decimal("1.00"), "0_75_1_00"),
            (Decimal("1.50"), "1_00_1_50"),
        ),
        "ge_1_50",
    )
    target_r = _bucket(
        trace["planned_target_r"],
        (
            (Decimal("1.00"), "lt_1r"),
            (Decimal("1.50"), "1_1_5r"),
            (Decimal("2.00"), "1_5_2r"),
            (Decimal("3.00"), "2_3r"),
        ),
        "ge_3r",
    )
    destination_ref = _bucket(
        trace["destination_distance_ref"],
        (
            (Decimal("0.50"), "lt_0_50ref"),
            (Decimal("1.00"), "0_50_1ref"),
            (Decimal("1.50"), "1_1_5ref"),
        ),
        "ge_1_5ref",
    )
    confirmation = _minutes_bucket(trace["confirmation_latency_minutes"])
    evidence_age = _minutes_bucket(trace["entry_evidence_age_minutes"])
    reclaim = _reclaim_bucket(trace["reference_reclaim_age_minutes"])
    decision = _decision_bucket(trace["decision_minute_ny"])
    entry_r = str(trade["r_multiple"])

    return {
        "family": family,
        "side": side,
        "h1": h1,
        "h4": h4,
        "volatility": volatility,
        "last_structure": last_structure,
        "cash_open": cash_open,
        "premarket": premarket,
        "prior_day": prior_day,
        "prior_location": prior_location,
        "path": path,
        "risk_ref_bucket": risk,
        "planned_target_r_bucket": target_r,
        "destination_ref_bucket": destination_ref,
        "confirmation_bucket": confirmation,
        "entry_age_bucket": evidence_age,
        "reclaim_bucket": reclaim,
        "decision_bucket": decision,
        "r_multiple": entry_r,
    }


def _class_keys(features: dict[str, str]) -> tuple[str, ...]:
    f = features
    keys = [
        f"family={f['family']}",
        f"side={f['side']}",
        f"h1={f['h1']}",
        f"h4={f['h4']}",
        f"volatility={f['volatility']}",
        f"last_structure={f['last_structure']}",
        f"cash_open={f['cash_open']}",
        f"premarket={f['premarket']}",
        f"prior_day={f['prior_day']}",
        f"prior_location={f['prior_location']}",
        f"risk={f['risk_ref_bucket']}",
        f"target_r={f['planned_target_r_bucket']}",
        f"destination_ref={f['destination_ref_bucket']}",
        f"confirmation={f['confirmation_bucket']}",
        f"entry_age={f['entry_age_bucket']}",
        f"reclaim={f['reclaim_bucket']}",
        f"decision={f['decision_bucket']}",
        (
            "family_h1="
            f"{f['family']}|{f['h1']}"
        ),
        (
            "family_volatility="
            f"{f['family']}|{f['volatility']}"
        ),
        (
            "family_last_structure="
            f"{f['family']}|{f['last_structure']}"
        ),
        (
            "family_risk="
            f"{f['family']}|{f['risk_ref_bucket']}"
        ),
        (
            "family_target_r="
            f"{f['family']}|{f['planned_target_r_bucket']}"
        ),
        (
            "family_confirmation="
            f"{f['family']}|{f['confirmation_bucket']}"
        ),
        (
            "family_entry_age="
            f"{f['family']}|{f['entry_age_bucket']}"
        ),
        (
            "family_h1_volatility="
            f"{f['family']}|{f['h1']}|{f['volatility']}"
        ),
        (
            "family_h1_risk="
            f"{f['family']}|{f['h1']}|{f['risk_ref_bucket']}"
        ),
        (
            "family_h1_last_structure="
            f"{f['family']}|{f['h1']}|{f['last_structure']}"
        ),
        (
            "family_h1_cash_open="
            f"{f['family']}|{f['h1']}|{f['cash_open']}"
        ),
        (
            "side_h1_volatility="
            f"{f['side']}|{f['h1']}|{f['volatility']}"
        ),
    ]
    return tuple(keys)


def replay(evidence_path: Path) -> dict[str, object]:
    base = entry_baseline.replay(evidence_path)
    traces = [
        cast(dict[str, object], row)
        for row in cast(list[object], base["reasoning_trace"])
        if cast(dict[str, object], row).get("action") == "EXECUTE"
    ]
    index: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for trace in traces:
        index[
            (
                str(trace["decision_at"]),
                str(trace["entry_family"]),
            )
        ].append(trace)

    enriched: list[dict[str, object]] = []
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for raw in cast(list[object], base["trades"]):
        trade = cast(dict[str, object], raw)
        key = (str(trade["signal_at"]), str(trade["entry_family"]))
        matches = index.get(key, [])
        if len(matches) != 1:
            raise AssertionError(
                f"terminal trade must map to one EXECUTE trace: {key} -> "
                f"{len(matches)}"
            )
        trace = matches[0]
        features = _features(trace, trade)
        row = dict(trade)
        row["pre_entry_features"] = features
        row["situation_fingerprint"] = trace["situation_fingerprint"]
        enriched.append(row)
        for class_key in _class_keys(features):
            groups[class_key].append(row)

    reports: dict[str, dict[str, object]] = {}
    for key, rows in sorted(groups.items()):
        if len(rows) < MIN_GROUP_SAMPLE:
            continue
        reports[key] = {
            "sample": len(rows),
            "stress_0_05r": specialist._metrics(
                rows,
                friction=specialist.FRICTION,
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "evidence": base["evidence"],
        "baseline_metrics": base["stress_0_05r"],
        "baseline_monte_carlo": base["monte_carlo"],
        "trade_count": len(enriched),
        "groups": reports,
        "trades": enriched,
        "governance": {
            "consumed_evidence_only": True,
            "admitted_terminal_population_only": True,
            "pre_entry_features_only": True,
            "common_structural_exit": True,
            "minimum_group_sample": MIN_GROUP_SAMPLE,
            "fold_identity_used_for_runtime_admission": False,
            "terminal_pnl_used_for_runtime_admission": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "baseline_metrics": payload["baseline_metrics"],
                "trade_count": payload["trade_count"],
                "group_count": len(cast(dict[str, object], payload["groups"])),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
