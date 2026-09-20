"""VT08 Index R99 — canonical STANDARD/PS-qualified wick-state census.

R98 showed that even a persistent, cross-H4 dynamic Protected-Swing lifecycle
cannot supply the Owner density contract by itself. The next source question is
not another way to stretch PS lifetime: TTrades distinguishes ordinary valid
closures from stronger Protected-Swing/Ideal-Formation confirmation and also
distinguishes expansion-like small opposing wicks from reversal-like large
opposing wicks.

R99 does not create a routing rule. It classifies the exact frozen canonical
surface (2448 / 1017 / 773) using only information available at signal time.

For each canonical opportunity:
- reuse R82 to classify the existing PS/CISD evidence as source-qualified
  (liquidity sweep and/or original-FVG reaction) or generic CISD;
- measure the H4 adverse run observed through signal time versus the directional
  body from H4 open to canonical entry;
- classify:
    SMALL_WICK_EXPANSION when directional body > adverse run,
    LARGE_WICK_REVERSAL when adverse run > directional body,
    EQUAL_FAIL_CLOSED on equality;
- report the cross-product with canonical model kind, market, side and anchor.

The comparison is deliberately ratio-free: no percentage threshold is searched
or fitted. No PnL is read and no signals are added/suppressed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r98_cross_h4_dynamic_poi_lifecycle as r98,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r99_standard_ideal_wick_state.v1"
IDENTITY = "VT08_INDEX_R99_STANDARD_PS_QUALIFIED_WICK_STATE_CENSUS_001"

SOURCE_R98_RUN_ID = 35535639692
SOURCE_R98_ARTIFACT_ID = 10612860698
SOURCE_R98_ARTIFACT_DIGEST = (
    "sha256:c51e7dd0351c8e677f368cda182e13fceafaf926b0b39ca203720d7f6d0368bf"
)

SMALL_WICK = "SMALL_WICK_EXPANSION"
LARGE_WICK = "LARGE_WICK_REVERSAL"
EQUAL_WICK = "EQUAL_FAIL_CLOSED"
QUALIFIED = "SOURCE_QUALIFIED_PS"
GENERIC = "GENERIC_CISD"


def _wick_state(
    observed: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    h4_open: Decimal,
    entry: Decimal,
) -> tuple[str, Decimal, Decimal]:
    if not observed:
        raise ValueError("R99 wick state requires observed M15 bars")

    if side is DemoTradingSetupSide.LONG:
        adverse = max(
            Decimal(),
            h4_open - min(bar.low for bar in observed),
        )
        directional = max(Decimal(), entry - h4_open)
    else:
        adverse = max(
            Decimal(),
            max(bar.high for bar in observed) - h4_open,
        )
        directional = max(Decimal(), h4_open - entry)

    if directional > adverse:
        state = SMALL_WICK
    elif adverse > directional:
        state = LARGE_WICK
    else:
        state = EQUAL_WICK
    return state, adverse, directional


def _ps_state(family: str) -> str:
    return GENERIC if family == r82.FAMILY_UNQUALIFIED else QUALIFIED


def _observed_through_signal(
    inside: Sequence[Vt08IndexC2R1Bar],
    *,
    signal_at: datetime,
) -> tuple[Vt08IndexC2R1Bar, ...]:
    cutoff = signal_at.astimezone(UTC)
    rows = tuple(
        bar
        for bar in inside
        if bar.closed_at.astimezone(UTC) <= cutoff
    )
    if not rows:
        raise ValueError("R99 signal predates all H4 M15 bars")
    return rows


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    _start, _end, expected = r74._window_contract(window_id)
    if len(stream) != expected:
        raise ValueError(f"R99 {window_id} canonical sample drift")

    h4_bars_by_symbol = {
        symbol: r82._h4_bar_cache(bars_by_symbol[symbol])
        for symbol in contract.MARKETS
    }

    wick_counts: Counter[str] = Counter()
    ps_counts: Counter[str] = Counter()
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    by_model: dict[str, Counter[str]] = defaultdict(Counter)
    by_market: dict[str, Counter[str]] = defaultdict(Counter)
    by_anchor: dict[str, Counter[str]] = defaultdict(Counter)
    by_side: dict[str, Counter[str]] = defaultdict(Counter)
    body_gt_zero = 0

    for opportunity, _outcome in stream:
        signal = opportunity.signal
        symbol = str(signal.symbol)
        inside = h4_bars_by_symbol[symbol].get(
            signal.h4_opened_at.astimezone(UTC)
        )
        if inside is None:
            raise ValueError("R99 canonical H4 missing")

        qualification = r82._classify_opportunity(
            opportunity,
            h4_bars=h4_bars_by_symbol[symbol],
        )
        ps_state = _ps_state(str(qualification["family"]))
        observed = _observed_through_signal(
            inside,
            signal_at=signal.signal_at,
        )
        wick_state, adverse, directional = _wick_state(
            observed,
            side=signal.side,
            h4_open=inside[0].open,
            entry=signal.entry,
        )
        body_gt_zero += int(directional > 0)

        wick_counts[wick_state] += 1
        ps_counts[ps_state] += 1
        matrix[wick_state][ps_state] += 1

        model_kind = signal.model_kind.value
        composite = f"{wick_state}|{ps_state}"
        by_model[model_kind][composite] += 1
        by_market[symbol][composite] += 1
        by_anchor[
            str(signal.h4_opened_at.astimezone(v7._NY).hour)
        ][composite] += 1
        by_side[signal.side.value][composite] += 1

        if adverse < 0 or directional < 0:
            raise ValueError("R99 negative geometry impossible")

    if sum(wick_counts.values()) != expected:
        raise ValueError(f"R99 {window_id} wick count drift")
    if sum(ps_counts.values()) != expected:
        raise ValueError(f"R99 {window_id} PS count drift")

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "wick_state_counts": dict(sorted(wick_counts.items())),
        "ps_state_counts": dict(sorted(ps_counts.items())),
        "wick_ps_matrix": {
            wick: dict(sorted(counter.items()))
            for wick, counter in sorted(matrix.items())
        },
        "directional_body_positive_count": body_gt_zero,
        "directional_body_nonpositive_count": expected - body_gt_zero,
        "by_model_kind": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_model.items())
        },
        "by_market": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_market.items())
        },
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
        "by_side": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_side.items())
        },
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R99 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R99 source failure decision drift")
    if r98.IDENTITY != (
        "VT08_INDEX_R98_CROSS_H4_DYNAMIC_POI_LIFECYCLE_001"
    ):
        raise ValueError("R99 R98 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r98": {
            "run_id": SOURCE_R98_RUN_ID,
            "artifact_id": SOURCE_R98_ARTIFACT_ID,
            "artifact_digest": SOURCE_R98_ARTIFACT_DIGEST,
        },
        "classification_contract": {
            "canonical_surface_changed": False,
            "wick_measurement": (
                "signal-time H4 adverse run versus directional body from H4 open"
            ),
            "small_wick_rule": "directional_body > adverse_run",
            "large_wick_rule": "adverse_run > directional_body",
            "equal_rule": "FAIL_CLOSED_DIAGNOSTIC",
            "numeric_percentage_threshold": None,
            "source_qualified_ps": [
                r82.FAMILY_LIQUIDITY,
                r82.FAMILY_FVG,
                r82.FAMILY_BOTH,
            ],
            "generic_cisd": r82.FAMILY_UNQUALIFIED,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R99_STANDARD_PS_QUALIFIED_WICK_STATE_CENSUS_COMPLETE_NO_RULE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "canonical_signal_surface_changed": False,
            "signals_added": False,
            "signals_suppressed": False,
            "numeric_threshold_search": False,
            "pnl_evaluated": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
            "candidate_created": False,
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
                "five_year": {
                    "wick_state_counts": report["five_year"][
                        "wick_state_counts"
                    ],
                    "ps_state_counts": report["five_year"]["ps_state_counts"],
                    "wick_ps_matrix": report["five_year"]["wick_ps_matrix"],
                },
                "recent_two_year": {
                    "wick_state_counts": report["recent_two_year"][
                        "wick_state_counts"
                    ],
                    "ps_state_counts": report["recent_two_year"][
                        "ps_state_counts"
                    ],
                    "wick_ps_matrix": report["recent_two_year"][
                        "wick_ps_matrix"
                    ],
                },
                "r66": {
                    "wick_state_counts": report["r66_failed_holdout"][
                        "wick_state_counts"
                    ],
                    "ps_state_counts": report["r66_failed_holdout"][
                        "ps_state_counts"
                    ],
                    "wick_ps_matrix": report["r66_failed_holdout"][
                        "wick_ps_matrix"
                    ],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
