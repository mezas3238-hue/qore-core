"""Frozen VT31 NAS100 Structural Target Intelligence candidate V1.

Candidate:
    VT31_NAS100_STRUCTURAL_TARGET_INTELLIGENCE_V1

Frozen development survivor:
    EQ40_PS1_DOL140_RUN20_DOL2_PS2

Root-corrected target architecture:
- existing VT31 strongest causal stack remains the admission/risk base;
- if the frozen 09:00-10:00 reference equilibrium is reached on a CLOSED M1
  strictly before the original terminal, bank 40%;
- protect the remaining pre-DOL1 journey with the FIRST confirmed M1
  protective swing (PS1), effective from the next M1;
- original terminal remains binding unless an earlier protective improvement
  or valid DOL1 event occurs;
- at DOL1, bank 40%;
- leave 20% runner toward DOL2 (+0.25 reference width);
- post-DOL1 runner uses PS2 structural protection;
- same-bar stop/target ambiguity is fail-closed STOP FIRST;
- no trade resurrection, stop widening, future-label runtime input, calendar
  rule or fold-identity rule.

Research/certification only. No live, production or real-capital authority.
"""
# ruff: noqa: B009
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_post_equilibrium_structural_protection_frontier_v2 as policy
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.structural_target_intelligence_candidate.v1"
CANDIDATE_ID = "VT31_NAS100_STRUCTURAL_TARGET_INTELLIGENCE_V1"
MARKET = "NAS100"
FROZEN_VARIANT = "EQ40_PS1_DOL140_RUN20_DOL2_PS2"

EQ_FRACTION = Decimal("0.40")
DOL1_FRACTION = Decimal("0.40")
RUNNER_FRACTION = Decimal("0.20")
EQ_PS_CONFIRMATIONS = 1

DEVELOPMENT_RUN_ID = 35519420549
DEVELOPMENT_HEAD_SHA = "4db6ea995ca43a3cc69d4338f04d2c752847ee9b"
DEVELOPMENT_AGGREGATE_ARTIFACT_ID = 10607289010
DEVELOPMENT_AGGREGATE_DIGEST = (
    "sha256:b436bff59a6cecfb176cba1a57e9ba53a06f66454e770bfcc2fdd6644fecefad"
)

DEVELOPMENT_RESULT = {
    "consumed": {
        "trade_count": 334,
        "profit_factor": "2.0881615529794195",
        "max_drawdown_r": "2.9101320845188896",
        "total_r": "14.842362152946336",
        "mc_positive_terminal_probability": "0.9155",
        "mc_p95_max_drawdown_r": "8.336538869236623",
        "both_years_positive": True,
    },
    "r5": {
        "trade_count": 350,
        "profit_factor": "5.471750305721373",
        "max_drawdown_r": "2.838129364909111",
        "total_r": "36.09047213257967",
        "mc_positive_terminal_probability": "0.9986",
    },
    "r6": {
        "trade_count": 334,
        "profit_factor": "2.987933106253374",
        "max_drawdown_r": "2.80728098644615",
        "total_r": "21.6613876962916",
        "mc_positive_terminal_probability": "0.9622",
    },
    "r8": {
        "trade_count": 300,
        "profit_factor": "3.721189524094895",
        "max_drawdown_r": "2.4968113629240363",
        "total_r": "22.83987631368507",
        "mc_positive_terminal_probability": "0.9815",
    },
}

FIVE_YEAR_GATES = {
    "trade_count_min": 800,
    "trade_count_max": 900,
    "profit_factor_min": "1.50",
    "total_r_min_exclusive": "0",
    "observed_max_drawdown_r_max": "6.00",
    "all_five_year_blocks_positive": True,
    "mc_positive_terminal_probability_min": "0.90",
    "mc_p95_max_drawdown_r_max": "15.00",
}


