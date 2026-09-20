"""Frozen VT31 NAS100 structural-target candidate V1.

This module freezes the development-passing target architecture selected from
Capacity Selective Target Ladder V1.

Candidate:
- current causal/base stack remains unchanged;
- 50% structural bank at the frozen 09:00-10:00 reference equilibrium when it
  is a forward level and is touched on a closed M1 strictly before terminal;
- if DOL1 is not reached, the remaining 50% preserves the original terminal;
- if DOL1 is reached, default is to realize the remaining 50% at DOL1;
- exception: when reference volatility was COMPRESSED at entry AND the DOL1
  touch M1 closes beyond DOL1, bank 25% at DOL1 and leave 25% runner;
- runner target = DOL2 (+0.25 frozen reference width);
- runner protection = second confirmed M1 protective swing (PS2), effective
  from the next M1;
- stop can only improve or hold, never widen;
- same-bar runner stop/target = STOP FIRST;
- no future journey label, date, fold identity or terminal PnL at runtime.

The candidate is frozen for extended consumed validation. It is NOT certified,
fresh, live or production-authorized.
"""
# ruff: noqa: I001
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_capacity_selective_target_ladder_v1 as frontier
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_2 import (
    METHODOLOGY_ID,
    SOURCE_SHA256,
    source_fingerprint,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
)

SCHEMA = "qore.vt31.nas100.structural_target_candidate.v1"
CANDIDATE_ID = "VT31_NAS100_STRUCTURAL_TARGET_V1"
SELECTED_VARIANT = "EQ50_COMPRESSED_ACCEPT_RUN25"

FROZEN_DEVELOPMENT_EVIDENCE = {
    "r5": {
        "artifact_id": 10380044761,
        "sha256": (
            "7b1e3d9e2bfd17ccc6f043befabf464838d150bc6034ced1f76a24ee248611d7"
        ),
    },
    "r6": {
        "artifact_id": 10389112524,
        "sha256": (
            "cf3ef22fa86916bfb2826f4fa48c7a9655b9509c76a05d9bb26d0d4cb6069581"
        ),
    },
    "r8": {
        "artifact_id": 10402199719,
        "sha256": (
            "4031c7e21bb311fdb99d7b1028fd9ff154ace1dc4886249ff978b700fdeeedcb"
        ),
    },
    "consumed_holdout": {
        "artifact_id": 10557487418,
        "sha256": (
            "acf2fa327a68a5a6d977dfdbc9c696cb13db6e0e7550b9da386f3699b5cf8d09"
        ),
    },
}


def contract() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "selected_variant": SELECTED_VARIANT,
        "market": "NAS100",
        "methodology_id": METHODOLOGY_ID,
        "source_sha256": SOURCE_SHA256,
        "source_fingerprint": source_fingerprint(),
        "base_stack": {
            "allocation": "ALLOC_G_CORE_FAMILY_050",
            "state_shield": "SHIELD_060",
            "breaker_management": "LOCK025_AFTER_CLOSED_1R",
            "loss_cluster_refined_multiplier": "0.35",
            "breaker_regime_multiplier": "0.35",
        },
        "target_architecture": {
            "equilibrium_bank_fraction": "0.50",
            "equilibrium_source": "frozen-09:00-10:00-reference-midpoint",
            "equilibrium_requires_strictly_earlier_closed_m1": True,
            "dol1_default_remaining_bank_fraction": "0.50",
            "runner_selector": (
                "reference_volatility_state=compressed AND "
                "DOL1-touch-M1-close-beyond-DOL1"
            ),
            "runner_selector_known_by": "DOL1-touch-M1-close",
            "runner_effective_from": "next-M1",
            "runner_dol1_bank_fraction": "0.25",
            "runner_fraction": "0.25",
            "runner_target": "DOL2_PLUS_0.25_FROZEN_REFERENCE_WIDTH",
            "runner_protection": "PS2_CONFIRMED_M1_NEXT_BAR_EFFECTIVE",
            "stop_can_only_improve_or_hold": True,
            "same_bar_runner_precedence": "STOP_FIRST",
        },
        "runtime_forbidden_inputs": (
            "future-journey-label",
            "terminal-pnl",
            "fold-identity",
            "calendar-date-as-edge-feature",
        ),
        "development_evidence": FROZEN_DEVELOPMENT_EVIDENCE,
    }


def contract_fingerprint() -> str:
    encoded = json.dumps(
        contract(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evaluate(
    path: Path,
    *,
    partition: str,
    include_rows: bool = False,
) -> dict[str, object]:
    rows, evidence, diagnostics, source_stats = alt._current_rows(path)
    (
        series,
        account,
        fingerprint,
        checked,
        evidence_sha,
        provider,
    ) = frontier.load_market_evidence(path)

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: item.opened_at)
        )
        for local_day, items in raw.items()
    }

    adjusted, ladder_diag = frontier._apply(
        rows,
        by_day=by_day,
        variant=SELECTED_VARIANT,
    )
    metrics = residual._metrics(adjusted)
    mc = engine._monte_carlo(
        adjusted,
        variant=f"{CANDIDATE_ID}:{partition}",
    )

    annual = (
        annuals._annual_blocks(
            adjusted,
            start=date(2022, 7, 18),
            years=2,
        )
        if partition == "consumed_holdout"
        else []
    )

    result: dict[str, object] = {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "selected_variant": SELECTED_VARIANT,
        "contract_fingerprint": contract_fingerprint(),
        "trade_count": len(adjusted),
        "metrics": metrics,
        "monte_carlo": mc,
        "annual_blocks": annual,
        "ladder_diagnostics": ladder_diag,
        "source_stats": source_stats,
        "diagnostics": diagnostics,
        "evidence": {
            **evidence,
            "account_fingerprint": account,
            "evidence_fingerprint": fingerprint,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "candidate_frozen": True,
            "parameters_mutable_inside_extended_validation": False,
            "future_journey_runtime_input": False,
            "stop_widened": False,
            "silver_bullet_changed": False,
            "opens_new_holdout": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    if include_rows:
        result["trade_rows"] = [
            dict(row)
            for row in sorted(
                adjusted,
                key=lambda item: cast(str, item["signal_at"]),
            )
        ]
    return result


def freeze_payload() -> dict[str, object]:
    return {
        "schema": f"{SCHEMA}.freeze",
        "candidate": contract(),
        "contract_fingerprint": contract_fingerprint(),
        "development_gates": {
            "trade_count_per_fold": "300-350",
            "profit_factor_minimum": "1.50",
            "observed_dd_max_r": "6",
            "mc_positive_terminal_minimum": "0.90",
            "mc_p95_dd_max_r": "15",
            "consumed_both_years_positive": True,
        },
        "extended_5y_gates": {
            "trade_count": "800-900",
            "profit_factor_minimum": "1.50",
            "observed_dd_max_r": "6",
            "all_five_year_blocks_positive": True,
            "mc_positive_terminal_minimum": "0.90",
            "mc_p95_dd_max_r": "15",
            "total_r_positive": True,
        },
        "governance": {
            "frozen_for_extended_validation": True,
            "five_year_opened": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
