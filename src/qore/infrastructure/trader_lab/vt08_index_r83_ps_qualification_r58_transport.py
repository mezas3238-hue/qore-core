"""VT08 Index R83 — Protected-Swing qualification x R58 risk transport.

R82 showed that roughly 70% of the canonical source-complete signal surface is
not mechanically attributable to either of the two source-observable Protected
Swing causes frozen for this audit: a liquidity-forming new high/low or a
reaction at the original FVG POI.

R83 does not suppress those trades and does not create a candidate. It applies
the exact frozen R47 -> R58 allocator to the unchanged canonical 5Y, recent2Y
and failed R66 surfaces, then decomposes effective risk and stressed economics
by the R82 Protected-Swing qualification families.

The purpose is causal diagnosis:
- does R58 add or remove effective weight by source qualification family?
- what fraction of cumulative effective weight is carried by source-qualified
  vs generic-CISD signals?
- does allocator transport failure coincide with risk being promoted on a
  structurally unqualified family?

No family is selected by PnL and no rule is changed here.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
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
    vt08_index_r80_source_2r_target_transport as r80,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
SCHEMA = "qore.trader_lab.vt08_index_r83_ps_qualification_r58_transport.v1"
IDENTITY = "VT08_INDEX_R83_PROTECTED_SWING_QUALIFICATION_R58_TRANSPORT_001"

SOURCE_R82_RUN_ID = 35519594414
SOURCE_R82_ARTIFACT_ID = 10607673530
SOURCE_R82_ARTIFACT_DIGEST = (
    "sha256:dcbce476da4516912c013a1aef3e074cdaf1e2fe2c50b33a17c5a0c7792ddda9"
)

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
QUALIFIED_FAMILIES = (
    r82.FAMILY_LIQUIDITY,
    r82.FAMILY_FVG,
    r82.FAMILY_BOTH,
)


def _identity(item: r15.AssignedTrade) -> tuple[object, ...]:
    return item.opportunity.identity()


def _metrics(
    rows: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    return r80._weighted_metrics(rows, stress=stress)


def _weight_stats(
    base_rows: Sequence[r15.AssignedTrade],
    final_rows: Sequence[r15.AssignedTrade],
) -> dict[str, Any]:
    base_by_id = {_identity(item): item for item in base_rows}
    final_by_id = {_identity(item): item for item in final_rows}
    if set(base_by_id) != set(final_by_id):
        raise ValueError("R83 family base/final identity drift")
    if not final_rows:
        return {
            "sample": 0,
            "base_total_weight": "0",
            "base_mean_weight": "0",
            "r58_total_weight": "0",
            "r58_mean_weight": "0",
            "r58_minus_r47_total_weight": "0",
            "risk_increase_count": 0,
            "risk_decrease_count": 0,
            "risk_unchanged_count": 0,
            "floor_weight_count": 0,
            "cap_weight_count": 0,
        }

    base_total = sum((item.weight for item in base_rows), Decimal())
    final_total = sum((item.weight for item in final_rows), Decimal())
    increased = 0
    decreased = 0
    unchanged = 0
    floor_count = 0
    cap_count = 0

    for identity, final in final_by_id.items():
        base = base_by_id[identity]
        if final.weight > base.weight:
            increased += 1
        elif final.weight < base.weight:
            decreased += 1
        else:
            unchanged += 1
        floor_count += int(final.weight == r55.MIN_EFFECTIVE_WEIGHT)
        cap_count += int(final.weight == r55.MAX_REQUESTED_WEIGHT)

    sample = len(final_rows)
    return {
        "sample": sample,
        "base_total_weight": str(base_total),
        "base_mean_weight": str(base_total / Decimal(sample)),
        "r58_total_weight": str(final_total),
        "r58_mean_weight": str(final_total / Decimal(sample)),
        "r58_minus_r47_total_weight": str(final_total - base_total),
        "risk_increase_count": increased,
        "risk_decrease_count": decreased,
        "risk_unchanged_count": unchanged,
        "floor_weight_count": floor_count,
        "cap_weight_count": cap_count,
    }


def _family_report(
    base_rows: Sequence[r15.AssignedTrade],
    final_rows: Sequence[r15.AssignedTrade],
    *,
    total_final_weight: Decimal,
    canonical_sample: int,
) -> dict[str, Any]:
    weight = _weight_stats(base_rows, final_rows)
    family_total = Decimal(str(weight["r58_total_weight"]))
    return {
        **weight,
        "sample_share": (
            str(Decimal(len(final_rows)) / Decimal(canonical_sample))
            if canonical_sample
            else "0"
        ),
        "cumulative_effective_weight_share": (
            str(family_total / total_final_weight)
            if total_final_weight
            else "0"
        ),
        "r47_primary": _metrics(base_rows, stress=PRIMARY_STRESS),
        "r47_secondary": _metrics(base_rows, stress=SECONDARY_STRESS),
        "r58_primary": _metrics(final_rows, stress=PRIMARY_STRESS),
        "r58_secondary": _metrics(final_rows, stress=SECONDARY_STRESS),
    }


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
        raise ValueError(f"R83 {window_id} canonical sample drift")

    base, base_diagnostics = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars_by_symbol,
    )
    final, r58_diagnostics = r55._apply_candidate(
        base,
        bars_by_symbol=bars_by_symbol,
    )
    base = tuple(base)
    final = tuple(final)
    if len(base) != expected or len(final) != expected:
        raise ValueError(f"R83 {window_id} allocator changed sample")

    base_by_id = {_identity(item): item for item in base}
    if len(base_by_id) != expected:
        raise ValueError(f"R83 {window_id} R47 identity collision")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }
    final_groups: dict[str, list[r15.AssignedTrade]] = defaultdict(list)
    base_groups: dict[str, list[r15.AssignedTrade]] = defaultdict(list)

    for item in final:
        classification = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        family = str(classification["family"])
        final_groups[family].append(item)
        base_groups[family].append(base_by_id[_identity(item)])

    if sum(len(rows) for rows in final_groups.values()) != expected:
        raise ValueError(f"R83 {window_id} family grouping drift")

    total_final_weight = sum((item.weight for item in final), Decimal())
    family_reports = {
        family: _family_report(
            base_groups[family],
            final_groups[family],
            total_final_weight=total_final_weight,
            canonical_sample=expected,
        )
        for family in r82.FAMILIES
    }

    qualified_final = tuple(
        item
        for family in QUALIFIED_FAMILIES
        for item in final_groups[family]
    )
    qualified_base = tuple(
        item
        for family in QUALIFIED_FAMILIES
        for item in base_groups[family]
    )
    unqualified_final = tuple(final_groups[r82.FAMILY_UNQUALIFIED])
    unqualified_base = tuple(base_groups[r82.FAMILY_UNQUALIFIED])

    qualified = _family_report(
        qualified_base,
        qualified_final,
        total_final_weight=total_final_weight,
        canonical_sample=expected,
    )
    unqualified = _family_report(
        unqualified_base,
        unqualified_final,
        total_final_weight=total_final_weight,
        canonical_sample=expected,
    )

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "r47_total_effective_weight": str(
            sum((item.weight for item in base), Decimal())
        ),
        "r58_total_effective_weight": str(total_final_weight),
        "r58_whole_window": {
            "primary": _metrics(final, stress=PRIMARY_STRESS),
            "secondary": _metrics(final, stress=SECONDARY_STRESS),
        },
        "r47_whole_window": {
            "primary": _metrics(base, stress=PRIMARY_STRESS),
            "secondary": _metrics(base, stress=SECONDARY_STRESS),
        },
        "source_qualified_union": qualified,
        "unqualified_generic_cisd": unqualified,
        "families": family_reports,
        "base_r47_diagnostics": base_diagnostics,
        "r58_diagnostics": r58_diagnostics,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R83 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R83 source failure decision drift")
    if r82.IDENTITY != (
        "VT08_INDEX_R82_PROTECTED_SWING_SOURCE_QUALIFICATION_AUDIT_001"
    ):
        raise ValueError("R83 R82 identity drift")

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
        "source_r82": {
            "identity": r82.IDENTITY,
            "run_id": SOURCE_R82_RUN_ID,
            "artifact_id": SOURCE_R82_ARTIFACT_ID,
            "artifact_digest": SOURCE_R82_ARTIFACT_DIGEST,
        },
        "allocator_contract": {
            "base": "EXACT_R47",
            "overlay": r58.CANDIDATE_ID,
            "rule_fingerprint": r58.RULE_FINGERPRINT,
            "signals_suppressed": False,
            "family_used_as_runtime_feature": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R83_PS_QUALIFICATION_R58_TRANSPORT_COMPLETE_NO_RULE_CHANGE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "exact_r47_r58_reproduction": True,
            "future_information_used": False,
            "source_qualification_used_to_change_risk": False,
            "source_qualification_used_to_suppress_signals": False,
            "family_selected_by_pnl": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
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
                    "whole": report["five_year"]["r58_whole_window"],
                    "qualified": report["five_year"]["source_qualified_union"],
                    "unqualified": report["five_year"][
                        "unqualified_generic_cisd"
                    ],
                },
                "recent_two_year": {
                    "whole": report["recent_two_year"]["r58_whole_window"],
                    "qualified": report["recent_two_year"][
                        "source_qualified_union"
                    ],
                    "unqualified": report["recent_two_year"][
                        "unqualified_generic_cisd"
                    ],
                },
                "r66": {
                    "whole": report["r66_failed_holdout"][
                        "r58_whole_window"
                    ],
                    "qualified": report["r66_failed_holdout"][
                        "source_qualified_union"
                    ],
                    "unqualified": report["r66_failed_holdout"][
                        "unqualified_generic_cisd"
                    ],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
