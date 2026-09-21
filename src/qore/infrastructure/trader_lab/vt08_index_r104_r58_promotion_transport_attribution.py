"""VT08 Index R104 — R58 promotion-mechanism transport attribution.

R103 proved that the remaining temporal instability is not explained by a
single confidence class:
- 5Y Y1 is damaged by a very small number of risk-increased trades inside the
  explicit-PS subset;
- R66 B2 has the opposite sign: its risk-increased explicit-PS trades are
  positive while STANDARD carries most of the loss.

R104 freezes the R102 policy EXPLICIT_FULL_R58_STANDARD_BASE and attributes
every explicit-PS risk request to the already-existing R55/R58 promotion
mechanisms:
- STRUCTURAL_REARM
- FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE
- FVG_H4_121_180_CISD_4_7
- CISD_LATE_REVALIDATION
- combinations of the above

No rule, signal, risk constant, entry, stop or target is changed. This is
causal transport attribution only.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as r35,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r103_confidence_temporal_failure_attribution as r103,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r104_r58_promotion_transport_attribution.v1"
IDENTITY = "VT08_INDEX_R104_R58_PROMOTION_MECHANISM_TRANSPORT_ATTRIBUTION_001"

SOURCE_R103_RUN_ID = 35554775759
SOURCE_R103_ARTIFACT_ID = 10620007573
SOURCE_R103_ARTIFACT_DIGEST = (
    "sha256:ee2a328624348d4fb6daf8a0f7da2cb97657f178ff72abf3ec4085abab26fb8d"
)
POLICY_ID = r102.POLICY_EXPLICIT_FULL


def _identity(item: r15.AssignedTrade) -> tuple[object, ...]:
    return item.opportunity.identity()


def _metrics(
    rows: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    return fx._metrics(
        tuple(
            (row.outcome.r_multiple - stress) * row.weight
            for row in sorted(
                rows,
                key=lambda x: (
                    x.exited_at.astimezone(UTC),
                    x.symbol,
                    x.trade_id,
                ),
            )
        )
    )


def _block_boundaries(window_id: str) -> tuple[date, ...]:
    if window_id == "5Y":
        return r35._annual_boundaries()
    if window_id == "2Y":
        return (
            r45.START_DATE,
            date(2025, 9, 15),
            r45.END_DATE_EXCLUSIVE,
        )
    if window_id == "R66":
        return (
            r66.START_DATE,
            r66.BLOCK_BOUNDARY,
            r66.END_DATE_EXCLUSIVE,
        )
    raise ValueError(f"unsupported window {window_id}")


def _block_name(window_id: str, index: int) -> str:
    return f"B{index + 1}" if window_id == "R66" else f"Y{index + 1}"


def _requested_labels(
    base: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> dict[tuple[object, ...], tuple[str, ...]]:
    h4_by_symbol = {
        symbol: v6._build_h4(
            {
                bar.opened_at.astimezone(UTC): bar
                for bar in bars
            }
        )
        for symbol, bars in bars_by_symbol.items()
    }
    reaction_bars, reaction_opened = r55._reaction_bars(
        bars_by_symbol
    )
    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    result: dict[tuple[object, ...], tuple[str, ...]] = {}
    for item in base:
        classification = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        explicit = str(classification["family"]) != r82.FAMILY_UNQUALIFIED
        if not explicit:
            labels: tuple[str, ...] = ("STANDARD_BASE_NO_PROMOTION",)
        else:
            _requested, raw_labels = r55._requested_weight(
                item,
                h4_by_symbol=h4_by_symbol,
                reaction_bars=reaction_bars,
                reaction_opened=reaction_opened,
            )
            clean = tuple(
                sorted(
                    label
                    for label in raw_labels
                    if not label.startswith("R47:")
                )
            )
            labels = clean if clean else ("EXPLICIT_BASE_NO_PROMOTION",)
        result[_identity(item)] = labels
    if len(result) != len(base):
        raise ValueError("R104 label identity collision")
    return result


def _label_key(labels: tuple[str, ...]) -> str:
    return "+".join(labels)


def _group_rows(
    rows: Sequence[r15.AssignedTrade],
    *,
    labels_by_id: dict[tuple[object, ...], tuple[str, ...]],
) -> dict[str, list[r15.AssignedTrade]]:
    groups: dict[str, list[r15.AssignedTrade]] = defaultdict(list)
    for row in rows:
        labels = labels_by_id[_identity(row)]
        groups[_label_key(labels)].append(row)
        for label in labels:
            groups[f"ATOM:{label}"].append(row)
    return groups


def _summarize_groups(
    groups: dict[str, list[r15.AssignedTrade]],
    *,
    base_by_id: dict[tuple[object, ...], r15.AssignedTrade],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, rows in sorted(groups.items()):
        increased = 0
        decreased = 0
        unchanged = 0
        base_weight = Decimal()
        final_weight = Decimal()
        for row in rows:
            base = base_by_id[_identity(row)]
            base_weight += base.weight
            final_weight += row.weight
            if row.weight > base.weight:
                increased += 1
            elif row.weight < base.weight:
                decreased += 1
            else:
                unchanged += 1
        result[key] = {
            "sample": len(rows),
            "risk_increased_count": increased,
            "risk_decreased_count": decreased,
            "risk_unchanged_count": unchanged,
            "base_weight_total": str(base_weight),
            "final_weight_total": str(final_weight),
            "weight_delta": str(final_weight - base_weight),
            "primary": _metrics(
                rows,
                stress=r102.PRIMARY_STRESS,
            ),
            "secondary": _metrics(
                rows,
                stress=r102.SECONDARY_STRESS,
            ),
        }
    return result


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
    bars: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        key: tuple(value)
        for key, value in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(stream),
        bars_by_symbol=bars,
    )
    base = tuple(base)
    final, policy_diag = r102._apply_confidence_policy(
        base,
        bars_by_symbol=bars,
        policy_id=POLICY_ID,
    )
    final = tuple(final)
    if len(base) != expected or len(final) != expected:
        raise ValueError(f"R104 {window_id} sample drift")

    base_by_id = {_identity(item): item for item in base}
    if len(base_by_id) != expected:
        raise ValueError("R104 base identity collision")

    labels_by_id = _requested_labels(
        base,
        bars_by_symbol=bars,
    )

    whole_groups = _group_rows(
        final,
        labels_by_id=labels_by_id,
    )

    boundaries = _block_boundaries(window_id)
    blocks: dict[str, Any] = {}
    for index in range(len(boundaries) - 1):
        start = boundaries[index]
        end = boundaries[index + 1]
        rows = tuple(
            row
            for row in final
            if start <= row.exited_at.date() < end
        )
        groups = _group_rows(
            rows,
            labels_by_id=labels_by_id,
        )
        blocks[_block_name(window_id, index)] = {
            "start_date": start.isoformat(),
            "end_date_exclusive": end.isoformat(),
            "sample": len(rows),
            "primary": _metrics(
                rows,
                stress=r102.PRIMARY_STRESS,
            ),
            "secondary": _metrics(
                rows,
                stress=r102.SECONDARY_STRESS,
            ),
            "promotion_groups": _summarize_groups(
                groups,
                base_by_id=base_by_id,
            ),
        }

    return {
        "window_id": window_id,
        "sample": expected,
        "policy_id": POLICY_ID,
        "policy_diagnostics": policy_diag,
        "whole_window_promotion_groups": _summarize_groups(
            whole_groups,
            base_by_id=base_by_id,
        ),
        "blocks": blocks,
        "provenance": provenance,
    }


def _transport_table(
    five: dict[str, Any],
    two: dict[str, Any],
    failed: dict[str, Any],
) -> dict[str, Any]:
    keys: set[str] = set()
    for section in (five, two, failed):
        keys.update(section["whole_window_promotion_groups"])

    rows: dict[str, Any] = {}
    for key in sorted(keys):
        per_window: dict[str, Any] = {}
        for name, section in (
            ("five_year", five),
            ("recent_two_year", two),
            ("r66", failed),
        ):
            row = section["whole_window_promotion_groups"].get(key)
            if row is None:
                per_window[name] = None
            else:
                per_window[name] = {
                    "sample": row["sample"],
                    "risk_increased_count": row["risk_increased_count"],
                    "secondary_pf": row["secondary"]["profit_factor"],
                    "secondary_total_r": row["secondary"]["total_r"],
                    "weight_delta": row["weight_delta"],
                }
        rows[key] = per_window
    return rows


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r103.IDENTITY != (
        "VT08_INDEX_R103_SOURCE_CONFIDENCE_TEMPORAL_FAILURE_ATTRIBUTION_001"
    ):
        raise ValueError("R104 R103 identity drift")

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
        "source_r103": {
            "run_id": SOURCE_R103_RUN_ID,
            "artifact_id": SOURCE_R103_ARTIFACT_ID,
            "artifact_digest": SOURCE_R103_ARTIFACT_DIGEST,
        },
        "policy_under_attribution": POLICY_ID,
        "promotion_atoms": [
            "STRUCTURAL_REARM",
            "FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE",
            "FVG_H4_121_180_CISD_4_7",
            "CISD_LATE_REVALIDATION",
        ],
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "transport_table": _transport_table(
            five,
            two,
            failed,
        ),
        "decision": "R104_R58_PROMOTION_TRANSPORT_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "policy_changed": False,
            "new_risk_constant": False,
            "signals_suppressed": False,
            "calendar_or_year_runtime_feature": False,
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
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "transport_table": report["transport_table"],
                "five_year_negative_blocks": {
                    k: v["promotion_groups"]
                    for k, v in report["five_year"]["blocks"].items()
                    if Decimal(str(v["secondary"]["total_r"])) <= 0
                },
                "r66_negative_blocks": {
                    k: v["promotion_groups"]
                    for k, v in report["r66_failed_holdout"]["blocks"].items()
                    if Decimal(str(v["secondary"]["total_r"])) <= 0
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
