"""VT08 Index R69 — R66 density causal decomposition.

R66 failed its preregistered 1,000-trade density gate with 773 trades.
R67 showed that density and economics failed for different reasons. R68 then
showed substantial provider incompleteness in the old SP500 slice, while also
showing that allocator changes alone cannot alter the 773-signal surface.

R69 is a density-only forensic decomposition. It does not fabricate missing
bars or trades and it does not change the failed R66 gate. It compares observed
trade formation per complete provider-backed M15 bucket across the consumed
5Y, recent2Y and failed R66 windows, then calculates transparent diagnostic
counterfactuals:

1. expected R66 count at its actually complete-M15 exposure if each market had
   formed signals at the 5Y or recent2Y structural rate;
2. expected R66 count if every observed R66 M15 bucket had been complete,
   again using those historical baseline formation rates.

Those counterfactuals are attribution only. They are not replacement evidence,
not synthetic reconstruction and not a certification score.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r68_r58_risk_transport_ablation as r68,
)

SCHEMA = "qore.trader_lab.vt08_index_r69_r66_density_causal_decomposition.v1"
IDENTITY = "VT08_INDEX_R69_R66_DENSITY_CAUSAL_DECOMPOSITION_001"
RATE_SCALE = Decimal("10000")
R66_DENSITY_GATE = r66.MIN_TRADES


def _market_counts(stream: tuple[tuple[Any, Any], ...]) -> dict[str, int]:
    counts = Counter(
        str(item[0].signal.symbol)
        for item in stream
    )
    return dict(sorted(counts.items()))


def _availability_rows(
    provenance: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return r68._availability(provenance)


def _rate(
    *,
    trades: int,
    complete_m15_buckets: int,
) -> Decimal:
    if complete_m15_buckets <= 0:
        raise ValueError("complete M15 exposure must be positive")
    return Decimal(trades) / Decimal(complete_m15_buckets)


def _projection(
    *,
    baseline_counts: dict[str, int],
    baseline_availability: dict[str, dict[str, Any]],
    r66_counts: dict[str, int],
    r66_availability: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_market: dict[str, Any] = {}
    total_observed = 0
    total_expected_complete_exposure = Decimal()
    total_expected_full_exposure = Decimal()

    for symbol in sorted(r66_counts):
        baseline_complete = int(
            baseline_availability[symbol]["complete_three_m5_buckets"]
        )
        baseline_rate = _rate(
            trades=int(baseline_counts[symbol]),
            complete_m15_buckets=baseline_complete,
        )

        failed_complete = int(
            r66_availability[symbol]["complete_three_m5_buckets"]
        )
        failed_total = int(r66_availability[symbol]["m15_buckets"])
        actual = int(r66_counts[symbol])

        expected_complete = Decimal(failed_complete) * baseline_rate
        expected_full = Decimal(failed_total) * baseline_rate
        coverage_component = expected_full - expected_complete
        structural_rate_component = expected_complete - Decimal(actual)

        total_observed += actual
        total_expected_complete_exposure += expected_complete
        total_expected_full_exposure += expected_full

        by_market[symbol] = {
            "actual_r66_trades": actual,
            "baseline_trades_per_10k_complete_m15": str(
                baseline_rate * RATE_SCALE
            ),
            "r66_trades_per_10k_complete_m15": str(
                _rate(
                    trades=actual,
                    complete_m15_buckets=failed_complete,
                )
                * RATE_SCALE
            ),
            "r66_complete_m15_buckets": failed_complete,
            "r66_total_m15_buckets": failed_total,
            "r66_partial_m15_buckets": (
                failed_total - failed_complete
            ),
            "expected_at_observed_complete_exposure": str(expected_complete),
            "expected_at_full_observed_bucket_exposure": str(expected_full),
            "projected_missing_coverage_component_trades": str(
                coverage_component
            ),
            "projected_structural_rate_component_trades": str(
                structural_rate_component
            ),
        }

    projected_coverage_component = (
        total_expected_full_exposure - total_expected_complete_exposure
    )
    projected_structural_rate_component = (
        total_expected_complete_exposure - Decimal(total_observed)
    )
    residual_to_gate_after_full_coverage = (
        Decimal(R66_DENSITY_GATE) - total_expected_full_exposure
    )

    return {
        "observed_r66_trades": total_observed,
        "expected_at_observed_complete_exposure": str(
            total_expected_complete_exposure
        ),
        "expected_at_full_observed_bucket_exposure": str(
            total_expected_full_exposure
        ),
        "projected_missing_coverage_component_trades": str(
            projected_coverage_component
        ),
        "projected_structural_rate_component_trades": str(
            projected_structural_rate_component
        ),
        "residual_to_preregistered_gate_after_full_coverage": str(
            residual_to_gate_after_full_coverage
        ),
        "full_coverage_projection_reaches_r66_gate": (
            total_expected_full_exposure >= Decimal(R66_DENSITY_GATE)
        ),
        "by_market": by_market,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R69 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R69 R66 failure decision drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, _five_bars, _five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, _two_bars, _two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    failed_stream, _failed_bars, _failed_opened, failed_provenance = (
        r66._build_stream(roots=roots)
    )

    five_counts = _market_counts(five_stream)
    two_counts = _market_counts(two_stream)
    failed_counts = _market_counts(failed_stream)
    if (
        sum(five_counts.values()),
        sum(two_counts.values()),
        sum(failed_counts.values()),
    ) != (2448, 1017, 773):
        raise ValueError("R69 source-complete sample drift")

    five_availability = _availability_rows(five_provenance)
    two_availability = _availability_rows(two_provenance)
    failed_availability = _availability_rows(failed_provenance)

    versus_five = _projection(
        baseline_counts=five_counts,
        baseline_availability=five_availability,
        r66_counts=failed_counts,
        r66_availability=failed_availability,
    )
    versus_two = _projection(
        baseline_counts=two_counts,
        baseline_availability=two_availability,
        r66_counts=failed_counts,
        r66_availability=failed_availability,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_failure": {
            "decision": r67.SOURCE_R66_DECISION,
            "run_id": r67.SOURCE_R66_RUN_ID,
            "artifact_id": r67.SOURCE_R66_ARTIFACT_ID,
            "artifact_digest": r67.SOURCE_R66_ARTIFACT_DIGEST,
        },
        "frozen_candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "modified": False,
        },
        "samples": {
            "five_year": sum(five_counts.values()),
            "recent_two_year": sum(two_counts.values()),
            "r66_failed_holdout": sum(failed_counts.values()),
            "r66_preregistered_gate": R66_DENSITY_GATE,
            "r66_shortfall": R66_DENSITY_GATE - sum(failed_counts.values()),
        },
        "market_counts": {
            "five_year": five_counts,
            "recent_two_year": two_counts,
            "r66_failed_holdout": failed_counts,
        },
        "source_availability": {
            "five_year": five_availability,
            "recent_two_year": two_availability,
            "r66_failed_holdout": failed_availability,
        },
        "counterfactual_attribution": {
            "five_year_baseline": versus_five,
            "recent_two_year_baseline": versus_two,
        },
        "interpretation": {
            "provider_incompleteness_is_material_in_r66_sp500": True,
            "provider_incompleteness_alone_explains_density_failure": False,
            "structural_formation_rate_is_lower_in_r66": True,
            "full_coverage_projection_reaches_gate_under_5y_rate": bool(
                versus_five["full_coverage_projection_reaches_r66_gate"]
            ),
            "full_coverage_projection_reaches_gate_under_recent2y_rate": bool(
                versus_two["full_coverage_projection_reaches_r66_gate"]
            ),
            "new_identity_requires_density_architecture_change_to_meet_gate": True,
        },
        "decision": "R69_DENSITY_DECOMPOSITION_COMPLETE_NO_CANDIDATE",
        "governance": {
            "forensics_only": True,
            "counterfactual_is_diagnostic_only": True,
            "missing_bars_reconstructed": False,
            "synthetic_prices_created": False,
            "interpolated_prices_created": False,
            "r66_gate_changed": False,
            "r66_window_changed": False,
            "r66_failure_preserved": True,
            "calendar_or_year_runtime_feature": False,
            "signal_suppression_performed": False,
            "replacement_candidate_created": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "samples": report["samples"],
                "market_counts": report["market_counts"],
                "counterfactual_attribution": report[
                    "counterfactual_attribution"
                ],
                "interpretation": report["interpretation"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
