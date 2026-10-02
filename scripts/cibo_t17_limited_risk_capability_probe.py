"""Build sanitized T17 limited-risk/GSL capability evidence from provider probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_report(
    *,
    account_report: dict[str, Any],
    provider_report: dict[str, Any],
) -> dict[str, object]:
    if account_report.get("provider_key") != "ctrader-demo":
        raise ValueError("T17 account report provider mismatch")
    if provider_report.get("provider_key") != "ctrader-demo":
        raise ValueError("T17 provider report provider mismatch")
    if account_report.get("environment") != "demo":
        raise ValueError("T17 account report environment mismatch")
    if provider_report.get("environment") != "demo":
        raise ValueError("T17 provider report environment mismatch")
    account_fp = account_report.get("account_fingerprint_sha256")
    provider_fp = provider_report.get("account_fingerprint_sha256")
    if (
        not isinstance(account_fp, str)
        or len(account_fp) != 64
        or account_fp != provider_fp
    ):
        raise ValueError("T17 account/provider fingerprint binding mismatch")

    limited = account_report.get("is_limited_risk")
    if limited is not None and type(limited) is not bool:
        raise ValueError("T17 is_limited_risk must be bool/null")

    symbols_raw = provider_report.get("symbols")
    if not isinstance(symbols_raw, dict) or not symbols_raw:
        raise ValueError("T17 provider symbols are required")

    supported: list[str] = []
    unsupported: list[str] = []
    unknown: list[str] = []
    for symbol, raw in sorted(symbols_raw.items()):
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("T17 provider symbol key invalid")
        if not isinstance(raw, dict):
            raise ValueError(f"T17 provider symbol row invalid: {symbol}")
        gsl = raw.get("guaranteed_stop_loss")
        if gsl is True:
            supported.append(symbol)
        elif gsl is False:
            unsupported.append(symbol)
        elif gsl is None:
            unknown.append(symbol)
        else:
            raise ValueError(f"T17 GSL capability invalid: {symbol}")

    coverage = not unknown
    candidate = limited is True and coverage and len(supported) == len(symbols_raw)

    blockers: list[str] = []
    if limited is None:
        blockers.append("T17_LIMITED_RISK_ACCOUNT_FIELD_UNKNOWN")
    elif limited is False:
        blockers.append("T17_ACCOUNT_NOT_LIMITED_RISK")
    if not coverage:
        blockers.append("T17_GSL_PROVIDER_UNIVERSE_COVERAGE_INCOMPLETE")
    if unsupported:
        blockers.append(
            "T17_GSL_UNAVAILABLE_ON_PROVIDER_SYMBOLS:" + ",".join(unsupported)
        )
    if candidate:
        blockers.extend(
            (
                "T17_GSL_CANDIDATE_EXECUTION_ECONOMICS_NOT_PROVEN",
                "T17_GSL_CANDIDATE_FRESH_OOS_UTILITY_NOT_PROVEN",
            )
        )
    blockers.extend(
        (
            "T17_OPTION_STRUCTURE_NOT_PROVEN",
            "T17_DEFINED_RISK_SPREAD_NOT_PROVEN",
        )
    )

    return {
        "schema": "qore.cibo.t17.limited_risk_capability.v1",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": account_fp,
        "account_limited_risk": limited,
        "limited_risk_margin_calculation_strategy": account_report.get(
            "limited_risk_margin_calculation_strategy"
        ),
        "observed_symbols": len(symbols_raw),
        "gsl_supported_symbols": supported,
        "gsl_unsupported_symbols": unsupported,
        "gsl_unknown_symbols": unknown,
        "provider_universe_gsl_coverage_complete": coverage,
        "limited_risk_candidate_identified": candidate,
        "option_structure_proven": False,
        "defined_risk_spread_proven": False,
        "gsl_execution_economics_proven": False,
        "fresh_oos_utility_demonstrated": False,
        "t17_policy_ready": False,
        "broker_mutation_performed": False,
        "productive_authority": False,
        "blockers": blockers,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=Path, required=True)
    parser.add_argument("--provider", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    account = json.loads(args.account.read_text(encoding="utf-8"))
    provider = json.loads(args.provider.read_text(encoding="utf-8"))
    report = build_report(
        account_report=account,
        provider_report=provider,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
