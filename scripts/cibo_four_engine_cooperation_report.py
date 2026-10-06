#!/usr/bin/env python3
"""Audit joint work across CIBO's four capital engines from replay sensors.

The report is observational/postdecision. It never changes a replay decision
and it never attributes causal PnL without a dedicated ablation.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Mapping

TARGETS = (
    "COMPOUND_PORTFOLIO",
    "ADAPTIVE_LEVERAGE",
    "SIZING",
    "CIBO_COMPOUND",
)


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    if isinstance(value, list):
        result: dict[str, object] = {}
        for item in value:
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError("sensor metric pairs are malformed")
            result[str(item[0])] = item[1]
        return result
    raise ValueError("sensor metrics must be mapping or pair list")


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {"true", "1"}:
        return True
    if raw in {"false", "0", "", "none"}:
        return False
    raise ValueError(f"cannot decode bool: {value!r}")


def _dec(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"non-finite decimal: {value!r}")
    return result


def _int(value: object) -> int:
    return int(str(value))


def _sensor_map(decision: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    raw = decision.get("function_sensors")
    if not isinstance(raw, list):
        raise ValueError("decision missing function_sensors")
    result: dict[str, Mapping[str, object]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("function sensor row invalid")
        code = str(item.get("function_code", ""))
        if code:
            if code in result:
                raise ValueError(f"duplicate function sensor: {code}")
            result[code] = item
    return result


def _active(code: str, output: Mapping[str, object]) -> bool:
    if code == "COMPOUND_PORTFOLIO":
        return _int(output.get("multiplier", 0)) > 0
    if code == "ADAPTIVE_LEVERAGE":
        return _int(output.get("selected_multiplier", 0)) > 0
    if code == "SIZING":
        return (
            str(output.get("action", "HOLD")) != "HOLD"
            and _dec(output.get("volume", 0)) > 0
        )
    if code == "CIBO_COMPOUND":
        return (
            _bool(output.get("applicable", False))
            and _bool(output.get("allow_incremental_compound", False))
        )
    return False


def build_report(replay: Mapping[str, object]) -> dict[str, object]:
    decisions = replay.get("decision_receipts")
    settlements = replay.get("settlement_receipts")
    if not isinstance(decisions, list) or not isinstance(settlements, list):
        raise ValueError("replay decisions/settlements missing")

    settlement_pnl: dict[str, Decimal] = {}
    for row in settlements:
        if not isinstance(row, Mapping):
            raise ValueError("settlement row invalid")
        signal = str(row.get("signal_fingerprint", ""))
        if signal:
            settlement_pnl[signal] = _dec(row.get("realized_net_pnl_usd", 0))

    stats = {
        code: {
            "call_count": 0,
            "downstream_consumed_count": 0,
            "decision_gate_count": 0,
            "final_binding_count": 0,
            "active_output_count": 0,
            "distinct_input_sha256": set(),
            "distinct_output_sha256": set(),
        }
        for code in TARGETS
    }
    patterns: Counter[str] = Counter()
    pattern_pnl: defaultdict[str, Decimal] = defaultdict(Decimal)
    handoffs: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    selected_above_four = 0
    maximum_selected_multiplier = 0
    compound_applicable = 0
    compound_allowed = 0

    for decision in decisions:
        if not isinstance(decision, Mapping):
            raise ValueError("decision receipt invalid")
        sensors = _sensor_map(decision)
        target_rows: dict[str, Mapping[str, object]] = {}
        for code in TARGETS:
            row = sensors.get(code)
            if row is None:
                missing[code] += 1
                continue
            target_rows[code] = row
            output = _mapping(row.get("output_metrics"))
            item = stats[code]
            item["call_count"] += 1
            item["downstream_consumed_count"] += int(
                _bool(row.get("downstream_consumed", False))
            )
            item["decision_gate_count"] += int(
                _bool(row.get("decision_gate_triggered", False))
            )
            item["final_binding_count"] += int(
                _bool(row.get("final_capital_binding", False))
            )
            item["active_output_count"] += int(_active(code, output))
            item["distinct_input_sha256"].add(str(row.get("input_sha256", "")))
            item["distinct_output_sha256"].add(str(row.get("output_sha256", "")))

        if len(target_rows) != len(TARGETS):
            patterns["INCOMPLETE_SENSOR_CHAIN"] += 1
            continue

        portfolio = _mapping(target_rows["COMPOUND_PORTFOLIO"]["output_metrics"])
        leverage_in = _mapping(target_rows["ADAPTIVE_LEVERAGE"]["input_metrics"])
        leverage = _mapping(target_rows["ADAPTIVE_LEVERAGE"]["output_metrics"])
        sizing = _mapping(target_rows["SIZING"]["output_metrics"])
        compound_in = _mapping(target_rows["CIBO_COMPOUND"]["input_metrics"])
        compound = _mapping(target_rows["CIBO_COMPOUND"]["output_metrics"])

        pm = _int(portfolio.get("multiplier", 0))
        lm = _int(leverage.get("selected_multiplier", 0))
        maximum_selected_multiplier = max(maximum_selected_multiplier, lm)
        selected_above_four += int(lm > 4)

        portfolio_active = pm > 0
        leverage_active = lm > 0
        sizing_active = _active("SIZING", sizing)
        compound_is_applicable = _bool(compound.get("applicable", False))
        compound_is_allowed = _bool(
            compound.get("allow_incremental_compound", False)
        )
        compound_applicable += int(compound_is_applicable)
        compound_allowed += int(compound_is_applicable and compound_is_allowed)

        handoffs["portfolio_to_leverage_multiplier_match"] += int(pm == lm)
        handoffs["portfolio_to_leverage_risk_match"] += int(
            _dec(portfolio.get("stop_risk_usd", 0))
            == _dec(leverage.get("stop_risk_cap_usd", 0))
        )
        handoffs["portfolio_to_leverage_margin_match"] += int(
            _dec(portfolio.get("margin_usd", 0))
            == _dec(leverage.get("margin_cap_usd", 0))
        )
        handoffs["leverage_declares_shared_portfolio_line"] += int(
            _bool(leverage.get("shared_portfolio_line", False))
        )
        handoffs["leverage_input_matches_portfolio_output"] += int(
            _int(leverage_in.get("upstream_portfolio_multiplier", -1)) == pm
        )

        sizing_feeds_compound = _bool(sizing.get("feeds_compound_gate", False))
        compound_requested = _bool(
            compound_in.get("realized_profit_source_requested", False)
        )
        handoffs["sizing_to_compound_applicability_match"] += int(
            sizing_feeds_compound == compound_requested
        )

        if (
            portfolio_active
            and leverage_active
            and sizing_active
            and compound_is_applicable
            and compound_is_allowed
        ):
            pattern = "FULL_FOUR_ENGINE_JOINT"
        elif (
            portfolio_active
            and leverage_active
            and sizing_active
            and not compound_is_applicable
        ):
            pattern = "THREE_ENGINE_BASE_CAPITAL_PATH"
        elif (
            portfolio_active
            and leverage_active
            and sizing_active
            and compound_is_applicable
            and not compound_is_allowed
        ):
            pattern = "COMPOUND_BLOCKED_AFTER_THREE_ENGINE_PATH"
        elif portfolio_active and leverage_active and not sizing_active:
            pattern = "PORTFOLIO_LEVERAGE_WITHOUT_SIZING"
        elif sizing_active and not (portfolio_active and leverage_active):
            pattern = "SIZING_WITHOUT_PORTFOLIO_LEVERAGE"
        else:
            pattern = "NO_JOINT_DEPLOYMENT"
        patterns[pattern] += 1
        signal = str(decision.get("signal_fingerprint", ""))
        if signal in settlement_pnl:
            pattern_pnl[pattern] += settlement_pnl[signal]

    module_summary: dict[str, object] = {}
    for code, item in stats.items():
        calls = int(item["call_count"])
        consumed = int(item["downstream_consumed_count"])
        bindings = int(item["final_binding_count"])
        active = int(item["active_output_count"])
        module_summary[code] = {
            "call_count": calls,
            "downstream_consumed_count": consumed,
            "decision_gate_count": int(item["decision_gate_count"]),
            "final_binding_count": bindings,
            "active_output_count": active,
            "distinct_input_count": len(item["distinct_input_sha256"]),
            "distinct_output_count": len(item["distinct_output_sha256"]),
            "consumption_rate": (
                "0" if calls == 0 else format(Decimal(consumed) / Decimal(calls), "f")
            ),
            "binding_rate": (
                "0" if calls == 0 else format(Decimal(bindings) / Decimal(calls), "f")
            ),
            "active_rate": (
                "0" if calls == 0 else format(Decimal(active) / Decimal(calls), "f")
            ),
        }

    decision_count = len(decisions)
    duplicate_surface = (
        decision_count > 0
        and handoffs["portfolio_to_leverage_multiplier_match"] == decision_count
        and handoffs["portfolio_to_leverage_risk_match"] == decision_count
        and handoffs["portfolio_to_leverage_margin_match"] == decision_count
        and handoffs["leverage_declares_shared_portfolio_line"] == decision_count
    )
    bottlenecks: list[dict[str, object]] = []
    if duplicate_surface:
        bottlenecks.append(
            {
                "severity": "HIGH",
                "code": "PORTFOLIO_LEVERAGE_SHARED_OUTPUT_SURFACE",
                "finding": (
                    "Compound Portfolio and Adaptive Leverage expose identical "
                    "multiplier/risk/margin outputs on every audited decision; "
                    "Leverage is not yet independently observable as a distinct actuator."
                ),
            }
        )
    for code in TARGETS:
        row = module_summary[code]
        if row["call_count"] and row["downstream_consumed_count"] == 0:
            bottlenecks.append(
                {
                    "severity": "HIGH",
                    "code": f"{code}_CALLED_NOT_CONSUMED",
                    "finding": f"{code} is called but never consumed downstream.",
                }
            )
        elif row["call_count"] and row["final_binding_count"] == 0:
            bottlenecks.append(
                {
                    "severity": "MEDIUM",
                    "code": f"{code}_NEVER_FINAL_BINDING",
                    "finding": (
                        f"{code} produces outputs but never directly binds the final "
                        "capital plan in this replay."
                    ),
                }
            )
    if compound_applicable == 0:
        bottlenecks.append(
            {
                "severity": "HIGH",
                "code": "CIBO_COMPOUND_NEVER_APPLICABLE",
                "finding": (
                    "CIBO Compound was observed on every decision but no decision "
                    "requested realized-profit capital, so compound never entered "
                    "the productive joint path."
                ),
            }
        )

    with localcontext() as context:
        context.prec = 100
        pattern_pnl_out = {
            key: format(value, "f")
            for key, value in sorted(pattern_pnl.items())
        }

    return {
        "schema": "qore.cibo.four-engine-cooperation-report.v1",
        "decision_count": decision_count,
        "targets": list(TARGETS),
        "module_summary": module_summary,
        "cooperation_pattern_counts": dict(sorted(patterns.items())),
        "cooperation_pattern_realized_pnl_usd_postdecision_association_only": (
            pattern_pnl_out
        ),
        "handoff_consistency_counts": dict(sorted(handoffs.items())),
        "missing_sensor_counts": dict(sorted(missing.items())),
        "compound_applicable_count": compound_applicable,
        "compound_allowed_count": compound_allowed,
        "maximum_selected_leverage_multiplier": maximum_selected_multiplier,
        "selected_multiplier_above_four_count": selected_above_four,
        "portfolio_and_leverage_share_exact_output_surface": duplicate_surface,
        "bottleneck_candidates": bottlenecks,
        "causal_pnl_attribution_claimed": False,
        "postdecision_observational_report": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    report = build_report(replay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
