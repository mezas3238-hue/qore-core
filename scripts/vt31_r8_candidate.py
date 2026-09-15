"""VT-31 R8 fast-raid tail-control candidate.

R8 is a new identity derived from the rejected R7 tail forensics. It preserves
all R7 methodology and economic gates, but tightens the predecision
raid-to-final-extreme containment from six M1 bars to four. The rule was
predeclared only after adjacent-threshold tail forensics showed <=3m and <=4m
passing the unchanged Monte Carlo p95 drawdown gate while >=5m failed.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
import vt31_r7_candidate as r7

CANDIDATE_ID = "VT31_R8_SILVER_BULLET_FAST_RAID_TAIL_CONTROL_001"
MARKETS = ("NAS100", "SP500", "US30")
FRICTION = Decimal("0.05")
MAX_SIGNAL_MINUTE = 20
MAX_RISK_TO_REFERENCE = Decimal("0.175")
MIN_CONFIRMATION_BODY_FRACTION = Decimal("0.50")
MIN_RAID_BODY_FRACTION = Decimal("0.35")
MAX_RAID_TO_EXTREME_BARS = 4
TARGET_R = Decimal(2)
FRESH_PARTITION_END = "2018-05-19T00:00:00+00:00"
FRESH_LOOKBACK_DAYS = 760
FORENSIC_FREEZE_SHA = "5302b0df71bec336b914284aab87cd37030708ca"
R7_TAIL_FORENSICS_RUN_ID = 34970594926
R7_TAIL_FORENSICS_ARTIFACT_ID = 10397666524


def contract_payload() -> dict[str, object]:
    """Return the immutable R8 candidate contract."""
    payload = r7.contract_payload()
    payload.update(
        {
            "candidate_id": CANDIDATE_ID,
            "parent_rejected_candidates": [
                "VT31_R5_SILVER_BULLET_QUALITY_001",
                "VT31_R6_SILVER_BULLET_DD_CONTROL_001",
                "VT31_R7_SILVER_BULLET_RAID_RESOLUTION_001",
            ],
            "forensic_freeze_sha": FORENSIC_FREEZE_SHA,
            "target": "fixed-2R",
            "friction_r_per_trade": "0.05",
            "fresh_partition_end_exclusive": FRESH_PARTITION_END,
            "fresh_requested_lookback_days": FRESH_LOOKBACK_DAYS,
            "retuning_after_fresh": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        }
    )
    containment = cast(
        dict[str, object], payload["qore_empirical_quality_containment"]
    )
    containment["raid_to_final_extreme_m1_bars_at_most"] = MAX_RAID_TO_EXTREME_BARS
    geometry = cast(dict[str, object], payload["raid_geometry_definition"])
    geometry["classification"] = (
        "qore-empirical-tail-control-confirmed-by-consumed-walk-forward-and-"
        "adjacent-threshold-monte-carlo"
    )
    payload["consumed_walk_forward_expected"] = {
        "fixed_rule_sample": 213,
        "fixed_rule_stressed_mean_r": "+0.2651",
        "fixed_rule_profit_factor": "1.459",
        "fixed_rule_max_drawdown_r": "8.70",
        "positive_six_month_windows": "7/7",
        "monte_carlo_positive_terminal_probability": "0.9964",
        "monte_carlo_p95_max_drawdown_r": "19.1333",
    }
    payload["r7_tail_forensics"] = {
        "run_id": R7_TAIL_FORENSICS_RUN_ID,
        "artifact_id": R7_TAIL_FORENSICS_ARTIFACT_ID,
        "forensic_rule": (
            "least-restrictive adjacent passing duration: <=4m; <=3m also "
            "passes; >=5m neighborhood fails p95 DD"
        ),
        "duration_3m_p95_dd_r": "17.7794",
        "duration_4m_p95_dd_r": "19.1333",
        "duration_5m_p95_dd_r": "22.4130",
        "duration_6m_p95_dd_r": "20.7794",
        "gate_r": "<=20",
    }
    return payload


def contract_fingerprint() -> str:
    encoded = json.dumps(
        contract_payload(), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _configure_parent() -> None:
    r7.CANDIDATE_ID = CANDIDATE_ID
    r7.MAX_SIGNAL_MINUTE = MAX_SIGNAL_MINUTE
    r7.MAX_RISK_TO_REFERENCE = MAX_RISK_TO_REFERENCE
    r7.MIN_CONFIRMATION_BODY_FRACTION = MIN_CONFIRMATION_BODY_FRACTION
    r7.MIN_RAID_BODY_FRACTION = MIN_RAID_BODY_FRACTION
    r7.MAX_RAID_TO_EXTREME_BARS = MAX_RAID_TO_EXTREME_BARS
    r7.TARGET_R = TARGET_R
    r5.CANDIDATE_ID = CANDIDATE_ID
    r5.MAX_SIGNAL_MINUTE = MAX_SIGNAL_MINUTE
    r5.MAX_RISK_TO_REFERENCE = MAX_RISK_TO_REFERENCE
    r5.MIN_CONFIRMATION_BODY_FRACTION = MIN_CONFIRMATION_BODY_FRACTION
    r5.TARGET_R = TARGET_R
    r5._quality = r7._r7_quality


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
    domain = b"qore:vt31-r8:sha256-domain-separated-moving-block-bootstrap-v1"
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
    """Replay exact R8 over one three-market evidence tranche."""
    _configure_parent()
    result = r5.replay(evidence_paths)
    trades = cast(list[dict[str, object]], result["trades"])
    monte_carlo, monte_carlo_gates = _monte_carlo(trades)
    result.update(
        {
            "schema": "qore.trader_lab.vt31_r8_candidate.v1",
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
        print("usage: vt31_r8_candidate.py NAS100_JSON SP500_JSON US30_JSON")
        return 2
    paths = {market: Path(path) for market, path in zip(MARKETS, args, strict=True)}
    result = replay(paths)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
