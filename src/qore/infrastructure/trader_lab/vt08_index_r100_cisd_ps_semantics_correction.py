"""VT08 Index R100 — CISD / Protected-Swing source semantics correction freeze.

Root-cause finding
------------------
R82/R84 introduced an additional Protected-Swing qualification layer after an
already aligned higher-timeframe POI + lower-timeframe CISD. That extra layer
required either:
- a new lower-timeframe liquidity extreme under a stricter mechanical test; or
- an FVG reaction tied to the original source FVG.

R98 bottleneck attribution proved that this extra gate is the dominant density
collapse:
- generic post-touch CISD + continuation is near/above the Owner density target;
- R84 strict PS qualification removes most of that surface;
- allowing causal M15 FVG reactions recovers only a minority of the loss.

Primary TTrades material distinguishes:
- the core H4->M15 execution sequence: higher-timeframe structure / POI,
  lower-timeframe CISD to confirm the swing/wick, then continuation;
- stronger/explicit Protected-Swing / Ideal-Formation evidence as additional
  confirmation, not a universal prerequisite that invalidates every standard
  CISD-confirmed model.

R100 freezes that semantic correction. It does NOT create a candidate and does
NOT read PnL. The frozen canonical surface is reclassified without changing any
signal:
- STANDARD_CISD_CONFIRMED: every canonical source-faithful opportunity;
- EXPLICIT_PS_MECHANISM_EVIDENCE: R82 liquidity/FVG/both subset;
- STANDARD_WITHOUT_EXTRA_PS_MECHANISM: formerly labelled generic/unqualified.

The old 'UNQUALIFIED_GENERIC_CISD' label is retained only as historical
provenance. It must no longer be interpreted as automatically source-invalid.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
    vt08_index_r98_ps_density_bottleneck_attribution as r98,
)

SCHEMA = "qore.trader_lab.vt08_index_r100_cisd_ps_semantics_correction.v1"
IDENTITY = "VT08_INDEX_R100_CISD_PROTECTED_SWING_SEMANTICS_CORRECTION_001"

SOURCE_R98_RUN_ID = 35553502458
SOURCE_R98_ARTIFACT_ID = 10619516510
SOURCE_R98_ARTIFACT_DIGEST = (
    "sha256:7878ee790fe11f9e8a6965dee74406cad8f5409705c7b1905288bed68788e05e"
)

TTRADES_IC_CISD_URL = (
    "https://ttrades.com/"
    "intracandle-cisd-ic-cisd-improve-your-entries/"
)
TTRADES_WICK_URL = (
    "https://ttrades.com/"
    "let-the-wick-form-trade-the-body-stop-getting-stopped-out/"
)
TTRADES_LONDON_URL = (
    "https://ttrades.com/"
    "how-to-trade-london-using-ttrades-fractal-model/"
)
TTRADES_IDEAL_URL = (
    "https://ttrades.com/"
    "ttrades-ideal-formation-high-probability-swing-points/"
)

STANDARD = "STANDARD_CISD_CONFIRMED"
EXPLICIT = "EXPLICIT_PS_MECHANISM_EVIDENCE"
STANDARD_WITHOUT_EXTRA = "STANDARD_WITHOUT_EXTRA_PS_MECHANISM"


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
        raise ValueError(f"R100 {window_id} canonical sample drift")

    h4_bars = {
        symbol: r82._h4_bar_cache(bars_by_symbol[symbol])
        for symbol in contract.MARKETS
    }
    explicit = 0
    without_extra = 0
    by_market: dict[str, Counter[str]] = {
        symbol: Counter()
        for symbol in contract.MARKETS
    }
    by_anchor: dict[str, Counter[str]] = {}

    for opportunity, _outcome in stream:
        symbol = str(opportunity.signal.symbol)
        classification = r82._classify_opportunity(
            opportunity,
            h4_bars=h4_bars[symbol],
        )
        family = str(classification["family"])
        anchor = str(classification["anchor"])
        by_anchor.setdefault(anchor, Counter())

        by_market[symbol][STANDARD] += 1
        by_anchor[anchor][STANDARD] += 1

        if family == r82.FAMILY_UNQUALIFIED:
            without_extra += 1
            by_market[symbol][STANDARD_WITHOUT_EXTRA] += 1
            by_anchor[anchor][STANDARD_WITHOUT_EXTRA] += 1
        else:
            explicit += 1
            by_market[symbol][EXPLICIT] += 1
            by_anchor[anchor][EXPLICIT] += 1

    if explicit + without_extra != expected:
        raise ValueError(f"R100 {window_id} semantic partition drift")

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "semantic_counts": {
            STANDARD: expected,
            EXPLICIT: explicit,
            STANDARD_WITHOUT_EXTRA: without_extra,
        },
        "old_r82_label_mapping": {
            "old_label": r82.FAMILY_UNQUALIFIED,
            "new_interpretation": STANDARD_WITHOUT_EXTRA,
            "automatically_source_invalid": False,
        },
        "by_market": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_market.items())
        },
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
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
        raise ValueError("R100 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R100 source failure decision drift")
    if r98.IDENTITY != (
        "VT08_INDEX_R98_PROTECTED_SWING_DENSITY_BOTTLENECK_ATTRIBUTION_001"
    ):
        raise ValueError("R100 R98 attribution identity drift")

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
        "primary_sources": {
            "ic_cisd": TTRADES_IC_CISD_URL,
            "wick_body": TTRADES_WICK_URL,
            "london_h4_m15": TTRADES_LONDON_URL,
            "ideal_formation": TTRADES_IDEAL_URL,
        },
        "corrected_source_semantics": {
            "primary_model": "D1_H4_M15",
            "higher_timeframe_poi_required": True,
            "lower_timeframe_cisd_required": True,
            "cisd_confirms_swing_or_wick": True,
            "continuation_required_for_entry": True,
            "explicit_liquidity_or_fvg_ps_mechanism_is_extra_evidence": True,
            "explicit_ps_mechanism_is_universal_gate": False,
            "ideal_formation_is_stronger_confirmation": True,
            "ordinary_valid_c2_c3_can_exist_without_ideal_formation": True,
            "old_unqualified_generic_label_is_source_invalid": False,
            "canonical_surface_changed": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R100_CISD_PS_SEMANTICS_CORRECTED_CANONICAL_SURFACE_PRESERVED",
        "governance": {
            "source_semantics_freeze": True,
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "canonical_signal_surface_changed": False,
            "signals_added": False,
            "signals_suppressed": False,
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
                "five_year": report["five_year"]["semantic_counts"],
                "recent_two_year": report["recent_two_year"]["semantic_counts"],
                "r66": report["r66_failed_holdout"]["semantic_counts"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
