"""VT08 Index R52 — source-complete CISD management causal lab.

R47 passed the dual-window economic gate but R51 identified severe allocator
concentration: almost all economic contribution comes from a very small set of
higher-weight FVG trades while CISD dominates trade count at the 0.005R floor.

R52 does not retune R47 and does not choose a production policy. It tests three
pre-registered, single-mechanism CISD management hypotheses while leaving every
entry, stop, FVG/relevant-swing lifecycle, structural identity, and source-
complete trade count unchanged:

1. SOFT_050_UNTIL_MFE050
2. NOPROGRESS_8B_MFE025
3. BE050

No combinations and no grid are evaluated. The purpose is causal falsification:
can early CISD failure/no-progress management improve the broad signal
population and reduce dependence on rare high-weight FVG winners?
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import vt08_index_r34_hybrid_formation_poi_health as r34
from qore.infrastructure.trader_lab import vt08_index_r43_sp500_long_stability_prior as r43
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as freeze
from qore.infrastructure.trader_lab import vt08_index_r51_concentration_robustness as r51
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

# Quality rebind after shared lint and strict-test repair.
SCHEMA = "qore.trader_lab.vt08_index_r52_cisd_management_causal_lab.v1"
IDENTITY = "VT08_INDEX_R52_CISD_MANAGEMENT_CAUSAL_LAB_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")

BASELINE_POLICY = r5.Policy(
    target_r=Decimal("2.5"),
    soft_close_loss_r=None,
    soft_close_until_mfe_r=None,
    deadline_bars=None,
    deadline_min_mfe_r=None,
    trail_name="OFF",
    trail_steps=(),
)

CISD_POLICIES: dict[str, r5.Policy] = {
    "SOFT_050_UNTIL_MFE050": r5.Policy(
        target_r=Decimal("2.5"),
        soft_close_loss_r=Decimal("0.5"),
        soft_close_until_mfe_r=Decimal("0.5"),
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="OFF",
        trail_steps=(),
    ),
    "NOPROGRESS_8B_MFE025": r5.Policy(
        target_r=Decimal("2.5"),
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=8,
        deadline_min_mfe_r=Decimal("0.25"),
        trail_name="OFF",
        trail_steps=(),
    ),
    "BE050": r5.Policy(
        target_r=Decimal("2.5"),
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="BE050",
        trail_steps=((Decimal("0.5"), Decimal("0")),),
    ),
}


def _is_cisd(opportunity: Any) -> bool:
    return str(opportunity.source_poi_kind).lower() == "cisd"


def _remanage(
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[Any, ...]],
    cisd_policy: r5.Policy,
) -> tuple[tuple[Any, r5.ManagedTrade], ...]:
    output: list[tuple[Any, r5.ManagedTrade]] = []
    for opportunity, baseline_outcome in stream:
        if _is_cisd(opportunity):
            symbol = opportunity.signal.symbol
            outcome = r5._manage_trade(
                opportunity.signal,
                bars=bars_by_symbol[symbol],
                opened=opened_by_symbol[symbol],
                policy=cisd_policy,
            )
        else:
            outcome = baseline_outcome
        output.append((opportunity, outcome))
    if len(output) != len(stream):
        raise ValueError("R52 changed source-complete density")
    return tuple(output)


def _raw_cisd_metrics(
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    values = tuple(
        outcome.r_multiple - stress
        for opportunity, outcome in stream
        if _is_cisd(opportunity)
    )
    return fx._metrics(values)


def _exit_reasons(
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
) -> dict[str, int]:
    reasons: dict[str, int] = defaultdict(int)
    for opportunity, outcome in stream:
        if _is_cisd(opportunity):
            reasons[outcome.exit_reason] += 1
    return dict(sorted(reasons.items()))


def _governed(
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> dict[str, Any]:
    _base_row, baseline = r34._row(stream, overlay=r43.BASE_POI_OVERLAY)
    assigned, diagnostics = r47._apply_transport_rules(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    primary = fx._metrics(
        r15._realized_values(assigned, stress=PRIMARY_STRESS)
    )
    secondary = fx._metrics(
        r15._realized_values(assigned, stress=SECONDARY_STRESS)
    )
    concentration = r51._concentration(assigned)
    return {
        "sample": len(assigned),
        "primary": primary,
        "secondary": secondary,
        "concentration": concentration,
        "diagnostics": diagnostics,
    }


def _window(
    *,
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[Any, ...]],
) -> dict[str, Any]:
    baseline = {
        "raw_cisd_primary": _raw_cisd_metrics(stream, stress=PRIMARY_STRESS),
        "raw_cisd_secondary": _raw_cisd_metrics(stream, stress=SECONDARY_STRESS),
        "cisd_exit_reasons": _exit_reasons(stream),
        "governed": _governed(
            stream,
            bars_by_symbol=bars_by_symbol,
        ),
    }

    hypotheses: dict[str, Any] = {}
    for policy_name, policy in CISD_POLICIES.items():
        managed = _remanage(
            stream,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            cisd_policy=policy,
        )
        governed = _governed(
            managed,
            bars_by_symbol=bars_by_symbol,
        )
        hypotheses[policy_name] = {
            "policy": policy.payload(),
            "raw_cisd_primary": _raw_cisd_metrics(
                managed,
                stress=PRIMARY_STRESS,
            ),
            "raw_cisd_secondary": _raw_cisd_metrics(
                managed,
                stress=SECONDARY_STRESS,
            ),
            "cisd_exit_reasons": _exit_reasons(managed),
            "governed": governed,
        }

    return {
        "sample": len(stream),
        "baseline": baseline,
        "hypotheses": hypotheses,
    }


def _cross_window_summary(
    five: dict[str, Any],
    two: dict[str, Any],
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for policy_name in CISD_POLICIES:
        five_row = five["hypotheses"][policy_name]
        two_row = two["hypotheses"][policy_name]
        five_raw = five_row["raw_cisd_secondary"]
        two_raw = two_row["raw_cisd_secondary"]
        five_governed = five_row["governed"]["secondary"]
        two_governed = two_row["governed"]["secondary"]
        rows[policy_name] = {
            "raw_cisd_secondary_positive_both_windows": (
                Decimal(str(five_raw["total_r"])) > 0
                and Decimal(str(two_raw["total_r"])) > 0
            ),
            "raw_cisd_secondary_pf": {
                "five_year": five_raw["profit_factor"],
                "recent_two_year": two_raw["profit_factor"],
            },
            "governed_secondary_pf": {
                "five_year": five_governed["profit_factor"],
                "recent_two_year": two_governed["profit_factor"],
            },
            "governed_secondary_total_r": {
                "five_year": five_governed["total_r"],
                "recent_two_year": two_governed["total_r"],
            },
            "nonfloor_trade_count": {
                "five_year": five_row["governed"]["concentration"][
                    "nonfloor_trade_count"
                ],
                "recent_two_year": two_row["governed"]["concentration"][
                    "nonfloor_trade_count"
                ],
            },
            "leave_top_three_terminal_positive": {
                "five_year": five_row["governed"]["concentration"][
                    "leave_top_three_terminal_positive"
                ],
                "recent_two_year": two_row["governed"]["concentration"][
                    "leave_top_three_terminal_positive"
                ],
            },
        }
    return rows


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R52 R48 freeze dependency drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )

    five = _window(
        stream=five_stream,
        bars_by_symbol={key: tuple(value) for key, value in five_bars.items()},
        opened_by_symbol=five_opened,
    )
    two = _window(
        stream=two_stream,
        bars_by_symbol={key: tuple(value) for key, value in two_bars.items()},
        opened_by_symbol=two_opened,
    )
    cross_window = _cross_window_summary(five, two)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "hypothesis_count": len(CISD_POLICIES),
        "preregistered_hypotheses": {
            key: policy.payload() for key, policy in CISD_POLICIES.items()
        },
        "five_year": five,
        "recent_two_year": two,
        "cross_window_summary": cross_window,
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "diagnostic_only": True,
            "candidate_selected": False,
            "combinatorial_grid_used": False,
            "entries_changed": False,
            "stops_changed": False,
            "fvg_management_changed": False,
            "relevant_swing_management_changed": False,
            "cisd_management_only": True,
            "source_complete_density_preserved": True,
            "five_year_consumed": True,
            "two_year_consumed": True,
            "fresh_holdout_claim": False,
            "certified": False,
            "demo_eligible": False,
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
                "hypothesis_count": report["hypothesis_count"],
                "cross_window_summary": report["cross_window_summary"],
                "governance": report["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