def frozen_rows(
    evidence_path: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows, _evidence, _diagnostics, _stats = alt._current_rows(
        evidence_path
    )
    series, *_ = load_market_evidence(evidence_path)

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(
                items,
                key=lambda item: getattr(item, "opened_at"),
            )
        )
        for local_day, items in raw.items()
    }

    adjusted, diagnostics = policy._apply(
        rows,
        by_day=by_day,
        eq_fraction=EQ_FRACTION,
        dol1_fraction=DOL1_FRACTION,
        runner_fraction=RUNNER_FRACTION,
        eq_ps_confirmations=EQ_PS_CONFIRMATIONS,
    )
    return adjusted, diagnostics


def contract_payload() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "market": MARKET,
        "methodology": (
            "VT31-AM-SILVER-BULLET-STRUCTURAL-TARGET-INTELLIGENCE"
        ),
        "timezone": "America/New_York",
        "source_granularity": "closed-M1",
        "silver_bullet_frozen": True,
        "frozen_variant": FROZEN_VARIANT,
        "target_policy": {
            "equilibrium_bank_fraction": format(EQ_FRACTION, "f"),
            "post_equilibrium_protection": "PS1",
            "dol1_bank_fraction": format(DOL1_FRACTION, "f"),
            "runner_fraction": format(RUNNER_FRACTION, "f"),
            "runner_destination": "DOL2_PLUS_0_25_REFERENCE_WIDTH",
            "post_dol1_runner_protection": "PS2",
            "same_bar_stop_target_precedence": "STOP_FIRST",
            "original_terminal_preserved": True,
            "no_trade_resurrection": True,
            "stop_can_only_improve_or_hold": True,
            "stop_widened": False,
        },
        "development_binding": {
            "run_id": DEVELOPMENT_RUN_ID,
            "head_sha": DEVELOPMENT_HEAD_SHA,
            "aggregate_artifact_id": DEVELOPMENT_AGGREGATE_ARTIFACT_ID,
            "aggregate_digest": DEVELOPMENT_AGGREGATE_DIGEST,
            "development_result": DEVELOPMENT_RESULT,
        },
        "five_year_validation": {
            "window_start": "2017-07-01",
            "window_end_exclusive": "2022-07-01",
            "fresh": False,
            "status": "CONSUMED_EXTENDED_VALIDATION",
            "parameters_retuned_inside_5y": False,
            "gates": FIVE_YEAR_GATES,
        },
        "causal_firewall": {
            "future_bars_as_runtime_input": False,
            "terminal_pnl_oracle": False,
            "fold_identity_rule": False,
            "calendar_rule": False,
            "trade_resurrection": False,
        },
        "candidate_frozen": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def contract_fingerprint() -> str:
    encoded = json.dumps(
        contract_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def replay(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    rows, diagnostics = frozen_rows(evidence_path)
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "contract_fingerprint": contract_fingerprint(),
        "partition": partition,
        "trade_count": len(rows),
        "metrics": residual._metrics(rows),
        "monte_carlo": engine._monte_carlo(
            rows,
            variant=f"{CANDIDATE_ID}:{partition}",
        ),
        "policy_diagnostics": diagnostics,
        "candidate_frozen": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path)
    parser.add_argument("--partition", default="frozen_candidate")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        print(
            json.dumps(
                {
                    "candidate_id": CANDIDATE_ID,
                    "contract_fingerprint": contract_fingerprint(),
                    "frozen_variant": FROZEN_VARIANT,
                    "development_run_id": DEVELOPMENT_RUN_ID,
                    "development_aggregate_artifact_id": (
                        DEVELOPMENT_AGGREGATE_ARTIFACT_ID
                    ),
                    "five_year_gates": FIVE_YEAR_GATES,
                },
                sort_keys=True,
            )
        )
        return

    if args.evidence is None:
        parser.error(
            "evidence path is required unless --self-test is used"
        )

    payload = replay(
        args.evidence,
        partition=args.partition,
    )
    encoded = json.dumps(
        payload,
        sort_keys=True,
        indent=2,
    ) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            encoded,
            encoding="utf-8",
        )
    print(encoded, end="")


if __name__ == "__main__":
    main()
