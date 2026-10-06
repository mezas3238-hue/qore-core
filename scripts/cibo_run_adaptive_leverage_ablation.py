#!/usr/bin/env python3
"""Run the sovereign Adaptive Leverage OFF ceiling ablation.

Ablation contract:
- same frozen manifest;
- same Native MAX cognition;
- same Portfolio objective/ranking;
- same Sizing, Compound, CMA and QORE Risk;
- only Portfolio/Adaptive Leverage maximum is fixed to 1x;
- no outcome-aware tuning and no target-capital tuning.

The result is research-only evidence for the mandatory adaptive_leverage
causal ablation.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path

from qore.infrastructure.cibo_single_account_historical_ceiling_replay import (
    run_historical_ceiling_replay,
)


_INITIAL_CAPITAL_USD = Decimal("60")
_ABLATION_NAME = "adaptive_leverage"
_FIXED_MULTIPLIER = 1


def _maximum_drawdown_usd(settlements) -> Decimal:
    capital = _INITIAL_CAPITAL_USD
    peak = capital
    maximum = Decimal(0)
    for item in sorted(
        settlements,
        key=lambda row: (row.settled_at, row.signal_fingerprint),
    ):
        with localcontext() as context:
            context.prec = 100
            capital += item.realized_net_pnl_usd
            peak = max(peak, capital)
            maximum = max(maximum, peak - capital)
    return maximum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--progress-every", type=int, default=100)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    def progress(payload: dict[str, object]) -> None:
        every = args.progress_every
        index = int(payload["epoch_index"])
        total = int(payload["decision_epoch_count"])
        if every > 0 and (index % every == 0 or index == total):
            print(json.dumps({"progress": payload}, sort_keys=True))

    result = run_historical_ceiling_replay(
        manifest,
        portfolio_fixed_multiplier=_FIXED_MULTIPLIER,
        progress_hook=progress,
    )

    multiplier_counts = Counter(
        item.adaptive_leverage_multiplier
        for item in result.decision_receipts
    )
    risk_counts = Counter(
        item.risk_decision for item in result.decision_receipts
    )
    executed = tuple(
        item
        for item in result.decision_receipts
        if item.risk_decision in {"ALLOW", "REDUCE"}
    )
    if any(item.adaptive_leverage_multiplier > 1 for item in executed):
        raise RuntimeError("Adaptive Leverage OFF emitted multiplier above 1x")

    maximum_drawdown = _maximum_drawdown_usd(result.settlement_receipts)
    payload = {
        "schema": "qore.cibo.sovereign-ceiling-ablation.v1",
        "name": _ABLATION_NAME,
        "ablation_contract": {
            "portfolio_fixed_multiplier": _FIXED_MULTIPLIER,
            "native_max_cognition_unchanged": True,
            "portfolio_objective_unchanged": True,
            "sizing_unchanged": True,
            "compound_unchanged": True,
            "cma_unchanged": True,
            "qore_risk_unchanged": True,
            "provider_assumption_unchanged": True,
            "outcome_aware_tuning": False,
            "target_capital_used_for_tuning": False,
        },
        "source_manifest_sha256": result.source_manifest_sha256,
        "decision_epoch_count": result.decision_epoch_count,
        "decision_count": len(result.decision_receipts),
        "settlement_count": len(result.settlement_receipts),
        "initial_capital_usd": format(_INITIAL_CAPITAL_USD, "f"),
        "ending_capital_usd": format(result.ending_capital_usd, "f"),
        "peak_capital_usd": format(result.peak_capital_usd, "f"),
        "net_pnl_usd": format(result.net_pnl_usd, "f"),
        "maximum_drawdown_usd": format(maximum_drawdown, "f"),
        "adaptive_leverage_multiplier_counts": {
            str(key): value
            for key, value in sorted(multiplier_counts.items())
        },
        "risk_decision_counts": {
            str(key): value for key, value in sorted(risk_counts.items())
        },
        "executed_decision_count": len(executed),
        "external_ai_call_count": result.external_ai_call_count,
        "outcome_used_for_predecision": result.outcome_used_for_predecision,
        "account_reset_count": result.account_reset_count,
        "economic_era_reset_count": result.economic_era_reset_count,
        "broker_mutation": result.broker_mutation,
        "certification_claimed": False,
        "executed": True,
        "research_only": True,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
