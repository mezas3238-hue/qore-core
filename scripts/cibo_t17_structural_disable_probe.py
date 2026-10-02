"""Build provider-bound T17 structural-disable evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_t17_structural_disable import (
    assess_t17_structural_disable,
)


def build_report(
    *,
    account_report: dict[str, Any],
    limited_risk_report: dict[str, Any],
) -> dict[str, object]:
    for payload, label in (
        (account_report, "account"),
        (limited_risk_report, "limited-risk"),
    ):
        if payload.get("provider_key") != "ctrader-demo":
            raise ValueError(f"T17 structural-disable {label} provider mismatch")
        if payload.get("environment") != "demo":
            raise ValueError(
                f"T17 structural-disable {label} environment mismatch"
            )

    account_fp = account_report.get("account_fingerprint_sha256")
    limited_fp = limited_risk_report.get("account_fingerprint_sha256")
    if not isinstance(account_fp, str) or account_fp != limited_fp:
        raise ValueError("T17 structural-disable fingerprint binding mismatch")

    taxonomy_complete = account_report.get("taxonomy_binding_complete")
    if type(taxonomy_complete) is not bool:
        raise ValueError("T17 structural-disable taxonomy flag invalid")

    option_candidates = account_report.get("option_taxonomy_candidates")
    if not isinstance(option_candidates, list) or any(
        not isinstance(item, str) or not item for item in option_candidates
    ):
        raise ValueError("T17 structural-disable option taxonomy invalid")

    limited = limited_risk_report.get("account_limited_risk")
    if limited is not None and type(limited) is not bool:
        raise ValueError("T17 structural-disable limited-risk flag invalid")

    observed_symbols = limited_risk_report.get("observed_symbols")
    if (
        type(observed_symbols) is not int
        or observed_symbols < 0
    ):
        raise ValueError("T17 structural-disable observed symbol count invalid")

    coverage = limited_risk_report.get(
        "provider_universe_gsl_coverage_complete"
    )
    if type(coverage) is not bool:
        raise ValueError("T17 structural-disable GSL coverage flag invalid")

    limited_candidate = limited_risk_report.get(
        "limited_risk_candidate_identified"
    )
    if type(limited_candidate) is not bool:
        raise ValueError("T17 structural-disable candidate flag invalid")

    def _symbols(name: str) -> tuple[str, ...]:
        raw = limited_risk_report.get(name)
        if not isinstance(raw, list) or any(
            not isinstance(item, str) or not item for item in raw
        ):
            raise ValueError(f"T17 structural-disable {name} invalid")
        return tuple(raw)

    evidence = assess_t17_structural_disable(
        provider_key="ctrader-demo",
        environment="demo",
        account_fingerprint_sha256=account_fp,
        taxonomy_binding_complete=taxonomy_complete,
        option_taxonomy_candidates=tuple(option_candidates),
        account_limited_risk=limited,
        observed_symbols=observed_symbols,
        gsl_supported_symbols=_symbols("gsl_supported_symbols"),
        gsl_unsupported_symbols=_symbols("gsl_unsupported_symbols"),
        gsl_unknown_symbols=_symbols("gsl_unknown_symbols"),
        provider_universe_gsl_coverage_complete=coverage,
        limited_risk_candidate_identified=limited_candidate,
    )
    payload = asdict(evidence)
    payload["schema"] = "qore.cibo.t17.structural_disable.v1"
    payload["evidence_sha256"] = evidence.fingerprint()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=Path, required=True)
    parser.add_argument("--limited-risk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    account = json.loads(args.account.read_text(encoding="utf-8"))
    limited = json.loads(args.limited_risk.read_text(encoding="utf-8"))
    report = build_report(
        account_report=account,
        limited_risk_report=limited,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
