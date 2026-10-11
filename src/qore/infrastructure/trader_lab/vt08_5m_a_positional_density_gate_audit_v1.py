"""Real-M15 outcome-blind density bottleneck audit, author positional branch.

TTrades positional entry 2026-08-08: completed C2/C3 HTF closure and
already confirmed LTF CISD/protected swing BEFORE the next HTF opens.
A fresh CISD inside the NEW HTF is not required for that entry TYPE.
Here PS & prior POI validity remain QORE mechanical PROXIES: not fills.
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
    c2_reversal_closure,
    c3_body_closure,
)
from qore.infrastructure.trader_lab.vt08_5m_source_bias_asof_attestation_v1 import (
    SOURCE_SHA,
    attest_bias,
)
from qore.infrastructure.trader_lab.vt08_5m_three_family_fvg_causal_shape_census_v1 import (
    available_unique_fvg,
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
    protected_swings_in_candle2,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.vt08.5m.positional_source_density_bottleneck.v1"
_NY = ZoneInfo("America/New_York")


def _fingerprint(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def c2_preconfirmed_positional_shape(
    *,
    c1: Vt08B01Bar,
    c2: Vt08B01Bar,
    c2_m15: tuple[Vt08B01Bar, ...],
    owner_open_at: Vt08B01Bar,
) -> dict[str, object]:
    """Mechanical upper bound; never author-complete or executable."""
    if c1.closed_at.astimezone(UTC) != c2.opened_at.astimezone(UTC):
        raise ValueError("C1/C2 time not contiguous")
    if c2.closed_at.astimezone(UTC) != owner_open_at.opened_at.astimezone(UTC):
        raise ValueError("next H4 must open exactly when C2 closes")
    if len(c2_m15) != 16:
        raise ValueError("C2 needs all 16 closed M15 before positional open")
    start = c2.opened_at.astimezone(UTC)
    for bar in c2_m15:
        if bar.opened_at.astimezone(UTC) != start:
            raise ValueError("C2 M15 source gap/reorder")
        if bar.closed_at.astimezone(UTC) != start + timedelta(minutes=15):
            raise ValueError("source M15 must close before decision")
        if bar.closed_at > c2.closed_at:
            raise ValueError("future C2 M15 in positional state")
        start = bar.closed_at.astimezone(UTC)
    if start != c2.closed_at.astimezone(UTC):
        raise ValueError("C2 M15 not completed")
    if (
        c2_m15[0].open != c2.open
        or c2_m15[-1].close != c2.close
        or max(x.high for x in c2_m15) != c2.high
        or min(x.low for x in c2_m15) != c2.low
    ):
        raise ValueError("C2 HTF mismatch with independently closed M15")

    side = _candle2_reversal_side(c1, c2)
    if side is None:
        return {
            "reversal_closure": False,
            "side": None,
            "m15_cisd_ps_count": 0,
            "risk_oriented": None,
            "prior_fvg_active_count": None,
            "decision_at": c2.closed_at.isoformat(),
        }
    reference_level = (
        c1.low if side is DemoTradingSetupSide.LONG else c1.high
    )
    ps = protected_swings_in_candle2(
        c2_m15, side=side, important_level=reference_level,
    )
    if any(x.confirmed_at > c2.closed_at for x in ps):
        raise AssertionError("future PS leaked into positional entry")
    # With multiple PS, no hindsight/RR selector, shape remains ambiguous.
    single = ps[0] if len(ps) == 1 else None
    risk = (
        (
            owner_open_at.open > single.price
            if side is DemoTradingSetupSide.LONG
            else owner_open_at.open < single.price
        )
        if single is not None else None
    )
    return {
        "reversal_closure": True,
        "side": side.value,
        "m15_cisd_ps_count": len(ps),
        "risk_oriented": risk,
        "protected_price": str(single.price) if single else None,
        "cisd_confirmed_at": single.confirmed_at.isoformat() if single else None,
        "decision_at": c2.closed_at.isoformat(),
        "hypothetical_open": str(owner_open_at.open),
        "source_htf_poi_verified": False,
        "position_entry_authorized": False,
    }


def evaluate(path: Path) -> dict[str, object]:
    fp, market, checked, sha, rows = load_market_evidence(path)
    if sha != SOURCE_SHA or market not in EXPANSION_MARKETS:
        raise ValueError("wrong M15 market or source SHA")
    source = {bar.opened_at: bar for bar in rows}
    if len(source) != len(rows):
        raise ValueError("duplicate source M15 open")
    counts: Counter[str] = Counter()
    years: dict[str, Counter[str]] = defaultdict(Counter)
    trace: list[dict[str, object]] = []

    def mark(key: str, y: str) -> None:
        counts[key] += 1
        years[y][key] += 1

    for anchor in rows:
        local = anchor.opened_at.astimezone(_NY)
        if local.hour not in ANCHORS_NY or local.minute or local.second:
            continue
        year = str(local.year)
        mark("OWNER_H4_ANCHORS", year)
        c1 = source_h4_from_m15(source, opened_at_local=local - timedelta(hours=8))
        c2 = source_h4_from_m15(source, opened_at_local=local - timedelta(hours=4))
        if c1 is None or c2 is None:
            mark("H4_C1_OR_C2_INCOMPLETE", year)
            continue
        c2bars = _window_bars(source, opened_at=c2.opened_at, closed_at=c2.closed_at)
        c1bars = _window_bars(source, opened_at=c1.opened_at, closed_at=c1.closed_at)
        if c2bars is None or c1bars is None:
            raise AssertionError("H4 aggregated exists but M15 origin missing")
        if c2.high > c1.high and c2.low < c1.low:
            mark("C2_DUAL_SWEEP_D", year)
            continue
        proof = c2_preconfirmed_positional_shape(
            c1=c1, c2=c2, c2_m15=c2bars, owner_open_at=anchor,
        )
        if not proof["reversal_closure"]:
            mark("C2_NO_SINGLE_SWEEP_REVERSAL_CLOSE", year)
            continue
        mark("C2_REVERSAL_CLOSURE_MECHANICAL", year)
        side = (
            DemoTradingSetupSide.LONG
            if proof["side"] == DemoTradingSetupSide.LONG.value
            else DemoTradingSetupSide.SHORT
        )
        nps = int(proof["m15_cisd_ps_count"])
        mark(
            "C2_PS_ZERO" if nps == 0 else
            "C2_PS_ONE" if nps == 1 else "C2_PS_MULTIPLE_D",
            year,
        )
        if nps == 1:
            mark("PS_PRECONFIRMED_BEFORE_C3_OPEN", year)
            if proof["risk_oriented"]:
                mark("PS_PRECONFIRMED_AND_STRUCTURALLY_ORIENTED", year)
            else:
                mark("PS_PRECONFIRMED_INVALID_OPEN_RISK", year)
        att = attest_bias(source, decision_at=anchor.opened_at)
        if att is None:
            mark("OLD_B01_DAILY_BIAS_NOT_ATTESTED", year)
        elif att.bias is None:
            mark("OLD_B01_DAILY_BIAS_UNRESOLVED", year)
        elif att.bias is side:
            mark("OLD_B01_DAILY_BIAS_ALIGNED", year)
        else:
            mark("OLD_B01_DAILY_BIAS_CONFLICT", year)
        # Context only; an active FVG is NOT necessarily a meaningful HTF POI.
        old_fvg, nfvg = available_unique_fvg(c1bars, side)
        mark(
            "C1_PREEXISTING_FVG_ZERO" if nfvg == 0 else
            "C1_PREEXISTING_FVG_ONE" if nfvg == 1 else
            "C1_PREEXISTING_FVG_MULTIPLE_D",
            year,
        )
        if nfvg != 1 and nps == 1:
            mark("PS_ONE_BUT_REJECTED_BY_UNIQUE_FVG_GATE", year)
        if nps == 1 and proof["risk_oriented"] and att is not None and att.bias is side:
            mark("PS_ONE_RISK_ORIENTED_AND_OLD_BIAS_ALIGNED", year)
        preimage = {
            "market": market, "c2_opened_at": c2.opened_at.isoformat(),
            "next_h4_owner": anchor.opened_at.isoformat(), "side": proof["side"],
            "family": "AUTHOR_POSITIONAL_C3_AFTER_COMPLETED_C2",
        }
        trace.append({
            "id": "vt08-positional-source:" + _fingerprint(preimage),
            "source_family": "AUTHOR_POSITIONAL_C3_AFTER_COMPLETED_C2",
            "market": market, "origin": preimage,
            "bias": att.bias.value if att is not None and att.bias else None,
            "bias_status": "NOT_ATTESTED" if att is None else "OLD_B01_PROXY",
            "prior_c1_active_fvg_count": nfvg,
            "has_one_prior_c1_fvg": old_fvg is not None,
            **proof,
            "methodology_status": "MECHANICAL_UPPER_BOUND_SOURCE_POI_NOT_ATTESTED",
            "source_verified_trade_entry": False,
            "cognitive_ready": False, "orders": 0, "fills": 0,
        })
    return {
        "schema": SCHEMA, "market": market,
        "source_sha": sha,
        "source_fingerprint": fp,
        "market_checked_at": checked.isoformat(),
        "stage_counts": dict(sorted(counts.items())),
        "yearly_stage_counts": {k: dict(sorted(v.items())) for k, v in sorted(years.items())},
        "source_shapes": trace,
        "source_positional_authority": "2026-08-08_TTRADES",
        "mechanical_upper_bound_only": True,
        "poi_high_low_opposing_candle_not_fully_adjudicated": True,
        "cognitive_ready": False,
        "orders": 0, "fills": 0, "pnl_evaluated": False,
        "sealed_7y_accessed": False,
    }
