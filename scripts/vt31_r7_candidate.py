"""VT-31 R7 raid-resolution candidate built from R5/R6 forensics.

R7 is a new research identity. It preserves R5/R6 as rejected and adds only
predecision raid geometry confirmed by consumed-evidence walk-forward.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    _detect_raid,
    _session_bars,
    _structure,
    build_reference_range,
)

CANDIDATE_ID = "VT31_R7_SILVER_BULLET_RAID_RESOLUTION_001"
MARKETS = ("NAS100", "SP500", "US30")
FRICTION = Decimal("0.05")
MAX_SIGNAL_MINUTE = 20
MAX_RISK_TO_REFERENCE = Decimal("0.175")
MIN_CONFIRMATION_BODY_FRACTION = Decimal("0.50")
MIN_RAID_BODY_FRACTION = Decimal("0.35")
MAX_RAID_TO_EXTREME_BARS = 6
TARGET_R = Decimal(2)
FRESH_PARTITION_END = "2018-05-19T00:00:00+00:00"
FRESH_LOOKBACK_DAYS = 760
FORENSIC_FREEZE_SHA = "e2088c7d24cc0a65e41f7150e94854d163b9e0fb"


def contract_payload() -> dict[str, object]:
    """Return the immutable R7 candidate contract."""
    return {
        "candidate_id": CANDIDATE_ID,
        "parent_rejected_candidates": [
            "VT31_R5_SILVER_BULLET_QUALITY_001",
            "VT31_R6_SILVER_BULLET_DD_CONTROL_001",
        ],
        "forensic_freeze_sha": FORENSIC_FREEZE_SHA,
        "source_market": "NAS100",
        "owner_authorized_transfer_markets": ["SP500", "US30"],
        "identical_configuration_across_markets": True,
        "methodology_sources": [
            "youtube:o0v4KQxZbpU",
            "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
            "https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/",
            "https://ttrades.com/protected-swings-and-cisd-how-to-trail-your-stop-loss/",
        ],
        "reference": "09:00-10:00-America/New_York",
        "setup_window": "10:00-11:00-America/New_York",
        "raid": "strict-first-side;both-sides-abstain",
        "confirmation": "R2.6-structural-close-v1",
        "entry_families": ["breaker", "fair-value-gap", "order-block"],
        "entry_selector": "nearest-still-valid-retracement-to-confirmation-close",
        "entry_zone_location": "near-stop",
        "pending_expiry": "11:00-America/New_York",
        "initial_stop": "raid-extreme-no-buffer",
        "target": "fixed-2R",
        "management": "M1-protected-swing-trail",
        "lifecycle": "16:00-America/New_York",
        "same_bar_policy": "censor-unknown-path",
        "gap_policy": "censor-trade",
        "qore_empirical_quality_containment": {
            "first_executable_setup_at_or_before": "10:20-America/New_York",
            "initial_risk_over_09_range_at_most": "0.175",
            "confirmation_direction_aligned": True,
            "confirmation_body_fraction_at_least": "0.50",
            "raid_body_fraction_at_least": "0.35",
            "raid_to_final_extreme_m1_bars_at_most": 6,
        },
        "raid_geometry_definition": {
            "raid_body_fraction": "abs(raid_close-raid_open)/(raid_high-raid_low)",
            "raid_to_final_extreme": "structure.extreme_index-raid.index",
            "observable_by": "structural-confirmation-before-entry",
            "source_rule": False,
            "classification": "qore-empirical-containment-from-leakage-free-walk-forward",
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
        "consumed_walk_forward_expected": {
            "fixed_rule_sample": 256,
            "fixed_rule_stressed_mean_r": "+0.2438",
            "fixed_rule_profit_factor": "1.415",
            "fixed_rule_max_drawdown_r": "9.60",
            "positive_six_month_windows": "7/7",
        },
        "fresh_partition_end_exclusive": FRESH_PARTITION_END,
        "fresh_requested_lookback_days": FRESH_LOOKBACK_DAYS,
        "fresh_minimum_calendar_span_days": 730,
        "fresh_acquisition": "one-shot-after-freeze-and-exact-head-full-qore-green",
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


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _r7_quality(
    prefix: tuple[object, ...], setup: object, reference_width: Decimal
) -> bool:
    instrument = getattr(prefix[0], "instrument")
    signal_at = getattr(setup, "signal_at")
    reference = build_reference_range(
        instrument=instrument,
        as_of=signal_at,
        bars=cast(object, prefix),
    )
    if reference is None:
        return False
    session = _session_bars(signal_at, cast(object, prefix))
    raid = _detect_raid(session, reference)
    if raid is None or (raid.high_taken and raid.low_taken):
        return False
    structure = _structure(session, raid)
    if structure is None:
        return False
    confirmation_index, extreme_index, _, _ = structure
    confirmation = session[confirmation_index]
    raid_bar = session[raid.index]

    raid_open = _d(raid_bar.open)
    raid_close = _d(raid_bar.close)
    raid_high = _d(raid_bar.high)
    raid_low = _d(raid_bar.low)
    raid_span = raid_high - raid_low
    if raid_span <= 0:
        return False
    raid_body_fraction = abs(raid_close - raid_open) / raid_span
    raid_to_extreme_bars = extreme_index - raid.index

    opened = _d(confirmation.open)
    closed = _d(confirmation.close)
    high = _d(confirmation.high)
    low = _d(confirmation.low)
    span = high - low
    if span <= 0:
        return False
    side = getattr(setup, "side").value
    aligned = closed > opened if side == "long" else closed < opened
    confirmation_body_fraction = abs(closed - opened) / span
    risk = cast(Decimal, getattr(setup, "risk"))
    local = signal_at.astimezone(r5.NY)
    signal_minute = local.hour * 60 + local.minute - 10 * 60
    return (
        aligned
        and confirmation_body_fraction >= MIN_CONFIRMATION_BODY_FRACTION
        and signal_minute <= MAX_SIGNAL_MINUTE
        and risk / reference_width <= MAX_RISK_TO_REFERENCE
        and raid_body_fraction >= MIN_RAID_BODY_FRACTION
        and raid_to_extreme_bars <= MAX_RAID_TO_EXTREME_BARS
    )


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
    domain = b"qore:vt31-r7:sha256-domain-separated-moving-block-bootstrap-v1"
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
        "positive_terminal_probability_at_least_0_70": probability >= Decimal("0.70"),
        "p95_max_drawdown_at_most_20r": p95_drawdown <= Decimal(20),
    }


def replay(evidence_paths: dict[str, Path]) -> dict[str, object]:
    """Replay R7 without mutating either rejected candidate identity."""
    r5.CANDIDATE_ID = CANDIDATE_ID
    r5.MAX_SIGNAL_MINUTE = MAX_SIGNAL_MINUTE
    r5.MAX_RISK_TO_REFERENCE = MAX_RISK_TO_REFERENCE
    r5.MIN_CONFIRMATION_BODY_FRACTION = MIN_CONFIRMATION_BODY_FRACTION
    r5.TARGET_R = TARGET_R
    r5._quality = _r7_quality
    result = r5.replay(evidence_paths)
    trades = cast(list[dict[str, object]], result["trades"])
    monte_carlo, monte_carlo_gates = _monte_carlo(trades)
    result.update(
        {
            "schema": "qore.trader_lab.vt31_r7_candidate.v1",
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
        print("usage: vt31_r7_candidate.py NAS100_JSON SP500_JSON US30_JSON")
        return 2
    paths = {market: Path(path) for market, path in zip(MARKETS, args, strict=True)}
    result = replay(paths)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
