"""VT08 Index R127 — target-state stop / afterlife causal attribution.

R126 is rejected: changing only the transport-adverse target state from the
canonical 2.5R research target to the source-authorized 2R target did not repair
R66 and slightly degraded the consumed 5Y/2Y economics.

R127 changes NOTHING. It studies the exact state isolated by R123:

    SWEEP_REVERSAL | PRIOR_DEEPER_THAN_FINAL_PS

The key unresolved question is whether the final canonical Protected Swing is
too shallow after the V6 first-CISD reset, or whether stopped trades genuinely
invalidate even the earlier deeper failed-attempt extreme.

For every exact target-state trade, R127 records only causal structure that was
known by canonical CISD confirmation plus post-entry path diagnostics:
- distance from final Protected Swing to the prior deeper failed-attempt extreme;
- canonical exit reason and time to exit;
- MFE before a canonical stop, excluding the stop bar for conservative ordering;
- whether the stop bar also breached the prior deeper extreme;
- whether that prior deeper extreme was breached within 4h / 24h after stop;
- favorable recovery after stop to 0.5R / 1R / 2R / 2.5R from the ORIGINAL entry;
- whether recovery occurred strictly before the prior-deeper breach.

This does not claim a wider stop would have won: widening the stop changes risk
geometry and target distance. R127 only decides whether a causal deeper-stop
replay is worth falsifying next. No signal, entry, stop, target, risk, market,
anchor or density is changed.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
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
    vt08_index_r107_standard_economic_root_attribution as r107,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r108_standard_source_retest_execution_replay as r108,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r109_standard_retest_timing_decay_attribution as r109,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r118_pre_cisd_failed_attempt_journey as r118,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r124_targeted_source_retest as r124,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r126_targeted_source_2r as r126,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r127_target_state_stop_afterlife.v1"
IDENTITY = "VT08_INDEX_R127_TARGET_STATE_STOP_AFTERLIFE_ATTRIBUTION_001"

SOURCE_R126_RUN_ID = 36059660561
SOURCE_R126_ARTIFACT_ID = 10833354775
SOURCE_R126_ARTIFACT_DIGEST = (
    "sha256:e52e6033dc75d61e631603f006c18f87"
    "e090f2346c9b1f7942208e48cb19131c"
)

TARGET_STATE = r124.TARGET_STATE
EXPECTED_TARGET_STATE = r124.EXPECTED_TARGET_STATE
EXPECTED_CANONICAL = r124.EXPECTED_CANONICAL
EXPECTED_STANDARD = r124.EXPECTED_STANDARD

RECOVERY_LEVELS = (
    Decimal("0.5"),
    Decimal("1"),
    Decimal("2"),
    Decimal("2.5"),
)


def _favorable_r(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    risk: Decimal,
    bar: Vt08IndexC2R1Bar,
) -> Decimal:
    if risk <= 0:
        raise ValueError("R127 invalid risk")
    if side is DemoTradingSetupSide.LONG:
        return (bar.high - entry) / risk
    return (entry - bar.low) / risk


def _breached(
    *,
    side: DemoTradingSetupSide,
    level: Decimal,
    bar: Vt08IndexC2R1Bar,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return bar.low <= level
    return bar.high >= level


def _prior_deepest(
    *,
    side: DemoTradingSetupSide,
    failed_attempts: Sequence[dict[str, Any]],
) -> Decimal:
    if not failed_attempts:
        raise ValueError("R127 target state requires a failed attempt")
    values = tuple(
        Decimal(str(row["extreme"]))
        for row in failed_attempts
    )
    return (
        min(values)
        if side is DemoTradingSetupSide.LONG
        else max(values)
    )


def _mfe_bucket(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "LT_0_25R"
    if value < Decimal("0.5"):
        return "R_0_25_TO_0_5"
    if value < Decimal("1"):
        return "R_0_5_TO_1"
    return "GE_1R"


def _minutes_bucket(value: int) -> str:
    if value <= 60:
        return "LE_60M"
    if value <= 120:
        return "M_61_TO_120"
    if value <= 240:
        return "M_121_TO_240"
    return "GT_240M"


def _extension_bucket(value: Decimal) -> str:
    if value <= Decimal("0.25"):
        return "LE_0_25R"
    if value <= Decimal("0.5"):
        return "R_0_25_TO_0_5"
    if value <= Decimal("1"):
        return "R_0_5_TO_1"
    return "GT_1R"


def _first_recovery(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    risk: Decimal,
    level: Decimal,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> datetime | None:
    for bar in bars:
        if _favorable_r(
            side=side,
            entry=entry,
            risk=risk,
            bar=bar,
        ) >= level:
            return bar.closed_at.astimezone(UTC)
    return None


def _first_breach(
    *,
    side: DemoTradingSetupSide,
    level: Decimal,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> datetime | None:
    for bar in bars:
        if _breached(side=side, level=level, bar=bar):
            return bar.closed_at.astimezone(UTC)
    return None


def _stop_forensics(
    item: Any,
    *,
    prior_deepest: Decimal,
    bars: Sequence[Vt08IndexC2R1Bar],
    opened: Sequence[datetime],
) -> dict[str, Any]:
    signal = item.opportunity.signal
    entry = signal.entry
    final_ps = signal.protected_swing_extreme
    risk = abs(entry - final_ps)
    if risk <= 0:
        raise ValueError("R127 target-state risk must be positive")

    signal_at = signal.signal_at.astimezone(UTC)
    exited_at = item.outcome.exited_at.astimezone(UTC)
    start = bisect_left(opened, signal_at)
    post_start = bisect_left(opened, exited_at)
    post_end = bisect_left(opened, exited_at + timedelta(hours=24))

    before_exit = tuple(
        bar
        for bar in bars[start:post_start]
        if bar.closed_at.astimezone(UTC) < exited_at
    )
    stop_bar = next(
        (
            bar
            for bar in bars[max(start, post_start - 2) : post_start + 1]
            if bar.closed_at.astimezone(UTC) == exited_at
        ),
        None,
    )
    if stop_bar is None:
        raise ValueError("R127 stop bar not found")

    post_24h = tuple(bars[post_start:post_end])
    post_4h = tuple(
        bar
        for bar in post_24h
        if bar.opened_at.astimezone(UTC) < exited_at + timedelta(hours=4)
    )
    breach_path = (stop_bar,) + post_24h

    pre_stop_mfe = max(
        (
            _favorable_r(
                side=signal.side,
                entry=entry,
                risk=risk,
                bar=bar,
            )
            for bar in before_exit
        ),
        default=Decimal(),
    )
    stop_bar_prior_breach = _breached(
        side=signal.side,
        level=prior_deepest,
        bar=stop_bar,
    )
    breach_4h = stop_bar_prior_breach or any(
        _breached(
            side=signal.side,
            level=prior_deepest,
            bar=bar,
        )
        for bar in post_4h
    )
    breach_24h = stop_bar_prior_breach or any(
        _breached(
            side=signal.side,
            level=prior_deepest,
            bar=bar,
        )
        for bar in post_24h
    )
    first_prior_breach = _first_breach(
        side=signal.side,
        level=prior_deepest,
        bars=breach_path,
    )

    recovery: dict[str, Any] = {}
    for level in RECOVERY_LEVELS:
        key = str(level).replace(".", "_")
        hit_at = _first_recovery(
            side=signal.side,
            entry=entry,
            risk=risk,
            level=level,
            bars=post_24h,
        )
        strict_before = (
            hit_at is not None
            and (
                first_prior_breach is None
                or hit_at < first_prior_breach
            )
        )
        same_bar_ambiguous = (
            hit_at is not None
            and first_prior_breach is not None
            and hit_at == first_prior_breach
        )
        recovery[f"hit_{key}r_24h"] = hit_at is not None
        recovery[f"hit_{key}r_before_prior_breach"] = strict_before
        recovery[f"hit_{key}r_same_bar_prior_breach_ambiguous"] = (
            same_bar_ambiguous
        )
        recovery[f"hit_{key}r_minutes_after_stop"] = (
            int((hit_at - exited_at).total_seconds() // 60)
            if hit_at is not None
            else None
        )

    additional = abs(prior_deepest - final_ps)
    extension_r = additional / risk

    return {
        "minutes_to_stop": int(
            (exited_at - signal_at).total_seconds() // 60
        ),
        "pre_stop_mfe_r_excluding_stop_bar": str(pre_stop_mfe),
        "pre_stop_mfe_bucket": _mfe_bucket(pre_stop_mfe),
        "prior_deeper_extension_r": str(extension_r),
        "prior_deeper_extension_bucket": _extension_bucket(extension_r),
        "stop_bar_breached_prior_deeper": stop_bar_prior_breach,
        "prior_deeper_breached_within_4h_after_stop": breach_4h,
        "prior_deeper_breached_within_24h_after_stop": breach_24h,
        "first_prior_deeper_breach_at": (
            first_prior_breach.isoformat()
            if first_prior_breach is not None
            else None
        ),
        **recovery,
    }


def _summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    stops = [row for row in rows if bool(row["is_stop"])]
    exit_reasons = Counter(str(row["exit_reason"]) for row in rows)
    if not stops:
        return {
            "sample": len(rows),
            "exit_reason_counts": dict(sorted(exit_reasons.items())),
            "stop_count": 0,
        }

    def count(field: str) -> int:
        return sum(bool(row[field]) for row in stops)

    return {
        "sample": len(rows),
        "exit_reason_counts": dict(sorted(exit_reasons.items())),
        "stop_count": len(stops),
        "stop_fraction": str(
            Decimal(len(stops)) / Decimal(len(rows))
        ) if rows else "0",
        "time_to_stop_bucket": dict(
            sorted(
                Counter(
                    _minutes_bucket(int(row["minutes_to_stop"]))
                    for row in stops
                ).items()
            )
        ),
        "pre_stop_mfe_bucket": dict(
            sorted(
                Counter(
                    str(row["pre_stop_mfe_bucket"])
                    for row in stops
                ).items()
            )
        ),
        "prior_deeper_extension_bucket": dict(
            sorted(
                Counter(
                    str(row["prior_deeper_extension_bucket"])
                    for row in stops
                ).items()
            )
        ),
        "stop_bar_breached_prior_deeper_count": count(
            "stop_bar_breached_prior_deeper"
        ),
        "stop_bar_survived_by_prior_deeper_count": (
            len(stops) - count("stop_bar_breached_prior_deeper")
        ),
        "prior_deeper_breached_within_4h_count": count(
            "prior_deeper_breached_within_4h_after_stop"
        ),
        "prior_deeper_breached_within_24h_count": count(
            "prior_deeper_breached_within_24h_after_stop"
        ),
        "after_stop_recovery": {
            "hit_0_5r_24h": count("hit_0_5r_24h"),
            "hit_1r_24h": count("hit_1r_24h"),
            "hit_2r_24h": count("hit_2r_24h"),
            "hit_2_5r_24h": count("hit_2_5r_24h"),
            "hit_2r_before_prior_breach": count(
                "hit_2r_before_prior_breach"
            ),
            "hit_2_5r_before_prior_breach": count(
                "hit_2_5r_before_prior_breach"
            ),
            "hit_2r_same_bar_ambiguous": count(
                "hit_2r_same_bar_prior_breach_ambiguous"
            ),
            "hit_2_5r_same_bar_ambiguous": count(
                "hit_2_5r_same_bar_prior_breach_ambiguous"
            ),
        },
    }


def _period_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["period"])].append(row)
    return {
        period: _summary(items)
        for period, items in sorted(grouped.items())
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol_raw, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = r74._window_contract(window_id)
    if expected != EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R127 {window_id} canonical contract drift")

    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        symbol: tuple(bars)
        for symbol, bars in bars_by_symbol_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        for symbol, bars in bars_by_symbol.items()
    }
    indexed_by_symbol = {
        symbol: {
            bar.opened_at.astimezone(UTC): bar
            for bar in bars
        }
        for symbol, bars in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _control_diag = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = tuple(control)
    if len(control) != expected:
        raise ValueError(f"R127 {window_id} control density drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R127 {window_id} STANDARD drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }

    rows: list[dict[str, Any]] = []
    target_items: list[Any] = []

    for item in control:
        if item.opportunity.identity() not in standard_ids:
            continue

        state, inside = r124._state_for_item(
            item,
            indexed_by_symbol=indexed_by_symbol,
            h4_cache=h4_cache,
        )
        if state != TARGET_STATE:
            continue

        signal = item.opportunity.signal
        touch_index = next(
            (
                index
                for index, bar in enumerate(inside)
                if bar.opened_at.astimezone(UTC)
                == item.opportunity.poi_touch_at.astimezone(UTC)
            ),
            None,
        )
        if touch_index is None:
            raise ValueError("R127 canonical POI touch missing")
        journey = r118._cisd_journey(
            inside,
            side=signal.side,
            start_index=touch_index,
        )
        if journey is None:
            raise ValueError("R127 canonical CISD journey missing")
        failed = tuple(journey["failed_attempts"])
        prior_deepest = _prior_deepest(
            side=signal.side,
            failed_attempts=failed,
        )
        relation = r118._prior_extreme_relation(
            side=signal.side,
            final_extreme=Decimal(str(journey["extreme"])),
            failed_attempts=failed,
        )
        if relation != "PRIOR_DEEPER_THAN_FINAL_PS":
            raise ValueError("R127 target-state relation drift")

        period = r109._period_label(
            exit_date=item.exited_at.astimezone(v7._NY).date(),
            window_id=window_id,
            start_date=start_date,
            end_date=end_date,
        )
        is_stop = str(item.outcome.exit_reason).startswith("stop")
        row: dict[str, Any] = {
            "trade_id": item.trade_id,
            "symbol": item.symbol,
            "side": signal.side.value,
            "anchor": str(
                signal.h4_opened_at.astimezone(v7._NY).hour
            ),
            "period": period,
            "signal_at": signal.signal_at.astimezone(UTC).isoformat(),
            "exited_at": item.exited_at.astimezone(UTC).isoformat(),
            "exit_reason": item.outcome.exit_reason,
            "is_stop": is_stop,
            "canonical_weight_r": str(item.weight),
            "canonical_raw_r": str(item.outcome.r_multiple),
            "secondary_r": str(
                (item.outcome.r_multiple - r102.SECONDARY_STRESS)
                * item.weight
            ),
            "failed_attempt_count": len(failed),
            "prior_deepest": str(prior_deepest),
            "final_protected_swing": str(
                signal.protected_swing_extreme
            ),
        }
        if is_stop:
            row.update(
                _stop_forensics(
                    item,
                    prior_deepest=prior_deepest,
                    bars=bars_by_symbol[item.symbol],
                    opened=opened_by_symbol[item.symbol],
                )
            )
        rows.append(row)
        target_items.append(item)

    if len(rows) != EXPECTED_TARGET_STATE[window_id]:
        raise ValueError(
            f"R127 {window_id} target-state drift: "
            f"{len(rows)} != {EXPECTED_TARGET_STATE[window_id]}"
        )

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "standard_sample": len(standard_ids),
        "target_state": TARGET_STATE,
        "target_state_sample": len(rows),
        "target_state_economic": r108._cohort_bundle(target_items),
        "summary": _summary(rows),
        "period_summary": _period_summary(rows),
        "stop_rows": [
            row
            for row in rows
            if bool(row["is_stop"])
        ],
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r126.IDENTITY != (
        "VT08_INDEX_R126_TARGETED_SOURCE_AUTHORIZED_2R_ABLATION_001"
    ):
        raise ValueError("R127 R126 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r126": {
            "run_id": SOURCE_R126_RUN_ID,
            "artifact_id": SOURCE_R126_ARTIFACT_ID,
            "artifact_digest": SOURCE_R126_ARTIFACT_DIGEST,
            "owner_decision": "REJECTED",
        },
        "causal_question": {
            "target_state": TARGET_STATE,
            "question": (
                "Does the prior deeper failed-attempt extreme survive "
                "canonical Protected-Swing stops often enough to justify "
                "a bounded deeper-stop replay?"
            ),
            "wider_stop_performance_claimed": False,
            "same_bar_recovery_vs_breach_counted_as_rescue": False,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": (
            "R127_TARGET_STATE_STOP_AFTERLIFE_ATTRIBUTION_COMPLETE_"
            "NO_RULE_CHANGE"
        ),
        "governance": {
            "research_only": True,
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "risk_changed": False,
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
                "five_year": report["five_year"]["summary"],
                "recent_two_year": report["recent_two_year"]["summary"],
                "r66": report["r66_failed_holdout"]["summary"],
                "r66_periods": report["r66_failed_holdout"][
                    "period_summary"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
