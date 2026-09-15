"""VT-31 R6 drawdown-control candidate built from consumed R5 fresh evidence.

R6 is a new candidate identity.  It does not reuse the R5 approval claim and
must pass a new one-shot historical partition before it can be adjudicated.
This module is validation infrastructure only and does not authorize trading.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5

CANDIDATE_ID = "VT31_R6_SILVER_BULLET_DD_CONTROL_001"
MARKETS = ("NAS100", "SP500", "US30")
FRICTION = Decimal("0.05")
MAX_SIGNAL_MINUTE = 20
MAX_RISK_TO_REFERENCE = Decimal("0.175")
MIN_CONFIRMATION_BODY_FRACTION = Decimal("0.60")
TARGET_R = Decimal("1.7")
FRESH_PARTITION_END = "2020-06-17T00:00:00+00:00"
FRESH_LOOKBACK_DAYS = 760
CONSUMED_R5_RUN_ID = 34925899014
CONSUMED_R5_ARTIFACT_ID = 10380044761
CONSUMED_R5_ARTIFACT_SHA256 = (
    "828335b99cd51c663e3f0f095df5137e881da3d7e8da741da8ca116a0400edf8"
)


def contract_payload() -> dict[str, object]:
    """Return the immutable R6 candidate contract."""
    return {
        "candidate_id": CANDIDATE_ID,
        "parent_rejected_candidate": "VT31_R5_SILVER_BULLET_QUALITY_001",
        "source_market": "NAS100",
        "owner_authorized_transfer_markets": ["SP500", "US30"],
        "identical_configuration_across_markets": True,
        "methodology_sources": [
            "youtube:o0v4KQxZbpU",
            "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
            (
                "https://ttrades.com/stop-loss-mastery-using-protected-swings-"
                "for-precise-invalidations/"
            ),
            (
                "https://ttrades.com/protected-swings-and-cisd-how-to-trail-"
                "your-stop-loss/"
            ),
        ],
        "reference": "09:00-10:00-America/New_York",
        "setup_window": "10:00-11:00-America/New_York",
        "raid": "strict-first-side;both-sides-abstain",
        "confirmation": "R2.6-structural-close-v1",
        "entry_families": ["breaker", "fair-value-gap", "order-block"],
        "entry_selector": (
            "nearest-still-valid-retracement-to-confirmation-close"
        ),
        "entry_zone_location": "near-stop",
        "pending_expiry": "11:00-America/New_York",
        "initial_stop": "raid-extreme-no-buffer",
        "target": "fixed-1.7R-qore-empirical-containment",
        "management": "M1-protected-swing-trail",
        "lifecycle": "16:00-America/New_York",
        "same_bar_policy": "censor-unknown-path",
        "gap_policy": "censor-trade",
        "qore_empirical_quality_containment": {
            "first_executable_setup_at_or_before": "10:20-America/New_York",
            "initial_risk_over_09_range_at_most": "0.175",
            "confirmation_direction_aligned": True,
            "confirmation_body_fraction_at_least": "0.60",
        },
        "friction_r_per_trade": "0.05",
        "minimum_aggregate_sample": 150,
        "minimum_sample_each_market": 30,
        "profit_factor_gate": ">=1.10",
        "max_drawdown_gate_r": "<=20",
        "quartile_gate": ">=3-of-4-positive",
        "market_gate": "every-market-stressed-mean-positive",
        "side_gate": "long-and-short-stressed-mean-positive",
        "temporal_gate": ">=2-of-3-eligible-blocks-positive",
        "monte_carlo": {
            "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": ">=0.70",
            "p95_max_drawdown_r": "<=20",
        },
        "consumed_research_evidence": {
            "r5_fresh_run_id": CONSUMED_R5_RUN_ID,
            "r5_fresh_artifact_id": CONSUMED_R5_ARTIFACT_ID,
            "r5_fresh_artifact_sha256": CONSUMED_R5_ARTIFACT_SHA256,
            "partition": "2020-06-17 through 2022-07-17 boundary",
        },
        "consumed_research_expected_metrics": {
            "sample": 162,
            "stressed_mean_r": "0.2125269605264151002034748334",
            "stressed_profit_factor": "1.385458171110241432087771950",
            "stressed_max_drawdown_r": "8.70000000000000000000000000",
            "monte_carlo_positive_terminal_probability": "0.9815",
            "monte_carlo_p95_max_drawdown_r": "18.66304347826087",
        },
        "fresh_partition_end_exclusive": FRESH_PARTITION_END,
        "fresh_requested_lookback_days": FRESH_LOOKBACK_DAYS,
        "fresh_minimum_calendar_span_days": 730,
        "fresh_acquisition": (
            "one-shot-after-freeze-and-exact-head-full-qore-green"
        ),
        "retuning_after_fresh": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def contract_fingerprint() -> str:
    encoded = json.dumps(
        contract_payload(), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _monte_carlo(
    trades: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, bool]]:
    values = [Decimal(cast(str, item["r_multiple"])) for item in trades]
    n = len(values)
    if n == 0:
        report = {
            "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": "0",
            "p05_terminal_r": "0",
            "p50_terminal_r": "0",
            "p95_max_drawdown_r": "0",
        }
        return report, {
            "positive_terminal_probability_at_least_0_70": False,
            "p95_max_drawdown_at_most_20r": True,
        }
    domain = b"qore:vt31-r6:sha256-domain-separated-moving-block-bootstrap-v1"
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for path_index in range(10000):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(values[(start + offset) % n] for offset in range(5))
            block_index += 1
        equity = Decimal(0)
        peak = Decimal(0)
        drawdown = Decimal(0)
        for value in sampled[:n]:
            equity += value - FRICTION
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        terminals.append(equity)
        drawdowns.append(drawdown)
    terminals.sort()
    drawdowns.sort()

    def quantile(values_: list[Decimal], numerator: int) -> Decimal:
        return values_[(len(values_) - 1) * numerator // 100]

    probability = Decimal(sum(value > 0 for value in terminals)) / Decimal(10000)
    p95_drawdown = quantile(drawdowns, 95)
    report = {
        "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(probability, "f"),
        "p05_terminal_r": format(quantile(terminals, 5), "f"),
        "p50_terminal_r": format(quantile(terminals, 50), "f"),
        "p95_max_drawdown_r": format(p95_drawdown, "f"),
    }
    return report, {
        "positive_terminal_probability_at_least_0_70": probability
        >= Decimal("0.70"),
        "p95_max_drawdown_at_most_20r": p95_drawdown <= Decimal(20),
    }


def replay(evidence_paths: dict[str, Path]) -> dict[str, object]:
    """Replay R6 without changing the source entry/raid implementation."""
    r5.CANDIDATE_ID = CANDIDATE_ID
    r5.MAX_SIGNAL_MINUTE = MAX_SIGNAL_MINUTE
    r5.MAX_RISK_TO_REFERENCE = MAX_RISK_TO_REFERENCE
    r5.MIN_CONFIRMATION_BODY_FRACTION = MIN_CONFIRMATION_BODY_FRACTION
    r5.TARGET_R = TARGET_R
    result = r5.replay(evidence_paths)
    trades = cast(list[dict[str, object]], result["trades"])
    monte_carlo, monte_carlo_gates = _monte_carlo(trades)
    result.update(
        {
            "schema": "qore.trader_lab.vt31_r6_candidate.v1",
            "candidate_id": CANDIDATE_ID,
            "contract": contract_payload(),
            "contract_fingerprint": contract_fingerprint(),
            "monte_carlo": monte_carlo,
            "monte_carlo_gates": monte_carlo_gates,
            "passes_monte_carlo_gates": all(monte_carlo_gates.values()),
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        }
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        print("usage: vt31_r6_candidate.py NAS100_JSON SP500_JSON US30_JSON")
        return 2
    paths = {market: Path(path) for market, path in zip(MARKETS, args, strict=True)}
    result = replay(paths)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
