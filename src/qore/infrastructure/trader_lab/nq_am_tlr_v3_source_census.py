"""Source-faithful V3 event census for the NQ AM liquidity-reversal research.

V3 is not a Trader. It measures source-observable event incidence on consumed
USTEC proxy evidence without selecting rules from P&L. Exact NQ futures evidence
remains a separate provider-evidence gate.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import nq_am_temporal_liquidity_reversal_v1 as v1
from qore.infrastructure.trader_lab import nq_am_temporal_liquidity_reversal_v2 as v2
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar, Evidence

IDENTITY = "QORE_NQ_AM_TLR_V3_SOURCE_CENSUS_001"
EVIDENCE_CLASS = "CONSUMED_USTEC_PROXY_RESEARCH_ONLY"

SOURCE_RULE_LEDGER: tuple[dict[str, str], ...] = (
    {
        "concept": "rth_opening_gap",
        "class": "SOURCE_EXPLICIT",
        "definition": "prior RTH final print to current 09:30 New York open",
    },
    {
        "concept": "gap_octants_quadrants",
        "class": "SOURCE_EXPLICIT",
        "definition": "grade the RTH opening gap into eighths and quarters",
    },
    {
        "concept": "initial_delivery_failure",
        "class": "SOURCE_EXPLICIT",
        "definition": "opening delivery fails lower quadrant and bodies fail lowest octant",
    },
    {
        "concept": "prior_daily_low_sellside",
        "class": "SOURCE_EXPLICIT",
        "definition": "pre-existing prior daily low used as downside liquidity reference",
    },
    {
        "concept": "two_sd_confluence",
        "class": "SOURCE_EXPLICIT",
        "definition": "reviewed event aligns prior daily low with two-SD gap extension",
    },
    {
        "concept": "macro_1050_1110",
        "class": "SOURCE_EXPLICIT",
        "definition": "price trades into 10:50-11:10 New York spooling window",
    },
    {
        "concept": "body_rejection",
        "class": "SOURCE_EXPLICIT",
        "definition": "wicks may penetrate while bodies do not accept below key area",
    },
    {
        "concept": "bearish_fvg_inversion",
        "class": "SOURCE_EXPLICIT",
        "definition": "bearish FVG from delivery leg is reclaimed and used as IFVG",
    },
    {
        "concept": "daily_midpoint_context_gate",
        "class": "QORE_MECHANIZATION",
        "definition": "V2 formula, not an explicit universal source rule",
    },
    {
        "concept": "gap_quarter_2sd_tolerance",
        "class": "QORE_MECHANIZATION",
        "definition": "V2 discretization, not an explicit universal source threshold",
    },
    {
        "concept": "ustec_vs_nq_contract",
        "class": "PROXY_LIMITATION",
        "definition": "cTrader USTEC CFD is not the exact exchange NQ futures contract",
    },
)


@dataclass(frozen=True, slots=True)
class DayObservation:
    ny_day: date
    gap_down: bool
    gap: Decimal | None
    opening_signature_1m: bool | None
    opening_signature_2m: bool | None
    opening_signature_5m: bool | None
    daily_context_v2_telemetry: bool | None
    prior_daily_reference_count: int
    untouched_reference_count: int


@dataclass(frozen=True, slots=True)
class ReferenceObservation:
    ny_day: date
    reference_day: date
    reference_low: Decimal
    untouched_before_0930: bool
    gap: Decimal | None
    extension_2: Decimal | None
    absolute_distance_to_2sd: Decimal | None
    normalized_distance_gap: Decimal | None
    opening_signature_1m: bool | None
    opening_signature_2m: bool | None
    opening_signature_5m: bool | None
    first_rth_touch_at: datetime | None
    touched_in_macro_1050_1110: bool
    body_rejected_reference_after_touch: bool | None
    body_rejected_2sd_after_touch: bool | None
    ifvg_entry_at: datetime | None
    target_0930_reached_by_noon: bool | None
    lower_low_before_target: bool | None


def _opening_signature(
    bars: tuple[Bar, ...],
    *,
    lower_quadrant: Decimal,
    lower_octant: Decimal,
    count: int,
) -> bool | None:
    if len(bars) < count:
        return None
    sample = bars[:count]
    return (
        max(item.high for item in sample) < lower_quadrant
        and max(item.close for item in sample) < lower_octant
    )


def _first_touch(
    bars: tuple[Bar, ...],
    *,
    start: datetime,
    end: datetime,
    level: Decimal,
) -> Bar | None:
    return next(
        (
            bar
            for bar in bars
            if start <= bar.opened_at < end and bar.low <= level
        ),
        None,
    )


def _outcome_after_ifvg(
    bars: tuple[Bar, ...],
    *,
    entry_at: datetime,
    expiry: datetime,
    target: Decimal,
    touch_low: Decimal,
) -> tuple[bool, bool]:
    target_reached = False
    lower_low_first = False
    for bar in bars:
        if not entry_at <= bar.opened_at < expiry:
            continue
        if bar.low < touch_low and not target_reached:
            lower_low_first = True
        if bar.high >= target:
            target_reached = True
            break
    return target_reached, lower_low_first


def _distance_bin(value: Decimal | None) -> str:
    if value is None:
        return "unavailable"
    if value <= Decimal("0.125"):
        return "<=0.125-gap"
    if value <= Decimal("0.25"):
        return "<=0.25-gap"
    if value <= Decimal("0.50"):
        return "<=0.50-gap"
    if value <= Decimal("1.00"):
        return "<=1.00-gap"
    return ">1.00-gap"


def census(
    evidence: Evidence,
    *,
    eval_open_ny: date,
    eval_close_ny: date,
) -> tuple[list[DayObservation], list[ReferenceObservation]]:
    rth = v1.build_rth_sessions(evidence.bars)
    eth = v2.build_eth_daily_sessions(
        evidence.bars,
        [item.ny_day for item in rth],
    )
    days: list[DayObservation] = []
    refs: list[ReferenceObservation] = []

    for index in range(1, len(rth)):
        current = rth[index]
        if not eval_open_ny <= current.ny_day < eval_close_ny:
            continue
        previous_rth = rth[index - 1]
        previous_eth = next(
            (item for item in reversed(eth) if item.trade_day < current.ny_day),
            None,
        )
        gap = previous_rth.settle - current.open
        gap_down = gap > 0
        early_end = v1._at_ny(current.ny_day, v1.EARLY_GAP_END)
        early = v1._bars_between(evidence.bars, current.open_at, early_end)

        sig1: bool | None = None
        sig2: bool | None = None
        sig5: bool | None = None
        extension_2: Decimal | None = None
        if gap_down:
            lower_octant = current.open + gap / Decimal(8)
            lower_quadrant = current.open + gap / Decimal(4)
            extension_2 = current.open - Decimal(2) * gap
            sig1 = _opening_signature(
                early,
                lower_quadrant=lower_quadrant,
                lower_octant=lower_octant,
                count=1,
            )
            sig2 = _opening_signature(
                early,
                lower_quadrant=lower_quadrant,
                lower_octant=lower_octant,
                count=2,
            )
            sig5 = _opening_signature(
                early,
                lower_quadrant=lower_quadrant,
                lower_octant=lower_octant,
                count=5,
            )

        context = (
            None
            if previous_eth is None
            else v2._daily_context_bullish(previous_eth, current.open)
        )
        prior = [item for item in eth if item.trade_day < current.ny_day][-5:]
        below = [item for item in prior if item.low < current.open]
        untouched_count = 0

        for item in below:
            touched_before = any(
                bar.low <= item.low
                for bar in evidence.bars
                if item.closed_at <= bar.opened_at < current.open_at
            )
            untouched = not touched_before
            untouched_count += int(untouched)

            abs_distance = (
                None if extension_2 is None else abs(item.low - extension_2)
            )
            normalized = (
                None
                if abs_distance is None or not gap_down
                else abs_distance / gap
            )
            macro_open = v1._at_ny(
                current.ny_day,
                v1.MACRO_FIRST_HALF_OPEN,
            )
            macro_close = v1._at_ny(current.ny_day, v1.MACRO_CLOSE)
            first_touch = _first_touch(
                evidence.bars,
                start=current.open_at,
                end=macro_close,
                level=item.low,
            )
            touched_macro = (
                first_touch is not None
                and macro_open <= first_touch.opened_at < macro_close
            )

            reject_ref: bool | None = None
            reject_2sd: bool | None = None
            ifvg_at: datetime | None = None
            target_reached: bool | None = None
            lower_low_first: bool | None = None
            if first_touch is not None:
                through_macro = tuple(
                    bar
                    for bar in evidence.bars
                    if first_touch.opened_at <= bar.opened_at < macro_close
                )
                reject_ref = all(bar.close > item.low for bar in through_macro)
                if extension_2 is not None:
                    reject_2sd = all(
                        bar.close > extension_2 for bar in through_macro
                    )
                ifvg = v1._ifvg_entry(
                    evidence.bars,
                    sweep_at=first_touch.opened_at,
                    deadline=macro_close,
                )
                if ifvg is not None:
                    _, ifvg_at, _ = ifvg
                    touch_low = min(
                        bar.low
                        for bar in through_macro
                        if bar.opened_at >= first_touch.opened_at
                    )
                    target_reached, lower_low_first = _outcome_after_ifvg(
                        evidence.bars,
                        entry_at=ifvg_at,
                        expiry=v1._at_ny(current.ny_day, v1.AM_EXPIRY),
                        target=current.open,
                        touch_low=touch_low,
                    )

            refs.append(
                ReferenceObservation(
                    ny_day=current.ny_day,
                    reference_day=item.trade_day,
                    reference_low=item.low,
                    untouched_before_0930=untouched,
                    gap=gap if gap_down else None,
                    extension_2=extension_2,
                    absolute_distance_to_2sd=abs_distance,
                    normalized_distance_gap=normalized,
                    opening_signature_1m=sig1,
                    opening_signature_2m=sig2,
                    opening_signature_5m=sig5,
                    first_rth_touch_at=(
                        None if first_touch is None else first_touch.opened_at
                    ),
                    touched_in_macro_1050_1110=touched_macro,
                    body_rejected_reference_after_touch=reject_ref,
                    body_rejected_2sd_after_touch=reject_2sd,
                    ifvg_entry_at=ifvg_at,
                    target_0930_reached_by_noon=target_reached,
                    lower_low_before_target=lower_low_first,
                )
            )

        days.append(
            DayObservation(
                ny_day=current.ny_day,
                gap_down=gap_down,
                gap=gap if gap_down else None,
                opening_signature_1m=sig1,
                opening_signature_2m=sig2,
                opening_signature_5m=sig5,
                daily_context_v2_telemetry=context,
                prior_daily_reference_count=len(below),
                untouched_reference_count=untouched_count,
            )
        )

    return days, refs


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _json_dataclass(value: Any) -> dict[str, Any]:
    return {key: _json_value(item) for key, item in asdict(value).items()}


def summarize(
    days: list[DayObservation],
    refs: list[ReferenceObservation],
) -> dict[str, Any]:
    untouched = [item for item in refs if item.untouched_before_0930]
    gap_refs = [item for item in untouched if item.gap is not None]
    macro = [item for item in gap_refs if item.touched_in_macro_1050_1110]
    bins: dict[str, dict[str, int]] = {}
    for item in gap_refs:
        label = _distance_bin(item.normalized_distance_gap)
        row = bins.setdefault(
            label,
            {
                "references": 0,
                "macro_touches": 0,
                "ifvg_confirmations": 0,
                "target_0930_reached": 0,
            },
        )
        row["references"] += 1
        row["macro_touches"] += int(item.touched_in_macro_1050_1110)
        row["ifvg_confirmations"] += int(item.ifvg_entry_at is not None)
        row["target_0930_reached"] += int(
            item.target_0930_reached_by_noon is True
        )

    return {
        "schema": "qore.nq_am_tlr_v3.source_census.v1",
        "identity": IDENTITY,
        "evidence_class": EVIDENCE_CLASS,
        "proxy_only": True,
        "source_instrument_equivalence_proven": False,
        "evaluated_sessions": len(days),
        "gap_down_sessions": sum(item.gap_down for item in days),
        "opening_signature_1m_sessions": sum(
            item.opening_signature_1m is True for item in days
        ),
        "opening_signature_2m_sessions": sum(
            item.opening_signature_2m is True for item in days
        ),
        "opening_signature_5m_sessions": sum(
            item.opening_signature_5m is True for item in days
        ),
        "prior_daily_reference_rows": len(refs),
        "untouched_reference_rows": len(untouched),
        "untouched_gap_down_reference_rows": len(gap_refs),
        "macro_touch_rows": len(macro),
        "macro_touch_with_ifvg_rows": sum(
            item.ifvg_entry_at is not None for item in macro
        ),
        "macro_touch_body_reject_reference_rows": sum(
            item.body_rejected_reference_after_touch is True for item in macro
        ),
        "macro_touch_body_reject_2sd_rows": sum(
            item.body_rejected_2sd_after_touch is True for item in macro
        ),
        "distance_bins": dict(sorted(bins.items())),
        "selection_authority": False,
        "pnl_computed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def write_census(evidence_path: Path, output: Path) -> dict[str, Any]:
    evidence, payload = v2._load_evidence(evidence_path)
    eval_open = date.fromisoformat(str(payload["evaluation_open_ny"]))
    eval_close = date.fromisoformat(str(payload["evaluation_close_ny"]))
    days, refs = census(
        evidence,
        eval_open_ny=eval_open,
        eval_close_ny=eval_close,
    )
    summary = summarize(days, refs)
    summary.update(
        {
            "evaluation_open_ny": eval_open.isoformat(),
            "evaluation_close_ny": eval_close.isoformat(),
            "provider": payload["provider"],
            "provider_symbol": payload["provider_symbol"],
            "instrument_class": payload["instrument_class"],
            "evidence_id": payload["evidence_id"],
        }
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "source-rule-ledger.json").write_text(
        json.dumps(SOURCE_RULE_LEDGER, indent=2, sort_keys=True) + "\n"
    )
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output / "day-observations.json").write_text(
        json.dumps(
            [_json_dataclass(item) for item in days],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (output / "reference-observations.json").write_text(
        json.dumps(
            [_json_dataclass(item) for item in refs],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            write_census(args.evidence, args.output),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
