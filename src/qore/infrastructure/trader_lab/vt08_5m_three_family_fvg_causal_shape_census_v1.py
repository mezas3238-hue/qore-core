"""1095D consumed-source research: causal FVG→touch→CISD/PS three families.

Three separate time contracts, one valid prior M15 FVG per market window,
no ex-post selection from multiple FVGs, no C3 final OHLC read when evaluating
C3 intracycle. All outputs SHAPE_ONLY, zero orders/fills/PnL.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, timedelta
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_c3_delayed_closure_c4_shape_census_v1 import (
    c3_body_closure,
)
from qore.infrastructure.trader_lab.vt08_5m_source_bias_asof_attestation_v1 import SOURCE_SHA
from qore.infrastructure.trader_lab.vt08_5m_ttrades_source_swing_asof_contract_v1 import (
    Family,
    PoiReceipt,
    PoiType,
    ProofStatus,
    evaluate_source_swing_asof,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _candle2_reversal_side,
    _window_bars,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.vt08.5m.three_family.fvg_source_causal_swing.shape.v1"
_NY = ZoneInfo("America/New_York")


def available_unique_fvg(
    bars: tuple[Vt08B01Bar, ...],
    side: DemoTradingSetupSide,
) -> tuple[PoiReceipt | None, int]:
    """Count preexisting uninvalidated closed M15 FVGs, no arbitrary selector.

    Invalidation beyond distal boundary is a transparent QORE research
    interpretation, not a universal author-published FVG invalidation.
    """
    result: list[PoiReceipt] = []
    for i in range(2, len(bars)):
        left, _, right = bars[i - 2 : i + 1]
        if side is DemoTradingSetupSide.LONG:
            lower, upper = left.high, right.low
        else:
            lower, upper = right.high, left.low
        if lower >= upper:
            continue
        invalidated = any(
            later.low < lower if side is DemoTradingSetupSide.LONG else later.high > upper
            for later in bars[i + 1 :]
        )
        if not invalidated:
            result.append(PoiReceipt(
                kind=PoiType.FVG, side=side,
                lower=lower, upper=upper,
                formed_at=right.closed_at,
                sources=bars[i - 2 : i + 1],
            ))
    return (result[0] if len(result) == 1 else None, len(result))


def first_source_swing_prefix(
    *,
    market: str,
    family: Family,
    side: DemoTradingSetupSide,
    c1: Vt08B01Bar,
    c2: Vt08B01Bar,
    c3: Vt08B01Bar | None,
    ltf: tuple[Vt08B01Bar, ...],
    poi: PoiReceipt,
) -> dict[str, object] | None:
    """Earliest *chronologically known* source shape, no later-bar selector."""
    for n in range(1, len(ltf) + 1):
        prefix = ltf[:n]
        rec = evaluate_source_swing_asof(
            market=market,
            family=family, side=side, c1=c1, c2=c2, c3=c3,
            ltf_bars=prefix, poi=poi,
            decision_at=prefix[-1].closed_at
            if family is not Family.C2_CLOSURE_TO_C3 else c2.closed_at,
        )
        if rec.status is ProofStatus.CONFIRMED_STRUCTURE_ONLY:
            if rec.cisd_confirmed_at is None:
                raise AssertionError("confirmed without CISD source timestamp")
            if family is not Family.C2_CLOSURE_TO_C3 and (
                rec.cisd_confirmed_at > prefix[-1].closed_at
            ):
                raise AssertionError("LTF CISD used future M15")
            return rec.payload()
        if rec.status is ProofStatus.DUAL_SWEEP_UNADJUDICATED:
            raise AssertionError("dual sweep must be filtered by source parent")
        if rec.status is ProofStatus.MULTIPLE_PS_UNADJUDICATED:
            return None
    return None


def audit_market(path: Path) -> dict[str, object]:
    fp, market, checked, sha, rows = load_market_evidence(path)
    if market not in EXPANSION_MARKETS or sha != SOURCE_SHA:
        raise ValueError("not the frozen consumed 1095D M15 source")
    index = {bar.opened_at: bar for bar in rows}
    if len(index) != len(rows):
        raise ValueError("duplicate source M15 opened_at")
    counts: Counter[str] = Counter()
    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    rows_out: list[dict[str, object]] = []

    def stage(key: str, year: str) -> None:
        counts[key] += 1
        by_year[year][key] += 1

    def add(
        family: Family, row: dict[str, object], year: str,
        anchor: Vt08B01Bar,
    ) -> None:
        if row["status"] != ProofStatus.CONFIRMED_STRUCTURE_ONLY.value:
            raise AssertionError("not confirmed geometry")
        stage(f"{family.value}:SINGLE_FVG_CISD_PS_SOURCE_SHAPE", year)
        event = {
            **row,
            "source_event_id": row["origin_id"],
            "market": market,
            "owner_anchor_ny": anchor.opened_at.astimezone(_NY).isoformat(),
            "poi_policy": "UNIQUE_FVG_ONLY_NO_PRIORITY_TIEBREAK",
            "source_poi_significance_adjudicated": False,
            "author_strategy_entry_approved": False,
        }
        event["snapshot_sha256"] = hashlib.sha256(
            json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        rows_out.append(event)

    for anchor in rows:
        local = anchor.opened_at.astimezone(_NY)
        if local.hour not in ANCHORS_NY or local.minute != 0 or local.second != 0:
            continue
        year = str(local.year)
        stage("OWNER_H4_ANCHORS", year)
        c1 = source_h4_from_m15(index, opened_at_local=local - timedelta(hours=8))
        c2 = source_h4_from_m15(index, opened_at_local=local - timedelta(hours=4))
        if c1 is None or c2 is None or c2.closed_at != anchor.opened_at:
            stage("MISSING_C1_C2_SOURCE", year)
            continue
        old_c1 = _window_bars(index, opened_at=c1.opened_at, closed_at=c1.closed_at)
        old_c2 = _window_bars(index, opened_at=c2.opened_at, closed_at=c2.closed_at)
        if old_c1 is None or old_c2 is None:
            raise AssertionError("H4 exists without exact M15 provenance")
        if c2.high > c1.high and c2.low < c1.low:
            stage("DUAL_SWEEP_D_EXCLUDED_FROM_ALL_THREE_FAMILIES", year)
            continue
        side = _candle2_reversal_side(c1, c2)
        if side is not None:
            stage("C2_SINGLE_SWEEP_REVERSED", year)
            c1poi, c1n = available_unique_fvg(old_c1, side)
            stage(f"C2_FVG_PRIOR_COUNT_{'ZERO' if c1n == 0 else 'ONE' if c1n == 1 else 'MULTIPLE_D'}", year)
            if c1poi is not None:
                row = first_source_swing_prefix(
                    market=market, family=Family.C2_CLOSURE_TO_C3,
                    side=side, c1=c1, c2=c2, c3=None,
                    ltf=old_c2, poi=c1poi,
                )
                if row:
                    add(Family.C2_CLOSURE_TO_C3, row, year, anchor)
            c2poi, c2n = available_unique_fvg(old_c2, side)
            stage(f"C3_FVG_PRIOR_COUNT_{'ZERO' if c2n == 0 else 'ONE' if c2n == 1 else 'MULTIPLE_D'}", year)
            if c2poi is not None:
                c3_ltf = _window_bars(
                    index,
                    opened_at=c2.closed_at,
                    closed_at=c2.closed_at + timedelta(hours=4),
                )
                if c3_ltf is None:
                    stage("C3_M15_WINDOW_MISSING", year)
                else:
                    row = first_source_swing_prefix(
                        market=market, family=Family.C3_CONTINUATION_INTRAC3,
                        side=side, c1=c1, c2=c2, c3=None,
                        ltf=c3_ltf, poi=c2poi,
                    )
                    if row:
                        add(Family.C3_CONTINUATION_INTRAC3, row, year, anchor)
            continue
        stage("C2_NOT_COMPLETED_REVERSAL_CLOSURE", year)
        swept_low = c2.low < c1.low
        swept_hi = c2.high > c1.high
        if not (swept_low or swept_hi):
            stage("C3_C4_NO_C2_SWEEP_D", year)
            continue
        c3 = source_h4_from_m15(index, opened_at_local=local)
        if c3 is None:
            stage("C3_MISSING_SOURCE", year)
            continue
        shapes = c3_body_closure(c2, c3)
        side = DemoTradingSetupSide.LONG if swept_low else DemoTradingSetupSide.SHORT
        if not any(s.side is side for s in shapes):
            stage("C3_CLOSURE_NOT_MATCHING_PRIOR_C2_SWEEP", year)
            continue
        stage("C3_CLOSURE_MATCHES_PRIOR_C2_SWEEP", year)
        c4_local = c3.closed_at.astimezone(_NY)
        if c4_local.hour not in ANCHORS_NY:
            stage("C4_OUTSIDE_OWNER_SHAPE_ONLY", year)
            continue
        c3_ltf = _window_bars(index, opened_at=c3.opened_at, closed_at=c3.closed_at)
        if c3_ltf is None:
            stage("C3_M15_MISSING_AFTER_H4", year)
            continue
        poi, npoi = available_unique_fvg(c3_ltf, side)
        stage(f"C4_FVG_PRIOR_COUNT_{'ZERO' if npoi == 0 else 'ONE' if npoi == 1 else 'MULTIPLE_D'}", year)
        if poi is None:
            continue
        c4_ltf = _window_bars(
            index, opened_at=c3.closed_at,
            closed_at=c3.closed_at + timedelta(hours=4),
        )
        if c4_ltf is None:
            stage("C4_M15_WINDOW_MISSING", year)
            continue
        row = first_source_swing_prefix(
            market=market, family=Family.C3_CLOSURE_TO_C4,
            side=side, c1=c1, c2=c2, c3=c3, ltf=c4_ltf, poi=poi,
        )
        if row:
            add(Family.C3_CLOSURE_TO_C4, row, year, anchor)

    return {
        "schema": SCHEMA,
        "market": market,
        "evidence_fingerprint": fp,
        "source_software_sha": sha,
        "evidence_checked_at": checked.isoformat(),
        "counts": dict(sorted(counts.items())),
        "counts_per_calendar_year": {
            k: dict(sorted(v.items())) for k, v in sorted(by_year.items())
        },
        "source_geometry_receipts": rows_out,
        "structural_proof_only": True,
        "source_poi_priority_fully_reconstructed": False,
        "cognitive_ready": False,
        "authorized_orders": 0,
        "fills": 0,
        "pnl_evaluated": False,
        "sealed_7y_accessed": False,
    }
