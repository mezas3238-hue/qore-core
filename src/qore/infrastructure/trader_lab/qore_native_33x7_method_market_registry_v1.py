"""QORE Native 33 × 7 pre-outcome methodology/market coverage registry (D0).

NO price/return data read here. An audit of research coverage != tests of edge.
Use the frozen original G0 source symbols only. This registry deliberately
exposes previously tested hypotheses as prior exposure, not new OOS results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_market33_source_census_v1 as census
from qore.infrastructure.trader_lab import qore_native_final33_three_m5_g0_v1 as final33
from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as source

IDENTITY = "QORE_NATIVE_33X7_FULL_FACTORIAL_DESIGN_ONLY_V1"
SOURCE_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
RESEARCH_ERA = "2016-09-17_TO_2022-09-17"
DIAGNOSTIC_ERA = "2022-09-17_TO_2024-09-17_PREVIOUSLY_EXPOSED"
POST_2024_OHLC_EMBARGO = True
PROFIT_READ = False
METHODOLOGIES: tuple[tuple[str, str], ...] = (
    ("REVERSAL_12H", "Reversión 12 horas"),
    ("POST_OPEN_CONT", "Continuación post-apertura / sesión"),
    ("PERSISTENCE_12H", "Persistencia 12 horas"),
    ("OPEN_INITIAL_REACTION", "Reacción inicial de sesión"),
    ("SWEEP_RECLAIM", "Barrido y recuperación de rango"),
    ("TREND_MULTI_DAY", "Tendencia multidiaria"),
    ("RANGE_BREAK_CONT", "Continuación tras ruptura de rango"),
)
PREVIOUS_SINGLE_MARKET: dict[tuple[str, str], tuple[int, str]] = {
    ("REVERSAL_12H", "XAUUSD"): (825, "NO_SUPPORT"),
    ("POST_OPEN_CONT", "NAS100"): (827, "NO_SUPPORT"),
    ("PERSISTENCE_12H", "EURUSD"): (822, "NO_SUPPORT"),
}
PRIOR_PANEL_SWEEP_PR = 830
SESSION_DEPENDENT = frozenset(("POST_OPEN_CONT", "OPEN_INITIAL_REACTION"))


def family_for(symbol: str) -> str:
    matched = [name for name, symbols in census.FAMILIES.items() if symbol in symbols]
    if len(matched) != 1:
        raise ValueError("frozen market family classification missing/overlapping")
    return matched[0]


def session_reference(symbol: str, method: str) -> dict[str, Any]:
    """A session research proxy is not proof of a broker or exchange opening."""
    if method not in SESSION_DEPENDENT:
        return {"session_kind": "UTC_SYNTHETIC_CAUSAL_M5",
                "tz": "UTC", "local_reference": None,
                "broker_open_verified": False}
    family = family_for(symbol)
    if family == "equity_indices":
        label, tz, clock = "US_CASH_OPEN_REFERENCE_CFD_NOT_FUTURES", "America/New_York", "09:30"
    elif family == "metals":
        label, tz, clock = "US_METALS_LIQUIDITY_PROXY_UNVALIDATED", "America/New_York", "08:00"
    else:
        label, tz, clock = "FX_LONDON_LIQUIDITY_TRANSITION_NOT_EXCHANGE_OPEN", "Europe/London", "08:00"
    return {"session_kind": label, "tz": tz, "local_reference": clock,
            "broker_open_verified": False}


def cell_prior(method: str, symbol: str) -> dict[str, Any]:
    if method == "SWEEP_RECLAIM":
        return {
            "status": "PREVIOUSLY_EVALUATED_IN_ALL33_PANEL_NOT_NEW_CONFIRMATION",
            "prior_pr": PRIOR_PANEL_SWEEP_PR,
            "prior_result": "PANEL_NO_SUPPORT_NOT_INDIVIDUAL_MARKET_INFERENCE",
        }
    if (method, symbol) in PREVIOUS_SINGLE_MARKET:
        pr, verdict = PREVIOUS_SINGLE_MARKET[(method, symbol)]
        return {
            "status": "PRIOR_SINGLE_MARKET_NO_SUPPORT_NOT_NEW_CONFIRMATION",
            "prior_pr": pr,
            "prior_result": verdict,
        }
    return {
        "status": "DESIGN_ONLY_NOT_TESTED",
        "prior_pr": None,
        "prior_result": None,
    }


def build() -> dict[str, Any]:
    census.frozen_family_contract()
    frozen = final33.FROZEN_UNIVERSE_33
    methods = [x[0] for x in METHODOLOGIES]
    if len(frozen) != 33 or len(methods) != 7 or len(set(methods)) != 7:
        raise ValueError("exactly 33 fixed symbols and seven fixed methodology IDs required")
    if SOURCE_SHA != "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85":
        raise ValueError("G0 exact signed source SHA cannot change")
    markets = sorted(frozen)
    cells: list[dict[str, Any]] = []
    for method, label in METHODOLOGIES:
        for symbol in markets:
            prior = cell_prior(method, symbol)
            if symbol in source.EXISTING:
                origin = "ORIGINAL12_CTRADER_DEMO_ACCOUNT_NOT_HOMOLOGATED"
            else:
                origin = "NEW21_ICMARKETS_CTRADER_DEMO_ACCOUNT"
            cells.append({
                "cell_id": f"{method}__{symbol}",
                "method_id": method,
                "method_label": label,
                "symbol": symbol,
                "market_family": family_for(symbol),
                "source_origin": origin,
                **session_reference(symbol, method),
                **prior,
                "paired_baseline_required": True,
                "independent_market_trial_asserted": False,
                "outcomes_read": False,
                "pnl_or_returns": None,
                "p_value": None,
                "net_profit_factor": None,
                "certified_edge": False,
                "eligible_for_live": False,
            })
    result = {
        "identity": IDENTITY,
        "status": "D0_ONLY_231_CELLS_REGISTERED_NO_ECONOMIC_TESTS_RUN",
        "source_g0_manifest_sha256": SOURCE_SHA,
        "source_markets": 33,
        "methodologies": len(METHODOLOGIES),
        "planned_cells": len(cells),
        "methods": [
            {"method_id": key, "label": label, "n_symbols": 33}
            for key, label in METHODOLOGIES
        ],
        "families": {name: len(members) for name, members in census.FAMILIES.items()},
        "previously_evaluated_in_all33_panel": sum(
            x["status"] == "PREVIOUSLY_EVALUATED_IN_ALL33_PANEL_NOT_NEW_CONFIRMATION"
            for x in cells
        ),
        "previous_single_market_evidence": sum(
            x["status"] == "PRIOR_SINGLE_MARKET_NO_SUPPORT_NOT_NEW_CONFIRMATION"
            for x in cells
        ),
        "design_only_untested": sum(x["status"] == "DESIGN_ONLY_NOT_TESTED" for x in cells),
        "market_returns_accessed_in_registry": PROFIT_READ,
        "development_era": RESEARCH_ERA,
        "temporal_diagnostic_era": DIAGNOSTIC_ERA,
        "post_2024_09_17_embargo_on_price_fields": POST_2024_OHLC_EMBARGO,
        "proposal_alpha_FWER": 0.05,
        "proposal_multiple_testing": "HOLM_FWER_OVER_ALL_PRE_REGISTERED_ECONOMIC_TESTS",
        "proposal_correlation_control": "SYNCHRONIZED_CALENDAR_WEEK_BOOTSTRAP_ACROSS_ALL_ASSETS_AND_METHODS",
        "proposed_cost_stress_roundtrip_bps_NOT_BROKER": [0, 1, 3, 5, 10, 20],
        "live_execution_or_net_profit_authorized": False,
        "native_traders_certified": 0,
        "source_prices_untouched": True,
        "cells": cells,
    }
    validate(result)
    return result


def validate(result: dict[str, Any]) -> None:
    census.frozen_family_contract()
    if (result.get("identity") != IDENTITY
            or result.get("status") != "D0_ONLY_231_CELLS_REGISTERED_NO_ECONOMIC_TESTS_RUN"
            or result.get("source_g0_manifest_sha256") != SOURCE_SHA
            or result.get("source_markets") != 33
            or result.get("methodologies") != 7
            or result.get("planned_cells") != 231
            or result.get("post_2024_09_17_embargo_on_price_fields") is not True
            or result.get("market_returns_accessed_in_registry") is not False
            or result.get("source_prices_untouched") is not True
            or result.get("live_execution_or_net_profit_authorized") is not False
            or result.get("native_traders_certified") != 0):
        raise ValueError("D0 source/gross/trading assertions must not be altered")
    cells = result.get("cells")
    if not isinstance(cells, list) or len(cells) != 231:
        raise ValueError("all 231 cells must be present, regardless of outcome")
    identifiers = [c.get("cell_id") for c in cells]
    if len(set(identifiers)) != 231:
        raise ValueError("duplicate or missing methodology-market cells")
    expected = {
        f"{method}__{symbol}"
        for method, _ in METHODOLOGIES for symbol in final33.FROZEN_UNIVERSE_33
    }
    if set(identifiers) != expected:
        raise ValueError("incomplete or substituted frozen 33x7 matrix")
    for cell in cells:
        method, symbol = cell.get("method_id"), cell.get("symbol")
        if cell.get("cell_id") != f"{method}__{symbol}":
            raise ValueError("method/market identity mismatch")
        if cell.get("market_family") != family_for(symbol):
            raise ValueError("market-family drift")
        if cell.get("status") != cell_prior(method, symbol)["status"]:
            raise ValueError("prior evidence cannot be rewritten as fresh confirmation")
        if cell.get("prior_pr") != cell_prior(method, symbol)["prior_pr"]:
            raise ValueError("prior PR evidence link missing")
        if cell.get("source_origin") != (
            "ORIGINAL12_CTRADER_DEMO_ACCOUNT_NOT_HOMOLOGATED"
            if symbol in source.EXISTING else "NEW21_ICMARKETS_CTRADER_DEMO_ACCOUNT"
        ):
            raise ValueError("source-broker provenance drift")
        if any((
            cell.get("outcomes_read") is not False,
            cell.get("pnl_or_returns") is not None,
            cell.get("p_value") is not None,
            cell.get("net_profit_factor") is not None,
            cell.get("certified_edge") is not False,
            cell.get("eligible_for_live") is not False,
            cell.get("independent_market_trial_asserted") is not False,
            cell.get("paired_baseline_required") is not True,
        )):
            raise ValueError("D0 design-only claims cannot imply measured edge")
        actual_clock = session_reference(symbol, method)
        if any(cell.get(k) != value for k, value in actual_clock.items()):
            raise ValueError("broker/session clock or proxy evidence drift")
    status_counts = Counter(c["status"] for c in cells)
    if (
        result.get("previously_evaluated_in_all33_panel") != 33
        or result.get("previous_single_market_evidence") != 3
        or result.get("design_only_untested") != 195
        or status_counts["PREVIOUSLY_EVALUATED_IN_ALL33_PANEL_NOT_NEW_CONFIRMATION"] != 33
        or status_counts["PRIOR_SINGLE_MARKET_NO_SUPPORT_NOT_NEW_CONFIRMATION"] != 3
        or status_counts["DESIGN_ONLY_NOT_TESTED"] != 195
    ):
        raise ValueError("unreported prior 33 panel/three single-market exposures")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("out_dir", type=Path)
    args = p.parse_args()
    result = build()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dest = args.out_dir / "qore-native-33x7-design-matrix.json"
    dest.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    dest.with_name(dest.name + ".sha256").write_text(f"{digest}  {dest.name}\n", encoding="utf-8")
    print(json.dumps({
        "identity": IDENTITY, "cells": result["planned_cells"],
        "prior_panel": 33, "prior_single": 3, "new_design_only": 195,
        "source_33_G0_SHA": SOURCE_SHA, "market_return_tests_executed": 0,
        "output_sha256": digest,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
